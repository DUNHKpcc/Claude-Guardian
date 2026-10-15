"""Offline OS-resolution projections; runners are injected, no native DNS calls."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import os_dns_probe as mac
import windows_dns_probe as windows
import probe_evidence as evidence
import status_dashboard as dashboard

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)


def result(query_type='A', addresses=None, error=None):
    scope = mac.QueryScope(mac.Binding('private-device', 'private-user', 'private-namespace',
        'darwin', '/private/python', '/private/work'), 'reserved.test', query_type)
    addresses = ['192.0.2.5' if query_type == 'A' else '2001:db8::5'] if addresses is None else addresses
    def runner(*args):
        if error:
            raise mac.ProbeError(error)
        return json.dumps(addresses).encode()
    with patch.object(mac.sys, 'platform', 'darwin'), patch.object(mac, '_run_child', side_effect=runner), \
         patch('socket.getaddrinfo', side_effect=AssertionError('no resolver')), patch('subprocess.Popen', side_effect=AssertionError('no process')):
        raw = mac.probe_os_dns(scope, verify_binding=lambda _: True, verify_runtime=lambda _: True,
                               approve_query=lambda *_: True)
    for fact in raw['facts']:
        fact['observed_at'] = NOW.isoformat()
    return raw



def windows_result(query_type='A', addresses=None, error=None):
    binding = windows.Binding('private-device', 'private-user', 'private-namespace', 'win32',
        r'C:\private\powershell.exe', r'C:\private\DnsClient.psd1', r'C:\private', r'C:\Windows')
    scope = windows.QueryScope(binding, 'reserved.test', query_type)
    addresses = ['192.0.2.5' if query_type == 'A' else '2001:db8::5'] if addresses is None else addresses
    def runner(*args):
        if error:
            raise windows.ProbeError(error)
        return json.dumps(addresses).encode()
    with patch.object(windows.sys, 'platform', 'win32'), patch.object(windows, '_run_child', side_effect=runner), \
         patch('socket.getaddrinfo', side_effect=AssertionError('no resolver')), patch('subprocess.Popen', side_effect=AssertionError('no process')):
        raw = windows.probe_windows_dns(scope, verify_binding=lambda _: True, verify_runtime=lambda _: True,
                                        approve_query=lambda *_: True)
    for fact in raw['facts']:
        fact['observed_at'] = NOW.isoformat()
    return raw


def windows_item(raw=None):
    return dict(result=windows_result() if raw is None else raw, captured_at=NOW.isoformat(),
                context=dict(target_ref='private-device', path_kind='windows_Resolve-DnsName_DnsOnly'),
                expected_path_kind='windows_Resolve-DnsName_DnsOnly')


def item(raw=None):
    return dict(result=result() if raw is None else raw, captured_at=NOW.isoformat(),
                context=dict(target_ref='private-device', path_kind='macos_getaddrinfo'),
                expected_path_kind='macos_getaddrinfo')


def bundle(*items):
    return dict(schema_version=evidence.SCHEMA, target_ref='private-device', samples=list(items))


def report():
    return dict(schema_version='guardian-report/0.1', snapshot={'observed_at': NOW.isoformat()},
                facts=[], findings=[], execution_status='completed')


class OSDnsDashboardTests(unittest.TestCase):
    def project(self, obj):
        return evidence.project_samples(bundle(obj), NOW)[0]

    def test_actual_produced_both_families_no_io_and_private_values(self):
        for kind, family in [('A', 4), ('AAAA', 6)]:
            obj = item(result(kind))
            with patch('socket.getaddrinfo', side_effect=AssertionError()), patch('socket.socket', side_effect=AssertionError()), \
                 patch('subprocess.Popen', side_effect=AssertionError()), patch.object(mac, 'probe_os_dns', side_effect=AssertionError()):
                projected = self.project(obj)
                html = dashboard.render(report(), NOW, bundle(obj))
            self.assertEqual(projected['status'], 'response_observed')
            self.assertEqual(projected['family'], family)
            self.assertIn('macOS 系统解析 getaddrinfo', html)
            self.assertIn('没有 DNS 报文/RCODE 证据', html)
            self.assertNotIn('rcode 0', html)
            for private in ('private-device', 'private-user', 'private-namespace', '/private/python',
                            '/private/work', 'reserved.test', '192.0.2.5', '2001:db8::5'):
                self.assertNotIn(private, html)

    def test_only_dns_row_and_empty_is_not_nxdomain_or_blocking(self):
        obj = item(result(addresses=[]))
        cards = {c['key']: c for c in dashboard.project(report(), NOW, bundle(obj))['cards']}
        self.assertEqual(cards['dns']['state'], 'unknown')
        self.assertEqual(cards['dns']['samples'][0]['dns']['address_count'], 0)
        for key in ('dns_leak', 'ipv4', 'ipv6', 'udp', 'stun', 'browser', 'failure'):
            self.assertEqual(cards[key]['state'], 'not_run')
            self.assertEqual(cards[key]['samples'], [])

    def test_source_coverage_and_family_mismatch_rejected(self):
        for location, key, value in [('raw', 'coverage', 'mihomo_dns_query_sample_only'),
                ('fact', 'source_ref', 'mihomo-dns-query'), ('value', 'resolver_api', 'windows_resolve_dns_name'),
                ('value', 'address_family', 'IPv6'), ('value', 'dns_rcode', 0),
                ('value', 'dns_packet_observed', True)]:
            obj = item(); target = obj['result']
            if location != 'raw': target = target['facts'][0]
            if location == 'value': target = target['value']
            target[key] = value
            with self.subTest(key=key), self.assertRaises(dashboard.GuardianError): self.project(obj)
        obj = item(); obj['result']['schema_version'] = 'guardian-future-dns-probe/0.1'
        with self.assertRaises(dashboard.GuardianError): self.project(obj)

    def test_all_producer_failure_codes_without_facts_remain_visible(self):
        self.assertEqual(mac.ERRORS, evidence.OS_DNS_ERRORS)
        for error in sorted(mac.ERRORS):
            obj = item(result(error=error))
            projected = self.project(obj)
            self.assertIsNone(projected['dns'])
            self.assertNotIn(projected['status'], ('unknown', 'response_observed'))
            html = dashboard.render(report(), NOW, bundle(obj))
            self.assertIn('无解析事实', html)
            self.assertIn(error, html)

    def test_freshness_context_and_authority_are_declarations_only(self):
        for at, state in [(None, 'time_invalid'), ('SECRET', 'time_invalid'),
                ((NOW+timedelta(seconds=1)).isoformat(), 'time_invalid'),
                ((NOW-timedelta(days=2)).isoformat(), 'stale')]:
            obj = item(); obj['result']['facts'][0]['observed_at'] = at
            self.assertEqual(self.project(obj)['status'], state)
        obj = item(); obj.pop('context')
        self.assertEqual(self.project(obj)['status'], 'context_unknown')
        obj = item(); obj['context']['target_ref'] = 'other'
        self.assertEqual(self.project(obj)['status'], 'target_mismatch')
        obj = item(); obj['context']['path_kind'] = 'mihomo_dns_query'
        self.assertEqual(self.project(obj)['status'], 'path_mismatch')
        obj = item(); obj['result'].update(verified=True, authorized=True, provenance='trusted_host')
        self.assertEqual(self.project(obj)['provenance'], 'unverified_import')
        obj = item(result(error='CANCELLED')); obj.pop('captured_at')
        self.assertEqual(self.project(obj)['status'], 'cancelled')
        self.assertIsNone(self.project(obj)['observed_at'])

    def test_malformed_counts_booleans_and_inconsistent_results(self):
        for key, value in [('address_count', True), ('address_count', -1), ('address_count', 129),
                           ('address_count', 0), ('query_type', 'TXT')]:
            obj = item(); obj['result']['facts'][0]['value'][key] = value
            with self.assertRaises(dashboard.GuardianError): self.project(obj)
        for value in (True, -1, 129, 0):
            obj = item(); obj['result']['facts'][0]['value']['address_class_counts']['non_global'] = value
            with self.assertRaises(dashboard.GuardianError): self.project(obj)
        for key, value in [('facts', []), ('facts', {}), ('error_code', 'TIMEOUT'),
                ('requests_attempted', True), ('requests_attempted', 0), ('execution_status', 'partial')]:
            obj = item(); obj['result'][key] = value
            with self.assertRaises(dashboard.GuardianError): self.project(obj)
        obj = item(result(error='TIMEOUT')); obj['result']['facts'] = result()['facts']
        with self.assertRaises(dashboard.GuardianError): self.project(obj)

    def test_existing_findings_and_mixed_outcomes_remain(self):
        items = [item(), item(result(error='TIMEOUT')), item(result(addresses=[]))]
        for code, state in [('INPUT_OR_RESPONSE_INVALID', 'error'), ('AUTHORIZATION_MISSING', 'authorization_needed')]:
            obj = report(); obj['findings'] = [dict(module_id='ENV-04', code=code)]
            card = next(c for c in dashboard.project(obj, NOW, bundle(*items))['cards'] if c['key'] == 'dns')
            self.assertEqual(card['state'], state)
            self.assertEqual([s['status'] for s in card['samples']], ['response_observed', 'timeout', 'response_observed'])

    def test_windows_actual_output_is_distinct_and_no_native_resolver_runs(self):
        for kind, family in [('A', 4), ('AAAA', 6)]:
            obj = windows_item(windows_result(kind))
            projected = self.project(obj)
            self.assertEqual(projected['status'], 'response_observed')
            self.assertEqual(projected['family'], family)
            with patch.object(windows, 'probe_windows_dns', side_effect=AssertionError()), \
                 patch('subprocess.Popen', side_effect=AssertionError()), patch('socket.socket', side_effect=AssertionError()):
                html = dashboard.render(report(), NOW, bundle(obj))
            self.assertIn('Windows 系统解析 Resolve-DnsName -DnsOnly', html)
            self.assertNotIn('macOS 系统解析 getaddrinfo', html)
            for private in ('192.0.2.5', '2001:db8::5', 'reserved.test', 'private-device', 'DnsClient.psd1'):
                self.assertNotIn(private, html)

    def test_windows_errors_and_missing_dependency_preserved(self):
        self.assertEqual(windows.ERRORS, mac.ERRORS | {'DEPENDENCY_MISSING'})
        for error in sorted(windows.ERRORS):
            obj = windows_item(windows_result(error=error))
            self.assertIsNone(self.project(obj)['dns'])
            self.assertNotIn(self.project(obj)['status'], ('unknown', 'response_observed'))
            self.assertIn(error, dashboard.render(report(), NOW, bundle(obj)))
        obj = item(result(error='TIMEOUT')); obj['result']['error_code'] = 'DEPENDENCY_MISSING'
        with self.assertRaises(dashboard.GuardianError): self.project(obj)

    def test_cross_platform_schema_source_api_and_path_rejected_or_mismatch(self):
        for key in ('source_ref', 'resolver_api'):
            obj = windows_item()
            if key == 'source_ref': obj['result']['facts'][0][key] = 'os-system-resolution'
            else: obj['result']['facts'][0]['value'][key] = 'macos_getaddrinfo'
            with self.assertRaises(dashboard.GuardianError): self.project(obj)
        obj = windows_item(); obj['context']['path_kind'] = 'macos_getaddrinfo'
        self.assertEqual(self.project(obj)['status'], 'path_mismatch')
        obj = windows_item(); obj['result']['schema_version'] = 'guardian-os-dns-probe/0.1'
        with self.assertRaises(dashboard.GuardianError): self.project(obj)
        objects = [item(), windows_item()]
        card = next(c for c in dashboard.project(report(), NOW, bundle(*objects))['cards'] if c['key'] == 'dns')
        self.assertEqual([s['endpoint'] for s in card['samples']], ['macos_getaddrinfo', 'windows_Resolve-DnsName_DnsOnly'])

    def test_free_text_and_forged_extra_claims_never_echoed(self):
        marker = '</style><script>SECRET_SENTINEL</script>'
        obj = item(); obj['result']['facts'][0]['value'].update(actual_server=marker, leak_assessment=marker,
            path_association=marker, cache_origin=marker, extra=marker)
        obj['context']['target_ref'] = marker
        raw = bundle(obj); raw['target_ref'] = marker
        html = dashboard.render(report(), NOW, raw)
        self.assertNotIn('SECRET_SENTINEL', html)
        self.assertNotIn('<script', html)
        self.assertIn('服务器和上游路径未知', html)


if __name__ == '__main__':
    unittest.main()
