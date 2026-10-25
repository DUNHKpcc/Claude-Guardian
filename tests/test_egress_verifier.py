"""Whole-machine IPv4-only egress judgement: supplied synthetic observations only."""
import copy
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import egress_verifier as v

GOOD = {
    'schema_version': v.SCHEMA, 'platform': 'macos', 'target_ref': 'mac-a',
    'tun': {'enabled': 'yes', 'strict_route': 'yes', 'default_route_via_tun': 'yes'},
    'core': {'ipv6': 'off'},
    'dns': {'ipv6': 'off', 'hijack': 'yes', 'leak_test': 'pass'},
    'rules': {'final_match': 'proxy', 'direct_exceptions': 'listed'},
    'firewall': 'fail_closed', 'os_ipv6': 'disabled',
    'ipv6_probe': 'unreachable', 'webrtc': 'no_leak', 'failure_drill': 'no_direct',
    'samples': [{'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'browser'},
                {'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'terminal'}],
    'lifecycle_checked': ['restart', 'sleep_wake', 'network_change'],
}


def evidence(**changes):
    document = copy.deepcopy(GOOD)
    for key, value in changes.items():
        if isinstance(value, dict) and isinstance(document.get(key), dict):
            document[key].update(value)
        else:
            document[key] = value
    return document


class EgressVerifier(unittest.TestCase):
    def test_all_layers_passing_is_established_and_never_echoes_addresses(self):
        report = v.judge(GOOD)
        self.assertEqual(report['status'], 'established')
        self.assertEqual(report['blockers'], [])
        self.assertEqual(report['advisories'], [])
        self.assertEqual(report['persistence'], {'status': 'checked', 'lifecycle_missing': []})
        self.assertNotIn('203.0.113.9', json.dumps(report))
        self.assertEqual((report['apply_supported'], report['service_eligibility'], report['ban_free']),
                         (False, 'not_assessed', 'not_promised'))

    def test_each_definite_failure_is_violated_with_its_layer(self):
        cases = {
            'tun': evidence(tun={'strict_route': 'no'}),
            'core_ipv6': evidence(core={'ipv6': 'on'}),
            'dns': evidence(dns={'leak_test': 'fail'}),
            'rules': evidence(rules={'final_match': 'direct'}),
            'exit_ipv4': evidence(samples=GOOD['samples'] + [{'family': 'ipv6', 'exit': '2001:db8::1', 'process': 'browser'}]),
            'ipv6_probe': evidence(ipv6_probe='reachable'),
            'webrtc': evidence(webrtc='leak'),
            'failure_drill': evidence(failure_drill='direct_observed'),
        }
        for layer, document in cases.items():
            with self.subTest(layer=layer):
                report = v.judge(document)
                self.assertEqual(report['status'], 'violated')
                self.assertEqual(report['layers'][layer], 'fail')
                self.assertTrue(all(report['layers'][name] == 'pass' for name in v.REQUIRED if name != layer))

    def test_unlisted_direct_exception_and_mixed_exits_fail(self):
        self.assertEqual(v.judge(evidence(rules={'direct_exceptions': 'unlisted'}))['layers']['rules'], 'fail')
        mixed = evidence(samples=[{'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'browser'},
                                  {'family': 'ipv4', 'exit': '203.0.113.10', 'process': 'terminal'}])
        report = v.judge(mixed)
        self.assertEqual(report['layers']['exit_ipv4'], 'fail')
        self.assertIn('EXIT_ADDRESS_MISMATCH', report['blockers'])
        wrong = evidence(expected_exit='203.0.113.77')
        self.assertEqual(v.judge(wrong)['layers']['exit_ipv4'], 'fail')
        self.assertEqual(v.judge(evidence(expected_exit='203.0.113.9'))['status'], 'established')

    def test_missing_or_unknown_observations_stay_incomplete_never_established(self):
        for change in (dict(tun={'enabled': 'unknown'}), dict(core={'ipv6': 'unknown'}),
                       dict(dns={'leak_test': 'not_run'}), dict(rules={'direct_exceptions': 'unknown'}),
                       dict(samples=[]), dict(ipv6_probe='not_run'), dict(webrtc='not_run'),
                       dict(failure_drill='not_run')):
            with self.subTest(change=change):
                report = v.judge(evidence(**change))
                self.assertEqual(report['status'], 'incomplete')
                self.assertTrue(report['blockers'])

    def test_samples_from_one_process_kind_are_not_enough(self):
        one = evidence(samples=[{'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'browser'},
                                {'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'browser'}])
        report = v.judge(one)
        self.assertEqual(report['status'], 'incomplete')
        self.assertIn('SAMPLES_FROM_ONE_PROCESS_KIND', report['blockers'])

    def test_firewall_and_os_ipv6_are_advisory_and_persistence_needs_lifecycle(self):
        report = v.judge(evidence(firewall='not_configured', os_ipv6='enabled', lifecycle_checked=['restart']))
        self.assertEqual(report['status'], 'established')
        self.assertEqual(report['advisories'], ['FIREWALL_FAIL_CLOSED_NOT_ESTABLISHED', 'OS_IPV6_NOT_DISABLED'])
        self.assertEqual(report['persistence'], {'status': 'not_established',
                                                 'lifecycle_missing': ['sleep_wake', 'network_change']})
        broken = v.judge(evidence(ipv6_probe='reachable', lifecycle_checked=list(v.LIFECYCLE)))
        self.assertEqual(broken['persistence']['status'], 'not_established')

    def test_invalid_input_is_rejected_with_fixed_codes(self):
        bad = {
            'INVALID_EVIDENCE': [[], dict(GOOD, extra=1), dict(GOOD, schema_version='x')],
            'UNSUPPORTED_PLATFORM': [dict(GOOD, platform='freebsd'), dict(GOOD, platform='ios')],
            'INVALID_TARGET_REF': [dict(GOOD, target_ref='../x'), dict(GOOD, target_ref='')],
            'INVALID_TUN': [evidence(tun={'enabled': 'maybe'}), dict(GOOD, tun={'enabled': 'yes'})],
            'INVALID_FIREWALL': [dict(GOOD, firewall='yes')],
            'INVALID_SAMPLES': [dict(GOOD, samples='x'), dict(GOOD, samples=[{'family': 'ipv4'}]),
                                dict(GOOD, samples=[{'family': 'ipv4', 'exit': '2001:db8::1', 'process': 'browser'}]),
                                dict(GOOD, samples=[{'family': 'ipv4', 'exit': '203.0.113.9', 'process': 'x'}]),
                                dict(GOOD, samples=GOOD['samples'] * 11)],
            'INVALID_EXIT_ADDRESS': [dict(GOOD, samples=[{'family': 'ipv4', 'exit': 'host.example', 'process': 'browser'}]),
                                     dict(GOOD, expected_exit='2001:db8::1')],
            'INVALID_LIFECYCLE': [dict(GOOD, lifecycle_checked=['reboot'])],
        }
        for code, documents in bad.items():
            for document in documents:
                with self.subTest(code=code):
                    with self.assertRaises(v.EvidenceError) as caught:
                        v.judge(document)
                    self.assertEqual(caught.exception.code, code)

    def test_cli_reads_private_file_and_reports_without_addresses(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'evidence.json'
            path.write_text(json.dumps(GOOD), encoding='utf-8')
            done = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'egress_verifier.py'), 'check',
                                   '--input', str(path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(done.returncode, 0, done.stderr)
            self.assertEqual(json.loads(done.stdout)['status'], 'established')
            self.assertNotIn('203.0.113.9', done.stdout)
            path.write_text('{"schema_version": 1', encoding='utf-8')
            failed = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'egress_verifier.py'), 'check',
                                     '--input', str(path)], capture_output=True, text=True, timeout=20)
            self.assertEqual(failed.returncode, 2)
            self.assertEqual(json.loads(failed.stderr)['code'], 'INVALID_EVIDENCE')
            missing = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'egress_verifier.py'), 'check',
                                      '--input', str(Path(tmp) / 'absent.json')], capture_output=True, text=True, timeout=20)
            self.assertEqual(json.loads(missing.stderr)['code'], 'INPUT_UNREADABLE')
            big = Path(tmp) / 'big.json'
            big.write_bytes(b' ' * (v.MAX_INPUT_BYTES + 1))
            self.assertEqual(json.loads(subprocess.run(
                [sys.executable, '-B', str(SCRIPTS / 'egress_verifier.py'), 'check', '--input', str(big)],
                capture_output=True, text=True, timeout=20).stderr)['code'], 'INPUT_TOO_LARGE')


if __name__ == '__main__':
    unittest.main()
