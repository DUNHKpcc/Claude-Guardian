"""Conservative Windows read-only exact-file plans; mutations unsupported.

Requires an explicitly authorized exact read and host-enforced exclusive access.
Uses local volume-GUID paths and NTFS only; rejects drive-letter/UNC/device paths,
reparse/offline/recall/unknown attributes, multiple hard links and alternate
streams. Every ancestor and the file remain open without write/delete sharing.
Share flags do not prevent every ACL/attribute change: the trusted host must
exclude these too. Not a boundary against a malicious caller/administrator.
Owner/group/DACL hashes are inspected, not used as a backup privacy guarantee.
SACL, EAs and other metadata are incomplete; no mutation or recovery is enabled.
Timeouts/cancellation are cooperative between synchronous calls, not hard deadlines.
The host must enforce a hard wall-clock limit in an isolated worker process for
blocked filesystem APIs; bounded bytes cannot bound a blocking ReadFile/open.
No raw bytes or security descriptor are returned. Plans are private because they
contain exact paths. The approval callback is a host assertion, never consent
proof. apply/verify/rollback fail before callbacks or I/O on every platform.

Remaining write design: protected backup DACL at creation, verified byte and
metadata backup, full preservation/rejection policy, exact-plan/target/hash and
backup-destination approval immediately before commit, replacement with exclusive
access retained or host exclusion, durable recovery manifest and fresh approved
conflict-safe rollback. Prepared-only recovery must not be blindly replayed.
No POSIX chmod, shell execution, privilege changes or installed dependencies.

Primary API references (read-only implementation; native validation pending):
https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createfilew
https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-getfileinformationbyhandleex
https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-getkernelobjectsecurity
https://learn.microsoft.com/en-us/windows/win32/fileio/naming-a-volume
https://learn.microsoft.com/en-us/windows/win32/fileio/file-attribute-constants
"""

import ctypes
import hashlib
import json
import math
import os
import re
import struct
import sys
import time
import uuid
from contextlib import contextmanager

__all__ = ['TransactionError', 'capabilities', 'plan', 'preview', 'apply',
           'verify', 'rollback', 'digest']

_OPERATIONS = ('plan', 'preview', 'apply', 'verify', 'rollback')
_GAPS = (
    'NATIVE_ANCESTOR_REPARSE_RECALL_VALIDATION',
    'EXCLUSIVE_WRITER_AND_RENAME_PROTOCOL',
    'PRIVATE_BACKUP_SECURITY_DESCRIPTOR',
    'ORIGINAL_METADATA_AND_SECURITY_PRESERVATION',
    'LIVE_EXACT_PLAN_TARGET_HASH_APPROVAL',
    'ATOMIC_COMMIT_AND_PARTIAL_FAILURE_RECOVERY',
    'CONFLICT_SAFE_AUTHORIZED_ROLLBACK',
    'NATIVE_WINDOWS_TRANSACTION_VALIDATION',
)


class TransactionError(Exception):
    """Stable non-secret failure, compatible with the common error attributes."""

    def __init__(self, code, recovery_id=None):
        super().__init__(code)
        self.code = code
        self.recovery_id = recovery_id


def _native_windows():
    # Describes only the Python runtime, never proves the intended target binding.
    return os.name == 'nt' and sys.platform == 'win32'


def _reason():
    return ('WINDOWS_TRANSACTION_BACKEND_UNIMPLEMENTED' if _native_windows()
            else 'PLATFORM_UNSUPPORTED')


def capabilities():
    """Return fresh, content-free operation status; does not inspect the device.

    A caller may mutate this report; it is informational and cannot enable an
    operation. No report field constitutes authorization or native acceptance.
    """
    return {
        'schema_version': 'windows-exact-file-capabilities/1',
        'runtime': 'windows' if _native_windows() else 'non_windows',
        'implementation_status': 'read_only_plan_with_unsupported_mutations',
        'native_transaction_acceptance': 'not_run',
        'target_binding': 'not_checked',
        'operations': {
            operation: {'execution_status': ('available_unvalidated' if _native_windows()
                         and operation in ('plan', 'preview') else 'blocked'),
                        'check_status': 'unknown', 'reason': ('NATIVE_ACCEPTANCE_NOT_RUN'
                         if _native_windows() and operation in ('plan', 'preview') else _reason())}
            for operation in _OPERATIONS
        },
        'required_capabilities': list(_GAPS),
        'changes': [],
        'recovery_required': False,
    }


