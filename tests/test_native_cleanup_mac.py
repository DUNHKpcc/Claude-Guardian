"""macOS C5 host: disposable home directory, synthetic process list and a scripted terminal."""
import copy
import io
import json
import os
from pathlib import Path
import re
import sys
import tempfile
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import cleanup_cli as cli
import cleanup_transactions as core
import native_cleanup_mac as native
from environment_entry_fixture import local_entry


class Terminal:
    """Scripted live terminal: answers with the phrase the prompt asks for, or a fixed reply."""
    def __init__(self, reply=None, tty=True):
        self.out = io.StringIO()
        self.reply, self.tty, self.prompts = reply, tty, []

    def isatty(self):
        return self.tty

    def write(self, text):
        self.out.write(text)
        self.prompts.append(text)

    def flush(self):
        pass

    def readline(self):
        if self.reply is not None:
            return self.reply + '\n'
        match = re.search(r'CONFIRM \S+ [0-9a-f]{8}', self.prompts[-1])
        return (match.group(0) if match else '') + '\n'


@unittest.skipUnless(os.name == 'posix', 'POSIX synthetic home only')
class NativeCleanupMac(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.home = str(Path(self.tmp.name).resolve())
        os.chmod(self.home, 0o700)
        self.processes = ['/usr/sbin/cfprefsd']
        self.ancestors = ['/bin/zsh', '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal']
        patches = [patch.object(native, '_platform', return_value='darwin'),
                   patch.object(native, '_home', side_effect=lambda: self.home),
                   patch.object(native, '_list_processes', side_effect=lambda: list(self.processes)),
                   patch.object(native, '_ancestor_commands', side_effect=lambda: list(self.ancestors))]
        for item in patches:
            item.start()
            self.addCleanup(item.stop)
        self.cli_root = self.home + '/.claude/cache'
        self.dot_claude = self.home + '/.claude'
        self.desktop = self.home + '/Library/Application Support/Claude'
        for path, files in ((self.cli_root, {'changelog.md': b'h', 'sub/notes.txt': b'n'}),
                            (self.desktop, {'config.json': b'{}', 'Local Storage/x': b'x'})):
            for rel, data in files.items():
                full = Path(path) / rel
                full.parent.mkdir(parents=True, exist_ok=True)
                full.write_bytes(data)
        for name, data in (('history.jsonl', b'prompts'), ('settings.json', b'{}'), ('projects/p/s.jsonl', b'transcript')):
            full = Path(self.dot_claude, name)
            full.parent.mkdir(parents=True, exist_ok=True)
            full.write_bytes(data)
        self.quarantine = self.home + '/.claude-guardian/quarantine'
        os.makedirs(self.quarantine, mode=0o700)
        self.projects = self.home + '/projects'
        os.makedirs(self.projects)
        Path(self.projects, 'code.py').write_text('keep')
        self.backup_dir = self.home + '/.claude-guardian/backups/backup-1'
        self.scope = {'schema_version': cli.SCOPE, 'target_ref': 'mac-a', 'mode': core.MODE,
                      'roots': [{'root_ref': 'cli', 'path': self.cli_root, 'data_kind': 'cli_app_data'},
                                {'root_ref': 'desktop', 'path': self.desktop, 'data_kind': 'desktop_app_data'}],
                      'protected_paths': [self.projects, self.backup_dir],
                      'quarantine_directory': self.quarantine, 'backup_ref': 'backup-1',
                      'host_context_ref': native.context_ref()}
        self.terminal = Terminal()
        self.entry = local_entry('mac-a')
        self.scope_file = Path(self.home) / 'scope.json'
        self.save(self.scope_file, self.scope)

    def save(self, path, document):
        Path(path).write_text(json.dumps(document), encoding='utf-8')
        os.chmod(path, 0o600)

    def host(self, scope=None, console=None):
        return native.MacCleanupHost(scope or self.scope, console=console or (self.terminal, self.terminal))

    def verified_host(self):
        host = self.host()
        host.create_backup()
        return host

    def verify(self, host, scope=None):
        scope = scope or self.scope
        return host.verify(scope['target_ref'], host.scope_digest,
                           {k: scope[k] for k in ('backup_ref', 'host_context_ref')})

    def test_only_fixed_claude_locations_are_classified_and_tiered(self):
        h = self.home
        cases = {h + '/.claude/cache': ('cli_app_data', 'regenerable'),
                 h + '/.claude/telemetry': ('cli_app_data', 'regenerable'),
                 h + '/.claude/stats-cache.json': ('cli_app_data', 'regenerable'),
                 h + '/.claude/shell-snapshots': ('cli_app_data', 'regenerable'),
                 h + '/.claude/statsig': ('cli_app_data', 'regenerable'),
                 h + '/Library/Caches/claude-cli-nodejs': ('cli_app_data', 'regenerable'),
                 h + '/Library/Logs/Claude': ('desktop_app_data', 'regenerable'),
                 h + '/Library/Logs/DiagnosticReports/Claude-2026.ips': ('desktop_app_data', 'regenerable'),
                 h + '/Library/Application Support/CrashReporter/Claude_x.plist': ('desktop_app_data', 'regenerable'),
                 h + '/Library/Caches/com.anthropic.claudefordesktop.ShipIt': ('desktop_app_data', 'regenerable'),
                 h + '/Library/Application Support/Claude': ('desktop_app_data', 'persistent'),
                 h + '/Library/Application Support/com.anthropic.claudefordesktop': ('desktop_app_data', 'persistent'),
                 h + '/Library/WebKit/com.anthropic.claudefordesktop': ('desktop_app_data', 'persistent'),
                 h + '/Library/Saved Application State/com.anthropic.claudefordesktop.savedState': ('desktop_app_data', 'persistent'),
                 h + '/Library/Preferences/ByHost/com.anthropic.claudefordesktop.AB-12.plist': ('desktop_app_data', 'persistent')}
        for path, (kind, level) in cases.items():
            with self.subTest(path=path):
                self.assertEqual((native.classify(path, h), native.tier(path, h)), (kind, level))
        for path in (h, h + '/Documents', h + '/.claude', h + '/.claude/projects', h + '/.claude/projects/p',
                     h + '/.claude/history.jsonl', h + '/.claude/settings.json', h + '/.claude/skills/x',
                     h + '/.claude/.credentials.json', h + '/.claude/backups', h + '/.claude/cache/sub',
                     h + '/Library/Application Support', h + '/Library/Application Support/Claude/sub',
                     h + '/.local/share/claude', h + '/.local/bin/claude', '/Applications/Claude.app',
                     h + '/Library/Caches/other', h + '/Library/Preferences/ByHost/com.apple.x.plist',
                     h + '/.claude.json'):
            with self.subTest(path=path):
                self.assertIsNone(native.classify(path, h))
        for path in (h + '/.claude', h + '/.claude/projects', h + '/.claude/projects/p/s.jsonl',
                     h + '/.claude/history.jsonl', h + '/.claude/.credentials.json', h + '/.claude/skills/x'):
            with self.subTest(protected=path):
                self.assertTrue(native.is_protected(path, h))
        self.assertFalse(native.is_protected(h + '/.claude/cache', h))

    def test_verify_refuses_each_unverified_condition(self):
        host = self.verified_host()
        self.assertEqual(self.verify(host), core.HOST_OK)
        self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        self.assertEqual(self.verify(host), 'active_host')
        self.processes[-1:] = ['/Users/x/.local/share/claude/versions/1/claude']
        self.assertEqual(self.verify(host), 'active_host')
        self.processes[-1:] = []
        with patch.object(native, '_list_processes', side_effect=OSError('no ps')):
            self.assertEqual(self.verify(host), 'active_host')
        with patch.object(native, '_platform', return_value='linux'):
            self.assertEqual(self.verify(host), 'unsupported_platform')
        self.assertEqual(host.verify('other', host.scope_digest, {'backup_ref': 'backup-1',
                         'host_context_ref': self.scope['host_context_ref']}), 'context_mismatch')
        self.assertEqual(host.verify('mac-a', '0' * 64, {'backup_ref': 'backup-1',
                         'host_context_ref': self.scope['host_context_ref']}), 'context_mismatch')

    def test_roots_outside_the_list_and_credential_scopes_are_refused(self):
        other = self.home + '/Documents'
        os.makedirs(other)
        scope = copy.deepcopy(self.scope)
        scope['roots'][0] = {'root_ref': 'cli', 'path': other, 'data_kind': 'cli_app_data'}
        self.assertEqual(self.verify(self.host(scope), scope), 'unknown_ownership')
        scope = copy.deepcopy(self.scope)
        scope['roots'][0] = {'root_ref': 'cli', 'path': self.home + '/.claude.json', 'data_kind': 'cli_app_data'}
        Path(self.home, '.claude.json').write_text('{}')
        self.assertEqual(self.verify(self.host(scope), scope), 'credential_scope')
        scope = copy.deepcopy(self.scope)
        scope['roots'][0]['data_kind'] = 'desktop_app_data'
        self.assertEqual(self.verify(self.host(scope), scope), 'unknown_ownership')
        for protected in (self.dot_claude, self.home + '/.claude/projects', self.home + '/.claude/history.jsonl'):
            with self.subTest(protected=protected):
                scope = copy.deepcopy(self.scope)
                scope['roots'][0] = {'root_ref': 'cli', 'path': protected, 'data_kind': 'cli_app_data'}
                self.assertEqual(self.verify(self.host(scope), scope), 'shared_scope')
                with self.assertRaises(core.CleanupError) as caught:
                    self.host(scope).create_backup()
                self.assertEqual(caught.exception.code, 'SHARED_SCOPE')
        Path(self.desktop, '.credentials.json').write_text('secret-token')
        host = self.host()
        host.create_backup()
        self.assertEqual(self.verify(host), 'credential_scope')

    def test_backup_must_exist_match_and_be_content_verified(self):
        host = self.host()
        self.assertEqual(self.verify(host), 'backup_unverified')
        result = host.create_backup()
        self.assertEqual((result['status'], result['roots'], result['files']), ('backup_created', 2, 4))
        self.assertEqual(self.verify(self.host()), core.HOST_OK)
        for rel in ('.claude/history.jsonl',):
            mode = oct(os.stat(self.backup_dir + '/data/root-0000/changelog.md').st_mode & 0o777)
            self.assertEqual(mode, '0o600')
        self.assertEqual(oct(os.stat(self.backup_dir).st_mode & 0o777), '0o700')
        Path(self.backup_dir + '/data/root-0000/changelog.md').write_bytes(b'X')
        self.assertEqual(self.verify(self.host()), 'backup_unverified')

    def test_live_change_after_backup_invalidates_verification(self):
        host = self.verified_host()
        Path(self.cli_root, 'changelog.md').write_bytes(b'changed-later')
        self.assertEqual(self.verify(host), 'backup_unverified')

    def test_backup_refuses_when_claude_runs_unprotected_or_existing(self):
        self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        with self.assertRaises(core.CleanupError) as caught:
            self.host().create_backup()
        self.assertEqual(caught.exception.code, 'ACTIVE_HOST')
        self.processes.pop()
        scope = copy.deepcopy(self.scope)
        scope['protected_paths'] = [self.projects]
        with self.assertRaises(core.CleanupError) as caught:
            self.host(scope).create_backup()
        self.assertEqual(caught.exception.code, 'BACKUP_NOT_PROTECTED')
        self.host().create_backup()
        with self.assertRaises(FileExistsError):
            self.host().create_backup()
        denied = Terminal(reply='no')
        scope = copy.deepcopy(self.scope)
        scope['backup_ref'] = 'backup-2'
        scope['protected_paths'] = [self.projects, self.home + '/.claude-guardian/backups/backup-2']
        with self.assertRaises(core.CleanupError) as caught:
            native.MacCleanupHost(scope, console=(denied, denied)).create_backup()
        self.assertEqual(caught.exception.code, 'AUTHORIZATION_REQUIRED')
        self.assertFalse(os.path.exists(self.home + '/.claude-guardian/backups/backup-2'))

    def test_approval_needs_live_terminal_and_exact_phrase_bound_to_operation_and_digest(self):
        digest = 'ab' * 32
        host = self.host(console=(Terminal(tty=False), Terminal(tty=False)))
        self.assertFalse(host.approve('quarantine', digest, 'mac-a', {}))
        for reply in ('', 'yes', 'confirm quarantine abababab', 'CONFIRM restore_cleanup abababab',
                      'CONFIRM quarantine 00000000', 'CONFIRM quarantine abababab extra'):
            with self.subTest(reply=reply):
                terminal = Terminal(reply=reply)
                self.assertFalse(self.host(console=(terminal, terminal)).approve('quarantine', digest, 'mac-a', {}))
        self.assertFalse(self.host().approve('unknown_operation', digest, 'mac-a', {}))
        self.assertFalse(self.host().approve('quarantine', 'short', 'mac-a', {}))
        terminal = Terminal()
        host = self.host(console=(terminal, terminal))
        self.assertTrue(host.approve('quarantine', digest, 'mac-a', {}))
        self.assertIn('.claude', terminal.out.getvalue())
        self.assertIn('可再生缓存/日志', terminal.out.getvalue())
        self.assertIn('始终受保护', terminal.out.getvalue())
        self.assertFalse(host.approve('restore_cleanup', digest, 'mac-a', {}) is True and len(terminal.prompts) == 1)
        self.assertTrue(host.approve('quarantine', digest, 'mac-a', {}))  # same operation and digest: one consent
        self.assertEqual(sum('操作: quarantine' in p for p in terminal.prompts), 1)

    def test_exclusive_requires_verified_scope_and_detects_start_during_section(self):
        host = self.verified_host()
        with host.exclusive('mac-a', host.scope_digest, {k: self.scope[k] for k in ('backup_ref', 'host_context_ref')}):
            pass
        self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        with self.assertRaises(RuntimeError):
            with host.exclusive('mac-a', host.scope_digest, {k: self.scope[k] for k in ('backup_ref', 'host_context_ref')}):
                self.fail('entered with Claude running')
        self.processes.pop()
        with self.assertRaises(RuntimeError):
            with host.exclusive('mac-a', host.scope_digest, {k: self.scope[k] for k in ('backup_ref', 'host_context_ref')}):
                self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        self.assertFalse(host.cancelled())

    def run_cli(self, args, host):
        out = io.StringIO()
        entry = self.entry if args[0] in ('plan', 'quarantine') else None
        code = cli.main(args, host=host, stdout=out, entry_request=entry)
        return code, json.loads(out.getvalue())

    def test_real_core_roundtrip_backup_plan_quarantine_reconcile_restore(self):
        host = self.verified_host()
        plan_file = Path(self.home) / 'plan.json'
        receipt_file = Path(self.home) / 'receipt.json'
        code, result = self.run_cli(['plan', '--scope', str(self.scope_file), '--plan-output', str(plan_file)], host)
        self.assertEqual(code, 0, result)
        digest = result['document_digest']
        code, result = self.run_cli(['quarantine', '--plan-file', str(plan_file), '--expected-plan-digest', digest], host)
        self.assertEqual(code, 0, result)
        self.assertFalse(os.path.exists(self.cli_root))
        self.assertFalse(os.path.exists(self.desktop))
        self.assertEqual(Path(self.projects, 'code.py').read_text(), 'keep')
        for name in ('history.jsonl', 'settings.json', 'projects/p/s.jsonl'):
            self.assertTrue(Path(self.dot_claude, name).exists(), name)
        self.assertEqual(self.verify(host), core.HOST_OK)  # roots verified at the quarantine location
        code, result = self.run_cli(['reconcile', '--plan-file', str(plan_file), '--expected-plan-digest', digest,
                                     '--receipt-output', str(receipt_file)], host)
        self.assertEqual(code, 0, result)
        code, result = self.run_cli(['restore', '--receipt-file', str(receipt_file),
                                     '--expected-receipt-digest', result['document_digest']], host)
        self.assertEqual(code, 0, result)
        self.assertEqual(Path(self.cli_root, 'changelog.md').read_bytes(), b'h')
        self.assertEqual(Path(self.dot_claude, 'history.jsonl').read_bytes(), b'prompts')
        self.assertEqual(Path(self.desktop, 'Local Storage/x').read_bytes(), b'x')
        self.assertTrue(os.path.isdir(self.backup_dir + '/data/root-0000'))

    def test_quarantine_stops_without_terminal_consent_and_when_claude_is_running(self):
        host = self.verified_host()
        plan_file = Path(self.home) / 'plan.json'
        code, result = self.run_cli(['plan', '--scope', str(self.scope_file), '--plan-output', str(plan_file)], host)
        digest = result['document_digest']
        argv = ['quarantine', '--plan-file', str(plan_file), '--expected-plan-digest', digest]
        refusing = Terminal(reply='no')
        code, result = self.run_cli(argv, native.MacCleanupHost(self.scope, console=(refusing, refusing)))
        self.assertEqual((code, result['code']), (2, 'AUTHORIZATION_REQUIRED'))
        silent = Terminal(tty=False)
        code, result = self.run_cli(argv, native.MacCleanupHost(self.scope, console=(silent, silent)))
        self.assertEqual((code, result['code']), (2, 'AUTHORIZATION_REQUIRED'))
        self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        code, result = self.run_cli(argv, host)
        self.assertEqual((code, result['code']), (2, 'HOST_SCOPE_UNVERIFIED'))
        self.assertEqual(host.last_refusal, 'active_host')
        self.assertTrue(os.path.exists(self.cli_root) and os.path.exists(self.desktop))

    def test_entry_point_reports_context_and_allowed_list_and_blocks_other_platforms(self):
        for command in ('context', 'allowed'):
            with patch('sys.stdout', new_callable=io.StringIO) as out:
                self.assertEqual(native.main([command]), 0)
            self.assertNotIn(self.home, out.getvalue())
        self.assertEqual(json.loads(out.getvalue())['not_in_scope'][:2], ['~/.claude (whole directory)', '~/.claude.json (credential_scope)'])
        with patch.object(native, '_platform', return_value='linux'), patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(native.main(['context']), 2)
        self.assertEqual(json.loads(err.getvalue())['code'], 'UNSUPPORTED_PLATFORM')
        with patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(native.main(['quarantine', '--plan-file', 'x']), 2)
        self.assertEqual(json.loads(err.getvalue())['code'], 'SCOPE_REQUIRED')
        with patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(native.main(['purge']), 2)
        self.assertEqual(json.loads(err.getvalue())['code'], 'INVALID_ARGUMENTS')

    def test_entry_point_backup_plan_quarantine_with_scripted_terminal_and_refusal_detail(self):
        entry_file = Path(self.home) / 'entry.json'
        self.save(entry_file, self.entry)
        plan_file = Path(self.home) / 'plan.json'
        console = (self.terminal, self.terminal)
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(native.main(['backup', '--scope', str(self.scope_file)], console=console), 0)
        self.assertEqual(json.loads(out.getvalue())['status'], 'backup_created')
        self.assertNotIn(self.home, out.getvalue())
        with patch('sys.stdout', new_callable=io.StringIO) as out:
            self.assertEqual(native.main(['plan', '--scope', str(self.scope_file), '--plan-output', str(plan_file),
                                          '--entry-file', str(entry_file)], console=console), 0)
        digest = json.loads(out.getvalue())['document_digest']
        argv = ['quarantine', '--plan-file', str(plan_file), '--expected-plan-digest', digest,
                '--host-scope', str(self.scope_file), '--entry-file', str(entry_file)]
        self.processes.append('/Applications/Claude.app/Contents/MacOS/Claude')
        with patch('sys.stdout', new_callable=io.StringIO), patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(native.main(argv, console=console), 2)
        self.assertEqual(json.loads(err.getvalue())['host_refusal'], 'active_host')
        self.processes.pop()
        with patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(native.main(argv, console=console), 0)
        self.assertFalse(os.path.exists(self.cli_root))
        with patch('sys.stderr', new_callable=io.StringIO) as err:
            self.assertEqual(native.main(argv[:-2] + ['--entry-file', str(Path(self.home) / 'missing.json')],
                                         console=console), 2)
        self.assertEqual(json.loads(err.getvalue())['code'], 'INVALID_ENTRY_FILE')

    def test_refuses_to_run_under_claude_code_or_the_claude_app(self):
        for ancestors in (['/bin/zsh', '/Users/x/.local/share/claude/versions/2/claude'],
                          ['/bin/zsh', '/Applications/Claude.app/Contents/MacOS/Claude'], ['/bin/zsh', 'claude-code']):
            with self.subTest(ancestors=ancestors):
                self.ancestors[:] = ancestors
                self.assertTrue(native.running_under_claude())
                with patch('sys.stderr', new_callable=io.StringIO) as err:
                    self.assertEqual(native.main(['backup', '--scope', str(self.scope_file)],
                                                 console=(self.terminal, self.terminal)), 2)
                self.assertEqual(json.loads(err.getvalue())['code'], 'RUNNING_UNDER_CLAUDE')
                self.assertFalse(os.path.exists(self.backup_dir))
        self.ancestors[:] = ['/bin/zsh', '/Applications/Utilities/Terminal.app/Contents/MacOS/Terminal']
        self.assertFalse(native.running_under_claude())
        with patch.object(native, '_ancestor_commands', side_effect=OSError('no ps')):
            self.assertTrue(native.running_under_claude())  # unknown ancestry fails closed
        with patch('sys.stdout', new_callable=io.StringIO):
            self.assertEqual(native.main(['context']), 0)  # read-only helpers still work


if __name__ == '__main__':
    unittest.main()
