"""Bounded credential-free controller audit; ENV v0.3 §19.8–19.10.

Host integration must establish the target device/user/network namespace, product
metadata, selected data root, PID + process start identity and listener ownership.
verify_binding must recheck that live evidence after approval and after each request.
approve_read must consult live audit approval for the exact binding/path/budget;
a model-supplied boolean or this module's input validation is NOT authorization or
independent ownership verification. Callbacks and injected transports are trusted
host code, not user-provided code. This module does not supply native adapters.

Only numeric loopback TCP in the executing namespace is supported. No discovery,
DNS, inherited proxies, credentials, cookies, redirects, retries, process starts,
configuration writes, or subscription refresh. Authentication requires handoff.
The deadline is cooperative around trusted callbacks/injected transports: the
host must bound their blocking work. Native socket connect/send use remaining
socket deadlines (cancellation is checked between those operations); response
reads poll cancellation every 50ms. This is not a hard realtime guarantee.
Reports describe visible controller snapshots, not browser/OS routing coverage.
Separate endpoint responses are non-atomic; no stable config revision or unchanged
snapshot is inferred. Revision aliases are random per call, never raw digests.
"""
import http.client
import io
import json
import re
import select
import socket
import time
import uuid
from dataclasses import dataclass
from datetime import datetime, timezone

PATHS = ('/version', '/configs', '/rules', '/proxies')
PUBLIC_ERROR_CODES = frozenset({
    'CANCELLED', 'TIMEOUT', 'BUDGET_EXCEEDED', 'INPUT_OR_RESPONSE_INVALID',
    'CONTROLLER_NOT_BOUND', 'AUTHORIZATION_MISSING',
    'AUTHENTICATION_HANDOFF_REQUIRED', 'CONTROLLER_RESPONSE_REJECTED',
    'PERMISSION_DENIED',
})
MAX_BYTES = 1024 * 1024
MAX_SECONDS = 15.0
MAX_DEPTH = 32
MAX_NODES = 20000
MODES = {'rule', 'global', 'direct'}
PROXY_TYPES = {'Direct', 'Reject', 'Selector', 'URLTest', 'Fallback', 'LoadBalance',
               'Relay', 'Shadowsocks', 'ShadowsocksR', 'VMess', 'VLESS', 'Trojan',
               'Socks5', 'Http', 'WireGuard', 'Hysteria', 'Hysteria2', 'Tuic'}
RULE_TYPES = {'Domain', 'DomainSuffix', 'DomainKeyword', 'GeoIP', 'IPCIDR',
              'IPCIDR6', 'SrcIPCIDR', 'DstPort', 'SrcPort', 'ProcessName',
              'ProcessPath', 'RuleSet', 'Match', 'Network', 'InName'}


class ControllerError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True)
class ControllerBinding:
    """Host-issued private binding; never copied into the public report."""
    target_ref: str
    namespace_ref: str
    desktop_user_ref: str
    instance_ref: str
    process_id: int
    process_start_ref: str
    host: str
    port: int


@dataclass(frozen=True)
class Budget:
    max_bytes: int = 262144  # per response, including bounded headers
    max_seconds: float = 5.0  # entire audit, not each request
    max_requests: int = 4
    max_depth: int = 24
    max_nodes: int = 10000


def _fail(code):
    raise ControllerError(code)


def _guard(deadline, cancelled):
    if cancelled():
        _fail('CANCELLED')
    if time.monotonic() >= deadline:
        _fail('TIMEOUT')


class _BoundedReader(io.RawIOBase):
    def __init__(self, sock, limit, deadline, cancelled):
        self.sock, self.remaining = sock, limit
        self.deadline, self.cancelled = deadline, cancelled

    def readable(self):
        return True

    def readinto(self, buffer):
        while True:
            _guard(self.deadline, self.cancelled)
            ready, _, _ = select.select([self.sock], [], [],
                                        max(0, min(.05, self.deadline - time.monotonic())))
            if ready:
                data = self.sock.recv(min(len(buffer), self.remaining + 1))
                self.remaining -= len(data)
                if self.remaining < 0:
                    _fail('BUDGET_EXCEEDED')
                buffer[:len(data)] = data
                return len(data)


