"""Synthetic policy tests; no native support or human consent is established."""
from dataclasses import replace
import importlib.util
from pathlib import Path
import sys
import unittest

from environment_entry_fixture import local_entry

PATH = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/workflow_guard.py'
spec = importlib.util.spec_from_file_location('workflow_guard', PATH)
w = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = w
spec.loader.exec_module(w)


class WorkflowTests(unittest.TestCase):
    def setUp(self):
        self.binding = w.Binding('mac', 'user', 'native', 'browser-profile', 'cfg-1', 'net-1', 'v1')
        self.requirements = w.Requirements(('network', 'protection'), ('client-path',), ('authenticated-path',))
        self.ready = w.Readiness('complete', (), (), (), local_entry(self.binding.target))
        self.local = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
        self.neutral = replace(self.local, operation=w.Operation.PROBE, action='neutral-probe',
                               contact=w.Contact.NEUTRAL, endpoint_refs=('approved-endpoint',))
        self.client = replace(self.local, operation=w.Operation.VERIFY, action='client-check', contact=w.Contact.CLAUDE)
        self.login = replace(self.client, action='official-login-handoff', contact=w.Contact.LOGIN_HANDOFF)
        self.payment = replace(self.client, action='payment-handoff', contact=w.Contact.PAYMENT_HANDOFF)
        self.change = replace(self.local, operation=w.Operation.APPLY, action='patch', risk=w.Risk.CHANGE)
        self.scopes = (self.local, self.neutral, self.client, self.login, self.payment, self.change)
        self.adapters = tuple(w.AdapterSupport(s, 'accepted', 'implemented', 'native_pass', 'validation-1') for s in self.scopes)
        self.requests = []
        self.reply = w.Reply.APPROVED
        def approve(request):
            self.requests.append(request)
            return self.reply
        self.guard = w.WorkflowGuard(self.binding, self.requirements, self.adapters, approve)
        self.evidence = tuple(w.Evidence(check, stage, self.binding, 10, 100, w.EvidenceKind.TARGET_NATIVE, 'pass')
                              for stage, checks in ((w.CheckStage.PRECONTACT, self.requirements.precontact),
                                                    (w.CheckStage.CLIENT_UNAUTHENTICATED, self.requirements.client_unauthenticated),
                                                    (w.CheckStage.CLIENT_AUTHENTICATED, self.requirements.client_authenticated)) for check in checks)

    def action(self, scope=None, **kwargs):
        return replace(w.Action(scope or self.local, self.binding, 'plan-1', 10, 100,
                                permissions_verified=True), **kwargs)

    def evaluate(self, action=None, evidence=None, ready=None, now=20):
        return self.guard.evaluate(action or self.action(), ready or self.ready,
                                   self.evidence if evidence is None else evidence, now)

    def pc1(self, evidence=None):
        return self.guard.transition(w.Phase.PC1, (self.client,), self.ready,
                                     self.evidence if evidence is None else evidence, 20)

    def pc2(self):
        return self.guard.transition(w.Phase.PC2, (self.client, self.login, self.payment), self.ready, self.evidence, 20)

    def test_closed_by_default_and_no_execution(self):
        self.assertEqual(self.guard.state.phase, w.Phase.PC0)
        self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)
        self.assertFalse(self.evaluate().executes)
        self.assertEqual(self.evaluate().enforcement_level, 'workflow_guard')

    def test_selected_target_audit_can_continue_with_other_interview_gaps(self):
        self.assertEqual(self.evaluate(ready=w.Readiness()).gaps, ('ENVIRONMENT_ENTRY_REQUIRED',))
        self.assertEqual(self.requests, [])
        incomplete = w.Readiness(entry_request=local_entry(self.binding.target))
        self.assertTrue(self.evaluate(ready=incomplete).allowed)
        self.assertFalse(self.evaluate(self.action(self.neutral), ready=incomplete).allowed)

    def test_neutral_consent_does_not_open_contact(self):
        self.assertTrue(self.evaluate(self.action(self.neutral)).allowed)
        self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)

    def test_pc1_narrow_handoff_and_live_action_approval(self):
        self.assertTrue(self.pc1().allowed)
        self.assertTrue(self.evaluate(self.action(self.client)).allowed)
        self.assertEqual(len(self.requests), 2)
        self.assertEqual(self.requests[-1].scopes, (self.client,))
        self.reply = w.Reply.DENIED
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)

    def test_exact_plan_presented_each_time(self):
        self.evaluate(self.action(plan_ref='plan-a', review_ref='review-a'))
        self.evaluate(self.action(plan_ref='plan-b', review_ref='review-b'))
        self.assertEqual([r.plan_ref for r in self.requests], ['plan-a', 'plan-b'])
        self.assertEqual(self.requests[-1].review_ref, 'review-b')

    def test_no_handoff_on_missing_stale_future_or_other_target_evidence(self):
        for evidence in ((), tuple(replace(e, expires_at=19) for e in self.evidence),
                         tuple(replace(e, observed_at=21) for e in self.evidence),
                         tuple(replace(e, binding=replace(self.binding, target='windows')) for e in self.evidence)):
            with self.subTest(evidence=evidence):
                self.assertFalse(self.pc1(evidence).allowed)
        self.assertFalse(self.requests)

    def test_ci_synthetic_and_unknown_results_cannot_open_gate(self):
        for updates in ({'kind': w.EvidenceKind.CI}, {'kind': w.EvidenceKind.SYNTHETIC},
                        {'result': 'unknown'}, {'result': 'skipped'}, {'result': 'fail'}):
            self.assertFalse(self.pc1(tuple(replace(e, **updates) for e in self.evidence)).allowed)

    def test_client_tests_cannot_satisfy_precontact(self):
        self.assertFalse(self.pc1(tuple(replace(e, stage=w.CheckStage.CLIENT_UNAUTHENTICATED)
                                       for e in self.evidence)).allowed)

    def test_no_authentication_cycle_and_pending_checks_reported(self):
        unauth = tuple(e for e in self.evidence if e.stage is not w.CheckStage.CLIENT_AUTHENTICATED)
        first = self.pc1(unauth)
        self.assertTrue(first.allowed)
        self.assertIn('authenticated-path', first.pending_checks)
        second = self.guard.transition(w.Phase.PC2, (self.login, self.payment), self.ready, unauth, 20)
        self.assertTrue(second.allowed)
        self.assertTrue(self.evaluate(self.action(self.login), evidence=unauth).allowed)
        self.assertFalse(self.evaluate(self.action(self.payment, review_ref='quote-1'), evidence=unauth).allowed)

    def test_pc2_requires_unauthenticated_checks(self):
        self.assertTrue(self.pc1().allowed)
        only_pre = tuple(e for e in self.evidence if e.stage is w.CheckStage.PRECONTACT)
        self.assertFalse(self.guard.transition(w.Phase.PC2, (self.login,), self.ready, only_pre, 20).allowed)

    def test_pc1_cannot_include_login_or_authenticated_checks(self):
        for scope in (self.login, self.payment, replace(self.client, requires_authentication=True)):
            self.assertFalse(self.guard.transition(w.Phase.PC1, (scope,), self.ready, self.evidence, 20).allowed)

    def test_cancel_denied_unknown_timeout_silence_bool_fail_closed(self):
        for reply in (w.Reply.CANCELLED, w.Reply.DENIED, w.Reply.UNKNOWN, w.Reply.TIMEOUT, None, True, 'approved'):
            self.reply = reply
            self.assertFalse(self.pc1().allowed)
            self.assertEqual(self.guard.state.phase, w.Phase.PC0)
            self.assertFalse(self.evaluate().allowed)

    def test_callback_missing_and_failure(self):
        self.guard.authorize = None
        self.assertIn('HOST_APPROVAL_UNAVAILABLE', self.evaluate().gaps)
        def broken(request):
            raise RuntimeError('private host error must not leak')
        self.guard.authorize = broken
        self.assertEqual(self.evaluate().gaps, ('HOST_APPROVAL_FAILED',))

    def test_old_saved_approval_never_restores_permission(self):
        self.pc1()
        saved = self.guard.snapshot()
        saved.update(approved=True, gate_state='open_scoped')
        self.guard.resume(saved)
        self.assertEqual(self.guard.state.phase, w.Phase.PC0)
        self.assertEqual(self.guard.state.observed_contact, 'previous_contact_reported')
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)

    def test_each_binding_dimension_invalidates_evidence_and_permissions(self):
        for key in self.binding.__dict__:
            with self.subTest(key=key):
                self.pc1()
                self.guard.rebind(replace(self.binding, **{key: 'changed'}))
                self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)
                self.assertFalse(self.pc1().allowed)
                self.assertFalse(self.evaluate().allowed)
                self.guard.rebind(self.binding)

    def test_stale_facts_nonfinite_timestamps(self):
        for changes in ({'facts_expires_at': 20}, {'facts_at': 21}, {'facts_at': float('nan')},
                        {'facts_expires_at': float('inf')}, {'facts_at': True}):
            self.assertIn('STALE_OR_INVALID_FACTS', self.evaluate(self.action(**changes)).gaps)

    def test_revoke_stops_new_contact(self):
        self.pc1()
        self.guard.revoke()
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)
        self.assertFalse(self.pc2().allowed)

    def test_operation_version_install_product_and_platform_scope_exact(self):
        for key, value in (('operation', w.Operation.APPLY), ('version', 'v2'), ('installation', 'store'),
                           ('product', 'other'), ('platform', 'windows'), ('action', 'different'),
                           ('module', 'ENV-02'), ('endpoint_refs', ('other-endpoint',))):
            self.assertIn('UNSUPPORTED_OPERATION_SCOPE', self.evaluate(self.action(replace(self.local, **{key: value}))).gaps)

    def test_accepted_design_and_implemented_do_not_mean_validated(self):
        for status in ('not_run', 'synthetic_pass', 'ci_pass', 'unknown'):
            self.guard.adapters = (replace(self.adapters[0], validation_status=status),)
            self.assertFalse(self.evaluate().allowed)
            self.assertFalse(self.guard.supported_scopes())

    def test_changes_require_exact_review_and_recovery(self):
        self.assertFalse(self.evaluate(self.action(self.change)).allowed)
        recovery = w.Recovery(True, True)
        self.assertTrue(self.evaluate(self.action(self.change, review_ref='diff-1', recovery=recovery)).allowed)
        self.assertFalse(self.evaluate(self.action(self.change, review_ref='diff-1', recovery=w.Recovery(True, False))).allowed)

    def test_control_channel_requires_independent_rescue(self):
        scope = replace(self.change, risk=w.Risk.CONTROL_CHANNEL)
        self.guard.adapters += (replace(self.adapters[-1], scope=scope),)
        action = self.action(scope, review_ref='diff-1', recovery=w.Recovery(True, True))
        self.assertIn('INDEPENDENT_OFFLINE_RESCUE_REQUIRED', self.evaluate(action).gaps)
        self.assertTrue(self.evaluate(replace(action, recovery=w.Recovery(True, True, True))).allowed)

    def test_rollback_preserves_later_changes(self):
        scope = replace(self.change, operation=w.Operation.ROLLBACK)
        self.guard.adapters += (replace(self.adapters[-1], scope=scope),)
        action = self.action(scope, review_ref='diff-1', recovery=w.Recovery(True, True))
        self.assertIn('LATER_CHANGES_NOT_PROTECTED', self.evaluate(action).gaps)
        self.assertTrue(self.evaluate(replace(action, recovery=w.Recovery(True, True, False, True))).allowed)

    def test_irreversible_is_handoff_only(self):
        scope = replace(self.change, risk=w.Risk.IRREVERSIBLE)
        self.guard.adapters += (replace(self.adapters[-1], scope=scope),)
        self.assertIn('IRREVERSIBLE_HANDOFF_REQUIRED', self.evaluate(self.action(scope, review_ref='diff-1', recovery=w.Recovery(True, True))).gaps)

    def test_payment_requires_separate_current_approval_and_review(self):
        self.pc1(); self.pc2()
        self.assertFalse(self.evaluate(self.action(self.payment)).allowed)
        self.assertTrue(self.evaluate(self.action(self.payment, review_ref='quote-current')).allowed)
        self.assertEqual(self.requests[-1].scopes, (self.payment,))
        self.assertFalse(self.evaluate(self.action(self.payment, review_ref='quote-current'), now=101).allowed)

    def test_g1_g2_and_contact_gates_are_independent(self):
        for ready in (replace(self.ready, g1_status='partial'), replace(self.ready, g1_status='paused'),
                      replace(self.ready, g1_status='emergency_deferred'), replace(self.ready, g2_gaps=('route',)),
                      replace(self.ready, conflicts=('network',))):
            self.assertFalse(self.guard.transition(w.Phase.PC1, (self.client,), ready, self.evidence, 20).allowed)
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)

    def test_required_manifest_and_opaque_references(self):
        with self.assertRaisesRegex(ValueError, 'INVALID_REQUIREMENTS'):
            w.WorkflowGuard(self.binding, w.Requirements())
        with self.assertRaisesRegex(ValueError, 'INVALID_REQUIREMENTS'):
            w.WorkflowGuard(self.binding, w.Requirements(('same',), ('same',)))
        with self.assertRaisesRegex(ValueError, 'INVALID_BINDING'):
            w.WorkflowGuard(replace(self.binding, target='https://example.com'), self.requirements)
        self.assertFalse(self.evaluate(self.action(plan_ref='curl https://example.com')).allowed)
        self.assertFalse(self.evaluate(self.action(replace(self.local, action='rm -rf /'))).allowed)

    def test_malformed_public_inputs_return_closed_decisions(self):
        for action in (None, {}, replace(self.action(), recovery=None),
                       replace(self.action(), binding=None), replace(self.action(), scope=None)):
            result = self.guard.evaluate(action, self.ready, self.evidence, 20)
            self.assertFalse(result.allowed)
            self.assertIn('INVALID_ACTION', result.gaps)
        for ready, evidence, now in ((None, self.evidence, 20), (self.ready, None, 20),
                                    (self.ready, ({},), 20), (self.ready, self.evidence, float('nan')),
                                    (replace(self.ready, g2_gaps=None), self.evidence, 20)):
            self.assertFalse(self.guard.evaluate(self.action(), ready, evidence, now).allowed)
            self.assertFalse(self.guard.transition(w.Phase.PC1, (self.client,), ready, evidence, now).allowed)
        self.assertFalse(self.requests)

    def test_observed_contact_revokes_and_never_erases_history(self):
        self.pc1()
        self.guard.record_observed_contact()
        self.assertEqual(self.guard.state.gate, w.GateState.REVOKED)
        self.assertFalse(self.evaluate(self.action(self.client)).allowed)
        self.guard.rebind(self.binding)
        self.assertEqual(self.guard.state.observed_contact, 'observed')
        self.assertEqual(self.guard.state.phase, w.Phase.PC0)

    def test_local_audit_cannot_hide_network_action(self):
        scope = replace(self.local, contact=w.Contact.NEUTRAL, endpoint_refs=('endpoint',))
        self.guard.adapters += (replace(self.adapters[0], scope=scope),)
        self.assertIn('OFFLINE_OPERATION_REQUIRED', self.evaluate(self.action(scope)).gaps)

    def test_change_cannot_claim_read_risk(self):
        scope = replace(self.change, risk=w.Risk.READ)
        self.guard.adapters += (replace(self.adapters[0], scope=scope),)
        self.assertIn('CHANGE_RISK_REQUIRED', self.evaluate(self.action(scope)).gaps)

    def test_missing_endpoints_and_os_permission(self):
        scope = replace(self.neutral, endpoint_refs=())
        self.guard.adapters += (replace(self.adapters[0], scope=scope),)
        self.assertIn('EXACT_ENDPOINTS_REQUIRED', self.evaluate(self.action(scope)).gaps)
        self.assertIn('HOST_OS_PERMISSION_REQUIRED', self.evaluate(self.action(permissions_verified=False)).gaps)

    def test_handoff_approval_cannot_override_revocation(self):
        def approve(request):
            self.guard.revoke()
            return w.Reply.APPROVED
        self.guard.authorize = approve
        result = self.pc1()
        self.assertIn('APPROVAL_CONTEXT_CHANGED', result.gaps)
        self.assertEqual(self.guard.state.gate, w.GateState.REVOKED)
        self.assertEqual(self.guard.state.phase, w.Phase.PC0)

    def test_handoff_approval_cannot_cross_target_during_callback(self):
        other = replace(self.binding, target='other-device')
        def approve(request):
            self.assertEqual(request.binding, self.binding)
            self.guard.rebind(other)
            return w.Reply.APPROVED
        self.guard.authorize = approve
        self.assertIn('APPROVAL_CONTEXT_CHANGED', self.pc1().gaps)
        self.assertEqual(self.guard.binding, other)
        self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)

    def test_action_approval_cannot_override_revocation_or_rebind(self):
        for mutation in ('revoke', 'rebind', 'resume', 'record_observed_contact'):
            self.setUp()
            self.assertTrue(self.pc1().allowed)
            def approve(request):
                if mutation == 'rebind':
                    self.guard.rebind(replace(self.binding, target='other-device'))
                elif mutation == 'resume':
                    self.guard.resume(self.guard.snapshot())
                else:
                    getattr(self.guard, mutation)()
                return w.Reply.APPROVED
            self.guard.authorize = approve
            with self.subTest(mutation=mutation):
                self.assertIn('APPROVAL_CONTEXT_CHANGED', self.evaluate(self.action(self.client)).gaps)
                self.assertNotEqual(self.guard.state.gate, w.GateState.OPEN)

    def test_rebind_away_and_back_still_invalidates_approval(self):
        def approve(request):
            self.guard.rebind(replace(self.binding, target='other-device'))
            self.guard.rebind(self.binding)
            return w.Reply.APPROVED
        self.guard.authorize = approve
        self.assertIn('APPROVAL_CONTEXT_CHANGED', self.pc1().gaps)

    def test_changed_adapter_registry_during_approval_is_rejected(self):
        def approve(request):
            self.guard.adapters = ()
            return w.Reply.APPROVED
        self.guard.authorize = approve
        self.assertIn('APPROVAL_CONTEXT_CHANGED', self.evaluate().gaps)

    def test_handoff_evidence_expiring_while_approval_waits_is_rejected(self):
        ticks = iter((0, 81))
        self.guard._clock = lambda: next(ticks)
        self.assertFalse(self.pc1().allowed)
        self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)

    def test_action_facts_expiring_while_approval_waits_are_rejected(self):
        ticks = iter((0, 81))
        self.guard._clock = lambda: next(ticks)
        self.assertIn('STALE_OR_INVALID_FACTS', self.evaluate().gaps)

    def test_contact_evidence_rechecked_after_action_approval(self):
        self.pc1()
        ticks = iter((0, 81))
        self.guard._clock = lambda: next(ticks)
        result = self.evaluate(self.action(self.client, facts_expires_at=1000))
        self.assertIn('EVIDENCE_REQUIRED:network', result.gaps)

    def test_invalid_approval_clock_fails_closed(self):
        for values in ((2, 1), (0, float('nan')), (True, 2)):
            ticks = iter(values)
            self.guard._clock = lambda: next(ticks)
            self.assertIn('APPROVAL_CLOCK_INVALID', self.evaluate().gaps)

    def test_latest_authoritative_evidence_supersedes_old_pass(self):
        for result in ('fail', 'unknown', 'skipped', 'blocked'):
            newer = replace(self.evidence[0], observed_at=19, result=result)
            self.assertFalse(self.pc1(self.evidence + (newer,)).allowed)
        expired = replace(self.evidence[0], observed_at=19, expires_at=20)
        self.assertFalse(self.pc1(self.evidence + (expired,)).allowed)

    def test_tied_evidence_conflict_denies_but_newer_pass_can_recover(self):
        failed = replace(self.evidence[0], result='fail')
        self.assertFalse(self.pc1(self.evidence + (failed,)).allowed)
        recovered = replace(self.evidence[0], observed_at=19)
        self.assertTrue(self.pc1(self.evidence + (failed, recovered)).allowed)

    def test_direct_pc2_unknown_transitions_rejected(self):
        self.assertFalse(self.pc2().allowed)
        self.assertFalse(self.guard.transition('PC1', (self.client,), self.ready, self.evidence, 20).allowed)


if __name__ == '__main__':
    unittest.main()
