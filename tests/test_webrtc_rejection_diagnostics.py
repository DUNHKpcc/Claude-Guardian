"""Fixed rejection classifications; synthetic HTTP only, with no real sockets."""
import contextlib
from email.message import Message
import io
from pathlib import Path
import sys
import threading
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import serve_webrtc as webrtc


AUTHORITY = '127.0.0.1:41234'
HOST = ('Host', AUTHORITY)
PRIVATE = 'synthetic-private-sentinel'
PREFIX = 'Local WebRTC request rejected; '


class MemoryRequest:
    """The stdlib HTTP parser uses only byte streams; no socket is constructed."""
    def __init__(self, data):
        self.input = io.BytesIO(data)
        self.output = io.BytesIO()

    def makefile(self, _mode, _buffering):
        return self.input

    def sendall(self, data):
        self.output.write(data)


class RejectionDiagnosticTests(unittest.TestCase):
    def setUp(self):
        sockets = patch.object(webrtc.socket, 'socket', side_effect=AssertionError('No sockets allowed'))
        sockets.start()
        self.addCleanup(sockets.stop)
        browser = patch('webbrowser.open', side_effect=AssertionError('No browser allowed'))
        browser.start()
        self.addCleanup(browser.stop)

    def server(self, enabled=True):
        def initialize(server, *_args):
            server.server_port = 41234
        with patch.object(webrtc.ThreadingHTTPServer, '__init__', initialize):
            return webrtc._BoundedServer(b'fixed asset', diagnose_rejection=enabled)

    def request(self, server=None, *, headers=(HOST,), method='GET', path=webrtc.ROUTE, raw=None):
        if server is None:
            server = self.server()
        if raw is None:
            lines = [method + ' ' + path + ' HTTP/1.0']
            lines += [name + ': ' + value for name, value in headers]
            raw = ('\r\n'.join(lines) + '\r\n\r\n').encode('ascii')
        connection = MemoryRequest(raw)
        webrtc._AssetHandler(connection, ('127.0.0.1', 1), server)
        return connection.output.getvalue()

    def capture(self, **kwargs):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            response = self.request(**kwargs)
        return response, stderr.getvalue()

    def fields(self, output):
        self.assertEqual(len(output.splitlines()), 1)
        self.assertTrue(output.startswith(PREFIX), output)
        return dict(field.split('=', 1) for field in output.strip()[len(PREFIX):].split('; '))

    def test_cross_site_navigation_still_rejected_with_safe_classes(self):
        response, output = self.capture(headers=[HOST,
            ('Sec-Fetch-Site', 'cross-site'), ('Sec-Fetch-Mode', 'navigate'),
            ('Sec-Fetch-Dest', 'document'), ('Sec-Fetch-User', '?1')])
        self.assertTrue(response.startswith(b'HTTP/1.0 403 '))
        self.assertEqual(self.fields(output), {
            'stage': 'fetch_site', 'method': 'GET', 'host': 'match', 'origin': 'absent',
            'exact_route': 'yes', 'content_length': 'absent', 'transfer_encoding': 'absent',
            'fetch_site': 'cross-site', 'fetch_mode': 'navigate', 'fetch_dest': 'document',
            'fetch_user': '?1'})
        self.assertNotIn(AUTHORITY, output)
        self.assertNotIn(webrtc.ROUTE, output)

    def test_host_and_origin_match_absent_or_invalid_only(self):
        for headers, status, stage, host, origin in (
                ([], 421, 'host', 'absent', 'absent'),
                ([('Host', PRIVATE)], 421, 'host', 'invalid', 'absent'),
                ([HOST, HOST], 421, 'host', 'invalid', 'absent'),
                ([HOST, ('Origin', PRIVATE)], 403, 'origin', 'match', 'invalid'),
                ([HOST, ('Origin', 'null')], 403, 'origin', 'match', 'invalid'),
                ([HOST, ('Origin', 'http://' + AUTHORITY)] * 1 + [('Content-Length', '0')],
                 400, 'body', 'match', 'match'),
                ([HOST, ('Origin', 'http://' + AUTHORITY), ('Origin', 'http://' + AUTHORITY)],
                 403, 'origin', 'match', 'invalid')):
            with self.subTest(status=status, host=host, origin=origin):
                response, output = self.capture(headers=headers)
                self.assertTrue(response.startswith(('HTTP/1.0 ' + str(status) + ' ').encode()))
                fields = self.fields(output)
                self.assertEqual((fields['stage'], fields['host'], fields['origin']),
                                 (stage, host, origin))
                self.assertNotIn(PRIVATE, output)
                self.assertNotIn(AUTHORITY, output)

    def test_body_header_values_never_logged(self):
        for name, field in (('Content-Length', 'content_length'),
                            ('Transfer-Encoding', 'transfer_encoding')):
            for values in (['0'], [''], [PRIVATE], ['0', PRIVATE]):
                with self.subTest(name=name, count=len(values)):
                    response, output = self.capture(headers=[HOST] + [(name, value) for value in values])
                    self.assertTrue(response.startswith(b'HTTP/1.0 400 '))
                    fields = self.fields(output)
                    self.assertEqual(fields['stage'], 'body')
                    self.assertEqual(fields[field], 'present')
                    self.assertNotIn(PRIVATE, output)

    def test_route_is_only_an_exact_match_boolean(self):
        for path in ('/', '/' + PRIVATE, webrtc.ROUTE + '?' + PRIVATE,
                     '/' + webrtc.ROUTE, 'http://' + AUTHORITY + webrtc.ROUTE):
            with self.subTest(path=path):
                response, output = self.capture(path=path)
                self.assertTrue(response.startswith(b'HTTP/1.0 404 '))
                fields = self.fields(output)
                self.assertEqual(fields['stage'], 'route')
                self.assertEqual(fields['exact_route'], 'no')
                self.assertNotIn(PRIVATE, output)
                self.assertNotIn(AUTHORITY, output)
                self.assertNotIn(webrtc.ROUTE, output)

    def test_get_head_and_other_are_the_only_method_classes(self):
        for method, expected, status in (('GET', 'GET', 403), ('HEAD', 'HEAD', 403),
                                         ('POST', 'other', 501), (PRIVATE, 'other', 501)):
            with self.subTest(method=method):
                response, output = self.capture(method=method, headers=[HOST, ('Origin', PRIVATE)])
                self.assertTrue(response.startswith(('HTTP/1.0 ' + str(status) + ' ').encode()))
                self.assertEqual(self.fields(output)['method'], expected)
                self.assertNotIn(PRIVATE, output)
                if method == 'HEAD':
                    self.assertTrue(response.endswith(b'\r\n\r\n'))

    def test_parser_rejection_has_fixed_request_stage_without_headers(self):
        response, output = self.capture(raw=('GET /' + PRIVATE + ' HTTP/private\r\n\r\n').encode())
        self.assertIn(b'Request rejected.', response)
        fields = self.fields(output)
        self.assertEqual(fields['stage'], 'request')
        self.assertEqual(fields['method'], 'other')
        self.assertEqual(fields['host'], 'absent')
        self.assertEqual(fields['exact_route'], 'no')
        self.assertNotIn(PRIVATE, output)

    def test_fetch_headers_missing_invalid_and_duplicate(self):
        for name, field in (('Sec-Fetch-Site', 'fetch_site'), ('Sec-Fetch-Mode', 'fetch_mode'),
                            ('Sec-Fetch-Dest', 'fetch_dest'), ('Sec-Fetch-User', 'fetch_user')):
            for values, expected in (([], 'missing'), ([''], 'invalid'),
                                     ([PRIVATE], 'invalid'), ([PRIVATE, PRIVATE], 'duplicate')):
                with self.subTest(header=name, kind=expected):
                    response, output = self.capture(headers=[('Host', PRIVATE)] + [(name, v) for v in values])
                    self.assertTrue(response.startswith(b'HTTP/1.0 421 '))
                    self.assertEqual(self.fields(output)[field], expected)
                    self.assertNotIn(PRIVATE, output)

    def test_common_fetch_enums_are_reported_without_normalization(self):
        samples = {
            'Site': ('none', 'same-origin', 'same-site', 'cross-site'),
            'Mode': ('navigate', 'cors', 'no-cors', 'same-origin', 'websocket'),
            'Dest': ('document', 'empty', 'iframe', 'image', 'script', 'style', 'font', 'worker'),
            'User': ('?1',),
        }
        for suffix, values in samples.items():
            for value in values:
                with self.subTest(header=suffix, value=value):
                    _, output = self.capture(headers=[('Host', PRIVATE), ('Sec-Fetch-' + suffix, value)])
                    self.assertEqual(self.fields(output)['fetch_' + suffix.lower()], value)
            _, output = self.capture(headers=[('Host', PRIVATE), ('Sec-Fetch-' + suffix, values[0].upper())])
            # ?1 has no case; the other fields must not normalize unknown input.
            self.assertEqual(self.fields(output)['fetch_' + suffix.lower()],
                             values[0] if suffix == 'User' else 'invalid')
        _, output = self.capture(headers=[('Host', PRIVATE), ('Sec-Fetch-User', '?0')])
        self.assertEqual(self.fields(output)['fetch_user'], 'invalid')

    def test_duplicate_fetch_site_reports_duplicate_and_preserves_existing_gate(self):
        for values, status in ((['cross-site', 'same-origin'], 403),
                               (['same-origin', 'cross-site'], 200)):
            server = self.server()
            response, output = self.capture(server=server, headers=[HOST] + [('Sec-Fetch-Site', v) for v in values])
            self.assertTrue(response.startswith(('HTTP/1.0 ' + str(status) + ' ').encode()))
            if status == 403:
                self.assertEqual(self.fields(output)['fetch_site'], 'duplicate')
            else:
                self.assertEqual(output, '')
                _, output = self.capture(server=server, path='/rejected')
                self.assertEqual(self.fields(output)['stage'], 'route')

    def test_no_raw_fields_or_header_names_are_logged(self):
        response, output = self.capture(method=PRIVATE, path='/' + PRIVATE, headers=[
            ('Host', PRIVATE), ('Origin', PRIVATE), ('Referer', PRIVATE), ('Cookie', PRIVATE),
            ('Authorization', PRIVATE), ('X-' + PRIVATE, PRIVATE),
            ('Content-Length', PRIVATE), ('Transfer-Encoding', PRIVATE),
            ('Sec-Fetch-Site', PRIVATE), ('Sec-Fetch-Mode', PRIVATE),
            ('Sec-Fetch-Dest', PRIVATE), ('Sec-Fetch-User', PRIVATE)])
        self.assertTrue(response.startswith(b'HTTP/1.0 501 '))
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn(PRIVATE.encode(), response)
        self.assertNotIn('Referer', output)
        self.assertNotIn('Cookie', output)
        self.assertNotIn('Authorization', output)
        self.assertNotIn('HTTP/1', output)
        self.assertLess(len(output), 512)
        self.assertEqual(self.fields(output)['stage'], 'request')

    def test_default_is_silent_and_success_does_not_use_the_once_slot(self):
        server = self.server(enabled=False)
        response, output = self.capture(server=server, headers=[])
        self.assertTrue(response.startswith(b'HTTP/1.0 421 '))
        self.assertEqual(output, '')
        server = self.server()
        response, output = self.capture(server=server)
        self.assertTrue(response.startswith(b'HTTP/1.0 200 '))
        self.assertEqual(output, '')
        _, output = self.capture(server=server, headers=[])
        self.assertEqual(self.fields(output)['stage'], 'host')
        _, output = self.capture(server=server, path='/again')
        self.assertEqual(output, '')

    def test_once_budget_is_separate_per_server(self):
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            for _ in range(2):
                server = self.server()
                self.request(server=server, headers=[])
                self.request(server=server, headers=[])
        self.assertEqual(len(stderr.getvalue().splitlines()), 2)

    def test_concurrent_rejections_emit_at_most_once(self):
        server = self.server()
        start = threading.Barrier(16)
        responses, errors = [], []
        lock = threading.Lock()
        def reject():
            try:
                start.wait(timeout=5)
                response = self.request(server=server, headers=[])
                with lock:
                    responses.append(response)
            except BaseException as error:
                with lock:
                    errors.append(error)
        stderr = io.StringIO()
        with contextlib.redirect_stderr(stderr):
            threads = [threading.Thread(target=reject) for _ in range(16)]
            for thread in threads:
                thread.start()
            for thread in threads:
                thread.join(5)
        self.assertTrue(all(not thread.is_alive() for thread in threads))
        self.assertEqual(errors, [])
        self.assertEqual(len(responses), 16)
        self.assertTrue(all(response.startswith(b'HTTP/1.0 421 ') for response in responses))
        self.assertEqual(self.fields(stderr.getvalue())['stage'], 'host')

    def test_output_sink_failures_do_not_change_response_or_retry_diagnostic(self):
        for error in (OSError(PRIVATE), ValueError(PRIVATE), RuntimeError(PRIVATE)):
            with self.subTest(error=type(error).__name__):
                server = self.server()
                with patch('builtins.print', side_effect=error) as output:
                    response = self.request(server=server, headers=[])
                    second = self.request(server=server, path='/later')
                self.assertTrue(response.startswith(b'HTTP/1.0 421 '))
                self.assertTrue(second.startswith(b'HTTP/1.0 404 '))
                output.assert_called_once()

    def test_security_headers_and_bodies_equal_without_diagnostics(self):
        cases = ({}, {'headers': []}, {'headers': [HOST, ('Origin', PRIVATE)]},
                 {'headers': [HOST, ('Sec-Fetch-Site', 'cross-site')]},
                 {'headers': [HOST, ('Content-Length', '0')]}, {'path': '/rejected'},
                 {'method': 'POST'}, {'method': 'HEAD', 'path': '/rejected'})
        for case in cases:
            with self.subTest(case=case), patch.object(webrtc._AssetHandler, 'date_time_string', return_value='fixed'):
                disabled, silent = self.capture(server=self.server(False), **case)
                enabled, _ = self.capture(server=self.server(True), **case)
                self.assertEqual(enabled, disabled)
                self.assertEqual(silent, '')
                self.assertIn(b'Cache-Control: no-store\r\n', enabled)
                self.assertIn(b'Cross-Origin-Resource-Policy: same-origin\r\n', enabled)
                self.assertIn(b'X-Frame-Options: DENY\r\n', enabled)
                self.assertNotIn(b'Access-Control-Allow-Origin:', enabled)
                self.assertNotIn(b'Set-Cookie:', enabled)

    def test_cli_option_is_explicit_and_constructor_default_is_false(self):
        for args, enabled in (([], False), (['--diagnose-rejection'], True)):
            with self.subTest(enabled=enabled):
                server = Mock(url='http://' + AUTHORITY + webrtc.ROUTE)
                server.__enter__ = Mock(return_value=server)
                server.__exit__ = Mock(return_value=False)
                with patch.object(webrtc, 'LocalProbeServer', return_value=server) as constructor, \
                        contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
                    self.assertEqual(webrtc.main(args), 0)
                constructor.assert_called_once_with(diagnose_rejection=enabled)
                server.serve.assert_called_once_with(webrtc.DEFAULT_DURATION)
        for kwargs, expected in (({}, False), ({'diagnose_rejection': True}, True)):
            with patch.object(webrtc, '_BoundedServer', return_value=Mock(authority=AUTHORITY)) as constructor, \
                    patch.object(webrtc, '_read_asset', return_value=b'fixed asset'):
                webrtc.LocalProbeServer(**kwargs)
            constructor.assert_called_once_with(b'fixed asset', expected)


if __name__ == '__main__':
    unittest.main()
