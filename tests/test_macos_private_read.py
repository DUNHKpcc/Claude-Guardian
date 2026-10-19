"""Synthetic Darwin ABI/metadata tests, never native Mac acceptance."""
import ast
from contextlib import ExitStack, contextmanager, redirect_stderr, redirect_stdout
import ctypes
import errno
import importlib.util
import io
from pathlib import Path
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
with patch.object(sys, 'path', [str(SCRIPTS)] + sys.path):
    SPEC = importlib.util.spec_from_file_location('macos_private_read', SCRIPTS / 'macos_private_read.py')
    m = importlib.util.module_from_spec(SPEC)
    SPEC.loader.exec_module(m)

FILE, PARENT = 11, 12
PROVENANCE = b'com.apple.provenance\0'


def info(fd, **changes):
    result = dict(st_dev=7, st_ino=100 + fd, st_mode=(stat.S_IFREG | 0o600)
                  if fd == FILE else (stat.S_IFDIR | 0o700),
                  st_nlink=1 if fd == FILE else 2, st_uid=501, st_gid=20,
                  st_size=11 if fd == FILE else 4096, st_mtime_ns=30,
                  st_ctime_ns=40, st_flags=0)
    result.update(changes)
    return SimpleNamespace(**result)


class Function:
    def __init__(self, implementation):
        self.implementation = implementation
        self.calls = []
        self.errno_before = []

    def __call__(self, *args):
        self.calls.append(args)
        self.errno_before.append(ctypes.get_errno())
        return self.implementation(*args)


class Native:
    """Independent fake libc ABI; only caller-provided ctypes buffers are written."""
    def __init__(self, states=None, names=None):
        self.states = states or {FILE: 'no_acl_reported', PARENT: 'no_acl_reported'}
        self.names = names or {FILE: PROVENANCE, PARENT: b''}
        self.live = {}
        self.symbols = []
        self.functions = {
            'flistxattr': Function(self.list_names),
            'acl_get_fd_np': Function(self.get_acl),
            'acl_valid': Function(lambda acl: 0),
            'acl_get_entry': Function(self.first_entry),
            'acl_free': Function(lambda acl: 0),
        }

    def __getattr__(self, name):
        self.symbols.append(name)
        if name not in self.functions:
            raise AttributeError(name)
        return self.functions[name]

    def list_names(self, fd, buffer, size, options):
        if options != 0x0020:
            raise AssertionError('compression visibility option missing')
        raw = self.names[fd]
        if buffer is None:
            if size != 0:
                raise AssertionError('invalid size query')
            return len(raw)
        if len(raw) > size:
            ctypes.set_errno(errno.ERANGE)
            return -1
        ctypes.memmove(buffer, raw, len(raw))
        return len(raw)

    def get_acl(self, fd, kind):
        if kind != 0x100:
            raise AssertionError('wrong Darwin ACL type')
        state = self.states[fd]
        if state == 'no_acl_reported':
            ctypes.set_errno(errno.ENOENT)
            return None
        pointer = 4096 + fd
        self.live[pointer] = state
        return pointer

    def first_entry(self, acl, which, entry):
        if which != 0:
            raise AssertionError('only Darwin FIRST_ENTRY is allowed')
        if self.live[acl] == 'empty_acl':
            ctypes.set_errno(errno.EINVAL)
            return -1
        ctypes.cast(entry, ctypes.POINTER(ctypes.c_void_p))[0] = 8192
        return 0


