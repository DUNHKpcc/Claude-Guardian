"""Run shipped PowerShell with OS-boundary fixtures; never call host firewall APIs."""
import json
from pathlib import Path
import shutil
import subprocess
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/claude-guardian'
PS = shutil.which('powershell.exe') or shutil.which('pwsh')


class SwitchCoveragePresentation(unittest.TestCase):
    @unittest.skipUnless(shutil.which('node'), 'Node unavailable')
    def test_real_renderer_does_not_show_unknown_or_failed_coverage_as_verified(self):
        script = (SKILL / 'assets/killswitch/switch.js').read_text(encoding='utf-8')
        fixture = """
const assert = require('node:assert/strict');
const elements = new Map();
const document = {
  getElementById(id) { if (!elements.has(id)) elements.set(id, {classList:{toggle(){}},textContent:''}); return elements.get(id); },
  querySelector() { return {classList:{toggle(){}}}; }
};
const fetch = () => new Promise(() => {});
"""
        assertions = """
for (const status of ['unknown','fail']) {
  render({protection:'on',startup:true,coverage:{status},checked_at:1});
  assert.notEqual(elements.get('symbol').textContent, '✓');
  assert.notEqual(elements.get('title').textContent, '保护已开启');
  assert.equal(elements.get('coverage-row').hidden, false);
  assert.equal(elements.get('coverage').textContent, status === 'fail' ? '失败，暂停使用' : '待核实');
}
render({protection:'on',startup:true,coverage:{status:'fail'},stale:true});
assert.equal(elements.get('coverage').textContent,'需要刷新');
"""
        result = subprocess.run(['node', '-e', fixture + script + assertions], capture_output=True, text=True, encoding='utf-8', timeout=10)
        self.assertEqual(result.returncode, 0, result.stderr)


