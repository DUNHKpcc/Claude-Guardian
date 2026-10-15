"""Offline adapter contract tests; no public network requests."""
import importlib.util
import io
from datetime import datetime, timezone, timedelta, tzinfo
from types import SimpleNamespace
from pathlib import Path
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/network_probes.py'
spec = importlib.util.spec_from_file_location('network_probes', FILE)
n = importlib.util.module_from_spec(spec)
spec.loader.exec_module(n)
PATH = 'direct_socket_os_route_tun_unknown'


class FakeTransport:
    path_kind = PATH
    def __init__(self, body=b'{"ip":"8.8.8.8"}', status=200, error=None, retry_after_values=()):
        self.retry_after_values = retry_after_values
        self.body, self.status, self.error = body, status, error
        self.calls = []
    def request(self, url, **limits):
        self.calls.append((url, limits))
        if self.error:
            raise self.error
        return n.Response(self.status, self.body, self.retry_after_values)


class ContractTests(unittest.TestCase):
    def probe(self, transport=None, endpoint='ipify_v4', **kwargs):
        return n.probe_https_ip(endpoint, approved_endpoints=[n.ENDPOINTS[endpoint][0]],
            approved_paths=[PATH], target_ref='local-target-1', transport=transport or FakeTransport(), **kwargs)

    def test_endpoint_and_path_consent(self):
        for approval in [[], ['https://api.ipify.org'], True, n.ENDPOINTS['ipify_v4'][0]]:
            with self.assertRaisesRegex(n.ProbeError, 'exact_endpoint_consent_required'):
                n.probe_https_ip('ipify_v4', approved_endpoints=approval, approved_paths=[PATH], target_ref='x')
        with self.assertRaisesRegex(n.ProbeError, 'explicit_path_consent_required'):
            n.probe_https_ip('ipify_v4', approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]], approved_paths=[], target_ref='x')

    def test_arbitrary_endpoints_rejected(self):
        for endpoint in ['https://claude.ai', 'https://user:password@api.ipify.org', 'https://example.com', 'ipify_v4?token=x']:
            with self.assertRaisesRegex(n.ProbeError, 'endpoint_not_allowlisted'):
                n.probe_https_ip(endpoint, approved_endpoints=[endpoint], approved_paths=[PATH], target_ref='x')

    def test_success_does_not_certify_browser_or_route(self):
        fake = FakeTransport()
        result = self.probe(fake)
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['observed_address_family'], 4)
        self.assertEqual(result['path_association'], 'unknown')
        self.assertEqual(result['browser_path'], 'not_observed')
        self.assertEqual(fake.calls, [(n.ENDPOINTS['ipify_v4'][0], dict(connect_timeout=5,total_timeout=10,max_body=4096))])
        self.assertNotIn('target_ref', fake.calls[0][1])

    def test_ipv6_and_dual_are_separate(self):
        v6 = b'{"ip":"2606:4700:4700::1111"}'
        self.assertEqual(self.probe(FakeTransport(v6), 'ipify_v6')['observed_address_family'], 6)
        self.assertEqual(self.probe(FakeTransport(), 'ipify_v6')['error'], 'unexpected_address_family')
        dual = self.probe(FakeTransport(), 'ipify_dual')
        self.assertIsNone(dual['expected_address_family'])
        self.assertEqual(dual['observed_address_family'], 4)

    def test_invalid_json_or_address(self):
        for body in [b'<html>challenge</html>', b'[]', b'null', b'{"ip":123}', b'{"ip":"fe80::1%eth0"}', b'\xff', b'{"ip":"junk"}']:
            with self.subTest(body=body):
                self.assertEqual(self.probe(FakeTransport(body))['error'], 'invalid_ip_json')
        self.assertEqual(self.probe(FakeTransport(b'{"ip":"127.0.0.1"}'))['error'], 'non_public_echo_address')

    def test_http_failure_never_retries(self):
        for status, error in [(301, 'redirect_rejected'), (429, 'rate_limited_no_retry'), (503, 'http_error')]:
            fake = FakeTransport(status=status)
            result = self.probe(fake)
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['error'], error)
            self.assertEqual(len(fake.calls), 1)

    def test_bounds_timeout_and_secret_suppression(self):
        self.assertEqual(self.probe(FakeTransport(b'x'*4097))['error'], 'response_too_large_or_invalid')
        self.assertEqual(self.probe(FakeTransport(error=TimeoutError()))['error'], 'timeout')
        result = self.probe(FakeTransport(error=RuntimeError('password=secret')))
        self.assertNotIn('secret', str(result))
        result = self.probe(FakeTransport(error=n.ProbeError('password=secret')))
        self.assertNotIn('secret', str(result))

    def test_browser_claim_or_proxy_fallback_rejected(self):
        with self.assertRaisesRegex(n.ProbeError, 'unsupported_path_kind'):
            self.probe(path_kind='browser')
        with self.assertRaisesRegex(n.ProbeError, 'transport_path_mismatch'):
            n.probe_https_ip('ipify_v4', approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],
                approved_paths=['explicit_proxy'], target_ref='x', path_kind='explicit_proxy')

    def test_webrtc_asset_is_opt_in_and_no_media(self):
        page = (FILE.parent.parent / 'assets/webrtc-probe.html').read_text()
        self.assertIn("start.addEventListener('click'", page)
        self.assertGreater(page.index('pc=new RTCPeerConnection'), page.index("start.addEventListener('click'"))
        self.assertIn("iceTransportPolicy:'all'", page)
        self.assertIn("setTimeout(() => finish('timeout'),12000)", page)
        self.assertNotIn('getUserMedia', page)
        self.assertNotIn('turn:', page)
        self.assertNotIn('fetch(', page)
        self.assertNotIn('<script src=', page)
        self.assertIn("path_status:'unknown'", page)

    def test_import_has_no_network_or_subprocess(self):
        with patch('subprocess.Popen', side_effect=AssertionError('must not start')):
            spec.loader.exec_module(n)

    def test_curl_security_flags_offline(self):
        class Stream(io.BytesIO):
            def __init__(self):
                super().__init__(b'HTTP/1.1 200 OK\r\n\r\n{"ip":"8.8.8.8"}\n200')
        class Process:
            stdout = Stream()
            returncode = 0
            def wait(self, timeout=None): return 0
            def poll(self): return 0
            def kill(self): pass
        with patch.object(n.Path, 'is_file', return_value=True), patch.object(n.subprocess, 'Popen', return_value=Process()) as popen, patch.dict(n.os.environ, {'HTTPS_PROXY':'http://secret:password@proxy','CURL_CA_BUNDLE':'bad'}):
            self.assertEqual(n.SystemRouteTransport().request(n.ENDPOINTS['ipify_v4'][0], connect_timeout=5,total_timeout=10,max_body=4096).status, 200)
        args, kwargs = popen.call_args
        cmd = args[0]
        self.assertEqual(cmd[1], '--disable')
        self.assertEqual(cmd[cmd.index('--proxy') + 1], '')
        for flag in ['-k', '--insecure', '--location', '--netrc']:
            self.assertNotIn(flag, cmd)
        self.assertNotIn('HTTPS_PROXY', kwargs['env'])
        self.assertNotIn('CURL_CA_BUNDLE', kwargs['env'])
        self.assertFalse(kwargs.get('shell', False))


