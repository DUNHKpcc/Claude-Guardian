"""Offline STUN codec vectors."""
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


if __name__ == '__main__':
    unittest.main()