class _ResponseSocket:
    def __init__(self, reader):
        self.reader = reader

    def makefile(self, mode):
        return io.BufferedReader(self.reader, buffer_size=4096)


def loopback_transport(binding, path, budget, deadline, cancelled):
    """Trusted transport boundary: one GET, no alternate destination or retry.

    Direct socket construction avoids even getaddrinfo for numeric literals.
    Status errors are returned without reading or exposing the response body.
    """
    _validate(binding, (path,), budget)
    _guard(deadline, cancelled)
    family = socket.AF_INET6 if binding.host == '::1' else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(max(.001, deadline - time.monotonic()))
        sock.connect((binding.host, binding.port))
        _guard(deadline, cancelled)
        host = '[::1]' if family == socket.AF_INET6 else '127.0.0.1'
        request = (f'GET {path} HTTP/1.1\r\nHost: {host}:{binding.port}\r\n'
                   'Accept: application/json\r\nConnection: close\r\n\r\n')
        _guard(deadline, cancelled)
        sock.settimeout(max(.001, deadline - time.monotonic()))
        sock.sendall(request.encode('ascii'))
        reader = _BoundedReader(sock, budget.max_bytes, deadline, cancelled)
        response = http.client.HTTPResponse(_ResponseSocket(reader))
        try:
            response.begin()
            if response.status != 200:
                return response.status, b''
            # HTTPResponse deliberately tolerates malformed framing. Inventory
            # evidence must not: reject duplicate/conflicting lengths and TE+CL.
            lengths = response.headers.get_all('Content-Length', [])
            transfers = response.headers.get_all('Transfer-Encoding', [])
            encodings = response.headers.get_all('Content-Encoding', [])
            if (len(lengths) > 1 or len(transfers) > 1 or len(encodings) > 1
                    or (lengths and transfers)):
                _fail('INPUT_OR_RESPONSE_INVALID')
            if lengths and not re.fullmatch(r'[0-9]{1,20}', lengths[0].strip()):
                _fail('INPUT_OR_RESPONSE_INVALID')
            if lengths and int(lengths[0].strip()) > budget.max_bytes:
                _fail('BUDGET_EXCEEDED')
            if transfers and transfers[0].strip().lower() != 'chunked':
                _fail('INPUT_OR_RESPONSE_INVALID')
            if encodings and encodings[0].strip().lower() != 'identity':
                _fail('INPUT_OR_RESPONSE_INVALID')
            raw = response.read(budget.max_bytes + 1)
            if response.length not in (None, 0):
                _fail('INPUT_OR_RESPONSE_INVALID')
            if len(raw) > budget.max_bytes:
                _fail('BUDGET_EXCEEDED')
            return response.status, raw
        finally:
            response.close()


def _validate(binding, paths, budget):
    if type(binding) is not ControllerBinding or type(budget) is not Budget:
        _fail('INPUT_OR_RESPONSE_INVALID')
    if binding.host not in ('127.0.0.1', '::1'):
        _fail('CONTROLLER_NOT_BOUND')
    if type(binding.port) is not int or not 1 <= binding.port <= 65535:
        _fail('CONTROLLER_NOT_BOUND')
    if type(binding.process_id) is not int or binding.process_id <= 0:
        _fail('CONTROLLER_NOT_BOUND')
    for value in (binding.target_ref, binding.namespace_ref, binding.desktop_user_ref,
                  binding.instance_ref, binding.process_start_ref):
        if not isinstance(value, str) or not 1 <= len(value) <= 128:
            _fail('CONTROLLER_NOT_BOUND')
    for value, upper in ((budget.max_bytes, MAX_BYTES), (budget.max_requests, 4),
                         (budget.max_depth, MAX_DEPTH), (budget.max_nodes, MAX_NODES)):
        if type(value) is not int or not 1 <= value <= upper:
            _fail('INPUT_OR_RESPONSE_INVALID')
    if type(budget.max_seconds) not in (int, float) or not 0 < budget.max_seconds <= MAX_SECONDS:
        _fail('INPUT_OR_RESPONSE_INVALID')
    if (not isinstance(paths, (tuple, list)) or not paths or
            len(paths) > budget.max_requests or any(type(p) is not str or p not in PATHS for p in paths)
            or len(set(paths)) != len(paths)):
        _fail('INPUT_OR_RESPONSE_INVALID')


