"""Internal Darwin metadata guard for an already-open private document pair.

No existing CLI uses this capability. Native validation is pending. The caller
authorizes and opens the exact file/parent, binds their pathname relationship,
keeps both descriptors alive, and bounds/parses any content read itself. This
module opens no paths, reads no content/xattr values or ACL principals, and
changes no object. Local/VM/VPS callers share this core, binding actual scope
and capabilities separately; a route name does not make a non-Darwin host valid.

The context manager yields None, never a reusable admission token. Repeated
metadata/stat observations are not atomicity, writer exclusion, complete xattr
visibility, runtime integrity, authenticity, or permission to write. Native
calls may block: bounded call counts do not promise a hard I/O deadline.
"""
from contextlib import contextmanager
import ctypes
import errno
import os
import stat
import sys

import macos_metadata_observer as metadata_names


MAX_DOCUMENT_BYTES = 4 * ((4 * 1024 * 1024 + 2) // 3) + 32768
_LIBSYSTEM = '/usr/lib/libSystem.B.dylib'
_ACL_TYPE_EXTENDED = 0x100
_ACL_FIRST_ENTRY = 0
_ALLOWED_NAMES = frozenset((b'com.apple.provenance',))
_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid', 'st_gid',
           'st_size', 'st_mtime_ns', 'st_ctime_ns', 'st_flags')
_NAME_ERRORS = frozenset((
    'INVALID_DESCRIPTOR', 'NAME_LIST_DENIED', 'NAME_LIST_UNSUPPORTED',
    'NAME_LIST_CHANGED', 'NAME_LIST_FAILED', 'NATIVE_RESULT_INVALID',
    'NAME_LIST_BOUNDS', 'NAME_LIST_MALFORMED', 'NATIVE_BACKEND_UNAVAILABLE'))


class PrivateReadError(Exception):
    """Fixed non-secret code; no native error text or metadata payload."""

    def __init__(self, code):
        super().__init__(code)
        self.code = code


def _fail(code):
    raise PrivateReadError(code) from None


def _checked(function, *args):
    """Sanitize only our metadata operations, never a caller's read exception."""
    try:
        return function(*args)
    except PrivateReadError:
        raise
    except metadata_names._Failure as error:
        code = error.args[0] if len(error.args) == 1 else None
        _fail(code if type(code) is str and code in _NAME_ERRORS else 'NAME_LIST_FAILED')
    except KeyboardInterrupt:
        _fail('CANCELLED')
    except Exception:
        _fail('PRIVATE_READ_FAILED')


def _descriptor(fd):
    if type(fd) is not int or not 0 <= fd <= 2**31 - 1:
        _fail('INVALID_DESCRIPTOR')


def _identity():
    if sys.platform != 'darwin':
        _fail('UNSUPPORTED_PLATFORM')
    if not all(callable(getattr(os, key, None)) for key in ('fstat', 'geteuid', 'getegid')):
        _fail('DESCRIPTOR_API_UNAVAILABLE')
    pair = (os.geteuid(), os.getegid())
    if any(type(value) is not int or not 0 <= value <= 2**32 - 1 for value in pair):
        _fail('CALLER_IDENTITY_UNAVAILABLE')
    return pair


def _snapshot(fd, identity):
    try:
        info = os.fstat(fd)
    except OSError as error:
        if error.errno == errno.EBADF:
            _fail('INVALID_DESCRIPTOR')
        if error.errno in (errno.EACCES, errno.EPERM):
            _fail('DESCRIPTOR_STAT_DENIED')
        _fail('DESCRIPTOR_STAT_FAILED')
    values = tuple(getattr(info, key, None) for key in _FIELDS)
    for key, value in zip(_FIELDS, values):
        if (type(value) is not int or abs(value) > 2**64
                or (key not in ('st_mtime_ns', 'st_ctime_ns') and value < 0)):
            _fail('DESCRIPTOR_STAT_INVALID')
    if info.st_flags > 2**32 - 1 or info.st_nlink < 1:
        _fail('DESCRIPTOR_STAT_INVALID')
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        _fail('OBJECT_TYPE_UNSUPPORTED')
    if (info.st_uid, info.st_gid) != identity:
        _fail('OBJECT_NOT_OWNED')
    return values


def _acl_error(number):
    if number == errno.EBADF:
        _fail('INVALID_DESCRIPTOR')
    if number in (errno.EACCES, errno.EPERM):
        _fail('ACL_READ_DENIED')
    if number in (errno.ENOTSUP, errno.EOPNOTSUPP):
        _fail('ACL_READ_UNSUPPORTED')
    _fail('ACL_READ_FAILED')


