"""Narrow offline exact-file transactions; not a native configuration adapter.

No CLI permission switch proves consent. The trusted host must verify the actual
user approval, target binding, permissions and exclusive-access boundary, then
supply authorize(operation, digest, target_ref) -> True. It is called again just
before commit to permit cancellation. Returning True is a host assertion, not
cryptographic evidence of consent. A malicious caller already has Python/file
access; this module is not a security boundary against that caller.

Only existing, single-link regular files on POSIX with descriptor-relative,
no-follow operations are supported. No creation/deletion, directory cleanup,
registry, keychain, native system setting, network request or shell execution.
Host must exclude concurrent writers for the whole operation: POSIX rename is
atomic but is not compare-and-swap. Advisory locks alone cannot guarantee this.
Multi-file atomicity, crash recovery of application state, ACL/xattr preservation
and application-effective verification are not claimed. The file owner/group
must equal the executing effective user/group; other ownership is rejected. Files with xattrs are
rejected. Backups and recovery manifests are never automatically deleted.

Plans contain private replacement bytes. Do not log/serialize plans into public
reports. preview() emits only hashes/lengths; it never emits content or paths.
"""
import base64
import ctypes
import hashlib
import json
import math
import os
import stat
import sys
import time
import uuid
from contextlib import contextmanager

