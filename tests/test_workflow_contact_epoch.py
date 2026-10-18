"""Synthetic ENV-T81/89 contact-review subgap tests, not native acceptance.

Native-looking bindings, adapters and evidence below are host fixtures only.
No network, client, process, system setting or real approval is exercised.
"""
from copy import copy, deepcopy
from dataclasses import asdict, replace
import importlib.util
import json
from pathlib import Path
import pickle
import sys
import unittest


PATH = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/workflow_guard.py'
spec = importlib.util.spec_from_file_location('workflow_contact_epoch', PATH)
w = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = w
spec.loader.exec_module(w)


class ContactEpochTests(unittest.TestCase):
    def setUp(self):
        self.binding = w.Binding('device', 'user', 'native', 'profile', 'cfg', 'net', 'v1')
        self.requirements = w.Requirements(('network', 'protection'), ('client-path',), ('auth-path',))
        self.ready = w.Readiness('complete', (), (), ())
        self.local = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
        self.plan = replace(self.local, operation=w.Operation.PLAN, action='recovery-plan')
        self.neutral = replace(self.local, operation=w.Operation.PROBE, action='neutral-probe',
                               contact=w.Contact.NEUTRAL, endpoint_refs=('approved-neutral',))
        self.client = replace(self.local, operation=w.Operation.VERIFY, action='client-check',
                              contact=w.Contact.CLAUDE)
        self.login = replace(self.client, action='login-handoff', contact=w.Contact.LOGIN_HANDOFF)
        self.payment = replace(self.client, action='payment-handoff', contact=w.Contact.PAYMENT_HANDOFF)
        self.adapters = tuple(w.AdapterSupport(s, 'accepted', 'implemented', 'native_pass', 'fixture')
                              for s in (self.local, self.plan, self.neutral, self.client, self.login, self.payment))
        self.requests = []
        self.guard = self.new_guard()
        self.old_evidence = tuple(w.Evidence(check, stage, self.binding, 10, 100,
                                             w.EvidenceKind.TARGET_NATIVE, 'pass')
                                  for stage, checks in (
                                      (w.CheckStage.PRECONTACT, self.requirements.precontact),
                                      (w.CheckStage.CLIENT_UNAUTHENTICATED, self.requirements.client_unauthenticated),
                                      (w.CheckStage.CLIENT_AUTHENTICATED, self.requirements.client_authenticated))
                                  for check in checks)

    def approve(self, request):
        self.requests.append(request)
        return w.Reply.APPROVED

    def new_guard(self):
        # The elapsed-approval clock deliberately has another origin from now.
        return w.WorkflowGuard(self.binding, self.requirements, self.adapters,
                               self.approve, clock=lambda: 777)

    def action(self, scope=None, **changes):
        return replace(w.Action(scope or self.client, self.binding, 'plan', 10, 100,
                                permissions_verified=True), **changes)

    def handoff(self, evidence=None, phase=w.Phase.PC1, guard=None):
        guard = guard or self.guard
        scopes = (self.client,) if phase is w.Phase.PC1 else (self.client, self.login, self.payment)
        return guard.transition(phase, scopes, self.ready,
                                self.old_evidence if evidence is None else evidence, 20)

    def reviewed_evidence(self, guard=None):
        # Simulates a NEW scoped host review at time 20. Merely retagging old
        # production records would violate the host contract, not prove review.
        guard = guard or self.guard
        return tuple(replace(e, observed_at=20, contact_epoch=guard.contact_epoch)
                     for e in self.old_evidence)

    def reviewed_action(self, scope=None, **changes):
        return self.action(scope, facts_at=20, facts_contact_epoch=self.guard.contact_epoch, **changes)

    def recover_pc1(self):
        if self.guard.state.phase is not w.Phase.PC0:
            self.guard.rebind(self.binding)
        evidence = self.reviewed_evidence()
        self.assertTrue(self.handoff(evidence).allowed)
        return evidence

    def test_incident_old_evidence_fresh_approval_cannot_reopen(self):
        self.guard.record_observed_contact()
        decision = self.handoff()
        self.assertFalse(decision.allowed)
        self.assertIn('EVIDENCE_REQUIRED:network', decision.gaps)
        self.assertEqual(self.requests, [])
        self.assertEqual(self.guard.state.gate, w.GateState.REVOKED)
        self.assertEqual(self.guard.state.observed_contact, 'observed')

    def test_fresh_timestamps_without_current_epoch_do_not_recover(self):
        self.guard.record_observed_contact()
        self.assertFalse(self.handoff(tuple(replace(e, observed_at=20) for e in self.old_evidence)).allowed)
        self.assertEqual(self.requests, [])

    def test_equal_clock_reviewed_evidence_and_action_can_recover(self):
        self.guard.record_observed_contact()
        evidence = self.recover_pc1()
        self.assertTrue(self.guard.evaluate(self.reviewed_action(), self.ready, evidence, 20).allowed)
        self.assertEqual([r.purpose for r in self.requests], ['handoff:controlled_contact', 'action:verify'])
        self.assertEqual(self.guard.state.observed_contact, 'observed')

    def test_new_evidence_does_not_refresh_old_action_facts(self):
        self.guard.record_observed_contact()
        evidence = self.recover_pc1()
        calls = len(self.requests)
        for action in (self.action(), self.action(facts_at=20)):
            result = self.guard.evaluate(action, self.ready, evidence, 20)
            self.assertIn('CONTACT_FACTS_REVALIDATION_REQUIRED', result.gaps)
        self.assertEqual(len(self.requests), calls)

    def test_same_binding_rebind_cannot_clear_incident_barrier(self):
        self.guard.record_observed_contact()
        evidence = self.reviewed_evidence()
        epoch = self.guard.contact_epoch
        self.guard.rebind(self.binding)
        self.assertIsNot(self.guard.contact_epoch, epoch)
        self.assertFalse(self.handoff().allowed)
        self.assertFalse(self.handoff(evidence).allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence()).allowed)
        self.assertEqual(self.guard.state.observed_contact, 'observed')

    def test_rebind_away_and_back_keeps_barrier_and_binding_checks(self):
        self.guard.record_observed_contact()
        evidence = self.reviewed_evidence()
        self.guard.rebind(replace(self.binding, target='other-device'))
        self.assertFalse(self.handoff(self.reviewed_evidence()).allowed)
        self.guard.rebind(self.binding)
        self.assertFalse(self.handoff(evidence).allowed)
        self.assertFalse(self.handoff().allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence()).allowed)

    def test_resume_rotates_review_identity_and_retains_history(self):
        self.guard.record_observed_contact()
        evidence = self.recover_pc1()
        epoch = self.guard.contact_epoch
        saved = self.guard.snapshot()
        saved.update(contact_epoch=epoch, approved=True)
        self.guard.resume(saved)
        self.assertIsNot(self.guard.contact_epoch, epoch)
        self.assertFalse(self.handoff(evidence).allowed)
        self.assertFalse(self.handoff().allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence()).allowed)
        self.assertEqual(self.guard.state.observed_contact, 'previous_contact_reported')

    def test_benign_or_empty_resume_cannot_erase_existing_barrier(self):
        for saved in (None, {}, {'phase': 'precontact', 'observed_contact': 'not_measured'}):
            self.setUp()
            self.guard.record_observed_contact()
            epoch = self.guard.contact_epoch
            self.guard.resume(saved)
            self.assertIsNotNone(self.guard.contact_epoch)
            self.assertIsNot(self.guard.contact_epoch, epoch)
            self.assertFalse(self.handoff().allowed)
            self.assertNotEqual(self.guard.state.observed_contact, 'not_measured')

    def test_cross_instance_resume_cannot_reuse_prior_instance_epoch(self):
        self.guard.record_observed_contact()
        evidence = self.recover_pc1()
        prior_epoch = self.guard.contact_epoch
        saved = self.guard.snapshot()
        saved['contact_epoch'] = prior_epoch
        other = self.new_guard()
        other.resume(saved)
        self.assertIsNot(other.contact_epoch, prior_epoch)
        self.assertFalse(self.handoff(evidence, guard=other).allowed)
        self.assertFalse(self.handoff(guard=other).allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence(other), guard=other).allowed)

    def test_resuming_previously_authorized_contact_also_requires_review(self):
        self.assertTrue(self.handoff().allowed)
        other = self.new_guard()
        other.resume(self.guard.snapshot())
        self.assertIsNotNone(other.contact_epoch)
        self.assertFalse(self.handoff(guard=other).allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence(other), guard=other).allowed)

    def test_second_incident_invalidates_recovered_evidence_and_facts(self):
        self.guard.record_observed_contact()
        evidence = self.recover_pc1()
        action = self.reviewed_action()
        self.guard.record_observed_contact()
        self.assertIsNot(self.guard.contact_epoch, action.facts_contact_epoch)
        self.assertFalse(self.guard.evaluate(action, self.ready, evidence, 20).allowed)
        self.guard.rebind(self.binding)
        self.assertFalse(self.handoff(evidence).allowed)
        fresh = self.recover_pc1()
        self.assertIn('CONTACT_FACTS_REVALIDATION_REQUIRED',
                      self.guard.evaluate(action, self.ready, fresh, 20).gaps)

    def test_copied_fabricated_and_serialized_epoch_values_do_not_match(self):
        class EqualToAnything:
            def __eq__(self, other):
                return True
        self.guard.record_observed_contact()
        epoch = self.guard.contact_epoch
        for other in (None, 1, 'contact-review-epoch', object(), w._ContactEpoch(),
                      EqualToAnything(), copy(epoch), deepcopy(epoch), pickle.loads(pickle.dumps(epoch))):
            evidence = tuple(replace(e, contact_epoch=other) for e in self.reviewed_evidence())
            self.assertFalse(self.handoff(evidence).allowed)
        self.assertEqual(self.requests, [])
        evidence = self.recover_pc1()
        for other in (None, object(), EqualToAnything(), deepcopy(epoch)):
            self.assertIn('CONTACT_FACTS_REVALIDATION_REQUIRED',
                          self.guard.evaluate(replace(self.reviewed_action(), facts_contact_epoch=other),
                                              self.ready, evidence, 20).gaps)

    def test_old_epoch_records_do_not_override_current_review(self):
        self.guard.record_observed_contact()
        evidence = self.reviewed_evidence()
        old_conflicts = tuple(replace(e, observed_at=20, result='fail') for e in self.old_evidence)
        old_future = replace(self.old_evidence[0], observed_at=21)
        self.assertTrue(self.handoff(evidence + old_conflicts + (old_future,)).allowed)

    def test_current_epoch_latest_failure_and_tied_conflict_still_deny(self):
        self.guard.record_observed_contact()
        evidence = self.reviewed_evidence()
        for result in ('fail', 'unknown', 'skipped', 'blocked'):
            failed = replace(evidence[0], result=result)
            self.assertFalse(self.handoff(evidence + (failed,)).allowed)
            earlier = tuple(replace(e, observed_at=19) for e in evidence)
            self.assertFalse(self.handoff(earlier + (failed,)).allowed)
        earlier_failed = replace(evidence[0], observed_at=19, result='fail')
        self.assertTrue(self.handoff(evidence + (earlier_failed,)).allowed)

    def test_new_epoch_does_not_bypass_evidence_type_stage_or_time(self):
        self.guard.record_observed_contact()
        evidence = self.reviewed_evidence()
        for updates in ({'expires_at': 20}, {'observed_at': 21}, {'observed_at': float('nan')},
                        {'kind': w.EvidenceKind.SYNTHETIC}, {'kind': w.EvidenceKind.CI},
                        {'stage': w.CheckStage.CLIENT_UNAUTHENTICATED}):
            self.assertFalse(self.handoff(tuple(replace(e, **updates) for e in evidence)).allowed)
        self.assertEqual(self.requests, [])

    def test_pc2_and_payment_require_each_applicable_current_stage(self):
        self.guard.record_observed_contact()
        current = self.recover_pc1()
        pre_only = tuple(e for e in current if e.stage is w.CheckStage.PRECONTACT)
        old_client = tuple(e for e in self.old_evidence if e.stage is not w.CheckStage.PRECONTACT)
        self.assertFalse(self.handoff(pre_only + old_client, phase=w.Phase.PC2).allowed)
        unauth = tuple(e for e in current if e.stage is not w.CheckStage.CLIENT_AUTHENTICATED)
        self.assertTrue(self.handoff(unauth, phase=w.Phase.PC2).allowed)
        self.assertTrue(self.guard.evaluate(self.reviewed_action(self.login), self.ready, unauth, 20).allowed)
        payment = self.reviewed_action(self.payment, review_ref='purchase-review')
        self.assertFalse(self.guard.evaluate(payment, self.ready, unauth + old_client, 20).allowed)
        self.assertTrue(self.guard.evaluate(payment, self.ready, current, 20).allowed)

    def test_local_audit_plan_and_neutral_recovery_remain_available(self):
        self.guard.record_observed_contact()
        for scope in (self.local, self.plan):
            self.assertTrue(self.guard.evaluate(self.action(scope), w.Readiness(), (), 20).allowed)
        self.assertTrue(self.guard.evaluate(self.action(self.neutral), self.ready, (), 20).allowed)
        self.assertEqual(self.guard.state.gate, w.GateState.REVOKED)
        self.assertFalse(self.guard.evaluate(self.action(self.neutral), w.Readiness(), (), 20).allowed)

    def test_cancelled_recovery_does_not_approve_or_rotate_review(self):
        self.guard.record_observed_contact()
        epoch = self.guard.contact_epoch
        current = self.reviewed_evidence()
        for reply in (w.Reply.CANCELLED, w.Reply.DENIED, w.Reply.TIMEOUT, None, True):
            self.guard.authorize = lambda request: reply
            self.assertFalse(self.handoff(current).allowed)
            self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)
            self.assertIs(self.guard.contact_epoch, epoch)
        self.guard.authorize = self.approve
        self.assertTrue(self.handoff(current).allowed)

    def test_mutation_during_handoff_or_action_approval_denies_outer_request(self):
        for action_call in (False, True):
            for mutation in ('incident', 'rebind', 'resume', 'revoke'):
                self.setUp()
                self.guard.record_observed_contact()
                evidence = self.recover_pc1() if action_call else self.reviewed_evidence()
                action = self.reviewed_action()
                def mutate(request):
                    if mutation == 'incident':
                        self.guard.record_observed_contact()
                    elif mutation == 'rebind':
                        self.guard.rebind(self.binding)
                    elif mutation == 'resume':
                        self.guard.resume(self.guard.snapshot())
                    else:
                        self.guard.revoke()
                    return w.Reply.APPROVED
                self.guard.authorize = mutate
                result = (self.guard.evaluate(action, self.ready, evidence, 20)
                          if action_call else self.handoff(evidence))
                self.assertIn('APPROVAL_CONTEXT_CHANGED', result.gaps)
                self.assertNotEqual(self.guard.state.gate, w.GateState.OPEN)

    def test_reentrant_fresh_handoff_is_not_overwritten_by_old_approval(self):
        calls = []
        def approve(request):
            calls.append(request)
            if len(calls) == 1:
                self.guard.record_observed_contact()
                self.guard.rebind(self.binding)
                self.assertTrue(self.handoff(self.reviewed_evidence()).allowed)
            return w.Reply.APPROVED
        self.guard.authorize = approve
        self.assertIn('APPROVAL_CONTEXT_CHANGED', self.handoff().gaps)
        self.assertEqual(len(calls), 2)
        self.assertEqual(self.guard.state.gate, w.GateState.OPEN)
        self.assertEqual(self.guard.state.observed_contact, 'observed')

    def test_review_started_before_incident_cannot_finish_under_new_epoch(self):
        self.guard.record_observed_contact()
        in_flight = self.reviewed_evidence()
        self.guard.record_observed_contact()
        completed_later = tuple(replace(e, observed_at=20) for e in in_flight)
        self.assertFalse(self.handoff(completed_later).allowed)
        self.assertTrue(self.handoff(self.reviewed_evidence()).allowed)

    def test_current_review_still_expires_while_approval_waits(self):
        self.guard.record_observed_contact()
        evidence = tuple(replace(e, expires_at=21) for e in self.reviewed_evidence())
        ticks = iter((777, 779))
        self.guard._clock = lambda: next(ticks)
        self.assertFalse(self.handoff(evidence).allowed)
        self.assertEqual(self.guard.state.gate, w.GateState.CLOSED)

    def test_snapshot_requests_and_repr_do_not_export_identity(self):
        self.guard.record_observed_contact()
        epoch = self.guard.contact_epoch
        evidence = self.recover_pc1()
        action = self.reviewed_action()
        self.assertTrue(self.guard.evaluate(action, self.ready, evidence, 20).allowed)
        snapshot = self.guard.snapshot()
        self.assertEqual(set(snapshot), {'phase', 'gate_state', 'observed_contact', 'runtime_permission_restorable'})
        encoded = json.dumps(snapshot)
        self.assertNotIn('epoch', encoded)
        self.assertEqual(repr(epoch), '<contact-review-epoch>')
        for item in (action, evidence[0], self.requests[-1]):
            self.assertNotIn('contact_epoch', repr(item))
            self.assertNotIn(hex(id(epoch)), repr(item))
        self.assertNotIn('contact_epoch', asdict(self.requests[-1]))
        copied = asdict(evidence[0])
        self.assertIsNot(copied['contact_epoch'], epoch)
        with self.assertRaises(TypeError):
            json.dumps(copied)
        with self.assertRaises(TypeError):
            json.dumps(epoch)

    def test_no_incident_legacy_positional_calls_and_copying_still_work(self):
        self.assertIsNone(self.guard.contact_epoch)
        evidence = w.Evidence('network', w.CheckStage.PRECONTACT, self.binding, 10, 100,
                              w.EvidenceKind.TARGET_NATIVE, 'pass')
        action = w.Action(self.client, self.binding, 'plan', 10, 100, '', True, w.Recovery())
        self.assertIsNone(evidence.contact_epoch)
        self.assertIsNone(action.facts_contact_epoch)
        self.assertEqual(deepcopy(evidence), evidence)
        self.assertEqual(deepcopy(action), action)
        self.assertIsNone(asdict(evidence)['contact_epoch'])
        self.assertIsNone(asdict(action)['facts_contact_epoch'])
        self.assertTrue(self.handoff().allowed)
        self.assertTrue(self.guard.evaluate(action, self.ready, self.old_evidence, 20).allowed)


if __name__ == '__main__':
    unittest.main()
