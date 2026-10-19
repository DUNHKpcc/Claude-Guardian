"""Synthetic observer boundaries; these mocks are not native Mac acceptance."""
import ast
import contextlib
import ctypes
import errno
import importlib.util
import io
import json
from pathlib import Path
import stat
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, call, patch


SCRIPT = (Path(__file__).resolve().parents[1] /
          'skills/claude-guardian/scripts/macos_metadata_observer.py')
SPEC = importlib.util.spec_from_file_location('macos_metadata_observer', SCRIPT)
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


def info(**changes):
    fields = dict(st_dev=99, st_ino=111, st_mode=stat.S_IFREG | 0o600,
                  st_nlink=1, st_uid=501, st_gid=20, st_size=11,
                  st_mtime_ns=22, st_ctime_ns=33, st_flags=0)
    fields.update(changes)
    return SimpleNamespace(**fields)


class NativeList:
    """Strict bounded stand-in; writes only to the supplied ctypes memory."""
    def __init__(self, *steps):
        self.steps = list(steps)
        self.calls = []

    def __call__(self, fd, buffer, length, options):
        self.calls.append((fd, buffer is None, length, options))
        step = self.steps.pop(0)
        if isinstance(step, BaseException):
            raise step
        if isinstance(step, tuple):
            result, native_errno = step
            ctypes.set_errno(native_errno)
            return result
        if isinstance(step, bytes):
            if buffer is None or len(step) > length:
                raise AssertionError('unsafe synthetic native read')
            ctypes.memmove(buffer, step, len(step))
            return len(step)
        return step


class Library:
    def __init__(self, query):
        self.query = query
        self.symbols = []

    def __getattr__(self, name):
        self.symbols.append(name)
        if name != 'flistxattr':
            raise AssertionError('unexpected native symbol')
        return self.query


def name_steps(raw):
    return [len(raw), raw] if raw else [0]


