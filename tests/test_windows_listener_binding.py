"""Offline mocked tests; native tests only on opted-in ephemeral Windows CI."""
import ctypes as C
import importlib.util
import json
import os
from pathlib import Path
import socket
import unittest
from unittest.mock import Mock, patch
from types import SimpleNamespace

PATH = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/windows_listener_binding.py'
spec = importlib.util.spec_from_file_location('windows_listener_binding', PATH)
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)


def selection(**changes):
    values = dict(target_ref='synthetic-target', namespace_ref='synthetic-namespace',
                  desktop_user_ref='synthetic-user', host='127.0.0.1', port=54321,
                  process_id=123, creation_filetime=456)
    values.update(changes)
    return w.Selection(**values)


def observed(**changes):
    values = dict(creation_filetime=456, same_user=True,
                  listeners=(('127.0.0.1', 123),))
    values.update(changes)
    return w._Observation(**values)


class Fake:
    def __init__(self, *values):
        self.values = list(values or (observed(), observed()))
        self.calls = 0

    def observe(self, *args):
        self.calls += 1
        item = self.values.pop(0)
        if isinstance(item, Exception):
            raise item
        return item


class WindowsListenerTests(unittest.TestCase):
    def check(self, expected=None, **kwargs):
        kwargs.setdefault('approve_read', lambda s, b: True)
        kwargs.setdefault('verify_context', lambda s: True)
        kwargs.setdefault('run_native', lambda call, deadline, cancelled: call())
        kwargs.setdefault('_reader', Fake())
        result = w.verify_listener(kwargs.pop('selection', selection()), **kwargs)
        self.assertEqual(result['error_code'], expected)
        self.assertEqual(result['listener_owner_verified'], expected is None)
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['changes'], [])
        self.assertNotIn('secret-sentinel', json.dumps(result))
        return result

    def test_success_no_private_metadata(self):
        result = self.check()
        self.assertNotIn('54321', json.dumps(result))
        self.assertNotIn('127.0.0.1', json.dumps(result))
        self.assertEqual(result['user_relation'], 'same')
        self.assertEqual(result['namespace_evidence'], 'host_callback_only_not_native_verified')
        self.assertEqual(result['coverage'], 'selected_listener_host_asserted_namespace')

    def test_denied_or_boolean_approval_never_reads(self):
        for approval in (False, True, lambda s, b: False):
            reader = Fake()
            self.check('AUTHORIZATION_MISSING', approve_read=approval, _reader=reader)
            self.assertEqual(reader.calls, 0)

    def test_context_and_runner_required(self):
        self.check('TARGET_USER_CONTEXT_MISMATCH', verify_context=lambda s: False)
        self.check('AUTHORIZATION_MISSING', run_native=None)

    def test_bad_targets(self):
        for host in ('localhost', '0.0.0.0', '::', '192.0.2.1', '127.1', '::1%0'):
            result = w.verify_listener(selection(host=host), approve_read=None,
                                       verify_context=None, run_native=None)
            self.assertIn(result['error_code'], ('CONTROLLER_NOT_BOUND', 'INPUT_INVALID'))
        for fields in ({'port': True}, {'process_id': 0}, {'creation_filetime': 0},
                       {'target_ref': ''}):
            self.check('INPUT_INVALID', selection=selection(**fields))

    def test_missing_wildcard_public_duplicate_and_wrong_pid(self):
        for listeners in ((), (('0.0.0.0', 123),), (('::', 123),),
                (('192.0.2.1', 123),), (('127.0.0.1', 999),),
                (('127.0.0.1', 123), ('127.0.0.1', 123)),
                (('127.0.0.1', 123), ('::1', 123))):
            self.check('CONTROLLER_NOT_BOUND', _reader=Fake(observed(listeners=listeners)))

    def test_pid_reuse_user_and_namespace_mismatch(self):
        self.check('CONTROLLER_NOT_BOUND', _reader=Fake(observed(creation_filetime=999)))
        self.check('TARGET_USER_CONTEXT_MISMATCH', _reader=Fake(observed(same_user=False)))
        self.check('TARGET_USER_CONTEXT_MISMATCH', verify_context=lambda s: False)

    def test_stale_snapshot(self):
        self.check('SNAPSHOT_CHANGED_DURING_AUDIT',
                   _reader=Fake(observed(), observed(creation_filetime=999)))

    def test_revocation(self):
        count = [0]
        def approve(s, b):
            count[0] += 1
            return count[0] < 3
        reader = Fake()
        self.check('AUTHORIZATION_MISSING', approve_read=approve, _reader=reader)
        self.assertEqual(reader.calls, 1)

    def test_final_approval_context_drift(self):
        count, valid = [0], [True]
        def approve(s, b):
            count[0] += 1
            if count[0] == 4:
                valid[0] = False
            return True
        self.check('TARGET_USER_CONTEXT_MISMATCH', approve_read=approve,
                   verify_context=lambda s: valid[0])

    def test_native_liveness_uses_wait_not_undefined_exit_time(self):
        native = w._NativeReader.__new__(w._NativeReader)
        def times(process, creation, exit_time, kernel, user):
            creation._obj.value = 456
            exit_time._obj.value = 999  # undefined while running, must be ignored
            return True
        native.k = SimpleNamespace(GetProcessTimes=times, WaitForSingleObject=Mock(return_value=258))
        self.assertEqual(native._times(42), 456)
        native.k.WaitForSingleObject.assert_called_once_with(42, 0)
        for status, error in ((0, 'SNAPSHOT_CHANGED_DURING_AUDIT'),
                              (0xffffffff, 'PERMISSION_DENIED'),
                              (128, 'NATIVE_READ_FAILED')):
            native.k.WaitForSingleObject.return_value = status
            with patch.object(w.C, 'get_last_error', return_value=5, create=True):
                with self.assertRaises(w.BindingError) as caught:
                    native._times(42)
            self.assertEqual(caught.exception.code, error)

    def test_cancellation_timeout_and_sanitized_errors(self):
        self.check('CANCELLED', cancelled=lambda: True)
        for exc, code in ((TimeoutError('secret-sentinel'), 'TIMEOUT'),
                          (PermissionError('secret-sentinel'), 'PERMISSION_DENIED'),
                          (RuntimeError('secret-sentinel'), 'NATIVE_READ_FAILED'),
                          (w.BindingError('secret-sentinel'), 'NATIVE_READ_FAILED')):
            self.check(code, _reader=Fake(exc))
        self.check('INPUT_INVALID', budget=w.Budget(max_seconds=float('nan')))
        self.check('INPUT_INVALID', budget=w.Budget(max_table_bytes=1048577))

    def test_host_timeout_and_cancellation_after_native_read(self):
        def timeout(*args):
            raise TimeoutError('secret-sentinel')
        self.check('TIMEOUT', run_native=timeout)
        state = [False]
        def cancel_after(call, deadline, cancelled):
            value = call()
            state[0] = True
            return value
        self.check('CANCELLED', run_native=cancel_after, cancelled=lambda: state[0])

    def test_native_missing_rights_impersonation_and_identity_preflight(self):
        native = w._NativeReader.__new__(w._NativeReader)
        native.k = SimpleNamespace(GetCurrentThread=lambda: 1, OpenProcess=Mock(return_value=0),
                                   CloseHandle=Mock())
        native.a = SimpleNamespace(OpenThreadToken=Mock(return_value=False))
        native.i = SimpleNamespace(GetExtendedTcpTable=Mock())
        with patch.object(w.C, 'get_last_error', side_effect=[1008, 5], create=True):
            with self.assertRaises(w.BindingError) as caught:
                native.observe(selection(), w.Budget(), lambda: None)
        self.assertEqual(caught.exception.code, 'PERMISSION_DENIED')
        native.i.GetExtendedTcpTable.assert_not_called()
        native.a.OpenThreadToken.return_value = True
        with self.assertRaises(w.BindingError) as caught:
            native.observe(selection(), w.Budget(), lambda: None)
        self.assertEqual(caught.exception.code, 'TARGET_USER_CONTEXT_MISMATCH')
        native.a.OpenThreadToken.return_value = False
        native.k.OpenProcess.return_value = 42
        native._times = lambda handle: 999
        with patch.object(w.C, 'get_last_error', return_value=1008, create=True):
            with self.assertRaises(w.BindingError) as caught:
                native.observe(selection(), w.Budget(), lambda: None)
        self.assertEqual(caught.exception.code, 'CONTROLLER_NOT_BOUND')
        native.k.CloseHandle.assert_called_with(42)
        native.k.OpenProcess.assert_called_with(0x101000, False, 123)
        native.i.GetExtendedTcpTable.assert_not_called()

    def test_ipv6_and_alternate_numeric_loopback(self):
        for host in ('::1', '127.0.0.2'):
            row = observed(listeners=((host, 123),))
            self.check(selection=selection(host=host), _reader=Fake(row, row))

    def test_native_unsupported_here(self):
        if os.name != 'nt':
            self.check('PLATFORM_UNSUPPORTED', _reader=None)

    def test_parser_ipv4_ipv6_and_bounds(self):
        for family, row_type, address in ((2, w._Row4, '127.0.0.1'), (23, w._Row6, '::1')):
            row = row_type()
            row.state, row.port, row.pid = 2, socket.htons(54321), 123
            if family == 2:
                row.address = int.from_bytes(socket.inet_pton(socket.AF_INET, address), 'little')
            else:
                row.address[:] = socket.inet_pton(socket.AF_INET6, address)
            raw = (1).to_bytes(4, 'little') + bytes(row)
            self.assertEqual(w._selected_rows(raw, family, 54321, w.Budget()), [(address, 123)])
            self.assertEqual(w._selected_rows(raw, family, 54322, w.Budget()), [])
            for malformed, budget in ((raw[:-1], w.Budget()),
                                      (raw, w.Budget(max_table_bytes=4)),
                                      ((2).to_bytes(4, 'little') + bytes(row), w.Budget(max_rows=1))):
                with self.assertRaises(w.BindingError):
                    w._selected_rows(malformed, family, 54321, budget)


