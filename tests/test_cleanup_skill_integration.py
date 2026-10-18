"""Packaged C5 intent-to-callable proof on disposable data, never native cleanup."""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]

EXAMPLE = r'''"""Synthetic POSIX demonstration only; creates/moves/restores its own temp files.

Usage: python -B temporary_example.py /path/to/Claude-Guardian-eighteenth
No real application paths or user cleanup permission are accepted as arguments.
The fake host/approval callbacks are suitable ONLY for this exclusive fixture.
"""
import hashlib
import json
import os
from pathlib import Path
import sys
import tempfile


def main(tree):
    if os.name != 'posix':
        print(json.dumps({'status': 'unsupported', 'scope': 'POSIX temporary fixture'}))
        return
    import importlib.util
    before = list(sys.path)
    def load(name):
        spec = importlib.util.spec_from_file_location('detached_' + name, Path(tree) / 'scripts' / (name + '.py'))
        module = importlib.util.module_from_spec(spec)
        sys.modules[spec.name] = module
        spec.loader.exec_module(module)
        return module
    c, f = load('cleanup_transactions'), load('interview_flow')
    assert sys.path == before
    assert 'yaml' not in sys.modules
    target = 'synthetic-cleanup-target'
    state = f.new_state(target, 'synthetic-account')
    state = f.record_fact(state, 'Q-D02', 'full_claude_data_reset', source='synthetic:fixture')
    intent = f.assessment(state)['cleanup']
    assert intent['requested_level'] == 'C5-full-claude-data-reset'
    assert intent['action_authorized'] is False
    with tempfile.TemporaryDirectory(prefix='guardian-c5-example-') as directory:
        base = Path(directory).resolve()
        base.chmod(0o700)
        data = base / 'selected-cli-data'
        data.mkdir(mode=0o700)
        original = {}
        for name in ('history', 'config', 'extensions'):
            path = data / name
            payload = ('synthetic-' + name).encode()
            path.write_bytes(payload)
            path.chmod(0o600)
            original[name] = payload
        protected = base / 'protected-source-and-codex'
        protected.mkdir(mode=0o700)
        (protected / 'keep').write_bytes(b'synthetic-protected')
        (protected / 'keep').chmod(0o600)
        quarantine = base / 'private-quarantine'
        quarantine.mkdir(mode=0o700)
        roots = [{'root_ref': 'selected-cli', 'path': str(data), 'data_kind': 'cli_app_data'}]
        # A synthetic, independently retained backup, outside selected scope.
        backup = base / 'verified-backup'
        backup.mkdir(mode=0o700)
        for name, payload in original.items():
            (backup / name).write_bytes(payload)
            (backup / name).chmod(0o600)
            assert (backup / name).read_bytes() == payload
        protection = [str(protected), str(backup)]
        scope = {'roots': roots, 'protected_paths': protection,
                 'quarantine_directory': str(quarantine), 'target_ref': target,
                 'mode': 'C5-full-local-data'}
        expected_scope = hashlib.sha256(json.dumps(scope, sort_keys=True, separators=(',', ':'), ensure_ascii=True, allow_nan=False).encode()).hexdigest()
        operations = []
        approved = set()

        def host_check(target_ref, scope_digest):
            # The entire fixture was created by this process, contains no app,
            # has no other writers, and remains within this private temp tree.
            assert target_ref == target and scope_digest == expected_scope
            assert base.is_dir() and not base.is_symlink()
            assert protected.is_dir() and backup.is_dir()
            assert (protected / 'keep').read_bytes() == b'synthetic-protected'
            return 'verified_inactive_claude_data'

        def authorize(operation, digest, target_ref):
            operations.append(operation)
            return (operation, digest, target_ref) in approved

        plan = c.plan(roots, protection, str(quarantine), target,
                      mode='C5-full-local-data', host_check=host_check)
        assert data.is_dir()  # planning did not remove it
        # In production, the host must show exact private scope and receive
        # current user approval. Here approval covers only our synthetic data.
        approved.add(('quarantine', plan.digest(), target))
        receipt = c.quarantine(plan, authorize=authorize, host_check=host_check,
                               exclusive_access=True)
        assert receipt.preview()['state'] == 'quarantined'
        assert not data.exists()
        assert ('restore_cleanup', receipt.digest(), target) not in approved
        approved.add(('restore_cleanup', receipt.digest(), target))
        restored = c.restore(receipt, authorize=authorize, host_check=host_check,
                             exclusive_access=True)
        assert restored.preview()['state'] == 'restored'
        for name, payload in original.items():
            assert (data / name).read_bytes() == payload
            assert (backup / name).read_bytes() == payload
        assert (protected / 'keep').read_bytes() == b'synthetic-protected'
        assert set(operations) == {'quarantine', 'restore_cleanup'}
        assert operations[0] == 'quarantine' and operations[-1] == 'restore_cleanup'
        print(json.dumps({'scope': 'synthetic temporary fixture only',
                          'plan': plan.preview(), 'quarantine': receipt.preview(),
                          'restore': restored.preview(), 'protected_unchanged': True,
                          'content_roundtrip': True}, sort_keys=True))


if __name__ == '__main__':
    if len(sys.argv) != 2:
        raise SystemExit('Expected detached fixture installation only')
    main(sys.argv[1])
'''


class CleanupSkillIntegrationTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.temp = tempfile.TemporaryDirectory(prefix='guardian-cleanup-installed-')
        cls.addClassCleanup(cls.temp.cleanup)
        cls.root = Path(cls.temp.name).resolve()
        archive = cls.root / 'release.zip'
        subprocess.run([sys.executable, '-B', str(ROOT / 'tools/package_skill.py'),
                        '--output', str(archive)], check=True, capture_output=True, timeout=30)
        with zipfile.ZipFile(archive) as z:
            cls.members = z.namelist()
            z.extractall(cls.root / 'installed')
        cls.installed = cls.root / 'installed/claude-guardian'
        cls.cwd = cls.root / 'unrelated'
        cls.cwd.mkdir()

    def test_explicit_release_contains_callable_and_private_artifacts_are_absent(self):
        self.assertIn('claude-guardian/scripts/cleanup_transactions.py', self.members)
        self.assertFalse(any('cleanup-eighteenth' in n or 'private-quarantine' in n for n in self.members))
        for name in ('SKILL.md', 'references/incidents-and-integrations.md'):
            self.assertIn('cleanup_transactions', (self.installed / name).read_text(encoding='utf-8'))
        self.assertIn('full_claude_data_reset', (self.installed / 'references/intake.md').read_text(encoding='utf-8'))

    @unittest.skipUnless(os.name == 'posix', 'POSIX fixture only; not Windows cleanup acceptance')
    def test_detached_intent_plan_quarantine_and_independent_restore(self):
        script = self.root / 'fixture.py'
        script.write_text(EXAMPLE, encoding='utf-8')
        p = subprocess.run([sys.executable, '-I', '-S', '-B', str(script), str(self.installed)],
                           cwd=self.cwd, capture_output=True, text=True, timeout=30)
        self.assertEqual(p.returncode, 0, p.stdout + p.stderr)
        result = json.loads(p.stdout)
        self.assertTrue(result['content_roundtrip'])
        self.assertTrue(result['protected_unchanged'])
        self.assertEqual(result['plan']['state'], 'planned')
        self.assertEqual(result['quarantine']['state'], 'quarantined')
        self.assertEqual(result['restore']['state'], 'restored')
        for key in ('plan', 'quarantine', 'restore'):
            self.assertEqual(result[key]['native_acceptance'], 'not_run')
        self.assertNotIn(str(self.root), p.stdout)
        self.assertEqual(list(self.cwd.iterdir()), [])


if __name__ == '__main__':
    unittest.main()
