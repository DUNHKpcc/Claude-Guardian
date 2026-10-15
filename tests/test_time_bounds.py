"""Synthetic clock/input robustness; no native calls or device acceptance."""
import importlib.util
from dataclasses import replace
from pathlib import Path
import sys
import unittest
from unittest.mock import Mock, patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'


def load(name):
    spec = importlib.util.spec_from_file_location('time_bounds_' + name, SCRIPTS / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


listener = load('windows_listener_binding')
transactions = load('windows_transactions')
workflow = load('workflow_guard')
INVALID = (float('nan'), float('inf'), -float('inf'), True, 10**1000)


class ListenerTimeTests(unittest.TestCase):
    def run_listener(self, **kwargs):
        selected = listener.Selection('target', 'namespace', 'user', '127.0.0.1', 1234, 123, 456)
        reader = Mock()
        reader.observe.return_value = listener._Observation(456, True, (('127.0.0.1', 123),))
        return listener.verify_listener(selected, approve_read=lambda *a: True,
                verify_context=lambda *a: True, run_native=lambda call, *a: call(),
                _reader=reader, **kwargs)

    def test_invalid_clock_initial_and_later(self):
        for value in INVALID:
            for sequence in ([value] * 30, [100, 100, value] + [100] * 30):
                with self.subTest(value=type(value).__name__, later=sequence[0] == 100), patch.object(listener.time, 'monotonic', side_effect=sequence):
                    result = self.run_listener()
                    self.assertEqual(result['error_code'], 'NATIVE_READ_FAILED')
                    self.assertFalse(result['listener_owner_verified'])
                    self.assertEqual(result['execution_status'], 'blocked')

    def test_unrepresentable_deadline(self):
        for value in (1e308, -1e308):
            with patch.object(listener.time, 'monotonic', return_value=value):
                self.assertEqual(self.run_listener()['error_code'], 'NATIVE_READ_FAILED')

    def test_backwards_clock_even_above_start(self):
        for sequence in ([100, 99] + [99] * 30, [100, 101, 100.5] + [101] * 30):
            with patch.object(listener.time, 'monotonic', side_effect=sequence):
                self.assertEqual(self.run_listener()['error_code'], 'NATIVE_READ_FAILED')

    def test_budget_and_deadline(self):
        for value in INVALID:
            self.assertEqual(self.run_listener(budget=listener.Budget(max_seconds=value))['error_code'], 'INPUT_INVALID')
        with patch.object(listener.time, 'monotonic', side_effect=[100, 103]):
            self.assertEqual(self.run_listener()['error_code'], 'TIMEOUT')
        with patch.object(listener.time, 'monotonic', return_value=100):
            self.assertEqual(self.run_listener(cancelled=lambda: True)['error_code'], 'CANCELLED')
            self.assertEqual(self.run_listener()['execution_status'], 'completed')


class TransactionTimeTests(unittest.TestCase):
    def test_invalid_clocks(self):
        for value in INVALID:
            for sequence in ([value] * 10, [100] + [value] * 10):
                with patch.object(transactions.time, 'monotonic', side_effect=sequence):
                    with self.assertRaises(transactions.TransactionError) as caught:
                        transactions._Budget(10, None).check()
                    self.assertEqual(caught.exception.code, 'INVALID_BUDGET')
        for sequence in ([100, 99], [100, 101, 100.5]):
            with patch.object(transactions.time, 'monotonic', side_effect=sequence):
                with self.assertRaises(transactions.TransactionError) as caught:
                    transactions._Budget(10, None).check()
                self.assertEqual(caught.exception.code, 'INVALID_BUDGET')

    def test_unrepresentable_deadline(self):
        for value in (1e308, -1e308):
            with patch.object(transactions.time, 'monotonic', return_value=value):
                with self.assertRaises(transactions.TransactionError) as caught:
                    transactions._Budget(10, None)
                self.assertEqual(caught.exception.code, 'INVALID_BUDGET')

    def test_public_plan_and_preview_huge_expiry(self):
        path = '\\\\?\\Volume{12345678-1234-1234-1234-123456789abc}\\config'
        state = dict(volume_serial=1, file_id='0' * 32, attributes=0, size=0, links=1,
                     creation_time=0, access_time=0, write_time=0, change_time=0)
        snapshot = dict(state, sha256='0' * 64, security_sha256='0' * 64,
                        security_scope='owner_group_dacl_only', ancestors=[state])
        with patch.object(transactions, '_native_windows', return_value=True), \
                patch.object(transactions, '_read_snapshot', return_value=snapshot) as reader:
            with self.assertRaises(transactions.TransactionError) as caught:
                transactions.plan(path, b'', 'target', now=10**1000, exclusive_access=True)
            self.assertEqual(caught.exception.code, 'INVALID_EXPIRY')
            reader.assert_not_called()
            plan = transactions.plan(path, b'', 'target', now=100, exclusive_access=True)
        for field in ('created_at', 'expires_at'):
            with self.assertRaises(transactions.TransactionError) as caught:
                transactions.preview(dict(plan, **{field: 10**1000}))
            self.assertEqual(caught.exception.code, 'INVALID_PLAN')

    def test_public_backup_parser_rejects_invalid_clock(self):
        blob = (transactions._BACKUP_HEADER.pack(1, 0, 0, 0)
                + transactions._BACKUP_HEADER.pack(3, 0, 20, 0) + b'0' * 20)
        for sequence in ([100, 99] + [99] * 30, [float('nan')] * 30):
            with patch.object(transactions.time, 'monotonic', side_effect=sequence):
                with self.assertRaises(transactions.TransactionError) as caught:
                    transactions.inspect_backup_streams(blob, expected_size=0,
                        expected_sha256=transactions._hash(b''))
                self.assertEqual(caught.exception.code, 'INVALID_BUDGET')

    def test_cancellation_and_callback_time_count(self):
        for callback, sequence, code in ((lambda: True, [100, 100], 'CANCELLED'),
                                         (lambda: False, [100, 100, 110], 'TIMEOUT')):
            with patch.object(transactions.time, 'monotonic', side_effect=sequence):
                with self.assertRaises(transactions.TransactionError) as caught:
                    transactions._Budget(10, callback).check()
                self.assertEqual(caught.exception.code, code)


class WorkflowTimeTests(unittest.TestCase):
    def setUp(self):
        w = workflow
        self.binding = w.Binding('target', 'user', 'native', 'profile', 'cfg', 'net', 'v1')
        self.ready = w.Readiness('complete', (), (), ())
        self.scope = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
        self.client = replace(self.scope, operation=w.Operation.VERIFY, contact=w.Contact.CLAUDE)
        self.guard = w.WorkflowGuard(self.binding, w.Requirements(('network',), ('client',)),
            tuple(w.AdapterSupport(s, 'accepted', 'implemented', 'native_pass', 'validated')
                  for s in (self.scope, self.client)), lambda req: w.Reply.APPROVED, clock=lambda: 100)
        self.action = w.Action(self.scope, self.binding, 'plan', 10, 100, permissions_verified=True)
        self.evidence = w.Evidence('network', w.CheckStage.PRECONTACT, self.binding, 10, 100,
                                  w.EvidenceKind.TARGET_NATIVE, 'pass')

    def test_public_invalid_now_and_fact_times(self):
        for value in INVALID:
            self.assertEqual(self.guard.evaluate(self.action, self.ready, (), value).gaps, ('INVALID_CONTEXT',))
            for field in ('facts_at', 'facts_expires_at'):
                decision = self.guard.evaluate(replace(self.action, **{field: value}), self.ready, (), 20)
                self.assertIn('STALE_OR_INVALID_FACTS', decision.gaps)

    def test_public_invalid_evidence_times(self):
        for value in INVALID:
            for field in ('observed_at', 'expires_at'):
                decision = self.guard.transition(workflow.Phase.PC1, (self.client,), self.ready,
                    (replace(self.evidence, **{field: value}),), 20)
                self.assertIn('EVIDENCE_REQUIRED:network', decision.gaps)
                self.assertEqual(self.guard.state.gate, workflow.GateState.CLOSED)

    def test_approval_clock_invalid(self):
        for sequence in ([100, 99], [100, float('nan')], [100, 10**1000], [-1e308, 1e308], [-10**308, 10**308]):
            self.guard._clock = Mock(side_effect=sequence)
            decision = self.guard.evaluate(self.action, self.ready, (), 20.0)
            self.assertEqual(decision.gaps, ('APPROVAL_CLOCK_INVALID',))
