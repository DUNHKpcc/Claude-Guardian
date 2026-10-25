"""Mihomo DNS -> offline panel; all results use injected bytes, never queries."""
import copy
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import mihomo_dns_probe as mihomo
import probe_evidence as evidence
import status_dashboard as dashboard

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
PATH = 'mihomo_dns_query'


def result(query_type='A', rcode=0, truncated=False, error=None):
    binding = mihomo.ControllerBinding(target_ref='private-device', namespace_ref='private-namespace',
        desktop_user_ref='private-user', instance_ref='private-instance', process_id=123,
        process_start_ref='private-start', host='127.0.0.1', port=54321)
    scope = mihomo.QueryScope(binding, 'reserved.test', query_type)
    kind = 1 if query_type == 'A' else 28
    payload = {'Status': rcode, 'TC': truncated,
               'Question': [{'Name': 'reserved.test.', 'Qtype': kind, 'Qclass': 1}],
               'Answer': [] if rcode else [{'name': 'reserved.test.', 'type': kind, 'TTL': 60,
                            'data': '192.0.2.5' if kind == 1 else '2001:db8::5'}]}
    def transport(*args):
        if error:
            raise mihomo.controller.ControllerError(error)
        return 200, json.dumps(payload).encode()
    with patch('socket.socket', side_effect=AssertionError('no socket')), patch('socket.getaddrinfo', side_effect=AssertionError('no resolver')):
        raw = mihomo.probe_mihomo_dns(scope, verify_binding=lambda _: True,
            approve_query=lambda *_: True, transport=transport)
    for fact in raw['facts']:
        fact['observed_at'] = NOW.isoformat()
    return raw


def item(raw=None):
    return dict(result=result() if raw is None else raw, captured_at=NOW.isoformat(),
                context=dict(target_ref='private-device', path_kind=PATH), expected_path_kind=PATH)


def bundle(*samples):
    return dict(schema_version=evidence.SCHEMA, target_ref='private-device', samples=list(samples))


def report():
    return dict(schema_version='guardian-report/0.1', snapshot={'observed_at': NOW.isoformat()},
                facts=[], findings=[], execution_status='completed')


