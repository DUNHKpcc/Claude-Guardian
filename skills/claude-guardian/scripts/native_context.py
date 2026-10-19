"""Narrow macOS process-context observation, not an execution authorization.

No I/O on import. Call only inside an already trusted host after scoped read
approval. Private handles must remain in that host; reports are not capabilities.
"""
import ctypes
import math
import os
import stat
import sys
import time
from dataclasses import dataclass, field


class ContextError(Exception):
    """Only stable, non-sensitive error codes cross this boundary."""
    def __init__(self, code, *, path_field='unknown', path_reason='unknown',
                 stage='unknown', reason='unknown'):
        super().__init__(code)
        self.path_field = path_field if type(path_field) is str and path_field in PATH_FIELDS else 'unknown'
        self.path_reason = path_reason if type(path_reason) is str and path_reason in PATH_REASONS else 'unknown'
        self.stage = stage if type(stage) is str and stage in API_STAGES else 'unknown'
        self.reason = reason if type(reason) is str and reason in API_REASONS else 'unknown'


PATH_FIELDS = frozenset({'unknown', 'executable', 'cwd', 'prefix', 'base_prefix'})
PATH_REASONS = frozenset({'unknown', 'invalid_syntax', 'too_deep', 'symlink',
                          'not_directory', 'not_regular_file'})
API_STAGES = frozenset({'unknown', 'console_user'})
API_REASONS = frozenset({'unknown', 'null_result'})


def api_diagnostic(error):
    """Expose the failing API stage, never an inferred identity or native data."""
    stage = getattr(error, 'stage', 'unknown')
    reason = getattr(error, 'reason', 'unknown')
    return {'stage': stage if type(stage) is str and stage in API_STAGES else 'unknown',
            'reason': reason if type(reason) is str and reason in API_REASONS else 'unknown'}


def path_diagnostic(error):
    """Fixed enums only, including when called with a foreign exception object."""
    field = getattr(error, 'path_field', 'unknown')
    reason = getattr(error, 'path_reason', 'unknown')
    return {'path_field': field if type(field) is str and field in PATH_FIELDS else 'unknown',
            'path_reason': reason if type(reason) is str and reason in PATH_REASONS else 'unknown'}


@dataclass(frozen=True, repr=False)
class _Identity:
    pid: int
    uid: int
    euid: int
    gid: int
    egid: int
    groups: tuple
    posix_session: int
    security_session: int
    security_attributes: int
    console_uid: int
    graphical_uid: int
    on_console: bool
    login_done: bool


@dataclass(frozen=True, repr=False)
class _Runtime:
    executable: str
    directory: str
    prefix: str
    base_prefix: str
    identities: tuple
    screen: str


@dataclass(frozen=True, repr=False)
class ContextHandle:
    """Ephemeral private observation. Neither consent nor namespace proof.

    Construction is internal convention, not protection from hostile Python.
    Do not serialize, log, or expose its private fields in a report.
    """
    _identity: _Identity = field(repr=False)
    _runtime: _Runtime = field(repr=False)
    _created: float = field(repr=False)
    _expires: float = field(repr=False)
    _marker: object = field(repr=False)

    def __repr__(self):
        return '<ContextHandle private observation>'

    def __reduce__(self):
        raise TypeError('Private context handles cannot be persisted')


_MARKER = object()
_FRAMEWORKS = '/System/Library/Frameworks/'
# CGSession.h defines CFSTR macros, not exported pointer symbols.
_CG_KEYS = {
    'kCGSessionUserIDKey': b'kCGSSessionUserIDKey',
    'kCGSessionOnConsoleKey': b'kCGSSessionOnConsoleKey',
    'kCGSessionLoginDoneKey': b'kCGSessionLoginDoneKey',
}


def _function(lib, name, result, *args):
    fn = getattr(lib, name)
    fn.restype, fn.argtypes = result, list(args)
    return fn


