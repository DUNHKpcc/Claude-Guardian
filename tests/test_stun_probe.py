"""Offline STUN vectors, injected sockets, and owned loopback UDP only."""
import importlib.util
import ipaddress
from pathlib import Path
import socket
import struct
import threading
import unittest
import zlib

FILE = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/stun_probe.py'
spec = importlib.util.spec_from_file_location('stun_probe', FILE)
s = importlib.util.module_from_spec(spec)
spec.loader.exec_module(s)
TX = bytes(range(12))


def attribute(kind, value):
    return struct.pack('!HH', kind, len(value)) + value + b'\0' * (-len(value) % 4)


def response(tx=TX, ip='192.0.2.1', port=32853, extra=b''):
    address = ipaddress.ip_address(ip)
    mask = struct.pack('!I', s.COOKIE) + tx
    value = struct.pack('!BBH', 0, 1 if address.version == 4 else 2, port ^ 0x2112)
    value += bytes(a ^ b for a, b in zip(address.packed, mask))
    attrs = attribute(0x20, value) + extra
    return struct.pack('!HHI', 0x101, len(attrs), s.COOKIE) + tx + attrs


class CodecTests(unittest.TestCase):
    def test_request_known_bytes_and_randomness(self):
        self.assertEqual(s.binding_request(TX), bytes.fromhex('000100002112a442') + TX)
        requests = {s.binding_request() for _ in range(32)}
        self.assertEqual(len(requests), 32)
        self.assertTrue(all(len(p) == 20 for p in requests))

    def test_both_families(self):
        for ip in ('192.0.2.1', '2001:db8:1234::abcd'):
            self.assertEqual(s.parse_binding_response(response(ip=ip), TX),
                             (ip, 32853, ipaddress.ip_address(ip).version))

    def test_rfc5769_ipv4_mapping_vector(self):
        # RFC 5769 section 2.2's txid and XOR-MAPPED bytes, independently known.
        tx = bytes.fromhex('b7e7a701bc34d686fa87dfae')
        p = bytes.fromhex('0101000c2112a442') + tx + bytes.fromhex('002000080001a147e112a643')
        self.assertEqual(s.parse_binding_response(p, tx), ('192.0.2.1', 32853, 4))

    def test_rfc5769_ipv6_mapping_vector(self):
        # RFC 5769 section 2.3 mapping bytes; no local encoder round-trip.
        tx = bytes.fromhex('b7e7a701bc34d686fa87dfae')
        attrs = bytes.fromhex('002000140002a1470113a9faa5d3f179bc25f4b5bed2b9d9')
        packet = bytes.fromhex('010100182112a442') + tx + attrs
        self.assertEqual(s.parse_binding_response(packet, tx),
                         ('2001:db8:1234:5678:11:2233:4455:6677', 32853, 6))

    def test_all_truncations_and_trailing_data(self):
        packet = response(extra=attribute(0x8022, b'x'))
        for n in range(len(packet)):
            with self.subTest(n=n), self.assertRaises(s.StunError):
                s.parse_binding_response(packet[:n], TX)
        with self.assertRaises(s.StunError):
            s.parse_binding_response(packet + b'\0', TX)

    def test_wrong_header_and_transaction(self):
        for index in (0, 1, 2, 4, 8):
            packet = bytearray(response())
            packet[index] ^= 1
            with self.assertRaises(s.StunError):
                s.parse_binding_response(bytes(packet), TX)

    def test_malformed_attributes(self):
        for attrs in (b'\x00\x20\xff\xff', attribute(0x20, b'\0' * 4),
                      attribute(0x20, b'\0\x03' + b'\0' * 6),
                      attribute(0x20, b'\0\x02' + b'\0' * 6)):
            packet = struct.pack('!HHI', 0x101, len(attrs), s.COOKIE) + TX + attrs
            with self.assertRaises(s.StunError):
                s.parse_binding_response(packet, TX)

    def test_unknown_required_and_missing_mapping(self):
        with self.assertRaisesRegex(s.StunError, 'unsupported_attribute'):
            s.parse_binding_response(response(extra=attribute(0x1111, b'')), TX)
        with self.assertRaisesRegex(s.StunError, 'missing_mapping'):
            s.parse_binding_response(struct.pack('!HHI', 0x101, 0, s.COOKIE) + TX, TX)

    def test_optional_padding_ignored_first_mapping_wins(self):
        packet = response(extra=attribute(0x8022, b'x')[:-3] + b'abc' + response(ip='192.0.2.2')[20:])
        self.assertEqual(s.parse_binding_response(packet, TX)[0], '192.0.2.1')

    def test_fingerprint(self):
        packet = bytearray(response())
        packet[2:4] = struct.pack('!H', len(packet) - 20 + 8)
        packet = bytes(packet) + attribute(0x8028, struct.pack('!I', zlib.crc32(packet) ^ 0x5354554e))
        self.assertEqual(s.parse_binding_response(packet, TX)[0], '192.0.2.1')
        with self.assertRaisesRegex(s.StunError, 'invalid_fingerprint'):
            s.parse_binding_response(packet[:-1] + bytes([packet[-1] ^ 1]), TX)

    def test_invalid_input_types_size(self):
        for packet in (None, '', bytearray(response()), b'x' * 4097):
            with self.assertRaises(s.StunError):
                s.parse_binding_response(packet, TX)
        for tx in (None, b'1', '123456789012'):
            with self.assertRaises(s.StunError):
                s.parse_binding_response(response(), tx)
        with self.assertRaises(s.StunError):
            s.binding_request(b'short')


