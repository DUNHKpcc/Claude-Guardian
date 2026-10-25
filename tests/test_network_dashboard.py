"""Dashboard cards filled from a network_check.py report (--network)."""
import copy
from datetime import datetime, timedelta, timezone
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import probe_evidence
import status_dashboard as dashboard

NOW = datetime(2026, 10, 25, 12, tzinfo=timezone.utc)


def base_report():
    return {'schema_version': 'guardian-report/0.1', 'record_kind': 'offline_analysis',
            'execution_status': 'completed', 'snapshot': {'observed_at': NOW.isoformat()},
            'facts': [], 'findings': []}


def network(status='pass', checked=NOW):
    return {'schema_version': 'guardian-network-check/0.1', 'platform': 'macos', 'target_ref': 'mac-a',
            'home_country': 'cn', 'checked_at': checked.strftime('%Y-%m-%dT%H:%M:%SZ'), 'endpoints': [],
            'overall': 'pass' if status == 'pass' else 'fail',
            'results': {
                'route': {'status': status, 'via_tun': 'yes' if status == 'pass' else 'no', 'interface': 'utun4'},
                'exit_ipv4': {'status': status, 'country': 'us', 'asn': 'AS64500 Example', 'family': 'ipv4'},
                'ipv6': {'status': status, 'probe': 'unreachable' if status == 'pass' else 'reachable'},
                'dns_leak': {'status': status, 'servers': [{'country': 'us' if status == 'pass' else 'cn',
                                                            'asn': 'AS13335 CloudFlare Inc'}], 'fake_ip': 'yes'},
                'udp': {'status': status, 'udp': 'open', 'same_exit_as_tcp': status == 'pass'},
                'failure_drill': {'status': 'not_run'}, 'webrtc': {'status': 'not_run'}}}


class NetworkDashboardTests(unittest.TestCase):
    def cards(self, net):
        return {c['key']: c for c in dashboard.project(base_report(), NOW, net)['cards']}

    def test_measured_passes_show_as_verified(self):
        cards = self.cards(network())
        for key in ('tun', 'ipv4', 'ipv6', 'dns_leak', 'dns', 'udp', 'stun'):
            self.assertEqual(cards[key]['state'], 'verified', key)
        self.assertEqual(cards['failure']['state'], 'not_run')
        self.assertEqual(cards['browser']['state'], 'not_run')
        self.assertIn('已堵住，只走 IPv4', cards['ipv6']['details'][0])
        html = dashboard.render(base_report(), NOW, network())
        self.assertIn('已验证', html)
        self.assertIn('IPv4_ONLY，整机只走 IPv4，IPv6 关闭', html)
        self.assertNotIn('整机IPv6不关', html)

    def test_failures_show_as_problems(self):
        cards = self.cards(network('fail'))
        for key in ('tun', 'ipv4', 'ipv6', 'dns_leak', 'udp'):
            self.assertEqual(cards[key]['state'], 'error', key)
        self.assertIn('有解析服务器在本国', cards['dns_leak']['details'][0])

    def test_stale_or_future_results_are_unknown(self):
        for checked in (NOW - timedelta(hours=25), NOW + timedelta(minutes=5)):
            cards = self.cards(network(checked=checked))
            self.assertEqual(cards['ipv4']['state'], 'unknown')
        self.assertIn('超过 24 小时', self.cards(network(checked=NOW - timedelta(hours=25)))['ipv4']['details'][0])

    def test_without_a_network_report_cards_stay_not_run(self):
        cards = self.cards(None)
        self.assertEqual(cards['dns_leak']['state'], 'not_run')

    def test_invalid_network_reports_are_refused(self):
        bad = []
        for mutate in (lambda r: r.update(schema_version='x'), lambda r: r['results'].pop('udp'),
                       lambda r: r['results']['udp'].update(status='great'), lambda r: r.update(checked_at='yesterday'),
                       lambda r: r['results'].update(extra={'status': 'pass'}), lambda r: r.update(platform='ios')):
            item = network()
            mutate(item)
            bad.append(item)
        for item in bad + [[], 'x']:
            with self.assertRaises(dashboard.GuardianError):
                dashboard.project(base_report(), NOW, item)

    def test_real_network_check_report_round_trips(self):
        import network_check as nc
        with patch.object(nc, 'https_get', side_effect=OSError('offline')), \
                patch.object(nc, 'check_route', return_value={'status': 'pass', 'via_tun': 'yes', 'interface': 'utun4'}), \
                patch.object(nc, 'check_fake_ip', return_value='unknown'), \
                patch.object(nc, 'check_udp', return_value={'status': 'error'}), \
                patch.object(nc, 'system_name', return_value='macos'):
            report, _ = nc.run('mac-a')
        report['checked_at'] = NOW.strftime('%Y-%m-%dT%H:%M:%SZ')
        cards = probe_evidence.project_network(json.loads(json.dumps(report)), NOW)
        self.assertEqual(cards['tun']['state'], 'verified')
        self.assertEqual(cards['ipv4']['state'], 'unknown')  # could not reach the test site

    def test_cli_flag(self):
        with tempfile.TemporaryDirectory() as tmp:
            src, net, out = (os.path.join(tmp, n) for n in ('r.json', 'n.json', 'd.html'))
            Path(src).write_text(json.dumps(base_report()), encoding='utf-8')
            fresh = network(checked=datetime.now(timezone.utc))
            Path(net).write_text(json.dumps(fresh), encoding='utf-8')
            with patch('sys.stdout', io.StringIO()):
                self.assertEqual(dashboard.main(['--input', src, '--network', net, '--output', out]), 0)
            self.assertIn('network_check.py 实测', Path(out).read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