class _MacAPI:
    """Fixed Apple framework calls; no shell, env lookup, or process enumeration."""
    def __init__(self):
        void, u32 = ctypes.c_void_p, ctypes.c_uint32
        self.cf = ctypes.CDLL(_FRAMEWORKS + 'CoreFoundation.framework/CoreFoundation')
        self.sc = ctypes.CDLL(_FRAMEWORKS + 'SystemConfiguration.framework/SystemConfiguration')
        self.cg = ctypes.CDLL(_FRAMEWORKS + 'CoreGraphics.framework/CoreGraphics')
        self.security = ctypes.CDLL(_FRAMEWORKS + 'Security.framework/Security')
        self.release = _function(self.cf, 'CFRelease', None, void)
        self.string = _function(self.cf, 'CFStringCreateWithCString', void,
                                void, ctypes.c_char_p, ctypes.c_uint32)
        self.type_id = _function(self.cf, 'CFGetTypeID', ctypes.c_ulong, void)
        self.bool_type = _function(self.cf, 'CFBooleanGetTypeID', ctypes.c_ulong)
        self.num_type = _function(self.cf, 'CFNumberGetTypeID', ctypes.c_ulong)
        self.dict_type = _function(self.cf, 'CFDictionaryGetTypeID', ctypes.c_ulong)
        self.bool_value = _function(self.cf, 'CFBooleanGetValue', ctypes.c_ubyte, void)
        self.num_value = _function(self.cf, 'CFNumberGetValue', ctypes.c_ubyte,
                                   void, ctypes.c_long, void)
        self.dict_value = _function(self.cf, 'CFDictionaryGetValue', void, void, void)
        self.console = _function(self.sc, 'SCDynamicStoreCopyConsoleUser', void,
                                 void, ctypes.POINTER(u32), ctypes.POINTER(u32))
        self.session = _function(self.security, 'SessionGetInfo', ctypes.c_int32,
                                 u32, ctypes.POINTER(u32), ctypes.POINTER(u32))
        self.graphics = _function(self.cg, 'CGSessionCopyCurrentDictionary', void)

    def _value(self, dictionary, symbol, kind):
        if symbol not in _CG_KEYS or kind not in ('bool', 'number'):
            raise ContextError('CONTEXT_UNKNOWN')
        # kCFStringEncodingUTF8; exactly three fixed SDK key literals only.
        key = self.string(None, _CG_KEYS[symbol], 0x08000100)
        if not key:
            raise ContextError('CONTEXT_UNKNOWN')
        try:
            value = self.dict_value(dictionary, key)
            expected = self.bool_type() if kind == 'bool' else self.num_type()
            if not value or self.type_id(value) != expected:
                raise ContextError('CONTEXT_UNKNOWN')
            if kind == 'bool':
                return bool(self.bool_value(value))
            number = ctypes.c_int64()
            # kCFNumberSInt64Type = 4, checked conversion, not a pointer cast.
            if not self.num_value(value, 4, ctypes.byref(number)):
                raise ContextError('CONTEXT_UNKNOWN')
            return number.value
        finally:
            self.release(key)

    def read(self):
        session, attributes = ctypes.c_uint32(), ctypes.c_uint32()
        if self.session(0xffffffff, ctypes.byref(session), ctypes.byref(attributes)):
            raise ContextError('CONTEXT_UNKNOWN')
        uid, gid = ctypes.c_uint32(), ctypes.c_uint32()
        name = self.console(None, ctypes.byref(uid), ctypes.byref(gid))
        if not name:
            # NULL does not establish whether anyone is logged in, nor why this
            # API failed to provide the observation. Identity remains unknown.
            raise ContextError('CONTEXT_UNKNOWN', stage='console_user', reason='null_result')
        # Never convert/copy the returned user's name into Python.
        self.release(name)
        dictionary = self.graphics()
        if not dictionary:
            raise ContextError('CONTEXT_INACTIVE')
        try:
            if self.type_id(dictionary) != self.dict_type():
                raise ContextError('CONTEXT_UNKNOWN')
            graphical_uid = self._value(dictionary, 'kCGSessionUserIDKey', 'number')
            on_console = self._value(dictionary, 'kCGSessionOnConsoleKey', 'bool')
            login_done = self._value(dictionary, 'kCGSessionLoginDoneKey', 'bool')
        finally:
            self.release(dictionary)
        return _Identity(os.getpid(), os.getuid(), os.geteuid(), os.getgid(),
            os.getegid(), tuple(sorted(os.getgroups())), os.getsid(0), session.value,
            attributes.value, uid.value, graphical_uid, on_console, login_done)


