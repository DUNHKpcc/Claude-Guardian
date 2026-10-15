"""Opt-in Windows Resolve-DnsName sample; no CLI, discovery or I/O on import."""
import base64
import ipaddress
import json
import math
import ntpath
import os
import re
import subprocess
import sys
import threading
import time
from dataclasses import dataclass
from datetime import datetime, timezone

MAX_OUTPUT = 8192
MAX_REQUEST = 4096
MAX_ADDRESSES = 128
ERRORS = frozenset({'INPUT_INVALID', 'UNSUPPORTED_PLATFORM', 'PC0_TARGET_FORBIDDEN',
    'TARGET_NOT_BOUND', 'RUNTIME_NOT_TRUSTED', 'AUTHORIZATION_MISSING', 'CANCELLED',
    'TIMEOUT', 'OUTPUT_INVALID', 'OUTPUT_LIMIT', 'RESOLUTION_FAILED', 'PROCESS_FAILED',
    'CLEANUP_FAILED', 'PERMISSION_DENIED', 'DEPENDENCY_MISSING'})


class ProbeError(Exception):
    pass


@dataclass(frozen=True)
class Binding:
    target_ref: str
    desktop_user_ref: str
    namespace_ref: str
    platform: str
    powershell_executable: str
    dnsclient_module: str
    working_directory: str
    system_root: str


@dataclass(frozen=True)
class QueryScope:
    binding: Binding
    name: str
    query_type: str

    @property
    def absolute_name(self):
        return self.name + '.'

    @property
    def network_effect(self):
        return 'system_dns_may_disclose_name_to_configured_resolvers_and_upstream'


@dataclass(frozen=True)
class Budget:
    max_seconds: float = 5.0


