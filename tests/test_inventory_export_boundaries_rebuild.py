"""Focused L regressions; not complete T11/ENV-T34/ENV-T121 or native acceptance."""
import copy
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import guardian as g
import clash_inventory as c
import status_dashboard as dashboard


def inventory():
    obj = json.loads((ROOT / 'tests/fixtures/proxy-port-conflict.json').read_text())
    report = g.base('audit', 'device-1')
    report.update(schema_version='env-inventory/0.2', record_kind='synthetic_example',
                  target_binding=obj['target_binding'], facts=obj['facts'])
    for fact in report['facts']:
        fact['observed_at'] = datetime.now(timezone.utc).isoformat()
        fact['source_refs'] = [fact.pop('source_ref')]
    return report


class ExportBoundaries(unittest.TestCase):
    def test_unknown_inventory_fields_rejected_before_projection(self):
        for where in ('root', 'fact', 'binding', 'contact', 'privacy', 'snapshot', 'limits'):
            for key in ('command', 'script', 'url', 'url_to_test', 'unknown_secret'):
                obj = inventory()
                location = {'root': obj, 'fact': obj['facts'][0],
                            'binding': obj['target_binding'], 'contact': obj['contact_control'],
                            'privacy': obj['privacy'], 'snapshot': obj['snapshot'],
                            'limits': obj['limits']}[where]
                location[key] = 'SYNTHETIC_MARKER'
                with self.subTest(where=where, key=key):
                    with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                        g.analyze(obj, 'device-1')

    def test_all_source_refs_validated_before_projection(self):
        for extra in ('ghp_' + 'A' * 36, {'unknown_secret': 'SYNTHETIC_MARKER'}, None):
            obj = inventory()
            obj['facts'][0]['source_refs'].append(extra)
            with self.subTest(extra_type=type(extra).__name__):
                with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                    g.analyze(obj, 'device-1')

    def test_synthetic_provenance_survives_analyze_plan_and_dashboard(self):
        for planning in (False, True):
            report = g.analyze(inventory(), 'device-1', planning)
            self.assertEqual(report['record_kind'], 'synthetic_example')
            self.assertTrue(dashboard.project(report)['synthetic'])
            self.assertEqual(report['changes'], [])
            self.assertEqual(report['contact_control']['gate_state'], 'closed')
            self.assertEqual(report['limits']['native_platform_validation'], 'not_run')

    def test_device_import_is_unverified_user_supplied_evidence(self):
        obj = inventory()
        obj['record_kind'] = 'device_observation'
        report = g.analyze(obj, 'device-1')
        self.assertEqual(report['record_kind'], 'user_supplied_observation')
        self.assertEqual(report['target_binding']['binding_state'], 'supplied_not_independently_verified')

    def test_unknown_provenance_rejected(self):
        obj = inventory(); obj['record_kind'] = 'private-unrecognized-marker'
        with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
            g.analyze(obj, 'device-1')

    def test_parser_errors_do_not_echo_input(self):
        cases = [('check', '--target-os', 'SYNTHETIC_MARKER'),
                 ('SYNTHETIC_MARKER',), ('interview', '--SYNTHETIC_MARKER'),
                 ('check', '--target-ref', 'SYNTHETIC_MARKER')]
        for argv in cases:
            result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'guardian.py'), *argv],
                                    capture_output=True, text=True, timeout=10)
            with self.subTest(argv=argv):
                self.assertEqual(result.returncode, 2)
                self.assertNotIn('SYNTHETIC_MARKER', result.stdout + result.stderr)
                self.assertIn('INPUT_OR_RESPONSE_INVALID', result.stderr)
                self.assertIn('usage:', result.stderr)

    def test_help_remains_available(self):
        result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'guardian.py'), 'check', '--help'],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0)
        self.assertIn('--target-os', result.stdout)

    def test_rejected_inventory_cannot_reach_stdout_or_saved_report(self):
        obj = inventory(); obj['unknown_secret'] = 'SYNTHETIC_MARKER'
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'input.json', Path(directory) / 'output.json'
            source.write_text(json.dumps(obj))
            result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'guardian.py'), 'plan',
                '--input', str(source), '--output', str(output), '--target-ref', 'device-1'],
                capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn('SYNTHETIC_MARKER', result.stdout + result.stderr + output.read_text())
            self.assertEqual(json.loads(result.stdout)['facts'], [])

    def test_static_inventory_credential_alias_never_echoed_on_block(self):
        for marker in ('ghp_' + 'A' * 36, 'sk-' + 'A' * 36):
            request = dict(schema_version='guardian-clash-inventory/0.1', target_ref=marker,
                operation='audit', contact_phase='precontact', gate_state='closed',
                target_binding=dict(binding_state='bound', target_ref=marker,
                    execution_location='native_local', desktop_user_relation='same',
                    filesystem_namespace='host_desktop', declared_os='macos'))
            with patch.object(c.sys, 'platform', 'darwin'), patch.object(c, '_read') as read:
                report = c.audit_inventory(request, marker)
            self.assertEqual(report['status'], 'blocked')
            self.assertNotIn(marker, json.dumps(report))
            read.assert_not_called()

    def test_malformed_provenance_is_safe_schema_error(self):
        for kind in ([], {}, None, 1):
            obj = inventory(); obj['record_kind'] = kind
            with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                g.analyze(obj, 'device-1')

    def test_unknown_finding_and_evidence_fields_rejected(self):
        for field in ('findings', 'evidence'):
            obj = inventory()
            obj[field] = [{'unknown_secret': 'SYNTHETIC_MARKER'}]
            with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                g.analyze(obj, 'device-1')

    def test_static_source_credential_alias_rejected_before_read(self):
        marker = 'github_pat_' + 'A' * 30
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'not-read.yaml')
            request = dict(schema_version='guardian-clash-inventory/0.1', target_ref='device-1',
                operation='audit', contact_phase='precontact', gate_state='closed',
                target_binding=dict(binding_state='bound', target_ref='device-1',
                    execution_location='native_local', desktop_user_relation='same',
                    filesystem_namespace='host_desktop', declared_os='macos'),
                authorization=dict(approved_paths=[path], local_hydrated_files=True),
                application=dict(product='clash-verge-rev', gui_version='2.5.5', core_version='1.19.0'),
                files=[dict(source_ref=marker, kind='profile', path=path)])
            with patch.object(c.sys, 'platform', 'darwin'), patch.object(c, '_read') as read:
                result = c.audit_inventory(request, 'device-1')
            self.assertEqual(result['status'], 'blocked')
            self.assertNotIn(marker, json.dumps(result))
            read.assert_not_called()

    def test_static_collector_import_is_independent_of_sibling_path(self):
        code = ("import importlib.util; "
                "s=importlib.util.spec_from_file_location('isolated_inventory', "
                + repr(str(SCRIPTS / 'clash_inventory.py')) + "); "
                "m=importlib.util.module_from_spec(s); s.loader.exec_module(m); "
                "assert m._alias('sk-SK') == 'sk-SK'")
        result = subprocess.run([sys.executable, '-I', '-B', '-c', code],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)

    def test_unhashable_offline_and_inventory_fields_are_fixed_errors(self):
        for imported in (False, True):
            for field in ('id', 'state', 'layer', 'declared_os', 'record_kind', 'snapshot_state'):
                for value in ([], {'unknown_secret': 'SYNTHETIC_MARKER'}):
                    obj = inventory()
                    if not imported:
                        obj = g.inventory_to_offline(obj)
                    if field in ('id', 'state', 'layer'):
                        obj['facts'][0][field] = value
                    elif field == 'declared_os':
                        obj['target_binding'][field] = value
                    else:
                        obj[field] = value
                    with self.subTest(imported=imported, field=field, kind=type(value).__name__):
                        with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                            g.analyze(obj, 'device-1')

    def test_interview_wrapper_rejects_unknown_fields(self):
        for location in ('root', 'contact', 'privacy', 'snapshot', 'limits', 'question'):
            for key in ('command', 'url', 'unknown_secret'):
                obj = g.interview({})
                target = {'root': obj, 'contact': obj['contact_control'],
                          'privacy': obj['privacy'], 'snapshot': obj['snapshot'],
                          'limits': obj['limits'], 'question': obj['question']}[location]
                target[key] = 'SYNTHETIC_MARKER'
                with self.subTest(location=location, key=key):
                    with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                        g.interview(obj)

    def test_interview_wrapper_wrong_question_type_is_fixed_error(self):
        for value in (None, [], 'SYNTHETIC_MARKER'):
            obj = g.interview({}); obj['question'] = value
            with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
                g.interview(obj)

    def test_interview_generated_wrappers_remain_supported(self):
        for answers in ({}, {'subscription_stage': 'existing_subscriber'},
                        {'account_status': 'suspended'}):
            result = g.interview({'answers': answers})
            self.assertEqual(g.interview(result)['state'], result['state'])

    def test_interview_free_choice_question_wrapper_remains_supported(self):
        obj = g.interview({'answers': {'subscription_stage': 'first_subscription',
                                      'os': 'macos', 'usage': 'web'}})
        self.assertEqual(obj['question']['field'], 'target_plan')
        self.assertIsNone(obj['question']['choices'])
        self.assertEqual(g.interview(obj)['question'], obj['question'])

    def test_cancelled_interview_wrapper_cannot_export(self):
        obj = g.interview({'cancelled': True})
        with self.assertRaises(g.GuardianError) as caught:
            g.interview(obj)
        self.assertEqual(caught.exception.code, 'USER_CANCELLED')
        with tempfile.TemporaryDirectory() as directory:
            source, output = Path(directory) / 'input.json', Path(directory) / 'output.json'
            source.write_text(json.dumps(obj))
            result = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'guardian.py'), 'interview',
                '--input', str(source), '--output', str(output)], capture_output=True, text=True, timeout=10)
            self.assertEqual(result.returncode, 3)
            self.assertFalse(output.exists())

    def test_static_nested_unknown_keys_rejected_before_callbacks_or_reads(self):
        with tempfile.TemporaryDirectory() as directory:
            path = str(Path(directory) / 'not-read.yaml')
            for where in ('target_binding', 'authorization', 'application'):
                request = dict(schema_version='guardian-clash-inventory/0.1', target_ref='device-1',
                    operation='audit', contact_phase='precontact', gate_state='closed',
                    target_binding=dict(binding_state='bound', target_ref='device-1',
                        execution_location='native_local', desktop_user_relation='same',
                        filesystem_namespace='host_desktop', declared_os='macos'),
                    authorization=dict(approved_paths=[path], local_hydrated_files=True),
                    application=dict(product='clash-verge-rev', gui_version='2.5.5', core_version='1.19.0'),
                    files=[dict(source_ref='source-1', kind='profile', path=path)])
                request[where]['command'] = 'SYNTHETIC_MARKER'
                with patch.object(c.sys, 'platform', 'darwin'), patch.object(c, '_read') as read:
                    callback = unittest.mock.Mock(return_value=False)
                    result = c.audit_inventory(request, 'device-1', cancel_check=callback)
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['errors'], [{'code': 'INPUT_OR_RESPONSE_INVALID'}])
                self.assertNotIn('SYNTHETIC_MARKER', json.dumps(result))
                read.assert_not_called()
                callback.assert_not_called()

    def test_ordinary_aliases_and_multiple_sources_remain_accepted(self):
        for value in ('task-current-target', 'sk-SK', 'sk-device', 'ghp_short'):
            self.assertEqual(c._alias(value), value)
        obj = inventory()
        obj['facts'][0]['source_refs'] += ['mac-build']
        self.assertTrue(g.analyze(obj, 'device-1')['facts'])


if __name__ == '__main__':
    unittest.main()
