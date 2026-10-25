"""Synthetic failures only: no socket, browser, STUN or native API calls."""
import contextlib
import ctypes
from email.message import Message
import errno
import io
import json
from pathlib import Path
import sys
import threading
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import serve_webrtc as webrtc


PRIVATE = '/private/test-path credential=synthetic-secret address=192.0.2.10'


class WebRTCDiagnosticTests(unittest.TestCase):
    def setUp(self):
        self.socket = patch.object(webrtc.socket, 'socket', side_effect=AssertionError('No socket allowed'))
        self.socket.start()
        self.addCleanup(self.socket.stop)
        self.bound = Mock(authority='127.0.0.1:41234')
        self.bind = patch.object(webrtc, '_BoundedServer', return_value=self.bound)
        self.bind_mock = self.bind.start()
        self.addCleanup(self.bind.stop)

    def run_main(self):
        stdout, stderr = io.StringIO(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            code = webrtc.main(['--duration', '0.1'])
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn('synthetic-secret', output)
        self.assertNotIn('Traceback', output)
        return code, output

    def test_bind_failure_is_distinct_and_redacted(self):
        for error, code in ((PermissionError(PRIVATE), 'PERMISSION_DENIED'),
                            (OSError(errno.EADDRINUSE, PRIVATE), 'ADDRESS_IN_USE'),
                            (OSError(errno.EADDRNOTAVAIL, PRIVATE), 'ADDRESS_UNAVAILABLE'),
                            (OSError(PRIVATE), 'IO_ERROR'),
                            (RuntimeError(PRIVATE), 'INVALID_STATE')):
            with self.subTest(code=code):
                self.bind_mock.side_effect = error
                status, output = self.run_main()
                self.assertEqual(status, 1)
                self.assertIn('stage=bind', output)
                self.assertIn('error=' + code, output)
                self.assertIn('probe_state=not_started', output)
                self.assertNotIn('http://', output)

    def test_asset_failure_precedes_bind(self):
        asset = Mock()
        asset.is_symlink.return_value = False
        asset.is_file.return_value = True
        asset.read_bytes.side_effect = OSError(PRIVATE)
        with patch.object(webrtc, 'ASSET', asset):
            status, output = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn('stage=asset', output)
        self.assertIn('error=IO_ERROR', output)
        self.bind_mock.assert_not_called()

    def test_asset_rejection_is_distinct_and_does_not_bind(self):
        for symlink, exists, body in ((True, True, b''), (False, False, b''),
                                      (False, True, b'x' * (128 * 1024 + 1))):
            asset = Mock()
            asset.is_symlink.return_value, asset.is_file.return_value = symlink, exists
            asset.read_bytes.return_value = body
            with patch.object(webrtc, 'ASSET', asset):
                status, output = self.run_main()
            self.assertEqual(status, 1)
            self.assertIn('stage=asset; error=INVALID_STATE; probe_state=not_started', output)
            self.bind_mock.assert_not_called()

    def test_serve_failure_after_url_never_claims_probe_not_started(self):
        for error, code in ((OSError(PRIVATE), 'IO_ERROR'),
                            (RuntimeError(PRIVATE), 'INVALID_STATE'),
                            (ValueError(PRIVATE), 'INVALID_STATE'),
                            (KeyError(PRIVATE), 'UNEXPECTED_ERROR')):
            with self.subTest(code=code), patch.object(webrtc.LocalProbeServer, 'serve', side_effect=error):
                status, output = self.run_main()
            self.assertEqual(status, 1)
            self.assertIn('http://127.0.0.1:41234/webrtc-probe.html', output)
            self.assertIn('stage=serve', output)
            self.assertIn('error=' + code, output)
            self.assertIn('probe_state=unknown', output)
            self.assertIn('Close any loaded probe page', output)
            self.assertNotIn('no probe was started', output.lower())
            self.assertNotIn('probe_state=not_started', output)

    def test_cleanup_failure_after_url_is_unknown(self):
        self.bound.server_close.side_effect = OSError(PRIVATE)
        with patch.object(webrtc.LocalProbeServer, 'serve'):
            status, output = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn('stage=cleanup', output)
        self.assertIn('probe_state=unknown', output)
        self.assertIn('Close any loaded probe page', output)

    def test_interrupt_after_url_warns_that_page_can_remain_active(self):
        with patch.object(webrtc.LocalProbeServer, 'serve', side_effect=KeyboardInterrupt):
            status, output = self.run_main()
        self.assertEqual(status, 130)
        self.assertIn('error=INTERRUPTED', output)
        self.assertIn('probe_state=unknown', output)
        self.assertIn('Close any loaded probe page', output)
        self.bound.server_close.assert_called_once_with()

    def test_interrupted_startup_still_exits_130_without_claiming_a_probe(self):
        self.bind_mock.side_effect = KeyboardInterrupt
        status, output = self.run_main()
        self.assertEqual(status, 130)
        self.assertIn('stage=bind', output)
        self.assertIn('error=INTERRUPTED', output)
        self.assertIn('probe_state=not_started', output)
        self.assertNotIn('http://', output)

    def test_partial_url_write_failure_is_conservatively_unknown(self):
        class PartialOutput(io.StringIO):
            def write(self, value):
                super().write(value[:10])
                raise OSError(PRIVATE)
        stdout, stderr = PartialOutput(), io.StringIO()
        with contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr), \
                patch.object(webrtc.LocalProbeServer, 'serve') as serve:
            status = webrtc.main(['--duration', '0.1'])
        self.assertEqual(status, 1)
        self.assertIn('stage=publish_url; error=IO_ERROR; probe_state=unknown', stderr.getvalue())
        self.assertIn('Close any loaded probe page', stderr.getvalue())
        self.assertNotIn(PRIVATE, stderr.getvalue())
        serve.assert_not_called()
        self.bound.server_close.assert_called_once_with()

    def test_unwritable_diagnostic_sink_still_returns_failure(self):
        sink = Mock()
        sink.write.side_effect = OSError(PRIVATE)
        self.bind_mock.side_effect = PermissionError(PRIVATE)
        with contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(sink):
            self.assertEqual(webrtc.main(['--duration', '0.1']), 1)

    def test_success_retains_zero_exit_and_closes_listener(self):
        with patch.object(webrtc.LocalProbeServer, 'serve') as serve:
            status, output = self.run_main()
        self.assertEqual(status, 0)
        self.assertIn('http://127.0.0.1:41234/webrtc-probe.html', output)
        self.assertNotIn('probe_state=', output)
        serve.assert_called_once_with(0.1)
        self.bound.server_close.assert_called_once_with()

    def test_deadline_cancellation_and_single_use_are_unchanged(self):
        with patch.object(webrtc.time, 'monotonic', side_effect=[10.0, 10.1, 10.2]):
            server = webrtc.LocalProbeServer()
            server.serve(0.15)
        self.bound.handle_request.assert_called_once_with()
        self.bound.server_close.assert_called_once_with()
        with self.assertRaisesRegex(RuntimeError, 'single-use'):
            server.serve(0.15)
        self.bound.reset_mock()
        cancelled = threading.Event()
        cancelled.set()
        server = webrtc.LocalProbeServer()
        server.serve(0.15, cancel_event=cancelled)
        self.bound.handle_request.assert_not_called()
        self.bound.server_close.assert_called_once_with()

    def test_actual_serve_exception_closes_listener(self):
        self.bound.handle_request.side_effect = OSError(PRIVATE)
        status, output = self.run_main()
        self.assertEqual(status, 1)
        self.assertIn('stage=serve; error=IO_ERROR; probe_state=unknown', output)
        self.bound.server_close.assert_called_once_with()

    def test_foreign_diagnostic_attribute_never_reaches_output(self):
        for value in (PRIVATE, [], {}, True, None):
            error = RuntimeError(PRIVATE)
            error._helper_stage = value
            with patch.object(webrtc.LocalProbeServer, 'serve', side_effect=error):
                status, output = self.run_main()
            self.assertEqual(status, 1)
            self.assertIn('stage=serve', output)

    def test_direct_constructor_preserves_permission_exception_type(self):
        self.bind_mock.side_effect = PermissionError(PRIVATE)
        with self.assertRaises(PermissionError):
            webrtc.LocalProbeServer()