class ProcessCleanupTests(unittest.TestCase):
    class Process:
        def __init__(self, error=None, read_error=False):
            self.stdout = io.BytesIO(b'HTTP/1.1 200 OK\r\n\r\n{"ip":"8.8.8.8"}\n200')
            if read_error:
                class Broken(io.BytesIO):
                    def read(self, count): raise OSError('private detail')
                self.stdout = Broken()
            self.returncode = None
            self.waits = []
            self.killed = False
            self.error = error
        def wait(self, timeout=None):
            self.waits.append(timeout)
            if len(self.waits) == 1 and self.error:
                raise self.error
            self.returncode = 0
            return 0
        def poll(self): return self.returncode
        def kill(self):
            self.killed = True
            self.returncode = -9

    def run_transport(self, process):
        with patch.object(n, '_fixed_curl', return_value=('/usr/bin/curl', {'LC_ALL':'C'}, '/')), patch.object(n.subprocess, 'Popen', return_value=process):
            return n.SystemRouteTransport().request(n.ENDPOINTS['ipify_v4'][0], connect_timeout=5,total_timeout=10,max_body=4096)

    def test_interrupt_kills_and_reaps_child(self):
        process = self.Process(KeyboardInterrupt())
        with self.assertRaises(KeyboardInterrupt):
            self.run_transport(process)
        self.assertTrue(process.killed)
        self.assertEqual(process.waits, [11, 1])
        self.assertTrue(process.stdout.closed)

    def test_timeout_kills_and_reaps_child(self):
        process = self.Process(n.subprocess.TimeoutExpired('curl', 11))
        with self.assertRaisesRegex(n.ProbeError, 'timeout'):
            self.run_transport(process)
        self.assertTrue(process.killed)
        self.assertEqual(process.waits, [11, 1])
        self.assertTrue(process.stdout.closed)

    def test_read_failure_is_reported(self):
        process = self.Process(read_error=True)
        with self.assertRaisesRegex(n.ProbeError, 'transport_read_failed'):
            self.run_transport(process)
        self.assertTrue(process.killed)
        self.assertTrue(process.stdout.closed)

    def test_headerless_curl_errors_keep_typed_exit_status(self):
        for code, expected in [(6,'dns_error'),(7,'connect_error'),(35,'tls_error'),(60,'tls_error'),(28,'timeout')]:
            for output in [b'', b'\n000', b'HTTP/1.1 ']:
                with self.subTest(code=code, output=output):
                    process=self.Process()
                    process.stdout=io.BytesIO(output)
                    def wait(timeout=None):
                        process.waits.append(timeout)
                        process.returncode=code
                        return code
                    process.wait=wait
                    with self.assertRaisesRegex(n.ProbeError, '^'+expected+'$'):
                        self.run_transport(process)
                    self.assertFalse(process.killed)
                    self.assertTrue(process.stdout.closed)
                    self.assertEqual(process.waits,[11,1])

    def test_success_exit_without_headers_is_invalid_not_observed(self):
        process=self.Process()
        process.stdout=io.BytesIO(b'\n200')
        with self.assertRaisesRegex(n.ProbeError,'^invalid_transport_response$'):
            self.run_transport(process)
        self.assertFalse(process.killed)

    def test_environment_has_no_user_injected_hooks(self):
        with patch.object(n.sys, 'platform', 'linux'), patch.object(n.Path, 'is_file', return_value=True), patch.dict(n.os.environ, {'SSLKEYLOGFILE':'secret', 'LD_PRELOAD':'evil', 'DYLD_INSERT_LIBRARIES':'evil', 'SystemRoot':'evil'}):
            executable, environment, cwd = n._fixed_curl()
        self.assertEqual(executable, '/usr/bin/curl')
        self.assertEqual(environment, {'PATH':'/usr/bin:/bin','LC_ALL':'C'})
        self.assertEqual(cwd, '/')

    def test_windows_root_is_os_api_not_environment(self):
        def windows_directory(buffer, length):
            buffer.value = r'C:\TrustedWindows'
            return len(buffer.value)
        api = SimpleNamespace(kernel32=SimpleNamespace(GetWindowsDirectoryW=windows_directory))
        with patch.object(n.sys, 'platform', 'win32'), patch.object(n.Path, 'is_file', return_value=True), patch.dict(n.os.environ, {'SystemRoot':r'C:\Untrusted'}), patch('ctypes.windll', api, create=True):
            executable, environment, cwd = n._fixed_curl()
        self.assertEqual(executable, r'C:\TrustedWindows\System32\curl.exe')
        self.assertEqual(environment['SystemRoot'], r'C:\TrustedWindows')
        self.assertNotIn('Untrusted', str(environment))


