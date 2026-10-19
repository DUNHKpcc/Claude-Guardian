"""Run the documented Bash copy step only in disposable homes."""
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest


@unittest.skipUnless(os.name == 'posix' and shutil.which('bash'),
                     'README Bash installation targets macOS/Linux')
class ReadmeInstallTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        self.home = self.root / 'home'
        self.home.mkdir()
        self.source = self.root / 'Claude-Guardian/skills/claude-guardian'
        (self.source / 'references').mkdir(parents=True)
        (self.source / 'SKILL.md').write_text('new skill\n', encoding='utf-8')
        (self.source / 'references/example.md').write_text('reference\n', encoding='utf-8')
        self.target = self.home / '.codex/skills/claude-guardian'
        readme = (Path(__file__).resolve().parents[1] / 'README.md').read_text(encoding='utf-8')
        block = re.search(r'```bash\ngit clone [^\n]+\n(.*?)\n```', readme, re.S)
        self.assertIsNotNone(block, 'Expected documented clone and Bash install block')
        self.install = block.group(1)

    def run_install(self):
        # Override HOME only for this child; never assign or touch the real home.
        env = dict(os.environ, HOME=str(self.home))
        return subprocess.run(['bash', '--noprofile', '--norc', '-c', self.install],
                              cwd=self.root, env=env, text=True,
                              capture_output=True, timeout=10)

    def assert_installed(self):
        result = self.run_install()
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual((self.target / 'SKILL.md').read_bytes(),
                         (self.source / 'SKILL.md').read_bytes())
        self.assertEqual((self.target / 'references/example.md').read_bytes(),
                         (self.source / 'references/example.md').read_bytes())
        self.assertFalse((self.target / 'claude-guardian').exists())

    def test_fresh_home(self):
        self.assert_installed()

    def test_parent_directory_already_exists(self):
        self.target.parent.mkdir(parents=True)
        self.assert_installed()

    def test_existing_skill_is_preserved_without_nesting(self):
        self.target.mkdir(parents=True)
        (self.target / 'SKILL.md').write_text('custom skill\n', encoding='utf-8')
        before = {p.relative_to(self.target): p.read_bytes()
                  for p in self.target.rglob('*') if p.is_file()}
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        after = {p.relative_to(self.target): p.read_bytes()
                 for p in self.target.rglob('*') if p.is_file()}
        self.assertEqual(after, before)
        self.assertFalse((self.target / 'claude-guardian').exists())

    def test_dangling_target_link_is_preserved(self):
        self.target.parent.mkdir(parents=True)
        self.target.symlink_to(self.root / 'missing')
        result = self.run_install()
        self.assertNotEqual(result.returncode, 0)
        self.assertTrue(self.target.is_symlink())
        self.assertFalse((self.root / 'missing').exists())


if __name__ == '__main__':
    unittest.main()
