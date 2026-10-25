"""Offline dashboard projection and local-only CLI regression tests."""
from datetime import datetime, timedelta, timezone
from html.parser import HTMLParser
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


class StructureParser(HTMLParser):
    """Record semantics and only initially visible text, without a browser."""
    def __init__(self):
        super().__init__()
        self.tags = []
        self.visible = []
        self.details_depth = 0
        self.in_summary = False
        self.in_style = False

    def handle_starttag(self, tag, attrs):
        self.tags.append((tag, dict(attrs)))
        if tag == 'details':
            self.details_depth += 1
        if tag == 'summary':
            self.in_summary = True
        if tag == 'style':
            self.in_style = True

    def handle_endtag(self, tag):
        if tag == 'details':
            self.details_depth -= 1
        if tag == 'summary':
            self.in_summary = False
        if tag == 'style':
            self.in_style = False

    def handle_data(self, data):
        if not self.in_style and (not self.details_depth or self.in_summary):
            self.visible.append(data)


class DashboardTests(unittest.TestCase):
    def test_spec_categories_remain_separate_and_explicit(self):
        view = dashboard.project(report(), NOW)
        self.assertEqual([c['key'] for c in view['cards']],
                         ['system', 'proxy', 'tun', 'ipv4', 'ipv6', 'dns', 'dns_leak', 'udp', 'stun', 'browser', 'failure'])
        html = dashboard.render(report(), NOW)
        for text in ['AAAA', 'DoH', 'Fake-IP', 'host/srflx/relay', 'Binding', '路径：未知', 'D-ENV-v0.3']:
            self.assertIn(text, html)

    def test_compact_table_semantics_and_primary_order(self):
        parser = StructureParser(); parser.feed(dashboard.render(report(), NOW))
        rows = [attrs['data-check'] for tag, attrs in parser.tags if tag == 'tr' and 'data-check' in attrs]
        self.assertEqual(rows, ['ipv4', 'ipv6', 'dns_leak', 'udp', 'stun', 'browser', 'tun', 'dns', 'system', 'proxy', 'failure'])
        self.assertEqual(sum(tag == 'table' for tag, _ in parser.tags), 1)
        self.assertEqual(sum(tag == 'caption' for tag, _ in parser.tags), 1)
        self.assertEqual(sum(tag == 'th' and attrs.get('scope') == 'row' for tag, attrs in parser.tags), 11)
        self.assertEqual(sum(tag == 'th' and attrs.get('scope') == 'col' for tag, attrs in parser.tags), 3)
        self.assertFalse(any(tag in {'article', 'script', 'iframe', 'form', 'img', 'link'} for tag, _ in parser.tags))

    def test_evidence_is_native_collapsed_and_main_view_is_brief(self):
        parser = StructureParser(); parser.feed(dashboard.render(report(), NOW))
        details = [attrs for tag, attrs in parser.tags if tag == 'details']
        self.assertEqual(len(details), 12)
        self.assertTrue(all('open' not in attrs for attrs in details))
        self.assertEqual(sum(tag == 'summary' for tag, _ in parser.tags), 12)
        visible = ''.join(parser.visible)
        self.assertIn('合成演示', visible)
        self.assertIn(NOW.isoformat(), visible)
        self.assertIn('系统：macOS', visible)
        self.assertEqual(visible.count('操作权限：'), 1)
        for text in ['D-ENV-v0.3', 'Fake-IP', '证据最早时间', '建议下一步', '状态怎么读', '一眼看清']:
            self.assertNotIn(text, visible)
        self.assertLess(len(visible), 500)

    def test_all_state_labels_are_textual_and_keyboard_focus_visible(self):
        for state, (label, _) in dashboard.STATES.items():
            self.assertIn('>' + label + '</span>', dashboard.badge(state))
        self.assertIn('summary:focus-visible', dashboard.CSS)
        self.assertIn('@media(max-width:520px)', dashboard.CSS)
        self.assertNotIn('min-width:', dashboard.CSS)

    def test_stale_and_non_demo_labels_remain_visible(self):
        obj = report(); obj.pop('record_kind')
        obj['snapshot']['observed_at'] = (NOW-timedelta(days=2)).isoformat()
        parser = StructureParser(); parser.feed(dashboard.render(obj, NOW))
        visible = ''.join(parser.visible)
        self.assertIn('离线快照', visible)
        self.assertIn('时间缺失、过期或无效', visible)
        self.assertNotIn('合成演示', visible)
        self.assertNotIn('macOS', visible)

    def test_execution_failure_is_visible_without_expanding(self):
        for state, label in [('failed', '报告执行失败'), ('blocked', '报告执行受阻'), ('interrupted', '报告执行中断')]:
            obj = report(); obj['execution_status'] = state
            parser = StructureParser(); parser.feed(dashboard.render(obj, NOW))
            self.assertIn(label, ''.join(parser.visible))

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

    def test_native_mac_flag_summary_is_visible_without_becoming_verified(self):
        from guardian import proxy_summary
        obj = report()
        obj['facts'][1]['value'] = proxy_summary('''<dictionary> {
  HTTPEnable : 1
  HTTPSEnable : 0
  HTTPProxy : PRIVATE-ENDPOINT
  ProxyAutoConfigURLString : https://PRIVATE-TOKEN.invalid/
  __SCOPED__ : <dictionary> {
    PRIVATE-INTERFACE : <dictionary> {
      SOCKSEnable : 1
    }
  }
}''')
        view = dashboard.project(obj, NOW)
        text = ' '.join(view['cards'][1]['details'])
        for expected in ('HTTP 开启', 'HTTPS 关闭', 'SOCKS 未知', 'PAC 未知', 'WPAD 未知', '存在，详情未采集', '实际路径另测'):
            self.assertIn(expected, text)
        self.assertNotIn('PRIVATE', dashboard.render(obj, NOW))
        self.assertEqual(view['cards'][1]['state'], 'unknown')
        obj['snapshot']['observed_at'] = (NOW-timedelta(days=2)).isoformat()
        self.assertEqual(dashboard.project(obj, NOW)['cards'][1]['details'], [])

    def test_mac_proxy_projection_rejects_arbitrary_summary_values(self):
        for value in ('http=PRIVATE', 'http=enabled;PRIVATE',
                      'http=enabled;https=disabled;socks=disabled;pac=disabled;wpad=unknown;scoped=not_reported;PRIVATE'):
            self.assertEqual(dashboard.safe_facts([{'id': 'P06', 'value': value}]), [])

    def test_native_process_architecture_is_labeled_as_process_only(self):
        text = dashboard.safe_facts([{'id': 'S04', 'value': 'x86_64', 'coverage': 'current_process_os'}])
        self.assertEqual(text, ['采集进程架构：x86_64'])

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
        # Arbitrary values under known keys are projected away. Unknown keys are rejected instead
        # (see UnknownFieldRejectionTests), so no 'secrets' member is injected here.
        obj = report(); obj.update(target_ref=marker, next_actions=[marker], evidence=[marker])
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


