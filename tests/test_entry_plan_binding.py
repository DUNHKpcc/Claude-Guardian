"""Private retained-plan entry bindings and unchanged legacy recovery protocols.

Every operation uses an exclusively owned temporary fixture. Native admission
is synthetic. Legacy wrappers below model the old wire shape around the same
unchanged low-level transaction; they never authorize a new production action.
"""
import copy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import test_cleanup_cli as cleanup_fixtures
import test_prepared_recovery_cli as prepared_recovery_fixtures
import test_recovery_cli as recovery_fixtures
import test_repair_execution as repair_fixtures
import test_rules_repair_cli as rules_fixtures


def proxy_entry(entry):
    entry['network'] = {'possession': 'present', 'selection': 'selected',
                        'configuration': 'effective', 'path': 'explicit',
                        'resource_ref': 'resource-a'}
    entry['local_entry'] = {'kind': 'mixed', 'entry_ref': 'entry-a'}
    entry['final_egress'] = {'kind': 'proxy', 'protocol': 'socks5'}


def changed_entry(entry, change):
    current = copy.deepcopy(entry)
    if change == 'resource':
        current['network']['resource_ref'] = 'resource-b'
    elif change == 'listener':
        current['local_entry']['entry_ref'] = 'entry-b'
    elif change == 'configuration':
        current['network']['configuration'] = 'imported'
    elif change == 'route':
        target = current['targets'][0]['target_ref']
        current['route']['choice'] = 'vm'
        current['targets'] = [{'role': 'vm_host', 'target_ref': 'fixture-vm-host'},
                              {'role': 'vm_guest', 'target_ref': target}]
    else:
        raise AssertionError('unknown synthetic mutation')
    return current


