"""Historical snapshot integrity and explicit isolation from current acceptance."""
from contextlib import contextmanager
import hashlib
import json
from pathlib import Path
import shutil
import tempfile
import unittest
from unittest.mock import patch

import acceptance_runtime_compat as compatibility

ROOT = Path(__file__).resolve().parents[1]
RUNTIME = 'skills/claude-guardian/scripts/interview_flow.py'
MANIFEST = json.loads((ROOT / compatibility.SNAPSHOT_REL / 'manifest.json').read_text(encoding='utf-8'))


@contextmanager
def source_copy():
    """Disposable minimal inputs; never mutate the current checkout."""
    with tempfile.TemporaryDirectory(prefix='guardian-historical-negative-') as temporary:
        copied = Path(temporary)
        shutil.copytree(ROOT / compatibility.SNAPSHOT_REL, copied / compatibility.SNAPSHOT_REL)
        for relative, entry in MANIFEST['sources'].items():
            if entry['origin'] == 'repository':
                target = copied / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(ROOT / relative, target)
        yield copied


class HistoricalSourceFixtureControls(unittest.TestCase):
    def test_exact_sparse_manifest_and_saved_public_source_sizes(self):
        manifest = compatibility.verify_historical_sources(ROOT)
        self.assertEqual(manifest, MANIFEST)
        self.assertEqual(manifest['release_commit'], '95015be0fc70d2a1b143b43aab09e7a7ab7a7565')
        self.assertEqual(manifest['release_tree'], '0fbe23a5fe52dd28706f933e4c9df94c077ae688')
        self.assertEqual(len(manifest['sources']), 64)
        self.assertEqual(manifest['snapshot_files'], 11)
        self.assertEqual(manifest['snapshot_bytes'], 552015)
        self.assertEqual({entry['origin'] for entry in manifest['sources'].values()},
                         {'snapshot', 'repository'})

    def test_every_snapshot_byte_and_inventory_member_is_required(self):
        relatives = ['manifest.json', 'README.md'] + ['source/' + relative
            for relative, entry in MANIFEST['sources'].items() if entry['origin'] == 'snapshot']
        for relative in relatives:
            for operation in ('missing', 'changed'):
                with self.subTest(relative=relative, operation=operation), source_copy() as root:
                    path = root / compatibility.SNAPSHOT_REL / relative
                    if operation == 'missing':
                        path.unlink()
                    else:
                        path.write_bytes(path.read_bytes() + b'\n# extra historical byte\n')
                    with self.assertRaises(AssertionError):
                        compatibility.verify_historical_sources(root)
        for extra in ('unreviewed.txt', 'source/extra.py', 'source/__pycache__/extra.pyc', 'empty-directory'):
            with self.subTest(extra=extra), source_copy() as root:
                path = root / compatibility.SNAPSHOT_REL / extra
                path.parent.mkdir(parents=True, exist_ok=True)
                path.mkdir() if extra == 'empty-directory' else path.write_bytes(b'unreviewed')
                with self.assertRaisesRegex(AssertionError, 'inventory changed'):
                    compatibility.verify_historical_sources(root)

    def test_all_repository_origin_members_fail_closed_on_drift(self):
        for relative, entry in MANIFEST['sources'].items():
            if entry['origin'] != 'repository':
                continue
            with self.subTest(relative=relative), source_copy() as root:
                path = root / relative
                path.write_bytes(path.read_bytes() + b'\n')
                with self.assertRaisesRegex(AssertionError, 'repository source drift'):
                    compatibility.verify_historical_sources(root)

    def test_missing_snapshot_never_falls_back_to_repository_source(self):
        with source_copy() as root:
            snapshot = root / compatibility.SNAPSHOT_REL / 'source' / RUNTIME
            target = root / RUNTIME
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(snapshot.read_bytes())
            snapshot.unlink()
            with self.assertRaisesRegex(AssertionError, 'inventory changed'):
                compatibility.verify_historical_sources(root)

    def test_modified_manifest_is_rejected_before_verifier_execution(self):
        with source_copy() as root:
            manifest = root / compatibility.SNAPSHOT_REL / 'manifest.json'
            manifest.write_bytes(manifest.read_bytes() + b'\n')
            with patch.object(compatibility, '_load_pinned_verifier') as execute:
                with self.assertRaisesRegex(AssertionError, 'Unreviewed historical source manifest'):
                    with compatibility.historical_baseline(root):
                        self.fail('Unreviewed historical root must never be yielded')
                execute.assert_not_called()

    def test_relative_path_guard_rejects_traversal_aliases_and_absolute_paths(self):
        for relative in ('', '.', '../outside', '/absolute', 'a/../outside', 'a//b',
                         './source', 'a\\b', 'C:/source', 1, None):
            with self.subTest(relative=relative), self.assertRaisesRegex(AssertionError, 'Unsafe historical'):
                compatibility._safe_path(ROOT, relative)

    def test_symlink_detection_in_snapshot_and_repository_ancestors_is_fail_closed(self):
        # Deterministic filesystem-status simulation also runs where Windows
        # does not grant creation of symlinks. This is not a native symlink claim.
        original = Path.is_symlink
        targets = [ROOT / compatibility.SNAPSHOT_REL / 'source',
                   ROOT / 'skills/claude-guardian/references',
                   ROOT / compatibility.SNAPSHOT_REL / 'source' / RUNTIME,
                   ROOT]
        for target in targets:
            with self.subTest(target=target.relative_to(ROOT) if target != ROOT else '.'):
                def is_link(path):
                    return path == target or original(path)
                with patch.object(Path, 'is_symlink', is_link):
                    with self.assertRaisesRegex(AssertionError, 'symlink'):
                        compatibility.verify_historical_sources(ROOT)

    def test_real_historical_root_is_not_current_and_original_bridge_stays_strict(self):
        with compatibility.historical_baseline(ROOT) as historical:
            bridge = compatibility.load(historical)
            self.assertNotEqual(historical, ROOT)
            self.assertFalse(historical.is_symlink())
            self.assertEqual(bridge.digest(historical / RUNTIME), bridge.AFTER)
            self.assertNotEqual(bridge.digest(ROOT / RUNTIME), bridge.AFTER)
            self.assertEqual((historical / RUNTIME).read_bytes(),
                             (ROOT / compatibility.SNAPSHOT_REL / 'source' / RUNTIME).read_bytes())
            self.assertEqual({path.relative_to(historical).as_posix()
                              for path in historical.rglob('*') if path.is_symlink()}, set())
            with self.assertRaisesRegex(AssertionError, 'Unreviewed current runtime'):
                compatibility.load(ROOT)
            with bridge.historical_source_view(historical, compatibility.EXPECTED_MANIFEST) as before:
                self.assertEqual(bridge.digest(before / RUNTIME), bridge.BEFORE)

    def test_every_copied_source_has_exact_recorded_bytes(self):
        with compatibility.historical_baseline(ROOT) as historical:
            for relative, entry in MANIFEST['sources'].items():
                with self.subTest(relative=relative):
                    raw = (historical / relative).read_bytes()
                    self.assertEqual(len(raw), entry['size_bytes'])
                    self.assertEqual(hashlib.sha256(raw).hexdigest(), entry['sha256'])


if __name__ == '__main__':
    unittest.main()
