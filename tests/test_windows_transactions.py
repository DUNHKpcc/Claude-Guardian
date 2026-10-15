"""Mocked Linux contract tests and opt-in native Windows temporary-file smoke.

Mocks are not Windows acceptance evidence. Native smoke does not certify writes.
"""
import copy
import ctypes
from contextlib import ExitStack
import importlib.util
import json
import os
from pathlib import Path
import struct
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('windows_transactions',
    ROOT / 'skills/claude-guardian/scripts/windows_transactions.py')
w = importlib.util.module_from_spec(spec)
spec.loader.exec_module(w)
GUID_ROOT = '\\\\?\\Volume{12345678-1234-1234-1234-123456789abc}\\'
PATH = GUID_ROOT + 'synthetic\\config'


class FakeAPI:
    def __init__(self):
        self.handles = {}
        self.events = []
        self.closed = []
        self.fail = None
        self.data = b'original'
        self.change = False

    def local_volume(self, root):
        self.events.append(('local', root))

    def filesystem(self, handle):
        self.events.append(('filesystem', handle))

    def open(self, path, directory, data=False):
        handle = len(self.handles) + 1
        self.handles[handle] = (path, directory, data)
        self.events.append(('open', handle, data))
        return handle

    def close(self, handle):
        self.closed.append(handle)

    def metadata(self, handle, directory):
        if self.fail == 'metadata':
            raise w.TransactionError('REPARSE_RECALL_OR_METADATA_UNSUPPORTED')
        result = {'volume_serial': 1, 'file_id': ('a' if directory else 'b') * 32,
                  'attributes': 16 if directory else 32, 'size': 0 if directory else 8,
                  'links': 1, 'creation_time': 1, 'access_time': 2,
                  'write_time': 3, 'change_time': 4}
        if self.change and any(e[0] == 'read' for e in self.events):
            result['change_time'] = 5
        return result

    def streams(self, handle, size):
        self.events.append(('streams', handle))
        if self.fail == 'streams':
            raise w.TransactionError('ALTERNATE_OR_UNKNOWN_STREAMS_UNSUPPORTED')

    def security(self, handle):
        self.events.append(('security', handle))
        if self.fail == 'security':
            raise w.TransactionError('SECURITY_METADATA_UNAVAILABLE')
        return 'c' * 64

    def read(self, handle):
        self.events.append(('read', handle))
        return self.data


