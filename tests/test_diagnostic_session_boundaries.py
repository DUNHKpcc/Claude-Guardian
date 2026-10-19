"""Offline adapter-boundary regressions, not native-host acceptance evidence."""
from contextlib import ExitStack
import io
import json
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import Mock, patch
from environment_entry_fixture import local_entry

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import diagnostic_session as m


class AdapterBoundaryTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('socket.getaddrinfo', side_effect=AssertionError('No network')))
        self.stack.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No process')))
        self.stack.enter_context(patch.object(m.sys, 'platform', 'darwin'))
        self.tick = 100.0
        self.stack.enter_context(patch.object(m.time, 'monotonic', side_effect=lambda: self.tick))
        self.capture = self.stack.enter_context(patch.object(m.native_context, 'capture_current_context', return_value=object()))
        self.recheck = self.stack.enter_context(patch.object(m.native_context, 'recheck_context', return_value={}))
        self.describe = self.stack.enter_context(patch.object(m.native_context, 'describe_context', return_value={
            'runtime_integrity': 'not_verified', 'network_namespace': 'unknown', 'gate_state': 'closed'}))
        self.child = self.stack.enter_context(patch.object(m.os_dns_probe, '_run_child', side_effect=lambda binding, request, deadline, cancelled: b'["2001:db8::1"]' if b'AAAA' in request else b'["192.0.2.1"]'))
        self.consent = Mock(return_value=True)
        self.cancel = Mock(return_value=False)
        # Synthetic host assertions exercise wiring only, never establish trust.
        binding = m.os_dns_probe.Binding('target', 'user', 'namespace', 'darwin', '/trusted/python', '/trusted')
        self.host = m.DNSHost(binding, Mock(return_value=True), Mock(return_value=True), Mock(return_value=True))

    def execute(self, **kwargs):
        kwargs.setdefault('consent', self.consent)
        kwargs.setdefault('cancelled', self.cancel)
        kwargs.setdefault('entry_request', local_entry('target'))
        result = m.execute('target', **kwargs)
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['contact_phase'], 'precontact')
        self.assertEqual(result['changes'], [])
        self.assertFalse(result['permission_restorable'])
        self.assertNotIn('SECRET', json.dumps(result))
        self.assertNotIn('192.0.2.1', json.dumps(result))
        return result

    def dns(self):
        return self.execute(dns_host=self.host, queries=[('reserved.test', 'A'), ('second.test', 'AAAA')])

    def test_healthy_adapters_preserve_separately_approved_samples(self):
        result = self.dns()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['errors'], [])
        self.assertEqual(self.consent.call_count, 3)
        self.assertEqual(self.child.call_count, 2)
        self.assertEqual(len(result['probe_evidence']['samples']), 2)

    def test_capture_uses_original_deadline_not_new_handle_lifetime(self):
        def capture(**kwargs):
            self.tick = 160.0
            return object()
        self.capture.side_effect = capture
        result = self.dns()
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        self.assertEqual(result['report']['facts'], [])
        self.recheck.assert_not_called()
        self.describe.assert_not_called()
        self.child.assert_not_called()

    def test_recheck_crossing_deadline_discards_context(self):
        def recheck(*args, **kwargs):
            self.tick = 160.0
            return {}
        self.recheck.side_effect = recheck
        result = self.dns()
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        self.describe.assert_not_called()
        self.child.assert_not_called()

    def test_delayed_dns_consent_expires_even_if_context_adapter_accepts(self):
        def consent(scope):
            if scope['operation'] == 'system_dns_query':
                self.tick = 160.0
            return True
        self.consent.side_effect = consent
        result = self.dns()
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')
        self.child.assert_not_called()

    def test_describe_crossing_deadline_makes_metadata_historical(self):
        def describe(handle):
            self.tick = 160.0
            return {'gate_state': 'closed'}
        self.describe.side_effect = describe
        result = self.execute()
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')
        self.assertEqual(result['context']['continuity'], 'not_current')

    def test_invalid_or_reversed_strict_flow_clock_fails_closed(self):
        for tick in (99.0, float('nan'), float('inf'), True, 10**1000):
            with self.subTest(tick=str(tick)[:30]):
                self.tick = 100.0
                def capture(**kwargs):
                    self.tick = tick
                    return object()
                self.capture.side_effect = capture
                result = self.execute()
                self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
                self.assertEqual(result['report']['facts'], [])
        self.child.assert_not_called()

    def test_unexpected_recheck_failure_inside_probe_cannot_recover(self):
        def child(*args):
            def fail_once(*args, **kwargs):
                self.recheck.side_effect = None
                raise RuntimeError('SECRET context adapter')
            self.recheck.side_effect = fail_once
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.dns()
        self.assertEqual(result['errors'], ['SESSION_FAILED'])
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(result['probe_evidence']['samples'], [])
        self.assertEqual(self.child.call_count, 1)
        self.assertEqual(self.consent.call_count, 2)

    def test_unexpected_cancellation_adapter_failure_inside_probe_is_latched(self):
        def child(*args):
            def fail_once():
                self.cancel.side_effect = None
                raise RuntimeError('SECRET cancellation adapter')
            self.cancel.side_effect = fail_once
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.dns()
        self.assertEqual(result['errors'], ['SESSION_FAILED'])
        self.assertEqual(result['probe_evidence']['samples'], [])
        self.assertEqual(self.child.call_count, 1)
        self.assertEqual(self.consent.call_count, 2)

    def test_transient_cancellation_inside_probe_discards_inflight_result(self):
        def child(*args):
            def stop_once():
                self.cancel.side_effect = None
                return True
            self.cancel.side_effect = stop_once
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.dns()
        self.assertEqual(result['errors'], ['CANCELLED'])
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['probe_evidence']['samples'], [])
        self.assertEqual(self.child.call_count, 1)

    def test_context_adapter_eof_inside_probe_is_cancellation(self):
        def child(*args):
            def fail_once(*args, **kwargs):
                self.recheck.side_effect = None
                raise EOFError('SECRET')
            self.recheck.side_effect = fail_once
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.dns()
        self.assertEqual(result['errors'], ['CANCELLED'])
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['probe_evidence']['samples'], [])
        self.assertEqual(self.child.call_count, 1)

    def test_later_adapter_failure_invalidates_earlier_evidence(self):
        def consent(scope):
            if scope.get('absolute_name') == 'second.test.':
                self.recheck.side_effect = RuntimeError('SECRET')
            return True
        self.consent.side_effect = consent
        result = self.dns()
        self.assertEqual(result['errors'], ['SESSION_FAILED'])
        samples = result['probe_evidence']['samples']
        self.assertEqual(len(samples), 1)
        self.assertEqual(samples[0]['context'], {})
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')
        self.assertEqual(self.child.call_count, 1)

    def test_cancellation_adapter_failure_before_consent_performs_no_read(self):
        self.cancel.side_effect = RuntimeError('SECRET')
        result = self.execute()
        self.assertEqual(result['errors'], ['SESSION_FAILED'])
        self.consent.assert_not_called()
        self.capture.assert_not_called()

    def test_windows_strict_capture_also_observes_session_deadline(self):
        def capture(**kwargs):
            self.tick = 160.0
            return object()
        with patch.object(m.sys, 'platform', 'win32'), \
                patch.object(m.windows_native_context, 'capture_current_context', side_effect=capture), \
                patch.object(m.windows_native_context, 'recheck_context') as recheck:
            result = self.execute()
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        recheck.assert_not_called()
        self.capture.assert_not_called()

    def test_cli_cancel_does_not_create_requested_dashboard(self):
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m.TerminalConsent, '__call__', return_value=False), \
                patch.object(m.guardian, 'save_new', wraps=m.guardian.save_new) as save:
            path = Path(directory) / 'cancelled.html'
            output = io.StringIO()
            code = m.run(['--target-ref', 'target', '--dashboard-output', str(path)], outgoing=output,
                         entry_request=local_entry('target'))
            self.assertEqual(code, 3)
            self.assertEqual(json.loads(output.getvalue())['status'], 'cancelled')
            self.assertNotIn('dashboard_saved', json.loads(output.getvalue()))
            self.assertFalse(path.exists())
            save.assert_not_called()
        self.capture.assert_not_called()

    def test_cli_explicit_blocked_report_can_still_be_saved(self):
        self.capture.side_effect = m.native_context.ContextError('PERMISSION_DENIED')
        with tempfile.TemporaryDirectory() as directory, \
                patch.object(m.TerminalConsent, '__call__', return_value=True):
            path = Path(directory) / 'blocked.html'
            output = io.StringIO()
            code = m.run(['--target-ref', 'target', '--dashboard-output', str(path)], outgoing=output,
                         entry_request=local_entry('target'))
            self.assertEqual(code, 2)
            self.assertTrue(json.loads(output.getvalue())['dashboard_saved'])
            self.assertIn('<html', path.read_text(encoding='utf-8'))


if __name__ == '__main__':
    unittest.main()
