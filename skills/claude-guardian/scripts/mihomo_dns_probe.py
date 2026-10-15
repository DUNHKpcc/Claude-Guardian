"""Opt-in ENV-04 Mihomo DNS sample; importing performs no I/O.

Trusted host callbacks must bind device/user/namespace/PID/start/listener AND
Mihomo product identity, and obtain fresh exact-scope network-query approval.
A localhost GET can cause upstream DNS traffic. Inventory approval is inadequate.
No credentials, discovery, CLI, configuration writes, or resolver fallback.
"""
import http.client
import ipaddress
import re
import socket
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from urllib.parse import urlencode

import controller_inventory as controller

ControllerBinding = controller.ControllerBinding
Budget = controller.Budget
ERRORS = controller.PUBLIC_ERROR_CODES | {'PC0_TARGET_FORBIDDEN', 'RESPONSE_CONTEXT_MISMATCH'}
TYPES = {'A': 1, 'AAAA': 28}


@dataclass(frozen=True)
class QueryScope:
    """Private exact query scope, never serialized into the public report."""
    binding: ControllerBinding
    name: str
    query_type: str

    @property
    def path(self):
        return '/dns/query?' + urlencode({'name': self.name, 'type': self.query_type})

    @property
    def network_effect(self):
        return 'mihomo_dns_query_may_contact_configured_upstream_resolvers'


def _fail(code='INPUT_OR_RESPONSE_INVALID'):
    raise controller.ControllerError(code)


def _name(value, response=False):
    if type(value) is not str:
        _fail()
    if response:
        value = value.removesuffix('.').lower()
    if (not 1 <= len(value) <= 253 or value != value.lower()
            or len(value.split('.')) < 2
            or any(not re.fullmatch(r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part)
                   for part in value.split('.'))):
        _fail()
    try:
        ipaddress.ip_address(value)
    except ValueError:
        return value
    _fail()


def _validate(scope, budget):
    if type(scope) is not QueryScope:
        _fail()
    # Reuse identity and bounded-budget checks, not the audit endpoint allowlist.
    controller._validate(scope.binding, ('/version',), budget)
    if budget.max_requests != 1:
        _fail()
    name = _name(scope.name)
    if type(scope.query_type) is not str or scope.query_type not in TYPES:
        _fail()
    if any('claude' in part or 'anthropic' in part for part in name.split('.')):
        _fail('PC0_TARGET_FORBIDDEN')


def dns_loopback_transport(scope, budget, deadline, cancelled):
    """One numeric-loopback GET. Internal transport, not an approval API.

    Reuses inventory's cancellation-aware byte-bounded reader. Its GET transport
    cannot be used directly: inventory intentionally excludes /dns/query.
    """
    _validate(scope, budget)
    binding = scope.binding
    guard = lambda: controller._guard(deadline, cancelled)
    guard()
    family = socket.AF_INET6 if binding.host == '::1' else socket.AF_INET
    with socket.socket(family, socket.SOCK_STREAM) as sock:
        sock.settimeout(max(.001, deadline - time.monotonic()))
        sock.connect((binding.host, binding.port))
        guard()
        host = '[::1]' if family == socket.AF_INET6 else '127.0.0.1'
        request = (f'GET {scope.path} HTTP/1.1\r\nHost: {host}:{binding.port}\r\n'
                   'Accept: application/json\r\nConnection: close\r\n\r\n')
        sock.settimeout(max(.001, deadline - time.monotonic()))
        guard()
        sock.sendall(request.encode('ascii'))
        reader = controller._BoundedReader(sock, budget.max_bytes, deadline, cancelled)
        response = http.client.HTTPResponse(controller._ResponseSocket(reader))
        try:
            response.begin()
            if response.status != 200:
                return response.status, b''
            lengths = response.headers.get_all('Content-Length', [])
            transfers = response.headers.get_all('Transfer-Encoding', [])
            encodings = response.headers.get_all('Content-Encoding', [])
            if (len(lengths) > 1 or len(transfers) > 1 or len(encodings) > 1
                    or (lengths and transfers)):
                _fail()
            if lengths and not re.fullmatch(r'[0-9]{1,20}', lengths[0].strip()):
                _fail()
            if lengths and int(lengths[0].strip()) > budget.max_bytes:
                _fail('BUDGET_EXCEEDED')
            if transfers and transfers[0].strip().lower() != 'chunked':
                _fail()
            if encodings and encodings[0].strip().lower() != 'identity':
                _fail()
            raw = response.read(budget.max_bytes + 1)
            if response.length not in (None, 0):
                _fail()
            if len(raw) > budget.max_bytes:
                _fail('BUDGET_EXCEEDED')
            return response.status, raw
        finally:
            response.close()


