"""Prepared recovery through real CLI subprocesses and synthetic POSIX terminals."""
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

import test_recovery_cli as old

tx = old.tx


@unittest.skipUnless(os.name == 'posix', 'POSIX recovery only; Windows unsupported')
class PreparedRecoveryCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='guardian-prepared-cli-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.file = self.root / 'synthetic-config'
        self.file.write_bytes(b'original synthetic data')
        self.file.chmod(0o600)
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.make_transaction('committed')
        self.bound = self.reconcile()['reconciliation_digest']

    make_transaction = old.RecoveryCLI.make_transaction
    run_cli = old.RecoveryCLI.run_cli
    tree = old.RecoveryCLI.tree

    def args(self, command='reconcile'):
        result = old.RecoveryCLI.args(self, command)
        if command == 'restore-prepared' and self.bound is not None:
            result += ['--reconciliation-digest', self.bound]
        if getattr(self, 'failure_runner', None):
            result = [sys.executable, '-B', '-c', self.failure_runner, str(old.SCRIPTS)] + result[3:]
        return result

    def reconcile(self):
        result = self.run_cli('reconcile')
        self.assertEqual(result.returncode, 0, result.stderr)
        return json.loads(result.stdout)

    def terminal(self, responses, **kwargs):
        return old.RecoveryCLI.terminal(self, responses, command='restore-prepared', **kwargs)

    def approvals(self):
        return ['EXCLUSIVE ACCESS ESTABLISHED', 'RESTORE_PREPARED ' + self.bound,
                'RESTORE_PREPARED ' + self.bound]

    def rewrite_receipt(self):
        self.receipt.write_text(json.dumps(self.document), encoding='utf-8')
        self.digest = tx.digest(self.document)

    def test_read_only_reconcile_pins_complete_operation_without_bytes(self):
        before = self.tree()
        result = self.reconcile()
        self.assertEqual(result['classification'], 'prepared_candidate_observed')
        self.assertTrue(result['restore_candidate'])
        observation = tx.reconcile(self.document, receipt_path=str(self.receipt),
            target_ref='synthetic-device', target_path=str(self.file), backup_batch=str(self.batch))
        self.assertEqual(result['reconciliation_digest'], tx.digest({
            'recovery_digest': self.digest, 'observation': observation}))
        self.assertEqual(self.reconcile(), result)
        self.assertEqual(self.tree(), before)
        output = json.dumps(result)
        for secret in ('original synthetic data', 'new synthetic data',
                       base64.b64encode(b'new synthetic data').decode(), 'proposed_base64'):
            self.assertNotIn(secret, output)
        self.assertEqual(result['application_effect'], 'not_tested')
        self.assertEqual(result['network_effect'], 'not_tested')

    def test_independent_terminal_separately_restores_without_applied_receipt(self):
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 0, output)
        self.assertEqual(self.file.read_bytes(), b'original synthetic data')
        self.assertEqual(self.file.stat().st_mode & 0o777, 0o600)
        self.assertTrue(self.receipt.exists())
        self.assertFalse((self.batch / 'applied.json').exists())
        self.assertEqual(len(list(self.batch.glob('restore-*.prepared.json'))), 1)
        self.assertEqual(len(list(self.batch.glob('rollback-*.json'))), 1)
        self.assertIn('"state": "restored"', output)
        self.assertEqual(output.count('or cancel:'), 3)

    def test_missing_stale_or_invalid_observation_digest_never_prompts(self):
        before = self.tree()
        for digest, code in ((None, 'EXPECTED_RECONCILIATION_REQUIRED'),
                             ('0' * 64, 'RECONCILIATION_STALE'),
                             ('bad', 'INVALID_EXPECTED_DIGEST')):
            self.bound = digest
            result = self.run_cli('restore-prepared')
            self.assertEqual(result.returncode, 2)
            self.assertIn(code, result.stderr)
            self.assertNotIn('or cancel:', result.stdout)
            self.assertEqual(self.tree(), before)

    def test_pipes_yes_override_and_old_rollback_do_not_authorize_restore(self):
        before = self.tree()
        result = self.run_cli('restore-prepared', input='\n'.join(self.approvals()) + '\n')
        self.assertIn('INTERACTIVE_TERMINAL_REQUIRED', result.stderr)
        self.assertNotEqual(self.run_cli('restore-prepared', ('--yes',)).returncode, 0)
        for command in ('preview', 'rollback'):
            self.assertIn('RECOVERY_REQUIRES_RECONCILIATION', self.run_cli(command).stderr)
        code, output = self.terminal(['EXCLUSIVE ACCESS ESTABLISHED', 'ROLLBACK ' + self.digest])
        self.assertEqual(code, 2, output)
        self.assertEqual(self.tree(), before)

    def test_cancel_each_fresh_prompt_preserves_target_and_private_batch(self):
        for index in range(3):
            with self.subTest(prompt=index):
                before = self.tree()
                code, output = self.terminal(self.approvals()[:index] + ['cancel'])
                self.assertEqual(code, 2, output)
                self.assertEqual(self.tree(), before)
                self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_timeout_and_queued_future_approvals_cannot_commit(self):
        before = self.tree()
        code, output = self.terminal([None], extra=('--approval-timeout', '1'))
        self.assertEqual(code, 2, output)
        self.assertIn('APPROVAL_TIMEOUT', output)
        future = ('RESTORE_PREPARED ' + self.bound + '\n') * 2
        code, output = self.terminal(['EXCLUSIVE ACCESS ESTABLISHED', None],
            queued_input=future, extra=('--approval-timeout', '1'))
        self.assertEqual(code, 2, output)
        self.assertNotIn('Approval 2/2', output)
        self.assertEqual(self.tree(), before)

    def test_explicit_scope_and_digest_rejected_before_embedded_reads(self):
        before = self.tree()
        for option, value, code in (
            ('--target-path', str(self.root / 'absent'), 'TARGET_MISMATCH'),
            ('--target-ref', 'other-device', 'TARGET_MISMATCH'),
            ('--backup-batch', str(self.root / 'absent'), 'BACKUP_SCOPE_MISMATCH'),
            ('--receipt-digest', '0' * 64, 'RECEIPT_DIGEST_MISMATCH')):
            result = self.run_cli('reconcile', (option, value))
            self.assertEqual(result.returncode, 2)
            self.assertIn(code, result.stderr)
        self.assertEqual(self.tree(), before)
        for command in ('reconcile', 'restore-prepared'):
            result = subprocess.run([sys.executable, '-B', str(old.CLI), command,
                '--receipt', str(self.receipt)], capture_output=True, text=True, timeout=10)
            self.assertIn('EXPLICIT_SCOPE_REQUIRED', result.stderr)
            self.assertEqual(self.tree(), before)

    def test_target_edit_after_reconcile_is_stale_and_never_prompts(self):
        self.file.write_bytes(b'later user edit')
        before = self.tree()
        result = self.run_cli('restore-prepared')
        self.assertIn('RECONCILIATION_STALE', result.stderr)
        self.assertNotIn('or cancel:', result.stdout)
        self.assertEqual(self.tree(), before)
        self.assertEqual(self.reconcile()['classification'], 'conflict')

    def test_same_content_inode_substitution_after_reconcile_is_stale(self):
        for selected in (self.file, self.receipt, self.batch / 'original.bin'):
            with self.subTest(path=selected.name):
                replacement = selected.with_name('substitute')
                replacement.write_bytes(selected.read_bytes())
                replacement.chmod(selected.stat().st_mode & 0o777)
                os.replace(replacement, selected)
                before = self.tree()
                result = self.run_cli('restore-prepared')
                self.assertIn('RECONCILIATION_STALE', result.stderr)
                self.assertNotIn('or cancel:', result.stdout)
                self.assertEqual(self.tree(), before)
                # Keep each next assertion independently bound to the latest read.
                self.bound = self.reconcile()['reconciliation_digest']

    def test_target_edit_during_each_confirmation_is_preserved(self):
        for index in range(3):
            with self.subTest(prompt=index):
                if index:
                    self.setUp()
                def edit(prompt):
                    if prompt == index:
                        self.file.write_bytes(b'later user edit')
                code, output = self.terminal(self.approvals(), on_prompt=edit)
                self.assertEqual(code, 2, output)
                self.assertEqual(self.file.read_bytes(), b'later user edit')
                self.assertFalse(list(self.batch.glob('rollback-*.json')))
                self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_receipt_and_backup_edits_during_final_confirmation_are_preserved(self):
        for selected_name in ('prepared.json', 'original.bin'):
            with self.subTest(path=selected_name):
                if selected_name == 'original.bin':
                    self.setUp()
                selected = self.batch / selected_name
                def edit(prompt):
                    if prompt == 2:
                        selected.write_bytes(b'changed private material')
                code, output = self.terminal(self.approvals(), on_prompt=edit)
                self.assertEqual(code, 2, output)
                self.assertIn('AUTHORIZATION_CANCELLED', output)
                self.assertEqual(self.file.read_bytes(), b'new synthetic data')
                self.assertEqual(selected.read_bytes(), b'changed private material')
                self.assertFalse(list(self.batch.glob('rollback-*.json')))

    def test_legacy_prepared_is_observable_but_never_restorable(self):
        self.document['schema_version'] = 'exact-file-recovery/1'
        self.document.pop('replacement')
        self.document.pop('batch_identity')
        self.rewrite_receipt()
        result = self.reconcile()
        self.assertEqual(result['classification'], 'legacy_identity_unproven')
        self.bound = result['reconciliation_digest']
        before = self.tree()
        result = self.run_cli('restore-prepared')
        self.assertIn('LEGACY_RECOVERY_IDENTITY_UNPROVEN', result.stderr)
        self.assertNotIn('or cancel:', result.stdout)
        self.assertEqual(self.tree(), before)

    def test_precommit_crash_and_applied_records_are_read_only_in_new_path(self):
        for crash, classification in (('prepared', 'original_observed'), ('none', 'applied_observed')):
            with self.subTest(crash=crash):
                self.backups = self.root / ('backups-' + crash)
                self.backups.mkdir(mode=0o700)
                self.file.write_bytes(b'original synthetic data')
                self.make_transaction(crash)
                result = self.reconcile()
                self.assertEqual(result['classification'], classification)
                self.bound = result['reconciliation_digest']
                before = self.tree()
                result = self.run_cli('restore-prepared')
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('or cancel:', result.stdout)
                self.assertEqual(self.tree(), before)

    def test_restoration_witness_reconciles_and_cannot_be_replayed(self):
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 0, output)
        self.receipt = next(self.batch.glob('restore-*.prepared.json'))
        self.document = json.loads(self.receipt.read_text(encoding='utf-8'))
        self.digest = tx.digest(self.document)
        result = self.reconcile()
        self.assertEqual(result['classification'], 'restored_candidate_observed')
        self.bound = result['reconciliation_digest']
        before = self.tree()
        result = self.run_cli('restore-prepared')
        self.assertIn('PREPARED_RECOVERY_REQUIRED', result.stderr)
        self.assertNotIn('or cancel:', result.stdout)
        self.assertEqual(self.tree(), before)

    def test_real_terminal_precommit_write_failure_preserves_candidate(self):
        self.failure_runner = '''
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
write = c.tx._write
def fail(fd, name, data, mode=0o600):
    if name.startswith('restore-'):
        raise OSError('synthetic witness failure')
    return write(fd, name, data, mode)
c.tx._write = fail
sys.exit(c.main(sys.argv[2:]))
'''
        before = self.tree()
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 2, output)
        self.assertIn('IO_FAILURE', output)
        self.assertEqual(output.count('or cancel:'), 3)
        self.assertEqual(self.tree(), before)
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))
        self.assertEqual(self.reconcile()['classification'], 'prepared_candidate_observed')

    def test_real_terminal_late_journal_failure_exposes_only_safe_recovery_ids(self):
        self.failure_runner = '''
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
write = c.tx._write
def fail(fd, name, data, mode=0o600):
    if name.startswith('rollback-'):
        raise OSError('synthetic private failure text must not leak')
    return write(fd, name, data, mode)
c.tx._write = fail
sys.exit(c.main(sys.argv[2:]))
'''
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 2, output)
        self.assertEqual(output.count('or cancel:'), 3)
        self.assertNotIn('synthetic private failure text', output)
        self.assertNotIn('"state": "restored"', output)
        self.assertEqual(self.file.read_bytes(), b'original synthetic data')
        error = [json.loads(line) for line in output.splitlines()
                 if line.startswith('{') and '"status": "blocked"' in line][-1]
        self.assertEqual(error['code'], 'IO_FAILURE')
        self.assertEqual(error['recovery_id'], self.batch.name)
        self.assertRegex(error['attempt_id'], '^[0-9a-f]{32}$')
        self.assertFalse(list(self.batch.glob('rollback-*.json')))
        self.receipt = self.batch / ('restore-' + error['attempt_id'] + '.prepared.json')
        self.document = json.loads(self.receipt.read_text(encoding='utf-8'))
        self.digest = tx.digest(self.document)
        before = self.tree()
        result = self.reconcile()
        self.assertEqual(result['classification'], 'restored_candidate_observed')
        self.bound = result['reconciliation_digest']
        result = self.run_cli('restore-prepared')
        self.assertIn('PREPARED_RECOVERY_REQUIRED', result.stderr)
        self.assertNotIn('or cancel:', result.stdout)
        self.assertEqual(self.tree(), before)


    def test_real_terminal_cleanup_failure_keeps_primary_error_and_retained_stage(self):
        self.failure_runner = '''
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
unlink = c.tx.os.unlink
def fail(name, *args, **kwargs):
    if name.startswith('.guardian-stage-'):
        raise OSError('synthetic cleanup failure')
    return unlink(name, *args, **kwargs)
c.tx.os.unlink = fail
sys.exit(c.main(sys.argv[2:]))
'''
        code, output = self.terminal(self.approvals()[:2] + ['cancel'])
        self.assertEqual(code, 2, output)
        self.assertIn('"code": "AUTHORIZATION_CANCELLED"', output)
        self.assertIn('"cleanup_code": "STAGING_CLEANUP_FAILED"', output)
        self.assertEqual(self.file.read_bytes(), b'new synthetic data')
        stages = list(self.root.glob('.guardian-stage-*'))
        self.assertEqual(len(stages), 1)
        self.assertEqual(stages[0].read_bytes(), b'original synthetic data')
        self.assertEqual((self.batch / 'original.bin').read_bytes(), b'original synthetic data')
        self.assertFalse(list(self.batch.glob('rollback-*.json')))

    def test_error_projection_allows_only_fixed_cleanup_codes_and_opaque_ids(self):
        # Error-projection injection only: no TTY bypass, authorization or write.
        for cleanup in ('STAGING_RETAINED', 'STAGING_CLEANUP_FAILED',
                        'DESCRIPTOR_CLOSE_FAILED', 'private cleanup detail'):
            with self.subTest(cleanup=cleanup):
                self.failure_runner = '''
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
def fail(*args, **kwargs):
    raise c.tx.TransactionError('IO_FAILURE', 'private recovery detail',
        attempt_id='private attempt detail', cleanup_code=%r)
c.tx.reconcile = fail
sys.exit(c.main(sys.argv[2:]))
''' % cleanup
                before = self.tree()
                result = self.run_cli('reconcile')
                self.assertEqual(result.returncode, 2)
                error = json.loads(result.stderr)
                if cleanup.startswith('private'):
                    self.assertNotIn('cleanup_code', error)
                else:
                    self.assertEqual(error['cleanup_code'], cleanup)
                self.assertNotIn('recovery_id', error)
                self.assertNotIn('attempt_id', error)
                self.assertNotIn('private', result.stderr.replace('retained private batch', ''))
                self.assertEqual(self.tree(), before)


if __name__ == '__main__':
    unittest.main()
