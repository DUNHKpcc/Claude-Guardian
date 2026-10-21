"""Offline probe results -> allowlisted dashboard, not native acceptance."""
from datetime import datetime, timedelta, timezone
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
from environment_entry_fixture import local_entry

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import network_probes as network
import probe_evidence as evidence
import status_dashboard as dashboard
import stun_probe as stun

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
PATH = 'direct_socket_os_route_tun_unknown'


def sample(kind='probe_https'):
    result = dict(sample_type=kind, status='observed', error=None, target_ref='private-device',
                  path_kind=PATH, observed_ip='8.8.8.8', observed_address_family=4)
    if kind == 'probe_https':
        result.update(endpoint_id='ipify_v4', endpoint=network.ENDPOINTS['ipify_v4'][0],
                      expected_address_family=4, started_at=NOW.isoformat(),
                      finished_at=NOW.isoformat(), http_status=200)
    else:
        result.update(endpoint=stun.ENDPOINT, observed_port=12345, cleanup='closed')
    return dict(result=result, expected_path_kind=PATH, captured_at=NOW.isoformat())


def bundle(*samples):
    return dict(schema_version=evidence.SCHEMA, target_ref='private-device', samples=list(samples))


def report():
    return dict(schema_version='guardian-report/0.1', snapshot={'observed_at': NOW.isoformat()},
                facts=[], findings=[], execution_status='completed')


