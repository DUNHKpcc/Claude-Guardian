"""Original ENV-T81 (L+C): exact offline eligibility replay, not native proof.

Host applicability, adapters, observations and consent replies are synthetic
fixtures. Full active-content review is in rebuild-required-controls-case.md.
The fail-fast I/O sentinels are test instrumentation, not OS isolation.
"""
from contextlib import contextmanager, ExitStack
from dataclasses import asdict, replace
from enum import Enum
import io
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import workflow_guard as w

FORBIDDEN_IO = ('builtins.open', 'io.open', 'os.open', 'socket.socket',
                'socket.create_connection', 'socket.getaddrinfo',
                'socket.gethostbyname', 'socket.gethostbyname_ex',
                'socket.gethostbyaddr', 'subprocess.Popen', 'os.system', 'os.popen')


@contextmanager
def offline_only():
    with ExitStack() as stack:
        mocks = [stack.enter_context(patch(name, side_effect=AssertionError(
            'forbidden fixture I/O: ' + name))) for name in FORBIDDEN_IO]
        yield
        for mock in mocks:
            mock.assert_not_called()


def plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


# Handwritten public fixture expectations, deliberately not derived from asdict
# of implementation outputs. New public fields therefore break these assertions.
EXPECTED_BINDING = {'target': 'device-a', 'user': 'user-a', 'namespace': 'native-a',
                    'profile': 'profile-a', 'configuration': 'config-a',
                    'network': 'network-a', 'runtime_version': 'runtime-a'}


def expected_scope(action, contact='claude', operation='verify'):
    return {'module': 'ENV-10', 'operation': operation, 'action': action,
            'product': 'fixture-client', 'version': 'v1',
            'installation': 'fixture-install', 'platform': 'fixture-platform',
            'contact': contact, 'risk': 'read', 'endpoint_refs': [],
            'requires_authentication': False}


EXPECTED_SCOPES = [expected_scope('offline-plan', 'local', 'plan'),
                   expected_scope('client-path'),
                   expected_scope('official-login', 'login_handoff'),
                   expected_scope('subscription-review', 'payment_handoff'),
                   expected_scope('gift-card-review', 'payment_handoff')]
PRE_GAPS = ('EVIDENCE_REQUIRED:target-path', 'EVIDENCE_REQUIRED:required-fault-blocking')
CLIENT_GAP = 'EVIDENCE_REQUIRED:client-path'
AUTH_GAP = 'EVIDENCE_REQUIRED:authenticated-path'
CONTROL_GAP = 'EVIDENCE_REQUIRED:required-fault-blocking'