class WindowsPlans(unittest.TestCase):
    def setUp(self):
        self.api = FakeAPI()
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(w, '_native_windows', return_value=True))
        self.factory = self.stack.enter_context(patch.object(w, '_WinAPI', return_value=self.api))

    def plan(self, **kw):
        return w.plan(PATH, b'replacement', 'synthetic-target', exclusive_access=True, **kw)

    def test_read_only_plan_and_private_content_free_preview(self):
        p = self.plan()
        self.assertEqual(p['before']['sha256'], w._hash(b'original'))
        self.assertEqual(p['after_sha256'], w._hash(b'replacement'))
        self.assertEqual(p['apply_status'], 'unsupported')
        self.assertEqual(p['metadata_completeness'], 'partial')
        preview = w.preview(p)
        self.assertTrue(preview['changed'])
        self.assertNotIn('path', preview)
        self.assertNotIn('original', json.dumps(p))
        self.assertNotIn('replacement', json.dumps(p))
        self.assertEqual(self.api.closed, [4, 3, 2, 1])
        events = self.api.events
        read_open = events.index(('open', 4, True))
        self.assertLess(events.index(('streams', 3)), read_open)
        self.assertLess(events.index(('security', 3)), read_open)
        self.assertEqual(w.digest(copy.deepcopy(p)), w.digest(p))
        p['target_ref'] = 'different-target'
        self.assertNotEqual(w.digest(p), preview['plan_digest'])

    def test_host_exclusion_required_before_native_api(self):
        with self.assertRaisesRegex(w.TransactionError, '^EXCLUSIVE_ACCESS_REQUIRED$'):
            w.plan(PATH, b'new', 'synthetic')
        self.factory.assert_not_called()

    def test_bad_paths_never_open_or_echo_secrets(self):
        for path in ['C:\\secret', '\\\\server\\secret', '\\\\?\\C:\\secret',
                     GUID_ROOT, PATH + ':secret', GUID_ROOT + '..\\secret',
                     GUID_ROOT + 'secret. ', GUID_ROOT + '\x00secret']:
            with self.subTest(path=path), self.assertRaises(w.TransactionError) as caught:
                w.plan(path, b'new', 'synthetic', exclusive_access=True)
            self.assertNotIn('secret', str(caught.exception))
        self.factory.assert_not_called()

    def test_unsafe_metadata_blocks_data_read_and_closes_handles(self):
        for fail in ['metadata', 'streams', 'security']:
            self.api.fail = fail
            self.api.events.clear()
            with self.assertRaises(w.TransactionError):
                self.plan()
            self.assertFalse(any(e[0] == 'read' for e in self.api.events))
            self.assertFalse(any(e[0] == 'open' and e[2] for e in self.api.events))

    def test_concurrent_change_and_short_reads_fail(self):
        self.api.change = True
        with self.assertRaisesRegex(w.TransactionError, '^CONCURRENT_CHANGE$'):
            self.plan()
        self.api.change = False
        self.api.data = b'short'
        with self.assertRaisesRegex(w.TransactionError, '^CONCURRENT_CHANGE$'):
            self.plan()

    def test_invalid_and_expired_inputs(self):
        for ttl in [False, 0, 3601, float('inf'), float('nan')]:
            with self.subTest(ttl=ttl), self.assertRaises(w.TransactionError):
                self.plan(ttl_seconds=ttl)
        for now in [True, float('nan'), float('inf'), 1e20]:
            with self.subTest(now=now), self.assertRaises(w.TransactionError):
                self.plan(now=now)
        p = self.plan(now=time.time() - 700)
        with self.assertRaisesRegex(w.TransactionError, '^INVALID_OR_EXPIRED_PLAN$'):
            w.preview(p)
        p['before']['unexpected'] = 'x' * (w.MAX_METADATA + 1)
        with self.assertRaisesRegex(w.TransactionError, '^INVALID_PLAN$'):
            w.digest(p)

    def test_mutations_never_call_approval_or_api_even_for_approved_plan(self):
        p = self.plan()
        self.factory.reset_mock()
        approve = Mock(return_value=True)
        for operation in [lambda: w.apply(p, target_ref='synthetic-target',
                               backup_directory=GUID_ROOT + 'backups',
                               authorize=approve, exclusive_access=True),
                          lambda: w.verify(p),
                          lambda: w.rollback(p, target_ref='synthetic-target',
                               authorize=approve, exclusive_access=True)]:
            with self.assertRaisesRegex(w.TransactionError,
                                        '^WINDOWS_TRANSACTION_BACKEND_UNIMPLEMENTED$'):
                operation()
        approve.assert_not_called()
        self.factory.assert_not_called()

    def test_cancel_before_open_and_sanitized_callback_failures(self):
        for callback, code in [(lambda: True, 'CANCELLED'),
                               (Mock(side_effect=ValueError('private-secret')), 'CANCELLATION_CHECK_FAILED'),
                               (lambda: 'private-secret', 'CANCELLATION_CHECK_FAILED')]:
            with self.subTest(code=code), self.assertRaisesRegex(w.TransactionError, '^' + code + '$'):
                self.plan(cancelled=callback)
        self.factory.assert_not_called()

    def test_cancel_immediately_after_open_closes_new_handle(self):
        with self.assertRaisesRegex(w.TransactionError, '^CANCELLED$'):
            self.plan(cancelled=lambda: bool(self.api.handles))
        self.assertEqual(self.api.closed, [1])
        self.assertFalse(any(e[0] == 'read' for e in self.api.events))

    def test_cancel_after_final_read_has_no_success_plan_and_closes_all(self):
        with self.assertRaisesRegex(w.TransactionError, '^CANCELLED$'):
            self.plan(cancelled=lambda: any(e[0] == 'read' for e in self.api.events))
        self.assertEqual(self.api.closed, [4, 3, 2, 1])

    def test_callback_error_after_read_is_sanitized_and_handles_closed(self):
        def cancelled():
            if any(e[0] == 'read' for e in self.api.events):
                raise RuntimeError('private-secret-after-read')
            return False
        with self.assertRaisesRegex(w.TransactionError, '^CANCELLATION_CHECK_FAILED$'):
            self.plan(cancelled=cancelled)
        self.assertEqual(self.api.closed, [4, 3, 2, 1])

    def test_cooperative_timeout_after_read_closes_all(self):
        original_read = self.api.read
        with patch.object(w.time, 'monotonic', return_value=0) as clock:
            def slow_read(handle):
                data = original_read(handle)
                clock.return_value = 11
                return data
            self.api.read = slow_read
            with self.assertRaisesRegex(w.TransactionError, '^TIMEOUT$'):
                self.plan(budget_seconds=10)
        self.assertEqual(self.api.closed, [4, 3, 2, 1])

    def test_bad_budget_and_slow_callback_fail_before_open(self):
        for budget in [True, 0, -1, 61, 10**1000, float('nan'), float('inf'), '10']:
            with self.subTest(budget=budget), self.assertRaisesRegex(w.TransactionError, '^INVALID_BUDGET$'):
                self.plan(budget_seconds=budget)
        with patch.object(w.time, 'monotonic', return_value=0) as clock:
            def slow_callback():
                clock.return_value = 11
                return False
            with self.assertRaisesRegex(w.TransactionError, '^TIMEOUT$'):
                self.plan(cancelled=slow_callback, budget_seconds=10)
        self.factory.assert_not_called()

    def test_capability_report_cannot_enable_writes(self):
        report = w.capabilities()
        self.assertEqual(report['operations']['plan']['execution_status'], 'available_unvalidated')
        self.assertEqual(report['native_transaction_acceptance'], 'not_run')
        report['operations']['apply']['execution_status'] = 'completed'
        self.assertEqual(w.capabilities()['operations']['apply']['execution_status'], 'blocked')


