"""Offline checks for the macOS PF killswitch script (ADR-054).

Rule rendering and DNS diagnostics run offline without touching PF. Loading rules,
the fuse, persistence and the failure drill require authorized real-device checks.
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
        return subprocess.run([BASH, str(SCRIPT), "render"], env=full, capture_output=True, text=True, encoding="utf-8", errors="replace", timeout=30)

    def test_config_diagnostics_survive_multibyte_punctuation(self):
        with tempfile.TemporaryDirectory() as tmp:
            cfg = Path(tmp) / "clash-verge.yaml"
            for locale in ("C", "en_US.UTF-8"):
                with self.subTest(locale=locale, case="missing"):
                    out = self.render(CONFIG=str(cfg), NICS="en0", LC_ALL=locale)
                    self.assertNotEqual(out.returncode, 0)
                    self.assertIn("找不到 Clash Verge 运行配置：", out.stderr)
                    self.assertNotIn("unbound variable", out.stderr)
                cfg.write_text("proxies:\n  - {server: '2001:db8::1', port: 443}\n"
                               "  - {server: 203.0.113.10, port: 443}\n", encoding="utf-8")
                with self.subTest(locale=locale, case="ipv6"):
                    out = self.render(CONFIG=str(cfg), NICS="en0", LC_ALL=locale)
                    self.assertEqual(out.returncode, 0, out.stderr)
                    self.assertIn("跳过 IPv6 节点 2001:db8::1（", out.stderr)
                cfg.unlink()

    def test_dns_diagnostics_survive_multibyte_punctuation(self):
        # Only OS observations are fixtures; source and run the actual DNS function.
        command = r"""
