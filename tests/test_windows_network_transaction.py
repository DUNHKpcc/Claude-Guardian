"""Actual transaction worker and step subprocesses against private temporary files.

Only scheduling, administrator admission and host paths are replaced. No network
settings, real scheduled tasks or user configuration are accessed.
"""
import hashlib
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import time
import unittest

ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / 'skills/claude-guardian/assets/killswitch/windows-network-transaction.ps1'
PS = shutil.which('powershell.exe') or shutil.which('pwsh')


@unittest.skipUnless(PS, 'PowerShell required; runs natively in Windows CI')
class NetworkTransaction(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)
        source = SOURCE.read_text(encoding='utf-8-sig')
        source = source.replace("$Root = Join-Path $env:ProgramData 'ClaudeGuardian\\NetworkTransaction'",
                                "$Root = '" + str(self.directory).replace("'", "''") + "'")
        source = source.replace("$PowerShell = Join-Path $env:SystemRoot 'System32\\WindowsPowerShell\\v1.0\\powershell.exe'",
                                "$PowerShell = '" + PS.replace("'", "''") + "'")
        source = source.replace('Global\\ClaudeGuardian-NetworkTransaction', 'GuardianFixture-' + self.directory.name)
        source = source.replace('Require-Administrator\nswitch', 'switch')
        boundary = "\nfunction Unregister-ScheduledTask { param($TaskName,[switch]$Confirm) }\n"
        if os.name != 'nt':
            boundary += '''
function Start-Process {
 param($FilePath,$ArgumentList,[switch]$PassThru,$WindowStyle,$RedirectStandardOutput,$RedirectStandardError)
 Microsoft.PowerShell.Management\\Start-Process -FilePath $FilePath -ArgumentList $ArgumentList -PassThru -RedirectStandardOutput $RedirectStandardOutput -RedirectStandardError $RedirectStandardError
}
'''
        source = source.replace('switch ($Action) {', boundary + '\nswitch ($Action) {')
        self.worker = self.directory / 'worker.ps1'
        self.worker.write_text(source, encoding='utf-8-sig')
        self.processes = []
        self.addCleanup(self.stop_workers)

    def stop_workers(self):
        for process in self.processes:
            if process.poll() is None:
                process.kill()
            process.wait(timeout=10)

    def make_state(self, *, timeout=15, fail_apply=None, fail_restore=None, fail_prepare=None):
        steps = []
        for name in ('dns', 'proxy'):
            text = r'''
param($Operation,$Snapshot)
$ErrorActionPreference='Stop'
$file = Join-Path $PSScriptRoot 'NAME.value'
Add-Content -LiteralPath (Join-Path $PSScriptRoot 'operations') -Value ('NAME:' + $Operation)
switch ($Operation) {
 'Prepare' {
  if ('FAIL_PREPARE' -eq 'NAME') { throw 'prepare fixture failure' }
  @{value=(Get-Content -LiteralPath $file -Raw).Trim()} | ConvertTo-Json | Set-Content -LiteralPath $Snapshot
 }
 'Apply' {
  Set-Content -LiteralPath $file -Value 'new'
  if ('FAIL_APPLY' -eq 'NAME') { throw 'partially applied fixture failure' }
 }
 'Check' {
  if ((Get-Content -LiteralPath $file -Raw).Trim() -ne 'new') { throw 'unexpected applied value' }
 }
 'Restore' {
  if ('FAIL_RESTORE' -eq 'NAME') { throw 'restore fixture failure' }
  Set-Content -LiteralPath $file -Value ((Get-Content -LiteralPath $Snapshot -Raw | ConvertFrom-Json).value)
 }
 'CheckRestore' {
  if ((Get-Content -LiteralPath $file -Raw).Trim() -ne (Get-Content -LiteralPath $Snapshot -Raw | ConvertFrom-Json).value) { throw 'restore readback failed' }
 }
}
'''.replace('FAIL_PREPARE', str(fail_prepare)).replace('FAIL_APPLY', str(fail_apply)).replace('FAIL_RESTORE', str(fail_restore)).replace('NAME', name)
            script = self.directory / (name + '.ps1')
            script.write_text(text, encoding='utf-8-sig')
            (self.directory / (name + '.value')).write_text('original', encoding='utf-8')
            steps.append({'id': name, 'script': script.name, 'scope': 'temporary fixture only',
                          'sha256': hashlib.sha256(script.read_bytes()).hexdigest().upper()})
        state = {'version': 1, 'id': 'fixture-id', 'target': 'fixture',
                 'phase': 'queued', 'timeout_seconds': timeout, 'deadline': 0, 'steps': steps,
                 'started': [], 'restored': [], 'failed': []}
        # .NET MachineName omits a DNS suffix on some hosts.
        machine = subprocess.run([PS, '-NoProfile', '-Command', '[Environment]::MachineName'],
                                 capture_output=True, text=True, encoding='utf-8', timeout=15, check=True)
        state['target'] = machine.stdout.strip()
        self.write_state(state)
        (self.directory / 'released').touch()
        return state

    def write_state(self, state):
        (self.directory / 'state.json').write_text(json.dumps(state), encoding='utf-8')

    def state(self):
        return json.loads((self.directory / 'state.json').read_text(encoding='utf-8-sig'))

    def launch(self):
        p = subprocess.Popen([PS, '-NoProfile', '-File', str(self.worker), '-Action', 'Worker'],
                             stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        self.processes.append(p)
        return p

    def wait_phase(self, phases, timeout=60):
        deadline = time.monotonic() + timeout
        while time.monotonic() < deadline:
            state = self.state()
            if state['phase'] in phases:
                return state
            if state['phase'] in {'prepare_failed', 'recovery_failed'} and state['phase'] not in phases:
                break
            time.sleep(.1)
        logs = '\n'.join(p.read_text(encoding='utf-8-sig', errors='replace') for p in self.directory.glob('*.log'))
        self.fail(f'phase {self.state()}: {logs}')

    def test_agent_process_exit_does_not_cancel_deadline_restore(self):
        self.make_state()
        # The short-lived launcher represents the Agent's shell. Worker outlives it.
        code = 'import subprocess,sys; subprocess.Popen(sys.argv[1:], stdin=subprocess.DEVNULL, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)'
        subprocess.run([sys.executable, '-c', code, PS, '-NoProfile', '-File', str(self.worker), '-Action', 'Worker'], check=True, timeout=10)
        state = self.wait_phase({'restored'})
        self.assertEqual(state['restored'], ['proxy', 'dns'])
        for name in ('dns', 'proxy'):
            self.assertEqual((self.directory / (name + '.value')).read_text(encoding='utf-8-sig').strip(), 'original')

    def test_partial_step_is_restored_before_previous_step(self):
        self.make_state(fail_apply='proxy')
        p = self.launch()
        state = self.wait_phase({'restored'})
        self.assertEqual(state['started'], ['dns', 'proxy'])
        self.assertEqual(state['restored'], ['proxy', 'dns'])
        self.assertEqual(p.wait(timeout=10), 0)

    def test_prepare_failure_and_unreleased_task_never_apply(self):
        self.make_state(fail_prepare='proxy')
        (self.directory / 'released').unlink()
        self.assertEqual(self.launch().wait(timeout=15), 0)
        self.assertEqual(self.state()['phase'], 'queued')
        self.assertFalse((self.directory / 'operations').exists())
        (self.directory / 'released').touch()
        self.assertEqual(self.launch().wait(timeout=20), 0)
        self.assertEqual(self.state()['phase'], 'prepare_failed')
        self.assertTrue((self.directory / 'operations').exists(),
                        (self.directory / 'worker-errors.log').read_text(encoding='utf-8-sig'))
        self.assertNotIn(':Apply', (self.directory / 'operations').read_text(encoding='utf-8-sig'))

    def test_failed_restore_retains_failure_and_continues_other_steps(self):
        self.make_state(fail_apply='proxy', fail_restore='proxy')
        self.assertEqual(self.launch().wait(timeout=30), 0)
        state = self.state()
        self.assertEqual(state['phase'], 'recovery_failed',
                         (self.directory / 'worker-errors.log').read_text(encoding='utf-8-sig'))
        self.assertEqual(state['failed'], ['proxy'])
        self.assertEqual(state['restored'], ['dns'])
        self.assertEqual((self.directory / 'dns.value').read_text(encoding='utf-8-sig').strip(), 'original')

    def test_commit_rechecks_actual_state_and_refuses_drift(self):
        self.make_state(timeout=20)
        p = self.launch()
        self.wait_phase({'awaiting_commit'})
        (self.directory / 'dns.value').write_text('drift', encoding='utf-8')
        (self.directory / 'commit').write_text('fixture-id', encoding='utf-8')
        self.assertEqual(self.wait_phase({'restored'})['phase'], 'restored')
        self.assertEqual(p.wait(timeout=10), 0)

    def test_valid_commit_is_durable_and_worker_retry_does_not_undo_it(self):
        self.make_state(timeout=20)
        p = self.launch()
        self.wait_phase({'awaiting_commit'})
        (self.directory / 'commit').write_text('fixture-id', encoding='utf-8')
        self.wait_phase({'committed'})
        self.assertEqual(p.wait(timeout=10), 0)
        self.assertEqual(self.launch().wait(timeout=10), 0)
        self.assertEqual((self.directory / 'dns.value').read_text(encoding='utf-8-sig').strip(), 'new')

    def test_interrupted_transaction_restores_without_resuming_apply(self):
        state = self.make_state()
        for name in ('dns', 'proxy'):
            (self.directory / (name + '.snapshot.json')).write_text('{"value":"original"}', encoding='utf-8')
            (self.directory / (name + '.value')).write_text('new', encoding='utf-8')
        state.update(phase='applying', started=['dns','proxy'])
        self.write_state(state)
        self.assertEqual(self.launch().wait(timeout=20), 0)
        self.assertEqual(self.state()['phase'], 'restored')
        self.assertNotIn(':Apply', (self.directory / 'operations').read_text(encoding='utf-8-sig'))

    def test_changed_script_never_executes(self):
        self.make_state()
        with (self.directory / 'dns.ps1').open('a') as f:
            f.write('\nthrow "changed"\n')
        self.assertEqual(self.launch().wait(timeout=10), 0)
        self.assertEqual(self.state()['phase'], 'prepare_failed')
        self.assertFalse((self.directory / 'operations').exists())

    def test_plan_rejects_wrong_target_and_nonlocal_step_paths(self):
        self.make_state()
        source = SOURCE.read_text(encoding='utf-8-sig')
        functions = source[source.index('function Save-State'):source.index('function Require-Administrator')]
        plan_path = self.directory / 'plan.json'
        plan = {'version': 1, 'target': self.state()['target'], 'restore_goal': 'temporary fixture',
                'timeout_seconds': 60, 'steps': [{'id': 'dns', 'script': 'dns.ps1', 'scope': 'fixture'}]}
        probe = self.directory / 'validate.ps1'
        probe.write_text("param($Plan)\n$ErrorActionPreference='Stop'\n" + functions +
                         "\ntry { Read-Plan $Plan | Out-Null; exit 0 } catch { [Console]::Error.WriteLine($_.ToString()); exit 2 }", encoding='utf-8-sig')
        for field, value, expected in [('target', plan['target'], 0), ('target', 'different-target', 2),
                                       ('timeout_seconds', 0, 2), ('timeout_seconds', '60', 2)]:
            candidate = dict(plan, **{field: value})
            plan_path.write_text(json.dumps(candidate), encoding='utf-8')
            result = subprocess.run([PS, '-NoProfile', '-File', str(probe), '-Plan', str(plan_path)], capture_output=True, timeout=15)
            self.assertEqual(result.returncode, expected, (field, value, result.stderr))
        for script in ('../dns.ps1', 'worker.ps1', 'https://example.invalid/a.ps1'):
            plan['steps'][0]['script'] = script
            plan_path.write_text(json.dumps(plan), encoding='utf-8')
            self.assertEqual(subprocess.run([PS, '-NoProfile', '-File', str(probe), '-Plan', str(plan_path)], capture_output=True, timeout=15).returncode, 2)

    @unittest.skipUnless(os.name == 'nt', 'Windows process-tree termination')
    def test_timed_out_step_is_stopped_before_restore(self):
        state = self.make_state(timeout=5)
        script = self.directory / 'dns.ps1'
        text = script.read_text(encoding='utf-8-sig').replace(" 'Apply' {", " 'Apply' {\n  Start-Sleep -Seconds 120")
        script.write_text(text, encoding='utf-8-sig')
        state['steps'][0]['sha256'] = hashlib.sha256(script.read_bytes()).hexdigest().upper()
        self.write_state(state)
        process = self.launch()
        self.wait_phase({'restored'})
        self.assertEqual(process.wait(timeout=10), 0)
        self.assertEqual(self.state()['started'], ['dns'])
        self.assertFalse((self.directory / 'child.json').exists())
        self.assertEqual((self.directory / 'dns.value').read_text(encoding='utf-8-sig').strip(), 'original')

    @unittest.skipUnless(os.name == 'nt', 'Windows scheduler object construction only')
    def test_native_scheduler_settings_need_neither_network_nor_ac_power(self):
        source = SOURCE.read_text(encoding='utf-8-sig')
        constructors = '\n'.join(line.strip() for line in source.splitlines()
                                 if line.strip().startswith(('$settings = New-ScheduledTaskSettingsSet',
                                                             '$timer = New-ScheduledTaskTrigger',
                                                             '$boot = New-ScheduledTaskTrigger')))
        probe = "$ErrorActionPreference='Stop'\n" + constructors + """
@{network=$settings.RunOnlyIfNetworkAvailable;battery=$settings.DisallowStartIfOnBatteries;stop=$settings.StopIfGoingOnBatteries;interval=$timer.Repetition.Interval;boot=$boot.CimClass.CimClassName} | ConvertTo-Json -Compress
"""
        result = subprocess.run([PS, '-NoProfile', '-Command', probe],
                                capture_output=True, text=True, encoding='utf-8', timeout=20)
        self.assertEqual(result.returncode, 0, result.stderr)
        state = json.loads(result.stdout.lstrip('\ufeff'))
        self.assertFalse(state['network'])
        self.assertFalse(state['battery'])
        self.assertFalse(state['stop'])
        self.assertEqual(state['interval'], 'PT1M')
        self.assertEqual(state['boot'], 'MSFT_TaskBootTrigger')