def _unsupported():
    raise TransactionError(_reason()) from None


MAX_BYTES = 4 * 1024 * 1024
MAX_METADATA = 65536
_ALLOWED_ATTRIBUTES = 0x1 | 0x2 | 0x4 | 0x10 | 0x20 | 0x80 | 0x2000
_ROOT = re.compile(r"^\\\\\?\\Volume\{[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\}\\")


def _fail(code):
    raise TransactionError(code) from None


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _path(path):
    if type(path) is not str or len(path) > 4096:
        _fail('UNSUPPORTED_PATH')
    match = _ROOT.match(path)
    if not match:
        _fail('LOCAL_VOLUME_GUID_PATH_REQUIRED')
    parts = path[match.end():].split('\\')
    if not parts or len(parts) > 64 or any(not part or part in ('.', '..') or part[-1] in '. '
                        or any(ord(c) < 32 or c in '/:*?<>|"' for c in part)
                        for part in parts):
        _fail('UNSAFE_PATH')
    return match.group(), parts


class _Budget:
    def __init__(self, seconds, cancelled):
        if (type(seconds) not in (int, float) or not math.isfinite(seconds)
                or not 0 < seconds <= 60):
            _fail('INVALID_BUDGET')
        if cancelled is not None and not callable(cancelled):
            _fail('INVALID_CANCELLATION_CALLBACK')
        self.deadline = time.monotonic() + seconds
        self.cancelled = cancelled

    def check(self):
        if time.monotonic() >= self.deadline:
            _fail('TIMEOUT')
        if self.cancelled is not None:
            try:
                value = self.cancelled()
            except Exception:
                _fail('CANCELLATION_CHECK_FAILED')
            if type(value) is not bool:
                _fail('CANCELLATION_CHECK_FAILED')
            if value:
                _fail('CANCELLED')
        # A slow cancellation callback counts against the same budget.
        if time.monotonic() >= self.deadline:
            _fail('TIMEOUT')


class _CheckedAPI:
    """Cooperative checks; always close a just-opened handle on cancellation."""
    def __init__(self, api, checkpoint):
        self.api, self.check = api, checkpoint
        api.checkpoint = checkpoint

    def open(self, *args):
        self.check()
        handle = self.api.open(*args)
        try:
            self.check()
        except BaseException:
            self.api.close(handle)
            raise
        return handle

    def close(self, handle):
        # Cleanup must proceed even after cancellation/deadline expiry.
        self.api.close(handle)

    def __getattr__(self, name):
        def checked(*args):
            self.check()
            result = getattr(self.api, name)(*args)
            self.check()
            return result
        return checked