source "$1" render >/dev/null
RULES_PENDING="$2/pending"
RULES_CONFIRMED="$2/confirmed"
need_mac() { :; }
networksetup() {
  case "$1" in
    -listallnetworkservices) printf '%s\n' 'Services' 'Automatic' 'Manual' ;;
    -getdnsservers)
      if [ "$2" = Automatic ]; then printf "%s\n" "There aren't any DNS Servers set";
      else printf '%s\n' '1.1.1.1'; fi ;;
  esac
}
scutil() { printf '%s\n' 'nameserver[0] : 1.1.1.1'; }
route() { printf '%s\n' 'interface: utun1'; }
do_dns
"""
        with tempfile.TemporaryDirectory() as tmp:
            for locale in ("C", "en_US.UTF-8"):
                with self.subTest(locale=locale):
                    env = {"PATH": os.environ.get("PATH", ""), "HOME": tmp,
                           "NODE_IPS": "203.0.113.10", "NODE_PORTS": "443",
                           "NICS": "en0", "LC_ALL": locale}
                    out = subprocess.run([BASH, "-c", command, "pf-dns-test", str(SCRIPT), tmp],
                                         env=env, capture_output=True, text=True,
                                         encoding="utf-8", errors="replace", timeout=30)
                    self.assertEqual(out.returncode, 0, out.stderr)
                    for expected in ("Automatic：自动", "Manual：手动", "utun1：会进 TUN"):
                        self.assertIn(expected, out.stdout)
                    self.assertNotIn("unbound variable", out.stderr)

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
        self.assertEqual(lines[-1], "block drop out log quick on $cg_nics all")
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

    def test_blocked_summary_keeps_categories_and_drops_addresses(self):
        # pflog lines as tcpdump -n -q -e prints them; the summary is what the owner pastes back
        log = "\n".join((
            "rule 4/0(match): block out on en0: 192.168.1.20.53211 > 192.168.1.1.53: UDP, length 32",
            "rule 4/0(match): block out on en0: 192.168.1.20.53212 > 192.168.1.1.53: UDP, length 32",
            "rule 4/0(match): block out on en0: 192.168.1.20.5353 > 224.0.0.251.5353: UDP, length 40",
            "rule 4/0(match): block out on en0: 192.168.1.20.61000 > 203.0.113.53.53: UDP, length 30",
            "rule 4/0(match): block out on en0: 192.168.1.20.50000 > 198.51.100.80.443: tcp 0",
            "rule 4/0(match): block out on en0: 192.168.1.20 > 203.0.113.1: ICMP echo request, id 1",
            "rule 4/0(match): block out on en7: IP6 fe80::1.5353 > ff02::fb.5353: UDP, length 40",
            "not a packet line",
        )) + "\n"
        out = subprocess.run([BASH, str(SCRIPT), "_summarize"], input=log, capture_output=True, text=True, timeout=30)
        self.assertEqual(out.returncode, 0, out.stderr)
        lines = out.stdout.splitlines()
        self.assertEqual(lines[0], "共 7 个被拦的包")
        self.assertRegex(lines[1], r"^\s+2  en0 局域网 UDP/53$")
        for row in ("en0 组播/广播 UDP/5353", "en0 公网 UDP/53", "en0 公网 TCP/443", "en0 公网 ICMP/-", "en7 IPv6"):
            self.assertIn(row, out.stdout)
        self.assertNotRegex(out.stdout, r"\d+\.\d+\.\d+\.\d+|fe80|ff02")

    def test_address_classes(self):
        for ip, expected in (("192.168.1.1", "局域网地址"), ("10.0.0.1", "局域网地址"), ("172.31.0.1", "局域网地址"),
                             ("172.32.0.1", "公网地址"), ("100.64.0.1", "运营商内网地址"), ("198.18.0.2", "fake-ip 地址"),
                             ("127.0.0.1", "本机回环"), ("1.1.1.1", "公网地址"), ("fe80::1", "IPv6 地址")):
            out = subprocess.run([BASH, str(SCRIPT), "_class", ip], capture_output=True, text=True, timeout=30)
            self.assertEqual(out.stdout.strip(), expected, ip)

    def test_privileged_commands_need_root(self):
        if os.geteuid() == 0:
            self.skipTest("running as root")
        for cmd in ("apply", "confirm", "rollback", "persist", "uninstall", "blocked"):
            out = subprocess.run([BASH, str(SCRIPT), cmd], capture_output=True, text=True, timeout=30)
            self.assertNotEqual(out.returncode, 0, cmd)


class ScriptContract(unittest.TestCase):
    def test_design_and_wiring(self):
        text = SCRIPT.read_text(encoding="utf-8")
        for term in ('ANCHOR="com.apple/claude-guardian"', "pfctl -E", "pfctl -X", "FUSE_SECONDS:-180",
                     "RULES_PENDING", "RULES_CONFIRMED", "launchctl bootstrap system", "-F rules",
                     "do_dns", "networksetup -getdnsservers", "aren't any", "tcpdump -n -q -l -e -i pflog0"):
            self.assertIn(term, text)
        # never edits the system pf.conf, never flushes global state or disables PF outright
        self.assertNotRegex(text, r">\s*/etc/pf\.conf")
        self.assertNotRegex(text, r"pfctl[^\n]*-F (all|states)")
        self.assertNotRegex(text, r"pfctl -d\b")
        code = "\n".join(l for l in text.splitlines() if not l.lstrip().startswith("#"))
        self.assertNotRegex(code, r"\b(mapfile|readarray|declare -A)\b")  # macOS ships bash 3.2
        guide = (ROOT / "skills" / "claude-guardian" / "references" / "local-firewall-prompts.md").read_text(encoding="utf-8")
        for term in ("Issue #17", "按网卡", "Issue #25", "已验收", "所有者确认", "现场修正版", "已合入随包脚本", "C 档"):
            self.assertIn(term, guide)
        self.assertNotIn("Block Mode", guide)
        self.assertNotIn("允许规则要加在**核心**身上", guide)
        self.assertIn("ADR-054", (ROOT / "docs" / "decisions.md").read_text(encoding="utf-8"))
        self.assertIn("assets/mac-killswitch/guardian-pf-killswitch.sh",
                      (ROOT / "tools" / "package_skill.py").read_text(encoding="utf-8"))


    def test_completed_pf_acceptance_documents_are_removed(self):
        names = ("docs/mac-pf-killswitch-test.md",
                 "reports/mac-pf-isolated-acceptance-2026-11-02.md")
        for name in names:
            self.assertFalse((ROOT / name).exists(), name)
        for path in (ROOT / "skills" / "claude-guardian").rglob("*.md"):
            for name in names:
                self.assertNotIn(Path(name).name, path.read_text(encoding="utf-8"), str(path))

    def test_pf_acceptance_status_is_synchronized(self):
        paths = (
            "README.md", "README.en.md",
            "skills/claude-guardian/references/scripts-index.md",
            "skills/claude-guardian/references/local-firewall-prompts.md",
            "skills/claude-guardian/references/routes-and-platforms.md",
            "skills/claude-guardian/references/whole-machine-ipv4.md",
        )
        for name in paths:
            with self.subTest(path=name):
                body = (ROOT / name).read_text(encoding="utf-8")
                self.assertIn("2026-11-09", body)
                self.assertIn("owner-confirmed" if name == "README.en.md" else "所有者确认", body)
        whole_machine = (ROOT / paths[-1]).read_text(encoding="utf-8")
        self.assertNotIn("停核心演练还没在真机上做", whole_machine)
        self.assertNotIn("靠 LuLu 或系统防火墙", whole_machine)
        english = (ROOT / "README.en.md").read_text(encoding="utf-8")
        self.assertNotIn("not yet verified on a real Mac", english)


if __name__ == "__main__":
    unittest.main()
