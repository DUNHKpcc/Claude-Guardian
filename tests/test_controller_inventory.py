"""Synthetic controller-only tests. Never connect to a user's controller."""
import importlib.util
import json
import os
from pathlib import Path
import socket
import threading
import time
import unittest
from unittest.mock import patch

SCRIPT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/controller_inventory.py'
spec = importlib.util.spec_from_file_location('controller_inventory', SCRIPT)
c = importlib.util.module_from_spec(spec)
spec.loader.exec_module(c)
SECRET = 'private-SENTINEL-password-url-name'


def binding(**changes):
    values = dict(target_ref='test-target', namespace_ref='test-netns',
                  desktop_user_ref='test-user', instance_ref='test-instance',
                  process_id=123, process_start_ref='test-start', host='127.0.0.1', port=54321)
    values.update(changes)
    return c.ControllerBinding(**values)


class Fake:
    def __init__(self, payload=None, status=200):
        self.payload = payload if payload is not None else {'mode': 'rule'}
        self.status, self.calls = status, []

    def __call__(self, bound, path, budget, deadline, cancelled):
        self.calls.append((bound, path))
        return self.status, json.dumps(self.payload).encode()


class ControllerTests(unittest.TestCase):
    def run_audit(self, paths=('/configs',), **kw):
        kw.setdefault('verify_binding', lambda bound: True)
        kw.setdefault('approve_read', lambda bound, path, budget: True)
        kw.setdefault('transport', Fake())
        return c.audit_controller(kw.pop('binding', binding()), paths, **kw)

    def test_safe_config_projection_and_provenance(self):
        result = self.run_audit(transport=Fake({'mode': 'rule', 'secret': SECRET,
                               'dns': {'nameserver': [SECRET]}, 'allow-lan': False,
                               'tun': {'enable': True, 'device': SECRET}}))
        self.assertEqual(result['execution_status'], 'completed')
        value = result['facts'][0]['value']
        self.assertEqual(value, {'mode': 'rule', 'allow-lan': False,
                                'tun_enabled_declared_by_controller': True})
        self.assertNotIn(SECRET, json.dumps(result))
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['facts'][0]['layer'], 'runtime_observed')
        self.assertEqual(result['coverage'], 'controller_snapshot_only')
        self.assertNotIn('fact_id', result['facts'][0])

    def test_only_numeric_loopback(self):
        for host in ('localhost', '127.1', '127.0.0.2', '0.0.0.0', '::',
                     '::ffff:127.0.0.1', '192.168.1.1', 'https://127.0.0.1', '::1%lo'):
            fake = Fake()
            result = self.run_audit(binding=binding(host=host), transport=fake)
            self.assertEqual(result['error_code'], 'CONTROLLER_NOT_BOUND', host)
            self.assertEqual(fake.calls, [])
        self.assertEqual(self.run_audit(binding=binding(host='::1'))['execution_status'], 'completed')

    def test_ports_and_identity_required(self):
        for changes in ({'port': 0}, {'port': True}, {'port': 65536},
                        {'process_id': 0}, {'namespace_ref': ''}, {'process_start_ref': ''}):
            fake = Fake()
            self.assertEqual(self.run_audit(binding=binding(**changes), transport=fake)['error_code'],
                             'CONTROLLER_NOT_BOUND')
            self.assertFalse(fake.calls)

    def test_exact_paths_only(self):
        for path in ('/connections', '/configs?x=1', '/version/', '/%76ersion',
                     '/dns/query', '/proxies/a/delay', '/logs', '/restart',
                     'http://127.0.0.1/version', '/rules\r\nAuthorization: x'):
            fake = Fake()
            self.assertEqual(self.run_audit((path,), transport=fake)['error_code'],
                             'INPUT_OR_RESPONSE_INVALID')
            self.assertFalse(fake.calls)

    def test_no_duplicates_or_unbounded_requests(self):
        for paths in ((), ('/version', '/version'), c.PATHS * 2):
            self.assertEqual(self.run_audit(paths)['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        self.assertEqual(self.run_audit(c.PATHS, budget=c.Budget(max_requests=2))['error_code'],
                         'INPUT_OR_RESPONSE_INVALID')

    def test_invalid_budgets(self):
        for budget in (c.Budget(max_seconds=float('nan')), c.Budget(max_seconds=float('inf')),
                       c.Budget(max_depth=33), c.Budget(max_bytes=0), c.Budget(max_nodes=True),
                       c.Budget(max_requests=5)):
            self.assertEqual(self.run_audit(budget=budget)['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_live_approval_exact_binding_path_budget(self):
        seen = []
        selected = binding()
        budget = c.Budget()
        def approve(bound, path, approved_budget):
            seen.append((bound, path, approved_budget))
            return path == '/version'
        fake = Fake({'meta': True, 'version': 'v1.19.0'})
        result = self.run_audit(('/version', '/configs'), binding=selected,
                                budget=budget, approve_read=approve, transport=fake)
        self.assertEqual(seen, [(selected, '/version', budget), (selected, '/configs', budget)])
        self.assertEqual(result['error_code'], 'AUTHORIZATION_MISSING')
        self.assertEqual(len(fake.calls), 1)

    def test_missing_or_non_boolean_attestation_blocks(self):
        for field in ('verify_binding', 'approve_read'):
            for answer in (False, None, 1, 'yes'):
                fake = Fake()
                result = self.run_audit(**{field: lambda *args: answer}, transport=fake)
                self.assertFalse(fake.calls)
                self.assertEqual(result['execution_status'], 'blocked')

    def test_binding_changed_after_request_discards_facts(self):
        answers = iter([True, True, True, True, True, False])
        fake = Fake({'meta': True})
        result = self.run_audit(('/version', '/configs'),
                                verify_binding=lambda b: next(answers), transport=fake)
        self.assertEqual(len(fake.calls), 2)
        self.assertEqual(result['error_code'], 'CONTROLLER_NOT_BOUND')
        self.assertEqual(result['facts'], [])

    def test_approval_wait_invalidates_binding_before_any_request(self):
        current = [True]
        def approve(*args):
            current[0] = False
            return True
        fake = Fake()
        result = self.run_audit(verify_binding=lambda b: current[0],
                                approve_read=approve, transport=fake)
        self.assertEqual(result['error_code'], 'CONTROLLER_NOT_BOUND')
        self.assertEqual(result['requests_attempted'], 0)
        self.assertFalse(fake.calls)

    def test_callback_controller_error_payload_is_never_public(self):
        def error(*args):
            raise c.ControllerError(SECRET)
        for callback in ('verify_binding', 'approve_read', 'cancelled', 'transport'):
            result = self.run_audit(**{callback: error})
            self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID', callback)
            self.assertNotIn(SECRET, json.dumps(result), callback)
        # Also reject arbitrary non-string exception payloads without serialization.
        def structured_error(*args):
            raise c.ControllerError({'private': SECRET})
        result = self.run_audit(transport=structured_error)
        self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_cancel_or_deadline_during_approval_prevents_request(self):
        state = [False]
        fake = Fake()
        def approve(*args):
            state[0] = True
            return True
        result = self.run_audit(approve_read=approve, cancelled=lambda: state[0], transport=fake)
        self.assertEqual(result['error_code'], 'CANCELLED')
        self.assertFalse(fake.calls)
        def slow_approve(*args):
            time.sleep(.02)
            return True
        result = self.run_audit(approve_read=slow_approve, budget=c.Budget(max_seconds=.01),
                                transport=fake)
        self.assertEqual(result['error_code'], 'TIMEOUT')
        self.assertFalse(fake.calls)

    def test_socket_send_uses_remaining_total_deadline(self):
        now, timeouts = [0.0], []
        class SyntheticSocket:
            def __enter__(self):
                return self
            def __exit__(self, *args):
                pass
            def settimeout(self, value):
                timeouts.append(value)
            def connect(self, address):
                now[0] = .4
            def sendall(self, request):
                raise c.ControllerError('TIMEOUT')
        with patch.object(c.socket, 'socket', return_value=SyntheticSocket()), \
             patch.object(c.time, 'monotonic', side_effect=lambda: now[0]):
            with self.assertRaises(c.ControllerError):
                c.loopback_transport(binding(), '/configs', c.Budget(), 1.0, lambda: False)
        self.assertEqual(timeouts, [1.0, .6])

    def test_auth_and_redirect_never_retry(self):
        for status in (401, 403, 301, 302, 303, 307, 308, 500):
            fake = Fake({'error': SECRET}, status=status)
            result = self.run_audit(('/version', '/configs'), transport=fake)
            expected = ('AUTHENTICATION_HANDOFF_REQUIRED' if status in (401, 403)
                        else 'CONTROLLER_RESPONSE_REJECTED')
            self.assertEqual(result['error_code'], expected)
            self.assertEqual(len(fake.calls), 1)
            self.assertNotIn(SECRET, json.dumps(result))

    def test_errors_never_echo_raw_content(self):
        for raw in (SECRET.encode(), b'{"x": NaN}', b'{"mode":"rule","mode":"global"}',
                    b'[]', b'\xff', b'{"mode":' + SECRET.encode()):
            result = self.run_audit(transport=lambda *args: (200, raw))
            self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
            self.assertNotIn(SECRET, json.dumps(result))
        def error(*args):
            raise RuntimeError(SECRET)
        self.assertNotIn(SECRET, json.dumps(self.run_audit(transport=error)))

    def test_depth_node_and_byte_budgets(self):
        for raw, budget in ((b'{"x":' + b'[' * 40 + b'0' + b']' * 40 + b'}', c.Budget()),
                            (b'{"x":[1,2,3,4]}', c.Budget(max_nodes=3)),
                            (b' ' * 21, c.Budget(max_bytes=20))):
            result = self.run_audit(transport=lambda *args: (200, raw), budget=budget)
            self.assertEqual(result['error_code'], 'BUDGET_EXCEEDED')

    def test_cancel_before_and_after_transport(self):
        fake = Fake()
        result = self.run_audit(cancelled=lambda: True, transport=fake)
        self.assertEqual(result['error_code'], 'CANCELLED')
        self.assertFalse(fake.calls)
        state = [False]
        def transport(*args):
            state[0] = True
            return 200, b'{}'
        result = self.run_audit(cancelled=lambda: state[0], transport=transport)
        self.assertEqual(result['error_code'], 'CANCELLED')
        self.assertEqual(result['facts'], [])

    def test_total_deadline_not_per_request(self):
        def slow(*args):
            time.sleep(.02)
            return 200, b'{}'
        result = self.run_audit(('/version', '/configs'), transport=slow,
                                budget=c.Budget(max_seconds=.01))
        self.assertEqual(result['error_code'], 'TIMEOUT')
        self.assertEqual(result['requests_attempted'], 1)

    def test_version_whitelist(self):
        self.assertEqual(self.run_audit(('/version',), transport=Fake({'meta': True,
                         'version': 'v1.19.0', 'extra': SECRET}))['facts'][0]['value'],
                         {'meta': True, 'version': 'v1.19.0'})
        self.assertEqual(self.run_audit(('/version',), transport=Fake({'version': SECRET}))
                         ['facts'][0]['value'], {})

    def test_rule_payload_and_names_discarded(self):
        payload = {'rules': [{'type': 'Domain', 'payload': SECRET, 'proxy': SECRET},
                             {'type': SECRET, 'hitCount': 900}]}
        result = self.run_audit(('/rules',), transport=Fake(payload))
        self.assertEqual(result['facts'][0]['value']['type_counts'], {'Domain': 1, 'unknown': 1})
        self.assertNotIn(SECRET, json.dumps(result))

    def test_proxy_graph_projection_direct_vs_selected(self):
        payload = {'proxies': {SECRET: {'type': 'Selector', 'all': ['d', 'p'], 'now': 'p',
                                       'history': [{'delay': SECRET}], 'testUrl': SECRET},
                               'd': {'type': 'Direct'}, 'p': {'type': 'Trojan', 'password': SECRET},
                               'lb': {'type': 'LoadBalance', 'all': ['d', 'p'], 'now': 'p'}}}
        result = self.run_audit(('/proxies',), transport=Fake(payload))
        groups = result['facts'][0]['value']['groups']
        self.assertTrue(groups[0]['has_direct_candidate'])
        self.assertEqual(groups[0]['selected_kind'], 'proxy')
        self.assertEqual(groups[1]['selected_kind'], 'not_applicable')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_raw_name_direct_does_not_imply_type(self):
        payload = {'proxies': {'g': {'all': ['DIRECT'], 'now': 'DIRECT', 'type': 'Selector'}}}
        group = self.run_audit(('/proxies',), transport=Fake(payload))['facts'][0]['value']['groups'][0]
        self.assertFalse(group['has_direct_candidate'])
        self.assertEqual(group['selected_kind'], 'unknown')

    def test_revisions_are_opaque_and_not_stable_hashes(self):
        a = self.run_audit()['facts'][0]['revision_ref']
        b = self.run_audit()['facts'][0]['revision_ref']
        self.assertNotEqual(a, b)
        self.assertTrue(a.startswith('revision-'))


class LocalTransportTests(unittest.TestCase):
    """Bind ephemeral synthetic listeners ourselves; no existing controller probes."""
    def serve_once(self, wire, delay=0):
        listener = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        listener.bind(('127.0.0.1', 0))
        listener.listen(1)
        listener.settimeout(2)
        port = listener.getsockname()[1]
        captured = []
        def serve():
            try:
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(1)
                    captured.append(conn.recv(8192))
                    time.sleep(delay)
                    try:
                        conn.sendall(wire)
                    except OSError:
                        pass
            finally:
                listener.close()
        thread = threading.Thread(target=serve, daemon=True)
        thread.start()
        self.addCleanup(thread.join, 3)
        return binding(port=port), captured

    def audit(self, bound, **kwargs):
        return c.audit_controller(bound, ('/configs',), verify_binding=lambda b: True,
                                  approve_read=lambda *args: True, **kwargs)

    def test_no_dns_no_proxy_no_credentials(self):
        body = b'{"mode":"rule","secret":"private-SENTINEL-password-url-name"}'
        bound, captured = self.serve_once(b'HTTP/1.1 200 OK\r\nContent-Length: ' +
                                         str(len(body)).encode() + b'\r\n\r\n' + body)
        with patch.object(socket, 'getaddrinfo', side_effect=AssertionError('DNS forbidden')), \
             patch.dict(os.environ, {'HTTP_PROXY': 'http://invalid:1', 'ALL_PROXY': 'http://invalid:1',
                                     'http_proxy': 'http://invalid:1', 'NO_PROXY': ''}):
            result = self.audit(bound)
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(len(captured), 1)
        request = captured[0].decode()
        self.assertTrue(request.startswith('GET /configs HTTP/1.1\r\n'))
        self.assertNotIn('Authorization', request)
        self.assertNotIn('Cookie', request)
        self.assertNotIn(SECRET, json.dumps(result))

    def test_redirect_is_not_followed(self):
        bound, captured = self.serve_once(b'HTTP/1.1 302 Found\r\nLocation: http://example.invalid/secret\r\n\r\n')
        with patch.object(socket, 'getaddrinfo', side_effect=AssertionError('DNS forbidden')):
            result = self.audit(bound)
        self.assertEqual(result['error_code'], 'CONTROLLER_RESPONSE_REJECTED')
        self.assertEqual(len(captured), 1)

    def test_auth_body_not_exposed(self):
        bound, _ = self.serve_once(b'HTTP/1.1 401 Unauthorized\r\n\r\n' + SECRET.encode())
        result = self.audit(bound)
        self.assertEqual(result['error_code'], 'AUTHENTICATION_HANDOFF_REQUIRED')
        self.assertNotIn(SECRET, json.dumps(result))

    def test_wire_size_including_headers_is_bounded(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\nX-Private: ' + b'x' * 4000 + b'\r\n\r\n{}')
        self.assertEqual(self.audit(bound, budget=c.Budget(max_bytes=100))['error_code'], 'BUDGET_EXCEEDED')

    def test_slow_response_deadline(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\n\r\n{}', delay=.15)
        result = self.audit(bound, budget=c.Budget(max_seconds=.03))
        self.assertEqual(result['error_code'], 'TIMEOUT')

    def test_cancel_during_read(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\n\r\n{}', delay=.2)
        start = time.monotonic()
        result = self.audit(bound, cancelled=lambda: time.monotonic() - start > .03)
        self.assertEqual(result['error_code'], 'CANCELLED')

    def test_ambiguous_or_invalid_http_framing_rejected(self):
        for headers, body in (
                (b'Content-Length: 15\r\nContent-Length: 999', b'{"mode":"rule"}'),
                (b'Content-Length: 15\r\nContent-Length: 15', b'{"mode":"rule"}'),
                (b'Content-Length: -1', b'{"mode":"rule"}'),
                (b'Content-Length: nope', b'{"mode":"rule"}'),
                (b'Content-Length: 999\r\nTransfer-Encoding: chunked',
                 b'f\r\n{"mode":"rule"}\r\n0\r\n\r\n'),
                (b'Transfer-Encoding: chunked\r\nTransfer-Encoding: chunked',
                 b'f\r\n{"mode":"rule"}\r\n0\r\n\r\n')):
            with self.subTest(headers=headers):
                bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\n' + headers + b'\r\n\r\n' + body)
                result = self.audit(bound)
                self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
                self.assertEqual(result['facts'], [])

    def test_truncated_body_rejected(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\nContent-Length: 200\r\n\r\n{}')
        self.assertEqual(self.audit(bound)['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_chunked_response_supported_bounded(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\nTransfer-Encoding: chunked\r\n\r\n'
                                   b'f\r\n{"mode":"rule"}\r\n0\r\n\r\n')
        # Correct chunk size is 15 bytes. Only the projected mode leaves transport.
        result = self.audit(bound)
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(result['facts'][0]['value'], {'mode': 'rule'})

    def test_compressed_body_rejected(self):
        bound, _ = self.serve_once(b'HTTP/1.1 200 OK\r\nContent-Encoding: gzip\r\n\r\n' + SECRET.encode())
        result = self.audit(bound)
        self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        self.assertNotIn(SECRET, json.dumps(result))


if __name__ == '__main__':
    unittest.main()