class Clock:
    def __init__(self):
        self.now = 0.0
    def __call__(self):
        return self.now


class FakeSocket:
    def __init__(self, clock, packets=None):
        self.clock, self.packets = clock, list(packets or [])
        self.sent, self.closed, self.timeout = [], False, None
    def settimeout(self, seconds):
        self.timeout = seconds
    def sendto(self, packet, peer):
        self.sent.append((packet, peer))
        return len(packet)
    def recvfrom(self, maximum):
        self.maximum = maximum
        if self.packets:
            p = self.packets.pop(0)
            return p(self) if callable(p) else p
        self.clock.now += self.timeout
        raise TimeoutError()
    def close(self):
        self.closed = True


def good(fake):
    packet, peer = fake.sent[-1]
    return response(tx=packet[8:20]), peer


class TransactionTests(unittest.TestCase):
    def setUp(self):
        self.scope = s.Scope('owned-loopback-fixture', '127.0.0.1', 3478, 4, 'fixture-target')
        self.clock = Clock()
        self.fake = FakeSocket(self.clock)
        self.opened = 0
    def factory(self, *args):
        self.opened += 1
        return self.fake
    def run_probe(self, **kw):
        args = dict(approve=lambda scope: scope, current_target=lambda: 'fixture-target',
                    cancelled=lambda: False, socket_factory=self.factory, monotonic=self.clock)
        args.update(kw)
        return s.probe_stun(self.scope, **args)

    def test_success_and_evidence_boundary(self):
        self.fake.packets = [good]
        result = self.run_probe()
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['path_association'], 'unknown')
        self.assertEqual(result['target_path'], 'not_observed')
        self.assertFalse(result['authenticated'])
        self.assertTrue(self.fake.closed)
        self.assertEqual(self.fake.maximum, s.MAX_PACKET + 1)

    def test_three_sends_same_transaction_and_deadline(self):
        result = self.run_probe()
        self.assertEqual(result['error'], 'timeout')
        self.assertEqual(result['sends'], 3)
        self.assertEqual(len({p for p, _ in self.fake.sent}), 1)
        self.assertLessEqual(self.clock.now, 3.500001)
        self.assertTrue(self.fake.closed)

    def test_preflight_gates_no_socket(self):
        for kw, code in ((dict(approve=lambda _: True), 'approval_required'),
                         (dict(cancelled=lambda: True), 'cancelled'),
                         (dict(current_target=lambda: 'other'), 'target_changed')):
            self.assertEqual(self.run_probe(**kw)['error'], code)
        self.assertEqual(self.opened, 0)

    def test_exact_scope_no_boolean_approval(self):
        for field, value in (('peer_port', 7777), ('target_ref', 'other'), ('path_kind', 'explicit_proxy')):
            result = self.run_probe(approve=lambda scope: scope._replace(**{field: value}))
            self.assertEqual(result['error'], 'approval_required')
        self.assertEqual(self.opened, 0)

    def test_gate_changes_after_socket_creation(self):
        for kw, code in ((dict(cancelled=lambda: self.opened > 0), 'cancelled'),
                         (dict(current_target=lambda: 'other' if self.opened else 'fixture-target'), 'target_changed'),
                         (dict(approve=lambda scope: None if self.opened else scope), 'approval_required')):
            self.opened = 0
            result = self.run_probe(**kw)
            self.assertEqual(result['error'], code)
            self.assertEqual(result['sends'], 0)
            self.assertTrue(self.fake.closed)

    def test_cancel_after_response_not_observed(self):
        def packet(fake):
            self.stopped = True
            return good(fake)
        self.stopped = False
        self.fake.packets = [packet]
        result = self.run_probe(cancelled=lambda: self.stopped)
        self.assertEqual(result['error'], 'cancelled')
        self.assertIsNone(result['observed_ip'])

    def test_revocation_after_first_send_prevents_retransmit(self):
        result = self.run_probe(approve=lambda scope: None if self.fake.sent else scope)
        self.assertEqual(result['error'], 'approval_required')
        self.assertEqual(result['sends'], 1)
        self.assertTrue(self.fake.closed)

    def test_permission_denied_and_short_send(self):
        def denied(*args):
            raise PermissionError('SECRET_SENTINEL')
        self.assertEqual(self.run_probe(socket_factory=denied)['error'], 'permission_denied')
        self.fake.sendto = lambda *args: 1
        result = self.run_probe()
        self.assertEqual(result['error'], 'transport_error')
        self.assertEqual(result['sends'], 1)
        self.assertTrue(self.fake.closed)

    def test_slow_approval_cannot_send(self):
        def approve(scope):
            self.clock.now += 10
            return scope
        result = self.run_probe(approve=approve)
        self.assertEqual(result['error'], 'timeout')
        self.assertEqual(self.opened, 0)

    def test_adversarial_then_valid(self):
        self.fake.packets = [lambda f: (good(f)[0], ('127.0.0.2', 3478)),
                             lambda f: (response(), f.sent[-1][1]),
                             lambda f: (b'x' * 4097, f.sent[-1][1]),
                             lambda f: (response(tx=f.sent[-1][0][8:20], ip='2001:db8::1'), f.sent[-1][1]), good]
        result = self.run_probe()
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['rejected'], 4)

    def test_correlated_terminal_responses_stop_before_good_packet(self):
        def unsupported(fake):
            p, peer = good(fake)
            return response(tx=p[8:20], extra=attribute(0x1234, b'')), peer
        def server_error(fake):
            p, peer = good(fake)
            attrs = attribute(9, b'\0\0\x04\0bad request')
            return struct.pack('!HHI', 0x111, len(attrs), s.COOKIE) + p[8:20] + attrs, peer
        for packet, code in ((unsupported, 'unsupported_attribute'), (server_error, 'server_error')):
            self.setUp()
            self.fake.packets = [packet, good]
            result = self.run_probe()
            self.assertEqual(result['error'], code)
            self.assertEqual(result['status'], 'unknown')
            self.assertEqual(result['received'], 1)
            self.assertEqual(len(self.fake.packets), 1)
            self.assertTrue(self.fake.closed)

    def test_unknown_required_does_not_hide_corruption(self):
        def bad_tail(fake):
            p, peer = good(fake)
            return response(tx=p[8:20], extra=attribute(0x1234, b'') + b'\x80\x22\xff\xff'), peer
        def bad_fingerprint(fake):
            p, peer = good(fake)
            return response(tx=p[8:20], extra=attribute(0x1234, b'') + attribute(0x8028, b'bad!')), peer
        self.fake.packets = [bad_tail, bad_fingerprint, good]
        result = self.run_probe()
        self.assertEqual(result['status'], 'observed')
        self.assertEqual(result['rejected'], 2)

    def test_flood_bounded(self):
        self.fake.packets = [(b'x', ('127.0.0.1', 3478))] * 100
        result = self.run_probe()
        self.assertEqual(result['error'], 'receive_budget_exhausted')
        self.assertEqual(result['received'], 64)
        self.assertTrue(self.fake.closed)

    def test_bad_budgets_and_scope(self):
        for budget in (True, float('nan'), float('inf'), 0, -1, 6, '3'):
            with self.assertRaisesRegex(s.StunError, 'invalid_budget'):
                self.run_probe(total_seconds=budget)
        for scope in (self.scope._replace(peer_ip='example.org'), self.scope._replace(peer_port=True),
                      self.scope._replace(endpoint='stun:evil.example:3478'),
                      self.scope._replace(family=6), self.scope._replace(path_kind='explicit_proxy'),
                      self.scope._replace(endpoint=s.ENDPOINT)):
            with self.assertRaises(s.StunError):
                s.probe_stun(scope, approve=lambda _: True, current_target=lambda: '', cancelled=lambda: False)
        self.assertEqual(self.opened, 0)

    def test_errors_sanitized_and_cleanup(self):
        def fail(*args):
            raise RuntimeError('SECRET_SENTINEL')
        self.assertEqual(self.run_probe(approve=fail)['error'], 'callback_error')
        self.fake.sendto = fail
        result = self.run_probe()
        self.assertEqual(result['error'], 'transport_error')
        self.assertNotIn('SECRET_SENTINEL', repr(result))
        self.assertTrue(self.fake.closed)

    def test_invalid_clocks_fail_closed(self):
        for value in (float('nan'), float('inf'), -float('inf'), True, '1', None):
            with self.subTest(value=value):
                result = self.run_probe(monotonic=lambda: value)
                self.assertEqual(result['error'], 'invalid_clock')
                self.assertEqual(result['sends'], 0)
                self.assertIsNone(result['observed_ip'])
        values = iter([1.0, 0.0])
        self.assertEqual(self.run_probe(monotonic=lambda: next(values))['error'], 'invalid_clock')
        self.assertEqual(self.opened, 0)

    def test_constant_clock_and_nonblocking_timeout_bounded(self):
        result = self.run_probe(monotonic=lambda: 1.0)
        self.assertEqual(result['error'], 'poll_budget_exhausted')
        self.assertEqual(result['polls'], s.MAX_POLLS)
        self.assertEqual(result['sends'], 1)
        self.assertTrue(self.fake.closed)

    def test_cleanup_rechecks_cancellation_target_clock_and_approval(self):
        for change, expected in (('cancel', 'cancelled'), ('target', 'target_changed'),
                                 ('deadline', 'timeout'), ('approval', 'approval_required'),
                                 ('nan', 'invalid_clock'), ('backward', 'invalid_clock')):
            with self.subTest(change=change):
                self.setUp()
                self.fake.packets = [good]
                state = {'closed': False}
                def close():
                    self.fake.closed = True
                    state['closed'] = True
                    if change == 'deadline':
                        self.clock.now = 10
                    elif change == 'nan':
                        self.clock.now = float('nan')
                    elif change == 'backward':
                        self.clock.now = -1
                self.fake.close = close
                result = self.run_probe(
                    cancelled=lambda: state['closed'] and change == 'cancel',
                    current_target=lambda: 'other' if state['closed'] and change == 'target' else 'fixture-target',
                    approve=lambda scope: None if state['closed'] and change == 'approval' else scope)
                self.assertEqual(result['status'], 'unknown')
                self.assertEqual(result['error'], expected)
                self.assertIsNone(result['observed_ip'])
                self.assertIsNone(result['observed_port'])
                self.assertIsNone(result['observed_address_family'])

    def test_cleanup_failure_invalidates_success(self):
        self.fake.packets = [good]
        def fail():
            raise OSError('SECRET_SENTINEL')
        self.fake.close = fail
        result = self.run_probe()
        self.assertEqual(result['error'], 'cleanup_failed')
        self.assertEqual(result['status'], 'unknown')
        self.assertIsNone(result['observed_ip'])


