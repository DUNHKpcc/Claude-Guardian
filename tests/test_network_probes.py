"""Offline adapter contract tests; no public network requests."""
import importlib.util
import io
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
    def __init__(self, body=b'{"ip":"8.8.8.8"}', status=200, error=None):
        self.body, self.status, self.error = body, status, error
        self.calls = []
    def request(self, url, **limits):
        self.calls.append((url, limits))
        if self.error:
            raise self.error
        return n.Response(self.status, self.body)


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
        class Stream:
            def read(self, limit):
                self.limit = limit
                value = getattr(self, 'value', b'{"ip":"8.8.8.8"}\n200')
                self.value = b''
                return value
            def close(self): pass
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
            self.stdout = io.BytesIO(b'{"ip":"8.8.8.8"}\n200')
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


if __name__ == '__main__':
    unittest.main()
