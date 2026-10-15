"""Bounded, pure DNS A/AAAA codec. No transport, resolver, CLI, or I/O on import.

This is protocol groundwork, not system/Mihomo DNS or DNS leak detection.
"""
import ipaddress
import re
import secrets
import struct
from typing import NamedTuple

MAX_PACKET = 4096
MAX_RECORDS = 128
# Each step visits a distinct packet offset; this also allows a maximally
# long expanded name reached through valid backward compression pointers.
MAX_NAME_STEPS = MAX_PACKET
ERRORS = frozenset({'invalid_query', 'malformed_packet', 'wrong_transaction',
                    'wrong_question', 'wrong_type', 'unsupported_response',
                    'record_budget_exhausted', 'ambiguous_answer'})


class DnsError(ValueError):
    """Fixed public errors never include names, packets, or exception text."""
    def __init__(self, code):
        super().__init__(code if code in ERRORS else 'malformed_packet')


class Query(NamedTuple):
    name: str
    query_type: str
    transaction_id: int


class Observation(NamedTuple):
    status: str
    rcode: int
    addresses: tuple
    address_family: int
    alias_present: bool
    cache_possible: bool = True
    path_association: str = 'unknown'
    leak_assessment: str = 'unknown'
    authenticated: bool = False


def _question(query):
    if (type(query) is not Query or type(query.name) is not str
            or type(query.query_type) is not str or query.query_type not in ('A', 'AAAA')
            or type(query.transaction_id) is not int
            or not 0 <= query.transaction_id <= 65535):
        raise DnsError('invalid_query')
    name = query.name[:-1] if query.name.endswith('.') else query.name
    if not name or len(name) > 253:
        raise DnsError('invalid_query')
    labels = name.split('.')
    if any(not re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9-]{0,61}[A-Za-z0-9])?', label)
           for label in labels):
        raise DnsError('invalid_query')
    return tuple(label.encode('ascii').lower() for label in labels), 1 if query.query_type == 'A' else 28


def make_query(name, query_type, transaction_id=None):
    """Return (Query, packet); producing bytes does not authorize their transmission.

    Names are explicit ASCII hostnames (preconverted IDNA if needed), not URLs,
    search suffixes, wildcard labels, or implicit/default service names.
    """
    query = Query(name, query_type, secrets.randbits(16) if transaction_id is None else transaction_id)
    labels, kind = _question(query)
    wire = b''.join(bytes([len(label)]) + label for label in labels) + b'\0'
    return query, struct.pack('!HHHHHH', query.transaction_id, 0x0100, 1, 0, 0, 0) + wire + struct.pack('!HH', kind, 1)


class _Reader:
    def __init__(self, packet):
        self.packet = packet
        # Pointers must reference a label boundary from an earlier parsed name.
        # This conservative subset rejects pointers into headers/opaque RDATA.
        self.boundaries = set()

    def name(self, offset):
        packet, labels, seen = self.packet, [], set()
        end, length = None, 1
        for _ in range(MAX_NAME_STEPS):
            if offset >= len(packet) or offset in seen:
                raise DnsError('malformed_packet')
            seen.add(offset)
            size = packet[offset]
            if size & 0xc0 == 0xc0:
                if offset + 1 >= len(packet):
                    raise DnsError('malformed_packet')
                pointer = ((size & 0x3f) << 8) | packet[offset + 1]
                if pointer >= offset or pointer not in self.boundaries:
                    raise DnsError('malformed_packet')
                self.boundaries.add(offset)
                if end is None:
                    end = offset + 2
                offset = pointer
            elif size & 0xc0:
                raise DnsError('malformed_packet')
            else:
                self.boundaries.add(offset)
                offset += 1
                if size == 0:
                    return tuple(labels), offset if end is None else end
                if offset + size > len(packet):
                    raise DnsError('malformed_packet')
                length += size + 1
                if length > 255:
                    raise DnsError('malformed_packet')
                labels.append(packet[offset:offset + size].lower())
                offset += size
        raise DnsError('malformed_packet')