@unittest.skipUnless(os.name == 'nt' and os.environ.get('GUARDIAN_WINDOWS_LISTENER_CI') == '1',
                     'Requires explicit opt-in on ephemeral Windows CI; no user process audit')
class NativeEphemeralWindowsTests(unittest.TestCase):
    def test_owned_ephemeral_listener_both_families(self):
        # Approval is scoped to this fixture's own current PID and temporary
        # socket. The outer CI job supplies the hard process lifetime timeout.
        native = w._NativeReader()
        for family, host in ((socket.AF_INET, '127.0.0.1'), (socket.AF_INET6, '::1')):
            with self.subTest(host=host), socket.socket(family, socket.SOCK_STREAM) as sock:
                sock.bind((host, 0))
                sock.listen(1)  # no connections or controller requests
                s = selection(host=host, port=sock.getsockname()[1], process_id=os.getpid(),
                              creation_filetime=native._times(native.k.GetCurrentProcess()))
                kwargs = dict(approve_read=lambda target, budget: target is s,
                              verify_context=lambda target: target is s,
                              run_native=lambda call, deadline, cancelled: call())
                result = w.verify_listener(s, **kwargs)
                self.assertEqual(result['error_code'], None)
                self.assertTrue(result['listener_owner_verified'])
                sock.close()
                result = w.verify_listener(s, **kwargs)
                self.assertFalse(result['listener_owner_verified'])
                self.assertEqual(result['error_code'], 'CONTROLLER_NOT_BOUND')


if __name__ == '__main__':
    unittest.main()
