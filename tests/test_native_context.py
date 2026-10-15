"""Synthetic OS/API fixtures only: never invoke real Apple/session APIs."""
import ctypes
from dataclasses import FrozenInstanceError, replace
import importlib
import json
from pathlib import Path
import pickle
import posixpath
import stat
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import native_context as m


def identity(**changes):
    values = dict(pid=100, uid=501, euid=501, gid=20, egid=20, groups=(20, 80),
        posix_session=100, security_session=901, security_attributes=0x10,
        console_uid=501, graphical_uid=501, on_console=True, login_done=True)
    values.update(changes)
    return m._Identity(**values)


def runtime(**changes):
    values = dict(executable='/trusted/python', directory='/trusted', prefix='/trusted',
        base_prefix='/trusted', identities=(), screen='root_owned_mode_screen_only')
    values.update(changes)
    return m._Runtime(**values)


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.platform = patch.object(m.sys, 'platform', 'darwin')
        self.platform.start()
        self.api_patch = patch.object(m, '_MacAPI')
        self.api = self.api_patch.start().return_value
        self.api.read.return_value = identity()
        self.runtime_patch = patch.object(m, '_runtime', return_value=runtime())
        self.runtime_patch.start()
        self.addCleanup(patch.stopall)

    def test_capture_and_recheck_redacted(self):
        handle = m.capture_current_context()
        result = m.recheck_context(handle)
        self.assertEqual(result['desktop_user_relation'], 'same_at_observation')
        self.assertEqual(result['runtime_integrity'], 'not_verified')
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['network_namespace'], 'unknown')
        self.assertEqual(result['target_association'], 'requires_trusted_host_assertion')
        raw = json.dumps(result) + repr(handle)
        for private in ('501', '901', '/trusted', '100'):
            self.assertNotIn(private, raw)
        self.assertEqual(self.api.read.call_count, 4)

    def test_private_handle_immutable_not_pickleable(self):
        handle = m.capture_current_context()
        with self.assertRaises(FrozenInstanceError):
            handle._identity = identity(uid=2)
        with self.assertRaises(TypeError):
            pickle.dumps(handle)

    def test_json_and_bools_not_handles(self):
        for value in (True, {'approved': True}, {}, None):
            with self.assertRaisesRegex(m.ContextError, 'INPUT_INVALID'):
                m.recheck_context(value)

    def test_unsupported_does_not_load_native_library(self):
        for platform in ('win32', 'linux'):
            with patch.object(m.sys, 'platform', platform), patch.object(m, '_MacAPI') as api:
                with self.assertRaisesRegex(m.ContextError, 'UNSUPPORTED_PLATFORM'):
                    m.capture_current_context()
                api.assert_not_called()

    def test_reject_foreign_inactive_unknown(self):
        cases = [({'uid': 0, 'euid': 0}, 'TARGET_USER_CONTEXT_MISMATCH'),
            ({'euid': 502}, 'TARGET_USER_CONTEXT_MISMATCH'),
            ({'egid': 80}, 'TARGET_USER_CONTEXT_MISMATCH'),
            ({'console_uid': 502}, 'TARGET_USER_CONTEXT_MISMATCH'),
            ({'graphical_uid': 502}, 'TARGET_USER_CONTEXT_MISMATCH'),
            ({'on_console': False}, 'CONTEXT_INACTIVE'),
            ({'login_done': False}, 'CONTEXT_INACTIVE'),
            ({'security_attributes': 0}, 'CONTEXT_INACTIVE'),
            ({'security_attributes': 0x1010}, 'CONTEXT_FOREIGN'),
            ({'security_attributes': 0x11}, 'CONTEXT_FOREIGN'),
            ({'security_session': 0xffffffff}, 'CONTEXT_UNKNOWN'),
            ({'on_console': 1}, 'CONTEXT_UNKNOWN'),
            ({'pid': True}, 'CONTEXT_UNKNOWN')]
        for fields, error in cases:
            with self.subTest(fields=fields):
                self.api.read.return_value = identity(**fields)
                with self.assertRaisesRegex(m.ContextError, error):
                    m.capture_current_context()

    def test_changes_during_capture_and_after_capture(self):
        self.api.read.side_effect = [identity(), identity(security_session=902)]
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_CHANGED'):
            m.capture_current_context()
        self.api.read.side_effect = None
        handle = m.capture_current_context()
        for change in ({'pid': 101}, {'security_session': 902}, {'groups': (20,)}):
            self.api.read.return_value = identity(**change)
            with self.assertRaisesRegex(m.ContextError, 'CONTEXT_CHANGED'):
                m.recheck_context(handle)

    def test_runtime_replacement_rejected(self):
        handle = m.capture_current_context()
        with patch.object(m, '_runtime', return_value=runtime(identities=(('replacement',),))):
            with self.assertRaisesRegex(m.ContextError, 'CONTEXT_CHANGED'):
                m.recheck_context(handle)

    def test_path_screen_is_not_runtime_verifier(self):
        with patch.object(m, '_runtime', return_value=runtime(screen='rejected_writable_or_nonroot')):
            handle = m.capture_current_context()
            result = m.recheck_context(handle)
        self.assertEqual(result['runtime_path_screen'], 'rejected_writable_or_nonroot')
        self.assertEqual(result['runtime_integrity'], 'not_verified')
        self.assertEqual(result['gate_state'], 'closed')

    def test_expiry_cancel_and_clock_reversal(self):
        with patch.object(m.time, 'monotonic', return_value=10):
            handle = m.capture_current_context(max_age_seconds=1)
        for clock in (9, 11):
            with patch.object(m.time, 'monotonic', return_value=clock):
                with self.assertRaisesRegex(m.ContextError, 'CONTEXT_EXPIRED'):
                    m.recheck_context(handle)
        with self.assertRaisesRegex(m.ContextError, 'CANCELLED'):
            m.capture_current_context(cancelled=lambda: True)
        for age in (True, 0, 61, float('nan'), float('inf'), 10**1000, '1'):
            with self.assertRaisesRegex(m.ContextError, 'INPUT_INVALID'):
                m.capture_current_context(max_age_seconds=age)

    def test_errors_do_not_leak_native_details(self):
        for exception, code in ((PermissionError('/secret'), 'PERMISSION_DENIED'),
                                (OSError('/secret'), 'CONTEXT_UNKNOWN')):
            self.api.read.side_effect = exception
            with self.assertRaises(m.ContextError) as caught:
                m.capture_current_context()
            self.assertEqual(str(caught.exception), code)


