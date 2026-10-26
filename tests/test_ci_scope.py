import importlib.util
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("ci_scope", ROOT / "tools" / "ci_scope.py")
ci_scope = importlib.util.module_from_spec(spec)
spec.loader.exec_module(ci_scope)


class CiScopeTests(unittest.TestCase):
    def test_docs_only_runs_linux(self):
        result = ci_scope.classify(["CHANGELOG.md", "skills/claude-guardian/references/account-onboarding.md",
                                    "skills/claude-guardian/sources/S03-claude-experience.pdf"])
        self.assertEqual(result["scope"], "docs")
        self.assertEqual(result["os"], ["ubuntu-latest"])

    def test_any_code_test_or_data_file_runs_full_matrix(self):
        for name in ("tools/ci_scope.py", "tests/test_guides.py", "skills/claude-guardian/sources/manifest.json",
                     "skills/claude-guardian/assets/webrtc-probe.html", "skills/claude-guardian/assets/vps-firewall/vps-guard.sh"):
            self.assertEqual(ci_scope.classify(["README.md", name])["scope"], "full", name)

    def test_workflow_markdown_still_runs_full_matrix(self):
        self.assertEqual(ci_scope.classify([".github/ISSUE_TEMPLATE/x.md"])["scope"], "full")

    def test_unreadable_range_runs_full_matrix(self):
        self.assertEqual(ci_scope.classify([])["scope"], "full")
        self.assertIsNone(ci_scope.changed_files("0" * 40, "HEAD"))
        self.assertIsNone(ci_scope.changed_files("", "HEAD"))

    def test_cli_reads_git_range(self):
        with tempfile.TemporaryDirectory() as tmp:
            run = lambda *a: subprocess.run(["git", *a], cwd=tmp, check=True, capture_output=True, text=True)
            run("init", "-q")
            run("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "--allow-empty", "-m", "a")
            Path(tmp, "a.md").write_text("x", encoding="utf-8")
            run("add", "a.md")
            run("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "b")
            out = subprocess.run([sys.executable, str(ROOT / "tools" / "ci_scope.py"), "--base", "HEAD~1", "--head", "HEAD"],
                                 cwd=tmp, capture_output=True, text=True, check=True,
                                 env={k: v for k, v in __import__("os").environ.items() if k != "GITHUB_OUTPUT"})
            self.assertIn("scope=docs", out.stdout)
            Path(tmp, "b.py").write_text("x", encoding="utf-8")
            run("add", "b.py")
            run("-c", "user.name=t", "-c", "user.email=t@example.invalid", "commit", "-q", "-m", "c")
            out = subprocess.run([sys.executable, str(ROOT / "tools" / "ci_scope.py"), "--base", "HEAD~1", "--head", "HEAD"],
                                 cwd=tmp, capture_output=True, text=True, check=True,
                                 env={k: v for k, v in __import__("os").environ.items() if k != "GITHUB_OUTPUT"})
            self.assertIn("scope=full", out.stdout)

    def test_workflow_uses_the_scope(self):
        wf = (ROOT / ".github" / "workflows" / "tests.yml").read_text(encoding="utf-8")
        self.assertIn("tools/ci_scope.py", wf)
        self.assertIn("fromJSON(needs.scope.outputs.os)", wf)
        self.assertIn("needs.scope.outputs.scope == 'full'", wf)


if __name__ == "__main__":
    unittest.main()
