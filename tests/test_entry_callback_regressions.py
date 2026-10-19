"""Entry revalidation using owned disposable files and synthetic hosts only.

Callbacks model a trusted host refreshing a current declaration while an
operation is pending. They do not replace authorization or native evidence.
No production adapter, device configuration or network transport is used.
"""
from contextlib import contextmanager
import io
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import test_cleanup_cli as cleanup_fixtures
import test_repair_cli as review_fixtures
import test_repair_execution as repair_fixtures


@unittest.skipUnless(os.name == 'posix', 'POSIX disposable-fixture tests only')
class EntryCallbackRegressions(unittest.TestCase):
    def fixture(self, cls):
        fixture = cls()
        fixture.setUp()
        self.addCleanup(fixture.doCleanups)
        return fixture

    @staticmethod
    def quarantine_args(fixture, digest):
        return ['quarantine', '--plan-file', str(fixture.planfile),
                '--expected-plan-digest', digest]

    @staticmethod
    def plan_args(fixture):
        return ['plan', '--scope', str(fixture.scopefile),
                '--plan-output', str(fixture.planfile)]

    def test_final_before_commit_withdrawal_never_changes_target(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        fixture.retained()
        calls = []

        def check():
            calls.append(None)
            # Initial admission, apply admission, then final before_commit.
            if len(calls) == 3:
                fixture.entry['route']['state'] = 'withdrawn'

        with repair_fixtures.synthetic_adapter(check):
            with self.assertRaisesRegex(repair_fixtures.e.tx.TransactionError,
                                        '^ENVIRONMENT_ENTRY_CHANGED$'):
                repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(len(calls), 3)
        self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)

    def test_post_write_withdrawal_reports_recovery_instead_of_success(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        fixture.retained()
        calls = []

        def check():
            calls.append(None)
            if len(calls) == 4:
                fixture.entry['route']['state'] = 'withdrawn'

        with repair_fixtures.synthetic_adapter(check):
            with self.assertRaisesRegex(repair_fixtures.e.tx.TransactionError,
                                        '^ENVIRONMENT_ENTRY_CHANGED$') as error:
                repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(len(calls), 4)
        self.assertNotEqual(fixture.target.read_bytes(), repair_fixtures.RAW)
        self.assertIsNotNone(error.exception.recovery_id)
        self.assertTrue((fixture.backups / error.exception.recovery_id).is_dir())

    def test_native_context_exit_withdrawal_reports_recovery(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        fixture.retained()

        @contextmanager
        def session(document):
            yield lambda: None
            fixture.entry['route']['state'] = 'withdrawn'

        with patch.object(repair_fixtures.e, '_native_session', session):
            with self.assertRaisesRegex(repair_fixtures.e.tx.TransactionError,
                                        '^ENVIRONMENT_ENTRY_CHANGED$') as error:
                repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(fixture.entry['route']['state'], 'withdrawn')
        self.assertNotEqual(fixture.target.read_bytes(), repair_fixtures.RAW)
        self.assertIsNotNone(error.exception.recovery_id)
        self.assertTrue((fixture.backups / error.exception.recovery_id).is_dir())

    def test_extra_review_cancellation_cannot_withdraw_before_target_read(self):
        fixture = self.fixture(review_fixtures.RepairCLI)
        prepared = fixture.prepare()
        calls = []

        def cancelled():
            calls.append(None)
            if len(calls) == 2:
                fixture.entry['route']['state'] = 'withdrawn'
            return False

        with patch.object(review_fixtures.r, '_read_source',
                          side_effect=AssertionError('target read')):
            with self.assertRaisesRegex(review_fixtures.r.RepairError,
                                        '^ENVIRONMENT_ENTRY_CHANGED$'):
                prepared.recheck_review(cancelled=cancelled)
        self.assertEqual(len(calls), 2)
        self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)

    def test_cleanup_plan_verify_withdrawal_precedes_scan(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        verify = fixture.host.verify

        def check(*args):
            result = verify(*args)
            fixture.entry['route']['state'] = 'withdrawn'
            return result

        fixture.host.verify = check
        with patch.object(cleanup_fixtures.cli.core, '_scan',
                          side_effect=AssertionError('target scan')):
            code, result = fixture.run_cli(self.plan_args(fixture))
        self.assertNotEqual(code, 0, result)
        self.assertEqual(fixture.entry['route']['state'], 'withdrawn')
        self.assertFalse(fixture.planfile.exists())
        self.assertTrue((fixture.base / 'app').is_dir())

    def test_cleanup_quarantine_final_verify_withdrawal_precedes_move(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        digest = fixture.planned()
        verify = fixture.host.verify
        calls = []

        def check(*args):
            result = verify(*args)
            calls.append(None)
            # The seventh verification is the final host check before rename.
            if len(calls) == 7:
                fixture.entry['route']['state'] = 'withdrawn'
            return result

        fixture.host.verify = check
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertNotEqual(code, 0, result)
        self.assertEqual(len(calls), 7)
        self.assertEqual(result['moved_count'], 0)
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')

    def test_cleanup_plan_save_approval_withdrawal_never_saves(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        approve = fixture.host.approve

        def check(operation, *args):
            result = approve(operation, *args)
            if operation == 'save_plan':
                fixture.entry['route']['state'] = 'withdrawn'
            return result

        fixture.host.approve = check
        code, result = fixture.run_cli(self.plan_args(fixture))
        self.assertNotEqual(code, 0, result)
        self.assertEqual(fixture.entry['route']['state'], 'withdrawn')
        self.assertFalse(fixture.planfile.exists())
        self.assertTrue((fixture.base / 'app').is_dir())

    def test_cleanup_postwrite_withdrawal_reports_recovery(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        digest = fixture.planned()
        verify = fixture.host.verify
        calls = []

        def check(*args):
            result = verify(*args)
            calls.append(None)
            if len(calls) == 8:
                fixture.entry['route']['state'] = 'withdrawn'
            return result

        fixture.host.verify = check
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertNotEqual(code, 0, result)
        self.assertEqual(len(calls), 8)
        self.assertFalse((fixture.base / 'app').exists())
        self.assertEqual(result['moved_count'], 1)
        self.assertEqual(result['stage'], 'after_move_verified')
        self.assertIsNotNone(result['recovery_id'])

    def test_cleanup_context_exit_withdrawal_reports_recovery(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        digest = fixture.planned()
        exclusive = fixture.host.exclusive

        @contextmanager
        def context(*args):
            with exclusive(*args):
                yield
            fixture.entry['route']['state'] = 'withdrawn'

        fixture.host.exclusive = context
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertNotEqual(code, 0, result)
        self.assertEqual(fixture.entry['route']['state'], 'withdrawn')
        self.assertFalse((fixture.base / 'app').exists())
        self.assertEqual(result['moved_count'], 1)
        self.assertEqual(result['stage'], 'after_move_verified')
        self.assertIsNotNone(result['recovery_id'])

    def test_cleanup_recovery_stays_available_without_entry(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        digest, _ = fixture.quarantined()
        fixture.entry['route']['state'] = 'withdrawn'
        # The fixture deliberately supplies no entry for recovery commands.
        code, result = fixture.run_cli([
            'reconcile', '--plan-file', str(fixture.planfile),
            '--expected-plan-digest', digest,
            '--receipt-output', str(fixture.receiptfile)])
        self.assertEqual(code, 0, result)
        code, result = fixture.run_cli([
            'restore', '--receipt-file', str(fixture.receiptfile),
            '--expected-receipt-digest', result['document_digest']])
        self.assertEqual(code, 0, result)
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
        self.assertEqual((fixture.base / 'protected/keep').read_bytes(), b'protected')

    def test_vps_quarantine_is_blocked_but_read_only_plan_is_available(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        fixture.entry['route']['choice'] = 'vps'
        fixture.entry['targets'][0]['role'] = 'vps'
        digest = fixture.planned()
        fixture.host.events.clear()
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertEqual(code, 2, result)
        self.assertEqual(result['code'], 'VPS_QUARANTINE_OUTSIDE_BASIC_CHECK_SCOPE')
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
        self.assertEqual(list((fixture.base / 'quarantine').iterdir()), [])
        self.assertFalse(any(event[:2] == ('approve', 'quarantine')
                             for event in fixture.host.events))

    def test_local_cleanup_needs_no_purchased_or_selected_network_resource(self):
        for resource_state in ('none', 'unknown'):
            with self.subTest(resource_state=resource_state):
                fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
                if resource_state == 'unknown':
                    fixture.entry['network'].update(
                        possession='unknown', selection='unknown',
                        configuration='unknown', path='unknown')
                self.assertEqual(fixture.entry['route']['choice'], 'local')
                self.assertEqual(fixture.entry['network']['possession'], resource_state)
                digest = fixture.planned()
                code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
                self.assertEqual(code, 0, result)
                self.assertEqual(result['state'], 'quarantined')
                self.assertFalse((fixture.base / 'app').exists())
                self.assertEqual((fixture.base / 'backup/data').read_bytes(), b'synthetic')
                self.assertEqual((fixture.base / 'protected/keep').read_bytes(), b'protected')

    def test_explicit_withdrawn_entry_cannot_block_existing_cleanup_recovery(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        digest, _ = fixture.quarantined()
        fixture.entry['route']['state'] = 'withdrawn'

        def run(args):
            output = io.StringIO()
            code = cleanup_fixtures.cli.main(args, host=fixture.host, stdout=output,
                                            entry_request=fixture.entry)
            result = json.loads(output.getvalue())
            self.assertEqual(code, 0, result)
            return result

        reconciled = run([
            'reconcile', '--plan-file', str(fixture.planfile),
            '--expected-plan-digest', digest,
            '--receipt-output', str(fixture.receiptfile)])
        restored = run([
            'restore', '--receipt-file', str(fixture.receiptfile),
            '--expected-receipt-digest', reconciled['document_digest']])
        self.assertEqual(restored['state'], 'restored')
        self.assertEqual(fixture.entry['route']['state'], 'withdrawn')
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
        self.assertEqual((fixture.base / 'backup/data').read_bytes(), b'synthetic')
        self.assertEqual((fixture.base / 'protected/keep').read_bytes(), b'protected')


if __name__ == '__main__':
    unittest.main()
