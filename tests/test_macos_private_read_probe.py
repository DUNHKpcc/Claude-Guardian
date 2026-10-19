"""Synthetic harness tests; no Darwin APIs or existing user files are used."""
import contextlib
import importlib.util
import io
import json
from pathlib import Path
import unittest
from unittest.mock import Mock, patch

SPEC = importlib.util.spec_from_file_location('guardian_private_read_probe',
    Path(__file__).resolve().parents[1] / 'tools/macos_private_read_probe.py')
m = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(m)


class PrivateReadProbeTests(unittest.TestCase):
    def test_platform_gate_precedes_native_loading(self):
        for platform in ('linux', 'win32'):
            with patch.object(m.sys, 'platform', platform), patch.object(m, 'DarwinMetadata') as api:
                with self.assertRaisesRegex(m.MetadataError, '^UNSUPPORTED_PLATFORM$'):
                    m.run()
                api.assert_not_called()

    def test_no_private_paths_or_arguments_accepted(self):
        output = io.StringIO()
        with patch.object(m, 'run') as run, contextlib.redirect_stdout(output):
            self.assertEqual(m.main(['--path', 'PRIVATE-PATH']), 1)
        run.assert_not_called()
        self.assertNotIn('PRIVATE', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['code'], 'INPUT_INVALID')

    def test_empty_acl_is_released_on_set_failure(self):
        api = Mock()
        api.acl_init.return_value = 123
        api.acl_set_fd.return_value = -1
        api.acl_free.return_value = 0
        with self.assertRaisesRegex(m.MetadataError, '^TEMP_EMPTY_ACL_SET_FAILED$'):
            m.set_empty_acl(api, 17)
        api.acl_free.assert_called_once_with(123)

    def test_empty_acl_release_failure_is_not_success(self):
        api = Mock()
        api.acl_init.return_value = 123
        api.acl_set_fd.return_value = 0
        api.acl_free.return_value = -1
        with self.assertRaisesRegex(m.MetadataError, '^TEMP_ACL_RELEASE_FAILED$'):
            m.set_empty_acl(api, 17)

    def test_empty_acl_allocation_failure_never_sets(self):
        api = Mock()
        api.acl_init.return_value = None
        with self.assertRaisesRegex(m.MetadataError, '^TEMP_ACL_INIT_FAILED$'):
            m.set_empty_acl(api, 17)
        api.acl_set_fd.assert_not_called()
        api.acl_free.assert_not_called()

    def test_read_occurs_inside_guard_and_only_reads_fixed_fixture(self):
        events = []
        @contextlib.contextmanager
        def guard(file_fd, parent_fd):
            events.append(('enter', file_fd, parent_fd))
            yield None
            events.append(('exit', file_fd, parent_fd))
        def read(fd, size, offset):
            events.append(('read', fd, size, offset))
            return b'{}'
        with patch.object(m.reader, 'observe_acl_fd', return_value='empty_acl'), \
                patch.object(m.reader, 'private_document_read', guard), \
                patch.object(m.os, 'pread', read, create=True):
            result = m.assess(17, 18)
        self.assertEqual(events, [('enter', 17, 18), ('read', 17, 3, 0), ('exit', 17, 18)])
        self.assertEqual(result['read_guard'], 'accepted')
        self.assertTrue(result['fixture_bytes_match'])

    @unittest.skipUnless(hasattr(m.os, 'pread') and hasattr(m.os, 'O_DIRECTORY'),
                         'POSIX disposable fixture harness')
    def test_negative_cases_cannot_pass_on_unrelated_failure(self):
        api = Mock()
        api.acl_init.return_value = 123
        api.acl_set_fd.return_value = api.acl_free.return_value = 0
        valid = {'file_acl': 'empty_acl', 'parent_acl': 'empty_acl',
                 'fixture_bytes_match': True, 'read_guard': 'accepted'}
        unrelated = dict(valid, read_guard='INVALID_DESCRIPTOR')
        with patch.object(m.sys, 'platform', 'darwin'), \
                patch.object(m.os, 'geteuid', return_value=1000, create=True), \
                patch.object(m.os, 'getuid', return_value=1000, create=True), \
                patch.object(m, 'DarwinMetadata', return_value=api), \
                patch.object(m, 'assess', side_effect=[valid, valid] + [unrelated] * 4):
            result = m.run()
        self.assertFalse(result['all_expected'])
        self.assertEqual(len(result['cases']), 6)
        self.assertEqual(result['production_cli_admission'], 'unchanged')
        api.attribute.assert_not_called()
        api.attributes.assert_not_called()
        api.copy.assert_not_called()
        api.acl.assert_not_called()

    def test_generic_native_exception_text_is_not_disclosed(self):
        output = io.StringIO()
        with patch.object(m, 'run', side_effect=OSError('PRIVATE-PATH')), \
                contextlib.redirect_stdout(output):
            self.assertEqual(m.main([]), 1)
        self.assertNotIn('PRIVATE', output.getvalue())
        self.assertEqual(json.loads(output.getvalue())['code'], 'FIXTURE_FAILED')

    def test_cancellation_is_terminal_and_not_success(self):
        output = io.StringIO()
        with patch.object(m, 'run', side_effect=KeyboardInterrupt()), \
                contextlib.redirect_stdout(output):
            self.assertEqual(m.main([]), 2)
        self.assertEqual(json.loads(output.getvalue())['code'], 'CANCELLED')

    def test_cli_reports_expected_boolean_without_inventing_production_admission(self):
        for expected in (False, True):
            output = io.StringIO()
            result = {'all_expected': expected, 'production_cli_admission': 'unchanged'}
            with patch.object(m, 'run', return_value=result), contextlib.redirect_stdout(output):
                self.assertEqual(m.main([]), 0 if expected else 1)
            self.assertEqual(json.loads(output.getvalue()), result)


if __name__ == '__main__':
    unittest.main()
