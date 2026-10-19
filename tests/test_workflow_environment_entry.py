"""Synthetic entry/workflow boundary tests; no native actions or real consent."""
from dataclasses import replace
import importlib.util
import json
from pathlib import Path
import sys
import unittest


PATH = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts/workflow_guard.py'
spec = importlib.util.spec_from_file_location('workflow_environment_entry', PATH)
w = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = w
spec.loader.exec_module(w)


def entry_request(target='device', route='local', proxy=False):
    targets = [{'role': route, 'target_ref': target}]
    if route == 'vm':
        targets = [{'role': 'vm_host', 'target_ref': 'host'},
                   {'role': 'vm_guest', 'target_ref': target}]
    request = {
        'schema_version': 'guardian-environment-entry-input/0.1',
        'route': {'choice': route, 'state': 'selected'},
        'targets': targets,
        'network': {'possession': 'none', 'selection': 'direct',
                    'configuration': 'not_applicable', 'path': 'direct'},
        'local_entry': {'kind': 'none'},
        'final_egress': {'kind': 'direct', 'protocol': 'unknown'},
        'client': 'claude_code',
    }
    if proxy:
        request['network'] = {'possession': 'present', 'selection': 'selected',
                              'configuration': 'effective', 'path': 'explicit',
                              'resource_ref': 'resource-a'}
        request['local_entry'] = {'kind': 'mixed', 'entry_ref': 'entry-a'}
        request['final_egress'] = {'kind': 'proxy', 'protocol': 'socks5'}
    return request


