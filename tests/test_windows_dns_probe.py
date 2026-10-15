"""Offline contracts and owned synthetic processes; never issue DNS queries."""
import base64
import importlib
import json
import os
import tempfile
from pathlib import Path
import subprocess
import sys
import threading
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import windows_dns_probe as m


def scope(**kwargs):
    values = dict(binding=m.Binding('device', 'user', 'namespace', 'win32',
        r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
        r'C:\Windows\System32\WindowsPowerShell\v1.0\Modules\DnsClient\DnsClient.psd1',
        r'C:\trusted', r'C:\Windows'), name='reserved.test', query_type='A')
    values.update(kwargs)
    return m.QueryScope(**values)


class GateTests(unittest.TestCase):
    def probe(self, selected=None, raw=b'["192.0.2.1"]', **kw):
        kw.setdefault('verify_binding', lambda _: True)
        kw.setdefault('verify_runtime', lambda _: True)
        kw.setdefault('approve_query', lambda *_: True)
        with patch.object(m.sys, 'platform', 'win32'), patch.object(m, '_run_child', return_value=raw) as runner:
            result = m.probe_windows_dns(selected or scope(), **kw)
        return result, runner

    def test_no_import_io(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError()), patch('subprocess.Popen', side_effect=AssertionError()):
            importlib.reload(m)

    def test_exact_approval_and_fresh_binding(self):
        calls = []
        selected = scope()
        def verify(b):
            self.assertIs(b, selected.binding)
            calls.append('binding')
            return True
        def runtime(b):
            calls.append('runtime')
            return True
        def approve(s, budget):
            self.assertIs(s, selected)
            self.assertEqual(s.absolute_name, 'reserved.test.')
            self.assertIn('disclose', s.network_effect)
            calls.append('approve')
            return True
        result, runner = self.probe(selected, verify_binding=verify, verify_runtime=runtime, approve_query=approve)
        self.assertEqual(calls, ['binding', 'runtime', 'approve', 'binding', 'runtime', 'binding', 'runtime'])
        self.assertEqual(json.loads(runner.call_args.args[1]), dict(name='reserved.test.', kind='A', module=selected.binding.dnsclient_module))
        self.assertEqual(result['execution_status'], 'completed')

    def test_denied_callbacks_and_nonboolean(self):
        for key, code in [('verify_binding', 'TARGET_NOT_BOUND'), ('verify_runtime', 'RUNTIME_NOT_TRUSTED'), ('approve_query', 'AUTHORIZATION_MISSING')]:
            for value in (False, None, 1, 'yes'):
                result, runner = self.probe(**{key: lambda *_, value=value: value})
                self.assertEqual(result['error_code'], code)
                runner.assert_not_called()

    def test_binding_revocation_before_spawn(self):
        n = iter((True, False))
        result, runner = self.probe(verify_binding=lambda _: next(n))
        self.assertEqual(result['error_code'], 'TARGET_NOT_BOUND')
        runner.assert_not_called()

    def test_binding_revocation_after_spawn_discards_facts(self):
        n = iter((True, True, False))
        result, _ = self.probe(verify_binding=lambda _: next(n))
        self.assertEqual(result['facts'], [])
        self.assertEqual(result['error_code'], 'TARGET_NOT_BOUND')

    def test_platform_closed(self):
        with patch.object(m.sys, 'platform', 'linux'), patch.object(m, '_run_child') as runner:
            result = m.probe_windows_dns(scope(), verify_binding=lambda _: True, verify_runtime=lambda _: True, approve_query=lambda *_: True)
        self.assertEqual(result['error_code'], 'UNSUPPORTED_PLATFORM')
        runner.assert_not_called()

    def test_bad_names_and_types(self):
        for name in ('api.anthropic.com', 'claude.ai', 'x.claude.test', 'Anthropic.com', 'a;ls.test', 'x.test.', 'a', '127.0.0.1', '*.test', 'x..test', 'a.'+'x'*64):
            result, runner = self.probe(scope(name=name))
            self.assertIn(result['error_code'], ('INPUT_INVALID', 'PC0_TARGET_FORBIDDEN'))
            runner.assert_not_called()
        for kind in ('TXT', 'A_AAAA', '', None):
            result, runner = self.probe(scope(query_type=kind))
            self.assertEqual(result['error_code'], 'INPUT_INVALID')
            runner.assert_not_called()

    def test_bad_paths_and_budget(self):
        from dataclasses import replace
        for path in ('powershell.exe', r'\\server\share\powershell.exe', r'C:\x\..\powershell.exe', r'C:\x:ads\powershell.exe'):
            result, runner = self.probe(scope(binding=replace(scope().binding, powershell_executable=path)))
            self.assertEqual(result['error_code'], 'INPUT_INVALID')
            runner.assert_not_called()
        for value in (False, float('nan'), float('inf'), 0, 16):
            result, runner = self.probe(budget=m.Budget(value))
            self.assertEqual(result['error_code'], 'INPUT_INVALID')
            runner.assert_not_called()

    def test_cancel_and_callback_errors_are_private(self):
        result, runner = self.probe(cancelled=lambda: True)
        self.assertEqual(result['error_code'], 'CANCELLED')
        runner.assert_not_called()
        def explode(*_):
            raise RuntimeError('PRIVATE_SECRET')
        result, _ = self.probe(approve_query=explode)
        self.assertNotIn('PRIVATE_SECRET', json.dumps(result))
        self.assertEqual(result['facts'], [])

    def test_projection_and_privacy(self):
        result, _ = self.probe(raw=b'["1.1.1.1","192.0.2.1","127.0.0.1"]')
        value = result['facts'][0]['value']
        self.assertEqual(value['address_class_counts'], dict(globally_routable=1, non_global=2))
        self.assertEqual(value['actual_server'], 'unknown')
        self.assertIsNone(value['dns_rcode'])
        self.assertFalse(value['dns_packet_observed'])
        text = json.dumps(result)
        for private in ('reserved.test', '192.0.2.1', 'C:\\', 'namespace'):
            self.assertNotIn(private, text)
        self.assertEqual(result['gate_state'], 'closed')
        result, _ = self.probe(scope(query_type='AAAA'), raw=b'["2001:db8::1"]')
        self.assertEqual(result['facts'][0]['value']['address_family'], 'IPv6')
        result, _ = self.probe(raw=b'[]')
        self.assertEqual(result['facts'][0]['value']['address_count'], 0)

    def test_bad_outputs(self):
        for raw in (b'{}', b'null', b'[1]', b'["::1"]', b'["1.1.1.1","1.1.1.1"]', b'["fe80::1%3"]', b'PRIVATE_SECRET', b'['+b' '*m.MAX_OUTPUT+b']'):
            result, _ = self.probe(raw=raw)
            self.assertIn(result['error_code'], ('OUTPUT_INVALID', 'OUTPUT_LIMIT'))
            self.assertEqual(result['facts'], [])

    def test_fixed_command_no_query_in_argv(self):
        with patch.object(m, '_run_process', return_value=b'[]') as runner:
            m._run_child(scope().binding, b'{"private":"sentinel"}', time.monotonic()+5, lambda: False)
        argv = runner.call_args.args[0]
        self.assertIn('-NoProfile', argv)
        self.assertIn('-NonInteractive', argv)
        self.assertNotIn('sentinel', str(argv))
        script = base64.b64decode(argv[-1]).decode('utf-16-le')
        self.assertEqual(script, m._SCRIPT)
        self.assertIn('DnsClient\\Resolve-DnsName -Name $request.name -Type $request.kind -DnsOnly', script)
        for forbidden in ('-ExecutionPolicy', '-Server ', '-LlmnrFallback', '-NetbiosFallback', 'Invoke-Expression', 'getaddrinfo', 'Clear-DnsClientCache'):
            self.assertNotIn(forbidden, script + str(argv))
        self.assertEqual(runner.call_args.kwargs['env']['PSModulePath'], '')


