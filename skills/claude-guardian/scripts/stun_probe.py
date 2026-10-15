"""Opt-in ENV-04 STUN diagnostic. Importing performs no I/O; no CLI.

The host must supply live approval and target-binding callbacks. See
 docs/stun-probe.md for the trusted adapter boundary and evidence limitations.
"""
import ipaddress
import math
import secrets
import socket
import struct
import time
from typing import NamedTuple
import zlib

COOKIE = 0x2112A442
ENDPOINT = 'stun:stun.cloudflare.com:3478'
PATH = 'direct_socket_os_route_tun_unknown'
MAX_PACKET = 4096
MAX_SENDS = 3
MAX_RECEIVES = 64
MAX_POLLS = 256
MAX_SECONDS = 5.0
POLL_SECONDS = 0.05
ERRORS = frozenset({
    'invalid_scope', 'approval_required', 'target_changed', 'cancelled',
    'invalid_budget', 'timeout', 'receive_budget_exhausted',
    'transport_error', 'permission_denied', 'callback_error', 'cleanup_failed',
    'poll_budget_exhausted', 'invalid_clock', 'server_error',
    'malformed_packet', 'wrong_transaction', 'wrong_type', 'missing_mapping',
    'unsupported_attribute', 'invalid_fingerprint', 'unexpected_address_family',
})


class StunError(ValueError):
    """Only fixed codes cross the public API; never exception/packet text."""
    def __init__(self, code):
        super().__init__(code if code in ERRORS else 'transport_error')


class Scope(NamedTuple):
    endpoint: str
    peer_ip: str
    peer_port: int
    family: int
    target_ref: str
    path_kind: str = PATH


def binding_request(transaction_id=None):
    """Return a bare request; production IDs use the OS cryptographic RNG."""
    txid = secrets.token_bytes(12) if transaction_id is None else transaction_id
    if type(txid) is not bytes or len(txid) != 12:
        raise StunError('malformed_packet')
    return struct.pack('!HHI', 0x0001, 0, COOKIE) + txid


def parse_binding_response(packet, transaction_id):
    """Pure strict parser returning (IP, port, IP version), no source claims.

    Unknown mandatory attributes are rejected. Optional attributes are skipped;
    FINGERPRINT, if supplied, is checked but is not authentication. Authentication
    attributes are unsupported, rather than silently treating them as verified.
    """
    if (type(packet) is not bytes or not 20 <= len(packet) <= MAX_PACKET
            or type(transaction_id) is not bytes or len(transaction_id) != 12):
        raise StunError('malformed_packet')
    kind, length, cookie = struct.unpack('!HHI', packet[:8])
    if length % 4 or length != len(packet) - 20 or cookie != COOKIE:
        raise StunError('malformed_packet')
    if packet[8:20] != transaction_id:
        raise StunError('wrong_transaction')
    if kind not in (0x0101, 0x0111):
        raise StunError('wrong_type')
    offset, mapped = 20, None
    unsupported, error_code = False, False
    while offset < len(packet):
        if offset + 4 > len(packet):
            raise StunError('malformed_packet')
        attr, size = struct.unpack('!HH', packet[offset:offset + 4])
        end = offset + 4 + size
        padded_end = end + (-size % 4)
        if padded_end > len(packet):
            raise StunError('malformed_packet')
        value = packet[offset + 4:end]
        if attr == 0x0020:
            if size not in (8, 20) or value[1] not in (1, 2):
                raise StunError('malformed_packet')
            version = 4 if value[1] == 1 else 6
            if size != (8 if version == 4 else 20):
                raise StunError('malformed_packet')
            mask = struct.pack('!I', COOKIE) + transaction_id
            address = bytes(a ^ b for a, b in zip(value[4:], mask))
            mapping = (str(ipaddress.ip_address(address)),
                       struct.unpack('!H', value[2:4])[0] ^ (COOKIE >> 16), version)
            if mapped is None:  # RFC 8489: first occurrence governs
                mapped = mapping
        elif attr == 0x0009 and kind == 0x0111:
            if size < 4 or not 3 <= (value[2] & 7) <= 6 or value[3] > 99:
                raise StunError('malformed_packet')
            try:
                reason = value[4:].decode('utf-8')
            except UnicodeDecodeError:
                raise StunError('malformed_packet') from None
            if len(reason) >= 128:
                raise StunError('malformed_packet')
            error_code = True
        elif attr == 0x8028:
            if size != 4 or padded_end != len(packet):
                raise StunError('invalid_fingerprint')
            if struct.unpack('!I', value)[0] != (zlib.crc32(packet[:offset]) ^ 0x5354554e):
                raise StunError('invalid_fingerprint')
        elif attr < 0x8000:
            unsupported = True
        offset = padded_end
    # Only after the complete envelope/TLVs/fingerprint are validated may a
    # correlated response end the transaction. Never let an early mandatory
    # attribute hide a corrupt tail that should instead be discarded.
    if kind == 0x0111:
        if not error_code:
            raise StunError('malformed_packet')
        raise StunError('server_error')
    if unsupported:
        raise StunError('unsupported_attribute')
    if mapped is None:
        raise StunError('missing_mapping')
    return mapped