MAX_BYTES = 4 * 1024 * 1024
MAX_BASE64 = 4 * ((MAX_BYTES + 2) // 3)
MAX_DOCUMENT = MAX_BASE64 + 32768


class TransactionError(Exception):
    """Stable non-secret error code, with optional recovery identifier."""

    def __init__(self, code, recovery_id=None):
        super().__init__(code)
        self.code = code
        self.recovery_id = recovery_id


def _fail(code):
    raise TransactionError(code) from None


def _hash(data):
    return hashlib.sha256(data).hexdigest()


def _bounded_document(document):
    """Accept bounded plain JSON data before serialization; never echo payloads."""
    budget = [256, MAX_DOCUMENT]
    def visit(value, depth):
        budget[0] -= 1
        if depth > 8 or budget[0] < 0:
            _fail('INVALID_DOCUMENT')
        if type(value) is str:
            budget[1] -= len(value)
            if budget[1] < 0:
                _fail('INVALID_DOCUMENT')
        elif type(value) is dict:
            if len(value) > 64:
                _fail('INVALID_DOCUMENT')
            for key, item in value.items():
                if type(key) is not str:
                    _fail('INVALID_DOCUMENT')
                visit(key, depth + 1)
                visit(item, depth + 1)
        elif type(value) is list:
            if len(value) > 64:
                _fail('INVALID_DOCUMENT')
            for item in value:
                visit(item, depth + 1)
        elif type(value) is int:
            if abs(value) > 2**64:
                _fail('INVALID_DOCUMENT')
        elif type(value) is float:
            if not math.isfinite(value):
                _fail('INVALID_DOCUMENT')
        elif value is not None and type(value) is not bool:
            _fail('INVALID_DOCUMENT')
    visit(document, 0)


def digest(document):
    """Digest bounded plain JSON data; digest validity does not prove consent."""
    _bounded_document(document)
    try:
        encoded = json.dumps(document, sort_keys=True, separators=(',', ':'),
                             ensure_ascii=True, allow_nan=False).encode()
        if len(encoded) > MAX_DOCUMENT:
            _fail('INVALID_DOCUMENT')
        return _hash(encoded)
    except (ValueError, TypeError, RecursionError, OverflowError):
        _fail('INVALID_DOCUMENT')


def _copy(document):
    digest(document)
    return json.loads(json.dumps(document, allow_nan=False))


def _hex(value, length):
    return (type(value) is str and len(value) == length
            and all(c in '0123456789abcdef' for c in value))


def _snapshot(value):
    fields = {'sha256', 'size', 'mode', 'uid', 'gid', 'device', 'inode',
              'mtime_ns', 'ctime_ns'}
    if type(value) is not dict or set(value) != fields or not _hex(value['sha256'], 64):
        _fail('INVALID_SNAPSHOT')
    for key in fields - {'sha256'}:
        if type(value[key]) is not int or abs(value[key]) > 2**64:
            _fail('INVALID_SNAPSHOT')
        if key not in ('mtime_ns', 'ctime_ns') and value[key] < 0:
            _fail('INVALID_SNAPSHOT')
    if value['size'] > MAX_BYTES or value['mode'] > 0o777:
        _fail('INVALID_SNAPSHOT')


def _path(value):
    # Do not normalize, expand variables/home markers, resolve or glob paths.
    if type(value) is not str or len(value) > 4096 or not value.startswith('/'):
        _fail('UNSAFE_PATH')
    parts = value.split('/')[1:]
    if not parts or any(p in ('', '.', '..') for p in parts):
        _fail('UNSAFE_PATH')
    if any(c in value for c in ('\x00', '\\', '~', '$', '*', '?', '[', ']')):
        _fail('UNSAFE_PATH')
    return parts


def _support():
    if (os.name != 'posix' or not hasattr(os, 'O_NOFOLLOW')
            or not hasattr(os, 'O_DIRECTORY') or os.open not in os.supports_dir_fd
            or (sys.platform != 'darwin' and not callable(getattr(os, 'listxattr', None)))):
        _fail('PLATFORM_UNSUPPORTED')


def _has_xattrs(fd):
    """Inspect the already-open file, with no pathname fallback or value reads.

    Darwin ABI verified against Apple's xnu/bsd/sys/xattr.h and flistxattr(2):
    https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/xattr.h
    https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flistxattr.2.html
    A NULL buffer requests only the required size; no untrusted-size allocation,
    retries, names or attribute values. XATTR_SHOWCOMPRESSION includes compression
    metadata normally hidden from the list. Any failure blocks the transaction.
    Listing observes attributes accessible to the current execution identity.
    """
    if type(fd) is not int or not 0 <= fd <= 2**31 - 1:
        _fail('XATTR_CHECK_FAILED')
    if sys.platform == 'darwin':
        try:
            # Fixed trusted OS library, never find_library/search-path resolution.
            library = ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
            query = library.flistxattr
            query.argtypes = [ctypes.c_int, ctypes.c_void_p, ctypes.c_size_t, ctypes.c_int]
            query.restype = ctypes.c_ssize_t
            size = query(fd, None, 0, 0x0020)  # XATTR_SHOWCOMPRESSION
        except (OSError, AttributeError, TypeError, ValueError):
            _fail('XATTR_CHECK_FAILED')
        if type(size) is not int or not 0 <= size <= 2**(ctypes.sizeof(ctypes.c_ssize_t) * 8 - 1) - 1:
            _fail('XATTR_CHECK_FAILED')
        return size > 0
    try:
        # CPython's supported fd form on Linux; never convert fd back to a path.
        return bool(os.listxattr(fd))
    except (OSError, AttributeError, TypeError, ValueError):
        _fail('XATTR_CHECK_FAILED')


@contextmanager
def _directory(path):
    _support()
    parts = _path(path)
    fd = None
    try:
        try:
            fd = os.open('/', os.O_RDONLY | os.O_DIRECTORY)
            for part in parts:
                next_fd = os.open(part, os.O_RDONLY | os.O_DIRECTORY | os.O_NOFOLLOW,
                                  dir_fd=fd)
                os.close(fd)
                fd = next_fd
        except OSError:
            _fail('UNSAFE_OR_UNAVAILABLE_DIRECTORY')
        yield fd
    finally:
        if fd is not None:
            os.close(fd)


@contextmanager
def _parent(path):
    parts = _path(path)
    if len(parts) < 2:
        _fail('ROOT_TARGET_UNSUPPORTED')
    with _directory('/' + '/'.join(parts[:-1])) as fd:
        yield fd, parts[-1]


def _identity(fd):
    s = os.fstat(fd)
    return [s.st_dev, s.st_ino]


def _read(fd, name):
    f = None
    try:
        f = os.open(name, os.O_RDONLY | os.O_NOFOLLOW | os.O_NONBLOCK, dir_fd=fd)
        s = os.fstat(f)
        if not stat.S_ISREG(s.st_mode) or s.st_nlink != 1:
            _fail('UNSUPPORTED_FILE_TYPE')
        if (s.st_size > MAX_BYTES or s.st_uid != os.geteuid()
                or s.st_gid != os.getegid()):
            _fail('UNSUPPORTED_FILE_SIZE_OR_OWNER')
        if stat.S_IMODE(s.st_mode) & 0o7000 or _has_xattrs(f):
            _fail('UNSUPPORTED_FILE_METADATA')
        data = bytearray()
        while len(data) <= MAX_BYTES:
            block = os.read(f, min(65536, MAX_BYTES + 1 - len(data)))
            if not block:
                break
            data.extend(block)
        after = os.fstat(f)
        if len(data) > MAX_BYTES:
            _fail('UNSUPPORTED_FILE_SIZE_OR_OWNER')
        if (s.st_size, s.st_mtime_ns, s.st_ctime_ns) != (
                after.st_size, after.st_mtime_ns, after.st_ctime_ns):
            _fail('CONCURRENT_CHANGE')
        return bytes(data), {'sha256': _hash(data), 'size': len(data),
                             'mode': stat.S_IMODE(s.st_mode), 'uid': s.st_uid,
                             'gid': s.st_gid, 'device': s.st_dev, 'inode': s.st_ino,
                             'mtime_ns': s.st_mtime_ns, 'ctime_ns': s.st_ctime_ns}
    except OSError:
        _fail('UNSAFE_OR_UNAVAILABLE_FILE')
    finally:
        if f is not None:
            os.close(f)


def plan(path, proposed, target_ref, *, ttl_seconds=600, now=None):
    """Read one exact file; no writes. Caller has already authorized this read."""
    if not isinstance(proposed, bytes) or len(proposed) > MAX_BYTES:
        _fail('INVALID_PROPOSED_BYTES')
    if not isinstance(target_ref, str) or not target_ref or len(target_ref) > 200:
        _fail('INVALID_TARGET')
    if type(ttl_seconds) not in (int, float) or not 0 < ttl_seconds <= 3600:
        _fail('INVALID_EXPIRY')
    now = time.time() if now is None else now
    if type(now) not in (int, float) or abs(now) > 1e12 or not math.isfinite(now):
        _fail('INVALID_EXPIRY')
    with _parent(path) as (fd, name):
        before, snapshot = _read(fd, name)
        parent_identity = _identity(fd)
    return {'schema_version': 'exact-file-plan/1', 'action_id': uuid.uuid4().hex,
            'operation': 'replace_existing_file', 'target_ref': target_ref,
            'path': path, 'parent_identity': parent_identity,
            'before': snapshot, 'after_sha256': _hash(proposed),
            'proposed_base64': base64.b64encode(proposed).decode('ascii'),
            'created_at': now, 'expires_at': now + ttl_seconds}


def _validate(p, now=None):
    _bounded_document(p)
    keys = {'schema_version', 'action_id', 'operation', 'target_ref', 'path',
            'parent_identity', 'before', 'after_sha256', 'proposed_base64',
            'created_at', 'expires_at'}
    if not isinstance(p, dict) or set(p) != keys:
        _fail('INVALID_PLAN')
    if p['schema_version'] != 'exact-file-plan/1' or p['operation'] != 'replace_existing_file':
        _fail('INVALID_PLAN')
    _path(p['path'])
    _snapshot(p['before'])
    identity = p['parent_identity']
    if (not _hex(p['action_id'], 32) or not _hex(p['after_sha256'], 64)
            or type(identity) is not list or len(identity) != 2
            or any(type(n) is not int or not 0 <= n <= 2**64 for n in identity)
            or type(p['target_ref']) is not str or not 0 < len(p['target_ref']) <= 200
            or type(p['proposed_base64']) is not str
            or len(p['proposed_base64']) > MAX_BASE64):
        _fail('INVALID_PLAN')
    for key in ('created_at', 'expires_at'):
        if type(p[key]) not in (int, float) or not math.isfinite(p[key]) or abs(p[key]) > 1e12:
            _fail('INVALID_PLAN')
    try:
        proposed = base64.b64decode(p['proposed_base64'], validate=True)
    except (ValueError, TypeError):
        _fail('INVALID_PLAN')
    if (len(proposed) > MAX_BYTES or _hash(proposed) != p['after_sha256']
            or not 0 < p['expires_at'] - p['created_at'] <= 3600
            or (now is not None and not p['created_at'] <= now < p['expires_at'])):
        _fail('INVALID_OR_EXPIRED_PLAN')
    return proposed


def _recovery(document):
    # Shape checks establish data integrity only, never authorization/authenticity.
    _bounded_document(document)
    keys = {'schema_version', 'plan', 'backup_directory', 'batch', 'state',
            'applied_snapshot'}
    if type(document) is not dict or set(document) != keys:
        _fail('INVALID_RECOVERY')
    if document['schema_version'] != 'exact-file-recovery/1':
        _fail('INVALID_RECOVERY')
    if document['state'] != 'applied':
        _fail('RECOVERY_REQUIRES_RECONCILIATION')
    proposed = _validate(document['plan'])  # Recovery remains possible after plan expiry.
    _path(document['backup_directory'])
    if not _hex(document['batch'], 32):
        _fail('INVALID_RECOVERY')
    actual = document['applied_snapshot']
    _snapshot(actual)
    p = document['plan']
    if (actual['sha256'] != p['after_sha256'] or actual['size'] != len(proposed)
            or any(actual[key] != p['before'][key] for key in ('mode', 'uid', 'gid', 'device'))):
        _fail('INVALID_RECOVERY')
    return document


def preview(p):
    """Content-free diff, suitable for a non-secret report.

Host must separately present a vetted/redacted semantic diff to the user.
Arbitrary content cannot be safely automatically redacted by this library.
"""
    proposed = _validate(p, time.time())
    return {'plan_digest': digest(p), 'before_sha256': p['before']['sha256'],
            'after_sha256': _hash(proposed), 'before_size': p['before']['size'],
            'after_size': len(proposed), 'changed': p['before']['sha256'] != _hash(proposed),
            'verification_scope': 'exact_file_bytes_only'}


def _authorize(callback, operation, document, target_ref):
    if not callable(callback):
        _fail('AUTHORIZATION_REQUIRED')
    try:
        accepted = callback(operation, digest(document), target_ref)
    except Exception:
        _fail('AUTHORIZATION_CANCELLED')
    if accepted is not True:
        _fail('AUTHORIZATION_DENIED')


def _write(fd, name, data, mode=0o600):
    f = os.open(name, os.O_WRONLY | os.O_CREAT | os.O_EXCL | os.O_NOFOLLOW,
                0o600, dir_fd=fd)
    try:
        view = memoryview(data)
        while view:
            n = os.write(f, view)
            if n <= 0:
                _fail('WRITE_FAILED')
            view = view[n:]
        os.fchmod(f, mode)
        os.fsync(f)
    finally:
        os.close(f)
    os.fsync(fd)


def _check_parent(path, expected):
    with _parent(path) as (fd, _):
        if _identity(fd) != expected:
            _fail('PARENT_CHANGED')


def _replace(fd, name, data, snapshot, path, parent_identity, before_commit):
    staging = '.guardian-stage-' + uuid.uuid4().hex
    try:
        _write(fd, staging, data, snapshot['mode'])
        if _read(fd, staging)[0] != data:
            _fail('STAGING_VERIFY_FAILED')
        before_commit()
        _check_parent(path, parent_identity)
        if _read(fd, name)[1] != snapshot:
            _fail('STALE_FILE')
        os.replace(staging, name, src_dir_fd=fd, dst_dir_fd=fd)
        os.fsync(fd)
        _check_parent(path, parent_identity)
        actual, state = _read(fd, name)
        if actual != data or state['mode'] != snapshot['mode']:
            _fail('POST_WRITE_VERIFY_FAILED')
        return state
    finally:
        try:
            os.unlink(staging, dir_fd=fd)
        except FileNotFoundError:
            pass


def apply(p, *, target_ref, backup_directory, authorize=None,
          exclusive_access=False):
    """Apply one plan; backup_directory must already be private and authorized.

exclusive_access=True asserts host-enforced writer exclusion, not consent.
Backup location is part of the authorization document alongside the entire plan.
On failure recovery_id identifies the retained private recovery batch, if made.
"""
    # Snapshot caller-owned mutable data before any callback or I/O.
    p = _copy(p)
    proposed = _validate(p, time.time())
    if target_ref != p['target_ref']:
        _fail('TARGET_MISMATCH')
    if exclusive_access is not True:
        _fail('EXCLUSIVE_ACCESS_REQUIRED')
    _path(backup_directory)
    authorization = {'plan': p, 'backup_directory': backup_directory}
    _authorize(authorize, 'apply', authorization, target_ref)
    batch = None
    try:
        with _parent(p['path']) as (fd, name), _directory(backup_directory) as backup_fd:
            s = os.fstat(backup_fd)
            if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) != 0o700:
                _fail('BACKUP_DIRECTORY_NOT_PRIVATE')
            if _identity(fd) != p['parent_identity']:
                _fail('PARENT_CHANGED')
            original, snapshot = _read(fd, name)
            if snapshot != p['before']:
                _fail('STALE_FILE')
            batch = uuid.uuid4().hex
            os.mkdir(batch, 0o700, dir_fd=backup_fd)
            os.fsync(backup_fd)
            batch_path = backup_directory + '/' + batch
            with _directory(batch_path) as recovery_fd:
                _write(recovery_fd, 'original.bin', original)
                if _read(recovery_fd, 'original.bin')[0] != original:
                    _fail('BACKUP_VERIFY_FAILED')
                recovery = {'schema_version': 'exact-file-recovery/1', 'plan': p,
                            'backup_directory': backup_directory, 'batch': batch,
                            'state': 'prepared', 'applied_snapshot': None}
                _write(recovery_fd, 'prepared.json', json.dumps(recovery, sort_keys=True).encode())
                def confirm():
                    _validate(p, time.time())
                    _authorize(authorize, 'apply', authorization, target_ref)
                    _validate(p, time.time())
                applied = _replace(fd, name, proposed, snapshot, p['path'],
                                   p['parent_identity'], confirm)
                recovery['state'] = 'applied'
                recovery['applied_snapshot'] = applied
                _write(recovery_fd, 'applied.json', json.dumps(recovery, sort_keys=True).encode())
                return recovery
    except (OSError, TransactionError) as exc:
        code = exc.code if isinstance(exc, TransactionError) else 'IO_FAILURE'
        raise TransactionError(code, batch) from None