class OwnedProcessTests(unittest.TestCase):
    def run_child(self, code, timeout=2, cancelled=lambda: False):
        return m._run_process([sys.executable, '-I', '-S', '-c', code], b'private',
            time.monotonic()+timeout, cancelled, cwd=str(Path.cwd()), env={})

    def test_owned_success_and_reaped(self):
        raw = self.run_child('import sys; assert sys.stdin.buffer.read()==b"private"; print("[]",end="")')
        self.assertEqual(raw, b'[]')

    def test_stdout_stderr_limits(self):
        for stream in ('stdout', 'stderr'):
            with self.assertRaisesRegex(m.ProbeError, '^OUTPUT_LIMIT$'):
                self.run_child('import sys,time; sys.'+stream+'.buffer.write(b"x"*100000); sys.'+stream+'.flush(); time.sleep(2)')

    def test_timeout_and_cancel_reap(self):
        for cancel in (False, True):
            start = time.monotonic()
            callback = (lambda: time.monotonic()-start > .08) if cancel else (lambda: False)
            with self.assertRaisesRegex(m.ProbeError, '^CANCELLED$' if cancel else '^TIMEOUT$'):
                self.run_child('import time; time.sleep(10)', timeout=.15, cancelled=callback)
            self.assertLess(time.monotonic()-start, 1.5)

    def test_cancel_closes_handles_and_reaps_owned_pid(self):
        original = subprocess.Popen
        children = []
        def spawn(*args, **kwargs):
            child = original(*args, **kwargs)
            children.append(child)
            return child
        start = time.monotonic()
        with patch.object(m.subprocess, 'Popen', side_effect=spawn):
            with self.assertRaisesRegex(m.ProbeError, '^CANCELLED$'):
                self.run_child('import time; time.sleep(10)',
                    cancelled=lambda: time.monotonic() - start > .08)
        self.assertEqual(len(children), 1)
        self.assertIsNotNone(children[0].returncode)
        self.assertTrue(all(stream.closed for stream in
            (children[0].stdin, children[0].stdout, children[0].stderr)))

    def test_thread_start_failure_reaps_and_closes_child(self):
        original_spawn = subprocess.Popen
        original_start = threading.Thread.start
        for fail_at in (1, 2, 3):
            children = []
            calls = []
            def spawn(*args, **kwargs):
                child = original_spawn(*args, **kwargs)
                children.append(child)
                return child
            def start(thread):
                calls.append(thread)
                if len(calls) == fail_at:
                    raise RuntimeError('PRIVATE_THREAD_FAILURE')
                return original_start(thread)
            with patch.object(m.subprocess, 'Popen', side_effect=spawn), patch.object(m.threading.Thread, 'start', start):
                with self.assertRaisesRegex(m.ProbeError, '^PROCESS_FAILED$'):
                    self.run_child('import time; time.sleep(10)')
            self.assertIsNotNone(children[0].returncode)
            self.assertTrue(all(stream.closed for stream in
                (children[0].stdin, children[0].stdout, children[0].stderr)))
            self.assertTrue(all(not t.is_alive() for t in calls))

    def test_wait_failure_is_cleanup_failure_not_success(self):
        original_spawn = subprocess.Popen
        children = []
        def spawn(*args, **kwargs):
            child = original_spawn(*args, **kwargs)
            children.append(child)
            original_wait = child.wait
            def wait(timeout=None):
                # Reap the real owned child first; inject only the reported error.
                original_wait(timeout=timeout)
                raise subprocess.TimeoutExpired('private', timeout)
            child.wait = wait
            return child
        with patch.object(m.subprocess, 'Popen', side_effect=spawn):
            with self.assertRaisesRegex(m.ProbeError, '^CLEANUP_FAILED$'):
                self.run_child('import sys; sys.stdin.buffer.read(); print("[]")')
        self.assertIsNotNone(children[0].returncode)
        self.assertTrue(all(stream.closed for stream in
            (children[0].stdin, children[0].stdout, children[0].stderr)))

    def test_worker_join_bound_and_liveness_failure(self):
        joins = []
        class LingeringWorker:
            def __init__(self, **kw):
                pass
            def start(self):
                pass
            def is_alive(self):
                return True
            def join(self, timeout):
                joins.append(timeout)
        started = time.monotonic()
        with patch.object(m.threading, 'Thread', LingeringWorker):
            with self.assertRaisesRegex(m.ProbeError, '^CLEANUP_FAILED$'):
                self.run_child('import time; time.sleep(10)', timeout=.05)
        self.assertEqual(len(joins), 3)
        self.assertTrue(all(0 <= bound <= 1 for bound in joins))
        self.assertLess(time.monotonic() - started, 1.5)

    def test_exit_codes_sanitized(self):
        for code, expected in ((20, 'RESOLUTION_FAILED'), (21, 'OUTPUT_INVALID'), (22, 'DEPENDENCY_MISSING'), (23, 'OUTPUT_LIMIT'), (9, 'PROCESS_FAILED')):
            with self.assertRaisesRegex(m.ProbeError, '^'+expected+'$'):
                self.run_child(f'import sys; sys.stdin.buffer.read(); sys.stderr.write("SECRET"); sys.exit({code})')