class ProbeEvidenceTests(unittest.TestCase):
    def project(self, value):
        return evidence.project_samples(bundle(value), NOW)[0]

    def test_success_is_only_imported_declaration(self):
        obj = bundle(sample(), sample('independent_stun'))
        # Forged authority members are refused outright rather than ignored (ENV-T121).
        forged = dict(obj, authorized=True, verified=True, provenance='trusted_host')
        with self.assertRaises(evidence.GuardianError):
            dashboard.project(report(), NOW, forged)
        view = dashboard.project(report(), NOW, obj)
        cards = {c['key']: c for c in view['cards']}
        self.assertEqual(cards['ipv4']['samples'][0]['status'], 'observed')
        self.assertEqual(cards['stun']['samples'][0]['status'], 'observed')
        for key in ('ipv4', 'stun'):
            self.assertEqual(cards[key]['state'], 'unknown')
            self.assertIn('未核验', cards[key]['details'][0])
        for key in ('udp', 'browser', 'ipv6', 'dns', 'dns_leak', 'failure'):
            self.assertEqual(cards[key]['state'], 'not_run')
        self.assertEqual(cards['tun']['state'], 'unknown')
        self.assertEqual(view['overall'], 'unknown')

    def test_imported_samples_never_erase_existing_error_or_permission_findings(self):
        for code, expected in [('INPUT_OR_RESPONSE_INVALID', 'error'),
                               ('AUTHORIZATION_MISSING', 'authorization_needed')]:
            obj = report(); obj['findings'] = [dict(module_id='ENV-03', code=code)]
            view = dashboard.project(obj, NOW, bundle(sample()))
            card = next(c for c in view['cards'] if c['key'] == 'ipv4')
            self.assertEqual(card['state'], expected)
            self.assertEqual(card['samples'][0]['status'], 'observed')
            self.assertEqual(len(card['details']), 2)
            if expected == 'error':
                self.assertEqual(view['overall'], 'error')
            self.assertIn('已记录成功声明', dashboard.render(obj, NOW, bundle(sample())))

    def test_cancel_stale_unknown_timeout_permission_and_mismatch_preserved(self):
        cases = [('error', 'cancelled', 'cancelled'), ('error', 'timeout', 'timeout'),
                 ('error', 'permission_denied', 'authorization_needed'),
                 ('error', 'target_changed', 'target_mismatch'),
                 ('target_ref', 'other-device', 'target_mismatch'),
                 ('path_kind', 'explicit_proxy', 'path_mismatch'),
                 ('status', 'unknown', 'unknown'), ('status', 'verified', 'unknown')]
        for key, value, status in cases:
            obj = sample(); obj['result'][key] = value
            with self.subTest(key=key, value=value):
                self.assertEqual(self.project(obj)['status'], status)
        obj = sample(); obj['result']['started_at'] = obj['result']['finished_at'] = (NOW-timedelta(days=2)).isoformat()
        self.assertEqual(self.project(obj)['status'], 'stale')
        obj['result']['error'] = 'cancelled'
        result = self.project(obj)
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['freshness'], 'stale')

    def test_time_never_created_from_render_or_capture_for_https(self):
        for kind in ('probe_https', 'independent_stun'):
            for bad in (None, '', 'SECRET', NOW.replace(tzinfo=None).isoformat(), (NOW+timedelta(seconds=1)).isoformat()):
                obj = sample(kind)
                if kind == 'probe_https':
                    obj['result']['finished_at'] = bad
                else:
                    obj['captured_at'] = bad
                with self.subTest(kind=kind, bad=bad):
                    self.assertEqual(self.project(obj)['status'], 'time_invalid')
        obj = sample(); obj['result']['started_at'] = (NOW+timedelta(seconds=1)).isoformat()
        self.assertEqual(self.project(obj)['status'], 'time_invalid')

    def test_no_last_wins_conflict_or_failure_loss(self):
        old, new = sample(), sample()
        new['result']['error'] = 'cancelled'
        for items in ((old, new), (new, old)):
            card = next(c for c in dashboard.project(report(), NOW, bundle(*items))['cards'] if c['key'] == 'ipv4')
            self.assertEqual({s['status'] for s in card['samples']}, {'observed', 'cancelled'})
            self.assertIn('已取消 1', card['details'][0])
            self.assertIn('已记录成功声明 1', card['details'][0])
            self.assertEqual(card['state'], 'unknown')

    def test_families_separated_and_dual_not_v6_test(self):
        obj = sample(); obj['result'].update(endpoint_id='ipify_dual', endpoint=network.ENDPOINTS['ipify_dual'][0], expected_address_family=None)
        self.assertEqual(self.project(obj)['keys'], ('ipv4',))
        obj['result'].update(observed_address_family=6, observed_ip='2606:4700:4700::1111')
        self.assertEqual(self.project(obj)['keys'], ('ipv6',))
        obj['result'].update(status='unknown', error='timeout', observed_address_family=None)
        self.assertEqual(self.project(obj)['keys'], ('ipv4', 'ipv6'))
        self.assertEqual(self.project(obj)['status'], 'timeout')

    def test_malformed_success_cannot_count(self):
        for key, value in [('observed_ip', 'SECRET'), ('observed_ip', 123),
                           ('observed_ip', '127.0.0.1'), ('observed_address_family', True),
                           ('http_status', True), ('http_status', 500),
                           ('observed_address_family', 6)]:
            obj = sample(); obj['result'][key] = value
            self.assertNotEqual(self.project(obj)['status'], 'observed')
        for key, value in [('cleanup', 'failed'), ('observed_port', True), ('observed_port', 0)]:
            obj = sample('independent_stun'); obj['result'][key] = value
            self.assertNotEqual(self.project(obj)['status'], 'observed')

    def test_no_secret_address_identity_or_markup_survives(self):
        marker = '</style><script>SECRET_SENTINEL</script>'
        # Unknown members are rejected (UnknownMemberRejectionTests); known members with hostile or forged
        # values (path_association is a producer-written member) are projected away here.
        obj = sample(); obj['result'].update(target_ref=marker, error=marker, path_association='verified')
        raw = bundle(obj); raw['target_ref'] = marker
        html = dashboard.render(report(), NOW, raw)
        for secret in ('SECRET_SENTINEL', 'private-device', '8.8.8.8', '<script', 'https://api.ipify.org'):
            self.assertNotIn(secret, html)
        self.assertIn('探测未成功', html)

    def test_bounded_envelope_and_endpoint_types(self):
        for obj in (None, {}, bundle(*([sample()] * 65)), dict(bundle(), samples={}),
                    bundle(None), bundle({'result': []})):
            with self.subTest(obj=type(obj)), self.assertRaises(dashboard.GuardianError):
                evidence.project_samples(obj, NOW)
        for kind in ('probe_https', 'independent_stun'):
            for bad in ([], {}, 'https://secret.invalid'):
                obj = sample(kind); obj['result']['endpoint'] = bad
                with self.assertRaises(dashboard.GuardianError):
                    self.project(obj)

    def test_real_https_output_with_injected_transport(self):
        class Transport:
            path_kind = PATH
            def request(self, url, **kwargs):
                return network.Response(200, b'{"ip":"8.8.8.8"}')
        with patch('socket.socket', side_effect=AssertionError('no sockets')), patch('subprocess.Popen', side_effect=AssertionError('no subprocess')):
            result = network.probe_https_ip('ipify_v4', approved_endpoints=[network.ENDPOINTS['ipify_v4'][0]],
                approved_paths=[PATH], target_ref='private-device', transport=Transport(),
                entry_request=local_entry('private-device'))
            obj = bundle(dict(result=result, expected_path_kind=PATH))
            html = dashboard.render(report(), datetime.now(timezone.utc), obj)
        self.assertIn('已记录成功声明', html)
        self.assertNotIn('8.8.8.8', html)

    def test_real_stun_cancelled_output_without_socket(self):
        scope = stun.Scope('owned-loopback-fixture', '127.0.0.1', 12345, 4, 'private-device')
        with patch('socket.socket', side_effect=AssertionError('no sockets')), patch('subprocess.Popen', side_effect=AssertionError('no subprocess')):
            result = stun.probe_stun(scope, approve=lambda value: value, current_target=lambda: 'private-device', cancelled=lambda: True,
                                     socket_factory=lambda *a: self.fail('socket factory must not run'))
            obj = bundle(dict(result=result, expected_path_kind=PATH, captured_at=NOW.isoformat()))
            html = dashboard.render(report(), NOW, obj)
        self.assertIn('已取消', html)
        self.assertIn('STUN 本地测试夹具', html)

    def test_offline_render_forbids_network_process_and_probe_calls(self):
        with patch('socket.socket', side_effect=AssertionError()), patch('subprocess.Popen', side_effect=AssertionError()), \
             patch.object(network, 'probe_https_ip', side_effect=AssertionError()), patch.object(stun, 'probe_stun', side_effect=AssertionError()):
            self.assertIn('已记录成功声明', dashboard.render(report(), NOW, bundle(sample())))

    def test_cli_explicit_optional_file_and_duplicate_json_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory); src, probes, output = root/'report.json', root/'probes.json', root/'page.html'
            src.write_text(json.dumps(report()), encoding='utf-8')
            probes.write_text(json.dumps(bundle(sample())), encoding='utf-8')
            cmd = [sys.executable, str(SCRIPTS/'status_dashboard.py'), '--input', str(src), '--probes', str(probes), '--output', str(output)]
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertIn('样本 1', output.read_text(encoding='utf-8'))
            output.unlink()
            probes.write_text('{"samples":[],"samples":[]}', encoding='utf-8')
            result = subprocess.run(cmd, capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse(output.exists())


class UnknownMemberRejectionTests(unittest.TestCase):
    """ENV-T121: probe evidence with members outside the release vocabulary is rejected, never ignored.

    JSON provenance/approval/verified members remain unable to grant authority because they are
    refused outright. Markers are synthetic.
    """
    MARKER = 'SYNTHSECRETQ7Z9K2'

    def check(self, mutate, kind='probe_https'):
        raw = bundle(sample(kind))
        mutate(raw)
        with self.assertRaises(evidence.GuardianError) as ctx:
            evidence.project_samples(raw, NOW)
        self.assertEqual(ctx.exception.code, 'DASHBOARD_PROBE_REPORT_INVALID')

    def test_unknown_members_rejected_at_every_level(self):
        marker = self.MARKER
        cases = {
            'bundle': lambda r: r.update(proxy_password=marker),
            'sample item': lambda r: r['samples'][0].update(subscription_url=marker),
            'sample verified flag': lambda r: r['samples'][0].update(verified=True),
            'context': lambda r: r['samples'][0].update(context={'target_ref': 'private-device', 'token': marker}),
            'https result': lambda r: r['samples'][0]['result'].update(command=marker),
            'https result verified flag': lambda r: r['samples'][0]['result'].update(verified=True),
        }
        for name, mutate in cases.items():
            with self.subTest(level=name):
                self.check(mutate)

    def test_unknown_member_in_stun_and_dns_results_rejected(self):
        self.check(lambda r: r['samples'][0]['result'].update(secret=self.MARKER), kind='independent_stun')
        for result in ({'schema_version': 'guardian-os-dns-probe/0.1', 'operation': 'probe', 'gate_state': 'closed',
                        'coverage': 'macos_system_resolution_sample_only', 'facts': [], 'requests_attempted': 0,
                        'execution_status': 'blocked', 'error_code': 'AUTHORIZATION_MISSING',
                        'password': self.MARKER},
                       {'schema_version': 'guardian-mihomo-dns-probe/0.1', 'operation': 'probe', 'gate_state': 'closed',
                        'coverage': 'mihomo_dns_query_sample_only', 'facts': [], 'requests_attempted': 0,
                        'execution_status': 'blocked', 'error_code': 'AUTHORIZATION_MISSING',
                        'password': self.MARKER}):
            with self.subTest(schema=result['schema_version']):
                raw = bundle(dict(result=result, captured_at=NOW.isoformat()))
                with self.assertRaises(evidence.GuardianError) as ctx:
                    evidence.project_samples(raw, NOW)
                self.assertEqual(ctx.exception.code, 'DASHBOARD_PROBE_REPORT_INVALID')

    def test_known_member_samples_still_projected(self):
        for kind in ('probe_https', 'independent_stun'):
            with self.subTest(kind=kind):
                self.assertEqual(len(evidence.project_samples(bundle(sample(kind)), NOW)), 1)

    def test_cli_rejects_unknown_probe_member_without_html_or_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp)
            (root / 'report.json').write_text(json.dumps(report()), encoding='utf-8')
            raw = bundle(sample()); raw['samples'][0]['result']['command'] = self.MARKER
            (root / 'probes.json').write_text(json.dumps(raw), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPTS / 'status_dashboard.py'), '--input', str(root / 'report.json'),
                                     '--probes', str(root / 'probes.json'), '--output', str(root / 'out.html')],
                                    capture_output=True, text=True)
            self.assertNotEqual(result.returncode, 0)
            self.assertFalse((root / 'out.html').exists())
            self.assertNotIn(self.MARKER, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
