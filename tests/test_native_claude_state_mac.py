"""macOS keychain / simple-mode / timezone actions: disposable home, stubbed system commands."""
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import native_claude_state_mac as state
import native_cleanup_mac as base
from test_native_cleanup_mac import Terminal


@unittest.skipUnless(os.name == 'posix', 'POSIX synthetic home only')
class NativeClaudeState(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = str(Path(self.tmp.name).resolve())
        self.processes = ['/usr/sbin/cfprefsd']
        self.ancestors = ['/bin/zsh']
        self.commands = []
        self.exit_codes = {}
        self.zone = 'Asia/Tokyo'
        for item in (patch.object(base, '_platform', return_value='darwin'),
                     patch.object(base, '_home', side_effect=lambda: self.home),
                     patch.object(base, '_list_processes', side_effect=lambda: list(self.processes)),
                     patch.object(base, '_ancestor_commands', side_effect=lambda: list(self.ancestors)),
                     patch.object(state, '_run', side_effect=self.fake_run),
                     patch.object(state, '_current_zone', side_effect=lambda: self.zone)):
            item.start()
            self.addCleanup(item.stop)
        self.terminal = Terminal()
        self.console = (self.terminal, self.terminal)
        self.settings = Path(self.home, '.claude/settings.json')
        self.settings.parent.mkdir(parents=True)

    def fake_run(self, argv, interactive=False):
        self.commands.append((list(argv), interactive))
        if argv[:2] == ['/usr/bin/sudo', state.SYSTEMSETUP]:
            self.zone = argv[-1]
        return self.exit_codes.get((argv[1], argv[-1]), self.exit_codes.get(argv[1], 0))

    def write_settings(self, data):
        self.settings.write_text(json.dumps(data), encoding='utf-8')
        os.chmod(self.settings, 0o600)

    def test_keychain_deletes_only_found_entries_after_terminal_consent_and_never_reads_secrets(self):
        self.exit_codes[('find-generic-password', 'Claude Safe Storage')] = 44
        result = state.keychain(['credentials', 'safe-storage'], console=self.console)
        self.assertEqual(result, {'status': 'deleted', 'deleted': 1})
        verbs = [(c[0][1], c[0][-1]) for c in self.commands]
        self.assertEqual(verbs, [('find-generic-password', 'Claude Code-credentials'),
                                 ('find-generic-password', 'Claude Safe Storage'),
                                 ('delete-generic-password', 'Claude Code-credentials')])
        for argv, _ in self.commands:
            self.assertEqual(argv[0], state.SECURITY)
            self.assertNotIn('-w', argv)
            self.assertNotIn('-g', argv)
        self.assertIn('不可恢复', self.terminal.out.getvalue())

    def test_keychain_nothing_found_or_refused_or_unreadable(self):
        self.exit_codes['find-generic-password'] = 44
        self.assertEqual(state.keychain(['credentials'], console=self.console), {'status': 'nothing_to_delete', 'deleted': 0})
        self.exit_codes['find-generic-password'] = 0
        refusing = Terminal(reply='no')
        with self.assertRaises(state.StateError) as caught:
            state.keychain(['credentials'], console=(refusing, refusing))
        self.assertEqual(caught.exception.code, 'AUTHORIZATION_REQUIRED')
        self.assertFalse(any(c[0][1] == 'delete-generic-password' for c in self.commands))
        self.exit_codes['find-generic-password'] = 1
        with self.assertRaises(state.StateError) as caught:
            state.keychain(['credentials'], console=self.console)
        self.assertEqual(caught.exception.code, 'KEYCHAIN_LOOKUP_FAILED')

    def test_every_action_refuses_when_claude_runs_or_started_from_claude_or_wrong_platform(self):
        for setup, code in ((lambda: self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude'), 'ACTIVE_HOST'),
                            (lambda: self.ancestors.append('/Users/x/.local/share/claude/versions/1/claude'), 'RUNNING_UNDER_CLAUDE')):
            self.processes[:] = ['/usr/sbin/cfprefsd']
            self.ancestors[:] = ['/bin/zsh']
            setup()
            for call in (lambda: state.keychain(['credentials'], console=self.console),
                         lambda: state.simple_mode('on', console=self.console),
                         lambda: state.timezone('Asia/Taipei', console=self.console)):
                with self.subTest(code=code), self.assertRaises(state.StateError) as caught:
                    call()
                self.assertEqual(caught.exception.code, code)
        self.processes[:] = []
        self.ancestors[:] = []
        with patch.object(base, '_platform', return_value='linux'), self.assertRaises(state.StateError) as caught:
            state.keychain(['credentials'], console=self.console)
        self.assertEqual(caught.exception.code, 'UNSUPPORTED_PLATFORM')
        self.assertEqual(self.commands, [])

    def test_simple_mode_edits_only_the_one_key_keeps_telemetry_and_backs_up(self):
        original = {'env': {'DISABLE_TELEMETRY': '1', 'OTHER': 'x'}, 'permissions': {'allow': ['Read']}, 'model': 'm'}
        self.write_settings(original)
        result = state.simple_mode('on', console=self.console)
        self.assertEqual(result, {'status': 'updated', 'state': 'on', 'backup_created': True})
        data = json.loads(self.settings.read_text())
        self.assertEqual(data['env'], {'DISABLE_TELEMETRY': '1', 'OTHER': 'x', 'CLAUDE_CODE_SIMPLE': '1'})
        self.assertEqual((data['permissions'], data['model']), (original['permissions'], original['model']))
        self.assertEqual(oct(os.stat(self.settings).st_mode & 0o777), '0o600')
        backups = list(Path(self.home, base.BACKUP_PARENT).glob('settings.json.*'))
        self.assertEqual(len(backups), 1)
        self.assertEqual(json.loads(backups[0].read_text()), original)
        self.assertEqual(oct(os.stat(backups[0]).st_mode & 0o777), '0o600')
        self.assertIn('订阅登录在此模式下不可用', self.terminal.out.getvalue())
        self.assertEqual(state.simple_mode('on', console=self.console), {'status': 'unchanged'})
        state.simple_mode('off', console=self.console)
        self.assertEqual(json.loads(self.settings.read_text())['env'], original['env'])
        self.assertEqual(state.simple_mode('off', console=self.console), {'status': 'unchanged'})

    def test_simple_mode_rejects_bad_structure_missing_consent_and_creates_no_file_for_off(self):
        self.settings.write_text('[1]')
        with self.assertRaises(state.StateError) as caught:
            state.simple_mode('on', console=self.console)
        self.assertEqual(caught.exception.code, 'SETTINGS_STRUCTURE_UNSUPPORTED')
        self.settings.write_text('{"env": 3}')
        with self.assertRaises(state.StateError) as caught:
            state.simple_mode('on', console=self.console)
        self.assertEqual(caught.exception.code, 'SETTINGS_STRUCTURE_UNSUPPORTED')
        self.settings.write_text('not json')
        with self.assertRaises(state.StateError) as caught:
            state.simple_mode('on', console=self.console)
        self.assertEqual(caught.exception.code, 'SETTINGS_UNREADABLE')
        self.write_settings({'model': 'm'})
        refusing = Terminal(reply='')
        with self.assertRaises(state.StateError) as caught:
            state.simple_mode('on', console=(refusing, refusing))
        self.assertEqual(caught.exception.code, 'AUTHORIZATION_REQUIRED')
        self.assertEqual(json.loads(self.settings.read_text()), {'model': 'm'})
        with self.assertRaises(state.StateError):
            state.simple_mode('maybe', console=self.console)
        self.settings.unlink()
        self.assertEqual(state.simple_mode('off', console=self.console), {'status': 'unchanged'})
        self.assertFalse(self.settings.exists())

    def test_timezone_validates_names_confirms_and_leaves_password_to_sudo(self):
        for bad in ('', 'Asia/../../etc/passwd', 'Not/AZone/Really/Deep', 'x;reboot', '/etc/passwd', None):
            with self.subTest(zone=bad), self.assertRaises(state.StateError) as caught:
                state.timezone(bad, console=self.console)
            self.assertEqual(caught.exception.code, 'INVALID_TIMEZONE')
        self.assertEqual(self.commands, [])
        result = state.timezone('Asia/Taipei', console=self.console)
        self.assertEqual(result, {'status': 'updated', 'previous': 'Asia/Tokyo', 'current': 'Asia/Taipei'})
        argv, interactive = self.commands[-1]
        self.assertEqual(argv, ['/usr/bin/sudo', state.SYSTEMSETUP, '-settimezone', 'Asia/Taipei'])
        self.assertTrue(interactive)  # inherits the terminal so sudo asks for the password itself
        self.assertIn('sudo systemsetup -settimezone Asia/Tokyo', self.terminal.out.getvalue())
        self.assertEqual(state.timezone('Asia/Taipei', console=self.console), {'status': 'unchanged'})

    def test_timezone_verification_waits_for_the_asynchronous_localtime_update(self):
        # Real-device finding F4: /etc/localtime changes a moment after systemsetup returns.
        reads = {'n': 0}
        def lagging():
            reads['n'] += 1
            return 'Asia/Taipei' if reads['n'] >= 4 else 'Asia/Tokyo'
        self.zone = 'Asia/Tokyo'
        with patch.object(state, '_current_zone', side_effect=lagging), patch.object(state.time, 'sleep') as sleep:
            result = state.timezone('Asia/Taipei', console=self.console)
        self.assertEqual(result['status'], 'updated')
        self.assertEqual(sleep.call_count, 2)  # polled, not a fixed long wait

    def test_timezone_refusal_failure_and_failed_verification(self):
        refusing = Terminal(reply='no')
        with self.assertRaises(state.StateError) as caught:
            state.timezone('Asia/Taipei', console=(refusing, refusing))
        self.assertEqual(caught.exception.code, 'AUTHORIZATION_REQUIRED')
        self.assertEqual(self.commands, [])
        self.exit_codes['/usr/sbin/systemsetup'] = 1
        self.exit_codes[state.SYSTEMSETUP] = 1
        with self.assertRaises(state.StateError) as caught:
            state.timezone('Asia/Taipei', console=self.console)
        self.assertEqual(caught.exception.code, 'TIMEZONE_CHANGE_FAILED')
        self.exit_codes.clear()
        with patch.object(state, '_current_zone', return_value='Asia/Tokyo'), patch.object(state.time, 'sleep'), \
                self.assertRaises(state.StateError) as caught:
            state.timezone('Asia/Taipei', console=self.console)
        self.assertEqual(caught.exception.code, 'TIMEZONE_VERIFY_FAILED')

    def test_entry_point_argument_validation_and_json_output(self):
        for argv in ([], ['keychain', '--service=bogus'], ['keychain', 'extra'], ['simple'], ['simple', 'on', 'x'],
                     ['timezone'], ['rotate-ids'], ['identity']):
            with self.subTest(argv=argv), patch('sys.stderr', new_callable=io.StringIO) as err:
                self.assertEqual(state.main(argv, console=self.console), 2)
                self.assertEqual(json.loads(err.getvalue())['code'], 'INVALID_ARGUMENTS')
        self.write_settings({})
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(state.main(['simple', 'on'], console=self.console), 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'updated')


if __name__ == '__main__':
    unittest.main()