class PathTests(unittest.TestCase):
    def setUp(self):
        # These are synthetic macOS path fixtures, even on a Windows test host.
        # Keep POSIX lexical semantics while lstat itself remains mocked below.
        lexical = patch.object(m.os.path, 'normpath', posixpath.normpath)
        lexical.start()
        self.addCleanup(lexical.stop)

    def fake_stat(self, path):
        return SimpleNamespace(st_mode=(stat.S_IFREG | 0o755) if path.endswith('python')
            else (stat.S_IFDIR | 0o755), st_uid=0, st_gid=0, st_dev=1, st_ino=2,
            st_size=10, st_mtime_ns=20, st_ctime_ns=30)

    def test_fixed_ancestor_chain(self):
        with patch.object(m.os, 'lstat', side_effect=self.fake_stat) as lookup:
            rows, screened = m._path_identity('/trusted/python', False)
        self.assertTrue(screened)
        self.assertEqual([c.args[0] for c in lookup.call_args_list], ['/', '/trusted', '/trusted/python'])
        self.assertEqual(len(rows), 3)

    def test_nonroot_writable_and_symlink(self):
        for attr, value in (('st_uid', 501), ('st_mode', stat.S_IFREG | 0o777)):
            def lookup(path):
                result = self.fake_stat(path)
                if path.endswith('python'):
                    setattr(result, attr, value)
                return result
            with patch.object(m.os, 'lstat', side_effect=lookup):
                self.assertFalse(m._path_identity('/trusted/python', False)[1])
        result = self.fake_stat('/trusted')
        result.st_mode = stat.S_IFLNK | 0o777
        with patch.object(m.os, 'lstat', return_value=result):
            with self.assertRaisesRegex(m.ContextError, 'RUNTIME_PATH_INVALID'):
                m._path_identity('/trusted/python', False)

    def test_invalid_paths(self):
        for path in ('relative', '/x/../python', '/x//python', '/x/./python', '//x/python', '/x\0python', True):
            with self.assertRaisesRegex(m.ContextError, 'RUNTIME_PATH_INVALID'):
                m._path_identity(path, False)


