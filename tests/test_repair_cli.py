"""Repair entry-point tests use only private synthetic temporary fixtures."""
from copy import deepcopy
import json
import os
from pathlib import Path
import pickle
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import repair_cli as r
from test_config_edit_plan import RAW, inputs


@unittest.skipUnless(os.name == 'posix', 'POSIX exact-file preflight only')
class RepairCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'extension.yaml'
        self.target.write_bytes(RAW)
        self.target.chmod(0o600)
        request, binding = inputs()
        self.document = {'schema_version': r.SCHEMA, 'remedy_request': request, 'binding': binding}
        self.request = self.root / 'request.json'
        self.save()

    def save(self):
        self.request.write_text(json.dumps(self.document))
        self.request.chmod(0o600)

    def prepare(self, **kwargs):
        return r.preflight(str(self.request), str(self.target), 'mac-a', **kwargs)

    def run_cli(self, command='preflight', *extra):
        return subprocess.run([sys.executable, '-B', str(SCRIPTS / 'repair_cli.py'), command,
                               '--request', str(self.request), '--target-path', str(self.target),
                               '--target-ref', 'mac-a', *extra], capture_output=True,
                              text=True, timeout=10)

    def tree(self):
        return {p.name: p.read_bytes() for p in self.root.iterdir()}

    def matching_snapshot(self, *, mixed=False):
        raw = RAW.replace(b'DOMAIN,example.test,Old', b'DOMAIN,example.test,approved-group')
        request, binding = inputs(raw)
        binding['rules']['rule-a']['expected'] = 'DOMAIN,example.test,approved-group'
        if mixed:
            request['intent']['rule_refs'].append('rule-b')
            binding['rules']['rule-b'] = {'index': 1, 'expected': 'DOMAIN-SUFFIX,example.org,Old'}
        self.document = {'schema_version': r.SCHEMA, 'remedy_request': request, 'binding': binding}
        self.target.write_bytes(raw)
        self.save()
        return raw

    def test_matching_snapshot_has_no_transaction_plan_or_receipt(self):
        self.matching_snapshot()
        before = self.tree()
        with patch.object(r.tx, 'plan', side_effect=AssertionError('action plan')), \
                patch.object(r.tx, 'apply', side_effect=AssertionError('apply')):
            prepared = self.prepare()
            self.assertIsNone(prepared._plan)
            report = prepared.public_report()
            review = prepared.private_review()
        self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
        self.assertEqual(report['changed_rules'], 0)
        self.assertEqual(report['matched_rules'], 1)
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['native_acceptance'], 'not_run')
        self.assertEqual(report['effective_routing'], 'not_run')
        self.assertEqual(review['selected_rule_changes'], [])
        self.assertEqual(review['matched_rule_refs'], ['rule-a'])
        self.assertEqual(review['policy_token_edits'], [])
        for field in ('plan_digest', 'retained_plan_digest', 'action_id', 'recovery_id', 'receipt_digest'):
            self.assertNotIn(field, report)
            self.assertNotIn(field, review)
        self.assertNotIn('ACTION_AUTHORIZATION_PENDING', report['blockers'])
        self.assertEqual(self.tree(), before)

    def test_matching_cli_plan_does_not_access_or_create_artifact_destinations(self):
        self.matching_snapshot()
        before = self.tree()
        # Neither destination exists. No-change observation must not open them.
        artifact = self.root / 'absent' / 'plan.json'
        backup = self.root / 'absent-backups'
        for command in ('preflight', 'diff', 'plan'):
            extra = [] if command == 'preflight' else ['--private-review']
            if command == 'plan':
                extra.extend(['--plan-file', str(artifact), '--backup-directory', str(backup)])
            result = self.run_cli(command, *extra)
            self.assertEqual(result.returncode, 0, result.stderr)
            report = json.loads(result.stdout.splitlines()[-1])
            self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
            self.assertEqual(report['artifact_write'], 'not_created_no_change')
            self.assertNotIn('retained_plan_digest', result.stdout)
            self.assertNotIn('action_id', result.stdout)
            self.assertFalse(artifact.exists())
            self.assertFalse(backup.exists())
            self.assertEqual(self.tree(), before)

    def test_mixed_private_review_only_lists_real_change_and_full_request_digest(self):
        raw = self.matching_snapshot(mixed=True)
        prepared = self.prepare()
        report, review = prepared.public_report(), prepared.private_review()
        self.assertEqual(report['changed_rules'], 1)
        self.assertEqual(report['matched_rules'], 1)
        self.assertEqual([item['rule_ref'] for item in review['selected_rule_changes']], ['rule-b'])
        self.assertEqual(review['matched_rule_refs'], ['rule-a'])
        self.assertEqual(prepared._request_digest, r.tx.digest(self.document))
        proposed = prepared._candidate.private_material()['candidate_bytes']
        self.assertEqual(proposed, raw.replace(b'DOMAIN-SUFFIX,example.org,Old',
                                              b'DOMAIN-SUFFIX,example.org,approved-group'))
        self.assertEqual(self.target.read_bytes(), raw)

    def test_matching_report_rechecks_changed_request_and_target(self):
        for change in ('request', 'bytes', 'inode', 'parent'):
            with self.subTest(change=change):
                self.matching_snapshot()
                prepared = self.prepare()
                if change == 'request':
                    self.document['remedy_request']['route_ref'] = 'changed-route'
                    self.save()
                    expected = 'REQUEST_CHANGED'
                elif change == 'bytes':
                    self.target.write_bytes(self.target.read_bytes() + b'# later edit\n')
                    expected = 'STALE_FILE'
                elif change == 'inode':
                    replacement = self.root / 'replacement'
                    replacement.write_bytes(self.target.read_bytes())
                    replacement.chmod(0o600)
                    replacement.replace(self.target)
                    expected = 'STALE_FILE'
                else:
                    read = r._read_source
                    def changed_parent(path):
                        raw, source = read(path)
                        if path == str(self.target):
                            source['parent_identity'] = [0, 0]
                        return raw, source
                    with patch.object(r, '_read_source', side_effect=changed_parent):
                        with self.assertRaisesRegex(r.RepairError, '^STALE_FILE$'):
                            prepared.public_report()
                    continue
                for render in (prepared.public_report, prepared.private_review):
                    with self.assertRaisesRegex(r.RepairError, '^' + expected + '$'):
                        render()

    def test_matching_report_keeps_original_cancel_and_deadline(self):
        self.matching_snapshot()
        cancelled = False
        prepared = self.prepare(cancelled=lambda: cancelled)
        cancelled = True
        with patch.object(r, '_load_request', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(r.RepairError, '^CANCELLED$'):
                prepared.public_report()
        prepared = self.prepare()
        with patch.object(r.time, 'monotonic', return_value=prepared._deadline + 1), \
                patch.object(r, '_load_request', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(r.RepairError, '^DEADLINE_EXCEEDED$'):
                prepared.private_review()

    def test_matching_preflight_rechecks_target_after_compilation(self):
        self.matching_snapshot()
        compile = r.edits.compile_edit_plan
        def changed(*args):
            result = compile(*args)
            self.target.write_bytes(self.target.read_bytes() + b'# after compile\n')
            return result
        with patch.object(r.edits, 'compile_edit_plan', side_effect=changed), \
                patch.object(r.tx, 'plan', side_effect=AssertionError('plan')):
            with self.assertRaisesRegex(r.RepairError, '^STALE_FILE$'):
                self.prepare()

    def test_all_commands_nonmutating_execute_precisely_blocked(self):
        before = self.tree()
        for command in ('plan', 'preflight', 'diff'):
            result = self.run_cli(command)
            self.assertEqual(result.returncode, 2 if command == 'execute' else 0, result.stderr)
            value = json.loads(result.stdout)
            self.assertFalse(value['apply_supported'])
            self.assertEqual(value['effective_routing'], 'not_run')
            self.assertIn('NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED', value['blockers'])
            self.assertEqual(value['changed_rules'], 1)
            if command == 'execute':
                self.assertEqual(value['code'], 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE')
            self.assertEqual(self.tree(), before)

    def test_reports_redacted_private_diff_exact(self):
        prepared = self.prepare()
        result = json.dumps(prepared.public_report()) + repr(prepared)
        for secret in ('secret-SENTINEL', 'example.test', 'approved-group', str(self.root)):
            self.assertNotIn(secret, result)
        review = prepared.private_review()
        delta = review['policy_token_edits'][0]
        self.assertEqual(RAW[delta['start']:delta['end']], b'Old')
        self.assertEqual(delta['after'], 'approved-group')
        self.assertNotIn('secret-SENTINEL', json.dumps(review))
        with self.assertRaises(TypeError):
            pickle.dumps(prepared)
        with self.assertRaises(TypeError):
            json.dumps(prepared)

    def test_explicit_private_diff_and_approval_flags(self):
        result = self.run_cli('diff', '--private-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        private = json.loads(result.stdout.splitlines()[0])
        self.assertEqual(private['selected_rule_changes'][0]['selector'], 'DOMAIN,example.test')
        self.assertNotIn('secret-SENTINEL', result.stdout)
        for flag in ('--yes', '--approved', '--native-pass'):
            result = self.run_cli('execute', flag)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(flag, result.stderr)

    def test_argument_errors_do_not_echo_private_values(self):
        for extra in (('--unknown', 'private-SENTINEL'),
                      ('--max-seconds', 'private-SENTINEL')):
            result = self.run_cli('preflight', *extra)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('private-SENTINEL', result.stderr + result.stdout)
            self.assertEqual(json.loads(result.stderr)['code'], 'INVALID_ARGUMENTS')

    def test_retained_private_review_binds_exact_artifact(self):
        backup = self.root / 'backups'
        backup.mkdir(mode=0o700)
        artifact = self.root / 'plan.json'
        result = self.run_cli('plan', '--plan-file', str(artifact),
                              '--backup-directory', str(backup), '--private-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        review, report = map(json.loads, result.stdout.splitlines())
        document = json.loads(artifact.read_text())
        digest = r.tx.digest(document)
        self.assertEqual(review['retained_plan_digest'], digest)
        self.assertEqual(report['retained_plan_digest'], digest)
        self.assertEqual(review['backup_directory'], str(backup))
        self.assertEqual(review['expires_at'], document['plan']['expires_at'])
        self.assertEqual(review['action_id'], document['plan']['action_id'])
        self.assertEqual(report['artifact_write'], 'private_plan_retained')
        self.assertEqual(self.target.read_bytes(), RAW)
        result = self.run_cli('execute', '--plan-file', str(artifact),
                              '--backup-directory', str(backup), '--plan-digest', digest)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['code'], 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE')
        self.assertEqual(list(backup.iterdir()), [])

    def test_json_cannot_grant_approval(self):
        self.document['approved'] = True
        self.save()
        with self.assertRaisesRegex(r.RepairError, '^INVALID_REPAIR_REQUEST$'):
            self.prepare()

    def test_target_mismatch_before_target_read(self):
        with patch.object(r.tx, '_read', side_effect=AssertionError('target read')):
            with self.assertRaisesRegex(r.RepairError, '^TARGET_MISMATCH$'):
                r.preflight(str(self.request), str(self.target), 'different')

    def test_stale_original_rejected(self):
        self.target.write_bytes(RAW + b'# later edit\n')
        with self.assertRaisesRegex(r.edits.EditPlanError, '^SNAPSHOT_REVISION_MISMATCH$'):
            self.prepare()

    def test_request_changed_during_plan(self):
        original = r.tx.plan
        def change(*args, **kwargs):
            plan = original(*args, **kwargs)
            self.document['binding']['group_name'] = 'changed'
            self.save()
            return plan
        with patch.object(r.tx, 'plan', side_effect=change):
            with self.assertRaisesRegex(r.RepairError, '^REQUEST_CHANGED$'):
                self.prepare()

    def test_same_bytes_replaced_during_plan(self):
        original = r.tx.plan
        def change(*args, **kwargs):
            other = self.root / 'replacement'
            other.write_bytes(RAW)
            other.chmod(0o600)
            other.replace(self.target)
            return original(*args, **kwargs)
        with patch.object(r.tx, 'plan', side_effect=change):
            with self.assertRaisesRegex(r.RepairError, '^STALE_FILE$'):
                self.prepare()

    def test_cancellation_and_deadline_no_reads(self):
        with patch.object(r, '_load_request', side_effect=AssertionError('read')):
            with self.assertRaisesRegex(r.RepairError, '^CANCELLED$'):
                self.prepare(cancelled=lambda: True)
            with patch.object(r.time, 'monotonic', side_effect=[0, 31]):
                with self.assertRaisesRegex(r.RepairError, '^DEADLINE_EXCEEDED$'):
                    self.prepare()
        for invalid in (True, 0, -1, float('nan'), float('inf'), 61):
            with self.assertRaisesRegex(r.RepairError, '^INVALID_DEADLINE$'):
                self.prepare(max_seconds=invalid)

    def test_cancellation_after_compile(self):
        original = r.edits.compile_edit_plan
        cancelled = False
        def compile(*args):
            nonlocal cancelled
            result = original(*args)
            cancelled = True
            return result
        with patch.object(r.edits, 'compile_edit_plan', side_effect=compile):
            with self.assertRaisesRegex(r.RepairError, '^CANCELLED$'):
                self.prepare(cancelled=lambda: cancelled)

    def test_no_network_subprocess_or_write_calls(self):
        with patch('socket.socket', side_effect=AssertionError('network')), \
                patch('subprocess.Popen', side_effect=AssertionError('process')), \
                patch.object(r.tx, 'apply', side_effect=AssertionError('apply')), \
                patch.object(r.tx, 'rollback', side_effect=AssertionError('rollback')):
            self.prepare()

    def test_link_target_and_unsafe_request_rejected(self):
        other = self.root / 'alias'
        other.symlink_to(self.target)
        with self.assertRaises(r.tx.TransactionError):
            r.preflight(str(self.request), str(other), 'mac-a')
        self.request.chmod(0o644)
        with self.assertRaisesRegex(r.tx.TransactionError, '^UNSAFE_RECEIPT_FILE$'):
            self.prepare()

    def test_unsupported_template_keeps_blocker(self):
        self.document['remedy_request']['template'] = 'tun-rule'
        self.save()
        with self.assertRaisesRegex(r.edits.EditPlanError, '^SEMANTIC_PLAN_BLOCKED$'):
            self.prepare()


if __name__ == '__main__':
    unittest.main()
