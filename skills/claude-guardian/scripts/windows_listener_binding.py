"""Opt-in, read-only Windows listener evidence. No CLI, transport, or discovery API.

Trusted host must approve exact Selection on every invocation, verify its device,
user and namespace mapping, and bound native blocking work with run_native. Neither
callbacks nor Selection are authorization supplied by a model. See accompanying doc.
"""
import ctypes as C
import ipaddress
import math
import os
import socket
import time
from dataclasses import dataclass

ERRORS = frozenset({'INPUT_INVALID', 'AUTHORIZATION_MISSING', 'TARGET_USER_CONTEXT_MISMATCH',
    'PLATFORM_UNSUPPORTED', 'PERMISSION_DENIED', 'CONTROLLER_NOT_BOUND',
    'SNAPSHOT_CHANGED_DURING_AUDIT', 'BUDGET_EXCEEDED', 'TIMEOUT', 'CANCELLED',
    'NATIVE_READ_FAILED'})


class BindingError(Exception):
    def __init__(self, code):
        self.code = code
        super().__init__(code)


@dataclass(frozen=True, repr=False)
class Selection:
    """Private host-owned metadata; never serialize to an agent-visible report."""
    target_ref: str
    namespace_ref: str
    desktop_user_ref: str
    host: str
    port: int
    process_id: int
    creation_filetime: int


@dataclass(frozen=True)
class Budget:
    max_seconds: float = 3.0
    max_table_bytes: int = 1048576
    max_rows: int = 16384


@dataclass(frozen=True, repr=False)
class _Observation:
    creation_filetime: int
    same_user: bool
    # Only rows at the selected port survive the native boundary.
    listeners: tuple


def _fail(code):
    raise BindingError(code)


def _validate(s, b):
    if type(s) is not Selection or type(b) is not Budget:
        _fail('INPUT_INVALID')
    if type(s.host) is not str or len(s.host) > 45 or '%' in s.host:
        _fail('INPUT_INVALID')
    try:
        address = ipaddress.ip_address(s.host)
    except ValueError:
        _fail('INPUT_INVALID')
    if not address.is_loopback or str(address) != s.host:
        _fail('CONTROLLER_NOT_BOUND')
    for value, limit in ((s.port, 65535), (s.process_id, 0xffffffff),
                         (s.creation_filetime, 0xffffffffffffffff)):
        if type(value) is not int or not 1 <= value <= limit:
            _fail('INPUT_INVALID')
    for value in (s.target_ref, s.namespace_ref, s.desktop_user_ref):
        if type(value) is not str or not 1 <= len(value) <= 128:
            _fail('INPUT_INVALID')
    if (type(b.max_seconds) not in (float, int) or not 0 < b.max_seconds <= 15
            or not math.isfinite(b.max_seconds)):
        _fail('INPUT_INVALID')
    for value, limit in ((b.max_table_bytes, 1048576), (b.max_rows, 16384)):
        if type(value) is not int or not 1 <= value <= limit:
            _fail('INPUT_INVALID')


