"""Offline dashboard projection and local-only CLI regression tests."""
from datetime import datetime, timedelta, timezone
import importlib.util
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
import status_dashboard as dashboard

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def report():
    return {'schema_version': 'guardian-report/0.1', 'record_kind': 'synthetic_example',
            'execution_status': 'completed', 'snapshot': {'observed_at': NOW.isoformat()},
            'facts': [{'id': 'S01', 'state': 'observed', 'value': 'macos', 'observed_at': NOW.isoformat()},
                      {'id': 'P06', 'state': 'observed', 'value': {'enabled': False}, 'observed_at': NOW.isoformat()}],
            'findings': []}


class DashboardTests(unittest.TestCase):
    def test_spec_categories_remain_separate_and_explicit(self):
        view = dashboard.project(report(), NOW)
        self.assertEqual([c['key'] for c in view['cards']],
                         ['system', 'proxy', 'tun', 'ipv4', 'ipv6', 'dns', 'dns_leak', 'udp', 'stun', 'browser', 'failure'])
        html = dashboard.render(report(), NOW)
        for text in ['AAAA', 'DoH', 'Fake-IP', 'host/srflx/relay', 'Binding', '路径：未知', 'D-ENV-v0.3']:
            self.assertIn(text, html)

    def test_duplicate_fact_ids_rejected(self):
        for field, values in [('S01', ['macos', 'windows']), ('P12', [True, False]), ('S01', ['macos', 'macos'])]:
            obj = report()
            obj['facts'] = [dict(id=field, value=value, state='observed', observed_at=NOW.isoformat()) for value in values]
            with self.subTest(field=field, values=values), self.assertRaises(dashboard.GuardianError):
                dashboard.project(obj, NOW)

    def test_unknown_ids_never_count_as_evidence(self):
        obj = report()
        obj['facts'] = [dict(id='S24', value='macos', state='observed', observed_at=NOW.isoformat())]
        card = dashboard.project(obj, NOW)['cards'][0]
        self.assertEqual(card['observed'], 0)
        self.assertEqual(card['total'], 0)
        self.assertEqual(card['details'], [])

    def test_invalid_fact_identifier_type_rejected(self):
        for value in [None, [], {}, 1]:
            obj = report(); obj['facts'][0]['id'] = value
            with self.subTest(value=value), self.assertRaises(dashboard.GuardianError):
                dashboard.project(obj, NOW)

    def test_native_inventory_snapshot_supported(self):
        obj = report(); obj["schema_version"] = "env-inventory/0.2"
        self.assertEqual(dashboard.project(obj, NOW)["overall"], "unknown")

    def test_completed_never_means_verified(self):
        obj = report(); obj['check_status'] = 'verified'
        view = dashboard.project(obj, NOW)
        self.assertEqual(view['overall'], 'unknown')
        self.assertTrue(all(c['state'] != 'verified' for c in view['cards']))
        self.assertEqual([c['state'] for c in view['cards'][3:]], ['not_run'] * 8)

    def test_narrow_facts_and_false_proxy_not_error(self):
        view = dashboard.project(report(), NOW)
        self.assertEqual(view['cards'][0]['details'], ['系统：macOS'])
        self.assertIn('关闭', view['cards'][1]['details'][0])
        self.assertEqual(view['cards'][1]['state'], 'unknown')

    def test_conflict_and_authorization_are_distinct(self):
        obj = report(); obj['findings'] = [
            {'module_id': 'ENV-02', 'code': 'PROXY_PORT_ASSOCIATION_CONFLICT'},
            {'module_id': 'ENV-01', 'code': 'PERMISSION_DENIED'}]
        view = dashboard.project(obj, NOW)
        self.assertEqual(view['overall'], 'error')
        self.assertEqual(view['cards'][0]['state'], 'authorization_needed')
        self.assertEqual(view['cards'][1]['state'], 'error')

    def test_timestamp_never_refreshes_old_fact(self):
        for value in [None, '', 'private-secret', (NOW-timedelta(days=2)).isoformat(), (NOW+timedelta(days=1)).isoformat()]:
            with self.subTest(value=value):
                obj = report(); obj['facts'][0]['observed_at'] = value
                card = dashboard.project(obj, NOW)['cards'][0]
                self.assertEqual(card['observed'], 0)
                self.assertEqual(card['details'], [])

    def test_stale_snapshot_hides_facts(self):
        obj = report(); obj['snapshot']['observed_at'] = (NOW-timedelta(days=2)).isoformat()
        view = dashboard.project(obj, NOW)
        self.assertFalse(view['snapshot_fresh'])
        self.assertEqual(view['cards'][0]['details'], [])

    def test_reported_and_unknown_not_observed(self):
        for state in ['reported', 'unknown', 'stale', 'not_applicable']:
            obj = report(); obj['facts'][0]['state'] = state
            self.assertEqual(dashboard.project(obj, NOW)['cards'][0]['details'], [])

    def test_no_arbitrary_text_or_secrets_survive(self):
        marker = '</style><script>alert("SECRET_SENTINEL")</script>'
        obj = report(); obj.update(target_ref=marker, next_actions=[marker], evidence=[marker], secrets=marker)
        obj['facts'][0].update(value=marker, source_ref=marker, context_ref=marker)
        obj['findings'] = [{'code': marker, 'module_id': marker}]
        obj['snapshot']['observed_at'] = marker
        html = dashboard.render(obj, NOW)
        for token in ['SECRET_SENTINEL', '<script', 'src=', 'href=', 'fetch(', '<iframe', '<form']:
            self.assertNotIn(token, html)
        self.assertIn("default-src 'none'", html)
        self.assertIn('viewport', html)
        self.assertIn('合成演示', html)

    def test_strict_boolean_and_enum_values(self):
        obj = report(); obj['facts'][1]['value'] = {'enabled': 'secret'}
        self.assertEqual(dashboard.project(obj, NOW)['cards'][1]['details'], [])
        obj['facts'][0]['value'] = ['macos']
        self.assertEqual(dashboard.project(obj, NOW)['cards'][0]['details'], [])

    def test_invalid_schema_and_structure(self):
        for obj in [{}, {'schema_version': 'other'}, dict(report(), facts=[None]), dict(report(), snapshot=[]), dict(report(), findings='secret')]:
            with self.subTest(obj=obj), self.assertRaises(dashboard.GuardianError):
                dashboard.project(obj, NOW)

    def test_unknown_execution_and_invalid_codes_are_not_echoed(self):
        obj = report(); obj['execution_status'] = {'secret': 'foo'}
        obj['findings'] = [{'module_id': 'ENV-01', 'code': []}]
        self.assertEqual(dashboard.project(obj, NOW)['execution'], '执行状态未知')

    def test_render_has_no_network_or_collector_calls(self):
        with patch('socket.socket', side_effect=AssertionError('network forbidden')), patch('subprocess.run', side_effect=AssertionError('process forbidden')):
            self.assertIn('环境状态', dashboard.render(report(), NOW))

    def test_cli_explicit_output_no_overwrite_and_private_permissions(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp)/'report.json', Path(tmp)/'status.html'
            source.write_text(json.dumps(report()), encoding='utf-8')
            cmd = [sys.executable, str(SCRIPTS/'status_dashboard.py'), '--input', str(source), '--output', str(target)]
            first = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(first.returncode, 0, first.stderr)
            before = target.read_bytes()
            second = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(second.returncode, 3)
            self.assertEqual(target.read_bytes(), before)
            if sys.platform != 'win32':
                self.assertEqual(target.stat().st_mode & 0o777, 0o600)

    def test_cli_malformed_or_duplicate_json_no_output(self):
        with tempfile.TemporaryDirectory() as tmp:
            source, target = Path(tmp)/'bad.json', Path(tmp)/'status.html'
            for data in ['SECRET_SENTINEL', '{"schema_version":1,"schema_version":2}']:
                source.write_text(data, encoding='utf-8')
                result = subprocess.run([sys.executable, str(SCRIPTS/'status_dashboard.py'), '--input', str(source), '--output', str(target)], capture_output=True, text=True)
                self.assertNotEqual(result.returncode, 0)
                self.assertFalse(target.exists())
                self.assertNotIn('SECRET_SENTINEL', result.stderr)


if __name__ == '__main__':
    unittest.main()
