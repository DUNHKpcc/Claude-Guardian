"""Synthetic integration only. Never inspect a real device or send DNS traffic."""
from contextlib import ExitStack
import importlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import time
import unittest
from unittest.mock import Mock, patch

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import diagnostic_session as m


class SessionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch('socket.getaddrinfo', side_effect=AssertionError('No network')))
        self.stack.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No process')))
        self.stack.enter_context(patch.object(m.sys, 'platform', 'darwin'))
        self.capture = self.stack.enter_context(patch.object(m.native_context, 'capture_current_context', return_value=object()))
        self.recheck = self.stack.enter_context(patch.object(m.native_context, 'recheck_context', return_value={}))
        self.stack.enter_context(patch.object(m.native_context, 'describe_context', return_value={
            'runtime_integrity': 'not_verified', 'filesystem_namespace': 'unknown',
            'network_namespace': 'unknown', 'gate_state': 'closed'}))
        self.child = self.stack.enter_context(patch.object(m.os_dns_probe, '_run_child', return_value=b'["192.0.2.1"]'))
        self.consent = Mock(return_value=True)
        self.binding = m.os_dns_probe.Binding('target', 'user', 'namespace', 'darwin', '/trusted/python', '/trusted')
        # These are synthetic host assertions only, never production adapters.
        self.host = m.DNSHost(self.binding, Mock(return_value=True),
                             Mock(return_value=True), Mock(return_value=True))

    def execute(self, **kwargs):
        kwargs.setdefault('consent', self.consent)
        result = m.execute('target', **kwargs)
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['changes'], [])
        self.assertFalse(result['permission_restorable'])
        self.assertNotIn('verified', [c['state'] for c in m.status_dashboard.project(
            result['report'], probe_report=result['probe_evidence'])['cards']])
        return result

    def test_metadata_only_does_not_synthesize_dns_authority(self):
        result = self.execute()
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['context']['runtime_integrity'], 'not_verified')
        self.assertIn('blocked_missing', result['dns_availability'])
        self.assertEqual(result['report']['limits']['collector_external_network'], 'forbidden')
        self.assertEqual(result['report']['limits']['system_dns_sample'], 'not_run')
        self.child.assert_not_called()

    def test_separate_exact_dns_consent_and_dashboard(self):
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        prompts = [c.args[0] for c in self.consent.call_args_list]
        self.assertEqual(len(prompts), 2)
        self.assertEqual(prompts[1]['absolute_name'], 'reserved.test.')
        self.assertEqual(prompts[1]['query_type'], 'A')
        self.assertIn('upstream', prompts[1]['disclosure'])
        self.assertIn('partial_findings', prompts[1])
        self.assertEqual(result['probe_evidence']['samples'][0]['result']['execution_status'], 'completed')
        self.assertIn('macOS 系统解析 getaddrinfo', result['dashboard_html'])
        self.assertEqual(result['report']['limits']['collector_external_network'],
                         'explicit_system_dns_samples_only')
        self.assertIn('ENV-04', result['report']['module_ids'])
        self.assertNotIn('192.0.2.1', json.dumps(result))
        self.assertNotIn('reserved.test', json.dumps(result))
        self.assertNotIn('/trusted', json.dumps(result))
        self.assertGreaterEqual(self.host.verify_binding.call_count, 4)

    def test_declining_local_performs_no_reads(self):
        self.consent.return_value = False
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['DECLINED'])
        self.capture.assert_not_called()
        self.child.assert_not_called()

    def test_declining_dns_retains_historical_partial_metadata(self):
        self.consent.side_effect = [True, False]
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['status'], 'cancelled')
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')
        self.child.assert_not_called()

    def test_cancel_before_read(self):
        self.execute(cancelled=lambda: True)
        self.capture.assert_not_called()
        self.consent.assert_not_called()

    def test_cancellation_during_consent_does_not_read(self):
        cancelled = [False]
        def approve(scope):
            cancelled[0] = True
            return True
        result = self.execute(consent=approve, cancelled=lambda: cancelled[0])
        self.assertEqual(result['status'], 'cancelled')
        self.capture.assert_not_called()

    def test_delayed_consent_expired_context_no_dns(self):
        def approve(scope):
            if scope['operation'] == 'system_dns_query':
                self.recheck.side_effect = m.native_context.ContextError('CONTEXT_EXPIRED')
            return True
        result = self.execute(consent=approve, dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['CONTEXT_EXPIRED'])
        self.child.assert_not_called()

    def test_rebind_after_consent_no_dns(self):
        def approve(scope):
            if scope['operation'] == 'system_dns_query':
                self.host.verify_binding.return_value = False
            return True
        result = self.execute(consent=approve, dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['TARGET_NOT_BOUND'])
        self.child.assert_not_called()

    def test_context_change_after_probe_discards_new_result(self):
        def child(*args):
            self.recheck.side_effect = m.native_context.ContextError('CONTEXT_CHANGED')
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['CONTEXT_CHANGED'])
        self.assertEqual(result['probe_evidence']['samples'], [])

    def test_transient_context_failure_inside_probe_is_latched(self):
        def child(*args):
            self.recheck.side_effect = [m.native_context.ContextError('CONTEXT_CHANGED'), {}]
            return b'["192.0.2.1"]'
        self.child.side_effect = child
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A'), ('second.test', 'A')])
        self.assertEqual(result['errors'], ['CONTEXT_CHANGED'])
        self.assertEqual(self.child.call_count, 1)
        self.assertEqual(result['probe_evidence']['samples'], [])

    def test_host_verifier_exceptions_are_latched_before_launch(self):
        for field, code in (('verify_binding', 'TARGET_NOT_BOUND'),
                            ('verify_runtime', 'RUNTIME_NOT_TRUSTED'),
                            ('verify_neutral', 'ENDPOINT_NEUTRALITY_UNVERIFIED')):
            with self.subTest(field=field):
                verifier = getattr(self.host, field)
                verifier.side_effect = [True, RuntimeError('SECRET host failure'), True]
                self.consent.reset_mock()
                self.child.reset_mock()
                result = self.execute(dns_host=self.host,
                    queries=[('reserved.test', 'A'), ('second.test', 'A')])
                self.assertEqual(result['errors'], [code])
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['probe_evidence']['samples'], [])
                self.assertEqual(result['report']['facts'][0]['state'], 'stale')
                self.assertEqual(self.consent.call_count, 2)
                self.assertNotIn('SECRET', json.dumps(result))
                self.child.assert_not_called()
                verifier.side_effect = None

    def test_host_verifier_exceptions_after_probe_stop_and_discard(self):
        for field, code in (('verify_binding', 'TARGET_NOT_BOUND'),
                            ('verify_runtime', 'RUNTIME_NOT_TRUSTED')):
            with self.subTest(field=field):
                verifier = getattr(self.host, field)
                verifier.side_effect = [True, True, True, RuntimeError('SECRET'), True]
                self.consent.reset_mock()
                self.child.reset_mock()
                result = self.execute(dns_host=self.host,
                    queries=[('reserved.test', 'A'), ('second.test', 'A')])
                self.assertEqual(result['errors'], [code])
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['probe_evidence']['samples'], [])
                self.assertEqual(self.child.call_count, 1)
                self.assertEqual(self.consent.call_count, 2)
                verifier.side_effect = None

    def test_host_trust_loss_on_later_query_invalidates_retained_sample(self):
        def approve(scope):
            if scope.get('absolute_name') == 'second.test.':
                self.host.verify_runtime.side_effect = RuntimeError('SECRET')
            return True
        result = self.execute(consent=approve, dns_host=self.host,
            queries=[('reserved.test', 'A'), ('second.test', 'A')])
        self.assertEqual(result['errors'], ['RUNTIME_NOT_TRUSTED'])
        self.assertEqual(self.child.call_count, 1)
        self.assertEqual(len(result['probe_evidence']['samples']), 1)
        self.assertEqual(result['probe_evidence']['samples'][0]['context'], {})
        self.assertEqual(result['report']['facts'][0]['state'], 'stale')

    def test_runtime_missing_stops_before_query_consent(self):
        self.host.verify_runtime.return_value = False
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['RUNTIME_NOT_TRUSTED'])
        self.assertEqual(self.consent.call_count, 1)
        self.child.assert_not_called()

    def test_unknown_neutrality_stops(self):
        self.host.verify_neutral.return_value = False
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['ENDPOINT_NEUTRALITY_UNVERIFIED'])
        self.child.assert_not_called()

    def test_pc0_forbidden_name(self):
        result = self.execute(dns_host=self.host, queries=[('api.anthropic.com', 'A')])
        self.assertEqual(result['errors'], ['PC0_TARGET_FORBIDDEN'])
        self.child.assert_not_called()

    def test_json_host_or_saved_grants_cannot_authorize(self):
        result = self.execute(dns_host={'approved': True, 'binding': self.binding})
        self.assertEqual(result['errors'], ['HOST_INTEGRATION_INVALID'])
        self.capture.assert_not_called()
        self.child.assert_not_called()
        self.consent.assert_not_called()

    def test_interview_answers_never_replace_approval(self):
        state = m.interview_flow.new_state('target', 'account')
        self.consent.return_value = False
        result = self.execute(interview=state)
        self.assertEqual(result['interview']['action_gate'], 'blocked')
        self.capture.assert_not_called()

    def test_missing_host_with_requested_query_is_visible(self):
        result = self.execute(queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['DNS_HOST_INTEGRATION_REQUIRED'])
        self.child.assert_not_called()

    def test_mixed_dns_results_preserved_with_separate_approvals(self):
        self.child.side_effect = [m.os_dns_probe.ProbeError('RESOLUTION_FAILED'), b'["192.0.2.1"]']
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A'), ('second.test', 'A')])
        self.assertEqual(result['errors'], ['RESOLUTION_FAILED'])
        samples = result['probe_evidence']['samples']
        self.assertEqual([s['result']['execution_status'] for s in samples], ['blocked', 'completed'])
        self.assertEqual(self.consent.call_count, 3)

    def test_timeout_stops_remaining_queries(self):
        self.child.side_effect = m.os_dns_probe.ProbeError('TIMEOUT')
        result = self.execute(dns_host=self.host, queries=[('reserved.test', 'A'), ('second.test', 'A')])
        self.assertEqual(result['errors'], ['TIMEOUT'])
        self.assertEqual(self.child.call_count, 1)

    def test_no_raw_exceptions_exported(self):
        self.capture.side_effect = RuntimeError('SECRET username /private/path')
        result = self.execute()
        self.assertEqual(result['errors'], ['SESSION_FAILED'])
        self.assertNotIn('SECRET', json.dumps(result))

    def test_cli_pipe_rejected(self):
        output = io.StringIO()
        code = m.run(['--target-ref', 'target'], incoming=io.StringIO('APPROVE\n'),
                     prompt=io.StringIO(), outgoing=output)
        self.assertEqual(code, 2)
        self.assertIn('LIVE_TERMINAL_REQUIRED', output.getvalue())
        self.capture.assert_not_called()

    def test_cli_no_yes_or_dns_or_import_options(self):
        for option in ('--yes', '--request', '--dns', '--restore-grants'):
            with self.subTest(option=option):
                output = io.StringIO()
                self.assertEqual(m.run(['--target-ref', 'target', option], outgoing=output), 2)
        self.capture.assert_not_called()

    def test_cli_explicit_new_save_only(self):
        with tempfile.TemporaryDirectory() as directory, patch.object(m.TerminalConsent, '__call__', return_value=True):
            path = str(Path(directory).resolve() / 'preview.html')
            output = io.StringIO()
            self.assertEqual(m.run(['--target-ref', 'target', '--dashboard-output', path], outgoing=output), 0)
            original = Path(path).read_text(encoding="utf-8")
            self.assertIn('<html', original)
            self.assertEqual(m.run(['--target-ref', 'target', '--dashboard-output', path], outgoing=io.StringIO()), 2)
            self.assertEqual(Path(path).read_text(encoding="utf-8"), original)
        self.child.assert_not_called()


class WindowsSessionTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m.sys, 'platform', 'win32'))
        self.stack.enter_context(patch('socket.getaddrinfo', side_effect=AssertionError('No DNS')))
        self.stack.enter_context(patch('subprocess.Popen', side_effect=AssertionError('No process')))
        self.mac = self.stack.enter_context(patch.object(m.native_context, 'capture_current_context', side_effect=AssertionError('No Mac API')))
        self.capture = self.stack.enter_context(patch.object(m.windows_native_context, 'capture_current_context', return_value=object()))
        self.recheck = self.stack.enter_context(patch.object(m.windows_native_context, 'recheck_context', return_value={}))
        self.stack.enter_context(patch.object(m.windows_native_context, 'describe_context', return_value={
            'platform': 'win32', 'coverage': 'owned_process_current_thread_session_only',
            'desktop_user_relation': 'unknown', 'binding_state': 'blocked',
            'blocking_reason': 'CONSOLE_ACCOUNT_EQUALITY_UNPROVEN', 'gate_state': 'closed'}))
        self.probe = self.stack.enter_context(patch.object(m.os_dns_probe, 'probe_os_dns', side_effect=AssertionError('No Mac DNS')))
        self.consent = Mock(return_value=True)

    def test_windows_metadata_route_preserves_unknown_binding(self):
        result = m.execute('windows-target', consent=self.consent)
        self.assertEqual(result['status'], 'partial')
        self.assertEqual(result['report']['facts'][0]['value'], 'windows')
        self.assertEqual(result['context']['desktop_user_relation'], 'unknown')
        self.assertEqual(result['context']['binding_state'], 'blocked')
        self.assertEqual(result['gate_state'], 'closed')
        self.assertEqual(result['changes'], [])
        self.assertEqual(result['dns_availability'], 'blocked_windows_session_dns_integration_unavailable')
        self.assertIn('owned_process_token_identity', self.consent.call_args.args[0]['scope'])
        self.assertNotIn('primary_console_session', self.consent.call_args.args[0]['scope'])
        self.mac.assert_not_called()
        self.probe.assert_not_called()

    def test_windows_requested_dns_never_reaches_mac_probe(self):
        binding = m.os_dns_probe.Binding('windows-target', 'u', 'n', 'darwin', '/p', '/')
        host = m.DNSHost(binding, Mock(return_value=True), Mock(return_value=True), Mock(return_value=True))
        result = m.execute('windows-target', consent=self.consent, dns_host=host,
                           queries=[('reserved.test', 'A')])
        self.assertEqual(result['errors'], ['WINDOWS_SESSION_DNS_UNAVAILABLE'])
        self.assertEqual(result['status'], 'blocked')
        self.assertEqual(self.consent.call_count, 1)
        self.probe.assert_not_called()
        host.verify_binding.assert_not_called()

    def test_windows_decline_and_cancel_do_not_capture(self):
        self.consent.return_value = False
        result = m.execute('windows-target', consent=self.consent)
        self.assertEqual(result['status'], 'cancelled')
        self.capture.assert_not_called()
        result = m.execute('windows-target', consent=self.consent, cancelled=lambda: True)
        self.assertEqual(result['status'], 'cancelled')
        self.capture.assert_not_called()

    def test_windows_native_failures_are_sanitized(self):
        for code in ('CONTEXT_INACTIVE_OR_REMOTE', 'CONTEXT_FOREIGN', 'CLEANUP_FAILED', 'PERMISSION_DENIED'):
            with self.subTest(code=code):
                self.capture.side_effect = m.windows_native_context.ContextError(code)
                result = m.execute('windows-target', consent=self.consent)
                self.assertEqual(result['errors'], [code])
                self.assertEqual(result['status'], 'blocked')
                self.assertEqual(result['report']['facts'], [])

    def test_windows_continuity_change_stops(self):
        self.recheck.side_effect = m.windows_native_context.ContextError('CONTEXT_CHANGED')
        result = m.execute('windows-target', consent=self.consent)
        self.assertEqual(result['errors'], ['CONTEXT_CHANGED'])
        self.assertEqual(result['probe_evidence']['samples'], [])


