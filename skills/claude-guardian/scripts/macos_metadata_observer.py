#!/usr/bin/env python3
"""Bounded, read-only Darwin observation of one already-open owned descriptor.

The caller selects, authorizes and opens a regular file or directory, and keeps
its descriptor open throughout this call. No paths are accepted or discovered.
For a child process, explicitly inherit only that descriptor using Python's
subprocess.run([... , '--fd', str(fd)], pass_fds=(fd,), shell=False).
Only fstat and native attribute-name listing inspect the selected object. Names
stay private; values, file contents and ACLs are not read. Fixed categories do
not establish trust, harmlessness, preservation, or permission to write.

Repeated name sets and stat fields can detect some concurrent changes. They
cannot establish an atomic snapshot, writer exclusion, complete visibility, or
absence of changes between observations. The caller retains descriptor ownership.
"""
import argparse
import ctypes
import errno
import json
import os
import stat
import sys


MAX_NAME_LIST_BYTES = 65536
MAX_NAMES = 32
MAX_NAME_BYTES = 127
_SHOW_COMPRESSION = 0x0020
_LIBSYSTEM = '/usr/lib/libSystem.B.dylib'
_SCHEMA = 'guardian-macos-metadata-observation/1'
_CATEGORIES = {
    b'com.apple.provenance': 'provenance',
    b'com.apple.decmpfs': 'compression',
    b'com.apple.ResourceFork': 'resource_fork',
    b'com.apple.FinderInfo': 'finder_info',
    b'com.apple.quarantine': 'quarantine',
    b'user.guardian.synthetic': 'synthetic_marker',
}
_STAT_FIELDS = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_uid',
                'st_gid', 'st_size', 'st_mtime_ns', 'st_ctime_ns')


class _Failure(Exception):
    """Internal fixed codes only; never attach native exception text."""


def _result():
    return {
        'schema_version': _SCHEMA,
        'observation_state': 'blocked',
        'code': 'OBSERVATION_FAILED',
        'descriptor_stat': 'not_checked',
        'native_name_listing': 'not_checked',
        'object_type': 'unknown',
        'xattr_names': 'not_inspected',
        'xattr_visibility': 'accessible_names_only',
        'xattr_count': None,
        'category_counts': None,
        'name_list_consistency': 'not_established',
        'attribute_values': 'not_inspected',
        'acl': 'not_inspected',
        'flags': 'unknown',
        'atomic_snapshot': 'not_established',
        'writer_exclusion': 'not_established',
        'preservation': 'not_established',
        'write_admission': 'not_established',
    }


def _native_failure(number):
    if number == errno.EBADF:
        raise _Failure('INVALID_DESCRIPTOR')
    if number in (errno.EACCES, errno.EPERM):
        raise _Failure('NAME_LIST_DENIED')
    if number in (errno.ENOTSUP, errno.EOPNOTSUPP):
        raise _Failure('NAME_LIST_UNSUPPORTED')
    if number == errno.ERANGE:
        raise _Failure('NAME_LIST_CHANGED')
    raise _Failure('NAME_LIST_FAILED')


class _DarwinNames:
    def __init__(self):
        # Fixed OS library and sole native symbol. No search-path resolution,
        # Python-wrapper fallback, value/ACL reads, or mutation/copy bindings.
        # Darwin ABI, name limit and option:
        # https://github.com/apple-oss-distributions/xnu/blob/main/bsd/sys/xattr.h
        # https://developer.apple.com/library/archive/documentation/System/Conceptual/ManPages_iPhoneOS/man2/flistxattr.2.html
        try:
            self._library = ctypes.CDLL(_LIBSYSTEM, use_errno=True)
            self._list = self._library.flistxattr
            self._list.argtypes = [ctypes.c_int, ctypes.c_void_p,
                                  ctypes.c_size_t, ctypes.c_int]
            self._list.restype = ctypes.c_ssize_t
        except (OSError, AttributeError, TypeError, ValueError):
            raise _Failure('NATIVE_BACKEND_UNAVAILABLE') from None

    def _query(self, fd, buffer, length):
        ctypes.set_errno(0)
        try:
            result = self._list(fd, buffer, length, _SHOW_COMPRESSION)
        except OSError as error:
            _native_failure(error.errno)
        if type(result) is not int:
            raise _Failure('NATIVE_RESULT_INVALID')
        if result == -1:
            _native_failure(ctypes.get_errno())
        if result < 0:
            raise _Failure('NATIVE_RESULT_INVALID')
        if result > MAX_NAME_LIST_BYTES:
            raise _Failure('NAME_LIST_BOUNDS')
        return result

    def names(self, fd):
        length = self._query(fd, None, 0)
        if not length:
            return frozenset()
        # The size query is checked before allocating, and there are no retries.
        buffer = ctypes.create_string_buffer(length)
        if self._query(fd, buffer, length) != length:
            raise _Failure('NAME_LIST_CHANGED')
        raw = buffer.raw
        if not raw.endswith(b'\0'):
            raise _Failure('NAME_LIST_MALFORMED')
        if raw.count(b'\0') > MAX_NAMES:
            raise _Failure('NAME_LIST_BOUNDS')
        names = raw[:-1].split(b'\0')
        if any(not name or len(name) > MAX_NAME_BYTES for name in names):
            raise _Failure('NAME_LIST_MALFORMED')
        try:
            for name in names:
                name.decode('utf-8', errors='strict')
        except UnicodeDecodeError:
            raise _Failure('NAME_LIST_MALFORMED') from None
        if len(set(names)) != len(names):
            raise _Failure('NAME_LIST_MALFORMED')
        return frozenset(names)


