"""Synthetic Windows API fixtures only, including on Windows CI."""
import ctypes
import dataclasses
import importlib.util
import json
from pathlib import Path
import pickle
import sys
import unittest
from unittest import mock

PATH = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/windows_native_context.py'
spec = importlib.util.spec_from_file_location('windows_native_context_tested', PATH)
m = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = m
spec.loader.exec_module(m)
SID = b'\x01\x02\x00\x00\x00\x00\x00\x05' + (21).to_bytes(4, 'little') + (123).to_bytes(4, 'little')
IDENTITY = m._Identity(321, 654, 1, 1, 1, 0, 0, SID, (10, 0), (20, 0), (30, 0), 0, 0, 0, 0)
PATHS = ('C:\\Python\\python.exe', 'C:\\work', 'C:\\Python', 'C:\\Python')


class ContextTests(unittest.TestCase):
    def setUp(self):
        self.platform = mock.patch.object(m.sys, 'platform', 'win32')
        self.platform.start()
        self.addCleanup(self.platform.stop)
        self.api = mock.patch.object(m, '_WindowsAPI')
        self.factory = self.api.start()
        self.addCleanup(self.api.stop)
        self.factory.return_value.read.return_value = IDENTITY
        self.runtime = mock.patch.object(m, '_runtime', return_value=PATHS)
        self.runtime.start()
        self.addCleanup(self.runtime.stop)

    def assert_code(self, code, function, *args, **kwargs):
        with self.assertRaisesRegex(m.ContextError, '^' + code + '$'):
            function(*args, **kwargs)

    def test_observation_never_binds_or_authorizes(self):
        h = m.capture_current_context()
        report = m.recheck_context(h)
        self.assertEqual(report['binding_state'], 'blocked')
        self.assertEqual(report['desktop_user_relation'], 'unknown')
        self.assertEqual(report['gate_state'], 'closed')
        self.assertEqual(report['runtime_integrity'], 'not_verified')
        self.assertEqual(report['native_platform_validation'], 'not_run')

    def test_private_and_not_persistable(self):
        h = m.capture_current_context()
        for text in (repr(h), json.dumps(m.describe_context(h))):
            for secret in ('321', '654', '123', 'C:\\', str(SID)):
                self.assertNotIn(secret, text)
        with self.assertRaises(TypeError):
            pickle.dumps(h)

    def test_invalid_handles(self):
        for h in ({}, None, dataclasses.replace(m.capture_current_context(), _marker=object())):
            self.assert_code('INPUT_INVALID', m.recheck_context, h)

    def test_invalid_budget(self):
        for v in (True, None, '1', 0, 61, float('nan'), float('inf'), 10**1000):
            self.assert_code('INPUT_INVALID', m.capture_current_context, max_age_seconds=v)

    def test_cancelled_before_native(self):
        self.assert_code('CANCELLED', m.capture_current_context, cancelled=lambda: True)
        self.factory.assert_not_called()

    def test_unsupported_platform_no_calls(self):
        with mock.patch.object(m.sys, 'platform', 'linux'):
            self.assert_code('UNSUPPORTED_PLATFORM', m.capture_current_context)
        self.factory.assert_not_called()

    def test_native_exceptions_sanitized(self):
        for error, code in ((PermissionError('PRIVATE'), 'PERMISSION_DENIED'),
                            (OSError('PRIVATE'), 'CONTEXT_UNKNOWN'),
                            (AttributeError('PRIVATE'), 'CONTEXT_UNKNOWN')):
            self.factory.side_effect = error
            self.assert_code(code, m.capture_current_context)

    def test_changed_during_capture(self):
        self.factory.return_value.read.side_effect = [IDENTITY, dataclasses.replace(IDENTITY, modified_id=(31, 0))]
        self.assert_code('CONTEXT_CHANGED', m.capture_current_context)

    def test_changed_after_capture(self):
        for field, replacement in (('pid', 322), ('thread_id', 655), ('sid', SID[:-1] + b'\x01'),
                                   ('token_id', (11, 0)), ('authentication_id', (21, 0)),
                                   ('modified_id', (31, 0))):
            self.factory.return_value.read.return_value = IDENTITY
            h = m.capture_current_context()
            self.factory.return_value.read.return_value = dataclasses.replace(IDENTITY, **{field: replacement})
            self.assert_code('CONTEXT_CHANGED', m.recheck_context, h)

    def test_runtime_changed(self):
        h = m.capture_current_context()
        with mock.patch.object(m, '_runtime', return_value=PATHS + ('changed',)):
            self.assert_code('CONTEXT_CHANGED', m.recheck_context, h)

    def test_expiry_and_clock_reversal(self):
        h = m.capture_current_context()
        for now in (h._expires, h._created - 1):
            with mock.patch.object(m.time, 'monotonic', return_value=now):
                self.assert_code('CONTEXT_EXPIRED', m.recheck_context, h)

    def test_capture_clock_reversal(self):
        for readings in ([100, 99, 98, 97, 96], [100, 101, 100.5],
                         [100, 101, 102, 101.5], [100, 101, 102, 103, 102.5]):
            with mock.patch.object(m.time, 'monotonic', side_effect=readings):
                self.assert_code('CONTEXT_EXPIRED', m.capture_current_context)

    def test_recheck_clock_reversal_during_collection(self):
        h = m.capture_current_context()
        t = h._created
        for offsets in ([1, .5], [1, 2, 1.5], [1, 2, 3, 2.5], [1, 2, 3, 4, 3.5]):
            with mock.patch.object(m.time, 'monotonic', side_effect=[t + n for n in offsets]):
                self.assert_code('CONTEXT_EXPIRED', m.recheck_context, h)

    def test_reject_foreign_service_and_elevation(self):
        for field, value in (('process_session', 0), ('token_session', 2), ('console_session', 2),
                             ('elevated', 1), ('app_container', 1), ('restricted', 1), ('ui_access', 1)):
            self.assert_code('CONTEXT_FOREIGN', m._validate_identity,
                             dataclasses.replace(IDENTITY, **{field: value}))
        for rid in (18, 19, 20):
            sid = b'\x01\x01\x00\x00\x00\x00\x00\x05' + rid.to_bytes(4, 'little')
            self.assert_code('CONTEXT_FOREIGN', m._validate_identity, dataclasses.replace(IDENTITY, sid=sid))

    def test_remote_inactive(self):
        for field, value in (('state', 4), ('protocol', 2)):
            self.assert_code('CONTEXT_INACTIVE_OR_REMOTE', m._validate_identity,
                             dataclasses.replace(IDENTITY, **{field: value}))

    def test_malformed_identity(self):
        for field, value in (('pid', True), ('state', -1), ('sid', b'bad'),
                             ('token_id', (True, 0)), ('token_id', [1, 0])):
            self.assert_code('CONTEXT_UNKNOWN', m._validate_identity,
                             dataclasses.replace(IDENTITY, **{field: value}))

    def test_deadline_checked_after_reads(self):
        with mock.patch.object(m.time, 'monotonic', side_effect=[0, 0, 31]):
            self.assert_code('CONTEXT_EXPIRED', m.capture_current_context)


