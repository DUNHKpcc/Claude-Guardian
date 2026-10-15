"""Offline gate tests and owned synthetic helpers only. Never resolve a name."""
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import time
import unittest
from unittest.mock import patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import os_dns_probe as m


def scope(**kw):
    values = dict(binding=m.Binding('device', 'user', 'namespace', 'darwin',
                                    sys.executable, str(Path.cwd())),
                  name='reserved.test', query_type='A')
    values.update(kw)
    return m.QueryScope(**values)


class GateTests(unittest.TestCase):
    def run_probe(self, selected=None, raw=b'["192.0.2.1"]', **kw):
        kw.setdefault('verify_binding', lambda b: True)
        kw.setdefault('verify_runtime', lambda b: True)
        kw.setdefault('approve_query', lambda s, b: True)
        with patch.object(m.sys, 'platform', 'darwin'), patch.object(m, '_run_child', return_value=raw) as runner:
            result = m.probe_os_dns(selected or scope(), **kw)
        return result, runner

    def test_no_io_on_import(self):
        import importlib
        with patch('socket.getaddrinfo', side_effect=AssertionError()), patch('subprocess.Popen', side_effect=AssertionError()):
            importlib.reload(m)

    def test_order_and_exact_absolute_query(self):
        calls = []
        selected = scope()
        def binding(b):
            self.assertIs(b, selected.binding)
            calls.append('binding')
            return True
        def runtime(b):
            calls.append('runtime')
            return True
        def approval(s, b):
            self.assertIs(s, selected)
            self.assertIn('configured_resolvers', s.network_effect)
            self.assertEqual(s.absolute_name, 'reserved.test.')
            calls.append('approval')
            return True
        result, runner = self.run_probe(selected, verify_binding=binding,
                                        verify_runtime=runtime, approve_query=approval)
        self.assertEqual(calls, ['binding', 'runtime', 'approval', 'binding', 'runtime', 'binding', 'runtime'])
        self.assertEqual(json.loads(runner.call_args.args[1]), ['reserved.test.', 'A'])
        self.assertEqual(result['execution_status'], 'completed')

    def test_report_privacy_and_limits(self):
        result, _ = self.run_probe()
        text = json.dumps(result)
        for private in ('reserved.test', '192.0.2.1', sys.executable, 'namespace'):
            self.assertNotIn(private, text)
        self.assertEqual(result['gate_state'], 'closed')
        value = result['facts'][0]['value']
        self.assertIsNone(value['dns_rcode'])
        self.assertFalse(value['dns_packet_observed'])
        self.assertEqual(value['actual_server'], 'unknown')
        self.assertEqual(value['address_class_counts']['non_global'], 1)

    def test_ipv6_and_empty_answer(self):
        for raw, count in ((b'["2001:db8::1"]', 1), (b'[]', 0)):
            result, _ = self.run_probe(scope(query_type='AAAA'), raw=raw)
            self.assertEqual(result['facts'][0]['value']['address_count'], count)
            self.assertEqual(result['facts'][0]['value']['address_family'], 'IPv6')

    def test_gate_rejection_never_spawns(self):
        for field, error in (('verify_binding', 'TARGET_NOT_BOUND'),
                             ('verify_runtime', 'RUNTIME_NOT_TRUSTED'),
                             ('approve_query', 'AUTHORIZATION_MISSING')):
            for value in (False, 1, None):
                result, runner = self.run_probe(**{field: lambda *a, v=value: v})
                self.assertEqual(result['error_code'], error)
                runner.assert_not_called()

    def test_binding_or_runtime_changes_discard_results(self):
        for field, error in (('verify_binding', 'TARGET_NOT_BOUND'), ('verify_runtime', 'RUNTIME_NOT_TRUSTED')):
            for states, attempts in (([True, False], 0), ([True, True, False], 1)):
                answers = iter(states)
                result, runner = self.run_probe(**{field: lambda *a: next(answers)})
                self.assertEqual(result['error_code'], error)
                self.assertEqual(runner.call_count, attempts)
                self.assertEqual(result['facts'], [])

    def test_invalid_query_and_pc0(self):
        for name in ('localhost', '127.0.0.1', 'reserved.test.', 'RESERVED.test',
                     'test..invalid', 'a.test\n', 'https://example.test', 'xn--.test', 1):
            result, runner = self.run_probe(scope(name=name))
            self.assertEqual(result['error_code'], 'INPUT_INVALID', name)
            runner.assert_not_called()
        for name in ('claude.ai', 'api.anthropic.com', 'myclaude.test'):
            result, runner = self.run_probe(scope(name=name))
            self.assertEqual(result['error_code'], 'PC0_TARGET_FORBIDDEN')
            runner.assert_not_called()
        for kind in ('ANY', 'MX', 1):
            self.assertEqual(self.run_probe(scope(query_type=kind))[0]['error_code'], 'INPUT_INVALID')

    def test_platform_and_budget_validation(self):
        for platform in ('win32', 'linux'):
            with patch.object(m.sys, 'platform', platform), patch.object(m, '_run_child') as runner:
                result = m.probe_os_dns(scope(), verify_binding=lambda b: True,
                    verify_runtime=lambda b: True, approve_query=lambda *a: True)
                self.assertEqual(result['error_code'], 'UNSUPPORTED_PLATFORM')
                runner.assert_not_called()
        for seconds in (True, 0, -1, 16, float('nan'), float('inf'), '5'):
            self.assertEqual(self.run_probe(budget=m.Budget(seconds))[0]['error_code'], 'INPUT_INVALID')

    def test_output_and_exception_suppression(self):
        for raw in (b'{}', b'null', b'[true]', b'["::1"]', b'["192.0.2.1","192.0.2.1"]',
                    b'["fe80::1%private"]', b'private-secret', b'[' * 4000,
                    json.dumps(['192.0.2.1'] * 129).encode(), b'x' * 4097):
            result, _ = self.run_probe(raw=raw)
            self.assertEqual(result['facts'], [])
            self.assertNotEqual(result['execution_status'], 'completed')
            self.assertNotIn('private-secret', json.dumps(result))
        result, runner = self.run_probe(verify_binding=lambda b: (_ for _ in ()).throw(ValueError('private-secret')))
        runner.assert_not_called()
        self.assertNotIn('private-secret', json.dumps(result))

    def test_cancel_before_spawn_and_expired_callback(self):
        result, runner = self.run_probe(cancelled=lambda: True)
        self.assertEqual(result['error_code'], 'CANCELLED')
        runner.assert_not_called()
        def slow(*args):
            time.sleep(.06)
            return True
        result, runner = self.run_probe(approve_query=slow, budget=m.Budget(.05))
        self.assertEqual(result['error_code'], 'TIMEOUT')
        runner.assert_not_called()


