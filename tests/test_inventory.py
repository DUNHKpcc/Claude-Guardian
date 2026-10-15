"""Synthetic-only platform fixtures; no Apple or Windows process is launched."""
import argparse
import importlib.util
import json
import subprocess
from pathlib import Path
import unittest
from unittest.mock import patch, Mock

SPEC = importlib.util.spec_from_file_location('inventory_guardian', Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/guardian.py')
g = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(g)

MAC_PROXY = '''<dictionary> {
  HTTPEnable : 1
  HTTPProxy : secret-user:secret-password@private.example
  HTTPPort : 7890
  HTTPSEnable : 0
  ProxyAutoConfigEnable : 1
  ProxyAutoConfigURLString : https://private.example/secret-token
  __SCOPED__ : <dictionary> {
    en0 : <dictionary> {
      HTTPEnable : 0
      SOCKSEnable : 1
    }
  }
}'''

class InventoryTests(unittest.TestCase):
    def test_mac_projection_and_scoped_not_flattened(self):
        output = g.proxy_summary(MAC_PROXY)
        self.assertIn('http=enabled', output)
        self.assertIn('socks=unknown', output)
        self.assertIn('scoped=present', output)
        self.assertNotIn('secret', output)
        self.assertNotIn('private', output)
        self.assertNotIn('7890', output)

    def test_mac_all_synthetic_fields(self):
        values = {'mac-version': '15.2.1', 'mac-build': '24C101', 'mac-locale': 'zh_CN', 'mac-languages': '(\n "zh-Hans-CN",\n en-US\n)', 'mac-proxy': MAC_PROXY}
        with patch.object(g.os, 'readlink', return_value='/var/db/timezone/zoneinfo/Asia/Shanghai'):
            facts, errors = g.extended_inventory('macos', values.__getitem__)
        self.assertEqual(errors, [])
        data = {f: v for f, v, _ in facts}
        self.assertEqual(data['S02'], 'macOS-product-15.2.1;build-24C101')
        self.assertEqual(data['S08'], 'IANA:Asia:Shanghai')
        self.assertEqual(data['S06'], 'zh-Hans-CN,en-US')
        self.assertEqual(len(data), 5)

    def test_windows_all_synthetic_fields(self):
        values = {'windows-system': json.dumps({'version':'10.0.26100', 'build':'26100', 'sku':100, 'ui':'zh-CN', 'timezone':'China Standard Time'}), 'windows-proxy': json.dumps({'enabled': 1, 'pac': True, 'ignored_secret':'secret-marker'})}
        facts, errors = g.extended_inventory('windows', values.__getitem__)
        self.assertEqual(errors, [])
        data = {f:v for f,v,_ in facts}
        self.assertEqual(data['S03'], 100)
        self.assertEqual(data['S08'], 'Windows:China Standard Time')
        self.assertEqual(data['P06'], 'user_proxy=enabled;pac_url=present;winhttp=not_collected')
        self.assertNotIn('secret-marker', str(facts))

    def test_unknown_is_not_false(self):
        facts, errors = g.extended_inventory('windows', lambda _: '{"enabled":null,"pac":false}')
        self.assertTrue(errors)
        self.assertEqual(facts[0][1], 'user_proxy=unknown;pac_url=absent;winhttp=not_collected')

    def test_failures_and_oversize_do_not_echo(self):
        def fail(_):
            raise g.GuardianError('PERMISSION_DENIED')
        facts, errors = g.extended_inventory('windows', fail)
        self.assertEqual(facts, [])
        self.assertEqual(len(errors), 2)
        facts, errors = g.extended_inventory('windows', lambda _: 'secret' * 65536)
        self.assertEqual(facts, [])
        self.assertEqual(errors[0][1], 'BUDGET_EXCEEDED')

    def test_invalid_proxy_and_locale_fail_closed(self):
        for raw in ('garbage secret', '<dictionary> {\n HTTPEnable : 1\n HTTPEnable : 0\n}', '<dictionary> {\n'):
            with self.assertRaises(g.GuardianError):
                g.proxy_summary(raw)
        values = {'mac-version':'SECRET', 'mac-build':'SECRET', 'mac-locale':'secret@example.com', 'mac-languages':'(secret@example.com)', 'mac-proxy':MAC_PROXY}
        with patch.object(g.os, 'readlink', return_value='/home/private/secret'):
            facts, errors = g.extended_inventory('macos', values.__getitem__)
        self.assertEqual([f for f,_,_ in facts], ['P06'])
        self.assertEqual(len(errors), 5)
        self.assertNotIn('secret@example.com', str(errors))

    def test_no_foreign_commands_or_dynamic_id(self):
        with patch.object(g.sys, 'platform', 'linux'), patch('subprocess.Popen') as popen:
            for collector in list(g.MAC_COMMANDS) + ['windows-system', 'windows-proxy', 'echo secret']:
                with self.assertRaises(g.GuardianError):
                    g.run_fixed(collector)
            popen.assert_not_called()

    def test_fixed_commands_have_no_shell_profile_or_environment_hooks(self):
        with patch.object(g.sys, 'platform', 'darwin'):
            for collector in g.MAC_COMMANDS:
                argv, env = g.fixed_command(collector)
                self.assertTrue(argv[0].startswith('/usr/'))
                self.assertNotIn('HOME', env)
                self.assertNotIn('BASH_ENV', env)
                self.assertNotIn('HTTP_PROXY', env)
        for script in (g.WINDOWS_SYSTEM_QUERY, g.WINDOWS_PROXY_QUERY):
            for forbidden in ('Invoke-Expression', 'Invoke-WebRequest', 'ExecutionPolicy', 'Get-ChildItem'):
                self.assertNotIn(forbidden, script)

    @patch.object(g, '_fixed_pipe_ready', return_value=True)
    def test_bounded_runner_mocked_io(self, _ready):
        process = Mock(returncode=0)
        process.stdout.fileno.return_value = 17
        with patch.object(g, 'fixed_command', return_value=(('/usr/bin/sw_vers','-productVersion'), {'LC_ALL':'C'})), patch('subprocess.Popen', return_value=process) as launch, patch.object(g.os, 'read', side_effect=[b'15.2\n', b'']):
            self.assertEqual(g.run_fixed('mac-version'), '15.2')
            self.assertFalse(launch.call_args.kwargs['shell'])
            process.wait.assert_called_once_with(timeout=5)
        process = Mock(returncode=-9)
        process.stdout.fileno.return_value = 17
        with patch.object(g, 'fixed_command', return_value=(('/usr/bin/sw_vers',), {})), patch('subprocess.Popen', return_value=process), patch.object(g.os, 'read', return_value=b'x'*4096):
            with self.assertRaisesRegex(g.GuardianError, 'BUDGET_EXCEEDED'):
                g.run_fixed('mac-version')
            process.kill.assert_called_once()

    @patch.object(g, '_fixed_pipe_ready', return_value=True)
    def test_process_failures_never_echo_raw_output(self, _ready):
        for returncode, chunks, expected in [(1, [b"secret-password", b""], "OS_QUERY_FAILED"), (0, [b"\xff", b""], "INPUT_OR_RESPONSE_INVALID")]:
            process = Mock(returncode=returncode)
            process.stdout.fileno.return_value = 17
            with patch.object(g, 'fixed_command', return_value=(('/usr/bin/sw_vers',), {})), patch('subprocess.Popen', return_value=process), patch.object(g.os, 'read', side_effect=chunks):
                with self.assertRaisesRegex(g.GuardianError, '^' + expected + '$'):
                    g.run_fixed('mac-version')
        with patch.object(g, 'fixed_command', return_value=(('/usr/bin/sw_vers',), {})), patch('subprocess.Popen', side_effect=PermissionError('secret-path')):
            with self.assertRaisesRegex(g.GuardianError, 'PERMISSION_DENIED'):
                g.run_fixed('mac-version')

    @patch.object(g, '_fixed_pipe_ready', return_value=True)
    def test_timeout_suppresses_command_output(self, _ready):
        process = Mock(returncode=-9)
        process.wait.side_effect = [subprocess.TimeoutExpired('secret', 5), None]
        with patch.object(g, 'fixed_command', return_value=(('/usr/bin/sw_vers',), {})), patch('subprocess.Popen', return_value=process), patch.object(g.os, 'read', return_value=b''):
            with self.assertRaisesRegex(g.GuardianError, '^BUDGET_EXCEEDED$'):
                g.run_fixed('mac-version')
            process.kill.assert_called_once()

    def test_expanded_native_handoff_keeps_gate_closed(self):
        args = argparse.Namespace(target_ref='device-1', confirm_target=True, authorize_audit=True, target_os='macos', target_kind='local', namespace='desktop', execution_location='native_local', user_context='same')
        extra = [('S02','macOS-product-15.2;build-24C101','mac-version'), ('S08','IANA:Asia:Shanghai','mac-timezone-link'), ('P06',g.proxy_summary(MAC_PROXY),'mac-proxy')]
        with patch.object(g.sys, 'platform','darwin'), patch.object(g, 'extended_inventory', return_value=(extra, [])), patch.object(g.os, 'uname', return_value=type('Uname', (), {'release':'fixture-kernel'})(), create=True):
            report = g.native_check(args)
        output = g.analyze(report, 'device-1', True)
        self.assertEqual(output['contact_control']['gate_state'], 'closed')
        self.assertEqual(output['changes'], [])
        self.assertEqual(output['plan']['diff'], [])
        self.assertEqual(report['limits']['native_platform_validation'], 'not_run')
        self.assertIn('IANA:Asia:Shanghai', json.dumps(g.redact(report)))

    def test_no_collectors_before_binding_and_authorization(self):
        args = argparse.Namespace(target_ref='device-1', confirm_target=True, authorize_audit=False, target_os='macos')
        with patch.object(g, 'extended_inventory') as collector:
            with self.assertRaisesRegex(g.GuardianError, 'AUTHORIZATION_MISSING'):
                g.native_check(args)
            collector.assert_not_called()

if __name__ == '__main__':
    unittest.main()