class RequiredControlsTests(unittest.TestCase):
    def setUp(self):
        self.records = []
        self.binding = w.Binding('device-a', 'user-a', 'native-a', 'profile-a',
                                 'config-a', 'network-a', 'runtime-a')
        self.requirements = w.Requirements(('target-path', 'required-fault-blocking'),
                                          ('client-path',), ('authenticated-path',))
        self.ready = w.Readiness('complete', (), (), ())
        local = w.Scope('ENV-10', w.Operation.PLAN, 'offline-plan', 'fixture-client',
                        'v1', 'fixture-install', 'fixture-platform')
        client = replace(local, operation=w.Operation.VERIFY, action='client-path',
                         contact=w.Contact.CLAUDE)
        self.local, self.client = local, client
        self.login = replace(client, action='official-login', contact=w.Contact.LOGIN_HANDOFF)
        self.payment = replace(client, action='subscription-review', contact=w.Contact.PAYMENT_HANDOFF)
        # Host-classified user handoff only; this is not a gift-card classifier
        # or a payment executor, and does not invent card-purchase permission.
        self.gift_card = replace(self.payment, action='gift-card-review')
        self.scopes = (local, client, self.login, self.payment, self.gift_card)
        self.adapters = tuple(w.AdapterSupport(scope, 'accepted', 'implemented',
                              'native_pass', 'synthetic-adapter-declaration') for scope in self.scopes)
        self.requests = []
        self.reply = w.Reply.APPROVED
        self.guard = w.WorkflowGuard(self.binding, self.requirements, self.adapters,
                                     self.approve, clock=lambda: 777)
        self.evidence = tuple(w.Evidence(check, stage, self.binding, 10, 100,
                              w.EvidenceKind.TARGET_MANUAL, 'pass')
            for stage, checks in ((w.CheckStage.PRECONTACT, self.requirements.precontact),
                                  (w.CheckStage.CLIENT_UNAUTHENTICATED, self.requirements.client_unauthenticated),
                                  (w.CheckStage.CLIENT_AUTHENTICATED, self.requirements.client_authenticated))
            for check in checks)

    def reset_fixture(self):
        records = self.records
        self.setUp()
        self.records = records

    def approve(self, request):
        self.requests.append(plain(asdict(request)))
        return self.reply

    def action(self, scope, **changes):
        return replace(w.Action(scope, self.binding, 'plan-a', 10, 100,
                                review_ref='review-a', permissions_verified=True), **changes)

    def check(self, label, value, gaps=(), pending=()):
        actual = plain(asdict(value))
        self.assertEqual(actual, {'allowed': not gaps, 'gaps': list(gaps),
            'supported_scopes': EXPECTED_SCOPES, 'pending_checks': list(pending),
            'enforcement_level': 'workflow_guard', 'executes': False})
        self.records.append({'label': label, 'decision': actual})
        return actual

    def state_is(self, phase='precontact', gate='closed', history='not_measured', scopes=()):
        state = plain(asdict(self.guard.state))
        snapshot = self.guard.snapshot()
        self.assertEqual(state, {'phase': phase, 'gate': gate, 'scopes': list(scopes),
                                 'observed_contact': history})
        self.assertEqual(snapshot, {'phase': phase, 'gate_state': gate,
            'observed_contact': history, 'runtime_permission_restorable': False})
        self.records.append({'state': state, 'snapshot': snapshot})

    def pc1(self, evidence=None, readiness=None, now=20):
        return self.guard.transition(w.Phase.PC1, (self.client,), readiness or self.ready,
                                     self.evidence if evidence is None else evidence, now)

    def pc2(self, evidence=None, readiness=None):
        return self.guard.transition(w.Phase.PC2, (self.login, self.payment, self.gift_card),
                                     readiness or self.ready,
                                     self.evidence if evidence is None else evidence, 20)

    def evaluate(self, scope, evidence=None, readiness=None, **changes):
        return self.guard.evaluate(self.action(scope, **changes), readiness or self.ready,
                                   self.evidence if evidence is None else evidence, 20)

    def no_callbacks(self):
        self.assertEqual(self.requests, [])
        self.records.append({'approval_requests': []})

    def assert_blocked_before_contact(self, label, evidence, readiness, extra):
        self.check(label + ':PC1', self.pc1(evidence, readiness), extra)
        self.check(label + ':direct-PC2', self.pc2(evidence, readiness), ('INVALID_TRANSITION',))
        for scope in (self.client, self.login, self.payment, self.gift_card):
            gaps = (('G2_INCOMPLETE',) if readiness.g2_gaps else ()) + (
                ('KNOWN_CONFLICT',) if readiness.conflicts else ())
            gaps += ('CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE',)
            gaps += tuple(x for x in extra if x.startswith('EVIDENCE_REQUIRED:'))
            if scope is not self.client:
                gaps += ('PC2_REQUIRED',)
            self.check(label + ':' + scope.action, self.evaluate(scope, evidence, readiness), gaps)
        self.state_is()
        self.no_callbacks()

    def test_unknown_or_absent_mandatory_control_denies_every_contact_handoff(self):
        with offline_only():
            for result in ('unknown', 'skipped', 'not_applicable', 'blocked', 'fail'):
                evidence = self.evidence[:1] + (replace(self.evidence[1], result=result),) + self.evidence[2:]
                self.assert_blocked_before_contact(result, evidence, self.ready, (CONTROL_GAP,))
            self.assert_blocked_before_contact('absent', self.evidence[:1] + self.evidence[2:],
                                              self.ready, (CONTROL_GAP,))
            # Readiness cannot be used as an alternative to mandatory evidence.
            self.assertEqual(self.guard.requirements, self.requirements)

    def test_missing_required_control_in_readiness_is_not_an_optional_limit(self):
        with offline_only():
            ready = replace(self.ready, g2_gaps=('required-fault-blocking-unknown',))
            self.assert_blocked_before_contact('mandatory-readiness-gap', self.evidence,
                                              ready, ('G2_INCOMPLETE',))

    def test_scoped_direct_path_conflict_denies_even_with_old_passing_evidence(self):
        with offline_only():
            ready = replace(self.ready, conflicts=('device-a-profile-a-direct-path-observed',))
            self.assert_blocked_before_contact('scoped-direct-path', self.evidence,
                                              ready, ('KNOWN_CONFLICT',))
            # Scope is explicit host input, not an actual network observation.
            self.records.append({'host_conflicts': list(ready.conflicts),
                                 'binding': plain(asdict(self.binding))})
            self.assertEqual(plain(asdict(self.binding)), EXPECTED_BINDING)

    def test_latest_unknown_failed_expired_and_tied_records_never_resurrect_old_pass(self):
        with offline_only():
            for changes in ({'observed_at': 19, 'result': 'unknown'},
                            {'observed_at': 19, 'result': 'fail'},
                            {'observed_at': 19, 'expires_at': 20},
                            {'result': 'fail'}, {'observed_at': 21},
                            {'observed_at': float('nan')}):
                evidence = self.evidence + (replace(self.evidence[1], **changes),)
                # Both list orders must use authoritative time, not first pass.
                for records in (evidence, tuple(reversed(evidence))):
                    self.check('newer-or-tied-invalid-evidence', self.pc1(records), (CONTROL_GAP,))
            self.state_is()
            self.no_callbacks()

    def test_wrong_kind_stage_time_or_binding_cannot_satisfy_required_control(self):
        with offline_only():
            variants = [{'kind': w.EvidenceKind.SYNTHETIC}, {'kind': w.EvidenceKind.CI},
                        {'stage': w.CheckStage.CLIENT_UNAUTHENTICATED},
                        {'observed_at': 21}, {'expires_at': 20}]
            variants += [{'binding': replace(self.binding, **{key: 'changed'})}
                         for key in EXPECTED_BINDING]
            for changes in variants:
                evidence = self.evidence[:1] + (replace(self.evidence[1], **changes),) + self.evidence[2:]
                self.check('invalid-required-record', self.pc1(evidence), (CONTROL_GAP,))
            self.state_is()
            self.no_callbacks()

    def test_recorded_contact_revokes_and_old_passes_or_new_timestamps_do_not_reopen(self):
        with offline_only():
            self.guard.record_observed_contact()
            self.state_is(gate='revoked', history='observed')
            for records in (self.evidence, tuple(replace(e, observed_at=20) for e in self.evidence)):
                self.check('incident-PC1-old-review', self.pc1(records), PRE_GAPS)
                self.check('incident-direct-PC2', self.pc2(records), ('INVALID_TRANSITION',))
                for scope in (self.client, self.login, self.payment, self.gift_card):
                    gaps = ('CONTACT_FACTS_REVALIDATION_REQUIRED', 'CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE') + PRE_GAPS
                    if scope is not self.client:
                        gaps += ('PC2_REQUIRED', CLIENT_GAP)
                    if scope in (self.payment, self.gift_card):
                        gaps += (AUTH_GAP,)
                    self.check('incident-old-action:' + scope.action, self.evaluate(scope, records), gaps)
            self.state_is(gate='revoked', history='observed')
            self.no_callbacks()

    def test_same_binding_reset_and_saved_open_gate_cannot_restore_incident_passes(self):
        with offline_only():
            self.guard.record_observed_contact()
            self.guard.rebind(self.binding)
            self.state_is(history='observed')
            self.check('rebound-old-pass', self.pc1(), PRE_GAPS)
            self.guard.resume({'phase': 'authenticated_use', 'gate_state': 'open_scoped',
                               'approved': True, 'observed_contact': 'observed'})
            self.state_is(history='previous_contact_reported')
            self.check('resumed-old-pass', self.pc1(), PRE_GAPS)
            self.no_callbacks()

    def test_current_epoch_review_does_not_clear_unresolved_direct_path_conflict(self):
        with offline_only():
            self.guard.record_observed_contact()
            current = tuple(replace(e, observed_at=20, contact_epoch=self.guard.contact_epoch)
                            for e in self.evidence)
            ready = replace(self.ready, conflicts=('device-a-profile-a-direct-path-observed',))
            self.check('current-review-conflict-persists', self.pc1(current, ready), ('KNOWN_CONFLICT',))
            self.state_is(gate='revoked', history='observed')
            self.no_callbacks()

    def test_new_required_unknown_after_pc1_blocks_login_and_payment_without_callback(self):
        with offline_only():
            self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
            self.requests.clear()
            newer = self.evidence + (replace(self.evidence[1], observed_at=19, result='unknown'),)
            self.check('PC2-required-now-unknown', self.pc2(newer), (CONTROL_GAP,))
            for scope in (self.client, self.login, self.payment, self.gift_card):
                gaps = ('CONTACT_FACTS_REVALIDATION_REQUIRED', 'CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE') + PRE_GAPS
                if scope is not self.client:
                    gaps += ('PC2_REQUIRED', CLIENT_GAP)
                if scope in (self.payment, self.gift_card):
                    gaps += (AUTH_GAP,)
                self.check('required-now-unknown:' + scope.action, self.evaluate(scope, newer), gaps)
            # A prerequisite of the existing grant is no longer established.
            self.state_is('controlled_contact', 'revoked')
            self.no_callbacks()

    def test_exact_granted_action_invalidates_failed_current_grant_prerequisites(self):
        with offline_only():
            for phase in ('PC1', 'PC2'):
                for failure in ('unknown-precontact', 'conflict', 'readiness', 'unknown-client'):
                    self.reset_fixture()
                    self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
                    if phase == 'PC2':
                        self.check('fixture-PC2', self.pc2(), pending=('authenticated-path',))
                    records, ready = self.evidence, self.ready
                    if failure == 'unknown-precontact':
                        records += (replace(records[1], observed_at=19, result='unknown'),)
                        gaps = (CONTROL_GAP,)
                    elif failure == 'unknown-client':
                        records += (replace(records[2], observed_at=19, result='unknown'),)
                        gaps = () if phase == 'PC1' else (CLIENT_GAP,)
                    elif failure == 'conflict':
                        ready = replace(ready, conflicts=('scoped-direct-path-observed',))
                        gaps = ('KNOWN_CONFLICT',)
                    else:
                        ready = replace(ready, g2_gaps=('required-control-unknown',))
                        gaps = ('G2_INCOMPLETE',)
                    self.requests.clear()
                    scope = self.client if phase == 'PC1' else self.login
                    self.check(phase + ':' + failure, self.evaluate(scope, records, ready), gaps)
                    if gaps:
                        self.state_is('controlled_contact' if phase == 'PC1' else 'authenticated_use', 'revoked')
                        self.no_callbacks()
                    else:
                        # Unauthenticated client checks are collected under PC1,
                        # not prerequisites of its existing preparation grant.
                        self.state_is('controlled_contact', 'open_scoped', scopes=(EXPECTED_SCOPES[1],))
                        self.assertEqual(len(self.requests), 1)

    def test_unrelated_invalid_requests_do_not_revoke_a_valid_grant(self):
        with offline_only():
            self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
            self.requests.clear()
            self.check('malformed-action', self.guard.evaluate(None, self.ready, (), 20), ('INVALID_ACTION',))
            self.check('malformed-context', self.guard.evaluate(self.action(self.client), None, (), 20),
                       ('INVALID_CONTEXT',))
            self.check('invalid-transition', self.pc1(()), ('INVALID_TRANSITION',))
            self.check('invalid-scope', self.guard.transition(w.Phase.PC2, (), self.ready, (), 20),
                       ('INVALID_SCOPE',))
            unknown = self.evidence + (replace(self.evidence[1], observed_at=19, result='unknown'),)
            self.check('other-target-action', self.evaluate(self.client, unknown,
                binding=replace(self.binding, target='other-device')),
                ('TARGET_BINDING_MISMATCH', CONTROL_GAP))
            self.check('out-of-scope-login', self.evaluate(self.login, unknown),
                ('CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE', CONTROL_GAP, 'PC2_REQUIRED'))
            self.check('stale-action-facts', self.evaluate(self.client, unknown, facts_expires_at=20),
                ('STALE_OR_INVALID_FACTS', CONTROL_GAP))
            self.check('missing-action-permission', self.evaluate(self.client, unknown, permissions_verified=False),
                ('HOST_OS_PERMISSION_REQUIRED', CONTROL_GAP))
            self.check('missing-exact-plan', self.evaluate(self.client, unknown, plan_ref=''),
                ('EXACT_PLAN_REQUIRED', CONTROL_GAP))
            unsupported = replace(self.client, action='unsupported')
            self.check('unsupported-transition', self.guard.transition(w.Phase.PC2, (unsupported,),
                self.ready, unknown, 20), (CONTROL_GAP, 'UNSUPPORTED_OPERATION_SCOPE'))
            self.state_is('controlled_contact', 'open_scoped', scopes=(EXPECTED_SCOPES[1],))
            self.no_callbacks()

    def test_invalidated_grant_cannot_reopen_with_old_passes_after_rebind_or_resume(self):
        with offline_only():
            for invalidation in ('unknown', 'conflict', 'approval-expiry', 'handoff-expiry'):
                for reset in ('rebind', 'resume'):
                    self.reset_fixture()
                    self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
                    records, ready = self.evidence, self.ready
                    if invalidation == 'unknown':
                        records += (replace(records[1], observed_at=19, result='unknown'),)
                        gaps = (CONTROL_GAP,)
                    elif invalidation == 'conflict':
                        ready = replace(ready, conflicts=('scoped-direct-path-observed',))
                        gaps = ('KNOWN_CONFLICT',)
                    else:
                        records = records[:1] + (replace(records[1], expires_at=21),) + records[2:]
                        ticks = iter((777, 779))
                        self.guard._clock = lambda: next(ticks)
                        gaps = (CONTROL_GAP,)
                    result = self.pc2(records) if invalidation == 'handoff-expiry' else self.evaluate(self.client, records, ready)
                    self.check('invalidate-before-retry', result, gaps)
                    self.state_is('controlled_contact', 'revoked')
                    epoch = self.guard.contact_epoch
                    self.assertIsNotNone(epoch)
                    self.check('repeated-revoked-old-action', self.evaluate(self.client),
                        ('CONTACT_FACTS_REVALIDATION_REQUIRED', 'CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE') + PRE_GAPS)
                    self.assertIs(self.guard.contact_epoch, epoch)
                    if reset == 'rebind':
                        self.guard.rebind(self.binding)
                        history = 'not_measured'
                    else:
                        self.guard.resume(self.guard.snapshot())
                        history = 'previous_contact_reported'
                    self.guard._clock = lambda: 777
                    self.requests.clear()
                    self.check('old-passes-after-' + reset, self.pc1(), PRE_GAPS)
                    self.check('new-times-old-review-after-' + reset,
                               self.pc1(tuple(replace(e, observed_at=20) for e in self.evidence)), PRE_GAPS)
                    self.state_is(history=history)
                    self.no_callbacks()
                    current = tuple(replace(e, observed_at=20, contact_epoch=self.guard.contact_epoch)
                                    for e in self.evidence)
                    self.check('new-scoped-review-after-' + reset, self.pc1(current),
                               pending=('client-path', 'authenticated-path'))
                    self.assertEqual(len(self.requests), 1)
                    self.requests.clear()
                    self.check('old-action-after-retry-recovery', self.evaluate(self.client, current),
                               ('CONTACT_FACTS_REVALIDATION_REQUIRED',))
                    self.no_callbacks()

    def test_missing_purchase_review_does_not_revoke_otherwise_valid_login_grant(self):
        with offline_only():
            self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
            self.check('fixture-PC2', self.pc2(), pending=('authenticated-path',))
            self.requests.clear()
            unknown = self.evidence + (replace(self.evidence[1], observed_at=19, result='unknown'),)
            self.check('incomplete-purchase-request', self.evaluate(self.payment, unknown, review_ref=''),
                       (CONTROL_GAP, 'CURRENT_PURCHASE_REVIEW_REQUIRED'))
            self.state_is('authenticated_use', 'open_scoped', scopes=EXPECTED_SCOPES[2:])
            self.no_callbacks()
            # A later properly scoped evaluation of the control does invalidate.
            self.check('valid-login-request-rechecks-control', self.evaluate(self.login, unknown), (CONTROL_GAP,))
            self.state_is('authenticated_use', 'revoked')
            self.no_callbacks()

    def test_declined_action_preserves_primary_reason_but_invalidates_expired_grant(self):
        with offline_only():
            for reply in (w.Reply.CANCELLED, w.Reply.DENIED, w.Reply.TIMEOUT, None, True):
                for expires in (21, 100):
                    self.reset_fixture()
                    self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
                    self.requests.clear()
                    epoch = self.guard.contact_epoch
                    records = self.evidence[:1] + (replace(self.evidence[1], expires_at=expires),) + self.evidence[2:]
                    self.reply = reply
                    ticks = iter((777, 779))
                    self.guard._clock = lambda: next(ticks)
                    self.check('declined-exact-client-action', self.evaluate(self.client, records),
                               ('CURRENT_EXACT_APPROVAL_REQUIRED',))
                    self.assertEqual(len(self.requests), 1)
                    if expires == 21:
                        self.state_is('controlled_contact', 'revoked')
                        self.assertIsNot(self.guard.contact_epoch, epoch)
                        self.guard.rebind(self.binding)
                        self.guard._clock = lambda: 777
                        self.requests.clear()
                        self.check('declined-expiry-old-pass-retry', self.pc1(), PRE_GAPS)
                        self.no_callbacks()
                    else:
                        self.state_is('controlled_contact', 'open_scoped', scopes=(EXPECTED_SCOPES[1],))
                        self.assertIs(self.guard.contact_epoch, epoch)

    def test_invalid_approval_clock_does_not_invent_expiry_or_override_context(self):
        with offline_only():
            for ticks_value in ((779, 777), (777, float('nan'))):
                self.reset_fixture()
                self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
                records = self.evidence[:1] + (replace(self.evidence[1], expires_at=21),) + self.evidence[2:]
                ticks = iter(ticks_value)
                self.guard._clock = lambda: next(ticks)
                self.check('invalid-elapsed-clock', self.evaluate(self.client, records), ('APPROVAL_CLOCK_INVALID',))
                self.state_is('controlled_contact', 'open_scoped', scopes=(EXPECTED_SCOPES[1],))
                self.assertIsNone(self.guard.contact_epoch)

    def test_current_grant_control_expiring_during_approval_revokes_without_erasing_phase(self):
        with offline_only():
            for handoff in (False, True):
                self.reset_fixture()
                self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
                self.requests.clear()
                records = self.evidence[:1] + (replace(self.evidence[1], expires_at=21),) + self.evidence[2:]
                ticks = iter((777, 779))
                self.guard._clock = lambda: next(ticks)
                value = self.pc2(records) if handoff else self.evaluate(self.client, records)
                self.check('current-control-expired-during-approval', value, (CONTROL_GAP,))
                self.state_is('controlled_contact', 'revoked')
                self.assertEqual(len(self.requests), 1)

    def test_real_path_incident_after_pc2_revokes_login_and_payment_immediately(self):
        with offline_only():
            self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
            self.check('fixture-PC2', self.pc2(), pending=('authenticated-path',))
            self.requests.clear()
            self.guard.record_observed_contact()
            ready = replace(self.ready, conflicts=('device-a-profile-a-direct-path-observed',))
            for scope in (self.login, self.payment, self.gift_card):
                gaps = ('KNOWN_CONFLICT', 'CONTACT_FACTS_REVALIDATION_REQUIRED',
                        'CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE') + PRE_GAPS + (CLIENT_GAP,)
                if scope is not self.login:
                    gaps += (AUTH_GAP,)
                self.check('PC2-direct-path-incident:' + scope.action,
                           self.evaluate(scope, readiness=ready), gaps)
            self.state_is('authenticated_use', 'revoked', 'observed')
            self.no_callbacks()

    def test_postcontact_checks_are_pending_not_misclassified_as_optional_or_pc0(self):
        with offline_only():
            pre = self.evidence[:2]
            self.check('precontact-complete-only', self.pc1(pre),
                       pending=('client-path', 'authenticated-path'))
            self.assertEqual(self.requests, [{'purpose': 'handoff:controlled_contact',
                'binding': EXPECTED_BINDING, 'scopes': [EXPECTED_SCOPES[1]],
                'plan_ref': '', 'review_ref': '', 'evaluated_at': 20}])
            self.requests.clear()
            self.check('unauth-client-required', self.pc2(pre), (CLIENT_GAP,))
            unauth = self.evidence[:3]
            self.check('controlled-login-handoff', self.pc2(unauth), pending=('authenticated-path',))
            self.check('controlled-login-action', self.evaluate(self.login, unauth))
            self.assertEqual([r['purpose'] for r in self.requests],
                             ['handoff:authenticated_use', 'action:verify'])
            self.assertEqual(self.requests[-1], {'purpose': 'action:verify',
                'binding': EXPECTED_BINDING, 'scopes': [EXPECTED_SCOPES[2]],
                'plan_ref': 'plan-a', 'review_ref': 'review-a', 'evaluated_at': 20})
            self.requests.clear()
            for scope in (self.payment, self.gift_card):
                self.check('authenticated-check-still-required:' + scope.action,
                           self.evaluate(scope, unauth), (AUTH_GAP,))
            self.no_callbacks()

    def test_payment_needs_current_review_and_own_approval_after_complete_fixture_handoffs(self):
        with offline_only():
            self.check('fixture-PC1', self.pc1(), pending=('client-path', 'authenticated-path'))
            self.check('fixture-PC2', self.pc2(), pending=('authenticated-path',))
            self.requests.clear()
            for scope in (self.payment, self.gift_card):
                self.check('no-purchase-review:' + scope.action,
                           self.evaluate(scope, review_ref=''), ('CURRENT_PURCHASE_REVIEW_REQUIRED',))
            self.no_callbacks()
            for reply in (w.Reply.DENIED, w.Reply.CANCELLED, w.Reply.TIMEOUT, None, True):
                self.reply = reply
                self.check('unapproved-payment', self.evaluate(self.payment), ('CURRENT_EXACT_APPROVAL_REQUIRED',))
            self.assertEqual(len(self.requests), 5)
            for request in self.requests:
                self.assertEqual(request, {'purpose': 'action:verify',
                    'binding': EXPECTED_BINDING, 'scopes': [EXPECTED_SCOPES[3]],
                    'plan_ref': 'plan-a', 'review_ref': 'review-a', 'evaluated_at': 20})
            self.records.append({'approval_requests': self.requests})

    def test_new_review_requires_complete_control_evidence_and_new_handoff_approval(self):
        with offline_only():
            self.guard.record_observed_contact()
            # Fixture models a new scoped host review, not retagging production
            # observations. No native review or recovery happened in this test.
            current = tuple(replace(e, observed_at=20, contact_epoch=self.guard.contact_epoch)
                            for e in self.evidence)
            unknown = current[:1] + (replace(current[1], result='unknown'),) + current[2:]
            self.check('new-review-incomplete', self.pc1(unknown), (CONTROL_GAP,))
            self.no_callbacks()
            self.reply = w.Reply.CANCELLED
            self.check('new-review-cancelled-handoff', self.pc1(current),
                       ('CURRENT_EXACT_APPROVAL_REQUIRED',))
            self.state_is(history='observed')
            self.assertEqual(len(self.requests), 1)
            self.reply = w.Reply.APPROVED
            self.check('new-review-exact-fixture-handoff', self.pc1(current),
                       pending=('client-path', 'authenticated-path'))
            self.assertEqual(len(self.requests), 2)
            self.assertEqual(self.requests[0], self.requests[1])
            self.assertEqual(self.requests[-1], {'purpose': 'handoff:controlled_contact',
                'binding': EXPECTED_BINDING, 'scopes': [EXPECTED_SCOPES[1]],
                'plan_ref': '', 'review_ref': '', 'evaluated_at': 20})
            self.requests.clear()
            self.check('old-action-after-new-review', self.evaluate(self.client, current),
                       ('CONTACT_FACTS_REVALIDATION_REQUIRED',))
            self.no_callbacks()
            self.state_is('controlled_contact', 'open_scoped', 'observed', (EXPECTED_SCOPES[1],))

    def test_control_expiring_during_handoff_approval_cannot_open_gate(self):
        with offline_only():
            records = self.evidence[:1] + (replace(self.evidence[1], expires_at=21),) + self.evidence[2:]
            ticks = iter((777, 779))
            self.guard._clock = lambda: next(ticks)
            self.check('approval-wait-expired-required-control', self.pc1(records), (CONTROL_GAP,))
            self.assertEqual(self.requests, [{'purpose': 'handoff:controlled_contact',
                'binding': EXPECTED_BINDING, 'scopes': [EXPECTED_SCOPES[1]],
                'plan_ref': '', 'review_ref': '', 'evaluated_at': 20}])
            self.records.append({'approval_requests': self.requests})
            self.state_is()

    def test_unknown_controls_allow_only_independent_offline_plan_not_automatic_contact(self):
        with offline_only():
            self.check('independent-local-plan', self.evaluate(self.local, (), w.Readiness()))
            self.assertEqual(self.requests, [{'purpose': 'action:plan', 'binding': EXPECTED_BINDING,
                'scopes': [EXPECTED_SCOPES[0]], 'plan_ref': 'plan-a', 'review_ref': 'review-a',
                'evaluated_at': 20}])
            self.state_is()
            self.records.append({'approval_requests': self.requests})

    def test_required_manifest_is_not_a_saved_permission_or_an_optional_flag(self):
        with offline_only():
            for requirements in (w.Requirements(),
                                 w.Requirements(('required-fault-blocking',), ('required-fault-blocking',)),
                                 w.Requirements(('required-fault-blocking',), ())):
                with self.assertRaisesRegex(ValueError, '^INVALID_REQUIREMENTS$'):
                    w.WorkflowGuard(self.binding, requirements)
            # An unsupported optional keyword is not accepted. Host omission is
            # still outside the guard's proof; see the explicit C-review limit.
            with self.assertRaises(TypeError):
                w.Requirements(precontact=('required-fault-blocking',),
                               client_unauthenticated=('client-path',), optional=True)
            self.state_is()
            self.no_callbacks()


def replay():
    suite = unittest.defaultTestLoader.loadTestsFromTestCase(RequiredControlsTests)
    cases = list(suite)
    result = unittest.TextTestRunner(stream=io.StringIO()).run(suite)
    if not result.wasSuccessful():
        raise AssertionError(result.failures + result.errors)
    return {'case_id': 'ENV-T81', 'original_layers': 'L + C',
            'scenario': '接触前必需项目未知或有真实误直连',
            'requirement': '门禁保持 closed；不是标成可选限制后自动登录/购卡',
            'execution': 'synthetic_host_assertions_under_test_io_sentinels',
            'native_acceptance': 'not_run', 'tests_run': result.testsRun,
            'cases': [{'test': case.id().split('.')[-1], 'records': case.records} for case in cases]}


if __name__ == '__main__':
    if sys.argv[1:] == ['--replay']:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    else:
        unittest.main()