class OfflinePreflight(unittest.TestCase):
    # Reuse the mocked plan fixture, not native acceptance evidence.
    setUp = WindowsPlans.setUp
    plan = WindowsPlans.plan
    def test_offline_readiness_denies_partial_security_without_io(self):
        p = self.plan()
        self.factory.reset_mock()
        with patch.object(w, '_native_windows', return_value=False):
            result = w.preflight(p, target_ref='synthetic-target')
        self.factory.assert_not_called()
        self.assertEqual(result['execution_status'], 'completed')
        self.assertEqual(result['write_readiness'], 'blocked')
        self.assertEqual(result['reason'], 'SECURITY_METADATA_UNAVAILABLE')
        self.assertEqual(result['plan_digest'], w.digest(p))
        self.assertEqual(result['source_freshness'], 'not_checked')
        self.assertEqual(result['target_binding'], 'not_checked')
        self.assertEqual(result['changes'], [])
        for secret in [PATH, 'synthetic-target', 'original', 'replacement']:
            self.assertNotIn(secret, json.dumps(result))
        result['write_readiness'] = 'ready'
        self.assertEqual(w.preflight(p, target_ref='synthetic-target')['write_readiness'], 'blocked')

    def test_preflight_mismatch_expiry_and_fake_completeness_fail(self):
        p = self.plan()
        self.factory.reset_mock()
        with self.assertRaisesRegex(w.TransactionError, '^TARGET_MISMATCH$'):
            w.preflight(p, target_ref='other')
        with self.assertRaisesRegex(w.TransactionError, '^INVALID_TARGET$'):
            w.preflight(p, target_ref=True)
        with patch.object(w.time, 'time', return_value=p['expires_at']):
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_OR_EXPIRED_PLAN$'):
                w.preflight(p, target_ref='synthetic-target')
        for field, value in [('metadata_completeness', 'complete'), ('apply_status', 'ready')]:
            forged = copy.deepcopy(p)
            forged[field] = value
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_PLAN$'):
                w.preflight(forged, target_ref='synthetic-target')
        forged = copy.deepcopy(p)
        forged['before']['security_scope'] = 'owner_group_dacl_sacl'
        with self.assertRaisesRegex(w.TransactionError, '^INVALID_PLAN$'):
            w.preflight(forged, target_ref='synthetic-target')
        self.factory.assert_not_called()

    def test_preflight_cancellation_and_budget(self):
        p = self.plan()
        self.factory.reset_mock()
        for seconds in [10**1000, -10**1000, float('nan'), float('inf'), True]:
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_BUDGET$'):
                w.preflight(p, target_ref='synthetic-target', budget_seconds=seconds)
        for callback, code in [(lambda: True, 'CANCELLED'),
                               (lambda: 'secret', 'CANCELLATION_CHECK_FAILED'),
                               (Mock(side_effect=RuntimeError('secret')), 'CANCELLATION_CHECK_FAILED')]:
            with self.assertRaisesRegex(w.TransactionError, '^' + code + '$'):
                w.preflight(p, target_ref='synthetic-target', cancelled=callback)
        with patch.object(w.time, 'monotonic', side_effect=[0, 0, 0, 11]):
            with self.assertRaisesRegex(w.TransactionError, '^TIMEOUT$'):
                w.preflight(p, target_ref='synthetic-target')
        self.factory.assert_not_called()


