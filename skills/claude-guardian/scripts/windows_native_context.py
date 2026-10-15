"""Owned Windows process observations, never target binding or authorization.

No native calls on import. All native execution requires prior scoped host
permission. Private handles are ephemeral and must not be serialized or logged.
"""
import ctypes
import math
import ntpath
import os
import sys
import time
from dataclasses import dataclass, field


_STAGES = frozenset({'unknown', 'dll_initialization', 'thread_token',
    'process_session', 'active_console', 'process_token', 'token_user',
    'token_statistics', 'token_session', 'token_elevation', 'token_app_container',
    'token_restrictions', 'token_ui_access', 'wts_state', 'wts_protocol',
    'token_cleanup', 'identity_validation', 'runtime_paths', 'collection'})
_REASONS = frozenset({'unknown', 'api_call_failed', 'return_size_mismatch',
    'sid_pointer_bounds', 'sid_header_invalid', 'sid_size_bounds',
    'unexpected_exception'})


def _diagnostic(value, allowed):
    return value if type(value) is str and value in allowed else 'unknown'


class ContextError(Exception):
    """Stable code and optional fixed diagnostic enums; no native identifiers."""
    def __init__(self, code, *, stage='unknown', reason='unknown'):
        super().__init__(code)
        self.stage = _diagnostic(stage, _STAGES)
        self.reason = _diagnostic(reason, _REASONS)


def _step(stage, function, *args):
    """Attribute existing failures without changing native calls or decisions."""
    try:
        return function(*args)
    except ContextError as error:
        error.stage = _diagnostic(error.stage, _STAGES)
        error.reason = _diagnostic(error.reason, _REASONS)
        if error.stage == 'unknown':
            error.stage = _diagnostic(stage, _STAGES)
        raise
    except PermissionError:
        raise ContextError('PERMISSION_DENIED', stage=stage,
                           reason='unexpected_exception') from None
    except (OSError, AttributeError, ValueError, TypeError):
        raise ContextError('CONTEXT_UNKNOWN', stage=stage,
                           reason='unexpected_exception') from None


_U32 = ctypes.c_uint32
_I32 = ctypes.c_int32
_PTR = ctypes.c_void_p


class _LUID(ctypes.Structure):
    _fields_ = [('low', _U32), ('high', _I32)]


class _Statistics(ctypes.Structure):
    _fields_ = [('token', _LUID), ('authentication', _LUID),
                ('expiration', ctypes.c_int64), ('kind', _I32),
                ('impersonation', _I32), ('charged', _U32), ('available', _U32),
                ('groups', _U32), ('privileges', _U32), ('modified', _LUID)]


class _TokenUser(ctypes.Structure):
    _fields_ = [('sid', _PTR), ('attributes', _U32)]


@dataclass(frozen=True, repr=False)
class _Identity:
    pid: int
    thread_id: int
    process_session: int
    token_session: int
    console_session: int
    state: int
    protocol: int
    sid: bytes
    token_id: tuple
    authentication_id: tuple
    modified_id: tuple
    elevated: int
    app_container: int
    restricted: int
    ui_access: int


@dataclass(frozen=True, repr=False)
class ContextHandle:
    _identity: _Identity = field(repr=False)
    _runtime: tuple = field(repr=False)
    _created: float = field(repr=False)
    _expires: float = field(repr=False)
    _marker: object = field(repr=False)

    def __repr__(self):
        return '<WindowsContextHandle private observation>'

    def __reduce__(self):
        raise TypeError('Private context handles cannot be persisted')


_MARKER = object()