@unittest.skipUnless(os.name == 'posix', 'POSIX owned temporary fixtures only')
class EntryPlanBinding(unittest.TestCase):
    def fixture(self, cls):
        fixture = cls()
        self.addCleanup(fixture.doCleanups)
        fixture.setUp()
        return fixture

    @staticmethod
    def quarantine_args(fixture, digest):
        return ['quarantine', '--plan-file', str(fixture.planfile),
                '--expected-plan-digest', digest]

    def test_repair_retains_only_private_digest_of_complete_entry(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        proxy_entry(fixture.entry)
        fixture.retained()
        document = json.loads(fixture.plan.read_text(encoding='utf-8'))
        self.assertEqual(document['schema_version'], 'guardian-retained-repair/0.3')
        self.assertEqual(document['entry_digest'], repair_fixtures.e.tx.digest(fixture.entry))
        self.assertNotIn('resource-a', fixture.plan.read_text(encoding='utf-8'))
        self.assertNotIn('entry-a', fixture.plan.read_text(encoding='utf-8'))
        with repair_fixtures.synthetic_adapter():
            result = repair_fixtures.e.execute(**fixture.arguments)
        self.assertNotIn('entry_digest', result)
        self.assertNotIn('resource-a', json.dumps(result))

    def test_repair_changed_entry_cannot_reuse_retained_plan_before_native_io(self):
        for change in ('resource', 'listener', 'configuration', 'route'):
            with self.subTest(change=change):
                fixture = self.fixture(repair_fixtures.RepairExecution)
                proxy_entry(fixture.entry)
                fixture.retained()
                original_plan = fixture.plan.read_bytes()
                fixture.arguments['entry_request'] = changed_entry(fixture.entry, change)
                with patch.object(repair_fixtures.e, '_native_session',
                                  side_effect=AssertionError('native admission')), \
                        patch.object(repair_fixtures.r, 'preflight',
                                     side_effect=AssertionError('target read')):
                    with self.assertRaisesRegex(repair_fixtures.r.RepairError,
                                                '^ENVIRONMENT_ENTRY_PLAN_MISMATCH$'):
                        repair_fixtures.e.execute(**fixture.arguments)
                self.assertEqual(fixture.plan.read_bytes(), original_plan)
                self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)
                self.assertEqual(list(fixture.backups.iterdir()), [])

    def test_repair_legacy_plan_cannot_be_upgraded_by_adding_probe_context(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        fixture.retained()
        original_plan = fixture.plan.read_bytes()
        current = copy.deepcopy(fixture.entry)
        current['schema_version'] = 'guardian-environment-entry-input/0.2'
        current['probe_context'] = {
            'schema_version': 'guardian-probe-context/0.1', 'executor': 'shell',
            'transport_path': 'direct_socket_os_route_tun_unknown',
            'binding': {'target_ref': current['targets'][0]['target_ref'], 'user_ref': 'user',
                        'namespace_ref': 'native', 'source': 'current_host_observation'},
            'resource': {'selection': 'unknown', 'source': 'current_user_declaration'}}
        current['probe_context']['resource']['selection'] = current['network']['selection']
        fixture.arguments['entry_request'] = current
        with patch.object(repair_fixtures.e, '_native_session',
                          side_effect=AssertionError('native admission')):
            with self.assertRaisesRegex(repair_fixtures.r.RepairError,
                                        '^ENVIRONMENT_ENTRY_PLAN_MISMATCH$'):
                repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(fixture.plan.read_bytes(), original_plan)
        self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)
        self.assertEqual(list(fixture.backups.iterdir()), [])

    def test_repair_equivalent_fresh_entry_and_reordered_keys_keep_plan_usable(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        proxy_entry(fixture.entry)
        fixture.retained()
        equivalent = copy.deepcopy(dict(reversed(list(fixture.entry.items()))))
        self.assertIsNot(equivalent, fixture.entry)
        fixture.arguments['entry_request'] = equivalent
        with repair_fixtures.synthetic_adapter():
            result = repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(result['status'], 'written_but_not_verified')

    def test_repair_changed_entry_requires_a_new_retained_plan(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        proxy_entry(fixture.entry)
        fixture.retained()
        fixture.entry = changed_entry(fixture.entry, 'resource')
        fresh_path = fixture.root / 'fresh-plan.json'
        fresh_digest = repair_fixtures.e.retain(
            fixture.prepare(), plan_path=str(fresh_path),
            backup_directory=str(fixture.backups))
        fixture.arguments.update(plan_path=str(fresh_path), plan_digest=fresh_digest,
                                 entry_request=fixture.entry)
        self.assertNotEqual(fresh_digest, fixture.digest)
        with repair_fixtures.synthetic_adapter():
            result = repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(result['status'], 'written_but_not_verified')

    def test_repair_legacy_retained_plan_never_authorizes_new_apply(self):
        fixture = self.fixture(repair_fixtures.RepairExecution)
        fixture.retained()
        document = json.loads(fixture.plan.read_text(encoding='utf-8'))
        document['schema_version'] = 'guardian-retained-repair/0.2'
        del document['entry_digest']
        fixture.plan.write_text(json.dumps(document), encoding='utf-8')
        fixture.arguments['plan_digest'] = repair_fixtures.e.tx.digest(document)
        with patch.object(repair_fixtures.e, '_native_session',
                          side_effect=AssertionError('native admission')):
            with self.assertRaisesRegex(repair_fixtures.e.tx.TransactionError,
                                        '^INVALID_RETAINED_PLAN$'):
                repair_fixtures.e.execute(**fixture.arguments)
        self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)
        self.assertEqual(list(fixture.backups.iterdir()), [])

    def test_repair_missing_or_malformed_new_digest_is_rejected(self):
        for digest in (None, 'not-a-digest'):
            with self.subTest(digest=digest):
                fixture = self.fixture(repair_fixtures.RepairExecution)
                fixture.retained()
                document = json.loads(fixture.plan.read_text(encoding='utf-8'))
                if digest is None:
                    del document['entry_digest']
                else:
                    document['entry_digest'] = digest
                fixture.plan.write_text(json.dumps(document), encoding='utf-8')
                fixture.arguments['plan_digest'] = repair_fixtures.e.tx.digest(document)
                with patch.object(repair_fixtures.e, '_native_session',
                                  side_effect=AssertionError('native admission')):
                    with self.assertRaisesRegex(repair_fixtures.e.tx.TransactionError,
                                                '^INVALID_RETAINED_PLAN$'):
                        repair_fixtures.e.execute(**fixture.arguments)
                self.assertEqual(fixture.target.read_bytes(), repair_fixtures.RAW)

    def test_cleanup_new_plan_binds_entry_without_exposing_aliases(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        proxy_entry(fixture.entry)
        digest = fixture.planned()
        document = json.loads(fixture.planfile.read_text(encoding='utf-8'))
        self.assertEqual(document['schema_version'], 'guardian-cleanup-operator-document/0.2')
        self.assertEqual(document['entry_digest'], cleanup_fixtures.cli.digest(fixture.entry))
        self.assertEqual(set(document['bindings']), {'backup_ref', 'host_context_ref'})
        self.assertNotIn('resource-a', fixture.planfile.read_text(encoding='utf-8'))
        self.assertNotIn('entry-a', fixture.planfile.read_text(encoding='utf-8'))
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertEqual(code, 0, result)
        self.assertNotIn('entry_digest', result)
        self.assertNotIn('resource-a', json.dumps(result))

    def test_cleanup_changed_entry_cannot_reuse_plan_before_target_verification(self):
        for change in ('resource', 'listener', 'configuration', 'route'):
            with self.subTest(change=change):
                fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
                proxy_entry(fixture.entry)
                digest = fixture.planned()
                original_plan = fixture.planfile.read_bytes()
                fixture.entry = changed_entry(fixture.entry, change)
                fixture.host.events.clear()
                with patch.object(cleanup_fixtures.cli, '_verify',
                                  side_effect=AssertionError('target verification')), \
                        patch.object(cleanup_fixtures.cli.core, 'quarantine',
                                     side_effect=AssertionError('target write')):
                    code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
                self.assertEqual(code, 2, result)
                self.assertEqual(result['code'], 'ENVIRONMENT_ENTRY_PLAN_MISMATCH')
                self.assertEqual(fixture.planfile.read_bytes(), original_plan)
                self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
                self.assertEqual(list((fixture.base / 'quarantine').iterdir()), [])
                self.assertEqual(fixture.host.events, [])

    def test_cleanup_equivalent_fresh_entry_and_reordered_keys_keep_plan_usable(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        proxy_entry(fixture.entry)
        digest = fixture.planned()
        fixture.entry = copy.deepcopy(dict(reversed(list(fixture.entry.items()))))
        code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertEqual(code, 0, result)
        self.assertEqual(result['state'], 'quarantined')

    def test_cleanup_legacy_plan_cannot_start_new_quarantine(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        fixture.planned()
        document = json.loads(fixture.planfile.read_text(encoding='utf-8'))
        document['schema_version'] = 'guardian-cleanup-operator-document/0.1'
        del document['entry_digest']
        fixture.save(fixture.planfile, document)
        digest = cleanup_fixtures.cli.digest(document)
        with patch.object(cleanup_fixtures.cli, '_verify',
                          side_effect=AssertionError('target verification')):
            code, result = fixture.run_cli(self.quarantine_args(fixture, digest))
        self.assertEqual(code, 2, result)
        self.assertEqual(result['code'], 'ENVIRONMENT_ENTRY_PLAN_BINDING_REQUIRED')
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
        self.assertEqual(list((fixture.base / 'quarantine').iterdir()), [])

    def test_cleanup_missing_or_malformed_new_digest_is_rejected(self):
        for digest in (None, 'not-a-digest'):
            with self.subTest(digest=digest):
                fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
                fixture.planned()
                document = json.loads(fixture.planfile.read_text(encoding='utf-8'))
                if digest is None:
                    del document['entry_digest']
                else:
                    document['entry_digest'] = digest
                fixture.save(fixture.planfile, document)
                expected = cleanup_fixtures.cli.digest(document)
                with patch.object(cleanup_fixtures.cli, '_verify',
                                  side_effect=AssertionError('target verification')):
                    code, result = fixture.run_cli(self.quarantine_args(fixture, expected))
                self.assertEqual(code, 2, result)
                self.assertEqual(result['code'], 'INVALID_DOCUMENT')
                self.assertTrue((fixture.base / 'app').exists())

    def test_legacy_cleanup_plan_reconciles_and_old_receipt_restores_without_entry(self):
        fixture = self.fixture(cleanup_fixtures.CleanupCLITests)
        fixture.quarantined()
        # The core journal is deliberately unchanged by the new wrapper.
        legacy = json.loads(fixture.planfile.read_text(encoding='utf-8'))
        legacy['schema_version'] = 'guardian-cleanup-operator-document/0.1'
        del legacy['entry_digest']
        fixture.save(fixture.planfile, legacy)
        fixture.entry['route']['state'] = 'withdrawn'
        digest = cleanup_fixtures.cli.digest(legacy)
        code, result = fixture.run_cli([
            'reconcile', '--plan-file', str(fixture.planfile),
            '--expected-plan-digest', digest,
            '--receipt-output', str(fixture.receiptfile)])
        self.assertEqual(code, 0, result)
        receipt = json.loads(fixture.receiptfile.read_text(encoding='utf-8'))
        self.assertEqual(receipt['schema_version'], 'guardian-cleanup-operator-document/0.1')
        self.assertEqual(receipt['material']['schema_version'], 'guardian-cleanup-receipt/0.1')
        self.assertNotIn('entry_digest', receipt)
        restore = ['restore', '--receipt-file', str(fixture.receiptfile),
                   '--expected-receipt-digest', result['document_digest']]
        fixture.host.denied.add('restore_cleanup')
        self.assertNotEqual(fixture.run_cli(restore)[0], 0)
        self.assertFalse((fixture.base / 'app').exists())
        fixture.host.denied.clear()
        code, result = fixture.run_cli(restore)
        self.assertEqual(code, 0, result)
        self.assertEqual((fixture.base / 'app/data').read_bytes(), b'synthetic')
        self.assertEqual((fixture.base / 'backup/data').read_bytes(), b'synthetic')
        self.assertEqual((fixture.base / 'protected/keep').read_bytes(), b'protected')

    def test_independent_original_receipt_protocol_restores_without_entry(self):
        fixture = self.fixture(recovery_fixtures.RecoveryCLI)
        self.assertEqual(fixture.document['schema_version'], 'exact-file-recovery/2')
        self.assertNotIn('entry_digest', fixture.document)
        code, output = fixture.terminal(fixture.approvals())
        self.assertEqual(code, 0, output)
        self.assertEqual(fixture.file.read_bytes(), b'original synthetic data')
        self.assertTrue(fixture.receipt.exists())

    def test_independent_original_prepared_protocol_restores_without_entry(self):
        fixture = self.fixture(prepared_recovery_fixtures.PreparedRecoveryCLI)
        self.assertEqual(fixture.document['schema_version'], 'exact-file-recovery/2')
        self.assertNotIn('entry_digest', fixture.document)
        code, output = fixture.terminal(fixture.approvals())
        self.assertEqual(code, 0, output)
        self.assertEqual(fixture.file.read_bytes(), b'original synthetic data')
        self.assertTrue(fixture.receipt.exists())

    def test_rules_preflight_cancel_withdrawal_precedes_profile_index_read(self):
        fixture = self.fixture(rules_fixtures.RulesRepairCLI)
        original_read = rules_fixtures.r._read_source
        reads, calls = [], []

        def cancelled():
            calls.append(None)
            if len(calls) == 4:
                fixture.entry['route']['state'] = 'withdrawn'
            return False

        def read(path):
            reads.append(path)
            self.assertNotEqual(path, str(fixture.index), 'profile index read after withdrawal')
            return original_read(path)

        with patch.object(rules_fixtures.r, '_read_source', side_effect=read):
            with self.assertRaisesRegex(rules_fixtures.r.RepairError,
                                        '^ENVIRONMENT_ENTRY_CHANGED$'):
                fixture.preflight(cancelled=cancelled)
        self.assertEqual(len(calls), 4)
        self.assertEqual(reads, [str(fixture.base), str(fixture.info)])
        self.assertEqual(fixture.target.read_bytes(), rules_fixtures.RAW)


if __name__ == '__main__':
    unittest.main()