def verify(recovery):
    """Verify bytes and file identity only, never application/network behavior."""
    recovery = _copy(_recovery(recovery))
    p = recovery['plan']
    with _parent(p['path']) as (fd, name):
        actual, snapshot = _read(fd, name)
        matched = (_identity(fd) == p['parent_identity'] and
                   snapshot == recovery['applied_snapshot'] and
                   _hash(actual) == p['after_sha256'])
    return {'check_status': 'pass' if matched else 'fail',
            'verification_scope': 'exact_file_bytes_only',
            'application_effect': 'not_tested', 'network_effect': 'not_tested'}


def rollback(recovery, *, target_ref, authorize=None, exclusive_access=False):
    """Restore only an applied receipt, after a fresh rollback authorization.

A prepared-only crash record needs manual reconciliation, never blind replay.
The host must obtain the receipt from its trusted retained private store.
"""
    recovery = _copy(_recovery(recovery))
    p = recovery['plan']
    if p['target_ref'] != target_ref:
        _fail('TARGET_MISMATCH')
    if exclusive_access is not True:
        _fail('EXCLUSIVE_ACCESS_REQUIRED')
    _authorize(authorize, 'rollback', recovery, target_ref)
    batch = recovery['batch']
    if not isinstance(batch, str) or len(batch) != 32 or any(c not in '0123456789abcdef' for c in batch):
        _fail('INVALID_RECOVERY')
    with _directory(recovery['backup_directory'] + '/' + batch) as bfd:
        s = os.fstat(bfd)
        if s.st_uid != os.geteuid() or stat.S_IMODE(s.st_mode) != 0o700:
            _fail('BACKUP_DIRECTORY_NOT_PRIVATE')
        original, _ = _read(bfd, 'original.bin')
        if _hash(original) != p['before']['sha256']:
            _fail('BACKUP_CORRUPT')
        with _parent(p['path']) as (fd, name):
            if _identity(fd) != p['parent_identity']:
                _fail('PARENT_CHANGED')
            current, snapshot = _read(fd, name)
            if snapshot != recovery['applied_snapshot'] or _hash(current) != p['after_sha256']:
                _fail('ROLLBACK_CONFLICT')
            restored = _replace(fd, name, original, snapshot, p['path'],
                                p['parent_identity'],
                                lambda: _authorize(authorize, 'rollback', recovery, target_ref))
            result = {'schema_version': 'exact-file-rollback/1', 'state': 'restored',
                      'recovery_digest': digest(recovery), 'restored_snapshot': restored,
                      'verification_scope': 'exact_file_bytes_only'}
            _write(bfd, 'rollback-' + uuid.uuid4().hex + '.json',
                   json.dumps(result, sort_keys=True).encode())
            return result
