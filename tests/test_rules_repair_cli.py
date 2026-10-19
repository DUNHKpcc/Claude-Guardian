"""End-to-end private temporary-file rules route; native gate stays closed."""
import json
import os
from pathlib import Path
import plistlib
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import repair_cli as r
import repair_execution as e
import test_repair_execution as transport_fixtures
from test_rules_extension_plan import RAW, BASE, inputs
from test_clash_verge_258 import INFO
from environment_entry_fixture import local_entry

INDEX = b'''current: profile-a
items:
  - uid: profile-a
    type: remote
    file: source.yaml
    option:
      rules: rules-a
  - uid: rules-a
    type: rules
    file: extension.yaml
'''


@unittest.skipUnless(os.name == 'posix', 'POSIX file transport only')
class RulesRepairCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.profiles = self.root / 'profiles'
        self.profiles.mkdir(mode=0o700)
        self.target = self.profiles / 'extension.yaml'
        self.base = self.profiles / 'source.yaml'
        self.index = self.root / 'profiles.yaml'
        self.info = self.root / 'Info.plist'
        self.request = self.root / 'request.json'
        self.entry = local_entry('mac-a')
        self.entry_file = self.root / 'entry.json'
        self.entry_file.write_text(json.dumps(self.entry), encoding='utf-8')
        self.entry_file.chmod(0o600)
        semantic, binding = inputs()
        self.document = {'schema_version': r.SCHEMA, 'remedy_request': semantic, 'binding': binding}
        for path, raw in ((self.target, RAW), (self.base, BASE), (self.index, INDEX),
                          (self.info, plistlib.dumps(INFO)),
                          (self.request, json.dumps(self.document).encode())):
            path.write_bytes(raw)
            path.chmod(0o600)
        self.scope = dict(candidate_kind='rules-prepend', base_path=str(self.base),
                          app_info_path=str(self.info), profile_index_path=str(self.index),
                          extension_uid='rules-a')
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.plan = self.root / 'plan.json'

    def preflight(self, **changes):
        return r.preflight(str(self.request), str(self.target), 'mac-a',
                           entry_request=self.entry, **dict(self.scope, **changes))

    def args(self, command):
        return [sys.executable, '-B', str(SCRIPTS / 'repair_cli.py'), command,
                '--request', str(self.request), '--target-path', str(self.target),
                '--target-ref', 'mac-a', '--entry-file', str(self.entry_file),
                '--candidate-kind', 'rules-prepend',
                '--base-path', str(self.base), '--app-info', str(self.info),
                '--profile-index', str(self.index), '--extension-uid', 'rules-a']

    def run_cli(self, command, *extra):
        return subprocess.run(self.args(command) + list(extra), capture_output=True, text=True, timeout=10)

    def retain(self):
        prepared = self.preflight()
        digest = e.retain(prepared, plan_path=str(self.plan), backup_directory=str(self.backups))
        return dict(request_path=str(self.request), plan_path=str(self.plan), plan_digest=digest,
                    target_path=str(self.target), target_ref='mac-a', backup_directory=str(self.backups),
                    entry_request=self.entry, **self.scope)

    def matching_snapshot(self):
        candidate = r.rules_edits.compile_rules_extension(RAW, BASE, *inputs())
        raw = candidate.private_material()['candidate_bytes']
        self.target.write_bytes(raw)
        semantic, binding = inputs(raw=raw)
        self.document = {'schema_version': r.SCHEMA, 'remedy_request': semantic, 'binding': binding}
        self.request.write_text(json.dumps(self.document))
        return raw

    def test_exact_repeat_cli_is_an_observation_without_artifact_or_receipt(self):
        raw = self.matching_snapshot()
        with patch.object(r.tx, 'plan', side_effect=AssertionError('action plan')):
            prepared = self.preflight()
            self.assertIsNone(prepared._plan)
            self.assertEqual(prepared.public_report()['matched_rules'], 1)
        result = self.run_cli('plan', '--plan-file', str(self.plan),
                              '--backup-directory', str(self.root / 'absent'), '--private-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        review, report = map(json.loads, result.stdout.splitlines())
        self.assertEqual(report['status'], 'no_change_in_supplied_snapshot')
        self.assertEqual(report['added_rules'], 0)
        self.assertEqual(report['matched_rules'], 1)
        self.assertFalse(report['apply_supported'])
        self.assertEqual(report['effective_routing'], 'not_run')
        self.assertEqual(review['selected_rule_changes'], [])
        self.assertEqual(review['matched_rule_refs'], ['rule-a'])
        self.assertIsNone(review['byte_insertion'])
        self.assertEqual(review['operation'], 'none')
        for key in ('plan_digest', 'retained_plan_digest', 'action_id', 'recovery_id', 'receipt_digest'):
            self.assertNotIn(key, review)
            self.assertNotIn(key, report)
        self.assertFalse(self.plan.exists())
        self.assertFalse((self.root / 'absent').exists())
        self.assertEqual(self.target.read_bytes(), raw)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_exact_repeat_review_rechecks_every_supporting_source_identity(self):
        self.matching_snapshot()
        for source in (self.base, self.info, self.index):
            with self.subTest(source=source.name):
                prepared = self.preflight()
                replacement = source.with_name('replacement')
                replacement.write_bytes(source.read_bytes())
                replacement.chmod(0o600)
                replacement.replace(source)
                for render in (prepared.public_report, prepared.private_review):
                    with self.assertRaisesRegex(r.RepairError, '^SOURCE_SNAPSHOT_CHANGED$'):
                        render()

    def test_exact_repeat_retention_is_rejected_without_destination_access(self):
        self.matching_snapshot()
        prepared = self.preflight()
        with patch.object(e.tx, '_path', side_effect=AssertionError('destination validation')), \
                patch.object(e.tx, '_directory', side_effect=AssertionError('backup access')), \
                patch.object(e.tx, '_parent', side_effect=AssertionError('artifact access')):
            with self.assertRaisesRegex(e.tx.TransactionError, '^NO_CHANGE_TO_RETAIN$'):
                e.retain(prepared, plan_path='unused', backup_directory='unused')
        self.assertFalse(self.plan.exists())
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_exact_repeat_source_change_during_compilation_still_blocks(self):
        self.matching_snapshot()
        compile = r.rules_edits.compile_rules_extension
        def changed(*args, **kwargs):
            result = compile(*args, **kwargs)
            self.index.write_bytes(INDEX + b'# changed during compilation\n')
            return result
        with patch.object(r.rules_edits, 'compile_rules_extension', side_effect=changed), \
                patch.object(r.tx, 'plan', side_effect=AssertionError('action plan')):
            with self.assertRaisesRegex(r.RepairError, '^SOURCE_SNAPSHOT_CHANGED$'):
                self.preflight()

    def test_preflight_and_exact_private_diff_no_write(self):
        result = self.run_cli('diff', '--private-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        private, public = map(json.loads, result.stdout.splitlines())
        self.assertEqual(public['added_rules'], 1)
        self.assertEqual(public['changed_rules'], 0)
        self.assertEqual(public['ownership']['status'], 'supplied_metadata_only')
        self.assertEqual(public['ownership']['format'], 'rules_seqmap')
        self.assertFalse(public['apply_supported'])
        self.assertEqual(private['operation'], 'insert_selected_prepend_rules')
        self.assertEqual(private['selected_rule_changes'][0]['added_rule'], 'DOMAIN,example.test,approved-group')
        self.assertEqual(private['base_source']['path'], str(self.base))
        self.assertNotIn('keep-SENTINEL', result.stdout)
        self.assertNotIn(str(self.root), json.dumps(public))
        self.assertEqual(self.target.read_bytes(), RAW)
        self.assertFalse(self.plan.exists())

    def test_all_metadata_inputs_explicit_before_any_read(self):
        with patch.object(r, '_load_request', side_effect=AssertionError('read')):
            for field in ('base_path', 'app_info_path', 'profile_index_path', 'extension_uid'):
                with self.assertRaisesRegex(r.RepairError, '^EXPLICIT_RULES_SOURCE_SCOPE_REQUIRED$'):
                    self.preflight(**{field: None})
            with self.assertRaisesRegex(r.RepairError, '^EXPLICIT_RULES_SOURCE_SCOPE_REQUIRED$'):
                self.preflight(candidate_kind='merge-policy')

    def test_base_directory_and_registry_source_link_bound(self):
        outside = self.root / 'source.yaml'
        outside.write_bytes(BASE)
        outside.chmod(0o600)
        with self.assertRaisesRegex(r.RepairError, '^PROFILE_DIRECTORY_SCOPE_MISMATCH$'):
            self.preflight(base_path=str(outside))
        other = self.profiles / 'other.yaml'
        other.write_bytes(BASE)
        other.chmod(0o600)
        with self.assertRaisesRegex(r.RepairError, '^BASE_PROFILE_FILE_MISMATCH$'):
            self.preflight(base_path=str(other))

    def test_ownership_type_uid_and_product_checked(self):
        with self.assertRaisesRegex(r.ownership.OwnershipError, '^PROFILE_LINK_MISSING$'):
            self.preflight(extension_uid='missing')
        self.index.write_bytes(INDEX.replace(b'type: rules', b'type: merge'))
        with self.assertRaisesRegex(r.ownership.OwnershipError, '^UNSUPPORTED_EXTENSION_TYPE$'):
            self.preflight()
        self.index.write_bytes(INDEX)
        self.info.write_bytes(plistlib.dumps(dict(INFO, CFBundleVersion='2.5.7')))
        with self.assertRaisesRegex(r.ownership.OwnershipError, '^UNSUPPORTED_PRODUCT_OR_VERSION$'):
            self.preflight()

    def test_retained_review_and_production_gate(self):
        result = self.run_cli('plan', '--plan-file', str(self.plan),
                              '--backup-directory', str(self.backups), '--private-review')
        self.assertEqual(result.returncode, 0, result.stderr)
        private, public = map(json.loads, result.stdout.splitlines())
        document = json.loads(self.plan.read_text())
        self.assertEqual(document['schema_version'], 'guardian-retained-repair/0.3')
        self.assertEqual(document['entry_digest'], e.tx.digest(self.entry))
        self.assertEqual(private['retained_plan_digest'], e.tx.digest(document))
        self.assertEqual(document['base_source']['path'], str(self.base))
        self.assertEqual(document['metadata_sources']['app_info']['path'], str(self.info))
        self.assertEqual(document['metadata_sources']['profile_index']['path'], str(self.index))
        self.assertEqual(document['extension_uid'], 'rules-a')
        result = self.run_cli('execute', '--plan-file', str(self.plan),
                              '--backup-directory', str(self.backups),
                              '--plan-digest', public['retained_plan_digest'])
        self.assertEqual(result.returncode, 2)
        self.assertEqual(json.loads(result.stderr)['code'], 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE')
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_same_bytes_source_inode_change_rejects_retained_plan(self):
        args = self.retain()
        for source in (self.base, self.info, self.index):
            with self.subTest(source=source.name):
                replacement = source.with_name('replacement')
                replacement.write_bytes(source.read_bytes())
                replacement.chmod(0o600)
                replacement.replace(source)
                with transport_fixtures.synthetic_adapter():
                    with self.assertRaisesRegex(e.tx.TransactionError, '^SOURCE_SNAPSHOT_CHANGED$'):
                        e.execute(**args)
                self.assertEqual(self.target.read_bytes(), RAW)
                self.assertEqual(list(self.backups.iterdir()), [])
                self.plan.unlink()  # Synthetic fixture artifact only.
                args = self.retain()

    def test_explicit_source_argument_cannot_be_redirected(self):
        args = self.retain()
        with self.assertRaisesRegex(e.tx.TransactionError, '^SOURCE_SCOPE_MISMATCH$'):
            e.execute(**dict(args, base_path=str(self.profiles / 'different.yaml')))
        with self.assertRaisesRegex(e.tx.TransactionError, '^CANDIDATE_SCOPE_MISMATCH$'):
            e.execute(**dict(args, extension_uid='other'))

    def test_source_changes_during_plan_rejected(self):
        original = r.tx.plan
        def changing(*args, **kwargs):
            result = original(*args, **kwargs)
            self.index.write_bytes(INDEX + b'# later metadata\n')
            return result
        with patch.object(r.tx, 'plan', side_effect=changing):
            with self.assertRaisesRegex(r.RepairError, '^SOURCE_SNAPSHOT_CHANGED$'):
                self.preflight()

    def test_source_change_at_final_commit_retains_backup(self):
        args = self.retain()
        calls = 0
        def recheck():
            nonlocal calls
            calls += 1
            if calls == 3:
                self.index.write_bytes(INDEX + b'# changed before final approval\n')
        with transport_fixtures.synthetic_adapter(side_effect=recheck):
            with self.assertRaisesRegex(e.tx.TransactionError, '^SOURCE_SNAPSHOT_CHANGED$') as caught:
                e.execute(**args)
        self.assertTrue(caught.exception.recovery_id)
        self.assertEqual(self.target.read_bytes(), RAW)
        self.assertTrue((self.backups / caught.exception.recovery_id / 'prepared.json').exists())

    def test_private_review_rechecks_request_and_supporting_sources(self):
        prepared = self.preflight()
        self.index.write_bytes(INDEX + b'# changed metadata\n')
        with self.assertRaisesRegex(r.RepairError, '^SOURCE_SNAPSHOT_CHANGED$'):
            prepared.recheck_review(str(self.request))
        self.index.write_bytes(INDEX)
        prepared = self.preflight()
        self.document['remedy_request']['route_ref'] = 'changed-route'
        self.request.write_text(json.dumps(self.document))
        with self.assertRaisesRegex(r.RepairError, '^REQUEST_CHANGED$'):
            prepared.recheck_review(str(self.request))

    def test_private_review_contains_linkage_chain_blockers(self):
        self.index.write_bytes(INDEX.replace(b'rules: rules-a', b'rules: rules-a\n      script: custom-script'))
        prepared = self.preflight()
        self.assertIn('PROFILE_SCRIPT_CHAIN_UNSUPPORTED', prepared.private_review()['blockers'])

    def test_synthetic_apply_reports_bytes_only(self):
        args = self.retain()
        with transport_fixtures.synthetic_adapter():
            result = e.execute(**args)
        self.assertEqual(result['byte_readback'], 'pass')
        self.assertEqual(result['effective_routing'], 'not_run')
        self.assertIn(b"'DOMAIN,example.test,approved-group'", self.target.read_bytes())
        self.assertEqual(self.base.read_bytes(), BASE)
        self.assertEqual(self.index.read_bytes(), INDEX)


if __name__ == '__main__':
    unittest.main()
