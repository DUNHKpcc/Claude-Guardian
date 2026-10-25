"""Release package: explicit member list, reproducible bytes, installed entry points run standalone."""
import ast
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'claude-guardian'
ENTRY = 'scripts/network_check.py'
SENTINEL = b'synthetic-unlisted-metadata-audit-sentinel'


def release_paths():
    tree = ast.parse((ROOT / 'tools/package_skill.py').read_text(encoding='utf-8'))
    assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                   and any(isinstance(target, ast.Name) and target.id == 'release_paths'
                           for target in node.targets)]
    if len(assignments) != 1:
        raise AssertionError('Expected one explicit release list')
    paths = ast.literal_eval(assignments[0].value)
    manifest = json.loads((SKILL / 'sources/manifest.json').read_text(encoding='utf-8'))
    for source in manifest['sources'] + manifest.get('collections', []):
        paths.append(source['path'])
        paths.extend(companion['path'] for companion in source.get('companions', []))
    return paths


class PackageMembersTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='guardian-package-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.base = Path(cls.tmp.name).resolve()
        cls.repo = cls.base / 'repo'
        cls.skill = cls.repo / 'skills/claude-guardian'
        cls.paths = release_paths()
        # Copy only the explicit public input list; never copy an actual audit.
        for relative in cls.paths:
            target = cls.skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            shutil.copyfile(SKILL / relative, target)
        (cls.repo / 'tools').mkdir()
        shutil.copyfile(ROOT / 'tools/package_skill.py', cls.repo / 'tools/package_skill.py')
        shutil.copyfile(ROOT / 'LICENSE', cls.repo / 'LICENSE')
        cls.decoys = ('scripts/metadata-audit.json', 'reports/metadata.json', 'audits/metadata.json',
                      'references/private-metadata-audit.md', 'docs/private-notes.md')
        for relative in cls.decoys:
            target = cls.skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(SENTINEL)
        cls.archive = cls.base / 'release.zip'
        cls.build(cls.archive)
        with zipfile.ZipFile(cls.archive) as archive:
            cls.members = archive.namelist()
            archive.extractall(cls.base / 'installed')
        cls.installed = cls.base / 'installed/claude-guardian'
        cls.unrelated = cls.base / 'unrelated'
        cls.unrelated.mkdir()

    @classmethod
    def build(cls, output):
        return subprocess.run(
            [sys.executable, '-B', str(cls.repo / 'tools/package_skill.py'),
             '--output', str(output)],
            check=True, capture_output=True, text=True, timeout=30,
        )

    def test_explicit_member_list_and_no_audits(self):
        expected = {'claude-guardian/' + path for path in self.paths}
        expected.add('claude-guardian/LICENSE')
        for path in (ENTRY, 'scripts/agent_rules_task.py', 'references/agent-rules-task.md'):
            self.assertEqual(self.paths.count(path), 1, path)
        self.assertEqual(len(expected), len(self.members))
        self.assertEqual(set(self.members), expected)
        self.assertEqual(self.members, sorted(self.members))
        self.assertFalse(any('docs/' in name or 'tests/' in name for name in self.members))
        for decoy in self.decoys:
            self.assertNotIn('claude-guardian/' + decoy, self.members)
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read('claude-guardian/' + ENTRY), (SKILL / ENTRY).read_bytes())
            for name in self.members:
                self.assertNotIn(SENTINEL, archive.read(name))

    def test_every_script_on_disk_is_shipped(self):
        on_disk = {'scripts/' + p.name for p in (SKILL / 'scripts').glob('*.py')}
        self.assertEqual(sorted(on_disk - set(self.paths)), [])

    def test_package_remains_byte_reproducible(self):
        second = self.base / 'release-second.zip'
        self.build(second)
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).digest(),
                         hashlib.sha256(second.read_bytes()).digest())

    def test_missing_member_is_not_silently_omitted(self):
        entry = self.skill / ENTRY
        saved = entry.read_bytes()
        entry.unlink()
        output = self.base / 'missing-entry.zip'
        try:
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                self.build(output)
            self.assertIn('Release manifest is incomplete', caught.exception.stderr)
            self.assertFalse(output.exists())
        finally:
            entry.write_bytes(saved)

    def test_installed_help_is_standalone_and_does_not_create_files(self):
        result = subprocess.run(
            [sys.executable, '-E', '-s', '-B', str(self.installed / ENTRY), '--help'],
            cwd=self.unrelated, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('run', result.stdout)
        self.assertEqual(list(self.unrelated.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