def _parse(raw, budget):
    if type(raw) is not bytes or len(raw) > budget.max_bytes:
        _fail('BUDGET_EXCEEDED')
    # Preflight nesting before recursive JSON decoder, ignoring quoted braces.
    depth, quoted, escaped = 0, False, False
    for char in raw:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            if depth > budget.max_depth:
                _fail('BUDGET_EXCEEDED')
        elif char in (93, 125):
            depth -= 1
    def pairs(items):
        obj = {}
        for key, value in items:
            if key in obj:
                _fail('INPUT_OR_RESPONSE_INVALID')
            obj[key] = value
        return obj
    def constant(_):
        _fail('INPUT_OR_RESPONSE_INVALID')
    obj = json.loads(raw.decode('utf-8'), object_pairs_hook=pairs, parse_constant=constant)
    if type(obj) is not dict:
        _fail('INPUT_OR_RESPONSE_INVALID')
    stack, count = [obj], 0
    while stack:
        value = stack.pop()
        count += 1
        if count > budget.max_nodes:
            _fail('BUDGET_EXCEEDED')
        if type(value) is dict:
            stack.extend(value.values())
        elif type(value) is list:
            stack.extend(value)
    return obj


def _project(path, obj):
    if path == '/version':
        result = {}
        if type(obj.get('meta')) is bool:
            result['meta'] = obj['meta']
        version = obj.get('version')
        if isinstance(version, str) and re.fullmatch(r'v?\d{1,4}\.\d{1,4}\.\d{1,4}', version):
            result['version'] = version
        return result
    if path == '/configs':
        result = {}
        mode = obj.get('mode')
        if type(mode) is str and mode in MODES:
            result['mode'] = mode
        for key in ('ipv6', 'allow-lan'):
            if type(obj.get(key)) is bool:
                result[key] = obj[key]
        tun = obj.get('tun')
        if type(tun) is dict and type(tun.get('enable')) is bool:
            result['tun_enabled_declared_by_controller'] = tun['enable']
        return result
    if path == '/rules':
        rules = obj.get('rules')
        if type(rules) is not list or any(type(rule) is not dict for rule in rules):
            _fail('INPUT_OR_RESPONSE_INVALID')
        counts = {}
        for rule in rules:
            kind = rule.get('type')
            kind = kind if type(kind) is str and kind in RULE_TYPES else 'unknown'
            counts[kind] = counts.get(kind, 0) + 1
        return {'rule_count': len(rules), 'type_counts': counts,
                'matching_or_hit_evidence': 'not_evaluated'}
    proxies = obj.get('proxies')
    if type(proxies) is not dict or any(type(p) is not dict for p in proxies.values()):
        _fail('INPUT_OR_RESPONSE_INVALID')
    groups = []
    for proxy in proxies.values():
        members = proxy.get('all')
        if members is None:
            continue
        if type(members) is not list or any(type(m) is not str for m in members):
            _fail('INPUT_OR_RESPONSE_INVALID')
        kind = proxy.get('type')
        kind = kind if type(kind) is str and kind in PROXY_TYPES else 'unknown'
        # Inspect only explicit controller types. A name containing DIRECT is not evidence.
        def member_type(name):
            item = proxies.get(name) if type(name) is str else None
            return item.get('type') if type(item) is dict else None
        selected = member_type(proxy.get('now'))
        selected = ('not_applicable' if kind == 'LoadBalance' else
                    'direct' if selected == 'Direct' else
                    'reject' if selected == 'Reject' else
                    'proxy' if type(selected) is str and selected in PROXY_TYPES - {'Selector', 'URLTest', 'Fallback', 'LoadBalance', 'Relay'} else 'unknown')
        groups.append({'group_ref': f'group-{len(groups) + 1}', 'type': kind,
                       'member_count': len(members),
                       'has_direct_candidate': any(member_type(m) == 'Direct' for m in members),
                       'selected_kind': selected, 'fallback_behavior': 'not_verified'})
    return {'proxy_count': len(proxies), 'groups': groups,
            'actual_traffic_or_direct_leak': 'not_evaluated'}