class _WinAPI:
    """Bounded stdlib ctypes calls; fixed system DLLs, no search-path plugins."""
    def __init__(self):
        if not _native_windows():
            _fail('PLATFORM_UNSUPPORTED')
        try:
            self.k = ctypes.WinDLL('kernel32.dll', use_last_error=True, winmode=0x800)
            self.a = ctypes.WinDLL('advapi32.dll', use_last_error=True, winmode=0x800)
            H, D, P, W = ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_wchar_p
            self._bind(self.k, 'CreateFileW', H, [W, D, D, P, D, D, H])
            self._bind(self.k, 'CloseHandle', ctypes.c_int, [H])
            self._bind(self.k, 'GetDriveTypeW', D, [W])
            self._bind(self.k, 'GetFileType', D, [H])
            self._bind(self.k, 'GetFileInformationByHandleEx', ctypes.c_int, [H, D, P, D])
            self._bind(self.k, 'ReadFile', ctypes.c_int, [H, P, D, P, P])
            self._bind(self.k, 'GetVolumeInformationByHandleW', ctypes.c_int,
                       [H, P, D, P, P, P, P, D])
            self._bind(self.a, 'GetKernelObjectSecurity', ctypes.c_int, [H, D, P, D, P])
        except (AttributeError, OSError):
            _fail('WINDOWS_API_UNAVAILABLE')

    @staticmethod
    def _bind(library, name, result, args):
        function = getattr(library, name)
        function.restype, function.argtypes = result, args

    def local_volume(self, root):
        if self.k.GetDriveTypeW(root) != 3:  # DRIVE_FIXED only
            _fail('NONLOCAL_OR_UNSUPPORTED_VOLUME')

    def open(self, path, directory, data=False):
        # READ_CONTROL + FILE_READ_ATTRIBUTES; FILE_READ_DATA only for final file.
        # OPEN_EXISTING, OPEN_REPARSE_POINT, OPEN_NO_RECALL; no write/delete sharing.
        access = 0x20080 | (1 if data else 0)
        flags = 0x00200000 | 0x00100000 | (0x02000000 if directory else 0)
        handle = self.k.CreateFileW(path, access, 1, None, 3, flags, None)
        if handle in (None, ctypes.c_void_p(-1).value):
            _fail('UNSAFE_OR_UNAVAILABLE_FILE')
        return handle

    def close(self, handle):
        if not self.k.CloseHandle(handle):
            _fail('HANDLE_CLOSE_FAILED')

    def info(self, handle, kind, size):
        buffer = ctypes.create_string_buffer(size)
        if not self.k.GetFileInformationByHandleEx(handle, kind, buffer, size):
            _fail('FILE_METADATA_UNAVAILABLE')
        return buffer.raw

    def filesystem(self, handle):
        name = ctypes.create_unicode_buffer(32)
        if not self.k.GetVolumeInformationByHandleW(handle, None, 0, None, None,
                                                     None, name, len(name)):
            _fail('VOLUME_METADATA_UNAVAILABLE')
        if name.value != 'NTFS':
            _fail('FILESYSTEM_UNSUPPORTED')

    def metadata(self, handle, directory):
        if self.k.GetFileType(handle) != 1:  # FILE_TYPE_DISK
            _fail('UNSUPPORTED_FILE_TYPE')
        attributes, tag = struct.unpack('<II', self.info(handle, 9, 8))
        if tag or attributes & ~_ALLOWED_ATTRIBUTES:
            _fail('REPARSE_RECALL_OR_METADATA_UNSUPPORTED')
        if bool(attributes & 0x10) != directory:
            _fail('UNSUPPORTED_FILE_TYPE')
        allocation, size, links, pending, is_directory = struct.unpack(
            '<qqIBB', self.info(handle, 1, 24)[:22])
        if pending or bool(is_directory) != directory or (not directory and links != 1):
            _fail('UNSUPPORTED_LINK_OR_DELETE_STATE')
        if not directory and not 0 <= size <= MAX_BYTES:
            _fail('UNSUPPORTED_FILE_SIZE')
        identity = self.info(handle, 18, 24)
        basic = self.info(handle, 0, 40)
        times = struct.unpack('<qqqqI', basic[:36])
        return {'volume_serial': struct.unpack('<Q', identity[:8])[0],
                'file_id': identity[8:].hex(), 'attributes': attributes,
                'size': size, 'links': links, 'creation_time': times[0],
                'access_time': times[1], 'write_time': times[2],
                'change_time': times[3]}

    def security(self, handle):
        # Explicit owner/group/DACL only; no SACL privilege escalation.
        buffer = ctypes.create_string_buffer(MAX_METADATA)
        needed = ctypes.c_uint32()
        if not self.a.GetKernelObjectSecurity(handle, 7, buffer, len(buffer),
                                             ctypes.byref(needed)):
            _fail('SECURITY_METADATA_UNAVAILABLE')
        if not 20 <= needed.value <= MAX_METADATA:
            _fail('SECURITY_METADATA_UNAVAILABLE')
        return _hash(buffer.raw[:needed.value])

    def streams(self, handle, size):
        data = self.info(handle, 7, MAX_METADATA)
        next_offset, length, stream_size, allocation = struct.unpack('<IIqq', data[:24])
        # Only the unnamed data stream; never read or report ADS names/contents.
        if (next_offset != 0 or length != 14 or stream_size != size
                or data[24:38] != '::$DATA'.encode('utf-16-le')):
            _fail('ALTERNATE_OR_UNKNOWN_STREAMS_UNSUPPORTED')

    def read(self, handle):
        checkpoint = getattr(self, 'checkpoint', lambda: None)
        chunks, total = [], 0
        while total <= MAX_BYTES:
            checkpoint()
            size = min(65536, MAX_BYTES + 1 - total)
            buffer, got = ctypes.create_string_buffer(size), ctypes.c_uint32()
            if not self.k.ReadFile(handle, buffer, size, ctypes.byref(got), None):
                _fail('READ_FAILED')
            checkpoint()
            if got.value > size:
                _fail('READ_FAILED')
            if not got.value:
                return b''.join(chunks)
            chunks.append(buffer.raw[:got.value])
            total += got.value
        _fail('UNSUPPORTED_FILE_SIZE')