def parse_response(packet, query):
    """Validate a complete bounded DNS message against an exact outstanding query.

    Source IP/port and transport association MUST be verified separately by a
    future authorized host adapter (RFC 5452). Even a matching packet is not
    authenticated, and addresses are untrusted data, never follow-up targets.
    No recursive resolution, CNAME follow-up, fallback, cache, or DNSSEC validation.
    """
    expected, kind = _question(query)
    if type(packet) is not bytes or not 12 <= len(packet) <= MAX_PACKET:
        raise DnsError('malformed_packet')
    txid, flags, qd, an, ns, ar = struct.unpack('!HHHHHH', packet[:12])
    if txid != query.transaction_id:
        raise DnsError('wrong_transaction')
    if not flags & 0x8000 or flags & 0x7800:
        raise DnsError('wrong_type')
    # Z is reserved; AD/CD are accepted but never treated as authentication.
    if flags & 0x0040 or (flags & 15) > 5:
        raise DnsError('unsupported_response')
    if qd != 1:
        raise DnsError('wrong_question')
    if an + ns + ar > MAX_RECORDS:
        raise DnsError('record_budget_exhausted')
    reader = _Reader(packet)
    name, offset = reader.name(12)
    if offset + 4 > len(packet):
        raise DnsError('malformed_packet')
    qtype, qclass = struct.unpack('!HH', packet[offset:offset + 4])
    offset += 4
    if name != expected or qtype != kind or qclass != 1:
        raise DnsError('wrong_question')
    # TC may contain a physically incomplete RR: never consume any answer from
    # it. A transport adapter must report unknown, not silently switch to TCP.
    if flags & 0x0200:
        return Observation('truncated', flags & 15, (), 4 if kind == 1 else 6, False)
    records, aliases, address_owners = {}, {}, set()
    for index in range(an + ns + ar):
        owner, offset = reader.name(offset)
        if offset + 10 > len(packet):
            raise DnsError('malformed_packet')
        rtype, rclass, ttl, size = struct.unpack('!HHIH', packet[offset:offset + 10])
        offset += 10
        end = offset + size
        if end > len(packet):
            raise DnsError('malformed_packet')
        value = None
        if rtype in (1, 28):
            if size != (4 if rtype == 1 else 16):
                raise DnsError('malformed_packet')
            value = str(ipaddress.ip_address(packet[offset:end]))
        elif rtype in (2, 5, 12):
            value, name_end = reader.name(offset)
            if name_end != end:
                raise DnsError('malformed_packet')
        elif rtype == 41:  # No EDNS was requested; extended RCODE is unsupported.
            raise DnsError('unsupported_response')
        if index < an and rclass == 1:
            if rtype in (1, 28):
                address_owners.add(owner)
            if rtype == kind:
                records.setdefault(owner, set()).add(value)
            elif rtype == 5:
                if owner in aliases and aliases[owner] != value:
                    raise DnsError('ambiguous_answer')
                aliases[owner] = value
        offset = end
    if offset != len(packet):
        raise DnsError('malformed_packet')
    if address_owners.intersection(aliases):
        raise DnsError('ambiguous_answer')
    # Never expose addresses from a negative/error response, even if it contains
    # superficially plausible answers. RCODE alone is not proof of nonexistence.
    if flags & 15:
        return Observation('negative_response' if flags & 15 == 3 else 'server_error',
                           flags & 15, (), 4 if kind == 1 else 6, bool(aliases))
    current, seen = expected, set()
    while current in aliases:
        if current in seen or current in records:
            raise DnsError('ambiguous_answer')
        seen.add(current)
        current = aliases[current]
    addresses = tuple(sorted(records.get(current, ())))
    return Observation('address_answer' if addresses else 'no_matching_address',
                       0, addresses, 4 if kind == 1 else 6, bool(seen))
