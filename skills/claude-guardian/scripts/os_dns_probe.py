"""Opt-in macOS system-resolution sample. No I/O on import and no CLI.

Host callbacks are trust boundaries, not JSON consent. Windows needs the distinct
Resolve-DnsName adapter specified in D-ENV 20.4.2; never substitute getaddrinfo.
"""
import ipaddress
import json
import math
import os
import re
import selectors
import subprocess
import sys
import time
from dataclasses import dataclass
from datetime import datetime, timezone

MAX_OUTPUT = 4096
MAX_ADDRESSES = 128
ERRORS = frozenset({'INPUT_INVALID', 'UNSUPPORTED_PLATFORM', 'PC0_TARGET_FORBIDDEN',
                    'TARGET_NOT_BOUND', 'RUNTIME_NOT_TRUSTED', 'AUTHORIZATION_MISSING',
                    'CANCELLED', 'TIMEOUT', 'OUTPUT_INVALID', 'OUTPUT_LIMIT',
                    'RESOLUTION_FAILED', 'PROCESS_FAILED', 'CLEANUP_FAILED',
                    'PERMISSION_DENIED'})


class ProbeError(Exception):
    pass


@dataclass(frozen=True)
class Binding:
    target_ref: str
    desktop_user_ref: str
    namespace_ref: str
    platform: str
    python_executable: str
    working_directory: str


@dataclass(frozen=True)
class QueryScope:
    binding: Binding
    name: str
    query_type: str

    @property
    def absolute_name(self):
        """Exact native resolver name covered by approve_query."""
        return self.name + '.'

    @property
    def network_effect(self):
        return 'system_resolution_may_contact_configured_resolvers'


@dataclass(frozen=True)
class Budget:
    max_seconds: float = 5.0


# Fixed code only; no application imports, eval, shell, external tools or retries.
# stdout is a bounded address list for private validation; public output is counts.
_HELPER = r'''
import ipaddress, json, socket, sys
try:
    request = sys.stdin.buffer.read(513)
    if len(request) > 512: raise ValueError()
    name, kind = json.loads(request)
    family = socket.AF_INET if kind == 'A' else socket.AF_INET6
    rows = socket.getaddrinfo(name, None, family, socket.SOCK_STREAM, 0, 0)
    if len(rows) > 128: raise ValueError()
    addresses = []
    for row in rows:
        if row[0] != family: raise ValueError()
        address = ipaddress.ip_address(row[4][0])
        if address.version != (4 if kind == 'A' else 6): raise ValueError()
        if str(address) not in addresses: addresses.append(str(address))
    raw = json.dumps(addresses, separators=(',', ':')).encode('ascii')
    if len(raw) > 4096: raise ValueError()
    sys.stdout.buffer.write(raw)
except socket.gaierror:
    sys.exit(20)
except Exception:
    sys.exit(21)
'''


def _guard(deadline, cancelled):
    if cancelled():
        raise ProbeError('CANCELLED')
    if time.monotonic() >= deadline:
        raise ProbeError('TIMEOUT')


def _validate(scope, budget):
    if type(scope) is not QueryScope or type(scope.binding) is not Binding or type(budget) is not Budget:
        raise ProbeError('INPUT_INVALID')
    b = scope.binding
    for value in (b.target_ref, b.desktop_user_ref, b.namespace_ref):
        if type(value) is not str or not re.fullmatch(r'[A-Za-z0-9_-]{1,80}', value):
            raise ProbeError('INPUT_INVALID')
    for path in (b.python_executable, b.working_directory):
        if type(path) is not str or len(path) > 4096 or '\0' in path or not os.path.isabs(path):
            raise ProbeError('INPUT_INVALID')
    if b.platform != 'darwin' or sys.platform != 'darwin':
        raise ProbeError('UNSUPPORTED_PLATFORM')
    if (type(budget.max_seconds) not in (int, float) or not math.isfinite(budget.max_seconds)
            or not .05 <= budget.max_seconds <= 15):
        raise ProbeError('INPUT_INVALID')
    name = scope.name
    if (type(name) is not str or not 1 <= len(name) <= 253 or name != name.lower()
            or len(name.split('.')) < 2 or any(not re.fullmatch(
                r'[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?', part) for part in name.split('.'))
            or type(scope.query_type) is not str or scope.query_type not in ('A', 'AAAA')):
        raise ProbeError('INPUT_INVALID')
    try:
        ipaddress.ip_address(name)
    except ValueError:
        pass
    else:
        raise ProbeError('INPUT_INVALID')
    if 'claude' in name or 'anthropic' in name:
        raise ProbeError('PC0_TARGET_FORBIDDEN')