def verify_listener(selection, *, approve_read, verify_context, run_native,
                    cancelled=lambda: False, budget=Budget(), _reader=None):
    """Return sanitized evidence only. Success is a momentary check, not a lease.

    approve_read(selection, budget) consults live exact-scope user approval.
    verify_context(selection) independently checks native device/user/namespace.
    run_native(callable, deadline, cancelled) MUST enforce a host-side timeout;
    Python cannot interrupt Win32 calls. It must preserve execution context and
    prevent timed-out work from continuing as an unowned background operation.
    All callbacks are trusted host integration, never serialized booleans.
    _reader is a private synthetic-test seam, not a user-configurable backend.
    """
    result = {'schema_version': 'guardian-windows-listener-binding/0.1',
              'execution_status': 'blocked', 'error_code': None,
              'listener_owner_verified': False, 'user_relation': 'unknown',
              'coverage': 'selected_listener_host_asserted_namespace',
              'namespace_evidence': 'host_callback_only_not_native_verified',
              'snapshot': 'non_atomic', 'gate_state': 'closed', 'changes': []}
    try:
        _validate(selection, budget)
        previous_tick = None
        def tick():
            nonlocal previous_tick
            value = time.monotonic()
            try:
                valid = type(value) in (int, float) and math.isfinite(value)
            except OverflowError:
                valid = False
            if not valid or (previous_tick is not None and value < previous_tick):
                _fail('NATIVE_READ_FAILED')
            previous_tick = value
            return value
        started = tick()
        deadline = started + budget.max_seconds
        if not math.isfinite(deadline) or deadline <= started:
            _fail('NATIVE_READ_FAILED')
        def guard():
            if cancelled():
                _fail('CANCELLED')
            if tick() >= deadline:
                _fail('TIMEOUT')
        guard()
        if not all(callable(x) for x in (approve_read, verify_context, run_native)):
            _fail('AUTHORIZATION_MISSING')
        if approve_read(selection, budget) is not True:
            _fail('AUTHORIZATION_MISSING')
        guard()
        if verify_context(selection) is not True:
            _fail('TARGET_USER_CONTEXT_MISMATCH')
        guard()
        previous = None
        for _ in range(2):
            # Revocation and host rebinding are checked before each native read.
            if approve_read(selection, budget) is not True:
                _fail('AUTHORIZATION_MISSING')
            if verify_context(selection) is not True:
                _fail('TARGET_USER_CONTEXT_MISMATCH')
            guard()
            observed = run_native(
                lambda: (_reader or _NativeReader()).observe(selection, budget, guard),
                deadline, cancelled)
            guard()
            if type(observed) is not _Observation:
                _fail('NATIVE_READ_FAILED')
            if previous is not None and observed != previous:
                _fail('SNAPSHOT_CHANGED_DURING_AUDIT')
            if observed.same_user is not True:
                _fail('TARGET_USER_CONTEXT_MISMATCH')
            if observed.creation_filetime != selection.creation_filetime:
                _fail('CONTROLLER_NOT_BOUND')
            # Conservative: every other listener at this port, even in the other
            # family, is ambiguity. Never normalize a wildcard into loopback.
            if observed.listeners != ((selection.host, selection.process_id),):
                _fail('CONTROLLER_NOT_BOUND')
            previous = observed
        if verify_context(selection) is not True:
            _fail('TARGET_USER_CONTEXT_MISMATCH')
        if approve_read(selection, budget) is not True:
            _fail('AUTHORIZATION_MISSING')
        guard()
        if verify_context(selection) is not True:
            _fail('TARGET_USER_CONTEXT_MISMATCH')
        guard()
        result.update(execution_status='completed', listener_owner_verified=True,
                      user_relation='same')
    except BindingError as exc:
        code = getattr(exc, 'code', None)
        result['error_code'] = code if type(code) is str and code in ERRORS else 'NATIVE_READ_FAILED'
    except TimeoutError:
        result['error_code'] = 'TIMEOUT'
    except PermissionError:
        result['error_code'] = 'PERMISSION_DENIED'
    except Exception:
        result['error_code'] = 'NATIVE_READ_FAILED'
    return result


# Fixed-width Win32 layouts also allow offline binary parser tests on Unix.
DWORD = C.c_uint32
HANDLE = C.c_void_p
BOOL = C.c_int32


class _Row4(C.Structure):
    _fields_ = [(name, DWORD) for name in ('state', 'address', 'port', 'remote', 'remote_port', 'pid')]


class _Row6(C.Structure):
    _fields_ = [('address', C.c_ubyte * 16), ('scope', DWORD), ('port', DWORD),
                ('remote', C.c_ubyte * 16), ('remote_scope', DWORD),
                ('remote_port', DWORD), ('state', DWORD), ('pid', DWORD)]


def _selected_rows(raw, family, port, budget):
    row_type = _Row4 if family == 2 else _Row6
    if len(raw) < 4 or len(raw) > budget.max_table_bytes:
        _fail('BUDGET_EXCEEDED')
    count = int.from_bytes(raw[:4], 'little')
    if count > budget.max_rows:
        _fail('BUDGET_EXCEEDED')
    if 4 + count * C.sizeof(row_type) > len(raw):
        _fail('NATIVE_READ_FAILED')
    selected = []
    for i in range(count):
        row = row_type.from_buffer_copy(raw, 4 + i * C.sizeof(row_type))
        if socket.ntohs(row.port & 0xffff) != port:
            continue
        if row.state != 2:
            _fail('NATIVE_READ_FAILED')
        address = (str(ipaddress.IPv4Address(row.address.to_bytes(4, 'little'))) if family == 2
                   else str(ipaddress.IPv6Address(bytes(row.address))))
        if family == 23 and row.scope:
            address += '%scoped'
        selected.append((address, row.pid))
    return selected