class WebRTCRequestGuardTests(unittest.TestCase):
    def handler(self, headers, path=webrtc.ROUTE):
        handler = object.__new__(webrtc._AssetHandler)
        handler.server = SimpleNamespace(authority='127.0.0.1:41234', asset=b'fixed asset')
        handler.headers = Message()
        for name, value in headers:
            handler.headers[name] = value
        handler.path = path
        handler.requestline = 'GET ' + path + ' HTTP/1.0'
        handler._reply = Mock()
        return handler

    def test_exact_host_origin_and_body_guards_remain_closed(self):
        host = ('Host', '127.0.0.1:41234')
        for headers, status in (([], 421), ([('Host', 'example.test')], 421),
                ([host, host], 421), ([host, ('Origin', 'https://example.test')], 403),
                ([host, ('Origin', 'null')], 403),
                ([host, ('Origin', 'http://127.0.0.1:41234'),
                  ('Origin', 'http://127.0.0.1:41234')], 403),
                ([host, ('Sec-Fetch-Site', 'cross-site')], 403),
                ([host, ('Content-Length', '0')], 400),
                ([host, ('Transfer-Encoding', 'chunked')], 400)):
            with self.subTest(status=status):
                handler = self.handler(headers)
                handler._serve_asset()
                self.assertEqual(handler._reply.call_args.args[0], status)
        handler = self.handler([host, ('Origin', 'http://127.0.0.1:41234')])
        handler._serve_asset()
        handler._reply.assert_called_once_with(200, b'fixed asset', 'text/html; charset=utf-8')

    def test_only_fixed_origin_form_path_is_served(self):
        for path in ('/', '/webrtc-probe.html?secret=synthetic', '//webrtc-probe.html',
                     'http://127.0.0.1:41234/webrtc-probe.html', '/../private'):
            handler = self.handler([('Host', '127.0.0.1:41234')], path)
            handler._serve_asset()
            self.assertEqual(handler._reply.call_args.args[0], 404)
            self.assertNotIn('synthetic', str(handler._reply.call_args))


