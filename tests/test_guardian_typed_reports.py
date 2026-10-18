"""Typed offline report boundaries, not native acceptance or universal secret detection.

ENV-T121 partial and §19.5: reserved field IDs must not admit arbitrary values.
P17 explicitly excludes node UUIDs. All sensitive markers here are synthetic.
"""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from types import SimpleNamespace
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / 'skills/claude-guardian/scripts/guardian.py'
SPEC = importlib.util.spec_from_file_location('typed_report_guardian', SCRIPT)
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)

UUID_SENTINEL = '4bb1dcb0-a60d-41aa-908c-37bcbd458a11'


def fixture():
    obj = json.loads((ROOT / 'tests/fixtures/proxy-port-conflict.json').read_text(encoding='utf-8'))
    for fact in obj['facts']:
        fact['observed_at'] = datetime.now(timezone.utc).isoformat()
    return obj


def with_fact(field, value, state='observed'):
    obj = fixture()
    obj['facts'] = [f for f in obj['facts'] if f['id'] != field]
    obj['facts'].append(dict(id=field, value=value, state=state, context_ref='device-1',
                            observed_at=datetime.now(timezone.utc).isoformat(),
                            layer='os_query', source_ref='synthetic-typed-value'))
    return obj


class TypedReportTests(unittest.TestCase):
    def assert_rejected(self, obj):
        with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$'):
            g.analyze(obj, 'device-1', True)

    def test_node_uuid_is_rejected_before_api_report(self):
        self.assert_rejected(with_fact('P17', UUID_SENTINEL))

    def test_node_uuid_is_rejected_before_stdout_and_saved_report(self):
        with tempfile.TemporaryDirectory(prefix='guardian-typed-report-') as temporary:
            directory = Path(temporary)
            source, output = directory / 'input.json', directory / 'output.json'
            source.write_text(json.dumps(with_fact('P17', UUID_SENTINEL)), encoding='utf-8')
            result = subprocess.run([sys.executable, '-B', str(SCRIPT), 'plan', '--target-ref',
                'device-1', '--input', str(source), '--output', str(output)], cwd=directory,
                env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'), capture_output=True,
                text=True, encoding='utf-8', timeout=10)
            self.assertEqual(result.returncode, 2)
            for text in (result.stdout, result.stderr, output.read_text(encoding='utf-8')):
                self.assertNotIn(UUID_SENTINEL, text)
            report = json.loads(result.stdout)
            self.assertEqual(report['execution_status'], 'blocked')
            self.assertEqual(report['inventory_readiness'], 'blocked')
            self.assertEqual(report['facts'], [])
            self.assertNotIn('plan', report)
            self.assertEqual(report['contact_control']['gate_state'], 'closed')
            self.assertEqual(report['changes'], [])
            self.assertEqual(json.loads(output.read_text(encoding='utf-8')), report)

    def test_unimplemented_fields_cannot_echo_arbitrary_scalar_values(self):
        supported = set(g.FACT_ENUMS) | {'S02', 'S03', 'S06', 'S07', 'S08', 'S09', 'P06', 'P09', 'P12'}
        for field in sorted(g.FACT_IDS - supported):
            for value in (UUID_SENTINEL, 'opaque-private-marker', 4111111111111111, True, [], {}):
                with self.subTest(field=field, value_type=type(value).__name__):
                    self.assert_rejected(with_fact(field, value))

    def test_unknown_does_not_create_an_arbitrary_value_channel(self):
        for state in g.STATES:
            with self.subTest(state=state):
                self.assert_rejected(with_fact('P17', UUID_SENTINEL, state))
                self.assert_rejected(with_fact('S01', 'opaque-private-marker', state))

    def test_explicit_valueless_gaps_are_preserved(self):
        for field in sorted(g.FACT_IDS):
            for state in sorted(g.VALUELESS_STATES):
                with self.subTest(field=field, state=state):
                    report = g.analyze(with_fact(field, None, state), 'device-1')
                    fact = next(f for f in report['facts'] if f['id'] == field)
                    self.assertIsNone(fact['value'])
                    self.assertEqual(fact['state'], state)
                    self.assertEqual(report['check_status'], 'unknown')
                    self.assertEqual(report['contact_control']['gate_state'], 'closed')

    def test_observed_reported_or_derived_null_is_not_a_valid_value(self):
        for field in ('S01', 'S06', 'P06', 'P17'):
            for state in ('observed', 'reported', 'derived'):
                with self.subTest(field=field, state=state):
                    self.assert_rejected(with_fact(field, None, state))

    def test_timestamp_aging_cannot_hide_invalid_observed_value(self):
        for delta in (-2, 2):
            obj = with_fact('S01', None)
            obj['facts'][-1]['observed_at'] = (datetime.now(timezone.utc) + timedelta(days=delta)).isoformat()
            self.assert_rejected(obj)

    def test_known_producer_value_contracts_round_trip(self):
        values = {
            'H04': ['same', 'different', 'unknown'],
            'S01': ['macos', 'windows'],
            'S02': ['24.1.0', '10.0.26100', 'macOS-product-15.2',
                    'macOS-product-15.2.1;build-24C101', 'Windows-version-10.0.26100;build-26100'],
            'S03': [0, 100, 10000],
            'S04': ['arm64', 'x86_64', 'aarch64', 'amd64', 'x64', 'x86'],
            'S06': ['', 'en-US', 'zh-Hans-CN,en-US'],
            'S07': ['zh_CN', 'en_US@calendar=gregorian', 'en-US'],
            'S08': ['IANA:Asia:Shanghai', 'IANA:Etc:GMT+1', 'Windows:China Standard Time', 'Windows:UTC'],
            'S09': [-43200, 0, 50400],
            'P06': [{'enabled': True, 'port': 7890}, {'enabled': False, 'port': 7890},
                    'http=enabled;https=disabled;socks=unknown;pac=enabled;wpad=unknown;scoped=present',
                    'user_proxy=unknown;pac_url=absent;winhttp=not_collected'],
            'P09': [{'selected_instance_port': 7897, 'port_owner_matches': True}],
            'P11': ['rule', 'global', 'direct'],
            'P12': [True, False],
        }
        for field, candidates in values.items():
            for value in candidates:
                with self.subTest(field=field, value=value):
                    report = g.analyze(with_fact(field, value), 'device-1')
                    self.assertEqual(next(f['value'] for f in report['facts'] if f['id'] == field), value)

    def test_mac_language_producer_and_importer_share_full_list_budget(self):
        language_lists = [
            ['zh-Hant-TW', 'zh-Hans-CN', 'sr-Latn-RS', 'sr-Cyrl-RS',
             'uz-Latn-UZ', 'uz-Cyrl-UZ', 'az-Latn-AZ', 'az-Cyrl-AZ',
             'pa-Guru-IN', 'pa-Arab-PK', 'mn-Cyrl-MN', 'mn-Mong-CN',
             'bs-Latn-BA', 'bs-Cyrl-BA', 'ff-Latn-SN', 'ha-Latn-NG'],
            # Producer permits 16 tags, each checked against its 160-char budget.
            ['en' + '-abcdef' * 22] * 16,
            ['sk-Latn-SK-fonipa', 'en-US', 'sk-SK'],
        ]
        for languages in language_lists:
            with self.subTest(length=len(','.join(languages))):
                values = {'mac-languages': '(' + ','.join(languages) + ')',
                          'mac-version': '14.7', 'mac-build': '23H124',
                          'mac-locale': 'en_US', 'mac-proxy': '<dictionary> {\n}'}
                with patch.object(g.os, 'uname', return_value=SimpleNamespace(machine='arm64'), create=True), \
                        patch.object(g.os, 'readlink', return_value='/var/db/timezone/zoneinfo/Etc/UTC'):
                    produced, errors = g.extended_inventory('macos', values.__getitem__)
                self.assertEqual(errors, [])
                report = g.base('audit', 'device-1')
                report.update(schema_version='env-inventory/0.2',
                              target_binding=fixture()['target_binding'])
                report['facts'] = [dict(id=field, value=value, state='observed',
                    context_ref='device-1', observed_at=datetime.now(timezone.utc).isoformat(),
                    layer='os_query', source_refs=[source]) for field, value, source in produced]
                imported = g.analyze(report, 'device-1')
                self.assertEqual(next(f['value'] for f in imported['facts'] if f['id'] == 'S06'),
                                 ','.join(languages))
        for value in (','.join(['en-US'] * 17), 'en' + '-abcdef' * 23):
            self.assert_rejected(with_fact('S06', value))

    def test_invalid_supported_values_fail_closed(self):
        values = {'H04': 'private-username', 'S02': 'fixture-kernel', 'S03': True,
                  'S04': 'PRIVATE_ARM_IDENTIFIER', 'S06': UUID_SENTINEL, 'S07': UUID_SENTINEL,
                  'S08': 'opaque-private-marker', 'S09': 4111111111111111, 'P11': 'GLOBAL',
                  'P12': 1, 'P06': {'enabled': True, 'port': 7890, 'raw': UUID_SENTINEL},
                  'P09': {'selected_instance_port': 7897, 'port_owner_matches': 1}}
        for field, value in values.items():
            with self.subTest(field=field):
                self.assert_rejected(with_fact(field, value))

    def test_metadata_qualifiers_are_closed_not_generic_aliases(self):
        for qualifier in ('reason_code', 'coverage'):
            obj = fixture()
            obj['facts'][0][qualifier] = 'opaque-private-marker'
            self.assert_rejected(obj)

    def test_known_credential_prefixes_are_not_report_aliases(self):
        for value in ('ghp_SYNTHETIC_PRIVATE_MARKER', 'github_pat_SYNTHETIC_PRIVATE_MARKER',
                      'sk-SYNTHETIC_PRIVATE_MARKER', 'ref-ghp_SYNTHETIC_PRIVATE_MARKER',
                      'ref-sk-SYNTHETIC_PRIVATE_MARKER'):
            with self.subTest(value=value):
                obj = fixture()
                obj['facts'][0]['source_ref'] = value
                self.assert_rejected(obj)
        # Ordinary task aliases contain the letters sk- but are not key prefixes.
        for value in ('task-1', 'task-current-target', 'task-production-1', 'task-abcdefghijkl',
                      'sk-SK', 'sk-device', 'ghp_short', 'github_pat_short'):
            self.assertEqual(g.alias(value), value)

    def test_embedded_known_tokens_are_rejected_before_direct_api_output(self):
        for prefix in ('ghp_', 'github_pat_', 'sk-', 'sk-ant-'):
            marker = prefix + 'A' * 36
            with self.subTest(prefix=prefix):
                self.assert_rejected(with_fact('S08', 'Windows:' + marker))
        self.assert_rejected(with_fact('S08', 'Windows:Bearer synthetic-private-marker'))
        self.assert_rejected(with_fact('S08', 'IANA:password:synthetic-private-marker'))

    def test_direct_api_validates_target_alias_before_echoing_it(self):
        for prefix in ('ghp_', 'github_pat_', 'sk-', 'sk-ant-', 'ref-ghp_', 'ref-sk-'):
            target = prefix + 'A' * 36
            obj = fixture()
            obj['target_ref'] = target
            for fact in obj['facts']:
                fact['context_ref'] = target
            with self.subTest(prefix=prefix):
                with self.assertRaisesRegex(g.GuardianError, '^INPUT_OR_RESPONSE_INVALID$') as raised:
                    g.analyze(obj, target)
                self.assertNotIn(target, str(raised.exception))

    def test_slovak_language_locale_and_task_alias_remain_valid(self):
        values = [('S06', 'sk-SK'), ('S07', 'sk-SK'),
                  ('S06', 'sk-Latn-SK-fonipa'), ('S07', 'sk-Latn-SK-fonipa'),
                  ('S06', 'en-US,sk-Latn-SK-fonipa,sk-SK')]
        for field, value in values:
            with self.subTest(field=field, value=value):
                obj = with_fact(field, value)
                obj['target_ref'] = 'task-1'
                for fact in obj['facts']:
                    fact['context_ref'] = 'task-1'
                report = g.analyze(obj, 'task-1')
                self.assertEqual(report['target_ref'], 'task-1')
                self.assertEqual(next(f['value'] for f in report['facts'] if f['id'] == field), value)

    def test_long_task_alias_is_preserved_in_direct_api(self):
        for target in ('task-current-target', 'task-production-1', 'task-abcdefghijkl',
                       'sk-SK', 'sk-device', 'ghp_short', 'github_pat_short'):
            obj = fixture()
            obj['target_ref'] = target
            for fact in obj['facts']:
                fact['context_ref'] = target
                fact['source_ref'] = 'task-synthetic-reference'
            report = g.analyze(obj, target)
            self.assertEqual(report['target_ref'], target)
            self.assertTrue(all(f['source_ref'] == 'task-synthetic-reference' for f in report['facts']))

    def test_native_inventory_import_uses_same_typed_boundary(self):
        obj = with_fact('P17', UUID_SENTINEL)
        report = g.base('audit', 'device-1')
        report.update(schema_version='env-inventory/0.2', target_binding=obj['target_binding'],
                      facts=copy.deepcopy(obj['facts']))
        for fact in report['facts']:
            fact['source_refs'] = [fact.pop('source_ref')]
        self.assert_rejected(report)

    def test_native_inventory_known_metadata_remains_compatible(self):
        obj = fixture()
        for field, value in [('S02', '24.1.0'), ('S03', 100), ('S04', 'arm64'),
                             ('S06', 'zh-Hans-CN,en-US'), ('S07', 'zh_CN'),
                             ('S08', 'IANA:Asia:Shanghai'), ('S09', 28800)]:
            obj['facts'].append(with_fact(field, value)['facts'][-1])
        report = g.base('audit', 'device-1')
        report.update(schema_version='env-inventory/0.2', target_binding=obj['target_binding'],
                      facts=copy.deepcopy(obj['facts']))
        for fact in report['facts']:
            fact['source_refs'] = [fact.pop('source_ref')]
            fact.update(reason_code='READ_ONLY_LIMITED_METADATA', coverage='target_os_metadata')
        result = g.analyze(report, 'device-1', True)
        self.assertEqual(len(result['facts']), len(report['facts']))
        self.assertEqual(result['plan']['diff'], [])  # Imported snapshot remains unknown.
        self.assertFalse(result['plan']['executable'])
        self.assertEqual(result['contact_control']['gate_state'], 'closed')

    def test_valid_proxy_plan_contract_is_unchanged(self):
        result = g.analyze(fixture(), 'device-1', True)
        self.assertEqual(result['inventory_readiness'], 'ready_for_configuration_plan')
        self.assertEqual(len(result['plan']['diff']), 1)
        self.assertFalse(result['plan']['executable'])
        self.assertEqual(result['changes'], [])


if __name__ == '__main__':
    unittest.main()