class WindowsOutputPathTests(unittest.TestCase):
    def test_bad_windows_save_path_rejected_before_collection_or_open(self):
        with patch.object(m.sys, 'platform', 'win32'), \
                patch.object(m, 'execute', side_effect=AssertionError('No collection')) as execute, \
                patch.object(m.guardian, 'save_new', side_effect=AssertionError('No save')) as save:
            for path in (r'C:\approved\NUL', r'C:\approved\session.html:extra'):
                code = m.run(['--target-ref', 'target', '--dashboard-output', path], outgoing=io.StringIO())
                self.assertEqual(code, 2)
            execute.assert_not_called()
            save.assert_not_called()


class WindowsTerminalTests(unittest.TestCase):
    def setUp(self):
        self.stack = ExitStack()
        self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(m.os, 'name', 'nt'))
        self.console = Mock()
        self.stack.enter_context(patch.dict(sys.modules, {'msvcrt': self.console}))
        incoming = Mock()
        incoming.fileno.return_value = 0
        incoming.isatty.return_value = True
        self.prompt = io.StringIO()
        self.prompt.isatty = lambda: True
        self.consent = m.TerminalConsent(incoming, self.prompt)

    def test_windows_exact_fresh_nonce_response(self):
        self.console.kbhit.side_effect = [False] + [True] * 40
        self.console.getwch.side_effect = list('APPROVE fresh\r')
        with patch.object(m.secrets, 'token_hex', return_value='fresh'):
            self.assertTrue(self.consent({'operation': 'local'}))
        self.assertIn('APPROVE fresh', self.prompt.getvalue())

    def test_windows_typeahead_is_discarded_and_old_nonce_rejected(self):
        queued = 'APPROVE old\r'
        self.console.kbhit.side_effect = [True] * len(queued) + [False] + [True] * 40
        self.console.getwch.side_effect = list(queued + 'APPROVE old\r')
        with patch.object(m.secrets, 'token_hex', return_value='fresh'):
            self.assertFalse(self.consent({'operation': 'local'}))

    def test_windows_excessive_queue_rejected(self):
        self.console.kbhit.return_value = True
        self.console.getwch.return_value = 'x'
        with self.assertRaisesRegex(m.SessionError, 'DECLINED'):
            self.consent({'operation': 'local'})
        self.assertEqual(self.console.getwch.call_count, 80)

    def test_windows_queue_drain_deadline(self):
        self.console.kbhit.return_value = True
        with patch.object(m.time, 'monotonic', side_effect=[0, 1]):
            with self.assertRaisesRegex(m.SessionError, 'CONSENT_TIMEOUT'):
                self.consent({'operation': 'local'})
        self.console.getwch.assert_not_called()

    def test_windows_partial_input_times_out(self):
        self.console.kbhit.return_value = False
        with patch.object(m.time, 'monotonic', side_effect=[0, 2]), patch.object(m.time, 'sleep'):
            with self.assertRaisesRegex(m.SessionError, 'CONSENT_TIMEOUT'):
                self.consent._read_windows_line(1)

    def test_windows_controls_fail_closed(self):
        self.console.kbhit.return_value = True
        for char in ('\x00', '\xe0', '\x1b', '\x1a'):
            self.console.getwch.return_value = char
            self.assertEqual(self.consent._read_windows_line(time.monotonic() + 1), '')
        self.console.getwch.return_value = '\x03'
        with self.assertRaises(KeyboardInterrupt):
            self.consent._read_windows_line(time.monotonic() + 1)

    def test_windows_bad_or_reversed_clock_fails_closed(self):
        self.console.kbhit.return_value = False
        for values in ([float('nan')], [True], [10**1000], [2, 1]):
            with self.subTest(values=str(values)[:30]):
                self.consent._last_time = None
                with patch.object(m.time, 'monotonic', side_effect=values), patch.object(m.time, 'sleep'):
                    with self.assertRaisesRegex(m.SessionError, 'CONSENT_TIMEOUT'):
                        self.consent._read_windows_line(10)

    def test_huge_timeout_rejected_without_overflow(self):
        with self.assertRaisesRegex(m.SessionError, 'INPUT_INVALID'):
            m.TerminalConsent(timeout=10**1000)

    def test_windows_nonstandard_input_descriptor_rejected(self):
        self.consent.incoming.fileno.return_value = 7
        with self.assertRaisesRegex(m.SessionError, 'LIVE_TERMINAL_REQUIRED'):
            self.consent({'operation': 'local'})
        self.console.getwch.assert_not_called()