class BackupStreamFraming(unittest.TestCase):
    # Opaque fake descriptors intentionally are NOT valid security evidence.
    DATA = b'private-data-sentinel'
    SECURITY = b'private-security-sentinel'

    @staticmethod
    def record(kind, payload=b'', attributes=0, name=b''):
        return struct.pack('<IIqI', kind, attributes, len(payload), len(name)) + name + payload

    def inspect(self, blob, **kwargs):
        return w.inspect_backup_streams(blob, expected_size=len(self.DATA),
                                       expected_sha256=w._hash(self.DATA), **kwargs)

    def valid(self):
        return self.record(1, self.DATA) + self.record(3, self.SECURITY, 2)

    def test_framing_acceptance_never_security_or_native_acceptance(self):
        for blob in [self.valid(), self.record(3, self.SECURITY) + self.record(1, self.DATA)]:
            with self.subTest(blob_order=blob[:4]), patch.object(w, '_WinAPI') as api:
                result = self.inspect(blob)
            api.assert_not_called()
            self.assertEqual(result['framing_status'], 'accepted')
            self.assertEqual(result['stream_count'], 2)
            self.assertEqual(result['security_descriptor_validation'], 'not_run')
            self.assertEqual(result['security_completeness'], 'unknown')
            self.assertEqual(result['native_capture_provenance'], 'not_verified')
            self.assertEqual(result['metadata_completeness'], 'unknown')
            self.assertEqual(result['apply_status'], 'unsupported')
            self.assertNotIn('sentinel', json.dumps(result))
            self.assertNotIn(w._hash(self.SECURITY), json.dumps(result))

    def test_every_truncation_and_trailing_bytes_fail(self):
        blob = self.valid()
        for length in range(len(blob)):
            with self.subTest(length=length), self.assertRaises(w.TransactionError):
                self.inspect(blob[:length])
        for trailer in [b'x', b'\0' * 20, self.record(1, self.DATA), self.record(3, self.SECURITY)]:
            with self.subTest(trailer_length=len(trailer)), self.assertRaises(w.TransactionError):
                self.inspect(blob + trailer)

    def test_all_unimplemented_stream_classes_fail_closed(self):
        for kind in [0, 2, 4, 5, 6, 7, 8, 9, 10, 11, 0xffffffff]:
            with self.subTest(kind=kind), self.assertRaisesRegex(w.TransactionError, '^UNSUPPORTED_METADATA$'):
                self.inspect(self.valid() + self.record(kind, b'private-sentinel'))

    def test_names_and_unsafe_attributes_rejected_without_echo(self):
        for kind in [1, 3]:
            for attributes in [1, 3, 4, 8, 16, 0x80000000]:
                with self.subTest(kind=kind, attributes=attributes), self.assertRaisesRegex(w.TransactionError, '^UNSUPPORTED_METADATA$'):
                    self.inspect(self.record(kind, self.SECURITY, attributes))
            with self.assertRaisesRegex(w.TransactionError, '^UNSUPPORTED_METADATA$'):
                self.inspect(self.record(kind, self.SECURITY, name='secret'.encode('utf-16-le')))
        with self.assertRaisesRegex(w.TransactionError, '^UNSUPPORTED_METADATA$'):
            self.inspect(self.record(1, self.DATA, 2))

    def test_invalid_lengths_and_missing_security_fail(self):
        for header in [struct.pack('<IIqI', 1, 0, -1, 0),
                       struct.pack('<IIqI', 1, 0, 2**63 - 1, 0),
                       struct.pack('<IIqI', 3, 0, w.MAX_METADATA + 1, 0),
                       struct.pack('<IIqI', 1, 0, 0, 1),
                       struct.pack('<IIqI', 1, 0, 0, w.MAX_METADATA + 2)]:
            with self.subTest(header=header), self.assertRaisesRegex(w.TransactionError, '^INVALID_BACKUP_STREAM$'):
                self.inspect(header)
        with self.assertRaisesRegex(w.TransactionError, '^SECURITY_METADATA_UNAVAILABLE$'):
            self.inspect(self.record(1, self.DATA))
        for security in [b'', b'x' * 19]:
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_BACKUP_STREAM$'):
                self.inspect(self.record(1, self.DATA) + self.record(3, security))

    def test_same_length_corruption_and_data_size_mismatch_fail(self):
        for payload in [b'X' * len(self.DATA), self.DATA + b'x']:
            with self.assertRaisesRegex(w.TransactionError, '^BACKUP_DATA_MISMATCH$'):
                self.inspect(self.record(1, payload) + self.record(3, self.SECURITY))

    def test_empty_data_and_maximum_payload_boundaries(self):
        for payload in [b'', b'x' * w.MAX_BYTES]:
            blob = self.record(1, payload) + self.record(3, b's' * w.MAX_METADATA)
            result = w.inspect_backup_streams(blob, expected_size=len(payload),
                                              expected_sha256=w._hash(payload))
            self.assertTrue(result['data_matches_expectation'])
            self.assertEqual(result['apply_status'], 'unsupported')
        with self.assertRaisesRegex(w.TransactionError, '^INVALID_BACKUP_STREAM_INPUT$'):
            self.inspect(b'x' * (w.MAX_BACKUP_BYTES + 1))

    def test_input_types_expectations_and_cancellation(self):
        for value in [None, 'private-sentinel', bytearray(self.valid()), memoryview(self.valid())]:
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_BACKUP_STREAM_INPUT$'):
                self.inspect(value)
        for size, digest in [(True, 'a' * 64), (-1, 'a' * 64), (w.MAX_BYTES + 1, 'a' * 64),
                             (0, None), (0, 'A' * 64), (0, 'secret')]:
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_BACKUP_EXPECTATION$'):
                w.inspect_backup_streams(self.valid(), expected_size=size, expected_sha256=digest)
        with self.assertRaisesRegex(w.TransactionError, '^CANCELLED$'):
            self.inspect(self.valid(), cancelled=lambda: True)
        with self.assertRaisesRegex(w.TransactionError, '^CANCELLATION_CHECK_FAILED$'):
            self.inspect(self.valid(), cancelled=Mock(side_effect=ValueError('secret')))
        for seconds in [10**1000, -10**1000, float('nan'), float('inf'), True]:
            with self.assertRaisesRegex(w.TransactionError, '^INVALID_BUDGET$'):
                self.inspect(self.valid(), budget_seconds=seconds)
        with patch.object(w.time, 'monotonic', side_effect=[0, 0, 0, 11]):
            with self.assertRaisesRegex(w.TransactionError, '^TIMEOUT$'):
                self.inspect(self.valid())

    def test_cancel_after_record_and_at_completion(self):
        for checks in [[False, False, True], [False, False, False, True]]:
            with self.subTest(checks=checks), self.assertRaisesRegex(w.TransactionError, '^CANCELLED$'):
                self.inspect(self.valid(), cancelled=Mock(side_effect=checks))