class MacAPITests(unittest.TestCase):
    def api(self):
        # Mock ctypes foreign functions, not the collector: exercise ABI wiring.
        libraries = {}
        def load(path):
            library = Mock()
            libraries[path] = library
            return library
        with patch.object(m.ctypes, 'CDLL', side_effect=load) as loader:
            api = m._MacAPI()
        self.assertEqual(loader.call_count, 4)
        self.assertTrue(all(p.startswith('/System/Library/Frameworks/') for p in libraries))
        return api

    def test_signatures_and_resource_release(self):
        api = self.api()
        self.assertEqual(api.session.restype, ctypes.c_int32)
        self.assertEqual(api.graphics.restype, ctypes.c_void_p)
        def session(selector, out_session, out_attributes):
            self.assertEqual(selector, 0xffffffff)
            out_session._obj.value, out_attributes._obj.value = 901, 0x10
            return 0
        def console(store, uid, gid):
            self.assertIsNone(store)
            uid._obj.value = 501
            return 123
        api.session.side_effect = session
        api.console.side_effect = console
        api.graphics.return_value = 456
        api.type_id.return_value = api.dict_type.return_value = 3
        with patch.object(api, '_value', side_effect=[501, True, True]), \
             patch.multiple(m.os, getpid=lambda: 100, getuid=lambda: 501,
                geteuid=lambda: 501, getgid=lambda: 20, getegid=lambda: 20,
                getgroups=lambda: [80, 20], getsid=lambda p: 100, create=True):
            self.assertEqual(api.read(), identity())
        self.assertEqual([call.args[0] for call in api.release.call_args_list], [123, 456])

    def test_dictionary_released_on_bad_field(self):
        api = self.api()
        api.session.return_value = 0
        api.console.return_value = 123
        api.graphics.return_value = 456
        api.type_id.return_value = api.dict_type.return_value = 3
        with patch.object(api, '_value', side_effect=m.ContextError('CONTEXT_UNKNOWN')):
            with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
                api.read()
        self.assertEqual([call.args[0] for call in api.release.call_args_list], [123, 456])

    def test_missing_console_stops_before_graphics(self):
        api = self.api()
        api.session.return_value = 0
        api.console.return_value = None
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_INACTIVE'):
            api.read()
        api.graphics.assert_not_called()
        api.release.assert_not_called()

    def test_typed_cf_values(self):
        api = self.api()
        api.string.return_value = 123
        api.dict_value.return_value = 456
        api.type_id.return_value = api.num_type.return_value = 3
        self.assertEqual(api.string.restype, ctypes.c_void_p)
        self.assertEqual(api.string.argtypes,
                         [ctypes.c_void_p, ctypes.c_char_p, ctypes.c_uint32])
        def convert(value, kind, number):
            self.assertEqual(kind, 4)
            number._obj.value = 501
            return 1
        api.num_value.side_effect = convert
        self.assertEqual(api._value(789, 'kCGSessionUserIDKey', 'number'), 501)
        api.string.assert_called_with(None, b'kCGSSessionUserIDKey', 0x08000100)
        api.release.assert_called_once_with(123)
        api.num_value.side_effect = None
        api.num_value.return_value = 0
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            api._value(789, 'kCGSessionUserIDKey', 'number')
        self.assertEqual(api.release.call_count, 2)
        api.bool_type.return_value = 4
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            api._value(789, 'kCGSessionOnConsoleKey', 'bool')
        self.assertEqual(api.release.call_count, 3)
        api.type_id.return_value = 4
        api.bool_value.return_value = 1
        self.assertIs(api._value(789, 'kCGSessionOnConsoleKey', 'bool'), True)
        api.string.assert_called_with(None, b'kCGSSessionOnConsoleKey', 0x08000100)
        self.assertIs(api._value(789, 'kCGSessionLoginDoneKey', 'bool'), True)
        api.string.assert_called_with(None, b'kCGSessionLoginDoneKey', 0x08000100)
        api.dict_value.return_value = None
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            api._value(789, 'kCGSessionOnConsoleKey', 'bool')
        self.assertEqual(api.release.call_count, 6)

    def test_cf_key_allocation_failure_and_allowlist(self):
        api = self.api()
        api.string.return_value = None
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            api._value(789, 'kCGSessionOnConsoleKey', 'bool')
        api.release.assert_not_called()
        api.dict_value.assert_not_called()
        api.string.reset_mock()
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            api._value(789, 'arbitrary key', 'bool')
        api.string.assert_not_called()

    def test_import_has_no_native_io(self):
        with patch.object(ctypes, 'CDLL', side_effect=AssertionError('native call on import')), \
             patch.object(m.os, 'lstat', side_effect=AssertionError('path call on import')):
            importlib.reload(m)


if __name__ == '__main__':
    unittest.main()
