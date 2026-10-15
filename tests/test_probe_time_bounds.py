"""Synthetic API time validation; no listeners, native probes, or subprocesses."""
from contextlib import ExitStack
from pathlib import Path
import sys
from types import SimpleNamespace
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import controller_inventory as controller
import os_dns_probe as mac_dns
import serve_webrtc as webrtc
import windows_dns_probe as windows_dns


INVALID_TIMES = (True, False, None, '1', float('nan'), float('inf'),
                 -float('inf'), 10 ** 1000, -(10 ** 1000))


def controller_binding():
    return controller.ControllerBinding('device', 'namespace', 'user', 'instance',
                                        123, 'process-start', '127.0.0.1', 54321)


def dns_scope(module):
    if module is mac_dns:
        bound = module.Binding('device', 'user', 'namespace', 'darwin',
                               '/trusted/python', '/trusted')
    else:
        bound = module.Binding('device', 'user', 'namespace', 'win32',
            r'C:\Windows\System32\WindowsPowerShell\v1.0\powershell.exe',
            r'C:\trusted\DnsClient.psd1', r'C:\trusted', r'C:\Windows')
    return module.QueryScope(bound, 'reserved.test', 'A')


class SyntheticOnlyTests(unittest.TestCase):
    def setUp(self):
        self.no_io = ExitStack()
        self.addCleanup(self.no_io.close)
        self.no_io.enter_context(patch('socket.socket', side_effect=AssertionError('No network I/O')))
        self.no_io.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No native probes')))


class ControllerClockTests(SyntheticOnlyTests):
    def audit(self, clock, **kwargs):
        transport = kwargs.setdefault('transport', Mock(return_value=(200, b'{"mode":"rule"}')))
        kwargs.setdefault('verify_binding', Mock(return_value=True))
        kwargs.setdefault('approve_read', Mock(return_value=True))
        with patch.object(controller, 'time', SimpleNamespace(monotonic=clock)):
            result = controller.audit_controller(controller_binding(), ('/configs',), **kwargs)
        return result, transport

    def assert_invalid(self, result):
        self.assertEqual(result['error_code'], 'INPUT_OR_RESPONSE_INVALID')
        self.assertEqual(result['execution_status'], 'blocked')
        self.assertEqual(result['facts'], [])

    def test_invalid_initial_clock_prevents_callbacks_and_transport(self):
        for value in INVALID_TIMES:
            with self.subTest(value=value):
                verify, approve = Mock(return_value=True), Mock(return_value=True)
                result, transport = self.audit(lambda: value, verify_binding=verify, approve_read=approve)
                self.assert_invalid(result)
                self.assertEqual(result['requests_attempted'], 0)
                verify.assert_not_called()
                approve.assert_not_called()
                transport.assert_not_called()

    def test_invalid_or_backward_clock_after_approval_prevents_transport(self):
        for value in INVALID_TIMES + (1.0,):
            with self.subTest(value=value):
                now = [2.0]
                def approve(*_):
                    now[0] = value
                    return True
                result, transport = self.audit(lambda: now[0], approve_read=approve)
                self.assert_invalid(result)
                self.assertEqual(result['requests_attempted'], 0)
                transport.assert_not_called()

    def test_regression_from_previous_read_even_above_initial_clock(self):
        # 0 -> 2 -> 1 is still a regression, despite staying above the start.
        readings = iter((0.0, 2.0, 1.0))
        result, transport = self.audit(lambda: next(readings))
        self.assert_invalid(result)
        transport.assert_not_called()

    def test_invalid_or_backward_clock_after_transport_cannot_publish_facts(self):
        for value in INVALID_TIMES + (1.0,):
            with self.subTest(value=value):
                now = [2.0]
                def transport(*_):
                    now[0] = value
                    return 200, b'{"mode":"rule"}'
                result, _ = self.audit(lambda: now[0], transport=transport)
                self.assert_invalid(result)
                self.assertEqual(result['requests_attempted'], 1)

    def test_budget_validation_is_bounded_before_callbacks(self):
        for value in INVALID_TIMES + (0, -1, 16):
            with self.subTest(value=value):
                clock = Mock(return_value=0.0)
                result, transport = self.audit(clock, budget=controller.Budget(max_seconds=value))
                self.assert_invalid(result)
                clock.assert_not_called()
                transport.assert_not_called()

    def test_clock_origin_must_allow_a_finite_future_deadline(self):
        for value in (sys.float_info.max, -sys.float_info.max, 10 ** 308):
            with self.subTest(value=value):
                result, transport = self.audit(lambda: value)
                self.assert_invalid(result)
                self.assertEqual(result['requests_attempted'], 0)
                transport.assert_not_called()

    def test_equal_and_finite_negative_clock_origins_are_valid(self):
        for value in (0, 1.5, -10.0):
            with self.subTest(value=value):
                result, transport = self.audit(lambda: value)
                self.assertEqual(result['execution_status'], 'completed')
                self.assertIsNone(result['error_code'])
                transport.assert_called_once()

    def test_timeout_and_cancellation_stay_distinct(self):
        now = [0.0]
        def approve(*_):
            now[0] = 5.0
            return True
        result, transport = self.audit(lambda: now[0], approve_read=approve)
        self.assertEqual(result['error_code'], 'TIMEOUT')
        transport.assert_not_called()
        result, transport = self.audit(lambda: 0.0, cancelled=lambda: True)
        self.assertEqual(result['error_code'], 'CANCELLED')
        transport.assert_not_called()