@unittest.skipUnless(PS, 'PowerShell unavailable; native fixtures run in CI')
class WindowsUpdateCoverage(unittest.TestCase):
    def run_ps(self, body):
        with tempfile.TemporaryDirectory() as directory:
            script = Path(directory) / 'fixture.ps1'
            script.write_text("$ErrorActionPreference='Stop'\n" + body, encoding='utf-8-sig')
            result = subprocess.run([PS, '-NoProfile', '-File', str(script)], capture_output=True,
                                    text=True, encoding='utf-8', errors='replace', timeout=30)
        self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
        return json.loads(result.stdout.lstrip('\ufeff'))

    def test_real_coverage_functions_reject_missing_paths_and_condition_drift(self):
        source = (SKILL / 'assets/killswitch/windows-switch.ps1').read_text(encoding='utf-8')
        functions = source[source.index('function Get-RuleConditions'):source.index('function Get-Snapshot')]
        fixture = r'''
$settings = @{enable_rules=@('guardian-test')}
$script:mode = 'normal'
function Get-NetFirewallRule { param($PolicyStore,$Name)
    [pscustomobject]@{Name=$Name;Store=$PolicyStore;Direction='Outbound';Action='Block';Profile='Any'}
}
function Get-NetFirewallApplicationFilter { process {
    if ($script:mode -eq 'denied') { throw 'AccessDenied' }
    $program = if ($script:mode -eq 'missing') {'missing.exe'} else {$PSCommandPath}
    if ($script:mode -eq 'program-drift' -and $_.Store -eq 'ActiveStore') { $program = 'changed.exe' }
    [pscustomobject]@{Program=$program;Package='Any'}
} }
function Get-NetFirewallServiceFilter { process {
    $service = if ($script:mode -eq 'service-drift' -and $_.Store -eq 'ActiveStore') {'changed'} else {'Any'}
    [pscustomobject]@{Service=$service}
} }
function Get-NetFirewallInterfaceFilter { process {
    $alias = if ($script:mode -eq 'interface-drift' -and $_.Store -eq 'ActiveStore') {'changed'} else {'Any'}
    [pscustomobject]@{InterfaceAlias=@($alias)}
} }
function Get-NetFirewallInterfaceTypeFilter { process { [pscustomobject]@{InterfaceType='Any'} } }
$baseline = @{rules=@(@{Name='guardian-test';conditions=(Get-RuleConditions (Get-NetFirewallRule -PolicyStore PersistentStore -Name 'guardian-test'))})}
$results = @{}
foreach ($mode in @('normal','missing','program-drift','service-drift','interface-drift','denied')) {
    $script:mode=$mode
    $results[$mode]=(Get-Coverage $baseline).status
}
$script:mode='normal'
$baseline.rules[0].conditions.Service='old-service'
$results['baseline-drift']=(Get-Coverage $baseline).status
$results['legacy-baseline']=(Get-Coverage @{rules=@(@{Name='guardian-test'})}).status
# Existing paths cannot prove that a new package helper or external runtime is covered.
$results['new-component-unverified']=(Get-Coverage @{rules=@()}).status
$results | ConvertTo-Json -Compress
'''
        actual = self.run_ps(functions + fixture)
        for scenario in ('missing', 'program-drift', 'service-drift', 'interface-drift', 'baseline-drift'):
            self.assertEqual(actual[scenario], 'fail', scenario)
        for scenario in ('normal', 'denied', 'legacy-baseline', 'new-component-unverified'):
            self.assertEqual(actual[scenario], 'unknown', scenario)

    def test_source_deployment_failure_preserves_old_rules_and_never_prints_success(self):
        source = (SKILL / 'sources/S05-local-protection.md').read_text(encoding='utf-8')
        code = source.split('### 步骤 4', 1)[1].split('```powershell\n', 1)[1].split('```', 1)[0]
        # Fixtures replace only native commands; the actual distributed code is executed.
        fixture = r'''
$script:fixtureRules = @{'old-protection'=@{Name='old-protection'}}
$script:removed=@(); $script:printed=@(); $script:calls=0
function Get-AppxPackage { param($Name) [pscustomobject]@{InstallLocation='fixture'} }
function Get-ChildItem { param($LiteralPath,[switch]$Recurse,$Filter,[switch]$File)
    [pscustomobject]@{FullName='fixture/app/one.exe'}
    [pscustomobject]@{FullName='fixture/app/two.exe'}
}
function New-NetFirewallRule { [CmdletBinding()]param($PolicyStore,$Name,$DisplayName,$Enabled,$Profile,$Direction,$Action,$Program,$InterfaceAlias,$Protocol,$RemoteAddress)
    $script:calls++
    if ($script:calls -eq FAIL_AT) { Write-Error 'Windows System Error 5'; return }
    $script:fixtureRules[$Name]=[pscustomobject]@{Name=$Name;Enabled=$Enabled;Profile=$Profile;Direction=$Direction;Action=$Action;Program=$Program;RemoteAddress=$RemoteAddress}
}
function Get-NetFirewallRule { [CmdletBinding()]param($PolicyStore,$Name)
    $rule = $script:fixtureRules[$Name]
    if ('MODE' -eq 'mismatch' -and $PolicyStore -eq 'ActiveStore') { $rule.Program='old-version.exe' }
    return $rule
}
function Get-NetFirewallApplicationFilter { [CmdletBinding()]param([Parameter(ValueFromPipeline=$true)]$Rule) process { [pscustomobject]@{Program=$Rule.Program;Package='Any'} } }
function Get-NetFirewallInterfaceFilter { [CmdletBinding()]param([Parameter(ValueFromPipeline=$true)]$Rule) process { [pscustomobject]@{InterfaceAlias='Any'} } }
function Get-NetFirewallAddressFilter { [CmdletBinding()]param([Parameter(ValueFromPipeline=$true)]$Rule) process { [pscustomobject]@{LocalAddress='Any';RemoteAddress=$Rule.RemoteAddress} } }
function Get-NetFirewallServiceFilter { [CmdletBinding()]param([Parameter(ValueFromPipeline=$true)]$Rule) process { [pscustomobject]@{Service='Any'} } }
function Get-NetFirewallPortFilter { [CmdletBinding()]param([Parameter(ValueFromPipeline=$true)]$Rule) process { [pscustomobject]@{Protocol='Any';LocalPort='Any';RemotePort='Any'} } }
function Remove-NetFirewallRule { [CmdletBinding()]param($PolicyStore,$Name)
    $script:removed += $Name
    $script:fixtureRules.Remove($Name)
}
function Write-Host { param($Object) $script:printed += $Object }
$failed=$false
try {
$ErrorActionPreference='Continue'
CODE
} catch { $failed=$true }
@{failed=$failed;oldRetained=$script:fixtureRules.ContainsKey('old-protection');remaining=$script:fixtureRules.Count;removed=@($script:removed);printed=@($script:printed);calls=$script:calls} | ConvertTo-Json -Compress
'''
        for mode, fail_at in [('first', 1), ('nth', 3), ('mismatch', 0), ('success', 0)]:
            with self.subTest(mode=mode):
                actual = self.run_ps(fixture.replace('FAIL_AT', str(fail_at)).replace('MODE', mode).replace('CODE', code))
                self.assertTrue(actual['oldRetained'])
                self.assertNotIn('old-protection', actual['removed'])
                if mode == 'success':
                    self.assertFalse(actual['failed'])
                    self.assertEqual(actual['remaining'], 5)
                    self.assertEqual(actual['removed'], [])
                    self.assertIn('NOT verified', actual['printed'][0])
                else:
                    self.assertTrue(actual['failed'])
                    self.assertEqual(actual['printed'], [])
                    self.assertEqual(actual['remaining'], 1)


if __name__ == '__main__':
    unittest.main()
