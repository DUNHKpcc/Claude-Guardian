"""Transport orchestration with synthetic adapter only; no production admission."""
from contextlib import contextmanager
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import repair_execution as e
import repair_cli as r
import test_repair_cli as fixtures
from test_config_edit_plan import RAW



@contextmanager
def synthetic_adapter(side_effect=None):
    from unittest.mock import Mock
    check = Mock(side_effect=side_effect)
    @contextmanager
    def session(document):
        yield check
    with patch.object(e, '_native_session', side_effect=session):
        yield check

@unittest.skipUnless(os.name == 'posix', 'POSIX synthetic files only')
class RepairExecution(unittest.TestCase):
    setUp = fixtures.RepairCLI.setUp
    save = fixtures.RepairCLI.save
    prepare = fixtures.RepairCLI.prepare
    tree = fixtures.RepairCLI.tree

    def retained(self):
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.plan = self.root / 'plan.json'
        self.digest = e.retain(self.prepare(), plan_path=str(self.plan),
                               backup_directory=str(self.backups))
        self.arguments = dict(request_path=str(self.request), plan_path=str(self.plan),
                              plan_digest=self.digest, target_path=str(self.target),
                              target_ref='mac-a', backup_directory=str(self.backups))

    def test_production_gate_closed_no_writes(self):
        self.retained()
        with self.assertRaisesRegex(e.tx.TransactionError, '^NATIVE_REPAIR_ADAPTER_UNAVAILABLE$'):
            e.execute(**self.arguments)
        self.assertEqual(self.target.read_bytes(), RAW)
        self.assertEqual(list(self.backups.iterdir()), [])
        self.assertEqual(self.plan.stat().st_mode & 0o777, 0o600)

    def test_synthetic_admitted_transport_and_independent_recovery(self):
        self.retained()
        with synthetic_adapter() as adapter:
            result = e.execute(**self.arguments)
        self.assertEqual(adapter.call_count, 4)
        self.assertEqual(result['byte_readback'], 'pass')
        self.assertEqual(result['effective_routing'], 'not_run')
        self.assertEqual(result['status'], 'written_but_not_verified')
        self.assertNotEqual(self.target.read_bytes(), RAW)
        receipt = json.loads((self.backups / result['recovery_id'] / 'applied.json').read_text())
        # Separate fresh recovery approval, not inherited from repair.
        expected = e.tx.digest(receipt)
        restored = e.tx.rollback(receipt, target_ref='mac-a', exclusive_access=True,
                                 authorize=lambda op, digest, target:
                                 op == 'rollback' and digest == expected and target == 'mac-a')
        self.assertEqual(restored['state'], 'restored')
        self.assertEqual(self.target.read_bytes(), RAW)
        with synthetic_adapter():
            with self.assertRaisesRegex(e.tx.TransactionError, '^STALE_FILE$'):
                e.execute(**self.arguments)  # Old plan cannot be replayed after restoration.

    def test_digest_expiry_target_backup_and_request_bound(self):
        self.retained()
        for key, value, code in [('plan_digest', '0' * 64, 'PLAN_DIGEST_MISMATCH'),
                                 ('target_ref', 'other', 'TARGET_MISMATCH'),
                                 ('backup_directory', str(self.root), 'BACKUP_SCOPE_MISMATCH')]:
            args = dict(self.arguments, **{key: value})
            with self.assertRaisesRegex(e.tx.TransactionError, '^' + code + '$'):
                e.execute(**args)
        with patch.object(e.time, 'time', return_value=1e10):
            with self.assertRaisesRegex(e.tx.TransactionError, '^INVALID_OR_EXPIRED_PLAN$'):
                e.execute(**self.arguments)
        self.document['remedy_request']['route_ref'] = 'different-route'
        self.save()
        with synthetic_adapter():
            with self.assertRaisesRegex(e.tx.TransactionError, '^REQUEST_CHANGED$'):
                e.execute(**self.arguments)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_changed_plan_cannot_be_used(self):
        self.retained()
        content = json.loads(self.plan.read_text())
        content['plan']['action_id'] = '1' * 32
        self.plan.write_text(json.dumps(content))
        with self.assertRaisesRegex(e.tx.TransactionError, '^PLAN_DIGEST_MISMATCH$'):
            e.execute(**self.arguments)

    def test_cancel_before_read_and_final_commit(self):
        self.retained()
        with patch.object(e, '_bound_document', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(r.RepairError, '^CANCELLED$'):
                e.execute(**self.arguments, cancelled=lambda: True)
        calls = 0
        cancelled = False
        def gate():
            nonlocal calls, cancelled
            calls += 1
            if calls == 3:
                cancelled = True
        with synthetic_adapter(side_effect=gate):
            with self.assertRaisesRegex(e.tx.TransactionError, '^CANCELLED$') as caught:
                e.execute(**self.arguments, cancelled=lambda: cancelled)
        self.assertTrue(caught.exception.recovery_id)
        self.assertEqual(self.target.read_bytes(), RAW)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'prepared.json').exists())

    def test_stale_context_before_commit_preserves_backup(self):
        self.retained()
        calls = 0
        def gate():
            nonlocal calls
            calls += 1
            if calls == 3:
                raise e.tx.TransactionError('STALE_NATIVE_CONTEXT')
        with synthetic_adapter(side_effect=gate):
            with self.assertRaisesRegex(e.tx.TransactionError, '^STALE_NATIVE_CONTEXT$') as caught:
                e.execute(**self.arguments)
        self.assertTrue(caught.exception.recovery_id)
        self.assertEqual(self.target.read_bytes(), RAW)

    def test_write_failure_retains_recovery(self):
        self.retained()
        with synthetic_adapter(), \
                patch.object(e.tx.os, 'replace', side_effect=OSError('private-error')):
            with self.assertRaisesRegex(e.tx.TransactionError, '^IO_FAILURE$') as caught:
                e.execute(**self.arguments)
        self.assertTrue(caught.exception.recovery_id)
        self.assertNotIn('private-error', str(caught.exception))
        self.assertEqual(self.target.read_bytes(), RAW)

    def test_post_commit_deadline_preserves_applied_recovery(self):
        self.retained()
        original = e.tx.verify
        cancelled = False
        def verify(receipt):
            nonlocal cancelled
            result = original(receipt)
            cancelled = True
            return result
        with synthetic_adapter(), patch.object(e.tx, 'verify', side_effect=verify):
            with self.assertRaisesRegex(e.tx.TransactionError, '^CANCELLED$') as caught:
                e.execute(**self.arguments, cancelled=lambda: cancelled)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'applied.json').exists())
        self.assertNotEqual(self.target.read_bytes(), RAW)

    def test_adapter_exit_failure_preserves_applied_receipt(self):
        self.retained()
        @contextmanager
        def session(document):
            yield lambda: None
            raise RuntimeError('private-SENTINEL')
        with patch.object(e, '_native_session', side_effect=session):
            with self.assertRaisesRegex(e.tx.TransactionError, '^NATIVE_ADAPTER_FAILURE$') as caught:
                e.execute(**self.arguments)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'applied.json').exists())
        self.assertNotEqual(self.target.read_bytes(), RAW)

    def test_write_and_resource_exit_failure_retains_prepared_batch(self):
        self.retained()
        @contextmanager
        def session(document):
            try:
                yield lambda: None
            finally:
                raise RuntimeError('private-cleanup-error')
        with patch.object(e, '_native_session', side_effect=session), \
                patch.object(e.tx.os, 'replace', side_effect=OSError('private-write-error')):
            with self.assertRaisesRegex(e.tx.TransactionError, '^NATIVE_ADAPTER_FAILURE$') as caught:
                e.execute(**self.arguments)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'prepared.json').exists())
        self.assertEqual(self.target.read_bytes(), RAW)

    def test_post_readback_context_change_retains_recovery(self):
        self.retained()
        calls = 0
        def check():
            nonlocal calls
            calls += 1
            if calls == 4:
                raise e.tx.TransactionError('STALE_NATIVE_CONTEXT')
        with synthetic_adapter(side_effect=check):
            with self.assertRaisesRegex(e.tx.TransactionError, '^STALE_NATIVE_CONTEXT$') as caught:
                e.execute(**self.arguments)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'applied.json').exists())

    def test_conflict_recovery_does_not_overwrite_later_edit(self):
        self.retained()
        with synthetic_adapter():
            result = e.execute(**self.arguments)
        receipt = json.loads((self.backups / result['recovery_id'] / 'applied.json').read_text())
        self.target.write_bytes(b'later change')
        with self.assertRaisesRegex(e.tx.TransactionError, '^ROLLBACK_CONFLICT$'):
            e.tx.rollback(receipt, target_ref='mac-a', exclusive_access=True,
                          authorize=lambda *args: True)
        self.assertEqual(self.target.read_bytes(), b'later change')


if __name__ == '__main__':
    unittest.main()