class DnsClockTests(SyntheticOnlyTests):
    modules = (mac_dns, windows_dns)

    def probe(self, module, clock, *, runner=None, **kwargs):
        kwargs.setdefault('verify_binding', Mock(return_value=True))
        kwargs.setdefault('verify_runtime', Mock(return_value=True))
        kwargs.setdefault('approve_query', Mock(return_value=True))
        selected = dns_scope(module)
        runner = runner or Mock(return_value=b'["192.0.2.1"]')
        probe = module.probe_os_dns if module is mac_dns else module.probe_windows_dns
        with patch.object(module, 'time', SimpleNamespace(monotonic=clock)), patch.object(
                module.sys, 'platform', selected.binding.platform), patch.object(module, '_run_child', runner):
            result = probe(selected, **kwargs)
        return result, runner

    def assert_invalid(self, result, code='OUTPUT_INVALID'):
        self.assertEqual(result['error_code'], code)
        self.assertEqual(result['execution_status'], 'blocked')
        self.assertEqual(result['facts'], [])

    def test_invalid_initial_clock_prevents_callbacks_and_runner(self):
        for module in self.modules:
            for value in INVALID_TIMES:
                with self.subTest(module=module.__name__, value=value):
                    verify, runtime, approve = (Mock(return_value=True) for _ in range(3))
                    result, runner = self.probe(module, lambda: value, verify_binding=verify,
                        verify_runtime=runtime, approve_query=approve)
                    self.assert_invalid(result)
                    self.assertEqual(result['requests_attempted'], 0)
                    for callback in (verify, runtime, approve, runner):
                        callback.assert_not_called()

    def test_invalid_or_backward_clock_after_approval_prevents_runner(self):
        for module in self.modules:
            for value in INVALID_TIMES + (1.0,):
                with self.subTest(module=module.__name__, value=value):
                    now = [2.0]
                    def approve(*_):
                        now[0] = value
                        return True
                    result, runner = self.probe(module, lambda: now[0], approve_query=approve)
                    self.assert_invalid(result)
                    self.assertEqual(result['requests_attempted'], 0)
                    runner.assert_not_called()

    def test_regression_from_previous_read_even_above_initial_clock(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                readings = iter((0.0, 2.0, 1.0))
                result, runner = self.probe(module, lambda: next(readings))
                self.assert_invalid(result)
                runner.assert_not_called()

    def test_invalid_or_backward_clock_after_runner_cannot_publish_elapsed(self):
        for module in self.modules:
            for value in INVALID_TIMES + (1.0,):
                with self.subTest(module=module.__name__, value=value):
                    now = [2.0]
                    def run(*_):
                        now[0] = value
                        return b'["192.0.2.1"]'
                    result, runner = self.probe(module, lambda: now[0], runner=Mock(side_effect=run))
                    self.assert_invalid(result)
                    self.assertEqual(result['requests_attempted'], 1)
                    runner.assert_called_once()

    def test_final_elapsed_sample_is_checked_after_projection(self):
        for module in self.modules:
            for value in INVALID_TIMES + (1.0,):
                with self.subTest(module=module.__name__, value=value):
                    now = [2.0]
                    original = module._project
                    def project(*args):
                        projected = original(*args)
                        now[0] = value
                        return projected
                    with patch.object(module, '_project', side_effect=project):
                        result, runner = self.probe(module, lambda: now[0])
                    self.assert_invalid(result)
                    runner.assert_called_once()

    def test_invalid_budget_never_reads_clock_or_starts_runner(self):
        for module in self.modules:
            for value in INVALID_TIMES + (0, -1, .049, 16):
                with self.subTest(module=module.__name__, value=value):
                    clock = Mock(return_value=0.0)
                    result, runner = self.probe(module, clock, budget=module.Budget(value))
                    self.assert_invalid(result, 'INPUT_INVALID')
                    clock.assert_not_called()
                    runner.assert_not_called()

    def test_clock_origin_must_allow_a_finite_future_deadline(self):
        for module in self.modules:
            for value in (sys.float_info.max, -sys.float_info.max, 10 ** 308):
                with self.subTest(module=module.__name__, value=value):
                    result, runner = self.probe(module, lambda: value)
                    self.assert_invalid(result)
                    self.assertEqual(result['requests_attempted'], 0)
                    runner.assert_not_called()

    def test_elapsed_is_finite_nonnegative_and_uses_checked_sample(self):
        for module in self.modules:
            for start, finish in ((0.0, .125), (2.0, 2.0), (-10.0, -9.875)):
                with self.subTest(module=module.__name__, start=start, finish=finish):
                    now = [start]
                    def run(*_):
                        now[0] = finish
                        return b'["192.0.2.1"]'
                    result, _ = self.probe(module, lambda: now[0], runner=Mock(side_effect=run))
                    self.assertEqual(result['execution_status'], 'completed')
                    self.assertEqual(result['facts'][0]['elapsed_ms'], round((finish - start) * 1000, 3))

    def test_budget_boundaries_and_clock_state_are_per_call(self):
        for module in self.modules:
            for start, seconds in ((100.0, .05), (0.0, 15)):
                with self.subTest(module=module.__name__, seconds=seconds):
                    result, _ = self.probe(module, lambda: start, budget=module.Budget(seconds))
                    self.assertEqual(result['execution_status'], 'completed')
                    self.assertEqual(result['facts'][0]['elapsed_ms'], 0.0)

    def test_timeout_and_cancellation_stay_distinct(self):
        for module in self.modules:
            with self.subTest(module=module.__name__):
                now = [0.0]
                def approve(*_):
                    now[0] = 5.0
                    return True
                result, runner = self.probe(module, lambda: now[0], approve_query=approve)
                self.assertEqual(result['error_code'], 'TIMEOUT')
                runner.assert_not_called()
                result, runner = self.probe(module, lambda: 0.0, cancelled=lambda: True)
                self.assertEqual(result['error_code'], 'CANCELLED')
                runner.assert_not_called()


class WebRtcDurationTests(SyntheticOnlyTests):
    def test_invalid_duration_rejected_before_server_state_or_io(self):
        # An uninitialized target proves validation needs no instance state or I/O.
        for value in INVALID_TIMES + (0, -1, 901):
            with self.subTest(value=value):
                with self.assertRaisesRegex(ValueError,
                        '^Duration must be greater than zero and at most 900 seconds$'):
                    webrtc.LocalProbeServer.serve(object(), duration_seconds=value)


if __name__ == '__main__':
    unittest.main()