class WorkflowEnvironmentEntryTests(unittest.TestCase):
    def setUp(self):
        self.binding = w.Binding('device', 'user', 'native', 'profile', 'cfg', 'net', 'v1')
        self.requirements = w.Requirements(('network',), ('client-path',), ('auth-path',))
        self.ready = w.Readiness('complete', (), (), (), entry_request())
        self.audit = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
        self.plan = replace(self.audit, operation=w.Operation.PLAN, action='offline-plan')
        self.probe = replace(self.audit, operation=w.Operation.PROBE, action='probe',
                             contact=w.Contact.NEUTRAL, endpoint_refs=('endpoint',))
        self.verify = replace(self.audit, operation=w.Operation.VERIFY, action='local-verify')
        self.client = replace(self.verify, action='client-verify', contact=w.Contact.CLAUDE)
        self.login = replace(self.client, action='login', contact=w.Contact.LOGIN_HANDOFF)
        self.apply = replace(self.audit, operation=w.Operation.APPLY, action='apply', risk=w.Risk.CHANGE)
        self.rollback = replace(self.apply, operation=w.Operation.ROLLBACK, action='restore-receipt')
        self.requests = []
        self.reply = w.Reply.APPROVED
        self.guard = w.WorkflowGuard(self.binding, self.requirements, (), self.approve, clock=lambda: 1000)
        for scope in (self.audit, self.plan, self.probe, self.verify, self.client,
                      self.login, self.apply, self.rollback):
            self.support(scope)
        self.evidence = tuple(w.Evidence(check, stage, self.binding, 10, 100,
                                         w.EvidenceKind.TARGET_NATIVE, 'pass')
                              for stage, checks in (
                                  (w.CheckStage.PRECONTACT, self.requirements.precontact),
                                  (w.CheckStage.CLIENT_UNAUTHENTICATED, self.requirements.client_unauthenticated),
                                  (w.CheckStage.CLIENT_AUTHENTICATED, self.requirements.client_authenticated))
                              for check in checks)

    def approve(self, request):
        self.requests.append(request)
        return self.reply

    def support(self, scope):
        self.guard.adapters += (w.AdapterSupport(scope, 'accepted', 'implemented', 'native_pass', 'fixture'),)
        return scope

    def action(self, scope=None, **changes):
        return replace(w.Action(scope or self.audit, self.binding, 'existing-plan', 10, 100,
                                review_ref='exact-review', permissions_verified=True,
                                recovery=w.Recovery(True, True, True, True)), **changes)

    def evaluate(self, scope=None, readiness=None, action=None):
        return self.guard.evaluate(action or self.action(scope),
                                   self.ready if readiness is None else readiness, self.evidence, 20)

    def handoff(self, readiness=None, phase=w.Phase.PC1, scopes=None):
        return self.guard.transition(phase, scopes or ((self.client,) if phase is w.Phase.PC1 else (self.login,)),
                                     self.ready if readiness is None else readiness, self.evidence, 20)

    def test_original_readiness_positions_and_explanation_gaps_are_unchanged(self):
        readiness = w.Readiness('complete', (), (), ())
        self.assertTrue(readiness.valid())
        self.assertIsNone(readiness.entry_request)
        self.assertEqual(readiness.gaps(), ())
        self.assertEqual(w.Readiness().gaps(), ('G1_INCOMPLETE', 'G2_INCOMPLETE'))

    def test_missing_entry_blocks_every_new_target_action_before_approval(self):
        readiness = replace(self.ready, entry_request=None)
        for scope in (self.audit, self.probe, self.verify, self.client, self.apply):
            with self.subTest(operation=scope.operation, contact=scope.contact):
                decision = self.evaluate(scope, readiness)
                self.assertFalse(decision.allowed)
                self.assertIn('ENVIRONMENT_ENTRY_REQUIRED', decision.gaps)
        self.assertEqual(self.requests, [])

    def test_missing_entry_blocks_handoff_despite_complete_evidence(self):
        decision = self.handoff(replace(self.ready, entry_request=None))
        self.assertEqual(decision.gaps, ('ENVIRONMENT_ENTRY_REQUIRED',))
        self.assertEqual(self.requests, [])
        self.assertIs(self.guard.state.gate, w.GateState.CLOSED)

    def test_unknown_unselected_and_withdrawn_routes_never_start_audit(self):
        for state in ('unasked', 'unknown', 'declined', 'conflict', 'stale', 'withdrawn'):
            request = entry_request()
            request['route']['state'] = state
            ready = replace(self.ready, entry_request=request)
            self.assertIn('EXPLICIT_CURRENT_ROUTE_SELECTION_REQUIRED', self.evaluate(readiness=ready).gaps)
            self.assertFalse(self.handoff(ready).allowed)
        self.assertEqual(self.requests, [])

    def test_malformed_unknown_schema_and_saved_assessment_fail_closed(self):
        wrong_schema = entry_request()
        wrong_schema['schema_version'] = 'guardian-environment-entry-input/999'
        saved_result = w._entry.assess_entry(entry_request())
        forged = entry_request()
        forged['approved'] = True
        for request in ({}, wrong_schema, saved_result, forged, True, 'ready'):
            decision = self.evaluate(readiness=replace(self.ready, entry_request=request))
            self.assertEqual(decision.gaps, ('INVALID_ENVIRONMENT_ENTRY',))
        self.assertEqual(self.requests, [])

    def test_selected_route_target_must_match_existing_binding_alias(self):
        for route in ('local', 'vm', 'vps'):
            ready = replace(self.ready, entry_request=entry_request('other', route))
            self.assertIn('REQUESTED_TARGET_NOT_IN_CURRENT_ROUTE', self.evaluate(readiness=ready).gaps)
        self.assertEqual(self.requests, [])

    def test_vm_target_declaration_does_not_replace_full_host_binding(self):
        ready = replace(self.ready, entry_request=entry_request(route='vm'))
        self.assertTrue(self.evaluate(readiness=ready).allowed)
        for field in self.binding.__dict__:
            bad = self.action(binding=replace(self.binding, **{field: 'other'}))
            self.assertIn('TARGET_BINDING_MISMATCH', self.evaluate(readiness=ready, action=bad).gaps)

    def test_only_pure_local_read_plan_can_skip_route_selection(self):
        self.assertTrue(self.evaluate(self.plan, w.Readiness()).allowed)
        withdrawn = entry_request()
        withdrawn['route']['state'] = 'withdrawn'
        self.assertTrue(self.evaluate(self.plan, w.Readiness(entry_request=withdrawn)).allowed)
        for changes in ({'risk': w.Risk.CHANGE}, {'endpoint_refs': ('endpoint',)},
                        {'requires_authentication': True}, {'contact': w.Contact.NEUTRAL}):
            scope = self.support(replace(self.plan, **changes))
            decision = self.evaluate(scope, w.Readiness())
            self.assertIn('ENVIRONMENT_ENTRY_REQUIRED', decision.gaps)
            self.assertFalse(decision.allowed)

    def test_pure_plan_retains_exact_scope_permissions_and_approval(self):
        for changes, code in (({'permissions_verified': False}, 'HOST_OS_PERMISSION_REQUIRED'),
                              ({'plan_ref': ''}, 'EXACT_PLAN_REQUIRED'),
                              ({'facts_expires_at': 20}, 'STALE_OR_INVALID_FACTS')):
            self.assertIn(code, self.evaluate(readiness=w.Readiness(), action=self.action(self.plan, **changes)).gaps)
        self.reply = w.Reply.CANCELLED
        self.assertIn('CURRENT_EXACT_APPROVAL_REQUIRED', self.evaluate(self.plan, w.Readiness()).gaps)

    def test_selected_route_allows_offline_precheck_before_network_is_ready(self):
        request = entry_request(proxy=True)
        request['network'].update(possession='unknown', selection='unknown', configuration='unknown', path='unknown')
        ready = w.Readiness(entry_request=request)
        for scope in (self.audit,):
            self.assertTrue(self.evaluate(scope, ready).allowed)
        complete = replace(self.ready, entry_request=request)
        self.assertTrue(self.evaluate(self.verify, complete).allowed)
        self.assertFalse(self.evaluate(self.probe, complete).allowed)
        self.assertFalse(self.evaluate(self.apply, complete).allowed)
        self.assertFalse(self.handoff(complete).allowed)

    def test_owned_resource_does_not_mean_configuration_is_ready_for_probe(self):
        request = entry_request(proxy=True)
        request['network']['configuration'] = 'absent'
        ready = replace(self.ready, entry_request=request)
        self.assertTrue(self.evaluate(self.audit, ready).allowed)
        self.assertTrue(self.evaluate(self.apply, ready).allowed)
        self.assertFalse(self.evaluate(self.probe, ready).allowed)
        self.assertFalse(self.handoff(ready).allowed)

    def test_imported_configuration_allows_separate_probe_approval(self):
        request = entry_request(proxy=True)
        request['network']['configuration'] = 'imported'
        ready = replace(self.ready, entry_request=request)
        self.assertTrue(self.evaluate(self.probe, ready).allowed)
        self.assertIs(self.guard.state.gate, w.GateState.CLOSED)
        self.reply = w.Reply.DENIED
        self.assertIn('CURRENT_EXACT_APPROVAL_REQUIRED', self.evaluate(self.probe, ready).gaps)

    def test_entry_eligibility_never_substitutes_for_action_or_contact_permissions(self):
        self.guard.authorize = None
        self.assertEqual(self.evaluate().gaps, ('HOST_APPROVAL_UNAVAILABLE',))
        self.assertIn('CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE', self.evaluate(self.client).gaps)
        self.assertIn('HOST_OS_PERMISSION_REQUIRED', self.evaluate(action=self.action(permissions_verified=False)).gaps)
        self.guard.adapters = ()
        self.assertIn('UNSUPPORTED_OPERATION_SCOPE', self.evaluate().gaps)

    def test_vps_basic_entry_cannot_be_used_for_configuration_even_with_contact_scope(self):
        ready = replace(self.ready, entry_request=entry_request(route='vps'))
        self.assertTrue(self.evaluate(self.audit, ready).allowed)
        self.assertTrue(self.evaluate(self.probe, ready).allowed)
        contact_apply = self.support(replace(self.apply, contact=w.Contact.CLAUDE))
        for scope in (self.apply, contact_apply):
            self.assertIn('VPS_CONFIGURATION_OUTSIDE_BASIC_CHECK_SCOPE', self.evaluate(scope, ready).gaps)
        self.assertIn('VPS_CONFIGURATION_OUTSIDE_BASIC_CHECK_SCOPE', self.handoff(ready, scopes=(contact_apply,)).gaps)

    def test_route_withdrawal_invalidates_existing_contact_grant(self):
        self.assertTrue(self.handoff().allowed)
        self.ready.entry_request['route']['state'] = 'withdrawn'
        decision = self.evaluate(self.client)
        self.assertFalse(decision.allowed)
        self.assertIn('EXPLICIT_CURRENT_ROUTE_SELECTION_REQUIRED', decision.gaps)
        self.assertIs(self.guard.state.phase, w.Phase.PC1)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)
        self.assertIsNotNone(self.guard.contact_epoch)
        self.assertEqual(len(self.requests), 1)

    def test_missing_malformed_or_changed_target_also_revokes_existing_grant(self):
        for mutation in ('missing', 'malformed', 'target'):
            self.setUp()
            self.assertTrue(self.handoff().allowed)
            if mutation == 'missing':
                ready = replace(self.ready, entry_request=None)
            elif mutation == 'malformed':
                ready = replace(self.ready, entry_request={})
            else:
                self.ready.entry_request['targets'][0]['target_ref'] = 'other'
                ready = self.ready
            self.assertFalse(self.evaluate(self.client, ready).allowed)
            self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_equally_eligible_changed_resource_invalidates_grant(self):
        self.ready = replace(self.ready, entry_request=entry_request(proxy=True))
        self.assertTrue(self.handoff().allowed)
        self.ready.entry_request['network']['resource_ref'] = 'resource-b'
        decision = self.evaluate(self.client)
        self.assertIn('ENVIRONMENT_ENTRY_CHANGED', decision.gaps)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_route_change_before_pc2_invalidates_pc1_grant(self):
        self.assertTrue(self.handoff().allowed)
        ready = replace(self.ready, entry_request=entry_request(route='vm'))
        decision = self.handoff(ready, phase=w.Phase.PC2)
        self.assertIn('ENVIRONMENT_ENTRY_CHANGED', decision.gaps)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_handoff_rechecks_callback_route_withdrawal_and_target_mutation(self):
        for mutation in ('route', 'target'):
            self.setUp()
            def approve(request):
                if mutation == 'route':
                    self.ready.entry_request['route']['state'] = 'withdrawn'
                else:
                    self.ready.entry_request['targets'][0]['target_ref'] = 'other'
                return w.Reply.APPROVED
            self.guard.authorize = approve
            self.assertFalse(self.handoff().allowed)
            self.assertIs(self.guard.state.gate, w.GateState.CLOSED)
            self.assertIs(self.guard.state.phase, w.Phase.PC0)

    def test_callback_equally_eligible_resource_or_entry_change_requires_fresh_review(self):
        for handoff in (False, True):
            for field, value in (('network', 'resource-b'), ('local_entry', 'entry-b')):
                self.setUp()
                self.ready = replace(self.ready, entry_request=entry_request(proxy=True))
                def approve(request):
                    key = 'resource_ref' if field == 'network' else 'entry_ref'
                    self.ready.entry_request[field][key] = value
                    return w.Reply.APPROVED
                self.guard.authorize = approve
                decision = self.handoff() if handoff else self.evaluate(self.probe)
                self.assertEqual(decision.gaps, ('ENVIRONMENT_ENTRY_CHANGED',))
                self.assertIs(self.guard.state.gate, w.GateState.CLOSED)

    def test_contact_action_callback_withdrawal_revokes_existing_grant(self):
        self.assertTrue(self.handoff().allowed)
        def approve(request):
            self.ready.entry_request['route']['state'] = 'withdrawn'
            return w.Reply.APPROVED
        self.guard.authorize = approve
        self.assertFalse(self.evaluate(self.client).allowed)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_declined_callback_still_revokes_changed_entry(self):
        self.assertTrue(self.handoff().allowed)
        def approve(request):
            self.ready.entry_request['route']['state'] = 'withdrawn'
            return w.Reply.DENIED
        self.guard.authorize = approve
        self.assertEqual(self.evaluate(self.client).gaps, ('CURRENT_EXACT_APPROVAL_REQUIRED',))
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_failed_callback_or_invalid_clock_cannot_keep_withdrawn_entry_open(self):
        for failure in ('callback', 'clock'):
            self.setUp()
            self.assertTrue(self.handoff().allowed)
            def approve(request):
                self.ready.entry_request['route']['state'] = 'withdrawn'
                if failure == 'callback':
                    raise RuntimeError('host failure')
                return w.Reply.APPROVED
            self.guard.authorize = approve
            if failure == 'clock':
                ticks = iter((1000, 999))
                self.guard._clock = lambda: next(ticks)
            expected = 'HOST_APPROVAL_FAILED' if failure == 'callback' else 'APPROVAL_CLOCK_INVALID'
            self.assertEqual(self.evaluate(self.client).gaps, (expected,))
            self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_unrelated_invalid_action_does_not_revoke_grant(self):
        self.assertTrue(self.handoff().allowed)
        self.ready.entry_request['route']['state'] = 'withdrawn'
        action = self.action(self.client, binding=replace(self.binding, target='other'))
        self.assertIn('TARGET_BINDING_MISMATCH', self.evaluate(action=action).gaps)
        self.assertIs(self.guard.state.gate, w.GateState.OPEN)
        self.assertFalse(self.evaluate(self.client).allowed)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)

    def test_current_entry_must_not_restore_saved_grant(self):
        self.assertTrue(self.handoff().allowed)
        saved = self.guard.snapshot()
        self.assertNotIn('entry', json.dumps(saved))
        self.guard.resume(saved)
        self.assertFalse(self.evaluate(self.client).allowed)
        self.assertIs(self.guard.state.gate, w.GateState.CLOSED)

    def test_exact_local_receipt_recovery_survives_unanswered_or_withdrawn_questionnaire(self):
        withdrawn = entry_request()
        withdrawn['route']['state'] = 'withdrawn'
        for readiness in (w.Readiness(), w.Readiness('blocked', ('route',), ('network',),
                                                     ('conflict',), withdrawn)):
            decision = self.evaluate(self.rollback, readiness)
            self.assertTrue(decision.allowed, decision.gaps)
            self.assertEqual(self.requests[-1].purpose, 'action:rollback')
            self.assertEqual(self.requests[-1].plan_ref, 'existing-plan')
            self.assertFalse(decision.executes)
        self.assertIs(self.guard.state.gate, w.GateState.CLOSED)

    def test_recovery_keeps_every_existing_safety_requirement(self):
        cases = (
            ({'binding': replace(self.binding, target='other')}, 'TARGET_BINDING_MISMATCH'),
            ({'facts_expires_at': 20}, 'STALE_OR_INVALID_FACTS'),
            ({'plan_ref': ''}, 'EXACT_PLAN_REQUIRED'),
            ({'review_ref': ''}, 'EXACT_REVIEW_REQUIRED'),
            ({'permissions_verified': False}, 'HOST_OS_PERMISSION_REQUIRED'),
            ({'recovery': w.Recovery(False, True, True, True)}, 'VERIFIED_RECOVERY_REQUIRED'),
            ({'recovery': w.Recovery(True, False, True, True)}, 'VERIFIED_RECOVERY_REQUIRED'),
            ({'recovery': w.Recovery(True, True, True, False)}, 'LATER_CHANGES_NOT_PROTECTED'),
        )
        for changes, gap in cases:
            decision = self.evaluate(readiness=w.Readiness(), action=self.action(self.rollback, **changes))
            self.assertFalse(decision.allowed)
            self.assertIn(gap, decision.gaps)
        self.assertEqual(self.requests, [])
        self.guard.adapters = ()
        self.assertIn('UNSUPPORTED_OPERATION_SCOPE', self.evaluate(self.rollback, w.Readiness()).gaps)

    def test_recovery_requires_current_approval_and_post_approval_freshness(self):
        self.reply = w.Reply.CANCELLED
        self.assertEqual(self.evaluate(self.rollback, w.Readiness()).gaps, ('CURRENT_EXACT_APPROVAL_REQUIRED',))
        self.reply = w.Reply.APPROVED
        ticks = iter((1000, 1081))
        self.guard._clock = lambda: next(ticks)
        self.assertEqual(self.evaluate(self.rollback, w.Readiness()).gaps, ('STALE_OR_INVALID_FACTS',))

    def test_control_channel_recovery_still_requires_verified_offline_rescue(self):
        scope = self.support(replace(self.rollback, risk=w.Risk.CONTROL_CHANNEL))
        action = self.action(scope, recovery=w.Recovery(True, True, False, True))
        self.assertIn('INDEPENDENT_OFFLINE_RESCUE_REQUIRED', self.evaluate(readiness=w.Readiness(), action=action).gaps)
        self.assertTrue(self.evaluate(scope, w.Readiness()).allowed)

    def test_new_changes_network_recovery_and_irreversible_work_cannot_borrow_exemption(self):
        for scope in (self.apply,
                      self.support(replace(self.rollback, contact=w.Contact.NEUTRAL, endpoint_refs=('endpoint',))),
                      self.support(replace(self.rollback, endpoint_refs=('endpoint',))),
                      self.support(replace(self.rollback, requires_authentication=True)),
                      self.support(replace(self.rollback, risk=w.Risk.READ)),
                      self.support(replace(self.rollback, risk=w.Risk.IRREVERSIBLE))):
            decision = self.evaluate(scope, w.Readiness())
            self.assertFalse(decision.allowed)
            self.assertIn('ENVIRONMENT_ENTRY_REQUIRED', decision.gaps)
        self.assertEqual(self.requests, [])

    def test_recovery_does_not_clear_revoked_contact_or_open_new_contact(self):
        self.guard.record_observed_contact()
        epoch = self.guard.contact_epoch
        self.assertTrue(self.evaluate(self.rollback, w.Readiness()).allowed)
        self.assertIs(self.guard.state.gate, w.GateState.REVOKED)
        self.assertIs(self.guard.contact_epoch, epoch)
        self.assertFalse(self.evaluate(self.client).allowed)


if __name__ == '__main__':
    unittest.main()
