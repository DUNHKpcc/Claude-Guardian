"""Basic network check: pure judgement and wiring with the network mocked out."""
import io
import ipaddress
import json
import os
from pathlib import Path
import socket
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import egress_verifier
import network_check as nc
import stun_probe

EXIT = '203.0.113.7'


class Console(io.StringIO):
    def __init__(self, tty=True):
        super().__init__()
        self.tty = tty

    def isatty(self):
        return self.tty

    def readline(self):
        return '\n'


def fake_https(responses):
    def get(host, path, family=socket.AF_INET, timeout=10, proxy=None):
        key = (host, path.split('?')[0].rsplit('/', 1)[0] if 'dnsleak' in path else path, proxy is not None)
        value = responses.get(key, responses.get((host, path, proxy is not None)))
        if isinstance(value, Exception):
            raise value
        if value is None:
            raise OSError('unreachable')
        return value
    return get


GOOD = {('ipinfo.io', '/json', False): json.dumps({'ip': EXIT, 'country': 'US', 'org': 'AS64500 Example'}),
        ('ipinfo.io', '/json', True): json.dumps({'ip': EXIT, 'country': 'US', 'org': 'AS64500 Example'}),
        ('api6.ipify.org', '/?format=json', False): OSError('no ipv6'),
        ('bash.ws', '/id', False): 'abcdef123456',
        ('bash.ws', '/dnsleak/test', False): json.dumps([
            {'ip': EXIT, 'country': 'us', 'asn': 'AS64500 Example', 'type': 'ip'},
            {'ip': '192.0.2.53', 'country': 'us', 'asn': 'AS13335 CloudFlare Inc', 'type': 'dns'},
            {'ip': 'DNS may be leaking.', 'country': '', 'asn': '', 'type': 'conclusion'}])}