def _function(lib, name, result, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, list(args)
    return fn


def _native_error():
    raise ContextError('PERMISSION_DENIED' if ctypes.get_last_error() == 5
                       else 'CONTEXT_UNKNOWN', reason='api_call_failed')


class _WindowsAPI:
    """Fixed local APIs only. Windows 8+ system32 loader flag; no fallback."""
    def __init__(self):
        load = lambda name: ctypes.WinDLL(name, use_last_error=True, winmode=0x800)
        kernel, security, wts = (load(n) for n in
                                 ('kernel32.dll', 'advapi32.dll', 'wtsapi32.dll'))
        self.pid = _function(kernel, 'GetCurrentProcessId', _U32)
        self.tid = _function(kernel, 'GetCurrentThreadId', _U32)
        self.process = _function(kernel, 'GetCurrentProcess', _PTR)
        self.thread = _function(kernel, 'GetCurrentThread', _PTR)
        self.session = _function(kernel, 'ProcessIdToSessionId', _I32,
                                 _U32, ctypes.POINTER(_U32))
        self.console = _function(kernel, 'WTSGetActiveConsoleSessionId', _U32)
        self.close = _function(kernel, 'CloseHandle', _I32, _PTR)
        self.open_process = _function(security, 'OpenProcessToken', _I32,
                                      _PTR, _U32, ctypes.POINTER(_PTR))
        self.open_thread = _function(security, 'OpenThreadToken', _I32,
                                     _PTR, _U32, _I32, ctypes.POINTER(_PTR))
        self.info = _function(security, 'GetTokenInformation', _I32,
                              _PTR, _I32, _PTR, _U32, ctypes.POINTER(_U32))
        self.query = _function(wts, 'WTSQuerySessionInformationW', _I32,
                               _PTR, _U32, _I32, ctypes.POINTER(_PTR), ctypes.POINTER(_U32))
        self.free = _function(wts, 'WTSFreeMemory', None, _PTR)

    def _close(self, handle):
        if not self.close(handle):
            raise ContextError('CLEANUP_FAILED')

    def _no_impersonation(self):
        token = _PTR()
        # OpenAsSelf changes access checking only; it does not impersonate.
        if self.open_thread(self.thread(), 0x0008, 1, ctypes.byref(token)):
            _step('token_cleanup', self._close, token)
            raise ContextError('CONTEXT_FOREIGN')
        if ctypes.get_last_error() != 1008:  # ERROR_NO_TOKEN only
            _native_error()

    def _fixed(self, token, kind, structure):
        value, length = structure(), _U32()
        if not self.info(token, kind, ctypes.byref(value), ctypes.sizeof(value),
                         ctypes.byref(length)):
            _native_error()
        if length.value != ctypes.sizeof(value):
            raise ContextError('CONTEXT_UNKNOWN', reason='return_size_mismatch')
        return value

    def _sid(self, token):
        # TOKEN_USER has a variable-length SID. A fixed 256-byte allocation is
        # larger than TOKEN_USER + maximum SID (68); reject any unexpected size.
        buffer, length = ctypes.create_string_buffer(256), _U32()
        if not self.info(token, 1, buffer, len(buffer), ctypes.byref(length)):
            _native_error()
        if not ctypes.sizeof(_TokenUser) <= length.value <= len(buffer):
            raise ContextError('CONTEXT_UNKNOWN', reason='return_size_mismatch')
        start, end = ctypes.addressof(buffer), ctypes.addressof(buffer) + length.value
        address = _TokenUser.from_buffer(buffer).sid
        if not address or not start + ctypes.sizeof(_TokenUser) <= address <= end - 8:
            raise ContextError('CONTEXT_UNKNOWN', reason='sid_pointer_bounds')
        header = ctypes.string_at(address, 8)
        size = 8 + 4 * header[1]
        if header[0] != 1 or header[1] > 15:
            raise ContextError('CONTEXT_UNKNOWN', reason='sid_header_invalid')
        if address + size > end:
            raise ContextError('CONTEXT_UNKNOWN', reason='sid_size_bounds')
        return ctypes.string_at(address, size)

    def _wts(self, kind, structure):
        pointer, length = _PTR(), _U32()
        try:
            # WTS_CURRENT_SERVER_HANDLE / WTS_CURRENT_SESSION, never remote.
            if not self.query(None, 0xffffffff, kind, ctypes.byref(pointer),
                              ctypes.byref(length)):
                _native_error()
            if not pointer.value or length.value != ctypes.sizeof(structure):
                raise ContextError('CONTEXT_UNKNOWN', reason='return_size_mismatch')
            return structure.from_buffer_copy(ctypes.string_at(pointer, length.value)).value
        finally:
            if pointer.value:
                self.free(pointer)

    def read(self):
        _step('thread_token', self._no_impersonation)
        pid, tid, session = self.pid(), self.tid(), _U32()
        if not _step('process_session', self.session, pid, ctypes.byref(session)):
            _step('process_session', _native_error)
        # Reject a foreign/non-console session before any WTS session query.
        console = _step('active_console', self.console)
        if not session.value or console == 0xffffffff or session.value != console:
            raise ContextError('CONTEXT_FOREIGN')
        token = _PTR()
        if not _step('process_token', self.open_process, self.process(), 0x0008, ctypes.byref(token)):
            _step('process_token', _native_error)
        try:
            sid = _step('token_user', self._sid, token)
            stats = _step('token_statistics', self._fixed, token, 10, _Statistics)
            if stats.kind != 1:  # TokenPrimary
                raise ContextError('CONTEXT_FOREIGN')
            session_id = _step('token_session', self._fixed, token, 12, _U32).value
            elevated = _step('token_elevation', self._fixed, token, 20, _U32).value
            app = _step('token_app_container', self._fixed, token, 29, _U32).value
            restricted = _step('token_restrictions', self._fixed, token, 21, _U32).value  # TokenHasRestrictions
            ui_access = _step('token_ui_access', self._fixed, token, 26, _U32).value
            luid = lambda value: (value.low, value.high)
            identity = _Identity(pid, tid, session.value, session_id, console,
                _step('wts_state', self._wts, 8, _I32),
                _step('wts_protocol', self._wts, 16, ctypes.c_uint16), sid,
                luid(stats.token), luid(stats.authentication), luid(stats.modified),
                elevated, app, restricted, ui_access)
        finally:
            _step('token_cleanup', self._close, token)
        _step('thread_token', self._no_impersonation)
        return identity


def _validate_identity(value):
    if type(value) is not _Identity:
        raise ContextError('CONTEXT_UNKNOWN')
    for name in ('pid', 'thread_id', 'process_session', 'token_session',
                 'console_session', 'state', 'protocol', 'elevated',
                 'app_container', 'restricted', 'ui_access'):
        number = getattr(value, name)
        if type(number) is not int or not 0 <= number < 0xffffffff:
            raise ContextError('CONTEXT_UNKNOWN')
    for pair in (value.token_id, value.authentication_id, value.modified_id):
        if (type(pair) is not tuple or len(pair) != 2 or
                any(type(v) is not int for v in pair) or
                not 0 <= pair[0] <= 0xffffffff or not -(2**31) <= pair[1] < 2**31):
            raise ContextError('CONTEXT_UNKNOWN')
    sid = value.sid
    if (type(sid) is not bytes or len(sid) < 8 or sid[0] != 1 or
            sid[1] > 15 or len(sid) != 8 + sid[1] * 4):
        raise ContextError('CONTEXT_UNKNOWN')
    # LocalSystem, LocalService, NetworkService; never infer regular user from
    # exclusion alone. Other service identities remain blocked by unknown relation.
    if sid[:8] == b'\x01\x01\x00\x00\x00\x00\x00\x05' and int.from_bytes(sid[8:], 'little') in (18, 19, 20):
        raise ContextError('CONTEXT_FOREIGN')
    if (not value.pid or not value.thread_id or not value.process_session or
            value.process_session != value.token_session or
            value.process_session != value.console_session or
            value.elevated or value.app_container or value.restricted or value.ui_access):
        raise ContextError('CONTEXT_FOREIGN')
    if value.state != 0 or value.protocol != 0:
        raise ContextError('CONTEXT_INACTIVE_OR_REMOTE')


def _runtime():
    # Pure syntax screening: do not traverse drive mappings, junctions or UNC.
    paths = (sys.executable, os.getcwd(), sys.prefix, sys.base_prefix)
    for path in paths:
        if (type(path) is not str or not 3 <= len(path) <= 1024 or
                not path[0].isascii() or not path[0].isalpha() or path[1:3] != ':\\' or
                any(ord(c) < 32 for c in path) or ':' in path[2:] or '/' in path or
                ntpath.normpath(path) != path or
                any(p.endswith((' ', '.')) for p in path[3:].split('\\') if p)):
            raise ContextError('RUNTIME_PATH_INVALID')
    return paths


def _guard(cancelled, deadline, previous):
    if cancelled():
        raise ContextError('CANCELLED')
    now = time.monotonic()
    if not previous <= now < deadline:
        raise ContextError('CONTEXT_EXPIRED')
    return now


def _collect(cancelled, deadline, previous):
    if sys.platform != 'win32':
        raise ContextError('UNSUPPORTED_PLATFORM')
    previous = _guard(cancelled, deadline, previous)
    try:
        api = _step('dll_initialization', _WindowsAPI)
        first = _step('collection', api.read)
        _step('identity_validation', _validate_identity, first)
        previous = _guard(cancelled, deadline, previous)
        runtime = _step('runtime_paths', _runtime)
        previous = _guard(cancelled, deadline, previous)
        second = _step('collection', api.read)
        _step('identity_validation', _validate_identity, second)
        if first != second:
            raise ContextError('CONTEXT_CHANGED')
        previous = _guard(cancelled, deadline, previous)
        return first, runtime
    except ContextError:
        raise
    except PermissionError:
        raise ContextError('PERMISSION_DENIED') from None
    except (OSError, AttributeError, ValueError, TypeError):
        raise ContextError('CONTEXT_UNKNOWN') from None


def capture_current_context(*, max_age_seconds=30.0, cancelled=lambda: False):
    """Capture an observation, with user relation unknown and binding BLOCKED.

    A trusted host must approve scoped reads first. There is no authority input,
    console-account lookup, credential creation, elevation or networking here.
    """
    if (type(max_age_seconds) not in (int, float) or
            not .1 <= max_age_seconds <= 60 or not math.isfinite(max_age_seconds) or
            not callable(cancelled)):
        raise ContextError('INPUT_INVALID')
    created = time.monotonic()
    expires = created + max_age_seconds
    identity, runtime = _collect(cancelled, expires, created)
    return ContextHandle(identity, runtime, created, expires, _MARKER)


def _check_handle(handle):
    if type(handle) is not ContextHandle or handle._marker is not _MARKER:
        raise ContextError('INPUT_INVALID')


def recheck_context(handle, *, cancelled=lambda: False):
    """Same-thread continuity only; even success leaves target binding blocked."""
    _check_handle(handle)
    if not callable(cancelled):
        raise ContextError('INPUT_INVALID')
    previous = _guard(cancelled, handle._expires, handle._created)
    identity, runtime = _collect(cancelled, handle._expires, previous)
    if identity != handle._identity or runtime != handle._runtime:
        raise ContextError('CONTEXT_CHANGED')
    return describe_context(handle)


def describe_context(handle):
    """Sanitized historical facts, not a fresh check or executable capability."""
    _check_handle(handle)
    return {'schema_version': 'guardian-windows-native-context/0.1',
        'platform': 'win32', 'coverage': 'owned_process_current_thread_session_only',
        'effective_user_relation': 'process_token_no_thread_impersonation_at_observation',
        'desktop_user_relation': 'unknown', 'binding_state': 'blocked',
        'blocking_reason': 'CONSOLE_ACCOUNT_EQUALITY_UNPROVEN',
        'session_state': 'active_console_session_at_observation',
        'target_association': 'requires_trusted_host_assertion',
        'filesystem_namespace': 'unknown', 'network_namespace': 'unknown',
        'runtime_path_screen': 'local_drive_syntax_only',
        'runtime_integrity': 'not_verified', 'gate_state': 'closed',
        'native_platform_validation': 'not_run', 'changes': [],
        'remaining_host_requirements': ['selected_target_association',
            'console_account_equality', 'execution_namespace',
            'runtime_and_dependency_trust', 'operation_specific_live_approval']}
