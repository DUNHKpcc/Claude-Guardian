"""Independent C5 core checks using exclusively owned temporary data.

These tests move synthetic local fixtures only. They do not approve cleanup of
real application data, certify a native host adapter, start applications, or
claim account, network, keychain, browser, or Windows behavior.
"""
import copy
import errno
import json
import math
import os
from pathlib import Path
import re
import stat
import subprocess
import sys
import tempfile
from types import SimpleNamespace
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import cleanup_transactions as cleanup

TARGET = 'synthetic-cleanup-device'
SECRET = 'synthetic-PRIVATE-cleanup-sentinel'


@unittest.skipUnless(os.name == 'posix', 'POSIX temporary cleanup core only; no Windows certification')
class CleanupTransactionsTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='guardian-cleanup-tests-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.root.chmod(0o700)
        self.app = self.root / 'explicit-app-data'
        self.app.mkdir(mode=0o700)
        self.nested = self.app / 'nested'
        self.nested.mkdir(mode=0o700)
        self.payload = self.nested / 'private-state'
        self.payload.write_bytes(b'\x00' + SECRET.encode() + b'\xff')
        self.payload.chmod(0o600)
        self.empty = self.app / 'empty'
        self.empty.mkdir(mode=0o700)
        self.second = self.root / 'explicit-cli-data'
        self.second.write_bytes(b'second-private-synthetic-payload')
        self.second.chmod(0o600)
        self.protected = self.root / 'protected-project'
        self.protected.mkdir(mode=0o700)
        self.protected_file = self.protected / 'keep'
        self.protected_file.write_bytes(b'protected-synthetic-state')
        self.protected_file.chmod(0o600)
        self.quarantine_dir = self.root / 'private-quarantine'
        self.quarantine_dir.mkdir(mode=0o700)
        self.roots = [
            {'root_ref': 'desktop-data', 'path': str(self.app), 'data_kind': 'desktop_app_data'},
            {'root_ref': 'cli-data', 'path': str(self.second), 'data_kind': 'cli_app_data'},
        ]
        self.before_payload = self.payload.read_bytes()
        self.before_second = self.second.read_bytes()
        self.before_protected = self.protected_file.read_bytes()

    @staticmethod
    def host_ok(target_ref, scope_digest):
        if target_ref != TARGET or not re.fullmatch(r'[0-9a-f]{64}', scope_digest):
            raise AssertionError('Host callback received an invalid binding')
        return cleanup.HOST_OK

    def plan(self, **kwargs):
        values = dict(roots=copy.deepcopy(self.roots),
                      protected_paths=[str(self.protected)],
                      quarantine_directory=str(self.quarantine_dir),
                      target_ref=TARGET, host_check=self.host_ok)
        values.update(kwargs)
        return cleanup.plan(**values)

    def authorizer(self, document, operation, calls=None):
        expected = document.digest()
        def authorize(actual_operation, actual_digest, actual_target):
            if calls is not None:
                calls.append((actual_operation, actual_digest, actual_target))
            return (actual_operation == operation and actual_digest == expected
                    and actual_target == TARGET)
        return authorize

    def quarantine(self, plan=None, **kwargs):
        if plan is None:
            plan = self.plan()
        values = dict(authorize=self.authorizer(plan, 'quarantine'),
                      host_check=self.host_ok, exclusive_access=True)
        values.update(kwargs)
        return cleanup.quarantine(plan, **values)

    def restore(self, receipt, **kwargs):
        values = dict(authorize=self.authorizer(receipt, 'restore_cleanup'),
                      host_check=self.host_ok, exclusive_access=True)
        values.update(kwargs)
        return cleanup.restore(receipt, **values)

    def assert_originals(self):
        self.assertEqual(self.payload.read_bytes(), self.before_payload)
        self.assertTrue(self.empty.is_dir())
        self.assertEqual(self.second.read_bytes(), self.before_second)
        self.assert_protected()

    def assert_protected(self):
        self.assertEqual(self.protected_file.read_bytes(), self.before_protected)
        self.assertEqual(stat.S_IMODE(self.protected.stat().st_mode), 0o700)
        self.assertEqual(stat.S_IMODE(self.protected_file.stat().st_mode), 0o600)

    def assert_private_error(self, operation):
        with self.assertRaises(cleanup.CleanupError) as caught:
            operation()
        error = caught.exception
        self.assertRegex(error.code, r'^[A-Z][A-Z0-9_]*$')
        for forbidden in (str(self.root), SECRET, self.before_second.decode()):
            self.assertNotIn(forbidden, str(error))
            self.assertNotIn(forbidden, repr(error))
        return error

    def assert_plan_rejected(self, **kwargs):
        result = self.assert_private_error(lambda: self.plan(**kwargs))
        self.assert_protected()
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])
        return result

    def test_constants_and_explicit_high_impact_mode(self):
        self.assertEqual(cleanup.MODE, 'C5-full-local-data')
        self.assertEqual(cleanup.HOST_OK, 'verified_inactive_claude_data')
        for mode in ('C0-audit', 'C1-cache', 'C2-desktop-reset', 'C3-cli-login-reset',
                     'C4-browser-site-reset', 'everything', '', None, True):
            with self.subTest(mode=mode):
                self.assert_plan_rejected(mode=mode)

    def test_plan_is_read_only_bounded_private_and_detached(self):
        before = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        plan = self.plan()
        after = sorted(str(p.relative_to(self.root)) for p in self.root.rglob('*'))
        self.assertEqual(before, after)
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])
        self.assert_originals()
        self.assertRegex(plan.digest(), r'^[0-9a-f]{64}$')
        material = plan.private_material()
        self.assertIsInstance(material, dict)
        old_digest = plan.digest()
        material.clear()
        self.assertEqual(plan.digest(), old_digest)
        self.assertTrue(plan.private_material())
        public = json.dumps(plan.preview(), sort_keys=True) + repr(plan) + str(plan)
        for forbidden in (str(self.root), str(self.app), SECRET):
            self.assertNotIn(forbidden, public)

    def test_roots_and_protection_inputs_are_copied(self):
        roots = copy.deepcopy(self.roots)
        protected = [str(self.protected)]
        plan = self.plan(roots=roots, protected_paths=protected)
        digest = plan.digest()
        roots[0]['path'] = str(self.protected)
        roots.clear()
        protected.clear()
        self.assertEqual(plan.digest(), digest)
        receipt = self.quarantine(plan)
        self.assertFalse(self.app.exists())
        self.assert_protected()
        self.restore(receipt)
        self.assert_originals()

    def test_real_directory_and_file_roundtrip_preserves_bytes_and_modes(self):
        before_mode = {str(p.relative_to(self.app)): stat.S_IMODE(p.stat().st_mode)
                       for p in (self.app, self.nested, self.payload, self.empty)}
        plan = self.plan()
        calls = []
        receipt = self.quarantine(plan, authorize=self.authorizer(plan, 'quarantine', calls))
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.assert_protected()
        self.assertGreaterEqual(len(calls), len(self.roots))
        self.assertTrue(all(c == ('quarantine', plan.digest(), TARGET) for c in calls))
        self.assertRegex(receipt.digest(), r'^[0-9a-f]{64}$')
        public = json.dumps(receipt.preview(), sort_keys=True) + repr(receipt) + str(receipt)
        for forbidden in (str(self.root), SECRET, self.before_second.decode()):
            self.assertNotIn(forbidden, public)
        calls = []
        restored = self.restore(receipt, authorize=self.authorizer(receipt, 'restore_cleanup', calls))
        self.assert_originals()
        self.assertGreaterEqual(len(calls), len(self.roots))
        self.assertTrue(all(c == ('restore_cleanup', receipt.digest(), TARGET) for c in calls))
        for relative, mode in before_mode.items():
            self.assertEqual(stat.S_IMODE((self.app / relative).stat().st_mode), mode)
        self.assertEqual(stat.S_IMODE(self.second.stat().st_mode), 0o600)
        self.assertRegex(restored.digest(), r'^[0-9a-f]{64}$')
        self.assertTrue(list(self.quarantine_dir.iterdir()), 'Recovery records must not be purged')

    def test_desktop_only_does_not_invent_cli_data(self):
        self.second.unlink()
        receipt = self.quarantine(self.plan(roots=self.roots[:1]))
        self.assertFalse(self.second.exists())
        self.restore(receipt)
        self.assertFalse(self.second.exists())
        self.assertEqual(self.payload.read_bytes(), self.before_payload)
        self.assert_protected()

    def test_empty_directory_is_recoverable(self):
        empty_root = self.root / 'only-empty-data'
        empty_root.mkdir(mode=0o700)
        plan = self.plan(roots=[{'root_ref': 'empty-data', 'path': str(empty_root),
                                'data_kind': 'desktop_app_data'}])
        receipt = self.quarantine(plan)
        self.assertFalse(empty_root.exists())
        self.restore(receipt)
        self.assertTrue(empty_root.is_dir())
        self.assertEqual(list(empty_root.iterdir()), [])

    def test_no_authorization_or_exclusive_access_cannot_move(self):
        plan = self.plan()
        for kwargs in ({'authorize': None}, {'exclusive_access': False},
                       {'exclusive_access': 1}, {'exclusive_access': 'yes'}):
            with self.subTest(kwargs=kwargs):
                self.assert_private_error(lambda: self.quarantine(plan, **kwargs))
                self.assert_originals()

    def test_authorization_requires_literal_true(self):
        plan = self.plan()
        for result in (False, None, 1, 'yes', {}, [True]):
            with self.subTest(result=result):
                self.assert_private_error(lambda: self.quarantine(plan, authorize=lambda *args: result))
                self.assert_originals()

    def test_authorizer_exception_is_redacted(self):
        def broken(*args):
            raise RuntimeError(SECRET + str(self.root))
        self.assert_private_error(lambda: self.quarantine(authorize=broken))
        self.assert_originals()

    def test_plan_requires_fresh_trusted_host_check(self):
        for host_check in (None, lambda *args: True, lambda *args: 1,
                           lambda *args: None, lambda *args: 'unverified'):
            with self.subTest(host_check=host_check):
                self.assert_plan_rejected(host_check=host_check)

    def test_all_host_denial_scopes_reject_without_writes(self):
        for status in ('active_host', 'unknown_ownership', 'shared_scope',
                       'credential_scope', 'browser_data_scope', 'unverified'):
            with self.subTest(status=status):
                self.assert_plan_rejected(host_check=lambda *args: status)
                plan = self.plan()
                self.assert_private_error(lambda: self.quarantine(plan, host_check=lambda *args: status))
                self.assert_originals()

    def test_host_check_exception_is_redacted(self):
        def broken(*args):
            raise RuntimeError(SECRET + str(self.root))
        self.assert_plan_rejected(host_check=broken)
        self.assert_private_error(lambda: self.quarantine(host_check=broken))
        self.assert_originals()

    def test_host_check_is_not_replaced_by_authorization(self):
        plan = self.plan()
        self.assert_private_error(lambda: self.quarantine(plan, host_check=None))
        self.assert_originals()
        receipt = self.quarantine(plan)
        self.assert_private_error(lambda: self.restore(receipt, host_check=None))
        self.assertFalse(self.app.exists())
        self.restore(receipt)
        self.assert_originals()

    def test_invalid_root_declarations_are_rejected(self):
        first = copy.deepcopy(self.roots[0])
        cases = ([], None, {}, [str(self.app)], [dict(first, data_kind='browser_data')],
                 [dict(first, data_kind='credentials')], [dict(first, data_kind='project')],
                 [dict(first, extra='unverified')], [{k: v for k, v in first.items() if k != 'root_ref'}],
                 [dict(first, root_ref='')], [dict(first, root_ref=None)],
                 [dict(first, path=str(self.root / 'missing'))])
        for roots in cases:
            with self.subTest(roots=roots):
                self.assert_plan_rejected(roots=roots)

    def test_duplicate_or_nested_roots_are_rejected(self):
        child = dict(self.roots[0], root_ref='nested-data', path=str(self.nested))
        for roots in (self.roots + [self.roots[0]], [self.roots[0], child],
                      [self.roots[0], dict(self.roots[1], root_ref='desktop-data')]):
            with self.subTest(roots=roots):
                self.assert_plan_rejected(roots=roots)

    def test_protected_paths_are_required_and_cannot_overlap(self):
        for protected in ([], None, str(self.protected), [str(self.app)], [str(self.payload)],
                          [str(self.root)], [str(self.second)]):
            with self.subTest(protected=protected):
                self.assert_plan_rejected(protected_paths=protected)
        # Lexical shared prefixes are not path ancestry.
        sibling = self.root / 'explicit-app-data-project'
        sibling.mkdir(mode=0o700)
        self.plan(protected_paths=[str(sibling)])

    def test_protected_aliases_into_selected_data_are_rejected(self):
        alias = self.root / 'protected-source-alias'
        alias.symlink_to(self.app, target_is_directory=True)
        self.assert_plan_rejected(protected_paths=[str(alias)])
        parent_alias = self.root / 'protected-parent-alias'
        parent_alias.symlink_to(self.root, target_is_directory=True)
        self.assert_plan_rejected(protected_paths=[str(parent_alias / self.app.name)])
        self.assert_originals()

    def test_quarantine_must_not_overlap_sources_or_protection(self):
        inside = self.app / 'quarantine'
        inside.mkdir(mode=0o700)
        for destination in (self.root, self.app, inside, self.protected, self.nested):
            with self.subTest(destination=destination):
                self.assert_plan_rejected(quarantine_directory=str(destination))

    def test_paths_are_explicit_canonical_and_never_expanded(self):
        bad_paths = ('relative-data', '~/data', '$HOME/data', str(self.app) + '/',
                     str(self.root) + '/./explicit-app-data',
                     str(self.root) + '/nested/../explicit-app-data',
                     str(self.root) + '/*', str(self.app) + '\x00private', '/')
        for value in bad_paths:
            with self.subTest(value=value):
                roots = [dict(self.roots[0], path=value)]
                self.assert_plan_rejected(roots=roots)

    def test_source_root_symlink_is_rejected(self):
        alias = self.root / 'source-alias'
        alias.symlink_to(self.app, target_is_directory=True)
        self.assert_plan_rejected(roots=[dict(self.roots[0], path=str(alias))])
        self.assert_originals()

    def test_source_ancestor_symlink_is_rejected(self):
        alias = self.root / 'parent-alias'
        alias.symlink_to(self.root, target_is_directory=True)
        self.assert_plan_rejected(roots=[dict(self.roots[0], path=str(alias / self.app.name))])
        self.assert_originals()

    def test_nested_symlink_is_rejected_without_following_it(self):
        (self.app / 'linked-protected').symlink_to(self.protected, target_is_directory=True)
        self.assert_plan_rejected()
        self.assert_originals()

    def test_quarantine_symlink_and_ancestor_symlink_are_rejected(self):
        alias = self.root / 'quarantine-alias'
        alias.symlink_to(self.quarantine_dir, target_is_directory=True)
        self.assert_plan_rejected(quarantine_directory=str(alias))
        parent_alias = self.root / 'quarantine-parent-alias'
        parent_alias.symlink_to(self.root, target_is_directory=True)
        self.assert_plan_rejected(quarantine_directory=str(parent_alias / self.quarantine_dir.name))

    def test_root_and_nested_hardlinks_are_rejected(self):
        external = self.root / 'hardlink-neighbor'
        os.link(self.payload, external)
        self.assert_plan_rejected()
        external.unlink()
        os.link(self.second, external)
        self.assert_plan_rejected()
        self.assert_originals()

    @unittest.skipUnless(hasattr(os, 'mkfifo'), 'FIFO fixture unavailable')
    def test_special_file_is_rejected_without_reading(self):
        os.mkfifo(self.app / 'fifo', 0o600)
        self.assert_plan_rejected()

    def test_group_or_world_writable_source_parents_are_rejected(self):
        for path in (self.app, self.nested, self.root):
            for mode in (0o720, 0o702, 0o777):
                with self.subTest(path=path.name, mode=mode):
                    old_mode = stat.S_IMODE(path.stat().st_mode)
                    path.chmod(mode)
                    try:
                        self.assert_plan_rejected()
                    finally:
                        path.chmod(old_mode)

    def test_quarantine_must_be_private_existing_directory(self):
        for mode in (0o755, 0o750, 0o770, 0o777):
            with self.subTest(mode=mode):
                self.quarantine_dir.chmod(mode)
                try:
                    self.assert_plan_rejected()
                finally:
                    self.quarantine_dir.chmod(0o700)
        self.assert_plan_rejected(quarantine_directory=str(self.root / 'not-created'))
        self.assert_plan_rejected(quarantine_directory=str(self.second))

    def test_special_mode_is_rejected(self):
        self.payload.chmod(0o4600)
        try:
            self.assert_plan_rejected()
        finally:
            self.payload.chmod(0o600)

    @unittest.skipUnless(hasattr(os, 'setxattr'), 'Extended attributes unavailable')
    def test_xattrs_are_rejected_instead_of_silently_lost(self):
        try:
            os.setxattr(self.payload, 'user.guardian-test', b'synthetic')
        except OSError as error:
            self.skipTest('Temporary filesystem does not permit user xattrs: ' + str(error.errno))
        self.assert_plan_rejected()

    def test_source_same_size_content_drift_blocks_all_moves(self):
        plan = self.plan()
        changed = b'X' * len(self.before_payload)
        self.payload.write_bytes(changed)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(self.payload.read_bytes(), changed)
        self.assertEqual(self.second.read_bytes(), self.before_second)
        self.assert_protected()

    def test_source_inode_replacement_with_same_bytes_is_stale(self):
        plan = self.plan()
        replacement = self.app / 'replacement'
        replacement.write_bytes(self.before_payload)
        replacement.chmod(0o600)
        os.replace(replacement, self.payload)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assert_originals()

    def test_source_tree_addition_and_removal_are_stale(self):
        plan = self.plan()
        addition = self.app / 'later-data'
        addition.write_bytes(b'new-synthetic-data')
        addition.chmod(0o600)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assertTrue(addition.exists())
        self.assert_originals()
        addition.unlink()
        plan = self.plan()
        self.empty.rmdir()
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(self.payload.read_bytes(), self.before_payload)
        self.assertEqual(self.second.read_bytes(), self.before_second)

    def test_source_permissions_drift_blocks_move(self):
        plan = self.plan()
        self.payload.chmod(0o640)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assert_originals()

    def test_source_swap_to_symlink_after_plan_is_rejected(self):
        plan = self.plan()
        original = self.root / 'detached-original'
        self.app.rename(original)
        self.app.symlink_to(self.protected, target_is_directory=True)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual((original / 'nested/private-state').read_bytes(), self.before_payload)
        self.assertEqual(self.second.read_bytes(), self.before_second)
        self.assert_protected()

    def test_callback_drift_immediately_before_move_is_rejected(self):
        plan = self.plan()
        changed = False
        def authorize(*args):
            nonlocal changed
            if not changed:
                self.payload.write_bytes(b'Z' * len(self.before_payload))
                changed = True
            return True
        self.assert_private_error(lambda: self.quarantine(plan, authorize=authorize))
        self.assertEqual(self.payload.read_bytes(), b'Z' * len(self.before_payload))
        self.assertEqual(self.second.read_bytes(), self.before_second)
        self.assert_protected()

    def test_immediate_cancellation_has_no_effect(self):
        self.assert_plan_rejected(cancelled=lambda: True)
        plan = self.plan()
        self.assert_private_error(lambda: self.quarantine(plan, cancelled=lambda: True))
        self.assert_originals()

    def test_cancellation_callback_exception_is_private(self):
        def broken():
            raise RuntimeError(SECRET + str(self.root))
        self.assert_plan_rejected(cancelled=broken)
        self.assert_private_error(lambda: self.quarantine(cancelled=broken))
        self.assert_originals()

    def test_invalid_deadline_bounds_are_rejected(self):
        for seconds in (0, -1, True, None, '30', math.nan, math.inf, -math.inf, 10**1000):
            with self.subTest(seconds=type(seconds).__name__):
                self.assert_plan_rejected(max_seconds=seconds)
                plan = self.plan()
                self.assert_private_error(lambda: self.quarantine(plan, max_seconds=seconds))
                self.assert_originals()

    def test_expired_runtime_budget_stops_before_writing(self):
        self.assert_plan_rejected(max_seconds=1e-30)
        plan = self.plan()
        self.assert_private_error(lambda: self.quarantine(plan, max_seconds=1e-30))
        self.assert_originals()
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])

    def test_more_than_sixteen_roots_are_rejected(self):
        roots = []
        for index in range(17):
            path = self.root / ('bounded-root-' + str(index))
            path.write_bytes(b'x')
            path.chmod(0o600)
            roots.append({'root_ref': 'bounded-' + str(index), 'path': str(path),
                          'data_kind': 'desktop_app_data'})
        self.assert_plan_rejected(roots=roots)

    def test_depth_budget_is_enforced(self):
        directory = self.app
        for index in range(34):
            directory = directory / ('d' + str(index))
            directory.mkdir(mode=0o700)
        (directory / 'leaf').write_bytes(b'x')
        self.assert_plan_rejected()

    def test_total_byte_budget_is_enforced_without_reading_oversized_file(self):
        large = self.app / 'oversized-sparse-file'
        with large.open('wb') as stream:
            stream.truncate(64 * 1024 * 1024 + 1)
        large.chmod(0o600)
        self.assert_plan_rejected()

    def test_root_entry_budget_is_enforced(self):
        for index in range(4097):
            (self.app / ('entry-' + str(index))).mkdir(mode=0o700)
        self.assert_plan_rejected()

    def test_partial_cancellation_reports_truth_and_is_recoverable(self):
        plan = self.plan()
        def cancelled():
            return not self.app.exists() or not self.second.exists()
        error = self.assert_private_error(lambda: self.quarantine(plan, cancelled=cancelled))
        self.assertIsNotNone(error.recovery_id)
        self.assertEqual(error.moved_count, 1)
        self.assertEqual(sum(path.exists() for path in (self.app, self.second)), 1)
        self.assert_protected()
        receipt = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.assertEqual(sum(path.exists() for path in (self.app, self.second)), 1)
        self.restore(receipt)
        self.assert_originals()

    def test_per_root_host_recheck_stops_after_first_move(self):
        plan = self.plan()
        def inactive_until_move(*args):
            return cleanup.HOST_OK if self.app.exists() and self.second.exists() else 'active_host'
        error = self.assert_private_error(lambda: self.quarantine(plan, host_check=inactive_until_move))
        self.assertEqual(error.moved_count, 1)
        receipt = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.restore(receipt)
        self.assert_originals()

    def test_per_root_authorization_recheck_stops_after_first_move(self):
        plan = self.plan()
        def approve_until_move(*args):
            return self.app.exists() and self.second.exists()
        error = self.assert_private_error(lambda: self.quarantine(plan, authorize=approve_until_move))
        self.assertEqual(error.moved_count, 1)
        receipt = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.restore(receipt)
        self.assert_originals()

    def test_private_manifest_and_journals_are_retained_with_restricted_modes(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        batch = self.quarantine_dir / plan.private_material()['action_id']
        self.assertEqual(receipt.recovery_id, batch.name)
        self.assertEqual(stat.S_IMODE(batch.stat().st_mode), 0o700)
        manifest = batch / 'manifest.json'
        document = json.loads(manifest.read_text(encoding='utf-8'))
        self.assertEqual(set(document), {'schema_version', 'plan', 'batch_identity'})
        self.assertEqual(document['schema_version'], 'guardian-cleanup-batch/0.1')
        self.assertEqual(document['plan'], plan.private_material())
        self.assertEqual(document['batch_identity'], [batch.stat().st_dev, batch.stat().st_ino])
        for index in range(len(self.roots)):
            self.assertTrue((batch / ('move-%04d.prepared.json' % index)).is_file())
            self.assertTrue((batch / ('move-%04d.done.json' % index)).is_file())
        records = list(batch.glob('*.json'))
        self.assertTrue(records)
        for record in records:
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)
        self.restore(receipt)
        self.assert_originals()
        for record in records:
            self.assertTrue(record.exists(), 'Recovery history must not be silently removed')
        prepared = list(batch.glob('restore-*.prepared.json'))
        self.assertGreaterEqual(len(prepared), len(self.roots))
        for record in prepared:
            self.assertEqual(stat.S_IMODE(record.stat().st_mode), 0o600)

    def test_restore_requires_separate_bound_approval(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        for authorize in (None, self.authorizer(plan, 'quarantine'), lambda *args: False,
                          lambda *args: 1, lambda *args: 'yes'):
            with self.subTest(authorize=authorize):
                self.assert_private_error(lambda: self.restore(receipt, authorize=authorize))
                self.assertFalse(self.app.exists())
                self.assertFalse(self.second.exists())
                self.assert_protected()
        self.restore(receipt)
        self.assert_originals()

    def test_restore_requires_live_host_and_exclusive_access(self):
        receipt = self.quarantine()
        for kwargs in ({'host_check': lambda *args: 'active_host'},
                       {'host_check': lambda *args: 'unverified'},
                       {'exclusive_access': False}, {'exclusive_access': 1}):
            with self.subTest(kwargs=kwargs):
                self.assert_private_error(lambda: self.restore(receipt, **kwargs))
                self.assertFalse(self.app.exists())
                self.assertFalse(self.second.exists())
        self.restore(receipt)
        self.assert_originals()

    def test_restore_never_overwrites_later_data(self):
        receipt = self.quarantine()
        self.app.mkdir(mode=0o700)
        later = self.app / 'new-user-data'
        later.write_bytes(b'later-synthetic-state')
        later.chmod(0o600)
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertEqual(later.read_bytes(), b'later-synthetic-state')
        self.assertFalse(self.payload.exists())
        self.assert_protected()

    def test_restore_never_overwrites_later_empty_directory_or_symlink(self):
        receipt = self.quarantine()
        self.app.symlink_to(self.protected, target_is_directory=True)
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertTrue(self.app.is_symlink())
        self.assert_protected()
        self.app.unlink()
        self.app.mkdir(mode=0o700)
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertEqual(list(self.app.iterdir()), [])
        self.assert_protected()

    def test_restore_never_overwrites_later_file(self):
        receipt = self.quarantine()
        self.second.write_bytes(b'later-file-state')
        self.second.chmod(0o600)
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertEqual(self.second.read_bytes(), b'later-file-state')
        self.assert_protected()

    def test_repeat_restore_does_not_overwrite_restored_data(self):
        receipt = self.quarantine()
        self.restore(receipt)
        changed = b'changed-after-restoration'
        self.payload.write_bytes(changed)
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertEqual(self.payload.read_bytes(), changed)
        self.assertEqual(self.second.read_bytes(), self.before_second)
        self.assert_protected()

    def test_restore_cancellation_preserves_recoverable_payload(self):
        receipt = self.quarantine()
        self.assert_private_error(lambda: self.restore(receipt, cancelled=lambda: True))
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.restore(receipt)
        self.assert_originals()

    def test_loader_rejects_bad_digest_target_and_non_manifest(self):
        path = self.root / 'untrusted-manifest.json'
        path.write_text('{}', encoding='utf-8')
        path.chmod(0o600)
        for digest, target in (('0' * 64, TARGET), ('bad-digest', TARGET),
                               ('0' * 64, 'different-device')):
            with self.subTest(digest=digest, target=target):
                self.assert_private_error(lambda: cleanup.load_manifest(str(path), digest, target))
        self.assert_originals()

    def test_loader_rejects_symlink_and_public_file(self):
        path = self.root / 'untrusted-manifest.json'
        path.write_text('{}', encoding='utf-8')
        path.chmod(0o644)
        self.assert_private_error(lambda: cleanup.load_manifest(str(path), '0' * 64, TARGET))
        alias = self.root / 'manifest-alias'
        alias.symlink_to(path)
        self.assert_private_error(lambda: cleanup.load_manifest(str(alias), '0' * 64, TARGET))
        self.assert_originals()

    def test_independent_manifest_load_and_reconcile_restore(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = self.quarantine_dir / receipt.recovery_id / 'manifest.json'
        loaded = cleanup.load_manifest(str(manifest), plan.digest(), TARGET)
        self.assertEqual(loaded.digest(), plan.digest())
        self.assertEqual(loaded.private_material(), plan.private_material())
        observed = cleanup.reconcile(loaded, receipt.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['state'], 'quarantined')
        self.assertEqual(observed.preview()['quarantined_count'], 2)
        self.restore(observed)
        self.assert_originals()
        final = cleanup.reconcile(loaded, receipt.recovery_id, host_check=self.host_ok)
        self.assertEqual(final.preview()['state'], 'restored')
        self.assertEqual(final.preview()['quarantined_count'], 0)

    def test_expired_plan_cannot_start_but_does_not_block_recovery(self):
        plan = self.plan()
        future = plan.private_material()['expires_at'] + 10
        with patch.object(cleanup.time, 'time', return_value=future):
            self.assert_private_error(lambda: self.quarantine(plan))
        self.assert_originals()
        receipt = self.quarantine(plan)
        manifest = self.quarantine_dir / receipt.recovery_id / 'manifest.json'
        with patch.object(cleanup.time, 'time', return_value=future):
            loaded = cleanup.load_manifest(str(manifest), plan.digest(), TARGET)
            observed = cleanup.reconcile(loaded, receipt.recovery_id, host_check=self.host_ok)
            self.restore(observed)
        self.assert_originals()

    def test_loader_binds_exact_digest_target_and_private_location(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = self.quarantine_dir / receipt.recovery_id / 'manifest.json'
        for digest, target in (('0' * 64, TARGET), (plan.digest(), 'different-device')):
            with self.subTest(digest=digest, target=target):
                self.assert_private_error(lambda: cleanup.load_manifest(str(manifest), digest, target))
        manifest.chmod(0o644)
        self.assert_private_error(lambda: cleanup.load_manifest(str(manifest), plan.digest(), TARGET))
        manifest.chmod(0o600)
        copied = self.root / 'copied-private-batch'
        copied.mkdir(mode=0o700)
        copy_manifest = copied / 'manifest.json'
        copy_manifest.write_bytes(manifest.read_bytes())
        copy_manifest.chmod(0o600)
        self.assert_private_error(lambda: cleanup.load_manifest(str(copy_manifest), plan.digest(), TARGET))
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.assert_protected()

    def test_manifest_tampering_never_grants_restore_or_reconcile(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = self.quarantine_dir / receipt.recovery_id / 'manifest.json'
        envelope = json.loads(manifest.read_text(encoding='utf-8'))
        envelope['plan']['target_ref'] = 'tampered-target'
        manifest.write_text(json.dumps(envelope), encoding='utf-8')
        self.assert_private_error(lambda: cleanup.load_manifest(str(manifest), plan.digest(), TARGET))
        self.assert_private_error(lambda: cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok))
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.assert_protected()

    def test_duplicate_manifest_keys_and_excessive_document_are_rejected(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = self.quarantine_dir / receipt.recovery_id / 'manifest.json'
        original = manifest.read_bytes()
        for raw in (b'{"schema_version":"one","schema_version":"two"}',
                    b'{"value":NaN}', b'[' * 1000 + b']' * 1000,
                    b' ' * (8 * 1024 * 1024 + 1)):
            with self.subTest(length=len(raw)):
                manifest.write_bytes(raw)
                self.assert_private_error(lambda: cleanup.load_manifest(str(manifest), plan.digest(), TARGET))
        manifest.write_bytes(original)
        # A loaded plan can make a fresh observation after manifest metadata changes.
        loaded = cleanup.load_manifest(str(manifest), plan.digest(), TARGET)
        observed = cleanup.reconcile(loaded, receipt.recovery_id, host_check=self.host_ok)
        self.restore(observed)
        self.assert_originals()

    def test_same_size_quarantine_corruption_blocks_restore(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        stored = self.quarantine_dir / receipt.recovery_id / 'root-0000' / 'nested/private-state'
        changed = b'Q' * len(self.before_payload)
        stored.write_bytes(changed)
        self.assert_private_error(lambda: cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok))
        self.assert_private_error(lambda: self.restore(receipt))
        self.assertEqual(stored.read_bytes(), changed)
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.assert_protected()

    def test_reconcile_rejects_both_and_neither_locations(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        self.second.write_bytes(self.before_second)
        self.second.chmod(0o600)
        self.assert_private_error(lambda: cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok))
        self.second.unlink()
        batch = self.quarantine_dir / receipt.recovery_id
        (batch / 'root-0001').rename(self.root / 'detached-recovery-data')
        self.assert_private_error(lambda: cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok))
        self.assert_private_error(lambda: self.restore(receipt))
        self.assert_protected()

    def test_receipt_material_copies_and_immutability_preserve_binding(self):
        receipt = self.quarantine()
        before = receipt.digest()
        material = receipt.private_material()
        material['observation']['roots'].clear()
        self.assertEqual(receipt.digest(), before)
        with self.assertRaises(cleanup.CleanupError):
            receipt._blob = b'{}'
        self.assertEqual(receipt.digest(), before)
        self.restore(receipt)
        self.assert_originals()

    def test_pre_move_journal_exists_before_each_actual_rename(self):
        plan = self.plan()
        batch = self.quarantine_dir / plan.private_material()['action_id']
        original_rename = cleanup.os.rename
        moves = []
        def checked_rename(source, destination, **kwargs):
            if str(destination).startswith('root-'):
                index = int(str(destination).split('-')[-1])
                prepared = batch / ('move-%04d.prepared.json' % index)
                self.assertTrue((batch / 'manifest.json').is_file())
                self.assertTrue(prepared.is_file())
                step = json.loads(prepared.read_text(encoding='utf-8'))
                self.assertEqual(step['operation'], 'quarantine')
                self.assertEqual(step['plan_digest'], plan.digest())
                self.assertEqual(step['index'], index)
                self.assertEqual(stat.S_IMODE(prepared.stat().st_mode), 0o600)
                self.assertFalse((batch / ('move-%04d.done.json' % index)).exists())
                moves.append(index)
            return original_rename(source, destination, **kwargs)
        with patch.object(cleanup.os, 'rename', side_effect=checked_rename):
            receipt = self.quarantine(plan)
        self.assertEqual(moves, [0, 1])
        self.restore(receipt)
        self.assert_originals()

    def test_prepared_journal_failure_leaves_every_source_untouched(self):
        plan = self.plan()
        original_write = cleanup.tx._write
        def failed_write(fd, name, *args, **kwargs):
            if name == 'move-0000.prepared.json':
                raise OSError(errno.ENOSPC, SECRET + str(self.root))
            return original_write(fd, name, *args, **kwargs)
        with patch.object(cleanup.tx, '_write', side_effect=failed_write):
            error = self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(error.moved_count, 0)
        self.assert_originals()
        self.assertIsNotNone(error.recovery_id)
        observed = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['quarantined_count'], 0)

    def test_second_move_io_failure_retains_partial_recovery(self):
        plan = self.plan()
        original_rename = cleanup.os.rename
        def fail_second(source, destination, **kwargs):
            if destination == 'root-0001':
                raise OSError(errno.EIO, SECRET + str(self.root))
            return original_rename(source, destination, **kwargs)
        with patch.object(cleanup.os, 'rename', side_effect=fail_second):
            error = self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(error.moved_count, 1)
        self.assertFalse(self.app.exists())
        self.assertEqual(self.second.read_bytes(), self.before_second)
        observed = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['state'], 'partial')
        self.restore(observed)
        self.assert_originals()

    def test_done_journal_failure_does_not_hide_successful_move(self):
        plan = self.plan()
        original_write = cleanup.tx._write
        def fail_done(fd, name, *args, **kwargs):
            if name == 'move-0000.done.json':
                raise OSError(errno.ENOSPC, SECRET + str(self.root))
            return original_write(fd, name, *args, **kwargs)
        with patch.object(cleanup.tx, '_write', side_effect=fail_done):
            error = self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(error.moved_count, 1)
        self.assertFalse(self.app.exists())
        self.assertEqual(self.second.read_bytes(), self.before_second)
        observed = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['quarantined_count'], 1)
        self.restore(observed)
        self.assert_originals()

    def test_rename_outcome_unknown_is_reconciled_from_disk(self):
        plan = self.plan()
        original_rename = cleanup.os.rename
        def ambiguous_rename(source, destination, **kwargs):
            result = original_rename(source, destination, **kwargs)
            if destination == 'root-0000':
                raise OSError(errno.EIO, SECRET + str(self.root))
            return result
        with patch.object(cleanup.os, 'rename', side_effect=ambiguous_rename):
            error = self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(error.stage, 'move_outcome_unknown')
        self.assertFalse(self.app.exists())
        observed = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['quarantined_count'], 1)
        self.restore(observed)
        self.assert_originals()

    def test_batch_path_rebinding_in_callback_blocks_new_moves(self):
        plan = self.plan()
        batch = self.quarantine_dir / plan.private_material()['action_id']
        parked = self.quarantine_dir / 'rebound-private-batch'
        changed = False
        def rebind_after_manifest(*args):
            nonlocal changed
            if (batch / 'manifest.json').exists() and not changed:
                batch.rename(parked)
                batch.mkdir(mode=0o700)
                changed = True
            return True
        self.assert_private_error(lambda: self.quarantine(plan, authorize=rebind_after_manifest))
        self.assertTrue(changed)
        self.assert_originals()
        self.assertFalse((parked / 'root-0000').exists())
        self.assertFalse((parked / 'root-0001').exists())

    def test_partial_restore_cancellation_is_reconciled_and_can_resume(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        def cancelled():
            return self.app.exists() or self.second.exists()
        error = self.assert_private_error(lambda: self.restore(receipt, cancelled=cancelled))
        self.assertEqual(error.moved_count, 1)
        self.assertEqual(sum(path.exists() for path in (self.app, self.second)), 1)
        observed = cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok)
        self.assertEqual(observed.preview()['state'], 'partial')
        self.restore(observed)
        self.assert_originals()

    def test_cancellation_callback_requires_a_literal_boolean(self):
        for value in (None, 0, 1, 'no', [], {}):
            with self.subTest(value=value):
                self.assert_plan_rejected(cancelled=lambda: value)
                self.assert_private_error(lambda: self.quarantine(cancelled=lambda: value))
                self.assert_originals()

    def test_nonfinite_monotonic_clock_fails_closed(self):
        for value in (math.nan, math.inf, -math.inf, True, None, 'invalid', 10**1000):
            for initial in (True, False):
                with self.subTest(value=type(value).__name__, initial=initial):
                    sequence = [value] * 100 if initial else [100, 100, value] + [100] * 100
                    with patch.object(cleanup.time, 'monotonic', side_effect=sequence):
                        self.assert_plan_rejected()
                    self.assert_originals()

    def test_backward_or_unrepresentable_clock_deadlines_fail_closed(self):
        for sequence in ([100, 99] + [99] * 1000,
                         [100, 101, 100.5] + [101] * 1000,
                         [1e308] * 1000, [-1e308] * 1000):
            with self.subTest(sequence=sequence[:3]):
                with patch.object(cleanup.time, 'monotonic', side_effect=sequence):
                    self.assert_plan_rejected()
                self.assert_originals()

    def test_quarantine_directory_identity_drift_is_rejected(self):
        plan = self.plan()
        parked = self.root / 'previous-quarantine'
        self.quarantine_dir.rename(parked)
        self.quarantine_dir.mkdir(mode=0o700)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assert_originals()
        self.assertEqual(list(parked.iterdir()), [])
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])

    def test_source_parent_identity_drift_is_rejected(self):
        container = self.root / 'source-container'
        container.mkdir(mode=0o700)
        nested_source = container / 'data'
        nested_source.write_bytes(b'synthetic-nested-data')
        nested_source.chmod(0o600)
        plan = self.plan(roots=[dict(self.roots[0], path=str(nested_source))])
        parked = self.root / 'previous-source-container'
        container.rename(parked)
        container.mkdir(mode=0o700)
        nested_source.write_bytes(b'later-nested-data')
        nested_source.chmod(0o600)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual((parked / 'data').read_bytes(), b'synthetic-nested-data')
        self.assertEqual(nested_source.read_bytes(), b'later-nested-data')
        self.assert_protected()

    def test_protected_path_replacement_after_plan_is_rejected(self):
        plan = self.plan()
        parked = self.root / 'previous-protected-project'
        self.protected.rename(parked)
        self.protected.mkdir(mode=0o700)
        self.protected_file.write_bytes(self.before_protected)
        self.protected_file.chmod(0o600)
        self.assert_private_error(lambda: self.quarantine(plan))
        self.assert_originals()
        self.assertEqual((parked / 'keep').read_bytes(), self.before_protected)

    def test_cross_filesystem_metadata_is_rejected_before_mutation(self):
        identity = self.payload.stat().st_ino
        original_fstat = cleanup.os.fstat
        def different_device(fd):
            value = original_fstat(fd)
            if value.st_ino == identity:
                names = ('st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid', 'st_gid',
                         'st_size', 'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns')
                fields = {key: getattr(value, key) for key in names}
                fields['st_dev'] += 1
                return SimpleNamespace(**fields)
            return value
        with patch.object(cleanup.os, 'fstat', side_effect=different_device):
            self.assert_plan_rejected()
        self.assert_originals()

    def test_foreign_owner_metadata_is_rejected_before_mutation(self):
        identity = self.payload.stat().st_ino
        original_fstat = cleanup.os.fstat
        def different_owner(fd):
            value = original_fstat(fd)
            if value.st_ino == identity:
                names = ('st_mode', 'st_ino', 'st_dev', 'st_nlink', 'st_uid', 'st_gid',
                         'st_size', 'st_atime_ns', 'st_mtime_ns', 'st_ctime_ns')
                fields = {key: getattr(value, key) for key in names}
                fields['st_uid'] += 1
                return SimpleNamespace(**fields)
            return value
        with patch.object(cleanup.os, 'fstat', side_effect=different_owner):
            self.assert_plan_rejected()
        self.assert_originals()

    def test_post_move_fsync_failure_reports_move_and_preserves_recovery(self):
        plan = self.plan()
        original_fsync = cleanup.os.fsync
        def fail_after_move(fd):
            if not self.app.exists():
                raise OSError(errno.EIO, SECRET + str(self.root))
            return original_fsync(fd)
        with patch.object(cleanup.os, 'fsync', side_effect=fail_after_move):
            error = self.assert_private_error(lambda: self.quarantine(plan))
        self.assertEqual(error.moved_count, 1)
        self.assertEqual(error.stage, 'after_move_not_verified')
        self.assertFalse(self.app.exists())
        self.assertEqual(self.second.read_bytes(), self.before_second)
        observed = cleanup.reconcile(plan, error.recovery_id, host_check=self.host_ok)
        self.restore(observed)
        self.assert_originals()

    def test_restore_prepared_journal_exists_before_each_actual_rename(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        batch = self.quarantine_dir / receipt.recovery_id
        original_rename = cleanup.os.rename
        moves = []
        def checked_rename(source, destination, **kwargs):
            if str(source).startswith('root-'):
                index = int(str(source).split('-')[-1])
                prepared = list(batch.glob('restore-*-%04d.prepared.json' % index))
                self.assertEqual(len(prepared), 1)
                step = json.loads(prepared[0].read_text(encoding='utf-8'))
                self.assertEqual(step['operation'], 'restore_cleanup')
                self.assertEqual(step['receipt_digest'], receipt.digest())
                self.assertEqual(step['index'], index)
                self.assertEqual(stat.S_IMODE(prepared[0].stat().st_mode), 0o600)
                moves.append(index)
            return original_rename(source, destination, **kwargs)
        with patch.object(cleanup.os, 'rename', side_effect=checked_rename):
            self.restore(receipt)
        self.assertEqual(moves, [0, 1])
        self.assert_originals()

    def test_reconcile_requires_target_bound_id_live_host_and_budget(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        for recovery_id, kwargs in (('different', {'host_check': self.host_ok}),
                                    (receipt.recovery_id, {'host_check': None}),
                                    (receipt.recovery_id, {'host_check': self.host_ok, 'cancelled': lambda: True}),
                                    (receipt.recovery_id, {'host_check': self.host_ok, 'max_seconds': 0})):
            with self.subTest(recovery_id=recovery_id, kwargs=kwargs):
                self.assert_private_error(lambda: cleanup.reconcile(plan, recovery_id, **kwargs))
        self.assertFalse(self.app.exists())
        self.assertFalse(self.second.exists())
        self.restore(receipt)
        self.assert_originals()

    def test_plan_constructor_top_level_mutations_fail_with_private_errors(self):
        original = self.plan().private_material()
        for field in original:
            for value in (None, True, 0, 'invalid', [], {}):
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.subTest(field=field, value=type(value).__name__):
                    self.assert_private_error(lambda: cleanup.CleanupPlan(changed))
        for changed in ({}, [], None, dict(original, extra=SECRET)):
            self.assert_private_error(lambda: cleanup.CleanupPlan(changed))
        for field in original:
            changed = copy.deepcopy(original)
            del changed[field]
            self.assert_private_error(lambda: cleanup.CleanupPlan(changed))
        self.assert_originals()
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])

    def test_receipt_constructor_top_level_mutations_fail_with_private_errors(self):
        receipt = self.quarantine()
        original = receipt.private_material()
        for field in original:
            for value in (None, True, 0, 'invalid', [], {}):
                changed = copy.deepcopy(original)
                changed[field] = value
                with self.subTest(field=field, value=type(value).__name__):
                    self.assert_private_error(lambda: cleanup.CleanupReceipt(changed))
        for field in original:
            changed = copy.deepcopy(original)
            del changed[field]
            self.assert_private_error(lambda: cleanup.CleanupReceipt(changed))
        self.restore(receipt)
        self.assert_originals()

    def test_unicode_path_receipt_budget_is_reserved_before_any_write(self):
        # Each component stays below the filesystem byte limit. The inventory
        # itself fits, but JSON escaping plus a recovery observation duplicates
        # these legal relative paths and exceeds the persisted envelope budget.
        directory = self.app
        for index in range(4):
            directory = directory / (('数' * 80) + str(index))
            directory.mkdir(mode=0o700)
        for index in range(1000):
            path = directory / ('leaf-%04d' % index)
            path.write_bytes(b'x')
            path.chmod(0o600)
        observed_sizes = []
        original_reserve = cleanup._reserve
        def reserve(document):
            encoded = json.dumps(document, sort_keys=True, separators=(',', ':'), ensure_ascii=True).encode()
            observed_sizes.append(len(encoded))
            return original_reserve(document)
        with patch.object(cleanup, '_reserve', side_effect=reserve):
            self.assert_plan_rejected()
        self.assertEqual(len(observed_sizes), 1)
        self.assertLess(observed_sizes[0], 4 * 1024 * 1024)
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])
        self.assertEqual(len(list(directory.iterdir())), 1000)
        self.assert_originals()

    def test_protected_inode_alias_is_rejected_before_opening_or_hashing(self):
        protected_stat = self.protected_file.stat()
        original_stat = cleanup.os.stat
        original_open = cleanup.os.open
        def aliased_stat(path, *args, **kwargs):
            if path == self.payload.name and kwargs.get('dir_fd') is not None:
                return protected_stat
            return original_stat(path, *args, **kwargs)
        with patch.object(cleanup.os, 'stat', side_effect=aliased_stat), \
                patch.object(cleanup.os, 'open', wraps=original_open) as opened:
            # The wrapper retains the real open() dir_fd capability.
            with patch.object(cleanup.os, 'supports_dir_fd', cleanup.os.supports_dir_fd | {opened}):
                error = self.assert_plan_rejected(protected_paths=[str(self.protected_file)])
            self.assertEqual(error.code, 'PROTECTED_ALIAS')
            self.assertFalse(any(call.args[0] == self.payload.name for call in opened.call_args_list))
        self.assert_originals()

    def test_isolated_exact_file_import_is_side_effect_free(self):
        code = r"""
import importlib.util
import json
import os
import sys

module_path, input_root = sys.argv[1:3]
original_sys_path = tuple(sys.path)
accesses = []

def check_path(value):
    if isinstance(value, (str, bytes)):
        path = os.path.abspath(os.fsdecode(value))
        if path == input_root or path.startswith(input_root + os.sep):
            accesses.append(path)
            raise AssertionError('Import accessed the synthetic input tree')

def guard(function):
    def wrapped(path, *args, **kwargs):
        check_path(path)
        return function(path, *args, **kwargs)
    return wrapped

# Audit covers import machinery's file opens; wrappers additionally cover
# metadata reads, which do not all generate CPython audit events.
for name in ('stat', 'lstat', 'scandir', 'listdir'):
    setattr(os, name, guard(getattr(os, name)))

def audit(event, args):
    if event == 'open' or event.startswith(('os.listdir', 'os.scandir', 'os.remove',
                                           'os.rename', 'os.rmdir', 'os.mkdir', 'os.chdir')):
        count = 2 if event.startswith('os.rename') else 1
        for argument in args[:count]:
            check_path(argument)
    if event.startswith(('subprocess.', 'socket.')):
        raise AssertionError('Import attempted a process or network operation')

sys.addaudithook(audit)
spec = importlib.util.spec_from_file_location('isolated_cleanup_core', module_path)
module = importlib.util.module_from_spec(spec)
spec.loader.exec_module(module)
names = ('plan', 'quarantine', 'reconcile', 'restore', 'load_manifest')
assert all(callable(getattr(module, name, None)) for name in names)
assert tuple(sys.path) == original_sys_path
assert not accesses
assert os.path.realpath(module.tx.__file__) == os.path.join(os.path.dirname(module_path), 'transactions.py')
print(json.dumps({'callable': list(names), 'input_accesses': len(accesses), 'sys_path_unchanged': True}))
"""
        environment = dict(os.environ, HOME=str(self.root), USERPROFILE=str(self.root))
        result = subprocess.run(
            [sys.executable, '-I', '-S', '-B', '-c', code,
             str(SCRIPTS / 'cleanup_transactions.py'), str(self.root)],
            cwd=str(self.root), env=environment, capture_output=True, text=True,
            timeout=20, check=False)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(result.stderr, '')
        self.assertEqual(json.loads(result.stdout), {
            'callable': ['plan', 'quarantine', 'reconcile', 'restore', 'load_manifest'],
            'input_accesses': 0, 'sys_path_unchanged': True})
        self.assert_originals()
        self.assertEqual(list(self.quarantine_dir.iterdir()), [])

    def test_unsupported_platform_rejects_before_posix_metadata_calls(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = str(self.quarantine_dir / receipt.recovery_id / 'manifest.json')
        operations = (lambda: self.plan(), lambda: self.quarantine(plan),
                      lambda: cleanup.reconcile(plan, receipt.recovery_id, host_check=self.host_ok),
                      lambda: self.restore(receipt),
                      lambda: cleanup.load_manifest(manifest, plan.digest(), TARGET))
        with patch.object(cleanup.os, 'name', 'nt'), \
                patch.object(cleanup.os, 'geteuid', side_effect=AssertionError('POSIX metadata used')):
            for operation in operations:
                error = self.assert_private_error(operation)
                self.assertEqual(error.code, 'PLATFORM_UNSUPPORTED')
        self.restore(receipt)
        self.assert_originals()

    def test_surrogate_paths_are_rejected_before_filesystem_access(self):
        for suffix in ('\ud800', '\udfff'):
            path = str(self.root) + '/surrogate-' + suffix
            self.assert_plan_rejected(roots=[dict(self.roots[0], path=path)])
            self.assert_plan_rejected(protected_paths=[path])
            self.assert_plan_rejected(quarantine_directory=path)
        self.assert_originals()

    def test_manifest_loader_honors_deadline_and_cancel_before_exact_read(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = str(self.quarantine_dir / receipt.recovery_id / 'manifest.json')
        for options in ({'cancelled': lambda: True}, {'max_seconds': 0},
                        {'max_seconds': 10**1000}, {'max_seconds': 1e-30},
                        {'cancelled': lambda: None}):
            with self.subTest(options=tuple(options)):
                with patch.object(cleanup.tx, '_read', wraps=cleanup.tx._read) as read:
                    self.assert_private_error(lambda: cleanup.load_manifest(
                        manifest, plan.digest(), TARGET, **options))
                    read.assert_not_called()
        self.restore(receipt)
        self.assert_originals()

    def test_manifest_loader_checks_cancellation_after_exact_read(self):
        plan = self.plan()
        receipt = self.quarantine(plan)
        manifest = str(self.quarantine_dir / receipt.recovery_id / 'manifest.json')
        cancelled = False
        original_read = cleanup.tx._read
        def read_then_cancel(*args, **kwargs):
            nonlocal cancelled
            result = original_read(*args, **kwargs)
            cancelled = True
            return result
        with patch.object(cleanup.tx, '_read', side_effect=read_then_cancel) as read:
            error = self.assert_private_error(lambda: cleanup.load_manifest(
                manifest, plan.digest(), TARGET, cancelled=lambda: cancelled))
            self.assertEqual(error.code, 'CANCELLED')
            read.assert_called_once()
        self.restore(receipt)
        self.assert_originals()

    def test_no_process_or_network_is_used_for_real_fixture_roundtrip(self):
        with patch('subprocess.Popen', side_effect=AssertionError('No processes permitted')), \
                patch('subprocess.run', side_effect=AssertionError('No processes permitted')), \
                patch('socket.socket', side_effect=AssertionError('No network permitted')):
            plan = self.plan()
            receipt = self.quarantine(plan)
            self.restore(receipt)
        self.assert_originals()


if __name__ == '__main__':
    unittest.main()
