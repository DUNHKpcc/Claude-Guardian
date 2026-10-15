"""Synthetic DNS bytes only: no public or operating-system DNS queries."""
import importlib.util
import ipaddress
import random
import socket
from pathlib import Path
import struct
import unittest
from unittest.mock import patch

FILE = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/dns_probe.py'
spec = importlib.util.spec_from_file_location('dns_probe', FILE)
d = importlib.util.module_from_spec(spec)
spec.loader.exec_module(d)


def name(value):
    return b''.join(bytes([len(x)]) + x.encode() for x in value.split('.')) + b'\0'


def rr(value=b'\xc0\x00\x02\x01', kind=1, owner=b'\xc0\x0c', cls=1):
    return owner + struct.pack('!HHIH', kind, cls, 60, len(value)) + value


def response(query, answers=(), authority=(), additional=(), flags=0x8180):
    _, request = d.make_query(*query)
    return (struct.pack('!HHHHHH', query.transaction_id, flags, 1, len(answers),
                        len(authority), len(additional)) + request[12:]
            + b''.join(answers + authority + additional))


class DnsCodecTests(unittest.TestCase):
    def setUp(self):
        self.query, self.request = d.make_query('example.test', 'A', 0x1234)

    def parse(self, packet):
        return d.parse_response(packet, self.query)

    def assertError(self, packet, code='malformed_packet'):
        with self.assertRaises(d.DnsError) as caught:
            self.parse(packet)
        self.assertEqual(str(caught.exception), code)

    def test_known_query_wire(self):
        self.assertEqual(self.request.hex(), '123401000001000000000000076578616d706c6504746573740000010001')

    def test_random_ids_and_explicit_zero(self):
        with patch.object(d.secrets, 'randbits', return_value=47) as random:
            query, _ = d.make_query('example.test', 'AAAA')
            self.assertEqual(query.transaction_id, 47)
            random.assert_called_once_with(16)
        self.assertEqual(d.make_query('example.test', 'A', 0)[0].transaction_id, 0)

    def test_invalid_query_fixed_error(self):
        for value in ('', '.', 'a..test', 'a.test..', 'https://example.test', '-a.test',
                      'a_.test', 'é.test', 'a' * 64 + '.test', 'a\n.test', '*.test'):
            with self.subTest(value=value), self.assertRaisesRegex(d.DnsError, '^invalid_query$'):
                d.make_query(value, 'A')
        for value in (True, -1, 65536, '1'):
            with self.assertRaises(d.DnsError):
                d.make_query('example.test', 'A', value)
        with self.assertRaises(d.DnsError):
            d.make_query('example.test', 'MX')

    def test_name_maximum(self):
        maximum = '.'.join(['a' * 63] * 3 + ['b' * 61])
        d.make_query(maximum, 'A')
        with self.assertRaises(d.DnsError):
            d.make_query(maximum + 'c', 'A')

    def test_maximum_label_count_with_compressed_owner(self):
        query, _ = d.make_query('.'.join(['a'] * 127), 'A', 0x1234)
        result = d.parse_response(response(query, (rr(),)), query)
        self.assertEqual(result.addresses, ('192.0.2.1',))

    def test_alias_conflicts_with_either_address_family(self):
        for query_type, answer_kind, conflict_kind in (('A', 1, 28), ('AAAA', 28, 1)):
            query, _ = d.make_query('example.test', query_type, 0x1234)
            alias = rr(name('alias.test'), 5)
            conflict = rr(b'\0' * (4 if conflict_kind == 1 else 16), conflict_kind)
            answer = rr(b'\0' * (4 if answer_kind == 1 else 16), answer_kind, name('alias.test'))
            for answers in ((alias, conflict, answer), (conflict, alias, answer)):
                with self.subTest(query_type=query_type), self.assertRaisesRegex(d.DnsError, '^ambiguous_answer$'):
                    d.parse_response(response(query, answers), query)

    def test_case_and_root_dot(self):
        query, request = d.make_query('EXAMPLE.Test.', 'A', 0x1234)
        self.assertEqual(request, self.request)
        self.assertEqual(d.parse_response(response(self.query, (rr(),)), query).status, 'address_answer')

    def test_a_and_evidence_limits(self):
        result = self.parse(response(self.query, (rr(),)))
        self.assertEqual(result.addresses, ('192.0.2.1',))
        self.assertEqual(result.address_family, 4)
        self.assertEqual(result.path_association, 'unknown')
        self.assertEqual(result.leak_assessment, 'unknown')
        self.assertTrue(result.cache_possible)
        self.assertFalse(result.authenticated)
        self.assertNotIn('example', repr(result))

    def test_aaaa(self):
        query, _ = d.make_query('example.test', 'AAAA', 2)
        packet = response(query, (rr(ipaddress.ip_address('2001:db8::1').packed, 28),))
        result = d.parse_response(packet, query)
        self.assertEqual(result.addresses, ('2001:db8::1',))
        self.assertEqual(result.address_family, 6)

    def test_other_address_type_is_not_answer(self):
        packet = response(self.query, (rr(b'\0' * 16, 28),))
        self.assertEqual(self.parse(packet).status, 'no_matching_address')

    def test_id_question_and_type_binding(self):
        for query in (d.Query('other.test', 'A', 0x1234),
                      d.Query('example.test', 'AAAA', 0x1234)):
            self.assertError(response(query), 'wrong_question')
        self.assertError(response(self.query._replace(transaction_id=1)), 'wrong_transaction')
        for flags in (0x0100, 0x8980):
            self.assertError(response(self.query, flags=flags), 'wrong_type')
        p = bytearray(response(self.query))
        p[-1] = 3
        self.assertError(bytes(p), 'wrong_question')

    def test_bad_question_count(self):
        p = bytearray(response(self.query)); p[5] = 2
        self.assertError(bytes(p), 'wrong_question')

    def test_truncated_never_exposes_addresses(self):
        packet = response(self.query, (rr(),), flags=0x8380)
        for p in (packet, packet[:-2]):
            result = self.parse(p)
            self.assertEqual(result.status, 'truncated')
            self.assertEqual(result.addresses, ())

    def test_short_and_oversize_packets(self):
        for p in (b'', b'\0' * 11, b'\0' * (d.MAX_PACKET + 1), bytearray(self.request)):
            self.assertError(p)

    def test_partial_rr_and_trailing_bytes(self):
        p = response(self.query, (rr(),))
        for cut in range(len(self.request), len(p)):
            self.assertError(p[:cut])
        self.assertError(p + b'\0')

    def test_address_lengths(self):
        for kind, size in ((1, 3), (1, 5), (28, 15), (28, 17)):
            self.assertError(response(self.query, (rr(b'\0' * size, kind),)))

    def test_pointer_invalid_boundaries_forward_self_and_header(self):
        start = len(self.request)
        for pointer in (0, 13, start, start + 2, 4095):
            self.assertError(response(self.query, (rr(owner=struct.pack('!H', 0xc000 | pointer)),)))
        self.assertError(response(self.query, (rr(owner=b'\x40'),)))

    def test_cycle_through_label(self):
        start = len(self.request)
        self.assertError(response(self.query, (rr(owner=b'\x01a' + struct.pack('!H', 0xc000 | start)),)))

    def test_expanded_name_limit(self):
        owner = b''.join(b'\x3f' + b'a' * 63 for _ in range(4)) + b'\0'
        self.assertError(response(self.query, (rr(owner=owner),)))

    def test_alias_chain_is_local_only(self):
        alias = rr(name('alias.test'), 5)
        address = rr(owner=name('alias.test'))
        result = self.parse(response(self.query, (alias, address)))
        self.assertEqual(result.addresses, ('192.0.2.1',))
        self.assertTrue(result.alias_present)
        result = self.parse(response(self.query, (alias,)))
        self.assertEqual(result.status, 'no_matching_address')
        self.assertEqual(result.addresses, ())

    def test_alias_loop_and_conflict(self):
        for answers in ((rr(b'\xc0\x0c', 5),),
                        (rr(name('alias.test'), 5), rr()),
                        (rr(name('alias.test'), 5), rr(name('other.test'), 5))):
            self.assertError(response(self.query, answers), 'ambiguous_answer')

    def test_alias_rdata_trailing_and_overflow(self):
        for value in (name('alias.test') + b'\0', b'\x3fabc', b''):
            self.assertError(response(self.query, (rr(value, 5),)))

    def test_unrelated_additional_authority_class_ignored(self):
        for kwargs in ({'answers': (rr(owner=name('other.test')), )},
                       {'additional': (rr(),)}, {'authority': (rr(),)},
                       {'answers': (rr(cls=3),)}):
            self.assertEqual(self.parse(response(self.query, **kwargs)).addresses, ())

    def test_negative_and_server_error_no_answers(self):
        for rcode in range(1, 6):
            result = self.parse(response(self.query, (rr(),), flags=0x8180 | rcode))
            self.assertEqual(result.rcode, rcode)
            self.assertEqual(result.addresses, ())
            self.assertEqual(result.status, 'negative_response' if rcode == 3 else 'server_error')

    def test_reserved_flags_and_edns(self):
        for flags in (0x81c0, 0x8186):
            self.assertError(response(self.query, flags=flags), 'unsupported_response')
        self.assertError(response(self.query, additional=(rr(b'', 41, b'\0'),)), 'unsupported_response')
        self.assertFalse(self.parse(response(self.query, (rr(),), flags=0x81b0)).authenticated)

    def test_record_budget(self):
        p = bytearray(response(self.query)); p[7] = 129
        self.assertError(bytes(p), 'record_budget_exhausted')

    def test_deduplicated_answers(self):
        self.assertEqual(self.parse(response(self.query, (rr(), rr()))).addresses, ('192.0.2.1',))

    def test_valid_suffix_and_rdata_compression(self):
        alias_offset = len(self.request) + 12
        alias = rr(b'\x05alias\xc0\x14', 5)
        address = rr(owner=struct.pack('!H', 0xc000 | alias_offset))
        result = self.parse(response(self.query, (alias, address)))
        self.assertEqual(result.addresses, ('192.0.2.1',))

    def test_pure_codec_never_resolves_or_opens_socket(self):
        with patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             patch.object(socket, 'getaddrinfo', side_effect=AssertionError('resolver')):
            self.assertEqual(self.parse(response(self.query, (rr(),))).status, 'address_answer')

    def test_seeded_mutations_only_return_observation_or_fixed_error(self):
        rng = random.Random(7)
        base = response(self.query, (rr(name('alias.test'), 5), rr(owner=name('alias.test'))))
        for _ in range(1000):
            packet = bytearray(base)
            for _ in range(rng.randrange(1, 5)):
                packet[rng.randrange(len(packet))] = rng.randrange(256)
            try:
                result = self.parse(bytes(packet))
            except d.DnsError as exc:
                self.assertIn(str(exc), d.ERRORS)
            else:
                self.assertIsInstance(result, d.Observation)
                self.assertEqual(result.leak_assessment, 'unknown')

    def test_errors_do_not_echo_data(self):
        self.assertEqual(str(d.DnsError('secret sentinel')), 'malformed_packet')


if __name__ == '__main__':
    unittest.main()