class _NativeReader:
    def __init__(self):
        if os.name != 'nt':
            _fail('PLATFORM_UNSUPPORTED')
        self.k = C.WinDLL('kernel32', use_last_error=True, winmode=0x800)
        self.a = C.WinDLL('advapi32', use_last_error=True, winmode=0x800)
        self.i = C.WinDLL('iphlpapi', use_last_error=True, winmode=0x800)
        signatures = [
            (self.k.OpenProcess, [DWORD, BOOL, DWORD], HANDLE),
            (self.k.CloseHandle, [HANDLE], BOOL),
            (self.k.WaitForSingleObject, [HANDLE, DWORD], DWORD),
            (self.k.GetCurrentProcess, [], HANDLE),
            (self.k.GetCurrentThread, [], HANDLE),
            (self.k.GetProcessTimes, [HANDLE] + [C.c_void_p] * 4, BOOL),
            (self.a.OpenProcessToken, [HANDLE, DWORD, C.POINTER(HANDLE)], BOOL),
            (self.a.OpenThreadToken, [HANDLE, DWORD, BOOL, C.POINTER(HANDLE)], BOOL),
            (self.a.GetTokenInformation, [HANDLE, DWORD, C.c_void_p, DWORD, C.POINTER(DWORD)], BOOL),
            (self.a.EqualSid, [C.c_void_p, C.c_void_p], BOOL),
            (self.i.GetExtendedTcpTable, [C.c_void_p, C.POINTER(DWORD), BOOL, DWORD, DWORD, DWORD], DWORD),
        ]
        for function, args, result in signatures:
            function.argtypes, function.restype = args, result

    def _check(self, success):
        if not success:
            _fail('PERMISSION_DENIED' if C.get_last_error() == 5 else 'NATIVE_READ_FAILED')

    def _user(self, process):
        token = HANDLE()
        self._check(self.a.OpenProcessToken(process, 8, C.byref(token)))
        try:
            needed = DWORD()
            ok = self.a.GetTokenInformation(token, 1, None, 0, C.byref(needed))
            if ok or C.get_last_error() != 122:
                _fail('NATIVE_READ_FAILED')
            if not 1 <= needed.value <= 4096:
                _fail('BUDGET_EXCEEDED')
            buffer = C.create_string_buffer(needed.value)
            self._check(self.a.GetTokenInformation(token, 1, buffer, needed, C.byref(needed)))
            return buffer  # keeps embedded SID alive; never stringify or export
        finally:
            self.k.CloseHandle(token)

    def _times(self, process):
        values = [C.c_uint64() for _ in range(4)]
        self._check(self.k.GetProcessTimes(process, *(C.byref(x) for x in values)))
        # Exit FILETIME is undefined while running. Only the documented wait
        # result establishes whether this process handle is still nonsignaled.
        status = self.k.WaitForSingleObject(process, 0)
        if status == 0:  # WAIT_OBJECT_0: process terminated
            _fail('SNAPSHOT_CHANGED_DURING_AUDIT')
        if status != 258:  # WAIT_TIMEOUT: still running
            _fail('PERMISSION_DENIED' if status == 0xffffffff and C.get_last_error() == 5
                  else 'NATIVE_READ_FAILED')
        return values[0].value

    def observe(self, selection, budget, guard):
        guard()
        # Reject impersonation rather than misreport the process token as the
        # effective thread user. Never impersonate, enable privileges, or elevate.
        thread_token = HANDLE()
        if self.a.OpenThreadToken(self.k.GetCurrentThread(), 8, True, C.byref(thread_token)):
            self.k.CloseHandle(thread_token)
            _fail('TARGET_USER_CONTEXT_MISMATCH')
        if C.get_last_error() != 1008:  # ERROR_NO_TOKEN
            _fail('TARGET_USER_CONTEXT_MISMATCH')
        process = self.k.OpenProcess(0x1000 | 0x100000, False, selection.process_id)
        self._check(process)
        try:
            creation = self._times(process)
            if creation != selection.creation_filetime:
                _fail('CONTROLLER_NOT_BOUND')
            owner, current = self._user(process), self._user(self.k.GetCurrentProcess())
            same_user = bool(self.a.EqualSid(C.cast(owner, C.POINTER(C.c_void_p))[0],
                                            C.cast(current, C.POINTER(C.c_void_p))[0]))
            if not same_user:
                _fail('TARGET_USER_CONTEXT_MISMATCH')
            rows = []
            for family in (2, 23):
                guard()
                needed = DWORD()
                code = self.i.GetExtendedTcpTable(None, C.byref(needed), False, family, 3, 0)
                if code != 122:
                    _fail('PERMISSION_DENIED' if code == 5 else 'NATIVE_READ_FAILED')
                if not 4 <= needed.value <= budget.max_table_bytes:
                    _fail('BUDGET_EXCEEDED')
                buffer = C.create_string_buffer(needed.value)
                code = self.i.GetExtendedTcpTable(buffer, C.byref(needed), False, family, 3, 0)
                if code:
                    _fail('SNAPSHOT_CHANGED_DURING_AUDIT' if code == 122 else
                          'PERMISSION_DENIED' if code == 5 else 'NATIVE_READ_FAILED')
                rows.extend(_selected_rows(buffer.raw, family, selection.port, budget))
            guard()
            if self._times(process) != creation:
                _fail('SNAPSHOT_CHANGED_DURING_AUDIT')
            return _Observation(creation, same_user, tuple(sorted(rows)))
        finally:
            self.k.CloseHandle(process)
