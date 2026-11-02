"""Offline checks for the macOS PF killswitch script (ADR-054).

Only the `render` path runs here: it builds the rules without touching PF. Loading rules,
the fuse, persistence and the failure drill need a real Mac (docs/mac-pf-killswitch-test.md).
"""
import os
import re
import shutil
import subprocess
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills" / "claude-guardian" / "assets" / "mac-killswitch" / "guardian-pf-killswitch.sh"
BASH = shutil.which("bash")

CONFIG = """mixed-port: 7897
port: 7890
dns:
  listen: 0.0.0.0:1053
proxies:
  - {name: a, server: 203.0.113.10, port: 443, type: vless}
  - name: "b"
    type: hysteria2
    server: '198.51.100.7'
    port: 8443
    ports: 20000-30000
- {name: c, server: "203.0.113.10", port: "2053", type: trojan}
proxy-groups:
  - {name: G, type: select, proxies: [a, b]}
rules:
  - MATCH,G
"""


@unittest.skipIf(BASH is None or os.name == "nt", "needs a POSIX bash")
class RenderRules(unittest.TestCase):
    def render(self, **env):
        full = {"PATH": os.environ.get("PATH", ""), "HOME": tempfile.gettempdir()}
        full.update(env)
        return subprocess.run([BASH, str(SCRIPT), "render"], env=full, capture_output=True, text=True, timeout=30)

    def test_syntax(self):
        self.assertEqual(subprocess.run([BASH, "-n", str(SCRIPT)]).returncode, 0)

    def test_reads_only_proxies_and_blocks_physical_nics(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "clash-verge.yaml"
            cfg.write_text(CONFIG, encoding="utf-8")
            out = self.render(CONFIG=str(cfg), NICS="en0,en7")
        self.assertEqual(out.returncode, 0, out.stderr)
        rules = out.stdout
        self.assertIn('cg_nics = "{ en0 en7 }"', rules)
        self.assertIn("table <cg_nodes> const { 198.51.100.7 203.0.113.10 }", rules)
        # proxy ports only: top-level port/mixed-port and the dns listener are not node ports
        self.assertIn('cg_node_ports = "{ 2053 443 8443 }"', rules)
        for port in ("7890", "7897", "1053"):
            self.assertNotIn(port, rules)
        lines = [l for l in rules.splitlines() if l and not l.startswith("#")]
        self.assertEqual(lines[-1], "block drop out quick on $cg_nics all")
        passes = [l for l in lines if l.startswith("pass ")]
        self.assertTrue(passes and all(l.startswith("pass out quick on $cg_nics ") for l in passes))
        # utun and lo0 are never named, so TUN and loopback traffic is left alone
        self.assertNotRegex(rules, r"utun|lo0")
        self.assertNotIn("cg_dns", rules)
        self.assertNotIn("cg_lan", rules)

    def test_optional_dns_and_lan_exceptions(self):
        out = self.render(NODE_IPS="203.0.113.10", NODE_PORTS="443", NICS="en0",
                          BOOTSTRAP_DNS="223.5.5.5", LAN_NET="192.168.1.0/24")
        self.assertEqual(out.returncode, 0, out.stderr)
        self.assertIn("to <cg_dns> port 53 keep state", out.stdout)
        self.assertIn("table <cg_lan> const { 192.168.1.0/24 }", out.stdout)

    def test_rejects_unsafe_or_wrong_inputs(self):
        cases = (
            dict(NODE_IPS="198.18.0.5", NODE_PORTS="443", NICS="en0"),      # fake-ip is not a node
            dict(NODE_IPS="1.2.3.4;x", NODE_PORTS="443", NICS="en0"),
            dict(NODE_IPS="1.2.3.400", NODE_PORTS="443", NICS="en0"),
            dict(NODE_IPS="1.2.3.4", NODE_PORTS="70000", NICS="en0"),
            dict(NODE_IPS="1.2.3.4", NODE_PORTS="443", NICS="en0}"),
            dict(NODE_IPS="1.2.3.4", NODE_PORTS="443", NICS="en0", LAN_NET="192.168.1.0/33"),
            dict(NODE_IPS="1.2.3.4", NICS="en0"),
            dict(CONFIG="/nonexistent/clash-verge.yaml", NICS="en0"),
        )
        for env in cases:
            out = self.render(**env)
            self.assertNotEqual(out.returncode, 0, env)
            self.assertIn("ERROR", out.stderr, env)
            self.assertNotIn("block drop", out.stdout, env)

    def test_privileged_commands_need_root(self):
        if os.geteuid() == 0:
            self.skipTest("running as root")
        for cmd in ("apply", "confirm", "rollback", "persist", "uninstall"):
            out = subprocess.run([BASH, str(SCRIPT), cmd], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(out.returncode, 0, cmd)


class ScriptContract(unittest.TestCase):
    def test_design_and_wiring(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for term in ('ANCHOR="com.apple/claude-guardian"', "pfctl -E", "pfctl -X", "FUSE_SECONDS:-180",
                     "RULES_PENDING", "RULES_CONFIRMED", "launchctl bootstrap system", "-F rules"):
            self.assertIn(term, text)
        # never edits the system pf.conf, never flushes global state or disables PF outright
        self.assertNotRegex(text, r">\s*/etc/pf\.conf")
        self.assertNotRegex(text, r"pfctl[^\n]*-F (all|states)")
        self.assertNotRegex(text, r"pfctl -d\b")
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotRegex(code, r"\b(mapfile|readarray|declare -A)\b")  # macOS ships bash 3.2
        guide = (ROOT / "skills" / "claude-guardian" / "references" / "local-firewall-prompts.md").read_text(encoding="utf-8")
        for term in ("Issue #17", "按网卡", "还没有在真机 Mac 上验证", "docs/mac-pf-killswitch-test.md", "C 档"):
            self.assertIn(term, guide)
        self.assertNotIn("Block Mode", guide)
        self.assertNotIn("允许规则要加在**核心**身上", guide)
        self.assertTrue((ROOT / "docs" / "mac-pf-killswitch-test.md").is_file())
        self.assertIn("ADR-054", (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8"))
        self.assertIn("assets/mac-killswitch/guardian-pf-killswitch.sh",
                      (ROOT / "tools" / "package_skill.py").read_text(encoding="utf-8"))


if __name__ == "__main__":
    unittest.main()
