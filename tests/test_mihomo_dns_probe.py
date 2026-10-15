"""Only injected data and test-owned loopback HTTP fixtures; no DNS resolution."""
import copy
import json
from pathlib import Path
import socket
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import mihomo_dns_probe as m

SECRET = 'DO-NOT-EXPORT-private-token'


def scope(name='reserved.test', query_type='A', **changes):
    values = dict(target_ref='test-device', namespace_ref='test-netns',
                  desktop_user_ref='test-user', instance_ref='test-instance',
                  process_id=123, process_start_ref='test-start', host='127.0.0.1', port=54321)
    values.update(changes)
    return m.QueryScope(m.ControllerBinding(**values), name, query_type)


def payload(query_type='A'):
    kind = m.TYPES[query_type]
    return {'Status': 0, 'Question': [{'Name': 'reserved.test.', 'Qtype': kind, 'Qclass': 1}],
            'TC': False, 'Answer': [{'name': 'reserved.test.', 'type': kind, 'TTL': 60,
                                    'data': '192.0.2.5' if kind == 1 else '2001:db8::5'}]}


class Fake:
    def __init__(self, value=None, status=200):
        self.value = payload() if value is None else value
        self.status, self.calls = status, []

    def __call__(self, *args):
        self.calls.append(args)
        return self.status, self.value if type(self.value) is bytes else json.dumps(self.value).encode()


