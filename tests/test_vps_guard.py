"""vps-guard.sh rule rendering: the opt-in mosh UDP rule (render only; nothing is applied)."""
import os
import shutil
import subprocess
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "skills" / "claude-guardian" / "references"


class VpsGuardMoshRule(unittest.TestCase):
    @unittest.skipUnless(os.name == "posix" and shutil.which("bash"), "needs bash")
    def test_vps_guard_mosh_udp_is_opt_in_and_scoped_to_admin_net(self):
        guard = ROOT / "skills" / "claude-guardian" / "assets" / "vps-firewall" / "vps-guard.sh"

        def render(**extra):
            env = {"PATH": os.environ.get("PATH", ""), "ADMIN_NET": "203.0.113.7/32", **extra}
            return subprocess.run(["bash", str(guard), "render"], env=env, capture_output=True, text=True)

        default = render()
        self.assertEqual(default.returncode, 0, default.stderr)
        self.assertNotIn("60000", default.stdout)
        self.assertEqual(default.stdout.count("udp dport"), 1)  # only the DHCP client rule
        enabled = render(MOSH="1")
        self.assertEqual(enabled.returncode, 0, enabled.stderr)
        self.assertIn("ip saddr 203.0.113.7/32 udp dport 60000-61000 counter accept", enabled.stdout)
        self.assertEqual(enabled.stdout.replace(
            "        ip saddr 203.0.113.7/32 udp dport 60000-61000 counter accept\n", ""), default.stdout)
        custom = render(MOSH="1", MOSH_PORTS="60001-60010")
        self.assertIn("udp dport 60001-60010 counter accept", custom.stdout)
        for bad in ({"MOSH": "yes"}, {"MOSH": "1", "MOSH_PORTS": "80-90"}, {"MOSH": "1", "MOSH_PORTS": "61000-60000"},
                    {"MOSH": "1", "MOSH_PORTS": "1;drop"}, {"MOSH": "1", "MOSH_PORTS": "60000-70000"}):
            with self.subTest(env=bad):
                result = render(**bad)
                self.assertNotEqual(result.returncode, 0)
                self.assertNotIn("table inet", result.stdout)
        vps = (REFS / "vps-guidance.md").read_text(encoding="utf-8")
        for term in ("MOSH=1", "UDP 60000–61000", "MOSH_PORTS", "重新 install 并 confirm"):
            self.assertIn(term, vps)


if __name__ == "__main__":
    unittest.main()