class RetryAfterTests(unittest.TestCase):
    now = datetime(2026, 10, 15, 12, 0, tzinfo=timezone.utc)

    def test_delta_seconds_zero_and_cap(self):
        for value, expected in [('0',0),(' 120 ',120),('86400',86400),('00001',1)]:
            result = n.parse_retry_after([value])
            self.assertEqual(result['status'], 'valid')
            self.assertEqual(result['delay_seconds'], expected)
            self.assertEqual(result['clock_trust'], 'unknown')
            self.assertFalse(result['automatic_retry'])

    def test_bad_duplicate_negative_and_excessive_values_are_sanitized(self):
        for values, expected in [([], 'missing'),(['1','1'],'duplicate'),(['-1'],'invalid'),
            (['+1'],'invalid'),(['1.5'],'invalid'),(['1, 2'],'invalid'),(['86401'],'exceeds_cap'),
            (['9'*128],'exceeds_cap'),(['9'*129],'invalid'),(['secret-token'],'invalid'),
            (['1\r\nAuthorization: secret-token'],'invalid'),(['１２'],'invalid'),(['Foo, 15 Oct 2026 12:02:00 GMT'],'invalid'),([None],'invalid'),('120','invalid')]:
            result=n.parse_retry_after(values)
            self.assertEqual(result['status'],expected,values)
            self.assertIsNone(result['delay_seconds'])
            self.assertNotIn('secret-token',str(result))

    def test_http_date_requires_actual_trusted_aware_observation(self):
        value=['Thu, 15 Oct 2026 12:02:00 GMT']
        for observed, trusted in [(self.now,False),(self.now,1),(self.now.replace(tzinfo=None),True),(None,True)]:
            self.assertEqual(n.parse_retry_after(value,response_observed_at=observed,observed_clock_trusted=trusted)['status'],'clock_untrusted')
        result=n.parse_retry_after(value,response_observed_at=self.now,observed_clock_trusted=True)
        self.assertEqual(result['delay_seconds'],120)
        self.assertEqual(result['clock_trust'],'caller_attested')
        for text, status in [('Thu, 15 Oct 2026 11:59:59 GMT','past_date'),
                             ('Sat, 17 Oct 2026 12:00:00 GMT','exceeds_cap'),
                             ('Thu, 99 Oct 2026 12:00:00 GMT','invalid'),
                             ('Thu, 15 Oct 2026 12:02:00 GMT secret-token','invalid')]:
            result=n.parse_retry_after([text],response_observed_at=self.now,observed_clock_trusted=True)
            self.assertEqual(result['status'],status)
            self.assertIsNone(result['delay_seconds'])
        result=n.parse_retry_after(value,response_observed_at=self.now+timedelta(microseconds=1),observed_clock_trusted=True)
        self.assertEqual(result['delay_seconds'],120)  # round up, not early

    def test_429_always_stops_once_without_sleep_and_clock_is_after_response(self):
        for values in [(),('60',),('-1',),('1','2'),('999999',),('Thu, 15 Oct 2026 12:02:00 GMT',)]:
            fake=FakeTransport(status=429,retry_after_values=values)
            def clock():
                self.assertEqual(len(fake.calls),1)
                return self.now,True
            with patch('time.sleep',side_effect=AssertionError('must never sleep')):
                result=n.probe_https_ip('ipify_v4',approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],approved_paths=[PATH],target_ref='test',transport=fake,response_clock=clock)
            self.assertEqual(result['error'],'rate_limited_no_retry')
            self.assertEqual(result['status'],'unknown')
            self.assertEqual(len(fake.calls),1)
            self.assertFalse(result['retry_after']['automatic_retry'])

    def test_backward_compatible_response_and_bad_clock_keep_stop_behavior(self):
        self.assertEqual(n.Response(429,b'').retry_after_values,())
        fake=FakeTransport(status=429,retry_after_values=['Thu, 15 Oct 2026 12:02:00 GMT'])
        def broken_clock(): raise RuntimeError('secret-token')
        result=n.probe_https_ip('ipify_v4',approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],approved_paths=[PATH],target_ref='test',transport=fake,response_clock=broken_clock)
        self.assertEqual(result['error'],'rate_limited_no_retry')
        self.assertEqual(result['retry_after']['status'],'clock_untrusted')
        self.assertNotIn('secret-token',str(result))

    def test_fractional_past_date_is_not_rounded_into_zero_delay(self):
        result=n.parse_retry_after(['Thu, 15 Oct 2026 12:00:00 GMT'],
            response_observed_at=self.now+timedelta(microseconds=500000),observed_clock_trusted=True)
        self.assertEqual(result['status'],'past_date')
        self.assertIsNone(result['delay_seconds'])

    def test_broken_timezone_is_unknown_and_preserves_429(self):
        class BrokenZone(tzinfo):
            def utcoffset(self, dt): raise ValueError('secret-token')
        bad_clock=self.now.replace(tzinfo=BrokenZone())
        result=n.parse_retry_after(['Thu, 15 Oct 2026 12:02:00 GMT'],
            response_observed_at=bad_clock,observed_clock_trusted=True)
        self.assertEqual(result['status'],'clock_untrusted')
        self.assertEqual(result['clock_trust'],'unknown')
        self.assertNotIn('secret-token',str(result))
        fake=FakeTransport(status=429,retry_after_values=['Thu, 15 Oct 2026 12:02:00 GMT'])
        result=n.probe_https_ip('ipify_v4',approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],
            approved_paths=[PATH],target_ref='test',transport=fake,response_clock=lambda:(bad_clock,True))
        self.assertEqual(result['error'],'rate_limited_no_retry')
        self.assertEqual(result['retry_after']['status'],'clock_untrusted')
        self.assertNotIn('secret-token',str(result))
        self.assertEqual(len(fake.calls),1)

    def test_invalid_clock_shapes_and_default_stay_unknown(self):
        for clock in [None, lambda: (), lambda: (self.now, True, 'secret-token'),
                      lambda: (None, True), lambda: (self.now, 'true'), lambda: (self.now.replace(tzinfo=None), True)]:
            fake=FakeTransport(status=429,retry_after_values=['Thu, 15 Oct 2026 12:02:00 GMT'])
            result=n.probe_https_ip('ipify_v4',approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],approved_paths=[PATH],target_ref='test',transport=fake,response_clock=clock)
            self.assertEqual(result['error'],'rate_limited_no_retry')
            self.assertEqual(result['retry_after']['status'],'clock_untrusted')
            self.assertNotIn('secret-token',str(result))
            self.assertEqual(len(fake.calls),1)

    def test_redirect_never_becomes_retry_advice(self):
        fake=FakeTransport(status=302,retry_after_values=['60'])
        result=n.probe_https_ip('ipify_v4',approved_endpoints=[n.ENDPOINTS['ipify_v4'][0]],approved_paths=[PATH],target_ref='test',transport=fake)
        self.assertEqual(result['error'],'redirect_rejected')
        self.assertIsNone(result['retry_after'])
        self.assertEqual(len(fake.calls),1)

    def test_combined_header_body_budget_at_exact_boundaries(self):
        prefix=b'HTTP/1.1 429 Limited\r\nRetry-After: 60\r\nX: '
        suffix=b'\r\n\r\n'
        header=prefix+b'a'*(n.MAX_HEADERS-len(prefix)-len(suffix))+suffix
        process=ProcessCleanupTests.Process()
        process.stdout=io.BytesIO(header+b'b'*4096+b'\n429')
        response=ProcessCleanupTests().run_transport(process)
        self.assertEqual(len(response.body),4096)
        self.assertEqual(response.retry_after_values,['60'])
        self.assertFalse(process.killed)

    def test_final_headers_only_and_no_arbitrary_header_projection(self):
        raw=(b'HTTP/1.1 103 Early Hints\r\nRetry-After: 999\r\n\r\n'
             b'HTTP/1.1 429 Too Many Requests\r\nRetry-After: 60\r\nSet-Cookie: secret-token\r\n\r\n{}\n429')
        response=n._parse_curl_response(raw,4096)
        self.assertEqual(response.retry_after_values,['60'])
        self.assertNotIn('secret-token',str(vars(response)))
        duplicate=n._parse_curl_response(b'HTTP/1.1 429 Limited\r\nRetry-After: 1\r\nretry-after: 2\r\n\r\n\n429',4096)
        self.assertEqual(n.parse_retry_after(duplicate.retry_after_values)['status'],'duplicate')
        with self.assertRaises(n.ProbeError):
            n._parse_curl_response(b'HTTP/1.1 200 Connection established\r\nRetry-After: 999\r\n\r\nHTTP/1.1 429 Limited\r\n\r\n\n429',4096)

    def test_transport_header_and_body_budgets_and_framing(self):
        for raw,error in [(b'HTTP/1.1 200 OK\r\nX: '+b'a'*8192+b'\r\n\r\n{}\n200','response_too_large'),
                          (b'HTTP/1.1 200 OK\r\n\r\n'+b'a'*4097+b'\n200','response_too_large')]:
            process=ProcessCleanupTests.Process()
            process.stdout=io.BytesIO(raw)
            with self.assertRaisesRegex(n.ProbeError,error):
                ProcessCleanupTests().run_transport(process)
            self.assertTrue(process.killed)
        process=ProcessCleanupTests.Process()
        process.stdout=io.BytesIO(b'HTTP/1.1 429 Limited\r\nRetry-After: 60\r\n\r\n{}\n429')
        response=ProcessCleanupTests().run_transport(process)
        self.assertEqual(response.retry_after_values,['60'])


if __name__ == '__main__':
    unittest.main()