@unittest.skipUnless(os.name == 'posix', 'POSIX terminal adapter only')
class TerminalTests(unittest.TestCase):
    def test_fresh_nonce_every_prompt_and_exact_response(self):
        incoming, prompt = Mock(), io.StringIO()
        incoming.isatty.return_value = True
        incoming.fileno.return_value = 5
        prompt.isatty = lambda: True
        consent = m.TerminalConsent(incoming, prompt)
        with patch('termios.tcflush'), patch.object(m.secrets, 'token_hex', side_effect=['first', 'second']), \
                patch.object(consent, '_read_line', side_effect=['APPROVE first\n', 'APPROVE first\n']):
            self.assertTrue(consent({'operation': 'local'}))
            self.assertFalse(consent({'operation': 'dns'}))
        self.assertIn('APPROVE second', prompt.getvalue())

    def test_real_read_wait_is_bounded_with_partial_input(self):
        reader, writer = os.pipe()
        self.addCleanup(os.close, writer)
        with os.fdopen(reader, 'rb', buffering=0) as incoming:
            os.write(writer, b'APPROVE partial')
            consent = m.TerminalConsent(incoming, io.StringIO())
            with self.assertRaisesRegex(m.SessionError, 'CONSENT_TIMEOUT'):
                consent._read_line(time.monotonic() + .02)

    def test_delayed_matching_reply_cannot_approve(self):
        incoming, prompt = Mock(), Mock()
        incoming.isatty.return_value = prompt.isatty.return_value = True
        consent = m.TerminalConsent(incoming, prompt, timeout=1)
        with patch('termios.tcflush'), patch.object(m.secrets, 'token_hex', return_value='fresh'), \
                patch.object(consent, '_read_line', return_value='APPROVE fresh\n'), \
                patch.object(m.time, 'monotonic', side_effect=[0, 2]):
            with self.assertRaisesRegex(m.SessionError, 'CONSENT_TIMEOUT'):
                consent({'operation': 'local'})


class ImportTests(unittest.TestCase):
    def test_import_has_no_authority_or_io(self):
        with patch('socket.getaddrinfo', side_effect=AssertionError()), \
                patch('subprocess.Popen', side_effect=AssertionError()), \
                patch.object(m.native_context, 'capture_current_context', side_effect=AssertionError()):
            importlib.reload(m)


if __name__ == '__main__':
    unittest.main()