class NativeABIContracts(unittest.TestCase):
    """Tests binary parsing/API arguments with mocks, not Windows execution."""
    def setUp(self):
        self.api = object.__new__(w._WinAPI)
        self.api.k = Mock()
        self.api.a = Mock()

    def test_open_existing_no_recall_no_follow_no_write_delete_share(self):
        self.api.k.CreateFileW.return_value = 123
        self.assertEqual(self.api.open(PATH, False), 123)
        self.api.k.CreateFileW.assert_called_with(PATH, 0x20080, 1, None, 3,
                                                 0x00300000, None)
        self.api.open(PATH, False, True)
        self.assertEqual(self.api.k.CreateFileW.call_args.args[1], 0x20081)

    def test_disk_locality_fails_closed(self):
        for kind in [0, 1, 2, 4, 5, 6]:
            self.api.k.GetDriveTypeW.return_value = kind
            with self.assertRaisesRegex(w.TransactionError, '^NONLOCAL_OR_UNSUPPORTED_VOLUME$'):
                self.api.local_volume(GUID_ROOT)

    def test_reparse_hydration_and_unknown_attributes_rejected(self):
        self.api.k.GetFileType.return_value = 1
        for attribute in [0x400, 0x1000, 0x40000, 0x400000, 0x800, 0x4000, 0x200]:
            self.api.info = Mock(return_value=struct.pack('<II', attribute, 0))
            with self.assertRaisesRegex(w.TransactionError,
                                        '^REPARSE_RECALL_OR_METADATA_UNSUPPORTED$'):
                self.api.metadata(123, False)
        self.api.info = Mock(return_value=struct.pack('<II', 32, 1))
        with self.assertRaises(w.TransactionError):
            self.api.metadata(123, False)

    def test_stream_binary_parser(self):
        data = struct.pack('<IIqq', 0, 14, 8, 4096) + '::$DATA'.encode('utf-16-le')
        self.api.info = Mock(return_value=data)
        self.api.streams(123, 8)
        for corrupted in [struct.pack('<I', 64) + data[4:], data[:-2] + b'xx',
                          struct.pack('<IIqq', 0, 14, 9, 4096) + data[24:]]:
            self.api.info.return_value = corrupted
            with self.assertRaisesRegex(w.TransactionError,
                                        '^ALTERNATE_OR_UNKNOWN_STREAMS_UNSUPPORTED$'):
                self.api.streams(123, 8)

    def test_non_windows_no_api_load(self):
        with patch.object(w, '_native_windows', return_value=False):
            with self.assertRaisesRegex(w.TransactionError, '^PLATFORM_UNSUPPORTED$'):
                w.plan(PATH, b'new', 'synthetic', exclusive_access=True)