@contextmanager
def _opened(api, path, directory, data=False):
    handle = api.open(path, directory, data)
    try:
        yield handle
    finally:
        api.close(handle)


def _read_snapshot(path, checkpoint):
    from contextlib import ExitStack
    root, parts = _path(path)
    checkpoint()
    api = _CheckedAPI(_WinAPI(), checkpoint)
    api.local_volume(root)
    with ExitStack() as stack:
        ancestors = []
        prefix = root
        for part in [None] + parts[:-1]:
            if part is not None:
                prefix += part + '\\'
            handle = stack.enter_context(_opened(api, prefix, True))
            state = api.metadata(handle, True)
            if not ancestors:
                api.filesystem(handle)
            ancestors.append((handle, state))
        handle = stack.enter_context(_opened(api, path, False))
        before = api.metadata(handle, False)
        api.streams(handle, before['size'])
        security = api.security(handle)
        read_handle = stack.enter_context(_opened(api, path, False, True))
        if api.metadata(read_handle, False) != before:
            _fail('CONCURRENT_CHANGE')
        data = api.read(read_handle)
        after = api.metadata(handle, False)
        if (before != after or len(data) != after['size']
                or api.security(handle) != security):
            _fail('CONCURRENT_CHANGE')
        for ancestor, state in ancestors:
            if api.metadata(ancestor, True) != state:
                _fail('ANCESTOR_CHANGED')
        return {'sha256': _hash(data), **after,
                'security_sha256': security,
                'security_scope': 'owner_group_dacl_only',
                'ancestors': [state for _, state in ancestors]}


def digest(document):
    """Hash this adapter's validated plan; never an authorization credential."""
    _validate(document)
    return _hash(json.dumps(document, sort_keys=True, separators=(',', ':'),
                            ensure_ascii=True, allow_nan=False).encode())


def plan(path, proposed, target_ref, *, ttl_seconds=600, now=None,
         exclusive_access=False, cancelled=None, budget_seconds=10):
    """Read exactly one existing NTFS file under a trusted host's exclusion.

    Caller authorizes the exact read separately. exclusive_access asserts the
    host excludes changes including metadata/ACL/volume mappings during this
    read; Windows share flags do not exclude every metadata change. No consent
    is inferred. This produces an inapplicable diagnostic plan, not permission
    or a promise that replacement preserves all metadata. No bytes are stored.
    """
    if not _native_windows():
        _fail('PLATFORM_UNSUPPORTED')
    if exclusive_access is not True:
        _fail('EXCLUSIVE_ACCESS_REQUIRED')
    _path(path)
    if type(proposed) is not bytes or len(proposed) > MAX_BYTES:
        _fail('INVALID_PROPOSED_BYTES')
    if type(target_ref) is not str or not 0 < len(target_ref) <= 200:
        _fail('INVALID_TARGET')
    now = time.time() if now is None else now
    if (type(ttl_seconds) not in (int, float) or not 0 < ttl_seconds <= 3600
            or type(now) not in (int, float) or not math.isfinite(now)
            or abs(now) > 1e12):
        _fail('INVALID_EXPIRY')
    budget = _Budget(budget_seconds, cancelled)
    budget.check()
    snapshot = _read_snapshot(path, budget.check)
    budget.check()
    return {'schema_version': 'windows-read-only-file-plan/1',
            'action_id': uuid.uuid4().hex, 'operation': 'replace_existing_file',
            'target_ref': target_ref, 'path': path, 'before': snapshot,
            'after_sha256': _hash(proposed), 'after_size': len(proposed),
            'created_at': now, 'expires_at': now + ttl_seconds,
            'apply_status': 'unsupported', 'metadata_completeness': 'partial',
            'gaps': list(_GAPS)}


