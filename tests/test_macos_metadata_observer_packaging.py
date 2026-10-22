"""Offline installed-observer/guide checks; no native metadata acceptance."""
import ast
import hashlib
import json
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock
import zipfile


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'claude-guardian'
OBSERVER = 'scripts/macos_metadata_observer.py'
GUIDE = ROOT / 'docs/macos-metadata-observer.md'
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


class MacOSMetadataObserverPackagingTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='guardian-metadata-package-')
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
        cls.decoys = (
            'scripts/macos_metadata_probe.py', 'scripts/metadata-audit.json',
            'reports/metadata.json', 'audits/metadata.json',
            'references/private-metadata-audit.md', 'docs/macos-metadata-observer.md',
        )
        for relative in cls.decoys:
            target = cls.skill / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(SENTINEL)
        (cls.repo / 'docs').mkdir()
        shutil.copyfile(GUIDE, cls.repo / 'docs/macos-metadata-observer.md')
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

    def test_explicit_99_member_package_contains_observer_and_no_audits(self):
        expected = {'claude-guardian/' + path for path in self.paths}
        expected.add('claude-guardian/LICENSE')
        self.assertEqual(self.paths.count(OBSERVER), 1)
        self.assertEqual(self.paths.count("scripts/agent_rules_task.py"), 1)
        self.assertEqual(self.paths.count("references/agent-rules-task.md"), 1)
        self.assertEqual(len(expected), 99)
        self.assertEqual(len(self.members), 99)
        self.assertEqual(set(self.members), expected)
        self.assertEqual(self.members, sorted(self.members))
        self.assertFalse(any('docs/' in name or 'tests/' in name for name in self.members))
        for decoy in self.decoys:
            self.assertNotIn('claude-guardian/' + decoy, self.members)
        with zipfile.ZipFile(self.archive) as archive:
            self.assertEqual(archive.read('claude-guardian/' + OBSERVER),
                             (SKILL / OBSERVER).read_bytes())
            self.assertEqual(archive.read('claude-guardian/sources/manifest.json'),
                             (SKILL / 'sources/manifest.json').read_bytes())
            for name in self.members:
                self.assertNotIn(SENTINEL, archive.read(name))

    def test_package_remains_byte_reproducible(self):
        second = self.base / 'release-second.zip'
        self.build(second)
        self.assertEqual(hashlib.sha256(self.archive.read_bytes()).digest(),
                         hashlib.sha256(second.read_bytes()).digest())

    def test_missing_observer_is_not_silently_omitted(self):
        observer = self.skill / OBSERVER
        saved = observer.read_bytes()
        observer.unlink()
        output = self.base / 'missing-observer.zip'
        try:
            with self.assertRaises(subprocess.CalledProcessError) as caught:
                self.build(output)
            self.assertIn('Release manifest is incomplete', caught.exception.stderr)
            self.assertFalse(output.exists())
        finally:
            observer.write_bytes(saved)

    def test_installed_help_is_standalone_and_does_not_create_reports(self):
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-B', str(self.installed / OBSERVER), '--help'],
            cwd=self.unrelated, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--fd', result.stdout)
        self.assertNotIn('--path', result.stdout)
        self.assertEqual(result.stderr, '')
        self.assertEqual(list(self.unrelated.iterdir()), [])

    def test_installed_help_off_darwin_does_not_touch_descriptor_or_native_library(self):
        # Force the off-Darwin branch even when this offline test runs on a Mac.
        runner = r'''
import ctypes, os, runpy, sys
script = sys.argv[1]
def forbidden(*args, **kwargs):
    raise AssertionError('help must not inspect an object or load a native library')
os.fstat = forbidden
ctypes.CDLL = forbidden
sys.platform = 'linux'
sys.argv = [script, '--help']
runpy.run_path(script, run_name='__main__')
'''
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-B', '-c', runner,
             str(self.installed / OBSERVER)],
            cwd=self.unrelated, capture_output=True, text=True, timeout=10,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn('--fd', result.stdout)
        self.assertEqual(result.stderr, '')

    def test_guide_example_passes_only_the_preopened_descriptor(self):
        text = GUIDE.read_text(encoding='utf-8')
        examples = re.findall(r'```python\n(.*?)\n```', text, flags=re.DOTALL)
        self.assertEqual(len(examples), 1)
        namespace = {}
        exec(compile(examples[0], str(GUIDE), 'exec'), namespace)
        expected = {'observation_state': 'unsupported', 'code': 'UNSUPPORTED_PLATFORM'}
        completed = subprocess.CompletedProcess([], 1, json.dumps(expected), '')
        fixed_script = self.installed / OBSERVER
        with mock.patch.object(subprocess, 'run', return_value=completed) as run:
            code, report = namespace['observe_selected_fd'](fixed_script, 42)
        self.assertEqual(code, 1)
        self.assertEqual(report, expected)
        run.assert_called_once_with(
            [sys.executable, '-I', '-S', '-B', str(fixed_script), '--fd', '42'],
            pass_fds=(42,), shell=False, capture_output=True, text=True,
            encoding='utf-8', timeout=10, check=False,
        )
        for boundary in ('already-open', 'required read approval', 'os.listxattr',
                         'flistxattr', 'not_inspected', 'not_established',
                         'native macOS execution is pending',
                         'cannot validate this module'):
            self.assertIn(boundary, text)
        self.assertNotRegex(text, r'/Users/[^\s/]+|/home/[^\s/]+')


if __name__ == '__main__':
    unittest.main()
