"""Synthetic boundaries: no Darwin metadata APIs; owned temporary files only."""
import importlib.util
import contextlib
import io
from pathlib import Path
import unittest
from unittest.mock import Mock, call, patch

SPEC = importlib.util.spec_from_file_location('macos_metadata_probe',
    Path(__file__).resolve().parents[1] / 'tools/macos_metadata_probe.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class MetadataProbeTests(unittest.TestCase):
    def test_unknown_cli_arguments_do_not_echo_private_values(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(m, 'run') as run:
            self.assertEqual(m.main(['--unknown', 'PRIVATE-TOKEN']), 1)
        run.assert_not_called()
        self.assertIn('INPUT_INVALID', output.getvalue())
        self.assertNotIn('PRIVATE', output.getvalue())

    def test_cli_cancellation_is_fixed_and_not_success(self):
        output = io.StringIO()
        with contextlib.redirect_stdout(output), patch.object(m, 'run', side_effect=KeyboardInterrupt()):
            self.assertEqual(m.main([]), 2)
        self.assertIn('CANCELLED', output.getvalue())
        self.assertIn('closed', output.getvalue())

    def test_platform_gate_does_not_load_library(self):
        for value in ('linux', 'win32'):
            with patch.object(m.sys, 'platform', value), patch.object(m.ctypes, 'CDLL') as load:
                with self.assertRaisesRegex(m.MetadataError, '^UNSUPPORTED_PLATFORM$'):
                    m.DarwinMetadata()
                load.assert_not_called()

    def test_copy_resets_both_offsets_before_native_call(self):
        api = Mock()
        api.copy.return_value = 0
        with patch.object(m.os, 'lseek') as seek:
            m.copy_fixture(api, 17, 18, reset_offsets=True)
        self.assertEqual(seek.call_args_list, [call(17, 0, m.os.SEEK_SET), call(18, 0, m.os.SEEK_SET)])
        api.copy.assert_called_once_with(17, 18, None, 15)

    def test_counterexample_retains_unreset_offsets(self):
        api = Mock()
        api.copy.return_value = 0
        with patch.object(m.os, 'lseek') as seek:
            m.copy_fixture(api, 17, 18, reset_offsets=False)
        seek.assert_not_called()

    def test_copy_error_is_failure(self):
        api = Mock()
        api.copy.return_value = -1
        with self.assertRaisesRegex(m.MetadataError, '^TEMP_COPY_FAILED$'):
            m.copy_fixture(api, 17, 18, reset_offsets=False)

    def test_attribute_size_and_changed_read_fail(self):
        api = m.DarwinMetadata.__new__(m.DarwinMetadata)
        for value in (-1, 65537, None, True):
            api.get = Mock(return_value=value)
            with self.assertRaisesRegex(m.MetadataError, '^ATTRIBUTE_UNAVAILABLE_OR_OVERSIZED$'):
                api.attribute(17, m.PROVENANCE)
            self.assertEqual(api.get.call_count, 1)
        api.get = Mock(side_effect=[11, 10])
        with self.assertRaisesRegex(m.MetadataError, '^ATTRIBUTE_CHANGED$'):
            api.attribute(17, m.PROVENANCE)

    def test_acl_objects_both_released_on_invalid_size(self):
        api = m.DarwinMetadata.__new__(m.DarwinMetadata)
        api.acl_get = Mock(return_value=111)
        def text(acl, size):
            size._obj.value = 65537
            return 222
        api.acl_text = text
        api.acl_free = Mock(return_value=0)
        with self.assertRaisesRegex(m.MetadataError, '^ACL_TEXT_FAILED$'):
            api.acl(17)
        self.assertEqual(api.acl_free.call_args_list, [call(222), call(111)])

    def test_acl_cleanup_failure_cannot_be_success(self):
        api = m.DarwinMetadata.__new__(m.DarwinMetadata)
        api.acl_get = Mock(return_value=111)
        api.acl_text = Mock(return_value=None)
        api.acl_free = Mock(return_value=-1)
        with self.assertRaisesRegex(m.MetadataError, '^ACL_RELEASE_FAILED$'):
            api.acl(17)

    def test_absent_provenance_is_neither_preserved_nor_different(self):
        source = dict(contents=b'PRIVATE', mode=0o640, owner=501, group=20, xattrs={}, acl=b'PRIVATE')
        self.assertFalse(m.equality(source, dict(source))['provenance'])
        self.assertFalse(m.differences(source, dict(source))['provenance'])
        self.assertEqual(m.provenance_result(False, [], False, False), 'not_run_no_runtime_sources')

    def test_distinct_donors_or_setter_success_do_not_prove_restore(self):
        for distinct, assignments, different, restored in (
                (True, [False, True, True], False, True),
                (False, [True, True, True], True, True),
                (True, [True], True, True), (True, [True, True, True], False, True)):
            self.assertEqual(m.provenance_result(distinct, assignments, different, restored),
                             'blocked_fixture_values_not_distinct_or_setter_not_effective')
        self.assertEqual(m.provenance_result(True, [True, True, True], True, False), 'failed_copy_readback')
        self.assertEqual(m.provenance_result(True, [True, True, True], True, True), 'observed_different_value_restore')

    def test_reset_restore_reestablishes_every_supported_difference(self):
        api = Mock()
        api.attribute.return_value = b'donor'
        fake_os = Mock(spec=['pwrite', 'ftruncate', 'fchmod', 'fchown'])
        fake_os.pwrite.return_value = 17
        with patch.object(m, 'os', fake_os):
            self.assertTrue(m.reset_restore_fixture(api, 19, 21, b'donor'))
        fake_os.pwrite.assert_called_once_with(19, b'different fixture', 0)
        fake_os.ftruncate.assert_called_once_with(19, 17)
        fake_os.fchmod.assert_called_once_with(19, 0o600)
        fake_os.fchown.assert_called_once_with(19, -1, 21)
        api.fixture_acl.assert_called_once_with(19, writable=True)
        self.assertEqual(api.set_attribute.call_args_list,
            [call(19, m.MARKER, b'different-marker'), call(19, m.PROVENANCE, b'donor')])

    def test_recovery_reseeds_and_snapshots_after_negative_copy(self):
        events = []
        source = dict(contents=b'original', mode=0o640, owner=1000, group=20,
                      xattrs={m.PROVENANCE: b'original'}, acl=b'original')
        divergent = dict(source, contents=b'different', mode=0o600, group=21,
                         xattrs={m.PROVENANCE: b'different'}, acl=b'different')
        snapshots = iter([source, divergent, source, source, divergent, source, source])
        def snapshot(*args):
            value = next(snapshots)
            events.append('snapshot-divergent' if value is divergent else 'snapshot-equal')
            return value
        def copy(*args, reset_offsets):
            events.append('copy-reset' if reset_offsets else 'copy-negative')
        fake_os = Mock(spec=['geteuid', 'getuid', 'getegid', 'getgroups',
                             'open', 'close', 'fchown', 'O_RDWR', 'O_NOFOLLOW'])
        fake_os.geteuid.return_value = fake_os.getuid.return_value = 1000
        fake_os.getegid.return_value = 20
        fake_os.getgroups.return_value = [20, 21]
        fake_os.open.side_effect = [17, 18, 19]
        fake_os.O_RDWR, fake_os.O_NOFOLLOW = 2, 0
        with patch.object(m.sys, 'platform', 'darwin'), \
                patch.object(m, 'os', fake_os), \
                patch.object(m, 'DarwinMetadata'), \
                patch.object(m, 'snapshot', side_effect=snapshot), \
                patch.object(m, 'copy_fixture', side_effect=copy), \
                patch.object(m, 'reset_restore_fixture', side_effect=lambda *a: events.append('reseed')):
            result = m.run()
        self.assertEqual(events, ['snapshot-equal', 'snapshot-divergent',
            'copy-reset', 'snapshot-equal', 'copy-negative', 'snapshot-equal',
            'reseed', 'snapshot-divergent', 'copy-reset', 'snapshot-equal', 'snapshot-equal'])
        self.assertEqual(fake_os.close.call_args_list, [call(17), call(18), call(19)])
        self.assertTrue(result['different_before_reset_restore']['acl'])
        self.assertEqual(result['different_provenance_restore'], 'not_run_no_runtime_sources')

    def test_equal_comparison_exports_only_booleans(self):
        source = dict(contents=b'PRIVATE', mode=0o640, owner=501, group=20,
                      xattrs={m.PROVENANCE: b'PRIVATE'}, acl=b'PRIVATE')
        out = m.equality(source, dict(source))
        self.assertTrue(all(value is True for value in out.values()))
        self.assertNotIn('PRIVATE', str(out))
        self.assertNotIn('501', str(out))


if __name__ == '__main__':
    unittest.main()