class PrivateReadTests(unittest.TestCase):
    @contextmanager
    def environment(self, native=None, snapshots=None):
        native = native or Native()
        snapshots = snapshots or {FILE: info(FILE), PARENT: info(PARENT)}
        with ExitStack() as stack:
            stack.enter_context(patch.object(m.sys, 'platform', 'darwin'))
            stack.enter_context(patch.object(m.os, 'geteuid', return_value=501, create=True))
            stack.enter_context(patch.object(m.os, 'getegid', return_value=20, create=True))
            stack.enter_context(patch.object(m.os, 'fstat', side_effect=lambda fd: snapshots[fd]))
            load = stack.enter_context(patch.object(m.ctypes, 'CDLL', return_value=native))
            yield native, snapshots, load

    def assert_code(self, code, action):
        with self.assertRaises(m.PrivateReadError) as caught:
            action()
        self.assertEqual(caught.exception.code, code)
        self.assertEqual(str(caught.exception), code)

    def pair(self, body=None, file_fd=FILE, parent_fd=PARENT):
        with m.private_document_read(file_fd, parent_fd) as capability:
            self.assertIsNone(capability)
            if body is not None:
                body()

    def test_natural_names_absent_acl_guard_yields_no_token(self):
        out, err = io.StringIO(), io.StringIO()
        with self.environment() as (native, _, load), redirect_stdout(out), redirect_stderr(err):
            self.pair()
        self.assertEqual(out.getvalue(), '')
        self.assertEqual(err.getvalue(), '')
        self.assertEqual(len(native.functions['acl_get_fd_np'].calls), 4)
        self.assertEqual(native.functions['acl_valid'].calls, [])
        self.assertEqual(native.functions['acl_get_entry'].calls, [])
        self.assertEqual(native.functions['acl_free'].calls, [])
        self.assertEqual(len(native.functions['flistxattr'].calls), 6)
        self.assertEqual(load.call_count, 2)
        for call in load.call_args_list:
            self.assertEqual(call.args, ('/usr/lib/libSystem.B.dylib',))
            self.assertEqual(call.kwargs, {'use_errno': True})

    def test_empty_acl_first_entry_only_and_exact_release(self):
        native = Native(states={FILE: 'empty_acl', PARENT: 'empty_acl'})
        with self.environment(native):
            self.pair()
        for symbol in ('acl_get_fd_np', 'acl_valid', 'acl_get_entry', 'acl_free'):
            self.assertEqual(len(native.functions[symbol].calls), 4)
            self.assertTrue(all(value == 0 for value in native.functions[symbol].errno_before))
        self.assertTrue(all(call[1] == 0 for call in native.functions['acl_get_entry'].calls))

    def test_observer_distinguishes_all_three_acl_states(self):
        for state in ('no_acl_reported', 'empty_acl', 'entries_present'):
            with self.subTest(state=state), self.environment(Native(states={FILE: state, PARENT: state})):
                self.assertEqual(m.observe_acl_fd(FILE), state)
                self.assertEqual(m.observe_acl_fd(PARENT), state)

    def test_ace_on_either_object_blocks_before_body(self):
        for fd in (FILE, PARENT):
            states = {FILE: 'no_acl_reported', PARENT: 'no_acl_reported', fd: 'entries_present'}
            body = Mock()
            with self.subTest(fd=fd), self.environment(Native(states=states)):
                self.assert_code('ACL_ENTRIES_PRESENT', lambda: self.pair(body))
            body.assert_not_called()

    def test_each_non_provenance_category_and_lookalike_is_rejected(self):
        rejected = (b'com.apple.decmpfs', b'com.apple.ResourceFork', b'com.apple.FinderInfo',
                    b'com.apple.quarantine', b'user.guardian.synthetic', b'private.marker',
                    b'com.apple.provenance.extra', b'COM.APPLE.PROVENANCE')
        for fd in (FILE, PARENT):
            for name in rejected:
                names = {FILE: b'', PARENT: b'', fd: name + b'\0'}
                with self.subTest(fd=fd, name=name), self.environment(Native(names=names)):
                    self.assert_code('UNSUPPORTED_XATTR_NAMES', self.pair)

    def test_empty_and_provenance_name_sets_on_both_objects(self):
        for raw in (b'', PROVENANCE):
            with self.subTest(raw=raw), self.environment(Native(names={FILE: raw, PARENT: raw})):
                self.pair()

    def test_exact_file_size_limit_and_directory_link_count(self):
        for length in (0, m.MAX_DOCUMENT_BYTES):
            with self.subTest(length=length), self.environment() as (_, snapshots, _):
                snapshots[FILE] = info(FILE, st_size=length, st_mtime_ns=-1)
                snapshots[PARENT] = info(PARENT, st_nlink=3)
                self.pair()

    def test_reused_name_parser_preserves_malformed_and_size_bounds(self):
        cases = ((b'bad', 'NAME_LIST_MALFORMED'), (b'\0', 'NAME_LIST_MALFORMED'),
                 (PROVENANCE * 2, 'NAME_LIST_MALFORMED'),
                 (b'\xff\0', 'NAME_LIST_MALFORMED'),
                 (b'x' * 128 + b'\0', 'NAME_LIST_MALFORMED'),
                 (b'x' * 65537, 'NAME_LIST_BOUNDS'))
        for raw, code in cases:
            with self.subTest(code=code, raw_size=len(raw)), \
                    self.environment(Native(names={FILE: raw, PARENT: b''})):
                self.assert_code(code, self.pair)

    def test_unsupported_platform_and_invalid_descriptors_do_not_load_native_code(self):
        with patch.object(m.sys, 'platform', 'linux'), patch.object(m.ctypes, 'CDLL') as load:
            self.assert_code('UNSUPPORTED_PLATFORM', self.pair)
            self.assert_code('UNSUPPORTED_PLATFORM', lambda: m.observe_acl_fd(FILE))
            load.assert_not_called()
        with self.environment() as (_, _, load):
            for fd in (True, -1, 2**31, None, 1.0, '11'):
                self.assert_code('INVALID_DESCRIPTOR', lambda: self.pair(file_fd=fd))
                self.assert_code('INVALID_DESCRIPTOR', lambda: self.pair(parent_fd=fd))
            self.assert_code('DESCRIPTOR_PAIR_INVALID', lambda: self.pair(parent_fd=FILE))
            load.assert_not_called()

    def test_missing_native_symbol_fails_closed(self):
        with self.environment() as (native, _, _):
            del native.functions['acl_valid']
            self.assert_code('NATIVE_BACKEND_UNAVAILABLE', self.pair)

    def test_file_and_parent_privacy_subset(self):
        cases = ((FILE, {'st_mode': stat.S_IFREG | 0o400}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_mode': stat.S_IFREG | 0o700}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_mode': stat.S_IFREG | 0o640}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_mode': stat.S_IFREG | 0o4600}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_nlink': 2}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_size': m.MAX_DOCUMENT_BYTES + 1}, 'UNSAFE_PRIVATE_FILE'),
                 (FILE, {'st_flags': 1}, 'UNSAFE_PRIVATE_FILE'),
                 (PARENT, {'st_mode': stat.S_IFDIR | 0o750}, 'UNSAFE_PRIVATE_PARENT'),
                 (PARENT, {'st_flags': 1}, 'UNSAFE_PRIVATE_PARENT'),
                 (FILE, {'st_mode': stat.S_IFIFO | 0o600}, 'OBJECT_TYPE_UNSUPPORTED'),
                 (PARENT, {'st_mode': stat.S_IFLNK | 0o700}, 'OBJECT_TYPE_UNSUPPORTED'))
        for fd, change, code in cases:
            with self.subTest(fd=fd, change=change), self.environment() as (_, snapshots, _):
                snapshots[fd] = info(fd, **change)
                self.assert_code(code, self.pair)

    def test_current_owner_and_group_required_for_both_objects(self):
        for fd in (FILE, PARENT):
            for change in ({'st_uid': 0}, {'st_gid': 21}):
                with self.subTest(fd=fd, change=change), self.environment() as (_, snapshots, _):
                    snapshots[fd] = info(fd, **change)
                    self.assert_code('OBJECT_NOT_OWNED', self.pair)

    def test_stat_field_types_bounds_and_required_flags(self):
        for fd in (FILE, PARENT):
            for key in m._FIELDS:
                for value in (None, True, 1.5, 2**65):
                    with self.subTest(fd=fd, key=key, value=value), self.environment() as (_, snapshots, _):
                        snapshots[fd] = info(fd, **{key: value})
                        self.assert_code('DESCRIPTOR_STAT_INVALID', self.pair)
            for change in ({'st_size': -1}, {'st_flags': 2**32}, {'st_nlink': 0}):
                with self.subTest(fd=fd, change=change), self.environment() as (_, snapshots, _):
                    snapshots[fd] = info(fd, **change)
                    self.assert_code('DESCRIPTOR_STAT_INVALID', self.pair)

    def test_stat_changes_during_metadata_query_block(self):
        with self.environment() as (native, snapshots, _):
            original = native.functions['acl_get_fd_np'].implementation
            def changing(fd, kind):
                snapshots[FILE] = info(FILE, st_ctime_ns=41)
                return original(fd, kind)
            native.functions['acl_get_fd_np'].implementation = changing
            self.assert_code('METADATA_CHANGED', self.pair)

    def test_each_full_snapshot_dimension_is_fresh_across_body(self):
        changes = {'st_dev': 8, 'st_ino': 999, 'st_size': 12,
                   'st_mtime_ns': 31, 'st_ctime_ns': 41}
        for fd in (FILE, PARENT):
            for key, value in changes.items():
                with self.subTest(fd=fd, key=key), self.environment() as (_, snapshots, _):
                    def body():
                        snapshots[fd] = info(fd, **{key: value})
                    self.assert_code('METADATA_CHANGED', lambda: self.pair(body))
        for fd, key, value, code in (
                (FILE, 'st_mode', stat.S_IFREG | 0o400, 'UNSAFE_PRIVATE_FILE'),
                (PARENT, 'st_mode', stat.S_IFDIR | 0o750, 'UNSAFE_PRIVATE_PARENT'),
                (FILE, 'st_nlink', 2, 'UNSAFE_PRIVATE_FILE'),
                (PARENT, 'st_nlink', 3, 'METADATA_CHANGED'),
                (FILE, 'st_uid', 502, 'OBJECT_NOT_OWNED'),
                (PARENT, 'st_gid', 21, 'OBJECT_NOT_OWNED'),
                (FILE, 'st_flags', 1, 'UNSAFE_PRIVATE_FILE')):
            with self.subTest(fd=fd, key=key), self.environment() as (_, snapshots, _):
                self.assert_code(code, lambda: self.pair(
                    lambda: snapshots.__setitem__(fd, info(fd, **{key: value}))))

    def test_metadata_and_acl_absence_forms_must_match_across_body(self):
        with self.environment() as (native, _, _):
            self.assert_code('METADATA_CHANGED', lambda: self.pair(
                lambda: native.names.__setitem__(FILE, b'')))
        with self.environment() as (native, _, _):
            self.assert_code('METADATA_CHANGED', lambda: self.pair(
                lambda: native.states.__setitem__(PARENT, 'empty_acl')))

    def test_identity_change_and_invalid_identity_block(self):
        with self.environment():
            for getter in ('geteuid', 'getegid'):
                with patch.object(m.os, getter, return_value=True):
                    self.assert_code('CALLER_IDENTITY_UNAVAILABLE', self.pair)
            with patch.object(m.os, 'geteuid', side_effect=[501, 501, 502]):
                self.assert_code('CALLER_IDENTITY_CHANGED', self.pair)

    def test_observe_acl_detects_changed_stat_and_requires_owned_regular_or_directory(self):
        with self.environment() as (_, snapshots, _):
            snapshots[FILE] = info(FILE, st_uid=0)
            self.assert_code('OBJECT_NOT_OWNED', lambda: m.observe_acl_fd(FILE))
        with self.environment(), patch.object(m.os, 'fstat', side_effect=[info(FILE), info(FILE, st_ino=999)]):
            self.assert_code('METADATA_CHANGED', lambda: m.observe_acl_fd(FILE))

    def test_body_failure_propagates_unchanged_and_never_succeeds(self):
        error = ValueError('synthetic caller parsing failure')
        with self.environment() as (native, _, _):
            with self.assertRaises(ValueError) as caught:
                with m.private_document_read(FILE, PARENT):
                    raise error
            self.assertIs(caught.exception, error)
        self.assertEqual(len(native.functions['acl_get_fd_np'].calls), 2)

    def test_native_error_messages_and_arbitrary_name_errors_do_not_leak(self):
        secret = 'synthetic-private-content'
        with self.environment() as (native, _, _):
            native.functions['acl_get_fd_np'].implementation = Mock(side_effect=OSError(errno.EACCES, secret))
            self.assert_code('ACL_READ_DENIED', self.pair)
        with self.environment(), patch.object(m.metadata_names._DarwinNames, 'names',
                                             side_effect=m.metadata_names._Failure(secret)):
            self.assert_code('NAME_LIST_FAILED', self.pair)
        with self.environment(), patch.object(m.os, 'fstat', side_effect=RuntimeError(secret)):
            self.assert_code('PRIVATE_READ_FAILED', self.pair)

    def test_no_mutation_content_path_or_principal_api_is_added(self):
        tree = ast.parse((SCRIPTS / 'macos_private_read.py').read_text(encoding='utf-8'))
        os_calls = {node.func.attr for node in ast.walk(tree) if isinstance(node, ast.Call)
                    and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os'}
        self.assertEqual(os_calls, {'fstat', 'geteuid', 'getegid'})
        with self.environment() as (native, _, _):
            self.pair()
        self.assertEqual(set(native.symbols),
                         {'flistxattr', 'acl_get_fd_np', 'acl_valid', 'acl_get_entry', 'acl_free'})
        self.assertEqual(native.functions['acl_get_fd_np'].argtypes, [ctypes.c_int, ctypes.c_int])
        self.assertIs(native.functions['acl_get_fd_np'].restype, ctypes.c_void_p)
        self.assertEqual(native.functions['acl_get_entry'].argtypes,
                         [ctypes.c_void_p, ctypes.c_int, ctypes.POINTER(ctypes.c_void_p)])


    def test_null_acl_accepts_only_explicit_enoent(self):
        for number, code in ((0, 'ACL_READ_FAILED'), (errno.EINVAL, 'ACL_READ_FAILED'),
                             (errno.EACCES, 'ACL_READ_DENIED'), (errno.EPERM, 'ACL_READ_DENIED'),
                             (errno.EBADF, 'INVALID_DESCRIPTOR'), (errno.EIO, 'ACL_READ_FAILED'),
                             (errno.ENOTSUP, 'ACL_READ_UNSUPPORTED')):
            with self.subTest(number=number), self.environment() as (native, _, _):
                def missing(fd, kind):
                    ctypes.set_errno(number)
                    return None
                native.functions['acl_get_fd_np'].implementation = missing
                self.assert_code(code, lambda: m.observe_acl_fd(FILE))
                self.assertEqual(native.functions['acl_free'].calls, [])

    def test_invalid_opaque_results_are_not_dereferenced(self):
        for value in (0, -1, True, 1.0, 16, 2**(8 * ctypes.sizeof(ctypes.c_void_p)) - 1):
            with self.subTest(value=value), self.environment() as (native, _, _):
                native.functions['acl_get_fd_np'].implementation = lambda fd, kind: value
                self.assert_code('ACL_RESULT_INVALID', lambda: m.observe_acl_fd(FILE))
                self.assertEqual(native.functions['acl_valid'].calls, [])

    def test_invalid_acl_released_once(self):
        for value in (-1, 1, None, False):
            with self.subTest(value=value), self.environment(Native(states={FILE: 'empty_acl'})) as (native, _, _):
                native.functions['acl_valid'].implementation = lambda acl: value
                self.assert_code('ACL_INVALID', lambda: m.observe_acl_fd(FILE))
                self.assertEqual(len(native.functions['acl_free'].calls), 1)
                self.assertEqual(native.functions['acl_get_entry'].calls, [])

    def test_empty_entry_requires_darwin_return_errno_and_null_output(self):
        for result, number, pointer in ((1, 0, 8192), (0, 0, None), (-1, 0, None),
                                        (-1, errno.EIO, None), (-1, errno.EINVAL, 8192),
                                        (False, 0, 8192), (None, errno.EINVAL, None)):
            with self.subTest(result=result, number=number, pointer=pointer), \
                    self.environment(Native(states={FILE: 'empty_acl'})) as (native, _, _):
                def unusual(acl, which, entry):
                    if pointer is not None:
                        ctypes.cast(entry, ctypes.POINTER(ctypes.c_void_p))[0] = pointer
                    ctypes.set_errno(number)
                    return result
                native.functions['acl_get_entry'].implementation = unusual
                self.assert_code('ACL_RESULT_INVALID', lambda: m.observe_acl_fd(FILE))
                self.assertEqual(len(native.functions['acl_free'].calls), 1)

    def test_stale_errno_is_cleared_before_absence_query(self):
        with self.environment() as (native, _, _):
            ctypes.set_errno(errno.ENOENT)
            native.functions['acl_get_fd_np'].implementation = lambda fd, kind: None
            self.assert_code('ACL_READ_FAILED', lambda: m.observe_acl_fd(FILE))

    def test_acl_release_failure_blocks_success(self):
        for result in (-1, None, False):
            with self.subTest(result=result), self.environment(Native(states={FILE: 'empty_acl'})) as (native, _, _):
                native.functions['acl_free'].implementation = lambda acl: result
                self.assert_code('ACL_RELEASE_FAILED', lambda: m.observe_acl_fd(FILE))
        with self.environment(Native(states={FILE: 'empty_acl'})) as (native, _, _):
            native.functions['acl_free'].implementation = Mock(side_effect=OSError('synthetic private error'))
            self.assert_code('ACL_RELEASE_FAILED', lambda: m.observe_acl_fd(FILE))

    def test_cancellation_releases_obtained_acl_once(self):
        with self.environment(Native(states={FILE: 'empty_acl'})) as (native, _, _):
            native.functions['acl_get_entry'].implementation = Mock(side_effect=KeyboardInterrupt())
            self.assert_code('CANCELLED', lambda: m.observe_acl_fd(FILE))
            self.assertEqual(len(native.functions['acl_free'].calls), 1)


if __name__ == '__main__':
    unittest.main()