class UnknownFieldRejectionTests(unittest.TestCase):
    """ENV-T121: unknown (possibly secret-bearing) members are rejected at the input boundary.

    Display-layer omission is not a substitute. Markers are synthetic.
    """
    MARKER = 'SYNTHSECRETQ7Z9K2'
    SCHEMAS = ('guardian-report/0.1', 'env-inventory/0.2')

    def injected(self, schema, where, key, value=None):
        obj = report()
        obj['schema_version'] = schema
        obj.setdefault('target_binding', {'declared_os': 'macos', 'desktop_user_relation': 'same',
                                          'filesystem_namespace': 'host_desktop', 'execution_location': 'native_local'})
        obj.setdefault('contact_control', {'contact_phase': 'precontact', 'gate_state': 'closed',
                                           'pc_g1': 'not_verified', 'pc_g2': 'not_run'})
        obj.setdefault('privacy', {'shareable': False})
        obj.setdefault('limits', {'environment_pass_claim': False})
        obj['findings'] = [{'code': 'STALE_EVIDENCE_REAUDIT_REQUIRED', 'module_id': 'ENV-01'}]
        target = obj if where == 'root' else (obj[where][0] if where in ('facts', 'findings') else obj[where])
        target[key] = self.MARKER if value is None else value
        return obj

    def test_unknown_members_rejected_everywhere_without_echo(self):
        places = [('root', 'proxy_password'), ('root', 'subscription_url'), ('root', 'command'),
                  ('root', 'url_to_test'), ('root', 'secrets'), ('snapshot', 'token'),
                  ('target_binding', 'secret'), ('contact_control', 'url'), ('privacy', 'token'),
                  ('limits', 'endpoint'), ('facts', 'password'), ('facts', 'command'),
                  ('findings', 'detail')]
        for schema in self.SCHEMAS:
            for where, key in places:
                with self.subTest(schema=schema, where=where, key=key):
                    obj = self.injected(schema, where, key)
                    with self.assertRaises(dashboard.GuardianError) as ctx:
                        dashboard.project(obj, NOW)
                    self.assertEqual(ctx.exception.code, 'DASHBOARD_REPORT_INVALID')
                    self.assertNotIn(self.MARKER, ctx.exception.code)

    def test_injected_report_with_only_known_members_is_still_accepted(self):
        for schema in self.SCHEMAS:
            with self.subTest(schema=schema):
                obj = self.injected(schema, 'root', 'next_actions', [])
                self.assertIn('overall', dashboard.project(obj, NOW))

    def test_cli_rejects_unknown_member_without_html_or_echo(self):
        for where, key in [('root', 'proxy_password'), ('facts', 'secret')]:
            with self.subTest(where=where), tempfile.TemporaryDirectory() as tmp:
                source, target = Path(tmp)/'report.json', Path(tmp)/'status.html'
                source.write_text(json.dumps(self.injected('guardian-report/0.1', where, key)), encoding='utf-8')
                result = subprocess.run([sys.executable, str(SCRIPTS/'status_dashboard.py'), '--input', str(source),
                                         '--output', str(target)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 2)
                self.assertFalse(target.exists())
                self.assertEqual(result.stderr.strip(), 'DASHBOARD_REPORT_INVALID')
                self.assertNotIn(self.MARKER, result.stdout + result.stderr)

    def test_reports_from_real_producers_remain_accepted(self):
        """Positive control: the shipped analyze/plan producers' output is not rejected."""
        fixture = ROOT / 'tests/fixtures/proxy-port-conflict.json'
        for command in ('analyze', 'plan'):
            with self.subTest(command=command), tempfile.TemporaryDirectory() as tmp:
                saved = Path(tmp)/'report.json'
                made = subprocess.run([sys.executable, str(SCRIPTS/'guardian.py'), command, '--input', str(fixture),
                                       '--target-ref', 'device-1', '--output', str(saved)],
                                      capture_output=True, text=True)
                self.assertEqual(made.returncode, 0, made.stderr)
                html = Path(tmp)/'status.html'
                result = subprocess.run([sys.executable, str(SCRIPTS/'status_dashboard.py'), '--input', str(saved),
                                         '--output', str(html)], capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertTrue(html.exists())


if __name__ == '__main__':
    unittest.main()
