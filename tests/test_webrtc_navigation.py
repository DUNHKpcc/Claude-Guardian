"""Exact cross-site navigation admission; in-memory HTTP, no sockets or browser."""
import contextlib
from email.message import Message
import importlib.util
import io
from pathlib import Path
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


FILE = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/serve_webrtc.py'
SPEC = importlib.util.spec_from_file_location('navigation_serve_webrtc', FILE)
webrtc = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(webrtc)
AUTHORITY = '127.0.0.1:41234'
HOST = ('Host', AUTHORITY)
NAVIGATION = (
    ('Sec-Fetch-Site', 'cross-site'),
    ('Sec-Fetch-Mode', 'navigate'),
    ('Sec-Fetch-Dest', 'document'),
    ('Sec-Fetch-User', '?1'),
)


class MemoryRequest:
    def __init__(self, data):
        self.input = io.BytesIO(data)
        self.output = io.BytesIO()

    def makefile(self, _mode, _buffering):
        return self.input

    def sendall(self, data):
        self.output.write(data)


class ExactNavigationTests(unittest.TestCase):
    def setUp(self):
        for target in ('socket.socket', 'socket.create_connection', 'webbrowser.open'):
            guard = patch(target, side_effect=AssertionError('No network or browser allowed'))
            guard.start()
            self.addCleanup(guard.stop)

    def server(self, diagnose=False):
        return SimpleNamespace(
            authority=AUTHORITY, asset=webrtc._read_asset(), diagnose_rejection=diagnose,
            _rejection_lock=threading.Lock(), _rejection_reported=False)

    def request(self, *, headers=None, method='GET', path=webrtc.ROUTE,
                server=None, version='HTTP/1.0', body=b''):
        if headers is None:
            headers = (HOST,) + NAVIGATION
        lines = [method + ' ' + path + ' ' + version]
        lines += [name + ': ' + value for name, value in headers]
        connection = MemoryRequest(('\r\n'.join(lines) + '\r\n\r\n').encode('ascii') + body)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            webrtc._AssetHandler(connection, ('127.0.0.1', 1), server or self.server())
        return connection.output.getvalue(), stderr.getvalue()

    def replaced(self, name, values):
        return [HOST] + [pair for pair in NAVIGATION if pair[0] != name] + [
            (name, value) for value in values]

    def assert_status(self, response, status):
        self.assertTrue(response.startswith(('HTTP/1.0 ' + str(status) + ' ').encode()),
                        response.split(b'\r\n', 1)[0])

    def test_exact_user_navigation_serves_unchanged_asset(self):
        for origin in ([], [('Origin', 'http://' + AUTHORITY)]):
            for version in ('HTTP/1.0', 'HTTP/1.1'):
                with self.subTest(origin=bool(origin), version=version):
                    response, diagnostic = self.request(
                        headers=[HOST] + list(NAVIGATION) + origin, version=version)
                    self.assert_status(response, 200)
                    self.assertEqual(response.split(b'\r\n\r\n', 1)[1], webrtc._read_asset())
                    self.assertEqual(diagnostic, '')

    def test_header_names_are_case_insensitive_but_values_remain_exact(self):
        response, _ = self.request(headers=[(name.lower(), value) for name, value in (HOST,) + NAVIGATION])
        self.assert_status(response, 200)
        for name, value in NAVIGATION[1:]:
            for wrong in (value.upper() if value != '?1' else '?0', value + ' ', value + ', ' + value):
                with self.subTest(name=name, value=wrong):
                    response, _ = self.request(headers=self.replaced(name, [wrong]))
                    self.assert_status(response, 403)

    def test_cross_site_head_never_uses_get_exception(self):
        response, _ = self.request(method='HEAD')
        self.assert_status(response, 403)
        self.assertEqual(response.split(b'\r\n\r\n', 1)[1], b'')

    def test_incomplete_handler_request_metadata_fails_closed(self):
        for missing in ('command', 'path', 'requestline'):
            with self.subTest(missing=missing):
                handler = object.__new__(webrtc._AssetHandler)
                handler.command = 'GET'
                handler.path = webrtc.ROUTE
                handler.requestline = 'GET ' + webrtc.ROUTE + ' HTTP/1.0'
                handler.headers = Message()
                for name, value in (HOST,) + NAVIGATION:
                    handler.headers[name] = value
                handler.server = self.server()
                handler._reply = Mock()
                delattr(handler, missing)
                handler._serve_asset()
                handler._reply.assert_called_once_with(
                    403, b'Cross-site request rejected.\n', 'text/plain')

    def test_other_methods_keep_unsupported_status(self):
        for method in ('POST', 'PUT', 'DELETE', 'OPTIONS', 'CONNECT', 'PATCH'):
            with self.subTest(method=method):
                response, _ = self.request(method=method)
                self.assert_status(response, 501)

    def test_fetch_iframe_prefetch_and_missing_activation_are_rejected(self):
        cases = (
            [('Sec-Fetch-Site', 'cross-site')],
            [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'cors'), ('Sec-Fetch-Dest', 'empty')],
            [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'no-cors'), ('Sec-Fetch-Dest', 'empty')],
            [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'), ('Sec-Fetch-Dest', 'iframe'), ('Sec-Fetch-User', '?1')],
            [('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'), ('Sec-Fetch-Dest', 'document')],
        )
        for headers in cases:
            with self.subTest(headers=headers):
                response, _ = self.request(headers=[HOST] + headers)
                self.assert_status(response, 403)

    def test_missing_empty_unknown_or_combined_navigation_metadata_rejected(self):
        invalid = {
            'Sec-Fetch-Mode': ('', 'unknown', 'cors', 'no-cors', 'same-origin', 'websocket', 'navigate, cors'),
            'Sec-Fetch-Dest': ('', 'unknown', 'empty', 'iframe', 'frame', 'image', 'script', 'object', 'document, iframe'),
            'Sec-Fetch-User': ('', 'unknown', '?0', 'true', '?1, ?1'),
        }
        for name, values in invalid.items():
            for replacement in ([],) + tuple([value] for value in values):
                with self.subTest(name=name, values=replacement):
                    response, _ = self.request(headers=self.replaced(name, replacement))
                    self.assert_status(response, 403)

    def test_duplicate_navigation_metadata_rejected_in_both_orders(self):
        for name, valid in NAVIGATION:
            other = {'Sec-Fetch-Site': 'same-origin', 'Sec-Fetch-Mode': 'cors',
                     'Sec-Fetch-Dest': 'iframe', 'Sec-Fetch-User': '?0'}[name]
            for values in ([valid, valid], [valid, other], [other, valid]):
                with self.subTest(name=name, values=values):
                    response, _ = self.request(headers=self.replaced(name, values))
                    self.assert_status(response, 403)

    def test_duplicate_site_never_uses_first_value_as_authority(self):
        for values in (['same-origin', 'same-origin'], ['none', 'same-site'],
                       ['same-origin', 'cross-site'], ['cross-site', 'same-origin']):
            with self.subTest(values=values):
                response, _ = self.request(headers=[HOST] + [('Sec-Fetch-Site', value) for value in values])
                self.assert_status(response, 403)

    def test_malformed_or_combined_site_metadata_is_not_non_cross_site(self):
        for value in ('', 'unknown', 'CROSS-SITE', 'cross-site ', 'same-origin, cross-site',
                      'cross-site, same-origin', 'same-origin, same-origin', 'none, same-site'):
            with self.subTest(value=value):
                response, _ = self.request(headers=self.replaced('Sec-Fetch-Site', [value]))
                self.assert_status(response, 403)

    def test_speculative_purpose_cannot_claim_activated_navigation(self):
        for name in ('Purpose', 'Sec-Purpose'):
            for values in (['prefetch'], ['prefetch;prerender'], [''], ['unknown'],
                           ['prefetch', 'prefetch']):
                with self.subTest(name=name, values=values):
                    response, _ = self.request(headers=[HOST] + list(NAVIGATION) + [
                        (name, value) for value in values])
                    self.assert_status(response, 403)

    def test_navigation_still_requires_one_exact_host(self):
        for values in ([], [AUTHORITY, AUTHORITY], [AUTHORITY, 'example.invalid'],
                       ['localhost:41234'], ['127.0.0.1'], ['127.0.0.1:1'],
                       ['user@' + AUTHORITY], [AUTHORITY + ', ' + AUTHORITY]):
            with self.subTest(values=values):
                response, _ = self.request(headers=[('Host', value) for value in values] + list(NAVIGATION))
                self.assert_status(response, 421)

    def test_navigation_still_rejects_invalid_or_duplicate_origin(self):
        same = 'http://' + AUTHORITY
        for values in ([''], ['null'], ['https://' + AUTHORITY], ['http://example.invalid'],
                       [same, same], [same, 'null'], ['null', same], [same + ', ' + same]):
            with self.subTest(values=values):
                response, _ = self.request(headers=[HOST] + list(NAVIGATION) + [('Origin', value) for value in values])
                self.assert_status(response, 403)

    def test_navigation_rejects_body_headers_even_zero_or_empty(self):
        for name in ('Content-Length', 'Transfer-Encoding'):
            for values in (['0'], [''], ['1'], ['chunked'], ['0', '0']):
                with self.subTest(name=name, values=values):
                    response, _ = self.request(headers=[HOST] + list(NAVIGATION) + [
                        (name, value) for value in values], body=b'x')
                    self.assert_status(response, 403)

    def test_navigation_requires_exact_original_request_target(self):
        for path in ('/', '/favicon.ico', webrtc.ROUTE + '?token=synthetic-private',
                     webrtc.ROUTE + '?', webrtc.ROUTE + '#fragment', '/' + webrtc.ROUTE,
                     'http://' + AUTHORITY + webrtc.ROUTE, '/%77ebrtc-probe.html',
                     '/./webrtc-probe.html', webrtc.ROUTE + '/'):
            with self.subTest(path=path):
                response, _ = self.request(path=path)
                self.assert_status(response, 403)
                self.assertNotIn(b'synthetic-private', response)

    def test_ordinary_non_cross_site_get_and_head_keep_existing_behavior(self):
        for site in (None, 'none', 'same-origin', 'same-site'):
            for method in ('GET', 'HEAD'):
                headers = [HOST] + ([] if site is None else [('Sec-Fetch-Site', site)])
                with self.subTest(site=site, method=method):
                    response, _ = self.request(headers=headers, method=method)
                    self.assert_status(response, 200)
                    if method == 'HEAD':
                        self.assertEqual(response.split(b'\r\n\r\n', 1)[1], b'')
        # This compatibility exception must not impose navigation metadata on
        # ordinary same-origin callers or change their body/route status codes.
        for extra, path, status in (
                ([('Sec-Fetch-Mode', 'cors'), ('Sec-Fetch-Dest', 'empty')], webrtc.ROUTE, 200),
                ([('Sec-Fetch-Mode', 'cors'), ('Sec-Fetch-Mode', 'unknown')], webrtc.ROUTE, 200),
                ([('Content-Length', '0')], webrtc.ROUTE, 400),
                ([('Transfer-Encoding', 'chunked')], webrtc.ROUTE, 400),
                ([], webrtc.ROUTE + '?query', 404)):
            with self.subTest(extra=extra, path=path):
                response, _ = self.request(headers=[HOST] + extra, path=path)
                self.assert_status(response, status)

    def test_navigation_response_has_identical_security_headers(self):
        with patch.object(webrtc._AssetHandler, 'date_time_string', return_value='fixed'):
            ordinary, _ = self.request(headers=[HOST])
            navigation, _ = self.request()
        self.assertEqual(navigation, ordinary)
        for header in (
                b'Cache-Control: no-store\r\n', b'X-Content-Type-Options: nosniff\r\n',
                b'Referrer-Policy: no-referrer\r\n', b'X-Frame-Options: DENY\r\n',
                b'Cross-Origin-Resource-Policy: same-origin\r\n',
                b'Permissions-Policy: camera=(), microphone=(), geolocation=()\r\n',
                b"connect-src 'none'", b"frame-ancestors 'none'", b'Connection: close\r\n'):
            self.assertIn(header, navigation)
        self.assertNotIn(b'Access-Control-Allow-Origin:', navigation)
        self.assertNotIn(b'Set-Cookie:', navigation)

    def test_allowed_navigation_does_not_consume_once_diagnostic(self):
        server = self.server(diagnose=True)
        response, diagnostic = self.request(server=server)
        self.assert_status(response, 200)
        self.assertEqual(diagnostic, '')
        self.assertFalse(server._rejection_reported)
        response, diagnostic = self.request(server=server, method='HEAD')
        self.assert_status(response, 403)
        self.assertEqual(len(diagnostic.splitlines()), 1)
        self.assertIn('stage=fetch_site; method=HEAD; host=match; origin=absent', diagnostic)
        self.assertIn('exact_route=yes; content_length=absent; transfer_encoding=absent', diagnostic)
        self.assertIn('fetch_site=cross-site; fetch_mode=navigate; fetch_dest=document; fetch_user=?1', diagnostic)
        self.assertNotIn(AUTHORITY, diagnostic)
        self.assertNotIn(webrtc.ROUTE, diagnostic)
        response, diagnostic = self.request(server=server, headers=[])
        self.assert_status(response, 421)
        self.assertEqual(diagnostic, '')

    def test_duplicate_site_diagnostic_reports_real_refusal(self):
        response, diagnostic = self.request(server=self.server(diagnose=True),
            headers=self.replaced('Sec-Fetch-Site', ['same-origin', 'cross-site']))
        self.assert_status(response, 403)
        self.assertIn('stage=fetch_site', diagnostic)
        self.assertIn('fetch_site=duplicate', diagnostic)

    def test_default_rejections_are_silent_and_untrusted_values_not_reflected(self):
        private = 'synthetic-private-sentinel'
        response, diagnostic = self.request(headers=self.replaced('Sec-Fetch-Mode', [private]))
        self.assert_status(response, 403)
        self.assertEqual(diagnostic, '')
        self.assertNotIn(private.encode(), response)
        response, diagnostic = self.request(server=self.server(diagnose=True),
            headers=self.replaced('Sec-Fetch-Mode', [private]))
        self.assert_status(response, 403)
        self.assertIn('fetch_mode=invalid', diagnostic)
        self.assertNotIn(private, diagnostic)


if __name__ == '__main__':
    unittest.main()