class MihomoDashboardTests(unittest.TestCase):
    def project(self, obj):
        return evidence.project_samples(bundle(obj), NOW)[0]

    def test_real_output_both_families_without_network_or_secret(self):
        for query_type, family in [('A', 4), ('AAAA', 6)]:
            obj = item(result(query_type))
            with patch('socket.socket', side_effect=AssertionError()), patch('socket.getaddrinfo', side_effect=AssertionError()), \
                 patch('subprocess.Popen', side_effect=AssertionError()), patch.object(mihomo, 'probe_mihomo_dns', side_effect=AssertionError()):
                sample = self.project(obj)
                html = dashboard.render(report(), NOW, bundle(obj))
            self.assertEqual(sample['status'], 'response_observed')
            self.assertEqual(sample['family'], family)
            self.assertIn('rcode 0', html)
            self.assertIn('非全局地址类 1', html)
            self.assertIn('已记录响应声明', html)
            for secret in ('reserved.test', '192.0.2.5', '2001:db8::5', 'private-device', 'private-instance', '54321'):
                self.assertNotIn(secret, html)

    def test_dns_sample_never_promotes_leak_or_other_rows(self):
        cards = {c['key']: c for c in dashboard.project(report(), NOW, bundle(item()))['cards']}
        self.assertEqual(cards['dns']['state'], 'unknown')
        self.assertEqual(cards['dns']['samples'][0]['keys'], ('dns',))
        for key in ('dns_leak', 'ipv4', 'ipv6', 'udp', 'stun', 'browser', 'failure'):
            self.assertEqual(cards[key]['state'], 'not_run')
            self.assertEqual(cards[key]['samples'], [])

    def test_negative_and_truncated_are_responses_not_success(self):
        for rcode, truncated in [(3, False), (2, True), (0, True)]:
            obj = item(result(rcode=rcode, truncated=truncated))
            self.assertEqual(self.project(obj)['status'], 'response_observed')
            html = dashboard.render(report(), NOW, bundle(obj))
            self.assertIn('rcode %d' % rcode, html)
            self.assertIn('截断 ' + ('是' if truncated else '否'), html)
            self.assertNotIn('已记录成功声明', html)

    def test_failure_without_facts_preserves_specific_outcome(self):
        for error, status in [('CANCELLED', 'cancelled'), ('TIMEOUT', 'timeout'),
                ('AUTHORIZATION_MISSING', 'authorization_needed'), ('PERMISSION_DENIED', 'authorization_needed'),
                ('AUTHENTICATION_HANDOFF_REQUIRED', 'authorization_needed'),
                ('CONTROLLER_NOT_BOUND', 'target_mismatch'), ('RESPONSE_CONTEXT_MISMATCH', 'target_mismatch'),
                ('INPUT_OR_RESPONSE_INVALID', 'error'), ('PC0_TARGET_FORBIDDEN', 'error')]:
            obj = item(result(error=error))
            with self.subTest(error=error):
                self.assertEqual(obj['result']['facts'], [])
                self.assertEqual(self.project(obj)['status'], status)
                self.assertIsNone(self.project(obj)['dns'])
                self.assertIn('无响应事实', dashboard.render(report(), NOW, bundle(obj)))

    def test_existing_errors_and_authorization_findings_not_hidden(self):
        for code, status in [('INPUT_OR_RESPONSE_INVALID', 'error'), ('AUTHORIZATION_MISSING', 'authorization_needed')]:
            obj = report(); obj['findings'] = [dict(module_id='ENV-04', code=code)]
            cards = {c['key']: c for c in dashboard.project(obj, NOW, bundle(item()))['cards']}
            self.assertEqual(cards['dns']['state'], status)
            self.assertEqual(cards['dns']['samples'][0]['status'], 'response_observed')

    def test_context_absent_or_mismatched_never_synthesized(self):
        obj = item(); obj.pop('context')
        self.assertEqual(self.project(obj)['status'], 'context_unknown')
        obj['context'] = dict(target_ref='another-device', path_kind=PATH)
        self.assertEqual(self.project(obj)['status'], 'target_mismatch')
        obj['context']['target_ref'] = 'private-device'; obj['context']['path_kind'] = 'explicit_proxy'
        self.assertEqual(self.project(obj)['status'], 'path_mismatch')
        obj = item(); obj.pop('expected_path_kind')
        self.assertEqual(self.project(obj)['status'], 'context_unknown')
        obj = item(); obj.update(authorized=True, verified=True, provenance='trusted_host')
        with self.assertRaises(evidence.GuardianError):  # forged authority members are refused, not ignored
            self.project(obj)
        self.assertEqual(self.project(item())['provenance'], 'unverified_import')

    def test_time_missing_future_stale_cancel_remains_explicit(self):
        for at, expected in [(None, 'time_invalid'), ('SECRET', 'time_invalid'),
                ((NOW+timedelta(seconds=1)).isoformat(), 'time_invalid'),
                ((NOW-timedelta(days=2)).isoformat(), 'stale')]:
            obj = item(); obj['result']['facts'][0]['observed_at'] = at
            self.assertEqual(self.project(obj)['status'], expected)
        obj = item(result(error='CANCELLED')); obj.pop('captured_at')
        projected = self.project(obj)
        self.assertEqual(projected['status'], 'cancelled')
        self.assertIsNone(projected['observed_at'])
        self.assertEqual(projected['freshness'], 'invalid')

    def test_strict_bounded_counts_rcode_types_and_invariants(self):
        for key, bad in [('rcode', True), ('rcode', -1), ('rcode', 4096),
                ('truncated', 'false'), ('question_matches', 'true'),
                ('answer_count', 257), ('address_count', True), ('cname_count', -1),
                ('answer_count', 0), ('query_type', 'TXT'), ('address_family', 'IPv6')]:
            obj = item(); obj['result']['facts'][0]['value'][key] = bad
            with self.subTest(key=key, bad=bad), self.assertRaises(dashboard.GuardianError):
                self.project(obj)
        for bad in (True, -1, 257, 0):
            obj = item(); obj['result']['facts'][0]['value']['address_class_counts']['non_global'] = bad
            with self.assertRaises(dashboard.GuardianError):
                self.project(obj)

    def test_invalid_structure_and_inconsistent_completion_rejected(self):
        cases = [('facts', {}), ('facts', []), ('execution_status', 'partial'),
                 ('requests_attempted', True), ('requests_attempted', 0),
                 ('error_code', 'SECRET'), ('error_code', 'TIMEOUT'),
                 ('operation', 'audit'), ('coverage', 'dns_leak_free'), ('gate_state', 'open')]
        for key, value in cases:
            obj = item(); obj['result'][key] = value
            with self.subTest(key=key), self.assertRaises(dashboard.GuardianError):
                self.project(obj)
        obj = item(); obj['result']['facts'] *= 2
        with self.assertRaises(dashboard.GuardianError): self.project(obj)
        obj = item(result(error='TIMEOUT')); obj['result']['facts'] = result()['facts']
        with self.assertRaises(dashboard.GuardianError): self.project(obj)

    def test_unexpected_strings_html_secrets_never_echoed(self):
        marker = '</style><script>SECRET_SENTINEL</script>'
        unknown = item(); unknown['result']['extra'] = marker
        with self.assertRaises(evidence.GuardianError) as ctx:  # unknown result member: refused, not echoed
            dashboard.render(report(), NOW, bundle(unknown))
        self.assertNotIn('SECRET_SENTINEL', ctx.exception.code)
        obj = item()
        obj['result']['facts'][0]['value'].update(secret=marker, question_ref=marker, cache_origin=marker, fake_ip_assessment=marker)
        obj['context']['target_ref'] = marker
        raw = bundle(obj); raw['target_ref'] = marker
        html = dashboard.render(report(), NOW, raw)
        for forbidden in ('SECRET_SENTINEL', '<script', 'href=', 'src='):
            self.assertNotIn(forbidden, html)
        self.assertIn('缓存来源、Fake-IP 和上游路径还要另查泄露', html)

    def test_mixed_outcomes_preserved_in_original_order(self):
        items = [item(), item(result(error='TIMEOUT')), item(result(rcode=3))]
        card = next(c for c in dashboard.project(report(), NOW, bundle(*items))['cards'] if c['key'] == 'dns')
        self.assertEqual([s['status'] for s in card['samples']], ['response_observed', 'timeout', 'response_observed'])
        self.assertIn('已记录响应声明 2', card['details'][0])
        self.assertIn('超时', card['details'][0])


if __name__ == '__main__':
    unittest.main()