@unittest.skipUnless(sys.platform == 'win32', 'Windows PowerShell mock-module test only')
class PowerShellMockTests(unittest.TestCase):
    def test_fixed_script_with_owned_mock_cmdlet_no_dns(self):
        # Execute the actual fixed script, substituting only an owned temporary
        # DnsClient module. The function checks exact query/type/DnsOnly and emits
        # synthetic records; this is not native DNS acceptance.
        root = os.environ.get('SystemRoot', r'C:\Windows')
        exe = str(Path(root) / 'System32/WindowsPowerShell/v1.0/powershell.exe')
        if not Path(exe).is_file():
            self.skipTest('Windows PowerShell is absent; no installation')
        with tempfile.TemporaryDirectory() as tmp:
            module = Path(tmp) / 'DnsClient.psm1'
            for answers in (0, 1, 2):
                module.write_text("""function Resolve-DnsName {
param([string]$Name,[string]$Type,[switch]$DnsOnly)
if ($Name -cne 'reserved.test.' -or $Type -cne 'A' -or !$DnsOnly) { throw 'scope' }
""" + '\n'.join("[pscustomobject]@{Type='A';Section='Answer';IPAddress='192.0.2."+str(i+1)+"'}" for i in range(answers)) + "\n}\nExport-ModuleMember -Function Resolve-DnsName", encoding='ascii')
                binding = m.Binding('device', 'user', 'namespace', 'win32', exe, str(module), tmp, root)
                request = json.dumps(dict(name='reserved.test.', kind='A', module=str(module))).encode('ascii')
                raw = m._run_child(binding, request, time.monotonic()+15, lambda: False)
                self.assertEqual(len(json.loads(raw)), answers)


if __name__ == '__main__':
    unittest.main()