def audit_controller(binding, paths, *, verify_binding, approve_read,
                     cancelled=lambda: False, budget=Budget(), transport=loopback_transport):
    """Return a secret-safe component result, not an env-inventory readiness report.

    verify_binding(binding) and approve_read(binding, path, budget) must return
    exactly True from trusted live host checks. No callback exception text escapes.
    Missing/denied/revoked approval stops all remaining reads. Cancellation clears
    partial facts. A changed binding clears partial facts too. No export occurs.
    Trusted callbacks must return promptly or provide their own host-side timeout;
    the audit checks elapsed time on return and cannot preempt arbitrary Python.
    """
    result = {'schema_version': 'guardian-controller-inventory/0.1', 'operation': 'audit',
              'contact_phase': 'precontact', 'gate_state': 'closed', 'changes': [],
              'facts': [], 'execution_status': 'blocked', 'error_code': None,
              'snapshot': 'non_atomic_visible_subset',
              'coverage': 'controller_snapshot_only',
              'not_tested': ['browser_routing', 'os_routing', 'dns_coverage',
                             'actual_traffic', 'native_ownership_adapter', 'cross_source_consistency'],
              'requests_attempted': 0}
    try:
        _validate(binding, paths, budget)
        deadline = time.monotonic() + budget.max_seconds
        for path in tuple(paths):
            _guard(deadline, cancelled)
            if verify_binding(binding) is not True:
                _fail('CONTROLLER_NOT_BOUND')
            if approve_read(binding, path, budget) is not True:
                _fail('AUTHORIZATION_MISSING')
            _guard(deadline, cancelled)
            # Approval may wait for a person while the selected process changes.
            # Recheck the live identity after that wait, immediately before I/O.
            if verify_binding(binding) is not True:
                _fail('CONTROLLER_NOT_BOUND')
            _guard(deadline, cancelled)
            result['requests_attempted'] += 1
            status, raw = transport(binding, path, budget, deadline, cancelled)
            _guard(deadline, cancelled)
            if verify_binding(binding) is not True:
                _fail('CONTROLLER_NOT_BOUND')
            if status in (401, 403):
                _fail('AUTHENTICATION_HANDOFF_REQUIRED')
            if type(status) is not int or status != 200:
                _fail('CONTROLLER_RESPONSE_REJECTED')
            projection = _project(path, _parse(raw, budget))
            _guard(deadline, cancelled)
            result['facts'].append({'layer': 'runtime_observed',
                                    'source_ref': 'controller' + path,
                                    'revision_ref': 'revision-' + uuid.uuid4().hex,
                                    'observed_at': datetime.now(timezone.utc).isoformat(),
                                    'clock_accuracy': 'not_verified',
                                    'coverage': 'controller_snapshot_only', 'value': projection})
        result['execution_status'] = 'completed'
    except ControllerError as exc:
        # Host callbacks/transports can raise this class too. Never serialize
        # their arbitrary payload (even exception subclasses) into the report.
        code = getattr(exc, 'code', None)
        result['error_code'] = (code if type(code) is str and code in PUBLIC_ERROR_CODES
                                else 'INPUT_OR_RESPONSE_INVALID')
    except (socket.timeout, TimeoutError):
        result['error_code'] = 'TIMEOUT'
    except PermissionError:
        result['error_code'] = 'PERMISSION_DENIED'
    except Exception:
        result['error_code'] = 'INPUT_OR_RESPONSE_INVALID'
    if result['error_code'] in ('CANCELLED', 'CONTROLLER_NOT_BOUND'):
        result['facts'] = []
    if result['facts'] and result['error_code']:
        result['execution_status'] = 'partial'
    return result