def _validate_scope(scope):
    if type(scope) is not Scope:
        raise StunError('invalid_scope')
    try:
        ip = ipaddress.ip_address(scope.peer_ip)
    except (ValueError, TypeError):
        raise StunError('invalid_scope') from None
    if (type(scope.peer_ip) is not str or '%' in scope.peer_ip
            or scope.peer_ip != str(ip)
            or type(scope.peer_port) is not int or not 1 <= scope.peer_port <= 65535
            or type(scope.family) is not int or scope.family != ip.version
            or type(scope.target_ref) is not str or not 1 <= len(scope.target_ref) <= 128
            or any(ord(c) < 32 for c in scope.target_ref) or not scope.target_ref.strip()
            or scope.path_kind != PATH):
        raise StunError('invalid_scope')
    # No arbitrary destinations: production is the selected fixed service;
    # the only other endpoint is an explicitly labelled owned loopback fixture.
    if scope.endpoint == ENDPOINT:
        if scope.peer_port != 3478 or not ip.is_global:
            raise StunError('invalid_scope')
    elif scope.endpoint != 'owned-loopback-fixture' or not ip.is_loopback:
        raise StunError('invalid_scope')


def probe_stun(scope, *, approve, current_target, cancelled, total_seconds=3.5,
               socket_factory=socket.socket, monotonic=time.monotonic):
    """One bounded transaction. Never resolves DNS, follows redirects or retries hosts.

    approve(scope) must return that exact Scope from fresh host authorization,
    including the host-verified DNS binding to peer_ip; a boolean is insufficient.
    current_target() returns the live target alias. cancelled() returns a bool.
    All callbacks and the socket factory are trusted, bounded host code.
    """
    _validate_scope(scope)
    if (type(total_seconds) not in (int, float) or not 0 < total_seconds <= MAX_SECONDS
            or not math.isfinite(total_seconds)):
        raise StunError('invalid_budget')
    if not all(callable(f) for f in (approve, current_target, cancelled, socket_factory, monotonic)):
        raise StunError('approval_required')
    result = dict(status='unknown', error=None, sends=0, received=0, rejected=0, polls=0,
                  observed_ip=None, observed_port=None, observed_address_family=None,
                  path_kind=PATH, path_association='unknown', browser_path='not_observed',
                  target_path='not_observed', endpoint=scope.endpoint,
                  target_ref=scope.target_ref, sample_type='independent_stun',
                  authenticated=False, cleanup='not_opened')
    sock = None
    last_clock = None
    def clock():
        nonlocal last_clock
        try:
            value = monotonic()
            if (type(value) not in (int, float) or not math.isfinite(value)
                    or (last_clock is not None and value < last_clock)):
                raise StunError('invalid_clock')
        except Exception:
            raise StunError('invalid_clock') from None
        last_clock = value
        return value

    def check():
        try:
            stop = cancelled()
            if type(stop) is not bool:
                raise StunError('callback_error')
            if stop:
                raise StunError('cancelled')
            if current_target() != scope.target_ref:
                raise StunError('target_changed')
            approval = approve(scope)
            if type(approval) is not Scope or approval != scope:
                raise StunError('approval_required')
            # Approval callbacks may themselves revoke/cancel or consume time.
            if cancelled() is not False:
                raise StunError('cancelled')
            if current_target() != scope.target_ref:
                raise StunError('target_changed')
            if clock() >= deadline:
                raise StunError('timeout')
        except StunError:
            raise
        except Exception:
            raise StunError('callback_error') from None
    try:
        deadline = clock() + total_seconds
        check()
        request = binding_request()
        sock = socket_factory(socket.AF_INET if scope.family == 4 else socket.AF_INET6,
                              socket.SOCK_DGRAM)
        peer = (scope.peer_ip, scope.peer_port) if scope.family == 4 else (scope.peer_ip, scope.peer_port, 0, 0)
        next_send = clock()
        while True:
            check()
            now = clock()
            if result['sends'] < MAX_SENDS and now >= next_send:
                sock.settimeout(min(POLL_SECONDS, deadline - now))
                check()
                # Count attempts before sending: a failing call still consumes budget.
                result['sends'] += 1
                if sock.sendto(request, peer) != len(request):
                    raise StunError('transport_error')
                next_send = clock() + 0.5 * (2 ** (result['sends'] - 1))
            check()
            wait = min(POLL_SECONDS, deadline - clock())
            if result['sends'] < MAX_SENDS:
                wait = min(wait, max(0.001, next_send - clock()))
            if wait <= 0:
                raise StunError('timeout')
            if result['polls'] >= MAX_POLLS:
                raise StunError('poll_budget_exhausted')
            result['polls'] += 1
            sock.settimeout(wait)
            try:
                packet, source = sock.recvfrom(MAX_PACKET + 1)
            except (TimeoutError, BlockingIOError):
                continue
            check()
            result['received'] += 1
            try:
                source_matches = (len(source) == len(peer)
                                  and ipaddress.ip_address(source[0]) == ipaddress.ip_address(peer[0])
                                  and source[1:] == peer[1:])
            except (ValueError, TypeError, IndexError):
                source_matches = False
            if source_matches:
                try:
                    mapped = parse_binding_response(packet, request[8:20])
                    if mapped[2] != scope.family:
                        raise StunError('unexpected_address_family')
                except StunError as exc:
                    if str(exc) in ('unsupported_attribute', 'server_error'):
                        raise
                    result['rejected'] += 1
                else:
                    check()
                    result.update(status='observed', observed_ip=mapped[0],
                                  observed_port=mapped[1], observed_address_family=mapped[2])
                    break
            else:
                result['rejected'] += 1
            if result['received'] >= MAX_RECEIVES:
                raise StunError('receive_budget_exhausted')
    except StunError as exc:
        result['error'] = str(exc) if str(exc) in ERRORS else 'transport_error'
    except PermissionError:
        result['error'] = 'permission_denied'
    except Exception:
        result['error'] = 'transport_error'
    finally:
        if sock is not None:
            try:
                sock.close()
                result['cleanup'] = 'closed'
            except Exception:
                result.update(status='unknown', error='cleanup_failed', cleanup='failed',
                              observed_ip=None, observed_port=None, observed_address_family=None)
    # Cleanup is a host boundary too: it may consume time or change live state.
    # Never let a valid packet certify a result that became stale during close.
    if result['status'] == 'observed':
        try:
            check()
        except StunError as exc:
            result.update(status='unknown', error=str(exc), observed_ip=None,
                          observed_port=None, observed_address_family=None)
    return result