def _snapshot(fd, effective_uid):
    try:
        info = os.fstat(fd)
    except OSError as error:
        if error.errno == errno.EBADF:
            raise _Failure('INVALID_DESCRIPTOR') from None
        if error.errno in (errno.EACCES, errno.EPERM):
            raise _Failure('DESCRIPTOR_STAT_DENIED') from None
        raise _Failure('DESCRIPTOR_STAT_FAILED') from None
    values = tuple(getattr(info, name, None) for name in _STAT_FIELDS)
    if any(type(value) is not int for value in values) or info.st_size < 0:
        raise _Failure('DESCRIPTOR_STAT_INVALID')
    if not (stat.S_ISREG(info.st_mode) or stat.S_ISDIR(info.st_mode)):
        raise _Failure('OBJECT_TYPE_UNSUPPORTED')
    if info.st_uid != effective_uid:
        raise _Failure('OBJECT_NOT_OWNED')
    flags = getattr(info, 'st_flags', None)
    if flags is not None and (type(flags) is not int or not 0 <= flags <= 2**32 - 1):
        raise _Failure('DESCRIPTOR_STAT_INVALID')
    return values + (flags,)


def observe_fd(fd):
    """Return only fixed labels/counts; never close or change the caller's fd.

    On Darwin, use at most two size queries and two bounded name reads, with
    fstat before, between and after. Empty lists need only their size queries.
    No result, including an empty observed list, permits a production write.
    The caller must prevent concurrent descriptor closure/reuse and independently
    authorize the exact selected object. A report is neither authority nor a
    persistent identity binding, and does not establish complete metadata state.
    """
    report = _result()
    try:
        if type(fd) is not int or not 0 <= fd <= 2**31 - 1:
            raise _Failure('INVALID_DESCRIPTOR')
        if sys.platform != 'darwin':
            report['observation_state'] = 'unsupported'
            raise _Failure('UNSUPPORTED_PLATFORM')
        if not all(callable(getattr(os, name, None)) for name in ('fstat', 'geteuid')):
            report['descriptor_stat'] = 'unavailable'
            raise _Failure('DESCRIPTOR_API_UNAVAILABLE')
        effective_uid = os.geteuid()
        if type(effective_uid) is not int or effective_uid < 0:
            raise _Failure('CALLER_IDENTITY_UNAVAILABLE')
        before = _snapshot(fd, effective_uid)
        report['descriptor_stat'] = 'available'
        api = _DarwinNames()
        report['native_name_listing'] = 'available'
        first = api.names(fd)
        if _snapshot(fd, effective_uid) != before:
            raise _Failure('METADATA_CHANGED')
        second = api.names(fd)
        if _snapshot(fd, effective_uid) != before:
            raise _Failure('METADATA_CHANGED')
        if os.geteuid() != effective_uid:
            raise _Failure('CALLER_IDENTITY_CHANGED')
        if first != second:
            raise _Failure('NAME_LIST_CHANGED')
        counts = {category: 0 for category in _CATEGORIES.values()}
        counts['unknown'] = 0
        for name in first:
            counts[_CATEGORIES.get(name, 'unknown')] += 1
        flags = before[-1]
        report.update(
            observation_state='observed', code='BOUNDED_OBSERVATION_COMPLETE',
            object_type='regular_file' if stat.S_ISREG(before[2]) else 'directory',
            xattr_names='observed', xattr_count=len(first), category_counts=counts,
            name_list_consistency='repeat_matched',
            flags='unknown' if flags is None else 'nonzero' if flags else 'zero')
    except _Failure as error:
        report['code'] = str(error)
        if report['code'] == 'NATIVE_BACKEND_UNAVAILABLE':
            report['native_name_listing'] = 'unavailable'
    except KeyboardInterrupt:
        report.update(observation_state='cancelled', code='CANCELLED')
    except Exception:
        # Native diagnostics may embed arbitrary paths or attribute names.
        report['code'] = 'OBSERVATION_FAILED'
    return report


def main(argv=None):
    class Parser(argparse.ArgumentParser):
        def error(self, message):
            raise _Failure('INPUT_INVALID')

    parser = Parser(prog='macos_metadata_observer', allow_abbrev=False,
                    description=__doc__)
    parser.add_argument('--fd', type=int, action='append', required=True,
                        help='one authorized, already-open inherited descriptor')
    try:
        args = parser.parse_args(argv)
        if len(args.fd) != 1:
            raise _Failure('INPUT_INVALID')
        result = observe_fd(args.fd[0])
    except _Failure:
        result = _result()
        result['code'] = 'INPUT_INVALID'
    except KeyboardInterrupt:
        result = _result()
        result.update(observation_state='cancelled', code='CANCELLED')
    print(json.dumps(result, sort_keys=True))
    return (0 if result['observation_state'] == 'observed' else
            2 if result['observation_state'] == 'cancelled' else 1)


if __name__ == '__main__':
    raise SystemExit(main())