def _validate(p):
    # Diagnostic plan validation is bounded and does not imply replay safety.
    if type(p) is not dict or set(p) != {
            'schema_version', 'action_id', 'operation', 'target_ref', 'path',
            'before', 'after_sha256', 'after_size', 'created_at', 'expires_at',
            'apply_status', 'metadata_completeness', 'gaps'}:
        _fail('INVALID_PLAN')
    budget = [4096, MAX_METADATA]
    def bounded(value, depth=0):
        budget[0] -= 1
        if depth > 8 or budget[0] < 0:
            _fail('INVALID_PLAN')
        if type(value) is str:
            budget[1] -= len(value)
            if len(value) > 4096 or budget[1] < 0:
                _fail('INVALID_PLAN')
        elif type(value) is dict:
            if len(value) > 64:
                _fail('INVALID_PLAN')
            for key, item in value.items():
                if type(key) is not str:
                    _fail('INVALID_PLAN')
                bounded(key, depth + 1)
                bounded(item, depth + 1)
        elif type(value) is list:
            if len(value) > 64:
                _fail('INVALID_PLAN')
            for item in value:
                bounded(item, depth + 1)
        elif type(value) not in (int, float, bool, type(None)):
            _fail('INVALID_PLAN')
    bounded(p)
    try:
        raw = json.dumps(p, allow_nan=False)
        if len(raw) > MAX_METADATA:
            _fail('INVALID_PLAN')
    except (ValueError, TypeError, RecursionError, OverflowError):
        _fail('INVALID_PLAN')
    if (p['schema_version'] != 'windows-read-only-file-plan/1'
            or p['operation'] != 'replace_existing_file'
            or p['apply_status'] != 'unsupported'
            or p['metadata_completeness'] != 'partial' or p['gaps'] != list(_GAPS)
            or type(p['before']) is not dict):
        _fail('INVALID_PLAN')
    _path(p['path'])
    if (type(p['action_id']) is not str or not re.fullmatch('[0-9a-f]{32}', p['action_id'])
            or type(p['target_ref']) is not str or not 0 < len(p['target_ref']) <= 200):
        _fail('INVALID_PLAN')
    state_fields = {'volume_serial', 'file_id', 'attributes', 'size', 'links',
                    'creation_time', 'access_time', 'write_time', 'change_time'}
    if set(p['before']) != state_fields | {'sha256', 'security_sha256',
                                           'security_scope', 'ancestors'}:
        _fail('INVALID_PLAN')
    ancestors = p['before']['ancestors']
    if (type(ancestors) is not list or not 1 <= len(ancestors) <= 64
            or p['before']['security_scope'] != 'owner_group_dacl_only'):
        _fail('INVALID_PLAN')
    for state in [p['before']] + ancestors:
        if type(state) is not dict or not state_fields <= set(state):
            _fail('INVALID_PLAN')
        if state is not p['before'] and set(state) != state_fields:
            _fail('INVALID_PLAN')
        if type(state['file_id']) is not str or not re.fullmatch('[0-9a-f]{32}', state['file_id']):
            _fail('INVALID_PLAN')
        for field in state_fields - {'file_id'}:
            if type(state[field]) is not int or abs(state[field]) > 2**64:
                _fail('INVALID_PLAN')
    security = p['before']['security_sha256']
    if type(security) is not str or not re.fullmatch('[0-9a-f]{64}', security):
        _fail('INVALID_PLAN')
    for value in (p['after_sha256'], p['before'].get('sha256')):
        if type(value) is not str or not re.fullmatch('[0-9a-f]{64}', value):
            _fail('INVALID_PLAN')
    for value in (p['after_size'], p['before'].get('size')):
        if type(value) is not int or not 0 <= value <= MAX_BYTES:
            _fail('INVALID_PLAN')
    for value in (p['created_at'], p['expires_at']):
        if type(value) not in (int, float) or not math.isfinite(value):
            _fail('INVALID_PLAN')
    if not 0 < p['expires_at'] - p['created_at'] <= 3600:
        _fail('INVALID_PLAN')


def preview(p):
    """Content/path-free diagnostic comparison; apply stays unsupported."""
    _validate(p)
    if not p['created_at'] <= time.time() < p['expires_at']:
        _fail('INVALID_OR_EXPIRED_PLAN')
    return {'plan_digest': digest(p), 'before_sha256': p['before']['sha256'],
            'after_sha256': p['after_sha256'], 'before_size': p['before']['size'],
            'after_size': p['after_size'],
            'changed': p['before']['sha256'] != p['after_sha256'],
            'apply_status': 'unsupported', 'metadata_completeness': 'partial',
            'verification_scope': 'diagnostic_exact_file_snapshot_only'}


def apply(p, *, target_ref, backup_directory, authorize=None,
          exclusive_access=False):
    """Unsupported even with approval; no callback, backup or mutation occurs."""
    _unsupported()


def verify(recovery):
    """Unsupported: never return pass for uninspected bytes or metadata."""
    _unsupported()


def rollback(recovery, *, target_ref, authorize=None, exclusive_access=False):
    """Unsupported: never replay a POSIX/caller receipt against Windows paths."""
    _unsupported()