class LoopbackTests(unittest.TestCase):
    def exchange(self, family, address):
        try:
            server = socket.socket(family, socket.SOCK_DGRAM)
            server.bind((address, 0))
        except OSError as exc:
            if family == socket.AF_INET6:
                self.skipTest('IPv6 loopback unavailable: ' + str(exc.errno))
            raise
        server.settimeout(2)
        failures = []
        def serve():
            try:
                packet, peer = server.recvfrom(100)
                server.sendto(b'truncated', peer)
                server.sendto(response(tx=bytes(12)), peer)
                server.sendto(response(tx=packet[8:20], ip=address), peer)
            except Exception as exc:
                failures.append(type(exc).__name__)
        worker = threading.Thread(target=serve)
        worker.start()
        try:
            scope = s.Scope('owned-loopback-fixture', address, server.getsockname()[1],
                            4 if family == socket.AF_INET else 6, 'owned-loopback')
            result = s.probe_stun(scope, approve=lambda exact: exact,
                                  current_target=lambda: 'owned-loopback', cancelled=lambda: False)
            self.assertEqual(result['status'], 'observed')
            self.assertEqual(result['observed_ip'], address)
            self.assertEqual(result['rejected'], 2)
            self.assertEqual(result['cleanup'], 'closed')
        finally:
            worker.join(3)
            server.close()
        self.assertFalse(worker.is_alive())
        self.assertEqual(failures, [])

    def test_ipv4_owned_udp(self):
        self.exchange(socket.AF_INET, '127.0.0.1')

    def test_ipv6_owned_udp(self):
        self.exchange(socket.AF_INET6, '::1')


if __name__ == '__main__':
    unittest.main()