def _run_child(binding, request, deadline, cancelled):
    """Private POSIX process runner; only fixed trusted helper code may be used.

    Spawn and kernel termination cannot be hard-deadlined by Python. After spawn,
    polling interrupts a blocked resolver; cleanup gets a separate 1 second bound.
    A cleanup failure is reported, never represented as successful cancellation.
    """
    _guard(deadline, cancelled)
    proc = subprocess.Popen([binding.python_executable, '-I', '-S', '-c', _HELPER],
                            stdin=subprocess.PIPE, stdout=subprocess.PIPE,
                            stderr=subprocess.DEVNULL, env={},
                            cwd=binding.working_directory, close_fds=True, shell=False)
    try:
        _guard(deadline, cancelled)
        # <512 bytes fits an empty POSIX pipe. The trusted helper creates no children.
        proc.stdin.write(request)
        proc.stdin.close()
        os.set_blocking(proc.stdout.fileno(), False)
        raw = bytearray()
        with selectors.DefaultSelector() as selector:
            selector.register(proc.stdout, selectors.EVENT_READ)
            eof = False
            while not eof or proc.poll() is None:
                _guard(deadline, cancelled)
                if eof:
                    time.sleep(min(.02, max(0, deadline - time.monotonic())))
                    continue
                for key, event in selector.select(min(.02, max(0, deadline - time.monotonic()))):
                    data = os.read(key.fd, min(1024, MAX_OUTPUT + 1 - len(raw)))
                    if not data:
                        eof = True
                        selector.unregister(proc.stdout)
                    else:
                        raw.extend(data)
                        if len(raw) > MAX_OUTPUT:
                            raise ProbeError('OUTPUT_LIMIT')
        _guard(deadline, cancelled)
        if proc.returncode == 20:
            raise ProbeError('RESOLUTION_FAILED')
        if proc.returncode != 0:
            raise ProbeError('PROCESS_FAILED')
        return bytes(raw)
    finally:
        cleanup_failed = False
        try:
            if proc.poll() is None:
                try:
                    proc.kill()
                except OSError:
                    # An exit race can make kill fail; still attempt bounded reap.
                    pass
            try:
                proc.wait(timeout=1)
            except (OSError, subprocess.TimeoutExpired):
                cleanup_failed = True
        finally:
            for stream in (proc.stdin, proc.stdout):
                if stream is not None:
                    try:
                        stream.close()
                    except OSError:
                        cleanup_failed = True
        if cleanup_failed:
            raise ProbeError('CLEANUP_FAILED')


def _project(raw, kind):
    if type(raw) is not bytes or len(raw) > MAX_OUTPUT:
        raise ProbeError('OUTPUT_LIMIT')
    rows = json.loads(raw)
    if type(rows) is not list or len(rows) > MAX_ADDRESSES:
        raise ProbeError('OUTPUT_INVALID')
    counts = {'globally_routable': 0, 'non_global': 0}
    seen = set()
    for value in rows:
        if type(value) is not str or len(value) > 45 or '%' in value:
            raise ProbeError('OUTPUT_INVALID')
        address = ipaddress.ip_address(value)
        if address.version != (4 if kind == 'A' else 6) or address in seen:
            raise ProbeError('OUTPUT_INVALID')
        seen.add(address)
        public = address.is_global and not any((address.is_multicast, address.is_reserved,
                address.is_loopback, address.is_link_local, address.is_unspecified))
        counts['globally_routable' if public else 'non_global'] += 1
    return {'question_ref': 'query-1', 'query_type': kind,
            'address_family': 'IPv4' if kind == 'A' else 'IPv6',
            'address_count': len(rows), 'address_class_counts': counts,
            'resolver_api': 'macos_getaddrinfo', 'cache_origin': 'possible_unknown',
            'dns_rcode': None, 'dns_packet_observed': False,
            'actual_server': 'unknown', 'path_association': 'unknown',
            'leak_assessment': 'unknown', 'fake_ip_assessment': 'not_evaluated'}


def probe_os_dns(scope, *, verify_binding, verify_runtime, approve_query,
                 cancelled=lambda: False, budget=Budget()):
    """One approved macOS final-resolution sample, gate remains closed.

    Trusted host verifies live target/device/user/namespace and effective context;
    runtime verifier verifies executable, stdlib/extensions/loader dependencies and
    working directory trust, including replacement races. Callbacks must bound their
    own work. Approval covers exact scope, trailing-dot absolute query and budget.
    No native identity/trust implementation is claimed by this library.
    """
    result = {'schema_version': 'guardian-os-dns-probe/0.1', 'operation': 'probe',
              'contact_phase': 'precontact', 'gate_state': 'closed', 'changes': [],
              'execution_status': 'blocked', 'error_code': None, 'facts': [],
              'requests_attempted': 0, 'coverage': 'macos_system_resolution_sample_only',
              'not_tested': ['windows_dns', 'browser_dns', 'dns_packet', 'actual_server',
                             'dns_leak_absence', 'upstream_route', 'native_ownership_adapter']}
    try:
        _validate(scope, budget)
        deadline = time.monotonic() + budget.max_seconds
        guard = lambda: _guard(deadline, cancelled)
        def verify():
            guard()
            if verify_binding(scope.binding) is not True:
                raise ProbeError('TARGET_NOT_BOUND')
            guard()
            if verify_runtime(scope.binding) is not True:
                raise ProbeError('RUNTIME_NOT_TRUSTED')
            guard()
        verify()
        if approve_query(scope, budget) is not True:
            raise ProbeError('AUTHORIZATION_MISSING')
        verify()
        # Absolute name suppresses search-suffix expansion; no second query/retry.
        request = json.dumps([scope.absolute_name, scope.query_type]).encode('ascii')
        guard()
        result['requests_attempted'] = 1
        started = time.monotonic()
        raw = _run_child(scope.binding, request, deadline, cancelled)
        verify()
        projection = _project(raw, scope.query_type)
        guard()
        result['facts'] = [{'source_ref': 'os-system-resolution', 'layer': 'runtime_observed',
                            'observed_at': datetime.now(timezone.utc).isoformat(),
                            'clock_accuracy': 'not_verified',
                            'elapsed_ms': round((time.monotonic() - started) * 1000, 3),
                            'value': projection}]
        result['execution_status'] = 'completed'
    except ProbeError as exc:
        code = exc.args[0] if exc.args else None
        result['error_code'] = code if type(code) is str and code in ERRORS else 'OUTPUT_INVALID'
    except PermissionError:
        result['error_code'] = 'PERMISSION_DENIED'
    except Exception:
        result['error_code'] = 'OUTPUT_INVALID'
    return result