def _validate_identity(value):
    if type(value) is not _Identity:
        raise ContextError('CONTEXT_UNKNOWN')
    ints = (value.pid, value.uid, value.euid, value.gid, value.egid,
            value.posix_session, value.security_session, value.security_attributes,
            value.console_uid, value.graphical_uid)
    if (any(type(v) is not int or v < 0 for v in ints)
            or type(value.groups) is not tuple
            or any(type(v) is not int or v < 0 for v in value.groups)
            or type(value.on_console) is not bool or type(value.login_done) is not bool
            or value.pid == 0 or value.posix_session == 0
            or value.security_session in (0, 0xfffffffe, 0xffffffff)):
        raise ContextError('CONTEXT_UNKNOWN')
    if (value.uid == 0 or value.uid != value.euid or value.gid != value.egid
            or value.uid != value.console_uid or value.uid != value.graphical_uid):
        raise ContextError('TARGET_USER_CONTEXT_MISMATCH')
    # Graphic access is not active-console proof; require both independently.
    if (not value.on_console or not value.login_done
            or not value.security_attributes & 0x10):
        raise ContextError('CONTEXT_INACTIVE')
    if value.security_attributes & (0x1 | 0x1000):
        raise ContextError('CONTEXT_FOREIGN')


def _path_identity(path, directory):
    """Conservative lstat screening, never an ACL/signature/integrity verdict."""
    if (type(path) is not str or not path.startswith('/') or len(path) > 4096
            or path.startswith('//') or '\0' in path or os.path.normpath(path) != path):
        raise ContextError('RUNTIME_PATH_INVALID', path_reason='invalid_syntax')
    parts = path.split('/')[1:]
    if len(parts) > 64:
        raise ContextError('RUNTIME_PATH_INVALID', path_reason='too_deep')
    paths = ['/'] + ['/' + '/'.join(parts[:i]) for i in range(1, len(parts) + 1)]
    if path == '/':
        paths = ['/']
    result, screened = [], True
    for index, selected in enumerate(paths):
        item = os.lstat(selected)
        final = index == len(paths) - 1
        required = stat.S_ISDIR if not final or directory else stat.S_ISREG
        if not required(item.st_mode):
            reason = ('symlink' if stat.S_ISLNK(item.st_mode) else
                      'not_directory' if not final or directory else 'not_regular_file')
            raise ContextError('RUNTIME_PATH_INVALID', path_reason=reason)
        screened &= item.st_uid == 0 and not item.st_mode & 0o022
        result.append((selected, item.st_dev, item.st_ino, item.st_mode,
                       item.st_uid, item.st_gid, item.st_size,
                       item.st_mtime_ns, item.st_ctime_ns))
    return tuple(result), screened


def _runtime():
    paths = (sys.executable, os.getcwd(), sys.prefix, sys.base_prefix)
    identities, screened = [], True
    for field, path, directory in zip(('executable', 'cwd', 'prefix', 'base_prefix'),
                                       paths, (False, True, True, True)):
        try:
            rows, acceptable = _path_identity(path, directory)
        except ContextError as error:
            if str(error) != 'RUNTIME_PATH_INVALID':
                raise
            raise ContextError('RUNTIME_PATH_INVALID', path_field=field,
                               path_reason=path_diagnostic(error)['path_reason']) from None
        identities.append(rows)
        screened &= acceptable
    return _Runtime(*paths, tuple(identities),
                    'root_owned_mode_screen_only' if screened else 'rejected_writable_or_nonroot')


def _guard(cancelled, deadline):
    if cancelled():
        raise ContextError('CANCELLED')
    if time.monotonic() >= deadline:
        raise ContextError('CONTEXT_EXPIRED')


def _collect(cancelled, deadline):
    if sys.platform != 'darwin':
        raise ContextError('UNSUPPORTED_PLATFORM')
    _guard(cancelled, deadline)
    try:
        api = _MacAPI()
        first = api.read()
        _validate_identity(first)
        _guard(cancelled, deadline)
        runtime = _runtime()
        _guard(cancelled, deadline)
        second = api.read()
        _validate_identity(second)
        if first != second:
            raise ContextError('CONTEXT_CHANGED')
        _guard(cancelled, deadline)
        return first, runtime
    except ContextError:
        raise
    except PermissionError:
        raise ContextError('PERMISSION_DENIED') from None
    except (OSError, AttributeError, ValueError, TypeError):
        raise ContextError('CONTEXT_UNKNOWN') from None