@unittest.skipUnless(os.name == 'nt' and sys.platform == 'win32'
                     and os.environ.get('GUARDIAN_TEST_WINDOWS_TRANSACTION_BOUNDARY') == '1',
                     'Requires native Windows and explicit synthetic-test opt-in')
class NativeWindowsSmoke(unittest.TestCase):
    def volume_path(self, target):
        api = w._WinAPI()
        root = ctypes.create_unicode_buffer(32768)
        volume = ctypes.create_unicode_buffer(64)
        api._bind(api.k, 'GetVolumePathNameW', ctypes.c_int,
                  [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32])
        api._bind(api.k, 'GetVolumeNameForVolumeMountPointW', ctypes.c_int,
                  [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32])
        self.assertTrue(api.k.GetVolumePathNameW(str(target), root, len(root)))
        self.assertTrue(api.k.GetVolumeNameForVolumeMountPointW(root.value, volume, len(volume)))
        return volume.value + str(target)[len(root.value):]

    def test_native_ads_and_hardlinks_rejected_before_data_read(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            target = root / 'synthetic-config'
            target.write_bytes(b'synthetic')
            path = self.volume_path(target)
            with open(str(target) + ':synthetic-stream', 'wb') as stream:
                stream.write(b'synthetic-ads')
            with patch.object(w._WinAPI, 'read', side_effect=AssertionError('data read')) as read:
                with self.assertRaisesRegex(w.TransactionError, '^ALTERNATE_OR_UNKNOWN_STREAMS_UNSUPPORTED$'):
                    w.plan(path, b'new', 'synthetic', exclusive_access=True)
                read.assert_not_called()
            os.unlink(str(target) + ':synthetic-stream')
            os.link(target, root / 'synthetic-hardlink')
            with patch.object(w._WinAPI, 'read', side_effect=AssertionError('data read')) as read:
                with self.assertRaisesRegex(w.TransactionError, '^UNSUPPORTED_LINK_OR_DELETE_STATE$'):
                    w.plan(path, b'new', 'synthetic', exclusive_access=True)
                read.assert_not_called()

    def test_native_junction_ancestor_rejected_before_data_read(self):
        # Microsoft REPARSE_DATA_BUFFER MountPoint layout and FSCTL_SET_REPARSE_POINT:
        # https://learn.microsoft.com/en-us/windows-hardware/drivers/ddi/ntifs/ns-ntifs-_reparse_data_buffer
        # https://learn.microsoft.com/en-us/windows/win32/api/winioctl/ni-winioctl-fsctl_set_reparse_point
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory).resolve()
            real = root / 'real'
            real.mkdir()
            (real / 'synthetic-config').write_bytes(b'synthetic')
            junction = root / 'junction'
            junction.mkdir()
            api = w._WinAPI()
            api._bind(api.k, 'DeviceIoControl', ctypes.c_int,
                      [ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_uint32,
                       ctypes.c_void_p, ctypes.c_uint32, ctypes.c_void_p, ctypes.c_void_p])
            handle = api.k.CreateFileW(str(junction), 0x40000000, 0, None, 3, 0x02200000, None)
            self.assertNotIn(handle, (None, ctypes.c_void_p(-1).value))
            try:
                substitute = ('\\??\\' + str(real)).encode('utf-16-le')
                printable = str(real).encode('utf-16-le')
                names = substitute + b'\x00\x00' + printable + b'\x00\x00'
                body = struct.pack('<HHHH', 0, len(substitute), len(substitute) + 2, len(printable)) + names
                packet = struct.pack('<IHH', 0xA0000003, len(body), 0) + body
                buffer = ctypes.create_string_buffer(packet)
                returned = ctypes.c_uint32()
                self.assertTrue(api.k.DeviceIoControl(handle, 0x000900A4, buffer, len(packet),
                                                     None, 0, ctypes.byref(returned), None))
            finally:
                api.close(handle)
            try:
                path = self.volume_path(root) + '\\junction\\synthetic-config'
                with patch.object(w._WinAPI, 'read', side_effect=AssertionError('data read')) as read:
                    with self.assertRaisesRegex(w.TransactionError, '^REPARSE_RECALL_OR_METADATA_UNSUPPORTED$'):
                        w.plan(path, b'new', 'synthetic', exclusive_access=True)
                    read.assert_not_called()
            finally:
                os.rmdir(junction)  # Remove only the synthetic junction itself.
            self.assertEqual((real / 'synthetic-config').read_bytes(), b'synthetic')

    def test_native_handles_closed_after_injected_metadata_denial(self):
        # Real native open/close; injected access denial, not an ACL acceptance test.
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'synthetic-config'
            target.write_bytes(b'synthetic')
            path = self.volume_path(target)
            api = w._WinAPI()
            opened = []
            original_open = api.open
            def track_open(*args):
                handle = original_open(*args)
                opened.append(handle)
                return handle
            api.open = track_open
            with patch.object(w, '_WinAPI', return_value=api), \
                 patch.object(api.a, 'GetKernelObjectSecurity', return_value=0), \
                 patch.object(api, 'read', side_effect=AssertionError('data read')) as read:
                with self.assertRaisesRegex(w.TransactionError, '^SECURITY_METADATA_UNAVAILABLE$'):
                    w.plan(path, b'new', 'synthetic', exclusive_access=True)
                read.assert_not_called()
            api._bind(api.k, 'GetHandleInformation', ctypes.c_int,
                      [ctypes.c_void_p, ctypes.c_void_p])
            self.assertTrue(opened)
            for handle in opened:
                flags = ctypes.c_uint32()
                self.assertFalse(api.k.GetHandleInformation(handle, ctypes.byref(flags)))

    def test_temporary_file_plan_and_mutation_rejection(self):
        with tempfile.TemporaryDirectory() as directory:
            target = Path(directory).resolve() / 'synthetic-config'
            target.write_bytes(b'synthetic-original')
            api = w._WinAPI()
            # Resolve only this synthetic temp fixture to its local volume GUID.
            root = ctypes.create_unicode_buffer(32768)
            volume = ctypes.create_unicode_buffer(64)
            api._bind(api.k, 'GetVolumePathNameW', ctypes.c_int,
                      [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32])
            api._bind(api.k, 'GetVolumeNameForVolumeMountPointW', ctypes.c_int,
                      [ctypes.c_wchar_p, ctypes.c_void_p, ctypes.c_uint32])
            self.assertTrue(api.k.GetVolumePathNameW(str(target), root, len(root)))
            self.assertTrue(api.k.GetVolumeNameForVolumeMountPointW(root.value, volume, len(volume)))
            path = volume.value + str(target)[len(root.value):]
            p = w.plan(path, b'synthetic-new', 'synthetic-windows', exclusive_access=True)
            self.assertEqual(p['before']['sha256'], w._hash(b'synthetic-original'))
            self.assertEqual(p['before']['security_scope'], 'owner_group_dacl_only')
            self.assertEqual(w.preview(p)['apply_status'], 'unsupported')
            approve = Mock(return_value=True)
            with self.assertRaises(w.TransactionError):
                w.apply(p, target_ref='synthetic-windows', backup_directory=path + '-backup',
                        authorize=approve, exclusive_access=True)
            approve.assert_not_called()
            self.assertEqual(target.read_bytes(), b'synthetic-original')
            self.assertFalse(Path(str(target) + '-backup').exists())


if __name__ == '__main__':
    unittest.main()