class APIBoundaryTests(unittest.TestCase):
    def setUp(self):
        # Never construct _WindowsAPI or load native DLLs in this test suite.
        self.api = object.__new__(m._WindowsAPI)

    def test_system32_loader_and_abi_declarations(self):
        libs = [mock.Mock(), mock.Mock(), mock.Mock()]
        with mock.patch.object(m.ctypes, 'WinDLL', side_effect=libs, create=True) as load:
            api = m._WindowsAPI()
        self.assertEqual(load.call_args_list, [mock.call(name, use_last_error=True, winmode=0x800)
            for name in ('kernel32.dll', 'advapi32.dll', 'wtsapi32.dll')])
        declarations = [
            (api.pid, m._U32, []), (api.tid, m._U32, []),
            (api.process, m._PTR, []), (api.thread, m._PTR, []),
            (api.session, m._I32, [m._U32, ctypes.POINTER(m._U32)]),
            (api.console, m._U32, []), (api.close, m._I32, [m._PTR]),
            (api.open_process, m._I32, [m._PTR, m._U32, ctypes.POINTER(m._PTR)]),
            (api.open_thread, m._I32, [m._PTR, m._U32, m._I32, ctypes.POINTER(m._PTR)]),
            (api.info, m._I32, [m._PTR, m._I32, m._PTR, m._U32, ctypes.POINTER(m._U32)]),
            (api.query, m._I32, [m._PTR, m._U32, m._I32, ctypes.POINTER(m._PTR), ctypes.POINTER(m._U32)]),
            (api.free, None, [m._PTR]),
        ]
        for function, result, args in declarations:
            self.assertIs(function.restype, result)
            self.assertEqual(function.argtypes, args)
            function.assert_not_called()

    def test_impersonation_token_closed_and_rejected(self):
        self.api.thread = lambda: -2
        self.api.open_thread = mock.Mock(return_value=1)
        self.api.close = mock.Mock(return_value=1)
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_FOREIGN'):
            self.api._no_impersonation()
        self.api.close.assert_called_once()
        self.assertEqual(self.api.open_thread.call_args.args[1:3], (8, 1))

    def test_only_no_token_error_accepted(self):
        self.api.thread = lambda: -2
        self.api.open_thread = lambda *a: 0
        with mock.patch.object(m.ctypes, 'get_last_error', return_value=1008, create=True):
            self.api._no_impersonation()
        for code in (5, 1347, 0):
            with mock.patch.object(m.ctypes, 'get_last_error', return_value=code, create=True):
                with self.assertRaises(m.ContextError):
                    self.api._no_impersonation()

    def test_wts_exact_owned_session_and_free(self):
        value = ctypes.c_uint16(0)
        def query(server, session, kind, pointer, length):
            self.assertIsNone(server)
            self.assertEqual((session, kind), (0xffffffff, 16))
            pointer._obj.value = ctypes.addressof(value)
            length._obj.value = 2
            return 1
        self.api.query, self.api.free = query, mock.Mock()
        self.assertEqual(self.api._wts(16, ctypes.c_uint16), 0)
        self.api.free.assert_called_once()

    def test_wts_wrong_length_still_freed(self):
        value = ctypes.c_uint16(0)
        def query(server, session, kind, pointer, length):
            pointer._obj.value = ctypes.addressof(value)
            length._obj.value = 3
            return 1
        self.api.query, self.api.free = query, mock.Mock()
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            self.api._wts(16, ctypes.c_uint16)
        self.api.free.assert_called_once()

    def test_sid_buffer_and_pointer_bounds(self):
        for invalid in (False, True):
            def info(token, kind, buffer, size, length):
                self.assertEqual((kind, size), (1, 256))
                offset = ctypes.sizeof(m._TokenUser)
                m._TokenUser.from_buffer(buffer).sid = ctypes.addressof(buffer) + (255 if invalid else offset)
                ctypes.memmove(ctypes.addressof(buffer) + offset, SID, len(SID))
                length._obj.value = offset + len(SID)
                return 1
            self.api.info = info
            if invalid:
                with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
                    self.api._sid(1)
            else:
                self.assertEqual(self.api._sid(1), SID)

    def test_fixed_length_enforced(self):
        def info(token, kind, value, size, length):
            length._obj.value = size + 1
            return 1
        self.api.info = info
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            self.api._fixed(1, 12, m._U32)

    def test_close_failure(self):
        self.api.close = lambda h: 0
        with self.assertRaisesRegex(m.ContextError, 'CLEANUP_FAILED'):
            self.api._close(1)

    def test_foreign_session_never_queries_other_session(self):
        self.api._no_impersonation = lambda: None
        self.api.pid, self.api.tid = lambda: 123, lambda: 456
        self.api.session = lambda pid, output: setattr(output._obj, 'value', 2) or 1
        self.api.console = lambda: 1
        self.api.open_process = mock.Mock()
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_FOREIGN'):
            self.api.read()
        self.api.open_process.assert_not_called()

    def test_complete_owned_native_read_and_cleanup(self):
        self.api._no_impersonation = mock.Mock()
        self.api.pid, self.api.tid = lambda: 321, lambda: 654
        self.api.session = lambda pid, output: setattr(output._obj, 'value', 1) or 1
        self.api.console = lambda: 1
        self.api.process = lambda: -1
        def open_process(process, access, output):
            self.assertEqual((process, access), (-1, 8))
            output._obj.value = 42
            return 1
        self.api.open_process = open_process
        self.api.close = mock.Mock(return_value=1)
        self.api._sid = lambda token: SID
        stats = m._Statistics()
        stats.kind, stats.token.low, stats.authentication.low, stats.modified.low = 1, 10, 20, 30
        def fixed(token, kind, structure):
            self.assertEqual(token.value, 42)
            return stats if kind == 10 else m._U32(1 if kind == 12 else 0)
        self.api._fixed = fixed
        self.api._wts = mock.Mock(return_value=0)
        self.assertEqual(self.api.read(), IDENTITY)
        self.api.close.assert_called_once()
        self.assertEqual(self.api._no_impersonation.call_count, 2)
        self.api.close.reset_mock()
        self.api._wts.side_effect = m.ContextError('CONTEXT_UNKNOWN')
        with self.assertRaisesRegex(m.ContextError, 'CONTEXT_UNKNOWN'):
            self.api.read()
        self.api.close.assert_called_once()

    def test_runtime_syntax_only(self):
        for path, acceptable in [('C:\\Python\\python.exe', True), ('Z:\\mapped\\python.exe', True),
                                 ('\\\\server\\share', False), ('C:relative', False),
                                 ('C:\\foo\\..\\bar', False), ('C:\\foo:bar', False),
                                 ('C:\\foo.\\python.exe', False)]:
            with mock.patch.object(m.sys, 'executable', path), mock.patch.object(m.os, 'getcwd', return_value='C:\\work'), mock.patch.object(m.sys, 'prefix', 'C:\\Python'), mock.patch.object(m.sys, 'base_prefix', 'C:\\Python'):
                if acceptable:
                    self.assertEqual(m._runtime()[0], path)
                else:
                    with self.assertRaisesRegex(m.ContextError, 'RUNTIME_PATH_INVALID'):
                        m._runtime()


if __name__ == '__main__':
    unittest.main()
