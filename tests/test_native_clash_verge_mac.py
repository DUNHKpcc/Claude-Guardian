"""Fixed macOS Clash Verge admission: synthetic process list and temporary files only."""
from contextlib import contextmanager
import os
from pathlib import Path
import subprocess
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import native_clash_verge_mac as native
import repair_execution as e
import test_rules_repair_cli as fixtures
from test_rules_extension_plan import RAW


@unittest.skipUnless(os.name == 'posix', 'POSIX synthetic files only')
class NativeClashVergeMac(unittest.TestCase):
    setUp = fixtures.RulesRepairCLI.setUp
    preflight = fixtures.RulesRepairCLI.preflight
    retain = fixtures.RulesRepairCLI.retain

    @contextmanager
    def admitted(self, processes=(), platform='darwin'):
        with patch.object(native, '_platform', return_value=platform), \
                patch.object(native, 'APP_INFO', str(self.info)), \
                patch.object(native, '_support_directory', return_value=str(self.root)), \
                patch.object(native, '_list_processes', side_effect=lambda: list(processes)):
            yield

    def retained(self):
        import recovery_cli
        args = self.retain()
        return recovery_cli.load_receipt(args['plan_path']), args

    def test_other_platforms_and_scopes_stay_unavailable(self):
        document, _ = self.retained()
        with self.admitted(platform='linux'):
            with self.assertRaisesRegex(native.tx.TransactionError, '^NATIVE_REPAIR_ADAPTER_UNAVAILABLE$'):
                with native.session(document):
                    self.fail('admitted on a non-Darwin platform')
        for change in (lambda d: d.update(candidate_kind='merge-policy'),
                       lambda d: d['metadata_sources']['app_info'].update(path='/tmp/Info.plist'),
                       lambda d: d['metadata_sources']['profile_index'].update(path=str(self.root / 'other.yaml')),
                       lambda d: d['base_source'].update(path=str(self.root / 'source.yaml')),
                       lambda d: d['plan'].update(path=str(self.root / 'extension.yaml')),
                       lambda d: d.pop('plan')):
            with self.subTest(change=change):
                altered = __import__('copy').deepcopy(document)
                change(altered)
                with self.admitted():
                    with self.assertRaisesRegex(native.tx.TransactionError, '^NATIVE_REPAIR_ADAPTER_UNAVAILABLE$'):
                        with native.session(altered):
                            self.fail('admitted outside the fixed scope')
        with self.admitted():
            with self.assertRaisesRegex(native.tx.TransactionError, '^NATIVE_REPAIR_ADAPTER_UNAVAILABLE$'):
                with native.session({}):
                    self.fail('admitted an empty document')

    def test_admits_fixed_scope_when_application_is_not_running(self):
        document, _ = self.retained()
        with self.admitted(processes=['/usr/sbin/cfprefsd', '/Applications/Safari.app/Contents/MacOS/Safari']):
            with native.session(document) as recheck:
                recheck()

    def test_running_gui_application_blocks_before_and_during_session(self):
        document, _ = self.retained()
        for command in ('/Applications/Clash Verge.app/Contents/MacOS/clash-verge',
                        '/Applications/Clash Verge.app/Contents/MacOS/anything',
                        '/Applications/Clash Verge.app/Contents/Frameworks/Helper'):
            with self.subTest(command=command):
                with self.admitted(processes=[command]):
                    with self.assertRaisesRegex(native.tx.TransactionError, '^CLASH_VERGE_RUNNING$'):
                        with native.session(document):
                            self.fail('admitted while the writer runs')
        running = []
        with self.admitted(processes=running):
            with native.session(document) as recheck:
                recheck()
                running.append('/Applications/Clash Verge.app/Contents/MacOS/clash-verge')
                with self.assertRaisesRegex(native.tx.TransactionError, '^CLASH_VERGE_RUNNING$'):
                    recheck()

    def test_core_and_service_helper_do_not_block_because_they_do_not_write_the_profile_files(self):
        # Real-device run: quitting the GUI leaves the KeepAlive root service and the core running;
        # blocking on them forced `sudo launchctl bootout` and dropped the TUN for no benefit.
        document, _ = self.retained()
        survivors = ['/Library/Application Support/clash-verge-service/cores/verge-mihomo',
                     '/Library/PrivilegedHelperTools/clash-verge-service', '/usr/local/bin/verge-mihomo-alpha']
        with self.admitted(processes=survivors):
            with native.session(document) as recheck:
                recheck()

    def test_process_list_failure_fails_closed(self):
        document, _ = self.retained()
        with patch.object(native, '_platform', return_value='darwin'), \
                patch.object(native, 'APP_INFO', str(self.info)), \
                patch.object(native, '_support_directory', return_value=str(self.root)):
            for failure in (subprocess.TimeoutExpired('ps', 5), OSError('missing')):
                with self.subTest(failure=type(failure).__name__), \
                        patch.object(native.subprocess, 'run', side_effect=failure):
                    with self.assertRaisesRegex(native.tx.TransactionError, '^PROCESS_LIST_UNAVAILABLE$'):
                        with native.session(document):
                            self.fail('admitted without a process list')
            for done in (subprocess.CompletedProcess([], 1, '', ''), subprocess.CompletedProcess([], 0, '  \n', '')):
                with self.subTest(code=done.returncode), patch.object(native.subprocess, 'run', return_value=done):
                    with self.assertRaisesRegex(native.tx.TransactionError, '^PROCESS_LIST_UNAVAILABLE$'):
                        with native.session(document):
                            self.fail('admitted without a process list')

    def test_process_list_uses_fixed_command_without_shell_or_inherited_environment(self):
        done = subprocess.CompletedProcess([], 0, '/sbin/launchd\n/usr/sbin/cfprefsd\n', '')
        with patch.object(native.subprocess, 'run', return_value=done) as run:
            self.assertEqual(native._list_processes(), ['/sbin/launchd', '/usr/sbin/cfprefsd'])
        args, kwargs = run.call_args
        self.assertEqual(args[0], ['/bin/ps', '-axo', 'comm='])
        self.assertIs(kwargs['shell'], False)
        self.assertEqual(set(kwargs['env']), {'PATH', 'LC_ALL'})
        self.assertEqual(kwargs['timeout'], native.PS_TIMEOUT)

    def test_metadata_replacement_or_untrusted_plist_blocks(self):
        document, _ = self.retained()
        with self.admitted():
            with native.session(document) as recheck:
                replacement = self.index.with_name('replacement')
                replacement.write_bytes(self.index.read_bytes())
                replacement.chmod(0o600)
                replacement.replace(self.index)
                with self.assertRaisesRegex(native.tx.TransactionError, '^SOURCE_SNAPSHOT_CHANGED$'):
                    recheck()
        self.info.chmod(0o666)
        with self.admitted():
            with self.assertRaisesRegex(native.tx.TransactionError, '^APP_METADATA_NOT_TRUSTED$'):
                with native.session(document):
                    self.fail('admitted a shared-writable application plist')

    def test_execute_writes_exact_bytes_with_real_adapter_and_recovery_receipt(self):
        args = self.retain()
        with self.admitted():
            result = e.execute(**args)
        self.assertEqual(result['status'], 'written_but_not_verified')
        self.assertEqual(result['byte_readback'], 'pass')
        self.assertEqual(result['application_reload'], 'not_run')
        self.assertEqual(result['effective_routing'], 'not_run')
        self.assertNotEqual(self.target.read_bytes(), RAW)
        self.assertTrue(list(self.backups.iterdir()))

    def test_execute_writes_while_only_core_and_service_survive(self):
        args = self.retain()
        with self.admitted(processes=['/Library/Application Support/clash-verge-service/cores/verge-mihomo',
                                      '/Library/PrivilegedHelperTools/clash-verge-service']):
            result = e.execute(**args)
        self.assertEqual(result['status'], 'written_but_not_verified')

    def test_execute_refuses_and_keeps_file_while_application_runs(self):
        args = self.retain()
        with self.admitted(processes=['/Applications/Clash Verge.app/Contents/MacOS/clash-verge']):
            with self.assertRaisesRegex(e.tx.TransactionError, '^CLASH_VERGE_RUNNING$'):
                e.execute(**args)
        self.assertEqual(self.target.read_bytes(), RAW)
        self.assertEqual(list(self.backups.iterdir()), [])

    def test_application_starting_during_commit_reports_error_with_recovery_batch(self):
        # Rechecks: 1 admission, 2 pre-authorization, 3 authorization, 4 just before the
        # replace (backup exists, target untouched), 5 after readback (target written).
        for start, written in ((4, False), (5, True)):
            with self.subTest(start=start):
                self.setUp()
                args = self.retain()
                running = []
                calls = {'n': 0}
                original = native._writer_running
                def starts_at_recheck():
                    calls['n'] += 1
                    if calls['n'] >= start:
                        running.append('/Applications/Clash Verge.app/Contents/MacOS/clash-verge')
                    return original()
                with self.admitted(processes=running), \
                        patch.object(native, '_writer_running', side_effect=starts_at_recheck):
                    with self.assertRaises(e.tx.TransactionError) as caught:
                        e.execute(**args)
                self.assertEqual(str(caught.exception), 'CLASH_VERGE_RUNNING')
                self.assertTrue(caught.exception.recovery_id)
                self.assertEqual(self.target.read_bytes() != RAW, written)
                self.assertEqual([item.name for item in self.backups.iterdir()],
                                 [caught.exception.recovery_id])


if __name__ == '__main__':
    unittest.main()