def capture_current_context(*, max_age_seconds=30.0, cancelled=lambda: False):
    """Read only this process/primary console and four fixed runtime path chains.

    Host must authorize these reads before calling. No JSON/CLI approval input.
    Native synchronous APIs cannot be forcibly deadline-interrupted here.
    """
    if (type(max_age_seconds) not in (int, float) or not .1 <= max_age_seconds <= 60
            or not math.isfinite(max_age_seconds) or not callable(cancelled)):
        raise ContextError('INPUT_INVALID')
    created = time.monotonic()
    expires = created + max_age_seconds
    identity, runtime = _collect(cancelled, expires)
    return ContextHandle(identity, runtime, created, expires, _MARKER)


def recheck_context(handle, *, cancelled=lambda: False):
    """Freshly compare to a private same-process handle; return sanitized facts.

    A passing comparison is observation continuity only, not target ownership,
    runtime trust, approval, network namespace identity, or a DNS execution gate.
    """
    if (type(handle) is not ContextHandle or handle._marker is not _MARKER
            or not callable(cancelled)):
        raise ContextError('INPUT_INVALID')
    _guard(cancelled, handle._expires)
    if time.monotonic() < handle._created:
        raise ContextError('CONTEXT_EXPIRED')
    identity, runtime = _collect(cancelled, handle._expires)
    if identity != handle._identity or runtime != handle._runtime:
        raise ContextError('CONTEXT_CHANGED')
    return describe_context(handle)


def describe_context(handle):
    """Redacted snapshot summary; does not re-read or establish freshness."""
    if type(handle) is not ContextHandle or handle._marker is not _MARKER:
        raise ContextError('INPUT_INVALID')
    return _summary(handle._runtime.screen)


def _summary(runtime_screen):
    return {'schema_version': 'guardian-native-context/0.1',
        'platform': 'darwin', 'coverage': 'current_process_primary_console_only',
        'desktop_user_relation': 'same_at_observation',
        'session_state': 'active_console_at_observation',
        'target_association': 'requires_trusted_host_assertion',
        'filesystem_namespace': 'unknown', 'network_namespace': 'unknown',
        'runtime_path_screen': runtime_screen,
        'runtime_integrity': 'not_verified', 'gate_state': 'closed',
        'changes': [], 'native_platform_validation': 'not_run',
        'remaining_host_requirements': ['selected_target_association',
            'execution_namespace', 'runtime_and_dependency_trust',
            'operation_specific_live_approval']}


def observe_context_metadata(*, max_seconds=5.0, cancelled=lambda: False):
    """Bounded metadata-only observation; never returns a ContextHandle.

    Preserves independently observed identity if restrictive runtime path syntax/
    node screening fails. Identity, expiry and cancellation failures still raise.
    Neither successful nor partial metadata may be passed as an execution gate.
    Host authorization for these exact reads is required before this call.
    """
    if (type(max_seconds) not in (int, float) or not .1 <= max_seconds <= 60
            or not math.isfinite(max_seconds) or not callable(cancelled)):
        raise ContextError('INPUT_INVALID')
    if sys.platform != 'darwin':
        raise ContextError('UNSUPPORTED_PLATFORM')
    started = time.monotonic()
    deadline = started + max_seconds
    _guard(cancelled, deadline)
    try:
        api = _MacAPI()
        first = api.read()
        _validate_identity(first)
        _guard(cancelled, deadline)
        runtime_error = None
        diagnostic = None
        try:
            screen = _runtime().screen
        except ContextError as error:
            # Only this known restrictive screen failure can degrade metadata.
            # Permission, cancellation, unknown API and identity errors cannot.
            if str(error) != 'RUNTIME_PATH_INVALID':
                raise
            screen = 'blocked_path_invalid'
            runtime_error = 'RUNTIME_PATH_INVALID'
            diagnostic = path_diagnostic(error)
        _guard(cancelled, deadline)
        second = api.read()
        _validate_identity(second)
        if first != second:
            raise ContextError('CONTEXT_CHANGED')
        _guard(cancelled, deadline)
        if time.monotonic() < started:
            raise ContextError('CONTEXT_EXPIRED')
        result = _summary(screen)
        result.update(observation_state='partial' if runtime_error else 'observed',
                      runtime_path_error=runtime_error,
                      runtime_path_continuity='not_established',
                      observation_kind='metadata_only_no_handle')
        if diagnostic is not None:
            result['runtime_path_diagnostic'] = diagnostic
        return result
    except ContextError:
        raise
    except PermissionError:
        raise ContextError('PERMISSION_DENIED') from None
    except (OSError, AttributeError, ValueError, TypeError):
        raise ContextError('CONTEXT_UNKNOWN') from None
