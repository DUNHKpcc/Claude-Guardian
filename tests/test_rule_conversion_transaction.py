"""Converter composition with synthetic POSIX artifact transactions only.

No production adapter is admitted here. The temporary fixture owns every target
and excludes other writers except deliberate conflict injections. These tests
do not establish engine loading, real configuration merging, or network effects.
"""
import hashlib
import json
import os
from pathlib import Path
import stat
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import rule_format_conversion as conversion
import transactions as tx

EXACT = 'exact-domain-lines/0.1'
MIHOMO_DOMAIN = 'mihomo/1.19.32/provider-domain-yaml'
MIHOMO_CLASSICAL = 'mihomo/1.19.32/provider-classical-yaml'
SING_BOX = 'sing-box/1.12.0/source-rule-set-json-v1'
PLAIN = b'example.invalid\n'
DOMAIN = b"payload:\n  - 'api.example.invalid'\n  - '+.example.invalid'\n"
CLASSICAL = (b"payload:\n  - 'DOMAIN,api.example.invalid'\n"
             b"  - 'DOMAIN-SUFFIX,example.invalid'\n")
JSON_OUTPUT = (b'{"version":1,"rules":[{"domain":["api.example.invalid"]},'
               b'{"domain_suffix":["example.invalid"]}]}\n')
ORIGINAL = b'{"version":1,"rules":[{"domain":["old.example.invalid"]}]}\n'
TARGET_REF = 'synthetic-conversion-artifact'


def binding(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'synthetic-source',
            'expected_sha256': hashlib.sha256(raw).hexdigest(),
            'evidence_kind': 'user_supplied', 'verified_at': '2026-10-18',
            'version_scope': 'pinned-conversion-fixture', 'purpose': 'conversion-test',
            'client_scope': ['synthetic-client'], 'feature_gate': 'synthetic-feature',
            'shared_service': False, 'activation_state': 'candidate'}