class _DarwinACL:
    """First-entry observation only; Darwin return semantics are not POSIX/Linux.

    Apple primary sources for constants, signatures and absent/empty handling:
    https://github.com/apple-oss-distributions/Libc/blob/main/include/sys/acl.h
    https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_file.c
    https://github.com/apple-oss-distributions/Libc/blob/main/posix1e/acl_entry.c
    https://github.com/apple-oss-distributions/Libc/blob/main/gen/filesec.c
    https://github.com/apple-oss-distributions/Libc/blob/main/sys/statx_np.c
    """

    def __init__(self):
        try:
            self._library = ctypes.CDLL(_LIBSYSTEM, use_errno=True)
            def bind(name, result, *arguments):
                function = getattr(self._library, name)
                function.argtypes, function.restype = list(arguments), result
                return function
            self._get = bind('acl_get_fd_np', ctypes.c_void_p, ctypes.c_int, ctypes.c_int)
            self._valid = bind('acl_valid', ctypes.c_int, ctypes.c_void_p)
            self._entry = bind('acl_get_entry', ctypes.c_int, ctypes.c_void_p,
                               ctypes.c_int, ctypes.POINTER(ctypes.c_void_p))
            self._free = bind('acl_free', ctypes.c_int, ctypes.c_void_p)
        except (OSError, AttributeError, TypeError, ValueError):
            _fail('NATIVE_BACKEND_UNAVAILABLE')

    def state(self, fd):
        acl = None
        try:
            ctypes.set_errno(0)
            try:
                acl = self._get(fd, _ACL_TYPE_EXTENDED)
            except OSError as error:
                _acl_error(error.errno)
            number = ctypes.get_errno()
            if acl is None:
                if number == errno.ENOENT:
                    # Source-derived absent FILESEC_ACL, not proof of native support.
                    return 'no_acl_reported'
                _acl_error(number)
            if not self._pointer(acl):
                _fail('ACL_RESULT_INVALID')
            ctypes.set_errno(0)
            valid = self._valid(acl)
            if type(valid) is not int or valid != 0:
                _fail('ACL_INVALID')
            entry = ctypes.c_void_p()
            ctypes.set_errno(0)
            result = self._entry(acl, _ACL_FIRST_ENTRY, ctypes.byref(entry))
            number = ctypes.get_errno()
            if type(result) is not int:
                _fail('ACL_RESULT_INVALID')
            if result == 0 and entry.value is not None:
                return 'entries_present'
            if result == -1 and number == errno.EINVAL and entry.value is None:
                return 'empty_acl'
            _fail('ACL_RESULT_INVALID')
        finally:
            if self._pointer(acl):
                try:
                    ctypes.set_errno(0)
                    released = self._free(acl)
                except Exception:
                    _fail('ACL_RELEASE_FAILED')
                if type(released) is not int or released != 0:
                    _fail('ACL_RELEASE_FAILED')

    @staticmethod
    def _pointer(value):
        # Never dereference/free special or malformed native return sentinels.
        return (type(value) is int
                and 16 < value < 2**(8 * ctypes.sizeof(ctypes.c_void_p)) - 16)


def _observe_acl(fd):
    _descriptor(fd)
    identity = _identity()
    before = _snapshot(fd, identity)
    state = _DarwinACL().state(fd)
    if _snapshot(fd, identity) != before:
        _fail('METADATA_CHANGED')
    if _identity() != identity:
        _fail('CALLER_IDENTITY_CHANGED')
    return state


def observe_acl_fd(fd):
    """Report no_acl_reported, empty_acl or entries_present on one owned fd.

    No ACL principal or text is read. This fixed label is observation, not a
    private-file or write-admission decision. Native platform testing is pending.
    """
    return _checked(_observe_acl, fd)


def _pair(file_fd, parent_fd, identity, names, acl):
    before = (_snapshot(file_fd, identity), _snapshot(parent_fd, identity))
    file_info, parent_info = (dict(zip(_FIELDS, value)) for value in before)
    if (file_info['st_mode'] != (stat.S_IFREG | 0o600) or file_info['st_nlink'] != 1
            or file_info['st_size'] > MAX_DOCUMENT_BYTES or file_info['st_flags'] != 0):
        _fail('UNSAFE_PRIVATE_FILE')
    if parent_info['st_mode'] != (stat.S_IFDIR | 0o700) or parent_info['st_flags'] != 0:
        _fail('UNSAFE_PRIVATE_PARENT')
    if before[0][:2] == before[1][:2]:
        _fail('DESCRIPTOR_PAIR_INVALID')
    observations = []
    for fd in (file_fd, parent_fd):
        attributes = names.names(fd)
        if not attributes <= _ALLOWED_NAMES:
            _fail('UNSUPPORTED_XATTR_NAMES')
        state = acl.state(fd)
        if state not in ('no_acl_reported', 'empty_acl'):
            _fail('ACL_ENTRIES_PRESENT')
        observations.append((attributes, state))
    after = (_snapshot(file_fd, identity), _snapshot(parent_fd, identity))
    if after != before:
        _fail('METADATA_CHANGED')
    if _identity() != identity:
        _fail('CALLER_IDENTITY_CHANGED')
    return before, tuple(observations)


def _begin(file_fd, parent_fd):
    _descriptor(file_fd)
    _descriptor(parent_fd)
    if file_fd == parent_fd:
        _fail('DESCRIPTOR_PAIR_INVALID')
    identity = _identity()
    names, acl = metadata_names._DarwinNames(), _DarwinACL()
    before = _pair(file_fd, parent_fd, identity, names, acl)
    return identity, names, acl, before


def _finish(file_fd, parent_fd, identity, names, acl, before):
    if _identity() != identity:
        _fail('CALLER_IDENTITY_CHANGED')
    if _pair(file_fd, parent_fd, identity, names, acl) != before:
        _fail('METADATA_CHANGED')


@contextmanager
def private_document_read(file_fd, parent_fd):
    """Bracket a caller's bounded read; yield None and retain neither descriptor.

    Exact 0600/0700 is this new narrow subset, not a change to any old reader.
    A body exception propagates unchanged and cannot yield successful completion.
    Caller must discard any read result if exit validation fails. This internal
    source-derived policy is not enabled in existing CLIs; native tests pending.
    """
    state = _checked(_begin, file_fd, parent_fd)
    yield None
    _checked(_finish, file_fd, parent_fd, *state)