class NetworkCheckTests(unittest.TestCase):
    def patched(self, responses=GOOD, route=('yes', 'utun4'), udp=EXIT, fake_ip='yes'):
        stack = [patch.object(nc, 'https_get', side_effect=fake_https(responses)),
                 patch.object(nc, 'check_route', return_value={'status': 'pass' if route[0] == 'yes' else 'fail',
                                                               'via_tun': route[0], 'interface': route[1]}),
                 patch.object(nc, 'check_fake_ip', return_value=fake_ip),
                 patch.object(nc, 'system_name', return_value='macos'),
                 patch.object(nc.time, 'sleep'),
                 patch.object(nc.socket, 'create_connection', side_effect=OSError('x')),
                 patch.object(nc.socket, 'getaddrinfo', side_effect=OSError('x'))]
        if udp is None:
            stack.append(patch.object(nc, 'check_udp', return_value={'status': 'warn', 'udp': 'blocked'}))
        else:
            stack.append(patch.object(nc, 'check_udp', side_effect=lambda exit_address: {
                'status': 'pass' if udp == exit_address else 'fail', 'udp': 'open',
                'same_exit_as_tcp': udp == exit_address}))
        for item in stack:
            item.start()
            self.addCleanup(item.stop)

    def test_endpoints_never_include_claude_or_anthropic(self):
        for item in nc.ENDPOINTS:
            self.assertNotIn('claude', item.lower())
            self.assertNotIn('anthropic', item.lower())
        with patch('sys.stdout', io.StringIO()):
            self.assertEqual(nc.main(['endpoints']), 0)

    def test_route_parsing_per_platform(self):
        self.assertEqual(nc.parse_route('macos', '   route to: default\n  interface: utun4\n'), 'utun4')
        self.assertEqual(nc.parse_route('linux', '1.1.1.1 dev FlClash table 2022 src 172.19.0.1 uid 1000'), 'FlClash')
        self.assertEqual(nc.parse_route('windows', 'Meta Tunnel\r\n'), 'Meta Tunnel')
        self.assertIsNone(nc.parse_route('linux', ''))
        for name in ('utun4', 'FlClash', 'Meta Tunnel', 'Mihomo', 'Wintun Userspace Tunnel', 'tun0'):
            self.assertTrue(nc.TUN_NAME.search(name), name)
        for name in ('en0', 'wlan0', 'Intel(R) Wi-Fi 6 AX201', 'eth0'):
            self.assertFalse(nc.TUN_NAME.search(name), name)

    def test_dns_judgement_uses_home_country_not_the_services_conclusion(self):
        rows = json.loads(GOOD[('bash.ws', '/dnsleak/test', False)])
        self.assertEqual(nc.judge_dns(rows, 'us', 'cn')['status'], 'pass')
        rows.append({'ip': '198.51.100.1', 'country': 'cn', 'asn': 'AS4134 Chinanet', 'type': 'dns'})
        self.assertEqual(nc.judge_dns(rows, 'us', 'cn')['status'], 'fail')
        self.assertEqual(nc.judge_dns([{'country': 'jp', 'asn': 'AS1', 'type': 'dns'}], 'us', 'cn')['status'], 'warn')
        self.assertEqual(nc.judge_dns({'error': 'No DNS servers found'}, 'us', 'cn')['status'], 'not_run')
        self.assertEqual(nc.judge_dns([{'type': 'ip', 'country': 'us'}], 'us', 'cn')['status'], 'not_run')

    def test_ipv6_answer_that_is_ipv4_counts_as_unreachable(self):
        with patch.object(nc, 'https_get', return_value=json.dumps({'ip': EXIT})):
            self.assertEqual(nc.check_ipv6(), {'status': 'pass', 'probe': 'unreachable'})
        with patch.object(nc, 'https_get', return_value=json.dumps({'ip': '2001:db8::1'})):
            self.assertEqual(nc.check_ipv6(), {'status': 'fail', 'probe': 'reachable'})
        with patch.object(nc, 'https_get', side_effect=OSError('x')):
            self.assertEqual(nc.check_ipv6()['probe'], 'unreachable')

    def test_exit_in_home_country_is_a_direct_exit(self):
        with patch.object(nc, 'https_get', return_value=json.dumps({'ip': EXIT, 'country': 'CN', 'org': 'AS4134'})):
            self.assertEqual(nc.check_exit_v4('cn')[0]['status'], 'fail')
        with patch.object(nc, 'https_get', return_value=json.dumps({'ip': EXIT, 'country': 'US', 'org': 'AS1'})):
            self.assertEqual(nc.check_exit_v4('cn')[0]['status'], 'pass')

    def test_full_run_passes_and_the_report_has_no_ip(self):
        self.patched()
        report, addresses = nc.run('mac-a', 'cn', proxy=('127.0.0.1', 7897))
        self.assertEqual(report['overall'], 'pass')
        self.assertTrue(report['results']['exit_via_proxy']['same_exit_as_direct'])
        text = json.dumps(report) + nc.summary(report)
        self.assertNotIn(EXIT, text)
        self.assertNotIn('192.0.2.53', text)
        self.assertIn('fake-ip', nc.summary(report))
        self.assertEqual(addresses, (EXIT, EXIT))

    def test_failures_are_reported(self):
        bad = dict(GOOD)
        bad[('api6.ipify.org', '/?format=json', False)] = json.dumps({'ip': '2001:db8::1'})
        bad[('bash.ws', '/dnsleak/test', False)] = json.dumps([{'country': 'cn', 'asn': 'AS4134', 'type': 'dns'}])
        self.patched(bad, route=('no', 'en0'), udp='198.51.100.9')
        report, _ = nc.run('mac-a', 'cn')
        r = report['results']
        self.assertEqual(report['overall'], 'fail')
        for key in ('route', 'ipv6', 'dns_leak', 'udp'):
            self.assertEqual(r[key]['status'], 'fail', key)
        self.assertIn('有解析服务器在本国', nc.summary(report))

    def test_evidence_is_accepted_by_egress_verifier(self):
        self.patched()
        report, addresses = nc.run('mac-a', 'cn', proxy=('127.0.0.1', 7897))
        evidence = nc.evidence(report, addresses)
        judged = egress_verifier.judge(evidence)
        self.assertEqual(judged['layers']['exit_ipv4'], 'pass')
        self.assertEqual(judged['layers']['ipv6_probe'], 'pass')
        self.assertEqual(evidence['dns'], {'ipv6': 'unknown', 'hijack': 'yes', 'leak_test': 'pass'})
        self.assertEqual(judged['status'], 'incomplete')  # settings and drills it cannot see stay open
        evidence['platform'] = 'linux'
        egress_verifier.judge(evidence)

    def test_failure_drill(self):
        answers = []

        def exit_v4(home, proxy=None, timeout=10):
            return answers.pop(0), None
        with patch.object(nc, 'check_exit_v4', side_effect=exit_v4):
            answers[:] = [{'status': 'error'}, {'status': 'pass'}]
            self.assertEqual(nc.failure_drill('cn', (Console(), Console()))['result'], 'no_direct')
            answers[:] = [{'status': 'fail', 'country': 'cn'}, {'status': 'pass'}]
            self.assertEqual(nc.failure_drill('cn', (Console(), Console()))['result'], 'direct_observed')
            answers[:] = [{'status': 'pass', 'country': 'us'}, {'status': 'pass'}]
            self.assertEqual(nc.failure_drill('cn', (Console(), Console()))['result'], 'core_still_running')
            answers[:] = [{'status': 'error'}, {'status': 'error'}]
            self.assertEqual(nc.failure_drill('cn', (Console(), Console()))['result'], 'inconclusive')
        self.assertEqual(nc.failure_drill('cn', (Console(False), Console(False)))['status'], 'not_run')

    def test_udp_stun_compares_mapped_address(self):
        class Sock:
            def __init__(self, *a):
                self.request = None
            def __enter__(self):
                return self
            def __exit__(self, *a):
                return False
            def settimeout(self, t):
                pass
            def sendto(self, data, peer):
                self.request = data
            def recvfrom(self, n):
                txid = self.request[8:20]
                addr = bytes(a ^ b for a, b in zip(ipaddress.ip_address(EXIT).packed, (0x2112A442).to_bytes(4, 'big')))
                attr = b'\x00\x20\x00\x08\x00\x01' + (1234 ^ 0x2112).to_bytes(2, 'big') + addr
                return b'\x01\x01' + len(attr).to_bytes(2, 'big') + (0x2112A442).to_bytes(4, 'big') + txid + attr, None
        with patch.object(nc.socket, 'getaddrinfo', return_value=[(socket.AF_INET, socket.SOCK_DGRAM, 0, '', ('192.0.2.1', 3478))]), \
                patch.object(nc.socket, 'socket', Sock):
            self.assertEqual(nc.check_udp(EXIT)['status'], 'pass')
            self.assertEqual(nc.check_udp('198.51.100.9')['status'], 'fail')

    def test_cli_writes_new_private_files_only(self):
        self.patched()
        with tempfile.TemporaryDirectory() as tmp:
            out, ev = os.path.join(tmp, 'r.json'), os.path.join(tmp, 'e.json')
            with patch('sys.stdout', io.StringIO()):
                self.assertEqual(nc.main(['run', '--target-ref', 'mac-a', '--output', out, '--evidence-output', ev]), 0)
            self.assertNotIn(EXIT, Path(out).read_text(encoding='utf-8'))
            self.assertIn(EXIT, Path(ev).read_text(encoding='utf-8'))
            if os.name == 'posix':
                self.assertEqual(os.stat(ev).st_mode & 0o777, 0o600)
            with patch('sys.stdout', io.StringIO()), patch('sys.stderr', io.StringIO()):
                self.assertEqual(nc.main(['run', '--target-ref', 'mac-a', '--output', out]), 2)  # never overwrites

    def test_only_local_proxy_ports_are_accepted(self):
        self.assertEqual(nc._proxy('http://127.0.0.1:7897'), ('127.0.0.1', 7897))
        for bad in ('http://10.0.0.2:7890', 'socks5://127.0.0.1:7890', '127.0.0.1:0', 'example.com:80'):
            with self.assertRaises(Exception):
                nc._proxy(bad)


if __name__ == '__main__':
    unittest.main()
