"""Synthetic POSIX temporary-file tests, not native configuration certification."""
import copy
import importlib.util
import json
import os
from pathlib import Path
import stat
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('transactions', ROOT / 'skills/claude-guardian/scripts/transactions.py')
t = importlib.util.module_from_spec(spec)
spec.loader.exec_module(t)


@unittest.skipUnless(os.name == 'posix', 'POSIX foundation only')
class Transactions(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()  # canonical temp root; transaction engine rejects alias paths
        self.file = self.root / 'config'
        self.file.write_bytes(b'original\x00private-token\xff')
        self.file.chmod(0o640)
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.p = t.plan(str(self.file), b'new\x00private-token\xfe', 'synthetic-device')

    def approval(self, p=None):
        expected = t.digest({'plan': p or self.p, 'backup_directory': str(self.backups)})
        return lambda op, d, target: op == 'apply' and d == expected and target == 'synthetic-device'

    def apply(self, p=None, authorize=None, **kwargs):
        return t.apply(p or self.p, target_ref='synthetic-device',
                       backup_directory=str(self.backups),
                       authorize=authorize or self.approval(p),
                       exclusive_access=True, **kwargs)

    def rollback(self, receipt, authorize=None):
        expected = t.digest(receipt)
        return t.rollback(receipt, target_ref='synthetic-device', exclusive_access=True,
                          authorize=authorize or (lambda op, d, target: op == 'rollback' and d == expected))

    def test_roundtrip_and_recovery_records(self):
        before = self.file.read_bytes()
        receipt = self.apply()
        self.assertEqual(t.verify(receipt)['check_status'], 'pass')
        self.assertEqual(t.verify(receipt)['network_effect'], 'not_tested')
        batch = self.backups / receipt['batch']
        self.assertEqual((batch / 'original.bin').read_bytes(), before)
        self.assertEqual(stat.S_IMODE((batch / 'original.bin').stat().st_mode), 0o600)
        self.assertEqual(stat.S_IMODE(batch.stat().st_mode), 0o700)
        self.assertEqual(json.loads((batch / 'applied.json').read_text()), receipt)
        self.assertEqual(self.rollback(receipt)['state'], 'restored')
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(stat.S_IMODE(self.file.stat().st_mode), 0o640)
        self.assertTrue((batch / 'original.bin').exists())
        self.assertEqual(len(list(batch.glob('rollback-*.json'))), 1)

    def test_plan_has_no_writes_and_preview_has_no_content(self):
        self.assertEqual(list(self.backups.iterdir()), [])
        output = json.dumps(t.preview(self.p))
        self.assertNotIn('private-token', output)
        self.assertNotIn(str(self.file), output)
        self.assertTrue(t.preview(self.p)['changed'])

    def test_missing_authorization(self):
        with self.assertRaisesRegex(t.TransactionError, 'AUTHORIZATION_REQUIRED'):
            t.apply(self.p, target_ref='synthetic-device', backup_directory=str(self.backups), exclusive_access=True)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_deny_cancel_and_non_boolean(self):
        for callback in (lambda *args: False, lambda *args: None, lambda *args: 1):
            with self.assertRaisesRegex(t.TransactionError, 'AUTHORIZATION_DENIED'):
                self.apply(authorize=callback)
        def cancelled(*args):
            raise RuntimeError('secret')
        with self.assertRaisesRegex(t.TransactionError, '^AUTHORIZATION_CANCELLED$'):
            self.apply(authorize=cancelled)

    def test_cancel_immediately_before_commit_retains_backup(self):
        count = 0
        def approve(*args):
            nonlocal count
            count += 1
            return count == 1
        before = self.file.read_bytes()
        with self.assertRaises(t.TransactionError) as raised:
            self.apply(authorize=approve)
        self.assertEqual(self.file.read_bytes(), before)
        self.assertTrue((self.backups / raised.exception.recovery_id / 'original.bin').exists())
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_host_exclusive_boundary_required(self):
        with self.assertRaisesRegex(t.TransactionError, 'EXCLUSIVE_ACCESS_REQUIRED'):
            t.apply(self.p, target_ref='synthetic-device', backup_directory=str(self.backups), authorize=self.approval())

    def test_wrong_target(self):
        with self.assertRaisesRegex(t.TransactionError, 'TARGET_MISMATCH'):
            t.apply(self.p, target_ref='different', backup_directory=str(self.backups), exclusive_access=True, authorize=lambda *a: True)

    def test_all_plan_content_bound(self):
        for key, value in [('action_id', 'changed'), ('target_ref', 'different')]:
            changed = copy.deepcopy(self.p)
            changed[key] = value
            with self.assertRaises(t.TransactionError):
                self.apply(changed, authorize=self.approval())
        changed = copy.deepcopy(self.p)
        changed['after_sha256'] = '0' * 64
        with self.assertRaisesRegex(t.TransactionError, 'INVALID_OR_EXPIRED_PLAN'):
            self.apply(changed)

    def test_backup_destination_bound(self):
        other = self.root / 'other'
        other.mkdir(mode=0o700)
        with self.assertRaisesRegex(t.TransactionError, 'AUTHORIZATION_DENIED'):
            t.apply(self.p, target_ref='synthetic-device', backup_directory=str(other),
                    exclusive_access=True, authorize=self.approval())

    def test_expired_future_and_nan(self):
        for a, b in [(0, 1), (time.time() + 100, time.time() + 200), (float('nan'), float('nan'))]:
            p = copy.deepcopy(self.p)
            p['created_at'], p['expires_at'] = a, b
            with self.assertRaises(t.TransactionError):
                self.apply(p, authorize=lambda *args: True)

    def test_stale_contents_and_mode(self):
        self.file.write_bytes(b'user edit')
        with self.assertRaisesRegex(t.TransactionError, 'STALE_FILE'):
            self.apply()
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_replaced_same_bytes_is_stale(self):
        other = self.root / 'other'
        other.write_bytes(self.file.read_bytes())
        other.chmod(0o640)
        other.replace(self.file)
        with self.assertRaisesRegex(t.TransactionError, 'STALE_FILE'):
            self.apply()

    def test_edit_during_confirmation_is_stale(self):
        def callback(*args):
            self.file.write_bytes(b'concurrent edit')
            return True
        with self.assertRaisesRegex(t.TransactionError, 'STALE_FILE'):
            self.apply(authorize=callback)
        self.assertEqual(self.file.read_bytes(), b'concurrent edit')

    def test_rollback_conflict_preserves_later_edit(self):
        receipt = self.apply()
        self.file.write_bytes(b'later edit')
        self.assertEqual(t.verify(receipt)['check_status'], 'fail')
        with self.assertRaisesRegex(t.TransactionError, 'ROLLBACK_CONFLICT'):
            self.rollback(receipt)
        self.assertEqual(self.file.read_bytes(), b'later edit')

    def test_rollback_requires_independent_approval(self):
        receipt = self.apply()
        with self.assertRaisesRegex(t.TransactionError, 'AUTHORIZATION_DENIED'):
            self.rollback(receipt, authorize=self.approval())

    def test_corrupt_backup_blocks_recovery(self):
        receipt = self.apply()
        (self.backups / receipt['batch'] / 'original.bin').write_bytes(b'corrupt')
        with self.assertRaisesRegex(t.TransactionError, 'BACKUP_CORRUPT'):
            self.rollback(receipt)

    def test_same_size_corrupt_backup_blocks_recovery(self):
        receipt = self.apply()
        backup = self.backups / receipt['batch'] / 'original.bin'
        original = backup.read_bytes()
        self.assertTrue(original)
        changed = bytes([original[0] ^ 1]) + original[1:]
        backup.write_bytes(changed)
        self.assertEqual(backup.stat().st_size, len(original))
        current = self.file.read_bytes()
        with self.assertRaisesRegex(t.TransactionError, 'BACKUP_CORRUPT'):
            self.rollback(receipt)
        self.assertEqual(self.file.read_bytes(), current)

    def test_prepared_receipt_not_blindly_restored(self):
        receipt = self.apply()
        receipt['state'] = 'prepared'
        with self.assertRaisesRegex(t.TransactionError, 'RECOVERY_REQUIRES_RECONCILIATION'):
            self.rollback(receipt)

    def test_path_traversal_expansion_and_relative_rejected(self):
        for path in ['relative', str(self.root) + '/../config', str(self.root) + '//config',
                     '/tmp/$HOME/config', '/tmp/~/config', '/tmp/*.json', '/tmp/a\\b']:
            with self.subTest(path=path), self.assertRaisesRegex(t.TransactionError, 'UNSAFE_PATH'):
                t.plan(path, b'x', 'synthetic-device')

    def test_symlink_leaf_parent_backup_rejected(self):
        link = self.root / 'link'
        link.symlink_to(self.file)
        with self.assertRaises(t.TransactionError):
            t.plan(str(link), b'x', 'synthetic-device')
        directory_link = self.root / 'linked-directory'
        directory_link.symlink_to(self.root, target_is_directory=True)
        with self.assertRaises(t.TransactionError):
            t.plan(str(directory_link / 'config'), b'x', 'synthetic-device')
        backup_link = self.root / 'backup-link'
        backup_link.symlink_to(self.backups, target_is_directory=True)
        with self.assertRaises(t.TransactionError):
            t.apply(self.p, target_ref='synthetic-device', backup_directory=str(backup_link),
                    authorize=lambda *a: True, exclusive_access=True)

    def test_hardlink_and_directory_rejected(self):
        os.link(self.file, self.root / 'hardlink')
        with self.assertRaisesRegex(t.TransactionError, 'UNSUPPORTED_FILE_TYPE'):
            t.plan(str(self.file), b'x', 'synthetic-device')
        with self.assertRaises(t.TransactionError):
            t.plan(str(self.backups), b'x', 'synthetic-device')

    def test_fifo_is_rejected_without_blocking(self):
        fifo = self.root / 'fifo'
        os.mkfifo(fifo)
        with self.assertRaisesRegex(t.TransactionError, 'UNSUPPORTED_FILE_TYPE'):
            t.plan(str(fifo), b'x', 'synthetic-device')

    def test_backup_permissions_fail_closed(self):
        self.backups.chmod(0o755)
        with self.assertRaisesRegex(t.TransactionError, 'BACKUP_DIRECTORY_NOT_PRIVATE'):
            self.apply()

    def test_no_arbitrary_extra_operations(self):
        p = copy.deepcopy(self.p)
        p['command'] = 'arbitrary command'
        with self.assertRaisesRegex(t.TransactionError, 'INVALID_PLAN'):
            self.apply(p, authorize=lambda *a: True)

    def test_parent_swap_after_plan_is_rejected(self):
        parent = self.root / 'parent'
        parent.mkdir()
        file = parent / 'config'
        file.write_bytes(b'original')
        p = t.plan(str(file), b'changed', 'synthetic-device')
        parent.rename(self.root / 'old-parent')
        parent.mkdir()
        file.write_bytes(b'original')
        with self.assertRaisesRegex(t.TransactionError, 'PARENT_CHANGED'):
            self.apply(p)

    def test_backup_failure_never_writes_target(self):
        before = self.file.read_bytes()
        real_write = t._write
        def fail_backup(fd, name, data, mode=0o600):
            if name == 'original.bin':
                raise OSError('private error content')
            return real_write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail_backup):
            with self.assertRaisesRegex(t.TransactionError, '^IO_FAILURE$') as exc:
                self.apply()
        self.assertIsNotNone(exc.exception.recovery_id)
        self.assertEqual(self.file.read_bytes(), before)

    def test_post_commit_journal_failure_retains_prepared_recovery(self):
        real_write = t._write
        def fail_journal(fd, name, data, mode=0o600):
            if name == 'applied.json':
                raise OSError('disk full')
            return real_write(fd, name, data, mode)
        with patch.object(t, '_write', side_effect=fail_journal):
            with self.assertRaises(t.TransactionError) as exc:
                self.apply()
        batch = self.backups / exc.exception.recovery_id
        self.assertTrue((batch / 'prepared.json').exists())
        self.assertTrue((batch / 'original.bin').exists())
        self.assertEqual(self.file.read_bytes(), b'new\x00private-token\xfe')

    def test_metadata_change_blocks_rollback(self):
        receipt = self.apply()
        self.file.chmod(0o600)
        with self.assertRaisesRegex(t.TransactionError, 'ROLLBACK_CONFLICT'):
            self.rollback(receipt)

    def test_malformed_plan_fields_are_controlled_before_authorization(self):
        mutations = [('before', None), ('before', {}), ('parent_identity', None),
                     ('parent_identity', [True, 1]), ('created_at', True),
                     ('created_at', 'secret'), ('expires_at', None),
                     ('proposed_base64', []), ('target_ref', {}), ('action_id', 'bad')]
        for key, value in mutations:
            p = copy.deepcopy(self.p)
            p[key] = value
            with self.subTest(key=key), self.assertRaises(t.TransactionError):
                t.preview(p)
            callback = Mock(return_value=True)
            with self.subTest(apply_key=key), self.assertRaises(t.TransactionError):
                self.apply(p, authorize=callback)
            callback.assert_not_called()
        for key, value in [('mode', 0o4755), ('size', -1), ('inode', True),
                           ('sha256', 'bad'), ('uid', 1.0)]:
            p = copy.deepcopy(self.p)
            p['before'][key] = value
            with self.subTest(snapshot=key), self.assertRaises(t.TransactionError):
                t.preview(p)

    def test_malformed_recovery_documents_are_controlled(self):
        receipt = self.apply()
        cases = [None, [], {}, {'schema_version': 'exact-file-recovery/1', 'state': 'applied'}]
        for key, value in [('plan', None), ('applied_snapshot', None), ('batch', '../bad'),
                           ('backup_directory', None), ('extra', 'secret')]:
            invalid = copy.deepcopy(receipt)
            invalid[key] = value
            cases.append(invalid)
        invalid = copy.deepcopy(receipt)
        invalid['applied_snapshot']['sha256'] = '0' * 64
        cases.append(invalid)
        for invalid in cases:
            with self.subTest(document_type=type(invalid).__name__):
                with self.assertRaises(t.TransactionError):
                    t.verify(invalid)
                callback = Mock(return_value=True)
                with self.assertRaises(t.TransactionError):
                    t.rollback(invalid, target_ref='synthetic-device', exclusive_access=True,
                               authorize=callback)
                callback.assert_not_called()

    def test_oversized_base64_rejected_before_decoding(self):
        p = copy.deepcopy(self.p)
        p['proposed_base64'] = 'A' * (t.MAX_BASE64 + 4)
        with patch.object(t.base64, 'b64decode', side_effect=AssertionError('must not decode')):
            with self.assertRaises(t.TransactionError):
                t.preview(p)

    def test_cyclic_non_json_and_unbounded_documents_controlled(self):
        cyclic = {}; cyclic['cycle'] = cyclic
        for invalid in [cyclic, {'bad': object()}, {'large': 10**1000}, {'nan': float('nan')}]:
            with self.assertRaises(t.TransactionError):
                t.digest(invalid)
            with self.assertRaises(t.TransactionError):
                self.apply(invalid, authorize=lambda *args: True)
        for now in ['secret', True, float('inf'), 10**1000]:
            with self.assertRaises(t.TransactionError):
                t.plan(str(self.file), b'x', 'synthetic-device', now=now)

    def test_expired_plan_still_allows_independently_authorized_recovery(self):
        receipt = self.apply()
        with patch.object(t.time, 'time', return_value=self.p['expires_at'] + 100):
            self.assertEqual(t.verify(receipt)['check_status'], 'pass')
            self.assertEqual(self.rollback(receipt)['state'], 'restored')

    def test_native_temporary_file_xattr_presence_and_refusal(self):
        # Synthetic file only. Darwin fsetxattr signature verified in Apple's
        # xnu/bsd/sys/xattr.h, adjacent to flistxattr; never a production write.
        fd = os.open(self.file, os.O_RDWR | os.O_NOFOLLOW)
        try:
            self.assertFalse(t._has_xattrs(fd))
            if t.sys.platform == 'darwin':
                library = t.ctypes.CDLL('/usr/lib/libSystem.B.dylib', use_errno=True)
                setter = library.fsetxattr
                setter.argtypes = [t.ctypes.c_int, t.ctypes.c_char_p, t.ctypes.c_void_p,
                                   t.ctypes.c_size_t, t.ctypes.c_uint32, t.ctypes.c_int]
                setter.restype = t.ctypes.c_int
                value = t.ctypes.create_string_buffer(b'test')
                self.assertEqual(setter(fd, b'user.guardian.synthetic', value, 4, 0, 0), 0)
            else:
                os.setxattr(fd, 'user.guardian.synthetic', b'test')
            self.assertTrue(t._has_xattrs(fd))
        finally:
            os.close(fd)
        with self.assertRaisesRegex(t.TransactionError, '^UNSUPPORTED_FILE_METADATA$'):
            t.plan(str(self.file), b'replacement', 'synthetic-device')

    def test_darwin_present_xattrs_reject_file_without_content_write(self):
        before = self.file.read_bytes()
        with patch.object(t.sys, 'platform', 'darwin'), \
                patch.object(t.ctypes, 'CDLL', return_value=Mock(flistxattr=Mock(return_value=1))):
            with self.assertRaisesRegex(t.TransactionError, '^UNSUPPORTED_FILE_METADATA$'):
                t.plan(str(self.file), b'replacement', 'synthetic-device')
        self.assertEqual(self.file.read_bytes(), before)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_duplicate_apply_fails_closed(self):
        self.apply()
        with self.assertRaisesRegex(t.TransactionError, 'STALE_FILE'):
            self.apply()