# Fixed program only. Private input is never interpolated into code or argv.
# No profiles, fallback resolver, server override, cache flush, or child process.
_SCRIPT = r'''
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$PSModuleAutoLoadingPreference = 'None'
try {
    Import-Module -Name ($PSHOME + '\Modules\Microsoft.PowerShell.Utility\Microsoft.PowerShell.Utility.psd1') -ErrorAction Stop
    $buf = New-Object char[] 4097
    $n = 0
    while ($n -lt 4097) {
        $k = [Console]::In.Read($buf, $n, 4097 - $n)
        if ($k -eq 0) { break }
        $n += $k
    }
    if ($n -gt 4096) { exit 21 }
    $request = Microsoft.PowerShell.Utility\ConvertFrom-Json -InputObject (-join $buf[0..($n-1)])
    if ($request.kind -cne 'A' -and $request.kind -cne 'AAAA') { exit 21 }
    Import-Module -Name $request.module -ErrorAction Stop
} catch { exit 22 }
try {
    $addresses = New-Object 'System.Collections.Generic.List[string]'
    $count = 0
    DnsClient\Resolve-DnsName -Name $request.name -Type $request.kind -DnsOnly -ErrorAction Stop | ForEach-Object {
        $count++
        if ($count -gt 128) { throw 'limit' }
        if ($_.Type.ToString() -ceq $request.kind -and $_.Section.ToString() -eq 'Answer') {
            $address = [string]$_.IPAddress
            if (!$addresses.Contains($address)) { $addresses.Add($address) }
        }
    }
    $raw = Microsoft.PowerShell.Utility\ConvertTo-Json -InputObject @($addresses.ToArray()) -Compress
    if ($raw.Length -gt 8192) { exit 23 }
    [Console]::Out.Write($raw)
    exit 0
} catch { exit 20 }
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
    for path in (b.powershell_executable, b.dnsclient_module, b.working_directory, b.system_root):
        # Local drive absolute paths only; no UNC/network or device namespace paths.
        if (type(path) is not str or len(path) > 1024 or
                not re.match(r'^[A-Za-z]:\\', path) or any(ord(c) < 32 for c in path)
                or ':' in path[2:] or '..' in path.replace('/', '\\').split('\\')):
            raise ProbeError('INPUT_INVALID')
    if ntpath.basename(b.powershell_executable).lower() != 'powershell.exe':
        raise ProbeError('INPUT_INVALID')
    if b.platform != 'win32' or sys.platform != 'win32':
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


def _run_process(argv, request, deadline, cancelled, *, cwd, env):
    """Private owned-child runner. Unbuffered pipe threads work on Windows too.

    Buffers are bounded independently; stderr is discarded. The trusted fixed
    child must not spawn descendants or hand off pipe handles. OS spawn/kill and
    host callbacks are not hard-real-time bounded by this Python implementation.
    """
    _guard(deadline, cancelled)
    proc = subprocess.Popen(argv, stdin=subprocess.PIPE, stdout=subprocess.PIPE,
        stderr=subprocess.PIPE, bufsize=0, shell=False, close_fds=True, cwd=cwd, env=env)
    output = bytearray()
    overflow = threading.Event()
    io_failed = threading.Event()
    threads = []

    def drain(stream, save):
        total = 0
        try:
            while True:
                data = stream.read(1024)
                if not data:
                    break
                total += len(data)
                if total > MAX_OUTPUT:
                    overflow.set()
                    break
                if save:
                    output.extend(data)
        except (OSError, ValueError):
            io_failed.set()

    def feed():
        try:
            view = memoryview(request)
            while view:
                n = proc.stdin.write(view)
                if not n:
                    raise OSError()
                view = view[n:]
        except (OSError, ValueError):
            io_failed.set()
        finally:
            try:
                proc.stdin.close()
            except OSError:
                io_failed.set()

    try:
        for fn, args in ((drain, (proc.stdout, True)), (drain, (proc.stderr, False)), (feed, ())):
            thread = threading.Thread(target=fn, args=args, daemon=True)
            try:
                thread.start()
            except RuntimeError:
                raise ProbeError('PROCESS_FAILED') from None
            threads.append(thread)
        while True:
            _guard(deadline, cancelled)
            if overflow.is_set():
                raise ProbeError('OUTPUT_LIMIT')
            if proc.poll() is not None and not any(t.is_alive() for t in threads):
                break
            time.sleep(.01)
        if io_failed.is_set():
            raise ProbeError('PROCESS_FAILED')
        code = {20: 'RESOLUTION_FAILED', 21: 'OUTPUT_INVALID', 22: 'DEPENDENCY_MISSING',
                23: 'OUTPUT_LIMIT'}.get(proc.returncode, 'PROCESS_FAILED')
        if proc.returncode:
            raise ProbeError(code)
        return bytes(output)
    finally:
        failed = False
        if proc.poll() is None:
            try:
                proc.kill()
            except OSError:
                pass
        end = time.monotonic() + 1
        try:
            proc.wait(timeout=1)
        except (OSError, subprocess.TimeoutExpired):
            failed = True
        for t in threads:
            try:
                t.join(max(0, end - time.monotonic()))
                failed |= t.is_alive()
            except RuntimeError:
                failed = True
        # Unbuffered FileIO has no buffered-reader lock; close after child reap.
        for stream in (proc.stdin, proc.stdout, proc.stderr):
            try:
                stream.close()
            except OSError:
                failed = True
        if failed:
            raise ProbeError('CLEANUP_FAILED')


def _run_child(binding, request, deadline, cancelled):
    if len(request) > MAX_REQUEST:
        raise ProbeError('INPUT_INVALID')
    encoded = base64.b64encode(_SCRIPT.encode('utf-16-le')).decode('ascii')
    return _run_process([binding.powershell_executable, '-NoLogo', '-NoProfile',
        '-NonInteractive', '-EncodedCommand', encoded], request, deadline, cancelled,
        cwd=binding.working_directory,
        env={'SystemRoot': binding.system_root, 'WINDIR': binding.system_root, 'PSModulePath': ''})


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
        'address_family': 'IPv4' if kind == 'A' else 'IPv6', 'address_count': len(rows),
        'address_class_counts': counts, 'resolver_api': 'windows_Resolve-DnsName_DnsOnly',
        'cache_origin': 'possible_unknown', 'hosts_origin': 'possible_unknown',
        'dns_rcode': None, 'dns_packet_observed': False, 'actual_server': 'unknown',
        'path_association': 'unknown', 'leak_assessment': 'unknown',
        'fake_ip_assessment': 'not_evaluated'}


def probe_windows_dns(scope, *, verify_binding, verify_runtime, approve_query,
                      cancelled=lambda: False, budget=Budget()):
    """Host callbacks must freshly verify identity, all runtime paths/dependencies,
    effective context and replacement races, and exact query/type/disclosure/budget.
    Literal True only; callbacks must bound their own work. No native trust adapter
    is implemented here. Approval is interactive host evidence, not saved JSON.
    """
    result = {'schema_version': 'guardian-windows-dns-probe/0.1', 'operation': 'probe',
        'contact_phase': 'precontact', 'gate_state': 'closed', 'changes': [],
        'execution_status': 'blocked', 'error_code': None, 'facts': [],
        'requests_attempted': 0, 'coverage': 'windows_system_dns_sample_only',
        'not_tested': ['browser_dns', 'dns_packet', 'actual_server', 'dns_leak_absence',
                       'upstream_route', 'native_ownership_adapter']}
    try:
        _validate(scope, budget)
        deadline = time.monotonic() + budget.max_seconds
        def verify():
            _guard(deadline, cancelled)
            if verify_binding(scope.binding) is not True:
                raise ProbeError('TARGET_NOT_BOUND')
            _guard(deadline, cancelled)
            if verify_runtime(scope.binding) is not True:
                raise ProbeError('RUNTIME_NOT_TRUSTED')
            _guard(deadline, cancelled)
        verify()
        if approve_query(scope, budget) is not True:
            raise ProbeError('AUTHORIZATION_MISSING')
        verify()
        request = json.dumps({'name': scope.absolute_name, 'kind': scope.query_type,
                              'module': scope.binding.dnsclient_module}).encode('ascii')
        if len(request) > MAX_REQUEST:
            raise ProbeError('INPUT_INVALID')
        _guard(deadline, cancelled)
        result['requests_attempted'] = 1
        started = time.monotonic()
        raw = _run_child(scope.binding, request, deadline, cancelled)
        verify()
        value = _project(raw, scope.query_type)
        _guard(deadline, cancelled)
        result['facts'] = [{'source_ref': 'windows-system-dns', 'layer': 'runtime_observed',
            'observed_at': datetime.now(timezone.utc).isoformat(), 'clock_accuracy': 'not_verified',
            'elapsed_ms': round((time.monotonic() - started) * 1000, 3), 'value': value}]
        result['execution_status'] = 'completed'
    except ProbeError as exc:
        code = exc.args[0] if exc.args else None
        result['error_code'] = code if type(code) is str and code in ERRORS else 'OUTPUT_INVALID'
    except PermissionError:
        result['error_code'] = 'PERMISSION_DENIED'
    except FileNotFoundError:
        result['error_code'] = 'DEPENDENCY_MISSING'
    except Exception:
        result['error_code'] = 'OUTPUT_INVALID'
    return result
