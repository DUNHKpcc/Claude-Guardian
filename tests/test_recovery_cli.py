"""Independent-process offline recovery; exclusively synthetic temporary files."""
import importlib.util
import json
import os
from pathlib import Path
import select
import re
import subprocess
import sys
import tempfile
import time
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
CLI = SCRIPTS / 'recovery_cli.py'
spec = importlib.util.spec_from_file_location('recovery_transactions', SCRIPTS / 'transactions.py')
tx = importlib.util.module_from_spec(spec)
spec.loader.exec_module(tx)

PRODUCER = '''
import json, os, sys
sys.path.insert(0, sys.argv[1])
import transactions as t
path, backup, crash = sys.argv[2:]
p = t.plan(path, b'new synthetic data', 'synthetic-device')
expected = t.digest({'plan': p, 'backup_directory': backup})
n = 0
def authorize(op, d, target):
    global n
    n += 1
    if crash == 'prepared' and n == 2:
        os._exit(73)
    return op == 'apply' and d == expected and target == 'synthetic-device'
write = t._write
def crash_write(fd, name, data, mode=0o600):
    if crash == 'committed' and name == 'applied.json':
        os._exit(74)
    return write(fd, name, data, mode)
t._write = crash_write
r = t.apply(p, target_ref='synthetic-device', backup_directory=backup,
            authorize=authorize, exclusive_access=True)
print(t.digest(r))
'''