class ExtendedAttributePlatformTests(unittest.TestCase):
    def test_darwin_descriptor_abi_no_names_or_allocation(self):
        for result in (0, 1, 4096, 2**62):
            query = Mock(return_value=result)
            library = Mock(flistxattr=query)
            with patch.object(t.sys, 'platform', 'darwin'), \
                    patch.object(t.ctypes, 'CDLL', return_value=library) as loader:
                self.assertEqual(t._has_xattrs(12), result > 0)
            loader.assert_called_once_with('/usr/lib/libSystem.B.dylib', use_errno=True)
            query.assert_called_once_with(12, None, 0, 0x0020)
            self.assertEqual(query.argtypes, [t.ctypes.c_int, t.ctypes.c_void_p,
                                             t.ctypes.c_size_t, t.ctypes.c_int])
            self.assertIs(query.restype, t.ctypes.c_ssize_t)

    def test_darwin_errors_fail_closed(self):
        for result in (-1, -2, None, True, 2**100):
            with self.subTest(result=result), patch.object(t.sys, 'platform', 'darwin'), \
                    patch.object(t.ctypes, 'CDLL', return_value=Mock(flistxattr=Mock(return_value=result))):
                with self.assertRaisesRegex(t.TransactionError, '^XATTR_CHECK_FAILED$'):
                    t._has_xattrs(12)
        for error in (OSError('private detail'), AttributeError('missing symbol')):
            with patch.object(t.sys, 'platform', 'darwin'), \
                    patch.object(t.ctypes, 'CDLL', side_effect=error):
                with self.assertRaisesRegex(t.TransactionError, '^XATTR_CHECK_FAILED$'):
                    t._has_xattrs(12)

    def test_descriptor_arguments_rejected_before_library_load(self):
        for fd in (None, True, -1, '/tmp/file', 2**40):
            with patch.object(t.ctypes, 'CDLL') as loader:
                with self.assertRaisesRegex(t.TransactionError, '^XATTR_CHECK_FAILED$'):
                    t._has_xattrs(fd)
                loader.assert_not_called()

    def test_darwin_support_does_not_require_linux_os_listxattr(self):
        with patch.object(t.sys, 'platform', 'darwin'), patch.object(t.os, 'name', 'posix'), \
                patch.object(t.os, 'listxattr', None, create=True), \
                patch.object(t.os, 'O_NOFOLLOW', 1, create=True), \
                patch.object(t.os, 'O_DIRECTORY', 1, create=True), \
                patch.object(t.os, 'supports_dir_fd', {t.os.open}):
            t._support()

    def test_non_darwin_still_requires_descriptor_xattr_support(self):
        with patch.object(t.sys, 'platform', 'linux'), \
                patch.object(t.os, 'listxattr', None, create=True):
            with self.assertRaisesRegex(t.TransactionError, '^PLATFORM_UNSUPPORTED$'):
                t._support()

    def test_linux_fd_only_and_errors(self):
        with patch.object(t.sys, 'platform', 'linux'), \
                patch.object(t.os, 'listxattr', return_value=['user.synthetic'], create=True) as query:
            self.assertTrue(t._has_xattrs(12))
            query.assert_called_once_with(12)
        with patch.object(t.sys, 'platform', 'linux'), \
                patch.object(t.os, 'listxattr', side_effect=OSError('private'), create=True):
            with self.assertRaisesRegex(t.TransactionError, '^XATTR_CHECK_FAILED$'):
                t._has_xattrs(12)


if __name__ == '__main__':
    unittest.main()