@unittest.skipUnless(os.name == 'posix', 'POSIX temporary-artifact transactions only; Windows writes unsupported')
class RuleConversionTransactionTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory(prefix='guardian-conversion-')
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.target = self.root / 'standalone-artifact'
        self.target.write_bytes(ORIGINAL)
        self.target.chmod(0o640)
        self.source = self.root / 'synthetic-source'
        self.source.write_bytes(CLASSICAL)
        self.source.chmod(0o600)
        self.neighbor = self.root / 'protected-neighbor'
        self.neighbor.write_bytes(b'protected\x00synthetic-SENTINEL\xff')
        self.neighbor.chmod(0o600)
        self.neighbor_before = self.neighbor.read_bytes()
        self.backups = self.root / 'private-backups'
        self.backups.mkdir(mode=0o700)

    def convert(self, raw=CLASSICAL, source_profile=MIHOMO_CLASSICAL,
                target_profile=SING_BOX, refs=None, declared=None):
        return conversion.convert_rule_format(
            raw, source_profile, target_profile,
            ['rule-a', 'rule-b'] if refs is None else refs,
            binding(raw) if declared is None else declared)

    def plan(self, raw=CLASSICAL, source_profile=MIHOMO_CLASSICAL,
             target_profile=SING_BOX, refs=None, declared=None):
        converted = self.convert(raw, source_profile, target_profile, refs, declared)
        output = converted.private_material()['output_bytes']
        return tx.plan(str(self.target), output, TARGET_REF), output

    def apply_authorizer(self, plan, calls=None):
        expected = tx.digest({'plan': plan, 'backup_directory': str(self.backups)})
        def approve(operation, digest, target):
            if calls is not None:
                calls.append((operation, digest, target))
            return operation == 'apply' and digest == expected and target == TARGET_REF
        return approve

    def apply(self, plan, authorize=None):
        return tx.apply(plan, target_ref=TARGET_REF, backup_directory=str(self.backups),
                        authorize=self.apply_authorizer(plan) if authorize is None else authorize,
                        exclusive_access=True)

    def rollback(self, receipt, calls=None):
        expected = tx.digest(receipt)
        def approve(operation, digest, target):
            if calls is not None:
                calls.append((operation, digest, target))
            return operation == 'rollback' and digest == expected and target == TARGET_REF
        return tx.rollback(receipt, target_ref=TARGET_REF, authorize=approve,
                           exclusive_access=True)

    def assert_protected(self, source=CLASSICAL):
        self.assertEqual(self.source.read_bytes(), source)
        self.assertEqual(stat.S_IMODE(self.source.stat().st_mode), 0o600)
        self.assertEqual(self.neighbor.read_bytes(), self.neighbor_before)
        self.assertEqual(stat.S_IMODE(self.neighbor.stat().st_mode), 0o600)

    def test_all_output_profiles_exact_readback_and_independent_restoration(self):
        cases = ((PLAIN, EXACT, EXACT, ['rule-a'], PLAIN),
                 (CLASSICAL, MIHOMO_CLASSICAL, MIHOMO_DOMAIN, ['rule-a', 'rule-b'], DOMAIN),
                 (DOMAIN, MIHOMO_DOMAIN, MIHOMO_CLASSICAL, ['rule-a', 'rule-b'], CLASSICAL),
                 (CLASSICAL, MIHOMO_CLASSICAL, SING_BOX, ['rule-a', 'rule-b'], JSON_OUTPUT))
        for raw, source_profile, target_profile, refs, expected in cases:
            with self.subTest(target_profile=target_profile):
                before_stat = self.target.stat()
                plan, output = self.plan(raw, source_profile, target_profile, refs)
                self.assertEqual(output, expected)
                self.assertEqual(self.target.read_bytes(), ORIGINAL)
                apply_calls = []
                receipt = self.apply(plan, self.apply_authorizer(plan, apply_calls))
                self.assertEqual(len(apply_calls), 2)
                self.assertEqual(self.target.read_bytes(), expected)
                self.assertEqual(tx.verify(receipt), {
                    'check_status': 'pass', 'verification_scope': 'exact_file_bytes_only',
                    'application_effect': 'not_tested', 'network_effect': 'not_tested'})
                batch = self.backups / receipt['batch']
                self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
                self.assertEqual(json.loads((batch / 'applied.json').read_text(encoding='utf-8')), receipt)
                self.assertEqual(stat.S_IMODE(batch.stat().st_mode), 0o700)
                self.assertEqual(stat.S_IMODE((batch / 'original.bin').stat().st_mode), 0o600)
                self.assert_protected()
                rollback_calls = []
                restored = self.rollback(receipt, rollback_calls)
                self.assertEqual(len(rollback_calls), 2)
                self.assertEqual(restored['state'], 'restored')
                self.assertEqual(restored['verification_scope'], 'exact_file_bytes_only')
                self.assertEqual(restored['restored_snapshot']['sha256'], hashlib.sha256(ORIGINAL).hexdigest())
                self.assertEqual(self.target.read_bytes(), ORIGINAL)
                after_stat = self.target.stat()
                self.assertEqual((stat.S_IMODE(after_stat.st_mode), after_stat.st_uid, after_stat.st_gid),
                                 (0o640, before_stat.st_uid, before_stat.st_gid))
                self.assertEqual(len(list(batch.glob('rollback-*.json'))), 1)
                self.assertTrue((batch / 'original.bin').exists())
                self.assertFalse(list(self.root.glob('.guardian-stage-*')))
                self.assert_protected()

    def test_conversion_rejections_never_reach_transaction_plan(self):
        mixed = b"payload:\n  - 'DOMAIN,api.example.invalid'\n  - 'IP-ASN,13335'\n"
        version_five = b'{"version":5,"rules":[{"domain":["example.invalid"]}]}\n'
        action = b"payload:\n  - 'DOMAIN,api.example.invalid,egress-a'\n"
        conditional = b'{"version":1,"rules":[{"domain":["example.invalid"],"port":[443]}]}\n'
        cases = ((CLASSICAL, MIHOMO_CLASSICAL, EXACT, ['rule-a', 'rule-b'], 'UNREPRESENTABLE_MATCH'),
                 (mixed, MIHOMO_CLASSICAL, SING_BOX, ['rule-a', 'rule-b'], 'UNREPRESENTABLE_MATCH'),
                 (version_five, SING_BOX, MIHOMO_DOMAIN, ['rule-a'], 'UNSUPPORTED_SCHEMA_VERSION'),
                 (action, MIHOMO_CLASSICAL, SING_BOX, ['rule-a'], 'UNREPRESENTABLE_ACTION'),
                 (conditional, SING_BOX, MIHOMO_DOMAIN, ['rule-a'], 'UNHANDLED_CONDITION'))
        for raw, source_profile, target_profile, refs, code in cases:
            with self.subTest(raw=raw):
                with patch.object(tx, 'plan', wraps=tx.plan) as planner:
                    with self.assertRaises(conversion.ConversionError) as caught:
                        self.plan(raw, source_profile, target_profile, refs)
                    planner.assert_not_called()
                self.assertEqual(str(caught.exception), code)
                self.assertNotIn('example.invalid', str(caught.exception))
                self.assertEqual(self.target.read_bytes(), ORIGINAL)
                self.assertEqual(list(self.backups.iterdir()), [])
                self.assert_protected()

    def test_changed_source_digest_rejects_before_output_plan(self):
        declared = binding(CLASSICAL)
        changed = CLASSICAL.replace(b'api.example.invalid', b'new.example.invalid')
        self.source.write_bytes(changed)
        with patch.object(tx, 'plan', wraps=tx.plan) as planner:
            with self.assertRaisesRegex(conversion.ConversionError, '^SOURCE_DIGEST_MISMATCH$'):
                self.plan(self.source.read_bytes(), declared=declared)
            planner.assert_not_called()
        self.assertEqual(self.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(self.backups.iterdir()), [])
        self.assert_protected(changed)

    def test_missing_or_wrong_apply_authorization_preserves_target(self):
        plan, _ = self.plan()
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_REQUIRED$'):
            tx.apply(plan, target_ref=TARGET_REF, backup_directory=str(self.backups), exclusive_access=True)
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
            self.apply(plan, lambda operation, digest, target: digest == '0' * 64)
        self.assertEqual(self.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(self.backups.iterdir()), [])
        self.assert_protected()

    def test_target_and_backup_scope_cannot_reuse_conversion_approval(self):
        plan, _ = self.plan()
        approve = self.apply_authorizer(plan)
        with self.assertRaisesRegex(tx.TransactionError, '^TARGET_MISMATCH$'):
            tx.apply(plan, target_ref='other-synthetic-target',
                     backup_directory=str(self.backups), authorize=approve, exclusive_access=True)
        other_backup = self.root / 'other-private-backups'
        other_backup.mkdir(mode=0o700)
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
            tx.apply(plan, target_ref=TARGET_REF, backup_directory=str(other_backup),
                     authorize=approve, exclusive_access=True)
        self.assertEqual(self.target.read_bytes(), ORIGINAL)
        self.assertEqual(list(self.backups.iterdir()), [])
        self.assertEqual(list(other_backup.iterdir()), [])
        self.assert_protected()

    def test_cancel_at_precommit_preserves_target_and_retains_backup(self):
        plan, _ = self.plan()
        calls = []
        bound = self.apply_authorizer(plan, calls)
        def approve_once(operation, digest, target):
            return bound(operation, digest, target) and len(calls) == 1
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$') as caught:
            self.apply(plan, approve_once)
        self.assertEqual(len(calls), 2)
        batch = self.backups / caught.exception.recovery_id
        self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
        self.assertTrue((batch / 'prepared.json').exists())
        self.assertFalse((batch / 'applied.json').exists())
        self.assertEqual(self.target.read_bytes(), ORIGINAL)
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))
        self.assert_protected()

    def test_stale_content_or_identity_blocks_converted_write(self):
        for same_bytes_new_inode in (False, True):
            with self.subTest(same_bytes_new_inode=same_bytes_new_inode):
                self.target.write_bytes(ORIGINAL)
                self.target.chmod(0o640)
                plan, _ = self.plan()
                expected = b'later synthetic edit\n'
                if same_bytes_new_inode:
                    replacement = self.root / 'replacement'
                    replacement.write_bytes(ORIGINAL)
                    replacement.chmod(0o640)
                    replacement.replace(self.target)
                    expected = ORIGINAL
                else:
                    self.target.write_bytes(expected)
                with self.assertRaisesRegex(tx.TransactionError, '^STALE_FILE$'):
                    self.apply(plan)
                self.assertEqual(self.target.read_bytes(), expected)
                self.assertEqual(list(self.backups.iterdir()), [])
                self.assert_protected()

    def test_rollback_requires_a_distinct_receipt_bound_authorization(self):
        plan, _ = self.plan()
        receipt = self.apply(plan)
        with self.assertRaisesRegex(tx.TransactionError, '^AUTHORIZATION_DENIED$'):
            tx.rollback(receipt, target_ref=TARGET_REF, authorize=self.apply_authorizer(plan),
                        exclusive_access=True)
        self.assertEqual(self.target.read_bytes(), JSON_OUTPUT)
        self.assertEqual(self.rollback(receipt)['state'], 'restored')
        self.assertEqual(self.target.read_bytes(), ORIGINAL)
        self.assert_protected()

    def test_rollback_conflict_preserves_later_edit_and_original_backup(self):
        plan, _ = self.plan()
        receipt = self.apply(plan)
        later = b'later user-owned synthetic bytes\n'
        self.target.write_bytes(later)
        self.assertEqual(tx.verify(receipt)['check_status'], 'fail')
        with self.assertRaisesRegex(tx.TransactionError, '^ROLLBACK_CONFLICT$'):
            self.rollback(receipt)
        self.assertEqual(self.target.read_bytes(), later)
        self.assertEqual((self.backups / receipt['batch'] / 'original.bin').read_bytes(), ORIGINAL)
        self.assert_protected()

    def test_postreplace_journal_failure_requires_reconciliation_not_fake_rollback(self):
        plan, output = self.plan()
        real_write = tx._write
        def fail_applied_journal(fd, name, data, mode=0o600):
            if name == 'applied.json':
                raise OSError('synthetic journal failure')
            return real_write(fd, name, data, mode)
        with patch.object(tx, '_write', side_effect=fail_applied_journal):
            with self.assertRaisesRegex(tx.TransactionError, '^IO_FAILURE$') as caught:
                self.apply(plan)
        self.assertIsNotNone(caught.exception.recovery_id)
        batch = self.backups / caught.exception.recovery_id
        prepared = json.loads((batch / 'prepared.json').read_text(encoding='utf-8'))
        self.assertEqual(prepared['state'], 'prepared')
        self.assertIsNone(prepared['applied_snapshot'])
        self.assertFalse((batch / 'applied.json').exists())
        self.assertEqual((batch / 'original.bin').read_bytes(), ORIGINAL)
        self.assertEqual(self.target.read_bytes(), output)
        with self.assertRaisesRegex(tx.TransactionError, '^RECOVERY_REQUIRES_RECONCILIATION$'):
            self.rollback(prepared)
        self.assertEqual(self.target.read_bytes(), output)
        self.assertFalse(list(batch.glob('rollback-*.json')))
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))
        self.assert_protected()


if __name__ == '__main__':
    unittest.main()