class ProbeTests(unittest.TestCase):
    def run_probe(self, selected=None, **kw):
        kw.setdefault('verify_binding', lambda binding: True)
        kw.setdefault('approve_query', lambda selected, budget: True)
        kw.setdefault('transport', Fake())
        return m.probe_mihomo_dns(selected or scope(), **kw)

    def test_projection_redacts_all_private_data(self):
        obj = payload()
        obj.update(secret=SECRET, Authority=[{'data': SECRET}], Additional=[{'data': SECRET}])
        result = self.run_probe(transport=Fake(obj))
        self.assertEqual(result['execution_status'], 'completed')
        public = json.dumps(result)
        for private in (SECRET, 'reserved.test', '192.0.2.5', 'test-device', '54321'):
            self.assertNotIn(private, public)
        self.assertEqual(result['facts'][0]['value']['address_class_counts']['non_global'], 1)
        self.assertEqual(result['gate_state'], 'closed')
        self.assertIn('dns_leak_absence', result['not_tested'])

    def test_multicast_is_not_globally_routable(self):
        for kind, address in (('A', '224.0.0.1'), ('AAAA', 'ff02::1'),
                              ('A', '127.0.0.1'), ('AAAA', '::'),
                              ('A', '169.254.1.1')):
            obj = payload(kind)
            obj['Answer'][0]['data'] = address
            result = self.run_probe(scope(query_type=kind), transport=Fake(obj))
            self.assertEqual(result['facts'][0]['value']['address_class_counts'],
                             {'globally_routable': 0, 'non_global': 1})

    def test_both_query_types(self):
        for kind in ('A', 'AAAA'):
            result = self.run_probe(scope(query_type=kind), transport=Fake(payload(kind)))
            self.assertEqual(result['facts'][0]['value']['query_type'], kind)

    def test_exact_scope_and_rebinding_order(self):
        calls = []
        selected = scope()
        def verify(binding):
            self.assertIs(binding, selected.binding)
            calls.append('verify')
            return True
        def approve(actual, budget):
            self.assertIs(actual, selected)
            self.assertEqual(actual.path, '/dns/query?name=reserved.test&type=A')
            self.assertIn('upstream', actual.network_effect)
            self.assertEqual(budget.max_requests, 1)
            calls.append('approve')
            return True
        def transport(*args):
            calls.append('query')
            return Fake()(*args)
        result = self.run_probe(selected, verify_binding=verify, approve_query=approve, transport=transport)
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(calls, ['verify', 'approve', 'verify', 'query', 'verify'])

    def test_permission_and_binding_fail_closed(self):
        for kw, code in (({'approve_query': lambda *a: False}, 'AUTHORIZATION_MISSING'),
                         ({'approve_query': lambda *a: 1}, 'AUTHORIZATION_MISSING'),
                         ({'verify_binding': lambda *a: False}, 'CONTROLLER_NOT_BOUND')):
            fake = Fake()
            self.assertEqual(self.run_probe(transport=fake, **kw)['error_code'], code)
            self.assertFalse(fake.calls)
        for checks in ([True, False], [True, True, False]):
            fake = Fake()
            it = iter(checks)
            result = self.run_probe(verify_binding=lambda *a: next(it), transport=fake)
            self.assertEqual(result['error_code'], 'CONTROLLER_NOT_BOUND')
            self.assertEqual(result['facts'], [])
            self.assertEqual(len(fake.calls), len(checks) - 2)

    def test_invalid_query_no_io(self):
        for name in ('localhost', '127.0.0.1', 'https://reserved.test', 'a.test?x=y',
                     'a.test#frag', 'a.test&x=y', 'a.test\r\nX: y', 'a..test',
                     '*.test', 'a_test.test', 'UPPER.test', 'a.test.', 'é.test',
                     '-a.test', 'a-.test', 'a' * 64 + '.test', ''):
            fake = Fake()
            self.assertEqual(self.run_probe(scope(name=name), transport=fake)['error_code'],
                             'INPUT_OR_RESPONSE_INVALID', name)
            self.assertFalse(fake.calls)
        for kind in ('TXT', 'ANY', 'a', 1, None):
            self.assertEqual(self.run_probe(scope(query_type=kind))['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_pc0_forbidden(self):
        for name in ('claude.ai', 'api.anthropic.com', 'www.claude.com', 'evil-claude.test'):
            fake = Fake()
            self.assertEqual(self.run_probe(scope(name=name), transport=fake)['error_code'], 'PC0_TARGET_FORBIDDEN')
            self.assertFalse(fake.calls)

    def test_binding_and_budget_validation(self):
        for changes in ({'host': 'localhost'}, {'host': '10.0.0.1'}, {'port': 0},
                        {'process_start_ref': ''}, {'process_id': True}, {'namespace_ref': ''}):
            self.assertEqual(self.run_probe(scope(**changes))['error_code'], 'CONTROLLER_NOT_BOUND')
        for budget in (m.Budget(), m.Budget(max_requests=1, max_seconds=float('nan')),
                       m.Budget(max_requests=1, max_bytes=0), m.Budget(max_requests=1, max_depth=99)):
            self.assertEqual(self.run_probe(budget=budget)['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_question_context(self):
        for change in ({'Name': 'wrong.test.'}, {'Qtype': 28}, {'Qclass': 3}, {'Qtype': True}):
            obj = payload()
            obj['Question'][0].update(change)
            self.assertEqual(self.run_probe(transport=Fake(obj))['error_code'], 'RESPONSE_CONTEXT_MISMATCH')
        for questions in ([], [{}, {}], None):
            obj = payload()
            obj['Question'] = questions
            self.assertEqual(self.run_probe(transport=Fake(obj))['error_code'], 'RESPONSE_CONTEXT_MISMATCH')

    def test_cname_chain_and_unrelated_records(self):
        obj = payload()
        obj['Answer'][0]['name'] = 'alias.test.'
        obj['Answer'].append({'name': 'reserved.test.', 'type': 5, 'TTL': 4, 'data': 'alias.test.'})
        self.assertEqual(self.run_probe(transport=Fake(obj))['execution_status'], 'completed')
        for name in ('unrelated.test.', 'reserved.test.'):
            bad = copy.deepcopy(obj)
            bad['Answer'][1]['data'] = name
            self.assertEqual(self.run_probe(transport=Fake(bad))['error_code'], 'RESPONSE_CONTEXT_MISMATCH')
        obj['Answer'][0]['type'] = 28
        self.assertEqual(self.run_probe(transport=Fake(obj))['error_code'], 'RESPONSE_CONTEXT_MISMATCH')

    def test_maximum_length_cname_presentation(self):
        alias = '.'.join(('a' * 63, 'b' * 63, 'c' * 63, 'd' * 61))
        self.assertEqual(len(alias), 253)
        obj = payload()
        obj['Answer'][0]['name'] = alias + '.'
        obj['Answer'].append({'name': 'reserved.test.', 'type': 5,
                              'TTL': 60, 'data': alias + '.'})
        self.assertEqual(self.run_probe(transport=Fake(obj))['execution_status'], 'completed')
        obj['Answer'][1]['data'] = alias + 'e.'
        self.assertEqual(self.run_probe(transport=Fake(obj))['error_code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_negative_response_is_sample_not_pass(self):
        obj = payload()
        obj.update(Status=3, Answer=[])
        result = self.run_probe(transport=Fake(obj))
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(result['facts'][0]['value']['rcode'], 3)
        self.assertEqual(result['gate_state'], 'closed')

    def test_invalid_schema_and_json(self):
        for raw in (b'{"Status":0,"Status":1}', b'{}junk', b'{"x":NaN}', b'[]',
                    b'{"x":' + b'[' * 30 + b'0' + b']' * 30 + b'}'):
            result = self.run_probe(transport=Fake(raw))
            self.assertIsNotNone(result['error_code'])
            self.assertEqual(result['facts'], [])
        for change in ({'Status': True}, {'Status': -1}, {'Status': 4096}, {'TC': 1}, {'Answer': {}}):
            obj = payload()
            obj.update(change)
            self.assertEqual(self.run_probe(transport=Fake(obj))['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        self.assertEqual(self.run_probe(transport=Fake(), budget=m.Budget(max_requests=1, max_nodes=2))['error_code'], 'BUDGET_EXCEEDED')
        self.assertEqual(self.run_probe(transport=Fake(b' ' * 100), budget=m.Budget(max_requests=1, max_bytes=99))['error_code'], 'BUDGET_EXCEEDED')

    def test_status_never_retries(self):
        for status in (401, 403, 302, 500, True):
            fake = Fake(status=status)
            result = self.run_probe(transport=fake)
            self.assertEqual(len(fake.calls), 1)
            self.assertEqual(result['error_code'], 'AUTHENTICATION_HANDOFF_REQUIRED' if status in (401, 403) else 'CONTROLLER_RESPONSE_REJECTED')

    def test_cancel_timeout_and_exception_privacy(self):
        fake = Fake()
        self.assertEqual(self.run_probe(cancelled=lambda: True, transport=fake)['error_code'], 'CANCELLED')
        self.assertFalse(fake.calls)
        def slow(*args):
            time.sleep(.02)
            return True
        self.assertEqual(self.run_probe(approve_query=slow, budget=m.Budget(max_requests=1, max_seconds=.005))['error_code'], 'TIMEOUT')
        for error in (RuntimeError(SECRET), m.controller.ControllerError(SECRET), PermissionError(SECRET), TimeoutError(SECRET)):
            def fail(*args):
                raise error
            result = self.run_probe(transport=fail)
            self.assertNotIn(SECRET, json.dumps(result))
            self.assertEqual(result['facts'], [])

    def test_cancellation_after_query_discards_result(self):
        stopped = False
        def transport(*args):
            nonlocal stopped
            stopped = True
            return Fake()(*args)
        result = self.run_probe(transport=transport, cancelled=lambda: stopped)
        self.assertEqual(result['error_code'], 'CANCELLED')
        self.assertEqual(result['facts'], [])
        self.assertEqual(result['requests_attempted'], 1)

    def test_inventory_audit_still_rejects_dns(self):
        with self.assertRaises(m.controller.ControllerError):
            m.controller._validate(scope().binding, (scope().path,), m.Budget(max_requests=1))

    def test_owned_loopback_stalled_read_is_cancelled(self):
        received = threading.Event()
        finished = threading.Event()
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(2)
            def serve():
                conn, _ = listener.accept()
                with conn:
                    conn.settimeout(2)
                    conn.recv(4096)
                    received.set()
                    finished.wait(2)
            thread = threading.Thread(target=serve)
            thread.start()
            started = time.monotonic()
            try:
                result = self.run_probe(scope(port=listener.getsockname()[1]),
                                        transport=m.dns_loopback_transport,
                                        cancelled=received.is_set)
            finally:
                finished.set()
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertEqual(result['error_code'], 'CANCELLED')
            self.assertLess(time.monotonic() - started, 1)

    def fixture(self, response, **kw):
        captured = []
        errors = []
        with socket.socket() as listener:
            listener.bind(('127.0.0.1', 0))
            listener.listen(1)
            listener.settimeout(2)
            def serve():
                try:
                    conn, _ = listener.accept()
                    with conn:
                        conn.settimeout(2)
                        request = b''
                        while b'\r\n\r\n' not in request:
                            request += conn.recv(4096)
                        captured.append(request)
                        conn.sendall(response)
                except Exception as exc:
                    errors.append(type(exc).__name__)
            thread = threading.Thread(target=serve)
            thread.start()
            try:
                with patch.object(socket, 'getaddrinfo', side_effect=AssertionError('no resolver')):
                    result = self.run_probe(scope(port=listener.getsockname()[1]), transport=m.dns_loopback_transport, **kw)
            finally:
                thread.join(3)
            self.assertFalse(thread.is_alive())
            self.assertFalse(errors)
        return result, captured

    def test_owned_loopback_real_transport(self):
        body = json.dumps(payload()).encode()
        result, captured = self.fixture(b'HTTP/1.1 200 OK\r\nContent-Length: ' + str(len(body)).encode() + b'\r\n\r\n' + body)
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(len(captured), 1)
        self.assertTrue(captured[0].startswith(b'GET /dns/query?name=reserved.test&type=A HTTP/1.1\r\n'))
        self.assertNotIn(b'Authorization', captured[0])
        self.assertNotIn(b'Cookie', captured[0])

    def test_owned_loopback_framing_redirect_auth(self):
        for headers, body, code in (
                (b'302 Found\r\nLocation: http://elsewhere.test/', b'', 'CONTROLLER_RESPONSE_REJECTED'),
                (b'401 Unauthorized', b'', 'AUTHENTICATION_HANDOFF_REQUIRED'),
                (b'200 OK\r\nContent-Length: 2\r\nContent-Length: 2', b'{}', 'INPUT_OR_RESPONSE_INVALID'),
                (b'200 OK\r\nContent-Length: 20', b'{}', 'INPUT_OR_RESPONSE_INVALID'),
                (b'200 OK\r\nContent-Encoding: gzip', b'{}', 'INPUT_OR_RESPONSE_INVALID'),
                (b'200 OK\r\nContent-Length: 999999', b'', 'BUDGET_EXCEEDED')):
            result, captured = self.fixture(b'HTTP/1.1 ' + headers + b'\r\n\r\n' + body)
            self.assertEqual(result['error_code'], code)
            self.assertEqual(len(captured), 1)


if __name__ == '__main__':
    unittest.main()