def _project(obj, scope):
    questions = obj.get('Question')
    if type(questions) is not list or len(questions) != 1 or type(questions[0]) is not dict:
        _fail('RESPONSE_CONTEXT_MISMATCH')
    question = questions[0]
    if (_name(question.get('Name'), True) != scope.name
            or type(question.get('Qtype')) is not int
            or question['Qtype'] != TYPES[scope.query_type]
            or type(question.get('Qclass')) is not int or question['Qclass'] != 1):
        _fail('RESPONSE_CONTEXT_MISMATCH')
    rcode = obj.get('Status')
    if type(rcode) is not int or not 0 <= rcode <= 4095 or type(obj.get('TC')) is not bool:
        _fail()
    answers = obj.get('Answer', [])
    if type(answers) is not list or len(answers) > 256:
        _fail()
    aliases, addresses = {}, []
    for answer in answers:
        if type(answer) is not dict:
            _fail()
        name = _name(answer.get('name'), True)
        kind, ttl, data = answer.get('type'), answer.get('TTL'), answer.get('data')
        if (type(kind) is not int or type(ttl) is not int or not 0 <= ttl <= 4294967295
                or type(data) is not str or len(data) > 254):
            _fail()
        if kind == 5:
            target = _name(data, True)
            if name in aliases:
                _fail('RESPONSE_CONTEXT_MISMATCH')
            aliases[name] = target
        elif kind == TYPES[scope.query_type]:
            address = ipaddress.ip_address(data)
            if '%' in data or address.version != (4 if kind == 1 else 6):
                _fail('RESPONSE_CONTEXT_MISMATCH')
            addresses.append((name, address))
        else:
            _fail('RESPONSE_CONTEXT_MISMATCH')
    reachable, current = set(), scope.name
    while current not in reachable:
        reachable.add(current)
        if current not in aliases:
            break
        current = aliases[current]
    else:
        _fail('RESPONSE_CONTEXT_MISMATCH')
    if (any(name not in reachable for name in aliases)
            or any(name != current for name, _ in addresses)):
        _fail('RESPONSE_CONTEXT_MISMATCH')
    counts = {'globally_routable': 0, 'non_global': 0}
    for _, address in addresses:
        global_unicast = (address.is_global and not any((address.is_multicast,
                              address.is_loopback, address.is_link_local,
                              address.is_unspecified, address.is_reserved)))
        counts['globally_routable' if global_unicast else 'non_global'] += 1
    return {'question_ref': 'query-1', 'question_matches': True,
            'query_type': scope.query_type, 'rcode': rcode, 'truncated': obj['TC'],
            'answer_count': len(answers), 'address_count': len(addresses),
            'cname_count': len(aliases), 'address_class_counts': counts,
            'address_family': 'IPv4' if scope.query_type == 'A' else 'IPv6',
            'fake_ip_assessment': 'not_evaluated', 'cache_origin': 'possible_unknown'}


def probe_mihomo_dns(scope, *, verify_binding, approve_query,
                     cancelled=lambda: False, budget=Budget(max_requests=1),
                     transport=dns_loopback_transport):
    """Gated single query. Callbacks/injected transport are trusted host code.

    verify_binding(binding) must verify live ownership and product identity;
    approve_query(scope, budget) must consult fresh network-probe consent for
    this target, exact name/type/path, budget and possible upstream disclosure.
    It must establish the name is an approved neutral PC0 endpoint. A caller's
    boolean is not user consent. There is no permissive callback default.
    Host callbacks must bound their own blocking work; deadlines are cooperative.
    """
    result = {'schema_version': 'guardian-mihomo-dns-probe/0.1', 'operation': 'probe',
              'contact_phase': 'precontact', 'gate_state': 'closed', 'changes': [],
              'execution_status': 'blocked', 'error_code': None, 'facts': [],
              'requests_attempted': 0, 'coverage': 'mihomo_dns_query_sample_only',
              'not_tested': ['system_dns', 'browser_dns', 'upstream_route',
                             'authoritative_correlation', 'dns_leak_absence',
                             'native_ownership_adapter']}
    try:
        _validate(scope, budget)
        deadline = time.monotonic() + budget.max_seconds
        guard = lambda: controller._guard(deadline, cancelled)
        guard()
        if verify_binding(scope.binding) is not True:
            _fail('CONTROLLER_NOT_BOUND')
        guard()
        if approve_query(scope, budget) is not True:
            _fail('AUTHORIZATION_MISSING')
        guard()
        if verify_binding(scope.binding) is not True:
            _fail('CONTROLLER_NOT_BOUND')
        guard()
        result['requests_attempted'] = 1
        started = time.monotonic()
        status, raw = transport(scope, budget, deadline, cancelled)
        guard()
        if verify_binding(scope.binding) is not True:
            _fail('CONTROLLER_NOT_BOUND')
        guard()
        if status in (401, 403):
            _fail('AUTHENTICATION_HANDOFF_REQUIRED')
        if type(status) is not int or status != 200:
            _fail('CONTROLLER_RESPONSE_REJECTED')
        projection = _project(controller._parse(raw, budget), scope)
        guard()
        result['facts'] = [{'source_ref': 'mihomo-dns-query', 'layer': 'runtime_observed',
                            'observed_at': datetime.now(timezone.utc).isoformat(),
                            'clock_accuracy': 'not_verified',
                            'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                            'value': projection}]
        result['execution_status'] = 'completed'
    except controller.ControllerError as exc:
        code = getattr(exc, 'code', None)
        result['error_code'] = code if type(code) is str and code in ERRORS else 'INPUT_OR_RESPONSE_INVALID'
    except (socket.timeout, TimeoutError):
        result['error_code'] = 'TIMEOUT'
    except PermissionError:
        result['error_code'] = 'PERMISSION_DENIED'
    except Exception:
        result['error_code'] = 'INPUT_OR_RESPONSE_INVALID'
    return result
