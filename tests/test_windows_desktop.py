"""Native desktop orchestration with isolated OS boundaries, never host firewall writes."""
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import tempfile
import unittest
from unittest.mock import patch

from test_killswitch import k, u

ASSETS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/assets/killswitch'
PS = shutil.which('powershell.exe') or shutil.which('pwsh')


def quote(path):
    return "'" + str(path).replace("'", "''") + "'"


class WindowsRetirement(unittest.TestCase):
    def test_windows_python_and_browser_entries_reject_before_starting(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(k.platform, 'system', return_value='Windows'):
            with self.assertRaises(k.SwitchError):
                k.load_config(Path(tmp) / 'absent.json')
            with self.assertRaises(ValueError):
                u.desktop(None, Path(tmp) / 'launcher')
            with self.assertRaises(ValueError):
                u.serve(None, {})
            self.assertFalse((Path(tmp) / 'launcher').exists())


@unittest.skipUnless(PS, 'PowerShell native fixtures run in Windows CI')
class WindowsDesktop(unittest.TestCase):
    def run_ps(self, body):
        with tempfile.TemporaryDirectory() as tmp:
            script = Path(tmp) / 'fixture.ps1'
            script.write_text("$ErrorActionPreference='Stop'\n[Console]::OutputEncoding=[Text.Encoding]::UTF8\n" + body, encoding='utf-8-sig')
            result = subprocess.run([PS, '-NoProfile', '-File', str(script)], capture_output=True, text=True, encoding='utf-8', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.lstrip('\ufeff'))

    def test_confirmation_deadline_failure_and_restore_use_real_entry(self):
        body = '. ' + quote(ASSETS / 'windows-desktop.ps1') + '\n' + r'''
$cfg=@{target=[Environment]::MachineName;windows=@{mode='whole_machine'}}
function Read-DesktopConfig { return $cfg }
function Test-DesktopAdmin { return $true }
function Confirm-DesktopAction { if ($script:case -eq 'cancel-before') { throw 'cancel' } }
function Assert-DesktopAppsClosed { if ($script:case -eq 'running') { throw 'running' } }
function Read-Host { if ($script:case -eq 'cancel-keep') { return 'cancel' }; return 'KEEP' }
function Invoke-SwitchBackend($operation,$configPath) {
    $script:calls += $operation
    if ($script:case -eq 'preflight' -and $operation -eq 'On') { throw 'previous fuse' }
    if ($script:case -eq 'confirm-error' -and $operation -eq 'Confirm') { throw 'failed readback' }
    if ($operation -eq 'Off') { return @{protection='off';startup=$false} }
    $state=@{protection='on';startup=$true;coverage=@{status='pass'}}
    if ($operation -eq 'On' -and $script:case -ne 'already-on') {
        $state.keep_until=[DateTimeOffset]::UtcNow.ToUnixTimeSeconds()+180
        if ($script:case -eq 'expired') { $state.keep_until=1 }
    }
    if ($script:case -eq 'unknown' -and $operation -eq 'Confirm') { $state.coverage.status='unknown' }
    return $state
}
$results=@{}
foreach ($case in @('normal','already-on','expired','cancel-keep','confirm-error','unknown','preflight','cancel-before','off','running')) {
    $script:case=$case; $script:calls=@();$ok=$true
    try { Invoke-DesktopSwitch $(if ($case -in @('off','running')) {'Off'} else {'On'}) $PSCommandPath 6>$null } catch { $ok=$false }
    $results[$case]=@{ok=$ok;calls=@($script:calls)}
}
$results | ConvertTo-Json -Depth 6 -Compress
'''
        actual = self.run_ps(body)
        expected = {'normal': (True, ['On', 'Confirm']), 'already-on': (True, ['On']),
                    'expired': (False, ['On', 'Off']), 'cancel-keep': (False, ['On', 'Off']),
                    'confirm-error': (False, ['On', 'Confirm', 'Off']), 'unknown': (False, ['On', 'Confirm', 'Off']),
                    'preflight': (False, ['On']), 'cancel-before': (False, []), 'off': (True, ['Off']), 'running': (False, [])}
        for case, (ok, calls) in expected.items():
            self.assertEqual(actual[case], {'ok': ok, 'calls': calls}, case)

    def test_config_target_legacy_recovery_and_process_gate(self):
        body = '. ' + quote(ASSETS / 'windows-desktop.ps1') + '\n' + r'''
$path=Join-Path (Split-Path $PSCommandPath) 'config.json'
$cfg=@{version=1;target=[Environment]::MachineName;backend='windows_firewall';protected_processes=@('Claude.exe');windows=@{mode='whole_machine'}}
$results=@{}
foreach ($case in @('valid','target','legacy-on','legacy-off','empty-processes')) {
    $candidate=$cfg.Clone()
    if ($case -eq 'target') {$candidate.target='wrong-target'}
    if ($case -like 'legacy-*') {$candidate.windows=@{}}
    if ($case -eq 'empty-processes') {$candidate.protected_processes=@()}
    $candidate | ConvertTo-Json -Depth 5 | Set-Content -LiteralPath $path -Encoding UTF8
    try { $null=Read-DesktopConfig $path $(if ($case -eq 'legacy-off') {'Off'} else {'On'});$results[$case]=$true } catch {$results[$case]=$false}
}
function Get-Process { [pscustomobject]@{ProcessName='claude'} }
try { Assert-DesktopAppsClosed $cfg; $results.running=$false } catch { $results.running=$true }
try { Confirm-DesktopAction On $cfg; $results.redirected=$false } catch { $results.redirected=$true }
$results | ConvertTo-Json -Compress
'''
        self.assertEqual(self.run_ps(body), {'valid': True, 'target': False, 'legacy-on': False, 'legacy-off': True, 'empty-processes': False, 'running': True, 'redirected': True})

    def test_legacy_backend_cannot_enable_or_create_snapshot(self):
        body = r'''
$path=Join-Path (Split-Path $PSCommandPath) 'old.json'
@{version=1;target=[Environment]::MachineName;backend='windows_firewall';windows=@{}} | ConvertTo-Json | Set-Content $path
$results=@{}
foreach ($action in @('On','Confirm','Snapshot','Preview','Audit','Status')) {
    try { & BACKEND -Action $action -Config $path; $results[$action]=$false } catch { $results[$action]=$_.Exception.Message -like '*recovery-only*' }
}
$results | ConvertTo-Json -Compress
'''.replace('BACKEND', quote(ASSETS / 'windows-switch.ps1'))
        self.assertEqual(self.run_ps(body), {action: True for action in ('On','Confirm','Snapshot','Preview','Audit','Status')})

    def test_legacy_baseline_restores_without_application_conditions(self):
        source = (ASSETS / 'windows-switch.ps1').read_text(encoding='utf-8')
        functions = source[source.index('function Index-Unique'):source.index("if ($Action -notin")]
        body = functions + r'''
$state=Join-Path (Split-Path $PSCommandPath) 'old-baseline.json'
$cfg=@{target='fixture'}; $names=@('proxy','old-app'); $autoDisable=$false; $task='fixture'
$settings=@{enable_rules=@('proxy');disable_rules=@('old-app')}
$profiles=@('Domain','Private','Public' | ForEach-Object { @{Name=$_;Enabled=1;DefaultOutboundAction=2} })
@{target='fixture';profiles=$profiles;rules=@(@{Name='proxy';Enabled=2},@{Name='old-app';Enabled=1});names=@('old-app','proxy')} | ConvertTo-Json -Depth 5 | Set-Content $state
$script:rules=@([pscustomobject]@{Name='proxy';Enabled=1},[pscustomobject]@{Name='old-app';Enabled=2})
$script:removed=$false
function Get-NetFirewallProfile { param($PolicyStore) $profiles }
function Get-NetFirewallRule { param($PolicyStore) $script:rules }
function Set-NetFirewallRule { param($InputObject,$Enabled,$ThrottleLimit,[switch]$Confirm) foreach ($r in $InputObject) {$r.Enabled=$Enabled} }
function Get-ScheduledTask { param($TaskName,$ErrorAction) @{State='Ready'} }
function Unregister-ScheduledTask { param($TaskName,[switch]$Confirm) $script:removed=$true }
Restore-Baseline
@{rules=$script:rules;removed=$script:removed} | ConvertTo-Json -Depth 5 -Compress
'''
        self.assertEqual(self.run_ps(body), {'rules': [{'Name': 'proxy', 'Enabled': 2}, {'Name': 'old-app', 'Enabled': 1}], 'removed': True})

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell child process')
    def test_native_backend_transport_unicode_paths_errors_and_invalid_json(self):
        with tempfile.TemporaryDirectory(prefix="guardian ' 中文 ") as tmp:
            path = Path(tmp)
            shutil.copyfile(ASSETS / 'windows-desktop.ps1', path / 'windows-desktop.ps1')
            config = path / '配置.json'
            config.write_text('{}', encoding='utf-8')
            (path / 'windows-switch.ps1').write_text(r'''
param($Action,$Config)
[Console]::OutputEncoding=New-Object Text.UTF8Encoding($false)
if ($Action -eq 'On') { @{path=$Config;exists=(Test-Path -LiteralPath $Config);message='中文回执'} | ConvertTo-Json -Compress }
elseif ($Action -eq 'Confirm') { Write-Error 'fixture backend failure'; exit 4 }
else { 'invalid json' }
''', encoding='utf-8-sig')
            body = '. ' + quote(path / 'windows-desktop.ps1') + '\n$configPath=' + quote(config) + '\n' + r'''
$result=@{success=(Invoke-SwitchBackend On $configPath)}
try { $null=Invoke-SwitchBackend Confirm $configPath; $result.failed=$false } catch { $result.failed=$_.Exception.Message -like '*fixture backend failure*' }
try { $null=Invoke-SwitchBackend Off $configPath; $result.invalid=$false } catch { $result.invalid=$true }
$result | ConvertTo-Json -Depth 5 -Compress
'''
            self.assertEqual(self.run_ps(body), {'success': {'path': str(config), 'exists': True, 'message': '中文回执'}, 'failed': True, 'invalid': True})

    @unittest.skipUnless(os.name == 'nt', 'Windows PowerShell elevation boundary')
    def test_elevation_waits_for_real_child_and_preserves_failure(self):
        body = '. ' + quote(ASSETS / 'windows-desktop.ps1') + '\n' + r'''
function Read-DesktopConfig { @{target=[Environment]::MachineName} }
function Test-DesktopAdmin { $false }
function Confirm-DesktopAction { throw 'must run in elevated child' }
$childPath=Join-Path (Split-Path $PSCommandPath) 'child.ps1'
'param([int]$Code); Start-Sleep -Milliseconds 100; exit $Code' | Set-Content $childPath
function Start-Process {
    param($FilePath,$Verb,$ArgumentList,[switch]$PassThru,$ErrorAction)
    if ($Verb -ne 'RunAs' -or $ArgumentList -notlike '*-Action On -Config*') { throw 'invalid elevation request' }
    if ($script:case -eq 'cancel') { throw 'user canceled elevation' }
    Microsoft.PowerShell.Management\Start-Process -FilePath $FilePath -ArgumentList ('-NoProfile -File "' + $childPath + '" -Code ' + $script:case) -PassThru
}
$result=@{}
foreach ($case in @('0','9','cancel')) {
    $script:case=$case
    try { Invoke-DesktopSwitch On $PSCommandPath; $result[$case]=$true } catch { $result[$case]=$false }
}
$result | ConvertTo-Json -Compress
'''
        self.assertEqual(self.run_ps(body), {'0': True, '9': False, 'cancel': False})

    @unittest.skipUnless(os.name == 'nt', 'Windows Shell shortcut API')
    def test_shortcuts_use_powershell_existing_icon_and_exact_paths(self):
        with tempfile.TemporaryDirectory(prefix="guardian ' 中文 ") as tmp:
            path = Path(tmp)
            config = path / '配置.json'
            config.write_text(json.dumps({'version': 1, 'target': os.environ['COMPUTERNAME'], 'backend':'windows_firewall', 'protected_processes':['Claude'], 'windows':{'mode':'whole_machine'}}), encoding='utf-8-sig')
            installed = path / '技能目录'
            installed.mkdir()
            for name in ('windows-shortcuts.ps1', 'windows-desktop.ps1', 'windows-switch.ps1', 'icon.ico'):
                shutil.copyfile(ASSETS / name, installed / name)
            output = path / '桌面入口'
            output.mkdir()
            unrelated = output / '保留.txt'
            unrelated.write_text('keep', encoding='utf-8')
            body = '& ' + quote(installed / 'windows-shortcuts.ps1') + ' -Config ' + quote(config) + ' -OutputDirectory ' + quote(output) + ' | Out-Null\n'
            body += "$shell=New-Object -ComObject Shell.Application\n$folder=$shell.NameSpace(" + quote(output) + ")\n$links=@(Get-ChildItem -LiteralPath " + quote(output) + " -Filter '*.lnk' | ForEach-Object {$l=$folder.ParseName($_.Name).GetLink;$icon='';$index=$l.GetIconLocation([ref]$icon);@{name=$_.Name;target=$l.Path;args=$l.Arguments;icon=($icon+','+$index);directory=$l.WorkingDirectory}})\n"
            body += "$rejected=$false;try { & " + quote(installed/'windows-shortcuts.ps1') + ' -Config ' + quote(config) + ' -OutputDirectory ' + quote(output) + " | Out-Null } catch {$rejected=$true}\n@{links=$links;overwriteRejected=$rejected}|ConvertTo-Json -Depth 5 -Compress"
            result = self.run_ps(body)
            self.assertEqual(unrelated.read_text(encoding='utf-8'), 'keep')
            self.assertTrue(result['overwriteRejected'])
            self.assertEqual(len(result['links']), 2)
            self.assertEqual({link['name'] for link in result['links']}, {'开启保护（限制直连）.lnk', '关闭保护（恢复联网）.lnk'})
            for link in result['links']:
                self.assertEqual(Path(link['target']).name.lower(), 'powershell.exe')
                for argument, expected in (('File', installed / 'windows-desktop.ps1'), ('Config', config)):
                    match = re.search(r'-' + argument + r' "([^"]+)"', link['args'])
                    self.assertIsNotNone(match, link['args'])
                    self.assertTrue(Path(match.group(1)).samefile(expected))
                self.assertIn('-ExecutionPolicy Bypass', link['args'])
                icon_path, icon_index = link['icon'].rsplit(',', 1)
                self.assertEqual(icon_index, '0')
                self.assertTrue(Path(icon_path).samefile(installed / 'icon.ico'))
                self.assertTrue(Path(link['directory']).samefile(installed))
            self.assertEqual(sum('-Action On ' in link['args'] for link in result['links']), 1)
            self.assertEqual(sum('-Action Off ' in link['args'] for link in result['links']), 1)