@unittest.skipUnless(os.name == 'posix', 'POSIX recovery only; Windows unsupported')
class RecoveryCLI(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name).resolve()
        self.file = self.root / 'synthetic-config'
        self.file.write_bytes(b'original synthetic data')
        self.file.chmod(0o600)
        self.backups = self.root / 'backups'
        self.backups.mkdir(mode=0o700)
        self.make_transaction()

    def make_transaction(self, crash='none'):
        result = subprocess.run([sys.executable, '-B', '-c', PRODUCER, str(SCRIPTS),
                                 str(self.file), str(self.backups), crash],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, {'none': 0, 'prepared': 73, 'committed': 74}[crash], result.stderr)
        self.batch = sorted(self.backups.iterdir())[-1]
        self.receipt = self.batch / ('applied.json' if crash == 'none' else 'prepared.json')
        self.document = json.loads(self.receipt.read_text())
        self.digest = tx.digest(self.document)

    def args(self, command='preview'):
        return [sys.executable, '-B', str(CLI), command, '--receipt', str(self.receipt),
                '--receipt-digest', self.digest, '--target-ref', 'synthetic-device',
                '--target-path', str(self.file), '--backup-batch', str(self.batch)]

    def run_cli(self, command='preview', extra=(), input=None):
        return subprocess.run(self.args(command) + list(extra), input=input,
                              capture_output=True, text=True, timeout=10)

    def tree(self):
        return {str(p.relative_to(self.root)): (p.stat().st_mode, p.read_bytes())
                for p in self.root.rglob('*') if p.is_file()}

    def terminal(self, responses, on_prompt=None, extra=(), queued_input=None, command='rollback'):
        import pty
        master, slave = pty.openpty()
        proc = subprocess.Popen(self.args(command) + list(extra), stdin=slave,
                                stdout=slave, stderr=slave, close_fds=True)
        os.close(slave)
        self.addCleanup(lambda: proc.kill() if proc.poll() is None else None)
        output = bytearray()
        sent = 0
        deadline = time.monotonic() + 12
        try:
            while time.monotonic() < deadline:
                if select.select([master], [], [], .1)[0]:
                    try:
                        block = os.read(master, 65536)
                    except OSError:
                        break
                    if not block:
                        break
                    output.extend(block)
                    prompts = output.count(b'or cancel:')
                    while sent < prompts:
                        if on_prompt:
                            on_prompt(sent)
                        if sent < len(responses) and responses[sent] is not None:
                            response = responses[sent]
                            challenges = re.findall(rb'Type exactly ("[^"\r\n]+") or cancel:', output)
                            challenge = json.loads(challenges[sent])
                            if challenge.rsplit(' ', 1)[0] == response:
                                response = challenge  # Enter this prompt's newly displayed nonce.
                            payload = response + '\n'
                            if sent == 0 and queued_input is not None:
                                payload += queued_input
                            os.write(master, payload.encode())
                        sent += 1
                if proc.poll() is not None:
                    # Drain the terminal through EOF rather than drop final output.
                    continue
            else:
                self.fail('Recovery terminal failed to finish within test deadline')
            return proc.wait(timeout=2), output.decode(errors='replace')
        finally:
            os.close(master)
            if proc.poll() is None:
                proc.kill()
                proc.wait()

    def approvals(self):
        return ['EXCLUSIVE ACCESS ESTABLISHED', 'ROLLBACK ' + self.digest,
                'ROLLBACK ' + self.digest]

    def test_inspect_and_preview_are_nonmutating(self):
        before = self.tree()
        result = subprocess.run([sys.executable, '-B', str(CLI), 'inspect', '--receipt',
                                 str(self.receipt)], capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(json.loads(result.stdout)['status'], 'unverified_candidate')
        self.assertEqual(json.loads(result.stdout)['candidate_receipt_digest'], self.digest)
        self.assertEqual(self.run_cli().returncode, 0)
        self.assertEqual(self.tree(), before)
        self.assertNotIn('new synthetic data', result.stdout)

    def test_independent_terminal_restores_bytes_retains_receipts(self):
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 0, output)
        self.assertEqual(self.file.read_bytes(), b'original synthetic data')
        self.assertTrue(self.receipt.exists())
        self.assertEqual(len(list(self.batch.glob('rollback-*.json'))), 1)
        self.assertIn('"state": "restored"', output)

    def test_no_approval_and_no_yes_override(self):
        before = self.tree()
        result = self.run_cli('rollback', input='\n'.join(self.approvals()) + '\n')
        self.assertIn('INTERACTIVE_TERMINAL_REQUIRED', result.stderr)
        self.assertNotEqual(self.run_cli('rollback', ('--yes',)).returncode, 0)
        self.assertEqual(self.tree(), before)

    def test_cancel_at_every_prompt(self):
        for index in range(3):
            with self.subTest(prompt=index):
                before = self.tree()
                responses = self.approvals()[:index] + ['cancel']
                code, output = self.terminal(responses)
                self.assertEqual(code, 2, output)
                self.assertEqual(self.tree(), before)

    def test_queued_approval_lines_cannot_approve_later_prompts(self):
        before = self.tree()
        # The first response is current and valid; subsequent pasted answers are
        # premature, even if they contain the exact receipt digest.
        future = ('ROLLBACK ' + self.digest + '\n') * 2
        code, output = self.terminal(['EXCLUSIVE ACCESS ESTABLISHED', None],
                                     queued_input=future,
                                     extra=('--approval-timeout', '1'))
        self.assertEqual(code, 2, output)
        self.assertIn('Approval 1/2', output)
        self.assertNotIn('Approval 2/2', output)
        self.assertNotIn('"state": "restored"', output)
        self.assertEqual(self.tree(), before)

    def test_timeout_fails_closed(self):
        before = self.tree()
        code, output = self.terminal([None], extra=('--approval-timeout', '1'))
        self.assertEqual(code, 2, output)
        self.assertIn('APPROVAL_TIMEOUT', output)
        self.assertEqual(self.tree(), before)

    def test_stale_target_and_same_bytes_new_inode_blocked(self):
        for value in (b'later user edit', b'new synthetic data'):
            other = self.root / 'replacement'
            other.write_bytes(value)
            os.replace(other, self.file)
            before = self.tree()
            result = self.run_cli()
            self.assertIn('ROLLBACK_CONFLICT', result.stderr)
            self.assertEqual(self.tree(), before)

    def test_edit_during_final_confirmation_is_preserved(self):
        def edit(index):
            if index == 2:
                self.file.write_bytes(b'later user edit')
        code, output = self.terminal(self.approvals(), on_prompt=edit)
        self.assertEqual(code, 2, output)
        self.assertIn('STALE_FILE', output)
        self.assertEqual(self.file.read_bytes(), b'later user edit')
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_corrupt_backup_and_receipt_are_blocked(self):
        original = self.batch / 'original.bin'
        original.write_bytes(b'corrupt')
        self.assertIn('BACKUP_CORRUPT', self.run_cli().stderr)
        self.receipt.write_text('{}')
        self.assertIn('RECEIPT_DIGEST_MISMATCH', self.run_cli().stderr)

    def test_expired_plan_can_recover_with_fresh_approval(self):
        self.document['plan']['created_at'] = 1
        self.document['plan']['expires_at'] = 2
        self.receipt.write_text(json.dumps(self.document))
        self.digest = tx.digest(self.document)
        code, output = self.terminal(self.approvals())
        self.assertEqual(code, 0, output)

    def test_wrong_scope_precedes_embedded_path_reads(self):
        for option, value, error in (
                ('--target-path', str(self.root / 'nonexistent'), 'TARGET_MISMATCH'),
                ('--target-ref', 'wrong-device', 'TARGET_MISMATCH'),
                ('--backup-batch', str(self.root / 'nonexistent'), 'BACKUP_SCOPE_MISMATCH')):
            self.assertIn(error, self.run_cli(extra=(option, value)).stderr)

    def test_inspect_never_reads_embedded_paths(self):
        self.receipt.write_text(json.dumps({'plan': {'path': '/never/read/this'},
                                          'backup_directory': '/also/never/read'}))
        result = self.run_cli('inspect')
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertNotIn('/never/read', result.stdout)

    def test_unsafe_receipt_inputs(self):
        original = self.receipt.read_bytes()
        for content in (b'{"a":1,"a":2}', b'{', b'[[[' * 1000,
                        b' ' * (tx.MAX_DOCUMENT + 1)):
            self.receipt.write_bytes(content)
            result = self.run_cli('inspect')
            self.assertNotEqual(result.returncode, 0)
            self.assertNotIn('Traceback', result.stderr)
        self.receipt.write_bytes(original)
        self.receipt.chmod(0o644)
        self.assertIn('UNSAFE_RECEIPT_FILE', self.run_cli('inspect').stderr)
        self.receipt.chmod(0o600)
        alias = self.root / 'hardlink'
        os.link(self.receipt, alias)
        self.assertIn('UNSAFE_RECEIPT_FILE', self.run_cli('inspect').stderr)
        alias.unlink()
        self.receipt.unlink()
        os.symlink(self.file, self.receipt)
        self.assertNotEqual(self.run_cli('inspect').returncode, 0)
        self.receipt.unlink()
        os.mkfifo(self.receipt, 0o600)
        self.assertIn('UNSAFE_RECEIPT_FILE', self.run_cli('inspect').stderr)

    def test_symlink_parent_rejected(self):
        alias = self.root / 'alias'
        alias.symlink_to(self.batch, target_is_directory=True)
        self.assertIn('UNSAFE_OR_UNAVAILABLE_DIRECTORY',
                      self.run_cli(extra=('--receipt', str(alias / 'applied.json'))).stderr)

    def test_crashed_prepared_states_never_replayed(self):
        for crash in ('prepared', 'committed'):
            with self.subTest(crash=crash):
                self.backups = self.root / ('backups-' + crash)
                self.backups.mkdir(mode=0o700)
                self.file.write_bytes(b'original synthetic data')
                self.make_transaction(crash)
                before = self.tree()
                self.assertEqual(self.run_cli('inspect').returncode, 0)
                self.assertIn('RECOVERY_REQUIRES_RECONCILIATION', self.run_cli().stderr)
                self.assertIn('RECOVERY_REQUIRES_RECONCILIATION', self.run_cli('rollback').stderr)
                self.assertEqual(self.tree(), before)

    def test_write_failure_retains_backup_and_reports_blocked(self):
        # Separate process failure injection; only the dedicated synthetic batch.
        runner = '''
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
c.confirm = lambda *args: None
c.tx._write = lambda *args, **kwargs: (_ for _ in ()).throw(OSError('synthetic failure'))
sys.exit(c.main(sys.argv[2:]))
'''
        result = subprocess.run([sys.executable, '-B', '-c', runner, str(SCRIPTS)] + self.args('rollback')[3:],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('IO_FAILURE', result.stderr)
        self.assertEqual(self.file.read_bytes(), b'new synthetic data')
        self.assertEqual((self.batch / 'original.bin').read_bytes(), b'original synthetic data')

    def test_receipt_edit_during_final_confirmation_cancels(self):
        def edit(index):
            if index == 2:
                self.receipt.write_text('{}')
        code, output = self.terminal(self.approvals(), on_prompt=edit)
        self.assertEqual(code, 2, output)
        self.assertIn('AUTHORIZATION_CANCELLED', output)
        self.assertEqual(self.file.read_bytes(), b'new synthetic data')
        self.assertFalse(list(self.root.glob('.guardian-stage-*')))

    def test_journal_failure_reports_error_even_after_restoration(self):
        runner = """
import sys
sys.path.insert(0, sys.argv[1])
import recovery_cli as c
c.confirm = lambda *args: None
write = c.tx._write
def fail_journal(fd, name, data, mode=0o600):
    if name.startswith('rollback-'):
        raise OSError('synthetic journal failure')
    return write(fd, name, data, mode)
c.tx._write = fail_journal
sys.exit(c.main(sys.argv[2:]))
"""
        result = subprocess.run([sys.executable, '-B', '-c', runner, str(SCRIPTS)] + self.args('rollback')[3:],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 2, result.stderr)
        self.assertIn('IO_FAILURE', result.stderr)
        self.assertEqual(self.file.read_bytes(), b'original synthetic data')
        self.assertTrue(self.receipt.exists())
        self.assertFalse(list(self.batch.glob('rollback-*.json')))
        self.assertIn('ROLLBACK_CONFLICT', self.run_cli().stderr)

    def test_normal_inspection_does_not_create_import_cache(self):
        # A clean synthetic copy proves ordinary invocation needs no -B flag.
        import shutil
        isolated = self.root / 'tool'
        isolated.mkdir(mode=0o700)
        for name in ('recovery_cli.py', 'transactions.py'):
            shutil.copyfile(SCRIPTS / name, isolated / name)
        result = subprocess.run([sys.executable, str(isolated / 'recovery_cli.py'),
                                 'inspect', '--receipt', str(self.receipt)],
                                capture_output=True, text=True, timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertFalse((isolated / '__pycache__').exists())

    def test_windows_support_gate(self):
        with patch.object(tx.os, 'name', 'nt'):
            with self.assertRaisesRegex(tx.TransactionError, 'PLATFORM_UNSUPPORTED'):
                tx._support()


if __name__ == '__main__':
    unittest.main()