@unittest.skipUnless(os.name == 'posix', 'POSIX runner; Windows intentionally unsupported')
class ChildTests(unittest.TestCase):
    def run_child(self, code, seconds=2, cancelled=lambda: False):
        processes = []
        popen = subprocess.Popen
        def owned(*a, **kw):
            proc = popen(*a, **kw)
            processes.append(proc)
            return proc
        with patch.object(m, '_HELPER', code), patch.object(m.subprocess, 'Popen', side_effect=owned):
            try:
                return m._run_child(scope().binding, b'[]', time.monotonic()+seconds, cancelled)
            finally:
                for proc in processes:
                    self.assertIsNotNone(proc.poll(), 'owned helper was not reaped')
                    self.assertTrue(proc.stdin.closed)
                    self.assertTrue(proc.stdout.closed)

    def test_clean_environment_and_isolated_runtime(self):
        code = ('import os,sys,json; sys.stdin.buffer.read(); '
                'assert "GUARDIAN_TEST_SECRET" not in os.environ; '
                'assert "PYTHONPATH" not in os.environ; '
                'assert sys.flags.isolated and sys.flags.no_site; '
                'sys.stdout.write("[]")')
        with patch.dict(os.environ, GUARDIAN_TEST_SECRET='private', PYTHONPATH='/bad', LD_PRELOAD='/bad'):
            self.assertEqual(self.run_child(code), b'[]')

    def test_timeout_kills_blocked_helper(self):
        start = time.monotonic()
        with self.assertRaisesRegex(m.ProbeError, '^TIMEOUT$'):
            self.run_child('import time; time.sleep(60)', seconds=.15)
        self.assertLess(time.monotonic()-start, 2)

    def test_cancellation_kills_blocked_helper(self):
        start = time.monotonic()
        with self.assertRaisesRegex(m.ProbeError, '^CANCELLED$'):
            self.run_child('import time; time.sleep(60)', cancelled=lambda: time.monotonic()-start > .15)
        self.assertLess(time.monotonic()-start, 2)

    def test_output_limit_and_nonzero_exit(self):
        with self.assertRaisesRegex(m.ProbeError, '^OUTPUT_LIMIT$'):
            self.run_child('import sys; sys.stdout.buffer.write(b"x"*1000000)')
        for code, expected in ((20, 'RESOLUTION_FAILED'), (21, 'PROCESS_FAILED')):
            with self.assertRaisesRegex(m.ProbeError, '^'+expected+'$'):
                self.run_child('import sys; sys.exit('+str(code)+')')

    def test_eof_before_exit_still_times_out(self):
        with self.assertRaisesRegex(m.ProbeError, '^TIMEOUT$'):
            self.run_child('import os,time; os.close(1); time.sleep(60)', seconds=.15)

    def test_callback_exception_reaps_owned_child(self):
        calls = 0
        def cancelled():
            nonlocal calls
            calls += 1
            if calls >= 3:
                raise RuntimeError('private')
            return False
        with self.assertRaisesRegex(RuntimeError, 'private'):
            self.run_child('import time; time.sleep(60)', cancelled=cancelled)