class WebRTCCleanupTests(unittest.TestCase):
    """Owned-resource lifecycle faults are injected; no actual sockets exist."""
    def setUp(self):
        guard = patch.object(webrtc.socket, 'socket', side_effect=AssertionError('No socket allowed'))
        guard.start()
        self.addCleanup(guard.stop)

    def raw_server(self):
        server = object.__new__(webrtc._BoundedServer)
        server.connection_lock = threading.Lock()
        server.connections = {Mock(), Mock()}
        server._pending_closes = set()
        server.closing = False
        return server, tuple(server.connections)

    def test_first_connection_close_failure_does_not_skip_other_resources(self):
        server, connections = self.raw_server()
        failure = OSError(PRIVATE)
        connections[0].close.side_effect = failure
        with patch.object(webrtc.ThreadingHTTPServer, 'server_close') as listener:
            with self.assertRaises(OSError) as caught:
                server.server_close()
        self.assertIs(caught.exception, failure)
        self.assertTrue(server.closing)
        for connection in connections:
            connection.shutdown.assert_called_once_with(webrtc.socket.SHUT_RDWR)
            connection.close.assert_called_once_with()
        listener.assert_called_once_with()

    def test_listener_failure_is_not_hidden_by_connection_failure(self):
        server, connections = self.raw_server()
        first_failure = OSError(PRIVATE)
        connections[0].close.side_effect = first_failure
        with patch.object(webrtc.ThreadingHTTPServer, 'server_close',
                          side_effect=PermissionError(PRIVATE)) as listener:
            with self.assertRaises(OSError) as caught:
                server.server_close()
        self.assertIs(caught.exception, first_failure)
        connections[1].close.assert_called_once_with()
        listener.assert_called_once_with()

    def test_shutdown_error_still_attempts_close_and_remaining_resources(self):
        server, connections = self.raw_server()
        connections[0].shutdown.side_effect = OSError(PRIVATE)
        with patch.object(webrtc.ThreadingHTTPServer, 'server_close') as listener:
            server.server_close()
        for connection in connections:
            connection.close.assert_called_once_with()
        listener.assert_called_once_with()

    def test_failed_resource_survives_request_thread_removing_active_connection(self):
        server, connections = self.raw_server()
        connections[0].close.side_effect = [OSError(PRIVATE), None]
        with patch.object(webrtc.ThreadingHTTPServer, 'server_close') as listener:
            with self.assertRaises(OSError):
                server.server_close()
            # A request thread can finish and discard its active entry between
            # cleanup attempts; its unconfirmed close must still be retried.
            server.connections.clear()
            server.server_close()
        self.assertEqual(connections[0].close.call_count, 2)
        self.assertEqual(connections[1].close.call_count, 1)
        self.assertEqual(listener.call_count, 2)
        self.assertFalse(server._pending_closes)

    def test_interrupted_shutdown_still_attempts_all_close_operations(self):
        server, connections = self.raw_server()
        connections[0].shutdown.side_effect = KeyboardInterrupt
        with patch.object(webrtc.ThreadingHTTPServer, 'server_close') as listener:
            with self.assertRaises(KeyboardInterrupt):
                server.server_close()
        for connection in connections:
            connection.close.assert_called_once_with()
        listener.assert_called_once_with()

    def test_failed_close_is_retryable_and_only_success_marks_closed(self):
        bound = Mock(authority='127.0.0.1:41234')
        bound.server_close.side_effect = [OSError(PRIVATE), None]
        with patch.object(webrtc, '_BoundedServer', return_value=bound):
            server = webrtc.LocalProbeServer()
        with self.assertRaises(OSError):
            server.close()
        self.assertTrue(server._cancel.is_set())
        self.assertFalse(server._closed)
        self.assertEqual(server._cleanup_state, 'unknown')
        server.close()
        self.assertTrue(server._closed)
        self.assertEqual(server._cleanup_state, 'complete')
        server.close()
        self.assertEqual(bound.server_close.call_count, 2)

    def run_main(self, primary, cleanup):
        bound = Mock(authority='127.0.0.1:41234')
        bound.handle_request.side_effect = primary
        bound.server_close.side_effect = cleanup
        stdout, stderr = io.StringIO(), io.StringIO()
        with patch.object(webrtc, '_BoundedServer', return_value=bound), \
                contextlib.redirect_stdout(stdout), contextlib.redirect_stderr(stderr):
            status = webrtc.main(['--duration', '0.1'])
        output = stdout.getvalue() + stderr.getvalue()
        self.assertNotIn(PRIVATE, output)
        self.assertNotIn('Traceback', output)
        self.assertNotIn('probe_state=not_started', output)
        self.assertIn('Close any loaded probe page', output)
        return status, output, bound

    def test_serve_and_cleanup_failure_preserve_primary_error_and_unknown_cleanup(self):
        status, output, bound = self.run_main(PermissionError(PRIVATE), OSError(PRIVATE))
        self.assertEqual(status, 1)
        self.assertIn('stage=serve; error=PERMISSION_DENIED; probe_state=unknown', output)
        self.assertIn('cleanup_state=unknown', output)
        self.assertNotIn('listener stopped', output.lower())
        self.assertEqual(bound.server_close.call_count, 2)

    def test_interrupt_and_cleanup_failure_preserve_exit_130(self):
        status, output, bound = self.run_main(KeyboardInterrupt(), OSError(PRIVATE))
        self.assertEqual(status, 130)
        self.assertIn('stage=serve; error=INTERRUPTED; probe_state=unknown', output)
        self.assertIn('cleanup_state=unknown', output)
        self.assertEqual(bound.server_close.call_count, 2)

    def test_transient_cleanup_failure_can_confirm_closed_without_hiding_primary(self):
        status, output, bound = self.run_main(PermissionError(PRIVATE), [OSError(PRIVATE), None])
        self.assertEqual(status, 1)
        self.assertIn('stage=serve; error=PERMISSION_DENIED; probe_state=unknown', output)
        self.assertIn('cleanup_state=complete', output)
        self.assertEqual(bound.server_close.call_count, 2)

    def test_successful_cleanup_does_not_hide_primary_serve_failure(self):
        status, output, bound = self.run_main(PermissionError(PRIVATE), None)
        self.assertEqual(status, 1)
        self.assertIn('stage=serve; error=PERMISSION_DENIED; probe_state=unknown', output)
        self.assertIn('cleanup_state=complete', output)
        self.assertEqual(bound.server_close.call_count, 1)

    def test_recovered_cleanup_error_without_serve_error_stays_failed(self):
        with patch.object(webrtc.time, 'monotonic', side_effect=[10.0, 10.2]):
            status, output, bound = self.run_main(None, [OSError(PRIVATE), None])
        self.assertEqual(status, 1)
        self.assertIn('stage=cleanup; error=IO_ERROR; probe_state=unknown', output)
        self.assertIn('cleanup_state=complete', output)
        self.assertEqual(bound.server_close.call_count, 2)


if __name__ == '__main__':
    unittest.main()
