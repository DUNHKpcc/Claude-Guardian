"""Loopback-only serving tests. These never start a browser or contact STUN."""
import contextlib
import http.client
import importlib.util
import io
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/serve_webrtc.py'
spec = importlib.util.spec_from_file_location('serve_webrtc', FILE)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


class ServerTests(unittest.TestCase):
    def setUp(self):
        try:
            self.server = w.LocalProbeServer()
        except PermissionError:
            self.skipTest('Environment does not permit loopback listener tests')
        self.port = self.server._server.server_port
        self.thread = threading.Thread(target=self.server.serve, kwargs={'duration_seconds': 5})
        self.thread.start()

    def tearDown(self):
        if hasattr(self, 'server'):
            self.server.close()
            self.thread.join(2)
            self.assertFalse(self.thread.is_alive())

    def request(self, path=w.ROUTE, method='GET', headers=None):
        connection = http.client.HTTPConnection('127.0.0.1', self.port, timeout=2)
        try:
            connection.request(method, path, headers=headers or {})
            response = connection.getresponse()
            return response.status, dict(response.getheaders()), response.read()
        finally:
            connection.close()

    def test_fixed_asset_only_and_security_headers(self):
        self.assertEqual(self.server._server.server_address[0], '127.0.0.1')
        self.assertGreater(self.port, 0)
        code, headers, body = self.request()
        self.assertEqual(code, 200)
        self.assertEqual(body, w.ASSET.read_bytes())
        self.assertEqual(headers['Cache-Control'], 'no-store')
        self.assertEqual(headers['X-Frame-Options'], 'DENY')
        self.assertIn('camera=()', headers['Permissions-Policy'])
        self.assertIn("frame-ancestors 'none'", headers['Content-Security-Policy'])
        self.assertNotIn('Access-Control-Allow-Origin', headers)
        self.assertNotIn('Set-Cookie', headers)

    def test_head_has_no_body(self):
        code, headers, body = self.request(method='HEAD')
        self.assertEqual(code, 200)
        self.assertEqual(body, b'')
        self.assertEqual(int(headers['Content-Length']), len(w.ASSET.read_bytes()))

    def test_no_directory_listing_traversal_query_or_absolute_url(self):
        for path in ['/', '/favicon.ico', '/../scripts/guardian.py', '/%2e%2e/scripts/guardian.py',
                     '/webrtc-probe.html?token=secret', '//webrtc-probe.html',
                     'http://127.0.0.1/webrtc-probe.html']:
            with self.subTest(path=path):
                code, _, body = self.request(path, headers={'Host': f'127.0.0.1:{self.port}'})
                self.assertEqual(code, 404)
                self.assertNotIn(b'secret', body)
                self.assertNotIn(b'guardian.py', body)

    def test_host_is_exact_bound_authority(self):
        for host in ['evil.example', 'localhost:' + str(self.port), '127.0.0.1',
                     '127.0.0.1:1', 'user:password@127.0.0.1:' + str(self.port)]:
            self.assertEqual(self.request(headers={'Host': host})[0], 421)

    def test_duplicate_or_missing_host_rejected(self):
        for host_lines in ['', f'Host: 127.0.0.1:{self.port}\r\nHost: evil.example\r\n']:
            with socket.create_connection(('127.0.0.1', self.port), timeout=2) as connection:
                connection.sendall((f'GET {w.ROUTE} HTTP/1.0\r\n{host_lines}\r\n').encode())
                self.assertIn(b'421', connection.recv(1024).split(b'\r\n')[0])

    def test_cross_origin_requests_rejected(self):
        self.assertEqual(self.request(headers={'Origin': 'https://evil.example'})[0], 403)
        self.assertEqual(self.request(headers={'Origin': 'null'})[0], 403)
        self.assertEqual(self.request(headers={'Sec-Fetch-Site': 'cross-site'})[0], 403)
        self.assertEqual(self.request(headers={'Origin': f'http://127.0.0.1:{self.port}'})[0], 200)

    def test_body_and_state_changing_methods_rejected(self):
        self.assertEqual(self.request(headers={'Content-Length': '0'})[0], 400)
        self.assertEqual(self.request(headers={'Transfer-Encoding': 'chunked'})[0], 400)
        for method in ['POST', 'PUT', 'DELETE', 'OPTIONS', 'CONNECT']:
            self.assertEqual(self.request(method=method)[0], 501)

    def test_credentials_and_request_data_not_logged_or_reflected(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            code, headers, body = self.request('/secret-token', headers={
                'Authorization': 'Bearer private-value', 'Cookie': 'private-value'})
        self.assertEqual(code, 404)
        self.assertNotIn('private-value', str(headers) + str(body))
        self.assertEqual(stderr.getvalue(), '')

    def test_close_is_idempotent_and_listener_removed(self):
        self.server.close()
        self.server.close()
        self.thread.join(2)
        with self.assertRaises(OSError):
            socket.create_connection(('127.0.0.1', self.port), timeout=.2)


class LifecycleTests(unittest.TestCase):
    def new_server(self):
        try:
            return w.LocalProbeServer()
        except PermissionError:
            self.skipTest('Environment does not permit loopback listener tests')

    def test_deadline_closes_even_incomplete_request(self):
        with self.new_server() as server:
            start = time.monotonic()
            thread = threading.Thread(target=server.serve, kwargs={'duration_seconds': .15})
            thread.start()
            with socket.create_connection(server._server.server_address, timeout=1) as client:
                client.sendall(b'GET /webrtc-probe.html HTTP/1.1\r\nHost:')
                thread.join(1)
                self.assertFalse(thread.is_alive())
                self.assertEqual(client.recv(1024), b'')
            self.assertLess(time.monotonic() - start, 1)

    def test_explicit_cancellation(self):
        with self.new_server() as server:
            cancel = threading.Event()
            thread = threading.Thread(target=server.serve, kwargs={'cancel_event': cancel})
            thread.start()
            cancel.set()
            thread.join(1)
            self.assertFalse(thread.is_alive())
            with self.assertRaisesRegex(RuntimeError, 'single-use'):
                server.serve()

    def test_duration_is_finite_and_bounded(self):
        with self.new_server() as server:
            for value in [0, -1, float('inf'), float('nan'), 901, True, '300', None]:
                with self.assertRaises(ValueError):
                    server.serve(value)

    def test_import_does_not_bind_socket_or_start_browser(self):
        with patch('socket.socket', side_effect=AssertionError('no listener on import')):
            spec.loader.exec_module(w)

    def test_cli_exposes_no_file_or_host_configuration(self):
        for flag in ['--host', '--port', '--directory', '--file']:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                w.main([flag, 'untrusted'])


if __name__ == '__main__':
    unittest.main()
