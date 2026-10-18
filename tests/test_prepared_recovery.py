"""Witness-backed recovery, exclusively dedicated synthetic temporary files."""
import copy
import importlib.util
import json
import os
import stat
import subprocess
import sys
from pathlib import Path
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('prepared_tx', ROOT / 'skills/claude-guardian/scripts/transactions.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


@unittest.skipUnless(os.name == 'posix', 'POSIX exact-file recovery only')
class PreparedRecovery(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='guardian-prepared-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'config'
        self.target.write_bytes(b'original synthetic bytes')
        self.target.chmod(0o640)
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.plan = t.plan(str(self.target), b'proposed synthetic bytes', 'synthetic-device')

    def apply(self):
        expected = t.digest({'plan': self.plan, 'backup_directory': str(self.backups)})
        return t.apply(self.plan, target_ref='synthetic-device', backup_directory=str(self.backups),
                       exclusive_access=True, authorize=lambda op, d, ref: (op, d, ref) == ('apply', expected, 'synthetic-device'))

    def interrupted_apply(self):
        write = t._write
        def fail(fd, name, data, mode=0o600):
            if name == 'applied.json':
                raise OSError('synthetic journal failure')
            return write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail):
            with self.assertRaises(t.TransactionError) as caught:
                self.apply()
        self.batch = self.backups / caught.exception.recovery_id
        self.receipt_path = self.batch / 'prepared.json'
        self.receipt = json.loads(self.receipt_path.read_text())

    def observation(self):
        return t.reconcile(self.receipt, receipt_path=str(self.receipt_path), target_ref='synthetic-device',
                           target_path=str(self.target), backup_batch=str(self.batch))

    def restore(self, observation=None, authorize=None):
        observation = observation or self.observation()
        expected = t.digest({'recovery_digest': t.digest(self.receipt), 'observation': observation})
        return t.restore_prepared(self.receipt, observation, target_ref='synthetic-device', exclusive_access=True,
                                  authorize=authorize or (lambda op, d, ref: (op, d, ref) == ('restore_prepared', expected, 'synthetic-device')))

    def test_post_commit_failure_can_be_separately_restored(self):
        self.interrupted_apply()
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')
        observation = self.observation()
        self.assertEqual(observation['classification'], 'prepared_candidate_observed')
        result = self.restore(observation)
        self.assertEqual(result['state'], 'restored')
        self.assertEqual(self.target.read_bytes(), b'original synthetic bytes')
        self.assertTrue((self.batch / 'prepared.json').exists())
        self.assertFalse((self.batch / 'applied.json').exists())
        self.assertEqual(result['application_effect'], 'not_tested')

    def tree(self):
        return {str(p.relative_to(self.root)): (p.stat().st_ino, p.stat().st_mode, p.read_bytes())
                for p in self.root.rglob('*') if p.is_file()}

    def test_reconcile_is_deterministic_nonmutating_and_content_free(self):
        self.interrupted_apply()
        before = self.tree()
        first = self.observation()
        self.assertEqual(first, self.observation())
        self.assertEqual(before, self.tree())
        self.assertNotIn('proposed synthetic bytes', json.dumps(first))
        self.assertNotIn('original synthetic bytes', json.dumps(first))
        self.assertEqual(first['network_effect'], 'not_tested')

    def test_witness_is_persisted_before_replace(self):
        write, replace = t._write, t.os.replace
        persisted = False
        def capture(fd, name, data, mode=0o600):
            nonlocal persisted
            result = write(fd, name, data, mode)
            if name == 'prepared.json':
                document = json.loads(data)
                self.assertEqual(document['schema_version'], 'exact-file-recovery/2')
                self.assertEqual(document['replacement']['snapshot']['sha256'], self.plan['after_sha256'])
                persisted = True
            return result
        def commit(*args, **kwargs):
            self.assertTrue(persisted)
            return replace(*args, **kwargs)
        with patch.object(t, '_write', side_effect=capture), patch.object(t.os, 'replace', side_effect=commit):
            receipt = self.apply()
        self.assertEqual(t.verify(receipt)['check_status'], 'pass')
        self.assertEqual(receipt['replacement']['snapshot']['inode'], receipt['applied_snapshot']['inode'])

    def test_witness_write_failure_prevents_target_commit(self):
        write = t._write
        def fail(fd, name, data, mode=0o600):
            if name == 'prepared.json':
                raise OSError('synthetic failure')
            return write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail), patch.object(t.os, 'replace') as replace:
            with self.assertRaises(t.TransactionError) as caught:
                self.apply()
            replace.assert_not_called()
        self.assertEqual(self.target.read_bytes(), b'original synthetic bytes')
        self.assertTrue(caught.exception.recovery_id)
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_same_bytes_foreign_inode_and_changed_metadata_are_conflicts(self):
        self.interrupted_apply()
        self.target.chmod(0o600)
        self.assertEqual(self.observation()['classification'], 'conflict')
        self.target.chmod(0o640)
        other = self.root / 'foreign'
        other.write_bytes(b'proposed synthetic bytes'); other.chmod(0o640)
        os.replace(other, self.target)
        self.assertEqual(self.observation()['classification'], 'conflict')
        with self.assertRaisesRegex(t.TransactionError, '^RECOVERY_WITNESS_MISMATCH$'):
            self.restore()
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_legacy_prepared_never_restored(self):
        self.interrupted_apply()
        self.receipt['schema_version'] = 'exact-file-recovery/1'
        del self.receipt['replacement']; del self.receipt['batch_identity']
        self.receipt_path.write_text(json.dumps(self.receipt))
        observation = self.observation()
        self.assertEqual(observation['classification'], 'legacy_identity_unproven')
        before = self.tree()
        with self.assertRaisesRegex(t.TransactionError, '^LEGACY_RECOVERY_IDENTITY_UNPROVEN$'):
            self.restore(observation)
        with self.assertRaisesRegex(t.TransactionError, '^RECOVERY_REQUIRES_RECONCILIATION$'):
            t.rollback(self.receipt, target_ref='synthetic-device', exclusive_access=True, authorize=lambda *args: True)
        self.assertEqual(before, self.tree())

    def test_legacy_applied_stays_strict_and_rolls_back(self):
        receipt = self.apply()
        receipt['schema_version'] = 'exact-file-recovery/1'
        del receipt['replacement']; del receipt['batch_identity']
        expected = t.digest(receipt)
        result = t.rollback(receipt, target_ref='synthetic-device', exclusive_access=True,
                            authorize=lambda op, d, ref: op == 'rollback' and d == expected)
        self.assertEqual(result['state'], 'restored')
        self.assertTrue((self.backups / result['recovery_id'] / ('restore-' + result['attempt_id'] + '.prepared.json')).exists())

    def test_two_separate_restore_authorizations_required(self):
        self.interrupted_apply()
        observation = self.observation()
        expected = t.digest({'recovery_digest': t.digest(self.receipt), 'observation': observation})
        calls = []
        def authorize(*args):
            calls.append(args)
            return args == ('restore_prepared', expected, 'synthetic-device')
        self.restore(observation, authorize)
        self.assertEqual(calls, [('restore_prepared', expected, 'synthetic-device')] * 2)

    def test_apply_approval_and_nonboolean_approval_are_rejected(self):
        self.interrupted_apply()
        for callback in (lambda op, *args: op == 'apply', lambda *args: 1, lambda *args: None):
            before = self.tree()
            with self.assertRaisesRegex(t.TransactionError, '^AUTHORIZATION_DENIED$'):
                self.restore(authorize=callback)
            self.assertEqual(before, self.tree())

    def test_cancellation_at_each_restore_approval_preserves_tree(self):
        self.interrupted_apply()
        for cancel_at in (1, 2):
            before = self.tree(); calls = 0
            def authorize(*args):
                nonlocal calls
                calls += 1
                return calls != cancel_at
            with self.assertRaisesRegex(t.TransactionError, '^AUTHORIZATION_DENIED$'):
                self.restore(authorize=authorize)
            self.assertEqual(before, self.tree())

    def test_changed_target_during_final_approval_is_not_overwritten(self):
        self.interrupted_apply(); calls = 0
        def authorize(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                self.target.write_bytes(b'later user edit')
            return True
        with self.assertRaisesRegex(t.TransactionError, '^RECONCILIATION_STALE$'):
            self.restore(authorize=authorize)
        self.assertEqual(self.target.read_bytes(), b'later user edit')
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_changed_receipt_same_bytes_new_inode_is_stale(self):
        self.interrupted_apply(); calls = 0
        def authorize(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                other = self.batch / 'replacement'
                other.write_bytes(self.receipt_path.read_bytes()); other.chmod(0o600)
                os.replace(other, self.receipt_path)
            return True
        with self.assertRaisesRegex(t.TransactionError, '^RECONCILIATION_STALE$'):
            self.restore(authorize=authorize)
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_changed_backup_same_bytes_new_inode_is_stale(self):
        self.interrupted_apply(); calls = 0
        def authorize(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                other = self.batch / 'replacement'
                other.write_bytes((self.batch / 'original.bin').read_bytes()); other.chmod(0o600)
                os.replace(other, self.batch / 'original.bin')
            return True
        with self.assertRaisesRegex(t.TransactionError, '^RECONCILIATION_STALE$'):
            self.restore(authorize=authorize)
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_changed_receipt_contents_and_corrupt_backup_block(self):
        self.interrupted_apply()
        self.receipt_path.write_text('{}')
        with self.assertRaisesRegex(t.TransactionError, '^RECEIPT_DIGEST_MISMATCH$'):
            self.observation()
        self.receipt_path.write_text(json.dumps(self.receipt))
        (self.batch / 'original.bin').write_bytes(b'corrupt')
        with self.assertRaisesRegex(t.TransactionError, '^BACKUP_CORRUPT$'):
            self.observation()

    def test_scope_rejected_before_any_embedded_read(self):
        self.interrupted_apply()
        for field, value in [('target_ref', 'wrong'), ('target_path', str(self.root / 'wrong')),
                             ('backup_batch', str(self.root / 'wrong')),
                             ('receipt_path', str(self.batch / 'alias.json'))]:
            arguments = dict(receipt_path=str(self.receipt_path), target_ref='synthetic-device',
                             target_path=str(self.target), backup_batch=str(self.batch))
            arguments[field] = value
            with patch.object(t, '_directory', side_effect=AssertionError('unexpected read')):
                with self.assertRaises(t.TransactionError):
                    t.reconcile(self.receipt, **arguments)

    def test_batch_replacement_and_parent_replacement_block(self):
        self.interrupted_apply()
        old = self.root / 'old-batch'; self.batch.rename(old)
        self.batch.mkdir(mode=0o700)
        for source in old.iterdir():
            destination = self.batch / source.name
            destination.write_bytes(source.read_bytes()); destination.chmod(0o600)
        with self.assertRaisesRegex(t.TransactionError, '^BACKUP_DIRECTORY_CHANGED$'):
            self.observation()

    def test_recovery_does_not_require_unexpired_apply_plan(self):
        self.interrupted_apply()
        with patch.object(t.time, 'time', return_value=self.plan['expires_at'] + 1000):
            self.assertEqual(self.restore()['state'], 'restored')

    def test_full_size_proposal_can_be_reconciled_and_restored(self):
        self.plan = t.plan(str(self.target), b'x' * t.MAX_BYTES, 'synthetic-device')
        self.interrupted_apply()
        self.assertGreater(self.receipt_path.stat().st_size, t.MAX_BYTES)
        self.assertEqual(self.observation()['classification'], 'prepared_candidate_observed')
        self.assertEqual(self.restore()['state'], 'restored')

    def test_restore_journal_failure_has_usable_readonly_witness(self):
        self.interrupted_apply()
        write = t._write
        def fail(fd, name, data, mode=0o600):
            if name.startswith('rollback-'):
                raise OSError('synthetic completion failure')
            return write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail):
            with self.assertRaisesRegex(t.TransactionError, '^IO_FAILURE$') as caught:
                self.restore()
        self.assertEqual(caught.exception.recovery_id, self.receipt['batch'])
        self.assertTrue(caught.exception.attempt_id)
        self.assertEqual(self.target.read_bytes(), b'original synthetic bytes')
        witness_path = self.batch / ('restore-' + caught.exception.attempt_id + '.prepared.json')
        witness = json.loads(witness_path.read_text())
        observation = t.reconcile(witness, receipt_path=str(witness_path), target_ref='synthetic-device',
                                  target_path=str(self.target), backup_batch=str(self.batch))
        self.assertEqual(observation['classification'], 'restored_candidate_observed')
        self.assertFalse(list(self.batch.glob('rollback-*.json')))
        self.assertEqual(self.observation()['classification'], 'conflict')

    def test_ordinary_rollback_journal_gap_is_witnessed_and_normalized(self):
        receipt = self.apply(); write = t._write
        def fail(fd, name, data, mode=0o600):
            if name.startswith('rollback-'):
                raise OSError('synthetic failure')
            return write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail):
            with self.assertRaisesRegex(t.TransactionError, '^IO_FAILURE$') as caught:
                t.rollback(receipt, target_ref='synthetic-device', exclusive_access=True, authorize=lambda *args: True)
        batch = self.backups / receipt['batch']
        path = batch / ('restore-' + caught.exception.attempt_id + '.prepared.json')
        observed = t.reconcile(json.loads(path.read_text()), receipt_path=str(path), target_ref='synthetic-device',
                               target_path=str(self.target), backup_batch=str(batch))
        self.assertEqual(observed['classification'], 'restored_candidate_observed')
        self.assertEqual(caught.exception.recovery_id, receipt['batch'])

    def test_postrename_directory_sync_failure_stays_recoverable(self):
        replace, fsync = t.os.replace, t.os.fsync
        renamed = False
        def replace_once(*args, **kwargs):
            nonlocal renamed
            result = replace(*args, **kwargs); renamed = True; return result
        def fail(fd):
            if renamed:
                raise OSError('synthetic target sync failure')
            return fsync(fd)
        with patch.object(t.os, 'replace', side_effect=replace_once), patch.object(t.os, 'fsync', side_effect=fail):
            with self.assertRaises(t.TransactionError) as caught:
                self.apply()
        self.batch = self.backups / caught.exception.recovery_id
        self.receipt_path = self.batch / 'prepared.json'
        self.receipt = json.loads(self.receipt_path.read_text())
        self.assertEqual(self.restore()['state'], 'restored')

    def test_successful_rename_does_not_cleanup_reused_stage_name(self):
        replace = t.os.replace
        foreign = []
        def replace_then_foreign(src, dst, **kwargs):
            result = replace(src, dst, **kwargs)
            name = self.root / src
            name.write_bytes(b'unrelated synthetic file')
            foreign.append(name)
            return result
        with patch.object(t.os, 'replace', side_effect=replace_then_foreign):
            self.apply()
        self.assertEqual(foreign[0].read_bytes(), b'unrelated synthetic file')

    def test_foreign_stage_during_approval_is_preserved(self):
        self.interrupted_apply(); calls = 0; foreign = []
        def authorize(*args):
            nonlocal calls
            calls += 1
            if calls == 2:
                stage = list(self.root.glob('.guardian-stage-*'))[0]
                other = self.root / 'foreign'
                other.write_bytes(b'foreign stage')
                os.replace(other, stage); foreign.append(stage)
            return True
        with self.assertRaisesRegex(t.TransactionError, '^STAGING_CHANGED$') as caught:
            self.restore(authorize=authorize)
        self.assertEqual(caught.exception.cleanup_code, 'STAGING_RETAINED')
        self.assertEqual(foreign[0].read_bytes(), b'foreign stage')
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_primary_denial_survives_cleanup_failure(self):
        self.interrupted_apply(); calls = 0
        unlink = t.os.unlink
        def authorize(*args):
            nonlocal calls
            calls += 1
            return calls != 2
        def fail(name, *args, **kwargs):
            if str(name).startswith('.guardian-stage-'):
                raise OSError('synthetic cleanup failure')
            return unlink(name, *args, **kwargs)
        with patch.object(t.os, 'unlink', side_effect=fail):
            with self.assertRaisesRegex(t.TransactionError, '^AUTHORIZATION_DENIED$') as caught:
                self.restore(authorize=authorize)
        self.assertEqual(caught.exception.cleanup_code, 'STAGING_CLEANUP_FAILED')
        self.assertEqual(caught.exception.recovery_id, self.receipt['batch'])

    def test_interrupt_after_rename_retains_batch_and_prepared_witness(self):
        replace = t.os.replace
        def interrupt(*args, **kwargs):
            replace(*args, **kwargs)
            raise KeyboardInterrupt()
        with patch.object(t.os, 'replace', side_effect=interrupt):
            with self.assertRaisesRegex(t.TransactionError, '^CANCELLED$') as caught:
                self.apply()
        self.batch = self.backups / caught.exception.recovery_id
        self.receipt_path = self.batch / 'prepared.json'
        self.receipt = json.loads(self.receipt_path.read_text())
        self.assertEqual(self.observation()['classification'], 'prepared_candidate_observed')

    def test_document_loader_rejects_duplicate_fields_and_unsafe_file(self):
        self.interrupted_apply()
        self.receipt_path.write_text('{"state":"prepared","state":"prepared"}')
        with self.assertRaisesRegex(t.TransactionError, '^INVALID_RECEIPT_JSON$'):
            self.observation()
        self.receipt_path.write_text(json.dumps(self.receipt)); self.receipt_path.chmod(0o644)
        with self.assertRaisesRegex(t.TransactionError, '^UNSAFE_RECEIPT_FILE$'):
            self.observation()

    def test_stale_full_snapshot_including_ctime_is_rejected(self):
        self.interrupted_apply(); observation = self.observation()
        self.target.chmod(0o600); self.target.chmod(0o640)
        self.assertEqual(self.observation()['classification'], 'prepared_candidate_observed')
        with self.assertRaisesRegex(t.TransactionError, '^RECONCILIATION_STALE$'):
            self.restore(observation)

    def test_no_exclusive_access_or_missing_authorization(self):
        self.interrupted_apply(); observation = self.observation()
        with self.assertRaisesRegex(t.TransactionError, '^EXCLUSIVE_ACCESS_REQUIRED$'):
            t.restore_prepared(self.receipt, observation, target_ref='synthetic-device', authorize=lambda *args: True)
        with self.assertRaisesRegex(t.TransactionError, '^AUTHORIZATION_REQUIRED$'):
            t.restore_prepared(self.receipt, observation, target_ref='synthetic-device', exclusive_access=True)

    def test_apply_rechecks_backup_and_prepared_after_approval(self):
        for mutation in ('receipt', 'backup', 'receipt_inode', 'backup_inode', 'batch'):
            with self.subTest(mutation=mutation):
                old_batches = set(self.backups.iterdir()); calls = 0
                def authorize(*args):
                    nonlocal calls
                    calls += 1
                    if calls == 2:
                        batch = (set(self.backups.iterdir()) - old_batches).pop()
                        if mutation == 'receipt':
                            (batch / 'prepared.json').write_text('{}')
                        elif mutation == 'backup':
                            (batch / 'original.bin').write_bytes(b'corrupt')
                        elif mutation == 'batch':
                            batch.rename(self.root / ('moved-' + batch.name))
                            batch.mkdir(mode=0o700)
                        else:
                            target = batch / ('prepared.json' if mutation == 'receipt_inode' else 'original.bin')
                            other = batch / 'replacement'; other.write_bytes(target.read_bytes()); other.chmod(0o600)
                            os.replace(other, target)
                    return True
                with self.assertRaises(t.TransactionError):
                    t.apply(self.plan, target_ref='synthetic-device', backup_directory=str(self.backups),
                            authorize=authorize, exclusive_access=True)
                self.assertEqual(self.target.read_bytes(), b'original synthetic bytes')
                self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_new_restore_witness_must_read_back_exactly(self):
        self.interrupted_apply(); write = t._write
        def corrupt(fd, name, data, mode=0o600):
            return write(fd, name, b'{}' if name.startswith('restore-') else data, mode)
        with patch.object(t, '_write', side_effect=corrupt):
            with self.assertRaisesRegex(t.TransactionError, '^RECEIPT_DIGEST_MISMATCH$'):
                self.restore()
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_backup_change_during_restore_witness_persist_blocks_commit(self):
        self.interrupted_apply(); write = t._write
        def mutate(fd, name, data, mode=0o600):
            result = write(fd, name, data, mode)
            if name.startswith('restore-'):
                (self.batch / 'original.bin').write_bytes(b'corrupt')
            return result
        with patch.object(t, '_write', side_effect=mutate):
            with self.assertRaisesRegex(t.TransactionError, '^BACKUP_CHANGED$'):
                self.restore()
        self.assertEqual(self.target.read_bytes(), b'proposed synthetic bytes')

    def test_rollback_first_approval_interrupt_is_normalized(self):
        receipt = self.apply(); before = self.tree()
        def cancel(*args):
            raise KeyboardInterrupt()
        with self.assertRaisesRegex(t.TransactionError, '^CANCELLED$') as caught:
            t.rollback(receipt, target_ref='synthetic-device', exclusive_access=True, authorize=cancel)
        self.assertEqual(caught.exception.recovery_id, receipt['batch'])
        self.assertEqual(before, self.tree())

    def test_primary_exception_survives_descriptor_close_failure(self):
        with t._directory(str(self.root)) as fd:
            real_close = t.os.close
            def close_then_fail(value):
                real_close(value)
                raise OSError('synthetic close failure')
            with patch.object(t.os, 'write', return_value=0), patch.object(t.os, 'close', side_effect=close_then_fail):
                with self.assertRaisesRegex(t.TransactionError, '^WRITE_FAILED$') as caught:
                    t._write(fd, 'partial-stage', b'synthetic')
        self.assertEqual(caught.exception.cleanup_code, 'DESCRIPTOR_CLOSE_FAILED')

    def test_original_observed_after_precommit_process_exit(self):
        self._process_crash('prepared')
        observation = self.observation()
        self.assertEqual(observation['classification'], 'original_observed')
        before = self.tree()
        with self.assertRaisesRegex(t.TransactionError, '^RECOVERY_WITNESS_MISMATCH$'):
            self.restore(observation)
        self.assertEqual(before, self.tree())

    def test_postrename_process_exit_can_restore(self):
        self._process_crash('renamed')
        self.assertEqual(self.observation()['classification'], 'prepared_candidate_observed')
        self.assertEqual(self.restore()['state'], 'restored')

    def test_postreadback_process_exit_can_restore(self):
        self._process_crash('journal')
        self.assertEqual(self.observation()['classification'], 'prepared_candidate_observed')
        self.assertEqual(self.restore()['state'], 'restored')

    def _process_crash(self, phase):
        producer = """
import os, sys
sys.path.insert(0, sys.argv[1])
import transactions as t
path, backup, phase = sys.argv[2:]
p = t.plan(path, b'proposed synthetic bytes', 'synthetic-device')
calls = 0
def authorize(*args):
    global calls
    calls += 1
    if phase == 'prepared' and calls == 2:
        os._exit(71)
    return True
replace, write = t.os.replace, t._write
def commit(*args, **kwargs):
    result = replace(*args, **kwargs)
    if phase == 'renamed':
        os._exit(72)
    return result
def journal(fd, name, data, mode=0o600):
    if phase == 'journal' and name == 'applied.json':
        os._exit(73)
    return write(fd, name, data, mode)
t.os.replace, t._write = commit, journal
t.apply(p, target_ref='synthetic-device', backup_directory=backup, authorize=authorize, exclusive_access=True)
"""
        result = subprocess.run([sys.executable, '-B', '-c', producer,
                                 str(ROOT / 'skills/claude-guardian/scripts'), str(self.target),
                                 str(self.backups), phase], capture_output=True, timeout=15)
        self.assertEqual(result.returncode, {'prepared': 71, 'renamed': 72, 'journal': 73}[phase], result.stderr)
        self.batch = list(self.backups.iterdir())[0]
        self.receipt_path = self.batch / 'prepared.json'
        self.receipt = json.loads(self.receipt_path.read_text())

    def test_backup_path_budget_blocks_unreopenable_generated_records(self):
        overhead = len('/' + '0' * 32 + '/restore-' + '0' * 32 + '.prepared.json')
        too_long = '/tmp/' + '/'.join(['x' * 100] * 40)
        self.assertLessEqual(len(too_long), 4096)
        self.assertGreater(len(too_long) + overhead, 4096)
        calls = []
        with self.assertRaisesRegex(t.TransactionError, '^UNSAFE_PATH$'):
            t.apply(self.plan, target_ref='synthetic-device', backup_directory=too_long,
                    exclusive_access=True, authorize=lambda *args: calls.append(args) or True)
        self.assertEqual(calls, [])
        self.assertEqual(self.target.read_bytes(), b'original synthetic bytes')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux long-path temporary fixture')
    def test_maximum_generated_journal_path_is_reopenable(self):
        overhead = len('/' + '0' * 32 + '/restore-' + '0' * 32 + '.prepared.json')
        desired = 4096 - overhead
        path = self.root / 'deep'
        path.mkdir(mode=0o700)
        while len(str(path)) < desired:
            remaining = desired - len(str(path))
            if remaining == 1:
                self.fail('fixture cannot make one-character component including slash')
            length = min(100, remaining - 1)
            if remaining - length - 1 == 1:
                length -= 1
            path = path / ('d' * length)
            path.mkdir(mode=0o700)
        self.assertEqual(len(str(path)), desired)
        self.backups = path
        self.interrupted_apply()
        result = self.restore()
        witness_path = self.batch / ('restore-' + result['attempt_id'] + '.prepared.json')
        self.assertEqual(len(str(witness_path)), 4096)
        # Linux pathname syscalls count the NUL against PATH_MAX. The core opens
        # each component descriptor-relatively, so its explicit 4096 API bound works.
        with t._directory(str(self.batch)) as fd:
            witness, _ = t._document_file(fd, witness_path.name)
        observation = t.reconcile(witness, receipt_path=str(witness_path), target_ref='synthetic-device',
                                  target_path=str(self.target), backup_batch=str(self.batch))
        self.assertEqual(observation['classification'], 'restored_candidate_observed')

    @unittest.skipUnless(sys.platform.startswith('linux'), 'Linux descriptor-relative Unicode budget fixture')
    def test_future_journal_envelope_budget_rejected_before_authorization(self):
        def branch(prefix, characters):
            with t._directory(str(self.root)) as rootfd:
                os.mkdir(prefix, 0o700, dir_fd=rootfd)
                fd = os.open(prefix, os.O_RDONLY | os.O_DIRECTORY, dir_fd=rootfd)
            parts = [prefix]
            try:
                while characters:
                    count = min(characters, 70)
                    part = '\u3042' * count
                    characters -= count
                    os.mkdir(part, 0o700, dir_fd=fd)
                    next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY, dir_fd=fd)
                    os.close(fd); fd = next_fd; parts.append(part)
                return str(self.root) + '/' + '/'.join(parts)
            finally:
                os.close(fd)
        target = branch('unicode-target', 3800) + '/synthetic'
        with t._parent(target) as (fd, name):
            t._write(fd, name, b'original')
        plan = t.plan(target, b'x' * t.MAX_BYTES, 'synthetic-device')
        def estimate(characters):
            parts = ['\u3042' * min(70, characters - i) for i in range(0, characters, 70)]
            backup = str(self.root) + '/unicode-backup/' + '/'.join(parts)
            staged = dict(plan['before'], sha256=plan['after_sha256'], size=t.MAX_BYTES)
            record = {'schema_version': 'exact-file-recovery/2', 'plan': plan,
                      'backup_directory': backup, 'batch': '0' * 32, 'state': 'prepared',
                      'applied_snapshot': None,
                      'batch_identity': [plan['before']['device'], plan['before']['inode']],
                      'replacement': {'name': '.guardian-stage-' + '0' * 32, 'snapshot': staged}}
            return len(json.dumps(record, sort_keys=True).encode())
        characters = max(1, (t.MAX_DOCUMENT - 100 - estimate(0)) // 6)
        characters -= max(0, (estimate(characters) - (t.MAX_DOCUMENT - 100) + 5) // 6)
        self.assertLess(estimate(characters), t.MAX_DOCUMENT)
        backup = branch('unicode-backup', characters)
        approvals = []
        with self.assertRaisesRegex(t.TransactionError, '^INVALID_DOCUMENT$'):
            t.apply(plan, target_ref='synthetic-device', backup_directory=backup,
                    exclusive_access=True, authorize=lambda *args: approvals.append(args) or True)
        self.assertEqual(approvals, [])
        with t._parent(target) as (fd, name):
            self.assertEqual(t._read(fd, name)[0], b'original')
        with t._directory(backup) as fd:
            self.assertEqual(os.listdir(fd), [])


if __name__ == '__main__':
    unittest.main()