class MetadataObserverTests(unittest.TestCase):
    def observe(self, first=b'', second=None, *, snapshots=None, query=None):
        if second is None:
            second = first
        query = query or NativeList(*(name_steps(first) + name_steps(second)))
        library = Library(query)
        snapshot = Mock(side_effect=snapshots or [info(), info(), info()])
        with patch.object(m.sys, 'platform', 'darwin'), \
                patch.object(m.os, 'geteuid', return_value=501, create=True), \
                patch.object(m.os, 'fstat', snapshot), \
                patch.object(m.ctypes, 'CDLL', return_value=library) as load:
            result = m.observe_fd(17)
        return result, query, library, snapshot, load

    def assert_unestablished(self, result):
        self.assertEqual(result['acl'], 'not_inspected')
        self.assertEqual(result['attribute_values'], 'not_inspected')
        for field in ('atomic_snapshot', 'writer_exclusion', 'preservation', 'write_admission'):
            self.assertEqual(result[field], 'not_established')

    def assert_blocked(self, result, code):
        self.assertEqual(result['observation_state'], 'blocked')
        self.assertEqual(result['code'], code)
        self.assertEqual(result['flags'], 'unknown')
        self.assertEqual(result['object_type'], 'unknown')
        self.assertIsNone(result['category_counts'])
        self.assertIsNone(result['xattr_count'])
        self.assertEqual(result['xattr_names'], 'not_inspected')
        self.assert_unestablished(result)

    def test_empty_observation_does_not_establish_no_acl_or_write_safety(self):
        result, query, library, snapshot, load = self.observe()
        self.assertEqual(result['schema_version'], 'guardian-macos-metadata-observation/1')
        self.assertEqual(result['observation_state'], 'observed')
        self.assertEqual(result['code'], 'BOUNDED_OBSERVATION_COMPLETE')
        self.assertEqual(result['xattr_count'], 0)
        self.assertEqual(set(result['category_counts'].values()), {0})
        self.assertEqual(result['flags'], 'zero')
        self.assertEqual(result['name_list_consistency'], 'repeat_matched')
        self.assertEqual(result['xattr_visibility'], 'accessible_names_only')
        self.assertEqual(query.calls, [(17, True, 0, 0x0020)] * 2)
        self.assertEqual(snapshot.call_args_list, [call(17)] * 3)
        self.assertEqual(library.symbols, ['flistxattr'])
        load.assert_called_once_with('/usr/lib/libSystem.B.dylib', use_errno=True)
        self.assertEqual(query.argtypes, [ctypes.c_int, ctypes.c_void_p,
                                         ctypes.c_size_t, ctypes.c_int])
        self.assertIs(query.restype, ctypes.c_ssize_t)
        self.assert_unestablished(result)

    def test_known_names_are_exact_fixed_categories_not_trust(self):
        raw = b'\0'.join(m._CATEGORIES) + b'\0'
        result = self.observe(raw)[0]
        self.assertEqual(result['observation_state'], 'observed')
        self.assertEqual(result['xattr_count'], 6)
        self.assertEqual(result['category_counts'], {
            'provenance': 1, 'compression': 1, 'resource_fork': 1,
            'finder_info': 1, 'quarantine': 1, 'synthetic_marker': 1, 'unknown': 0})
        self.assert_unestablished(result)
        serialized = json.dumps(result)
        self.assertNotIn('com.apple.', serialized)
        self.assertNotIn('user.guardian.synthetic', serialized)

    def test_unknown_names_stay_private_and_are_not_prefix_classified(self):
        names = [b'com.apple.provenance.PRIVATE-SECRET', b'user.guardian.synthetic.extra',
                 b'com.apple.unknown.PRIVATE', b'com.apple.Provenance',
                 'private.秘密'.encode('utf-8')]
        result = self.observe(b'\0'.join(names) + b'\0')[0]
        self.assertEqual(result['category_counts']['unknown'], 5)
        self.assertEqual(result['category_counts']['provenance'], 0)
        self.assertEqual(result['category_counts']['synthetic_marker'], 0)
        serialized = json.dumps(result, ensure_ascii=False)
        for private in ('PRIVATE', '秘密', 'com.apple.', 'user.guardian.', '501', '111'):
            self.assertNotIn(private, serialized)
        self.assertEqual(result['xattr_count'], 5)

    def test_directory_and_different_group_are_supported_observation_objects(self):
        result = self.observe(snapshots=[info(st_mode=stat.S_IFDIR | 0o700,
                                            st_gid=987)] * 3)[0]
        self.assertEqual(result['observation_state'], 'observed')
        self.assertEqual(result['object_type'], 'directory')

    def test_flags_are_fixed_categories_only(self):
        for flags, expected in ((0, 'zero'), (1, 'nonzero'), (2**32 - 1, 'nonzero')):
            with self.subTest(flags=flags):
                result = self.observe(snapshots=[info(st_flags=flags)] * 3)[0]
                self.assertEqual(result['flags'], expected)
                self.assert_unestablished(result)
        without_flags = info()
        del without_flags.st_flags
        self.assertEqual(self.observe(snapshots=[without_flags] * 3)[0]['flags'], 'unknown')

    def test_name_order_is_not_a_metadata_change(self):
        result = self.observe(b'one\0two\0', b'two\0one\0')[0]
        self.assertEqual(result['observation_state'], 'observed')

    def test_invalid_descriptors_do_no_io_or_native_load(self):
        for fd in (True, False, -1, 2**31, 17.0, '17', None, object()):
            with self.subTest(fd_type=type(fd).__name__), \
                    patch.object(m.sys, 'platform', 'darwin'), \
                    patch.object(m.os, 'fstat') as fstat, \
                    patch.object(m.ctypes, 'CDLL') as load:
                self.assert_blocked(m.observe_fd(fd), 'INVALID_DESCRIPTOR')
                fstat.assert_not_called()
                load.assert_not_called()

    def test_unsupported_platform_has_no_native_or_descriptor_fallback(self):
        for platform in ('linux', 'win32', 'darwin-extra'):
            with self.subTest(platform=platform), \
                    patch.object(m.sys, 'platform', platform), \
                    patch.object(m.os, 'fstat') as fstat, \
                    patch.object(m.ctypes, 'CDLL') as load:
                result = m.observe_fd(17)
                self.assertEqual(result['observation_state'], 'unsupported')
                self.assertEqual(result['code'], 'UNSUPPORTED_PLATFORM')
                self.assertIsNone(result['xattr_count'])
                fstat.assert_not_called()
                load.assert_not_called()

    def test_missing_python_xattr_wrappers_does_not_make_darwin_unsupported(self):
        with patch.object(m.os, 'listxattr', None, create=True), \
                patch.object(m.os, 'setxattr', None, create=True):
            self.assertEqual(self.observe()[0]['observation_state'], 'observed')

    def test_missing_descriptor_api_is_a_distinct_capability_failure(self):
        for name in ('fstat', 'geteuid'):
            with patch.object(m.sys, 'platform', 'darwin'), \
                    patch.object(m.os, name, None, create=True), \
                    patch.object(m.ctypes, 'CDLL') as load:
                result = m.observe_fd(17)
                self.assert_blocked(result, 'DESCRIPTOR_API_UNAVAILABLE')
                self.assertEqual(result['descriptor_stat'], 'unavailable')
                load.assert_not_called()

    def test_invalid_object_or_owner_stops_before_native_query(self):
        cases = [(info(st_uid=502), 'OBJECT_NOT_OWNED')]
        for kind in (stat.S_IFLNK, stat.S_IFIFO, stat.S_IFSOCK, stat.S_IFCHR, stat.S_IFBLK):
            cases.append((info(st_mode=kind | 0o600), 'OBJECT_TYPE_UNSUPPORTED'))
        for snapshot, code in cases:
            with self.subTest(code=code):
                result, query, _, _, load = self.observe(snapshots=[snapshot])
                self.assert_blocked(result, code)
                self.assertFalse(query.calls)
                load.assert_not_called()

    def test_invalid_stat_fields_are_not_observation_success(self):
        cases = [info(st_size=-1), info(st_ino=True), info(st_mtime_ns=None),
                 info(st_flags=True), info(st_flags=-1), info(st_flags=2**32)]
        for snapshot in cases:
            self.assert_blocked(self.observe(snapshots=[snapshot])[0], 'DESCRIPTOR_STAT_INVALID')

    def test_fstat_errors_have_fixed_codes_without_private_diagnostics(self):
        for native_errno, code in ((errno.EBADF, 'INVALID_DESCRIPTOR'),
                                   (errno.EPERM, 'DESCRIPTOR_STAT_DENIED'),
                                   (errno.EIO, 'DESCRIPTOR_STAT_FAILED')):
            result = self.observe(snapshots=[OSError(native_errno, 'PRIVATE-PATH')])[0]
            self.assert_blocked(result, code)
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_unavailable_library_or_symbol_is_distinct_from_empty_names(self):
        for error in (OSError('PRIVATE-LIBRARY'), AttributeError('PRIVATE-SYMBOL')):
            with patch.object(m.sys, 'platform', 'darwin'), \
                    patch.object(m.os, 'fstat', return_value=info()), \
                    patch.object(m.os, 'geteuid', return_value=501, create=True), \
                    patch.object(m.ctypes, 'CDLL', side_effect=error):
                result = m.observe_fd(17)
                self.assert_blocked(result, 'NATIVE_BACKEND_UNAVAILABLE')
                self.assertEqual(result['native_name_listing'], 'unavailable')
                self.assertNotIn('PRIVATE', json.dumps(result))
        result = self.observe(query=NativeList(RuntimeError('PRIVATE-NATIVE')))[0]
        self.assert_blocked(result, 'OBSERVATION_FAILED')
        self.assertNotIn('PRIVATE', json.dumps(result))

    def test_native_error_codes_are_not_an_empty_attribute_list(self):
        errors = [(errno.EBADF, 'INVALID_DESCRIPTOR'), (errno.EACCES, 'NAME_LIST_DENIED'),
                  (errno.EPERM, 'NAME_LIST_DENIED'), (errno.ENOTSUP, 'NAME_LIST_UNSUPPORTED'),
                  (errno.EOPNOTSUPP, 'NAME_LIST_UNSUPPORTED'), (errno.ERANGE, 'NAME_LIST_CHANGED'),
                  (errno.EIO, 'NAME_LIST_FAILED'), (0, 'NAME_LIST_FAILED')]
        for number, code in errors:
            with self.subTest(number=number):
                result, query, *_ = self.observe(query=NativeList((-1, number)))
                self.assert_blocked(result, code)
                self.assertEqual(len(query.calls), 1)
        self.assert_blocked(self.observe(query=NativeList(
            OSError(errno.EACCES, 'PRIVATE-NAME')))[0], 'NAME_LIST_DENIED')

    def test_invalid_native_lengths_fail_before_allocation(self):
        for length, code in ((True, 'NATIVE_RESULT_INVALID'), (None, 'NATIVE_RESULT_INVALID'),
                             (-2, 'NATIVE_RESULT_INVALID'), (1.5, 'NATIVE_RESULT_INVALID'),
                             (65537, 'NAME_LIST_BOUNDS'), (2**100, 'NAME_LIST_BOUNDS')):
            with self.subTest(length=length), \
                    patch.object(m.ctypes, 'create_string_buffer') as allocate:
                result, query, *_ = self.observe(query=NativeList(length))
                self.assert_blocked(result, code)
                allocate.assert_not_called()
                self.assertEqual(len(query.calls), 1)

    def test_name_list_allocation_has_a_hard_ceiling(self):
        allocate = m.ctypes.create_string_buffer
        with patch.object(m.ctypes, 'create_string_buffer', wraps=allocate) as allocations:
            result = self.observe(query=NativeList(65536, b'\0' * 65536))[0]
        self.assert_blocked(result, 'NAME_LIST_BOUNDS')
        allocations.assert_called_once_with(65536)

    def test_read_size_growth_shrink_or_failure_has_no_retry(self):
        for returned, code in ((1, 'NAME_LIST_CHANGED'), (0, 'NAME_LIST_CHANGED'),
                               (3, 'NAME_LIST_CHANGED'), (True, 'NATIVE_RESULT_INVALID'),
                               (65537, 'NAME_LIST_BOUNDS'), ((-1, errno.ERANGE), 'NAME_LIST_CHANGED')):
            with self.subTest(returned=returned):
                result, query, *_ = self.observe(query=NativeList(2, returned))
                self.assert_blocked(result, code)
                self.assertEqual(len(query.calls), 2)

    def test_malformed_names_are_fixed_failures_with_no_disclosure(self):
        for raw in (b'PRIVATE', b'\0', b'PRIVATE\0\0', b'\0PRIVATE\0',
                    b'PRIVATE\0PRIVATE\0', b'P' * 128 + b'\0', b'PRIVATE-\xff\0'):
            with self.subTest(size=len(raw)):
                result = self.observe(raw)[0]
                self.assert_blocked(result, 'NAME_LIST_MALFORMED')
                self.assertNotIn('PRIVATE', json.dumps(result))

    def test_name_count_and_utf8_byte_length_bounds(self):
        valid = b'\0'.join(('name%02d' % n).encode() for n in range(32)) + b'\0'
        self.assertEqual(self.observe(valid)[0]['xattr_count'], 32)
        self.assert_blocked(self.observe(valid + b'extra\0')[0], 'NAME_LIST_BOUNDS')
        self.assertEqual(self.observe(b'P' * 127 + b'\0')[0]['xattr_count'], 1)
        self.assert_blocked(self.observe(('私' * 43).encode() + b'\0')[0], 'NAME_LIST_MALFORMED')

    def test_name_set_changes_even_same_length_are_detected(self):
        for first, second in ((b'first\0', b'other\0'), (b'', b'name\0'), (b'name\0', b'')):
            self.assert_blocked(self.observe(first, second)[0], 'NAME_LIST_CHANGED')

    def test_descriptor_identity_and_metadata_drift_at_each_boundary_fail_closed(self):
        fields = ('st_dev', 'st_ino', 'st_mode', 'st_nlink', 'st_gid', 'st_size',
                  'st_mtime_ns', 'st_ctime_ns', 'st_flags')
        for field in fields:
            changed = info(**{field: getattr(info(), field) + 1})
            for boundary in (1, 2):
                snapshots = [info(), info(), info()]
                snapshots[boundary] = changed
                with self.subTest(field=field, boundary=boundary):
                    result = self.observe(b'com.apple.provenance\0', snapshots=snapshots)[0]
                    self.assert_blocked(result, 'METADATA_CHANGED')
        self.assert_blocked(self.observe(snapshots=[info(), info(st_uid=502)])[0],
                            'OBJECT_NOT_OWNED')
        self.assert_blocked(self.observe(snapshots=[info(), OSError(errno.EBADF, 'PRIVATE')])[0],
                            'INVALID_DESCRIPTOR')

    def test_changed_caller_identity_is_not_observation_success(self):
        with patch.object(m.sys, 'platform', 'darwin'), \
                patch.object(m.os, 'fstat', return_value=info()), \
                patch.object(m.os, 'geteuid', side_effect=[501, 502], create=True), \
                patch.object(m.ctypes, 'CDLL', return_value=Library(NativeList(0, 0))):
            self.assert_blocked(m.observe_fd(17), 'CALLER_IDENTITY_CHANGED')

    def test_cancellation_discards_partial_observation(self):
        for query in (NativeList(KeyboardInterrupt()), NativeList(2, b'x\0', KeyboardInterrupt())):
            result = self.observe(query=query)[0]
            self.assertEqual(result['observation_state'], 'cancelled')
            self.assertEqual(result['code'], 'CANCELLED')
            self.assertIsNone(result['xattr_count'])
            self.assert_unestablished(result)

    def test_no_path_content_value_acl_write_close_or_descriptor_offset_io(self):
        denied = ('open', 'close', 'dup', 'dup2', 'read', 'pread', 'write', 'pwrite', 'lseek',
                  'stat', 'lstat', 'listdir', 'scandir', 'walk', 'ftruncate', 'fchmod', 'fchown',
                  'fsync', 'rename', 'replace', 'unlink', 'listxattr', 'getxattr', 'setxattr',
                  'removexattr')
        with contextlib.ExitStack() as stack:
            guards = [stack.enter_context(patch.object(m.os, name,
                side_effect=AssertionError('forbidden object IO'), create=True)) for name in denied]
            stack.enter_context(patch('builtins.open', side_effect=AssertionError('path IO')))
            outcomes = [self.observe(b'com.apple.provenance\0'),
                        self.observe(query=NativeList((-1, errno.EBADF))),
                        self.observe(query=NativeList(KeyboardInterrupt()))]
            self.assertEqual(outcomes[0][0]['observation_state'], 'observed')
            self.assertEqual(outcomes[1][0]['code'], 'INVALID_DESCRIPTOR')
            self.assertEqual(outcomes[2][0]['code'], 'CANCELLED')
            for _, _, library, *_ in outcomes:
                self.assertEqual(library.symbols, ['flistxattr'])
            for guard in guards:
                guard.assert_not_called()

    def test_module_has_no_import_time_native_or_filesystem_operations(self):
        spec = importlib.util.spec_from_file_location('observer_import_check', SCRIPT)
        module = importlib.util.module_from_spec(spec)
        with patch.object(m.ctypes, 'CDLL') as load, patch.object(m.os, 'fstat') as fstat:
            spec.loader.exec_module(module)
        load.assert_not_called()
        fstat.assert_not_called()

    def test_static_io_surface_has_only_selected_fd_stat_and_name_read(self):
        tree = ast.parse(SCRIPT.read_text(encoding='utf-8'))
        os_calls = {node.func.attr for node in ast.walk(tree)
                    if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute)
                    and isinstance(node.func.value, ast.Name) and node.func.value.id == 'os'}
        self.assertEqual(os_calls, {'fstat', 'geteuid'})
        native_symbols = {node.attr for node in ast.walk(tree)
                          if isinstance(node, ast.Attribute) and isinstance(node.value, ast.Attribute)
                          and node.value.attr == '_library'}
        self.assertEqual(native_symbols, {'flistxattr'})

    def test_cli_requires_one_fd_and_never_echoes_untrusted_inputs(self):
        for args in ([], ['--fd', 'PRIVATE-PATH'], ['--fd', '17', '--fd', '18'],
                     ['--path', 'PRIVATE-PATH'], ['--fd', '17', 'PRIVATE-NAME'], ['--f', '17']):
            output, errors = io.StringIO(), io.StringIO()
            with contextlib.redirect_stdout(output), contextlib.redirect_stderr(errors), \
                    patch.object(m, 'observe_fd') as observe:
                self.assertEqual(m.main(args), 1)
            observe.assert_not_called()
            self.assertEqual(json.loads(output.getvalue())['code'], 'INPUT_INVALID')
            self.assertEqual(errors.getvalue(), '')
            self.assertNotIn('PRIVATE', output.getvalue())

    def test_cli_forwards_only_integer_and_uses_fixed_exit_codes(self):
        for state, expected in (('observed', 0), ('blocked', 1), ('unsupported', 1), ('cancelled', 2)):
            result = m._result()
            result['observation_state'] = state
            output = io.StringIO()
            with contextlib.redirect_stdout(output), patch.object(m, 'observe_fd', return_value=result) as observe:
                self.assertEqual(m.main(['--fd', '17']), expected)
            observe.assert_called_once_with(17)
            self.assertEqual(json.loads(output.getvalue()), result)

    def test_help_explains_inherited_descriptor_scope_without_external_docs(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), self.assertRaises(SystemExit) as caught:
            m.main(['--help'])
        self.assertEqual(caught.exception.code, 0)
        help_text = ' '.join(output.getvalue().split())
        for statement in ('pass_fds', 'shell=False', 'No paths', 'already-open', 'authorizes',
                          'ACLs are not read', 'writer exclusion', 'permission to write'):
            self.assertIn(statement, help_text)


if __name__ == '__main__':
    unittest.main()