class CleanupFailureTests(unittest.TestCase):
    def test_failed_reaping_is_not_successful_cancellation(self):
        import io
        from unittest.mock import Mock
        proc = Mock(stdin=io.BytesIO(), stdout=io.BytesIO())
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired('fixed-helper', 1)
        checks = iter([False, True])
        with patch.object(m.subprocess, 'Popen', return_value=proc):
            with self.assertRaisesRegex(m.ProbeError, '^CLEANUP_FAILED$'):
                m._run_child(scope().binding, b'[]', time.monotonic()+2, lambda: next(checks))
        proc.kill.assert_called_once()
        proc.wait.assert_called_once_with(timeout=1)
        self.assertTrue(proc.stdin.closed)
        self.assertTrue(proc.stdout.closed)

    def test_stream_close_error_preserves_reap_failure_and_closes_other_pipe(self):
        import io
        from unittest.mock import Mock
        class BrokenClose(io.BytesIO):
            def close(self):
                super().close()
                raise OSError('private stream detail')
        proc = Mock(stdin=BrokenClose(), stdout=io.BytesIO())
        proc.poll.return_value = None
        proc.wait.side_effect = subprocess.TimeoutExpired('fixed-helper', 1)
        checks = iter([False, True])
        with patch.object(m.subprocess, 'Popen', return_value=proc):
            with self.assertRaisesRegex(m.ProbeError, '^CLEANUP_FAILED$'):
                m._run_child(scope().binding, b'[]', time.monotonic()+2, lambda: next(checks))
        proc.kill.assert_called_once()
        proc.wait.assert_called_once_with(timeout=1)
        self.assertTrue(proc.stdin.closed)
        self.assertTrue(proc.stdout.closed)

    def test_kill_exit_race_still_reaps(self):
        import io
        from unittest.mock import Mock
        proc = Mock(stdin=io.BytesIO(), stdout=io.BytesIO())
        proc.poll.return_value = None
        proc.kill.side_effect = ProcessLookupError()
        checks = iter([False, True])
        with patch.object(m.subprocess, 'Popen', return_value=proc):
            with self.assertRaisesRegex(m.ProbeError, '^CANCELLED$'):
                m._run_child(scope().binding, b'[]', time.monotonic()+2, lambda: next(checks))
        proc.wait.assert_called_once_with(timeout=1)
        self.assertTrue(proc.stdin.closed)
        self.assertTrue(proc.stdout.closed)

    def test_keyboard_interrupt_closes_owned_pipes(self):
        import io
        from unittest.mock import Mock
        proc = Mock(stdin=io.BytesIO(), stdout=io.BytesIO())
        proc.poll.return_value = None
        calls = 0
        def cancel():
            nonlocal calls
            calls += 1
            if calls == 2:
                raise KeyboardInterrupt()
            return False
        with patch.object(m.subprocess, 'Popen', return_value=proc):
            with self.assertRaises(KeyboardInterrupt):
                m._run_child(scope().binding, b'[]', time.monotonic()+2, cancel)
        proc.kill.assert_called_once()
        proc.wait.assert_called_once_with(timeout=1)
        self.assertTrue(proc.stdin.closed)
        self.assertTrue(proc.stdout.closed)


class HelperTests(unittest.TestCase):
    def test_real_helper_uses_only_exact_system_api_with_mock(self):
        import io
        from types import SimpleNamespace
        for kind, family, ip in (('A', socket.AF_INET, '192.0.2.1'), ('AAAA', socket.AF_INET6, '2001:db8::1')):
            stdin = SimpleNamespace(buffer=io.BytesIO(json.dumps(['reserved.test.', kind]).encode()))
            stdout = SimpleNamespace(buffer=io.BytesIO())
            with patch.object(sys, 'stdin', stdin), patch.object(sys, 'stdout', stdout), patch.object(
                    socket, 'getaddrinfo', return_value=[(family, socket.SOCK_STREAM, 6, '', (ip, 0))]) as resolve:
                exec(m._HELPER, {})
            resolve.assert_called_once_with('reserved.test.', None, family, socket.SOCK_STREAM, 0, 0)
            self.assertEqual(json.loads(stdout.buffer.getvalue()), [ip])


if __name__ == '__main__':
    unittest.main()
