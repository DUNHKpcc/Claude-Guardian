"""Pure workflow eligibility, ENV §3/18 and main §6.13. No executor or I/O.

The host is the trust boundary: it supplies reviewed applicability, exact adapter
support, target-native observations and a LIVE approval callback. These typed
records, digests and callback responses are assertions, not proof of human
consent, signatures, sandboxing, or protection against a malicious Python caller.
The host must derive them from real approvals/observations, never model output or
persisted permission flags. Callback requests contain opaque references only;
this module accepts no command, URL, credential or arbitrary executor.

After observed contact, the host must review the current control gaps and collect
or revalidate the affected evidence/action facts using the current contact_epoch.
Capture that identity when the review starts; never retag preincident records at
handoff time. The epoch is an in-process freshness assertion, not authorization,
a credential, or proof that the host actually performed its review. It is omitted
from requests/snapshots and must not be exported or reconstructed from reports.
No clock-domain assumption or additional time-to-live is imposed by this marker.

An allowed result is a point-in-time scheduling decision, never an execution
capability. Re-evaluate immediately before each action. Host/OS approvals remain
separate; saved reports cannot restore permissions. Enforcement is workflow-only,
not process/network isolation. No support for automatic login/payment is provided.
"""
from dataclasses import dataclass, field
from enum import Enum
import math
import re
import time
from typing import Callable, Optional, Tuple


class Phase(Enum):
    PC0 = 'precontact'
    PC1 = 'controlled_contact'
    PC2 = 'authenticated_use'


class GateState(Enum):
    CLOSED = 'closed'
    AWAITING = 'eligible_awaiting_user'
    OPEN = 'open_scoped'
    REVOKED = 'revoked'


class Operation(Enum):
    AUDIT = 'audit'
    PROBE = 'probe'
    PLAN = 'plan'
    APPLY = 'apply'
    VERIFY = 'verify'
    ROLLBACK = 'rollback'


class Contact(Enum):
    LOCAL = 'local'
    NEUTRAL = 'neutral'
    CLAUDE = 'claude'
    LOGIN_HANDOFF = 'login_handoff'
    PAYMENT_HANDOFF = 'payment_handoff'


class Risk(Enum):
    READ = 'read'
    CHANGE = 'change'
    CONTROL_CHANNEL = 'control_channel'
    IRREVERSIBLE = 'irreversible'


class Reply(Enum):
    APPROVED = 'approved'
    DENIED = 'denied'
    CANCELLED = 'cancelled'
    TIMEOUT = 'timeout'
    UNKNOWN = 'unknown'


class EvidenceKind(Enum):
    TARGET_NATIVE = 'target_native'
    TARGET_MANUAL = 'target_manual'
    SYNTHETIC = 'synthetic'
    CI = 'ci'


class CheckStage(Enum):
    PRECONTACT = 'PC-G1'
    CLIENT_UNAUTHENTICATED = 'PC-G2-unauthenticated'
    CLIENT_AUTHENTICATED = 'PC-G2-authenticated'


def _ref(value):
    return type(value) is str and re.fullmatch(r'[A-Za-z0-9][A-Za-z0-9_.:-]{0,127}', value) is not None


def _finite_time(value):
    try:
        return type(value) in (int, float) and math.isfinite(value)
    except OverflowError:
        return False


def _fresh(observed, expires, now):
    return all(_finite_time(x) for x in (observed, expires, now)) and observed <= now < expires


class _ContactEpoch:
    """Opaque, non-address-bearing identity; copies are different review epochs."""
    __slots__ = ()

    def __repr__(self):
        return '<contact-review-epoch>'


@dataclass(frozen=True)
class Binding:
    target: str
    user: str
    namespace: str
    profile: str
    configuration: str
    network: str
    runtime_version: str

    def valid(self):
        return all(_ref(v) for v in self.__dict__.values())


@dataclass(frozen=True)
class Scope:
    module: str
    operation: Operation
    action: str
    product: str
    version: str
    installation: str
    platform: str
    contact: Contact = Contact.LOCAL
    risk: Risk = Risk.READ
    endpoint_refs: Tuple[str, ...] = ()
    requires_authentication: bool = False

    def valid(self):
        return (all(_ref(v) for v in (self.module, self.action, self.product,
                self.version, self.installation, self.platform))
                and isinstance(self.operation, Operation) and isinstance(self.contact, Contact)
                and isinstance(self.risk, Risk) and type(self.endpoint_refs) is tuple
                and all(_ref(v) for v in self.endpoint_refs)
                and type(self.requires_authentication) is bool)


@dataclass(frozen=True)
class AdapterSupport:
    scope: Scope
    design_status: str = 'unknown'
    implementation_status: str = 'not_implemented'
    validation_status: str = 'not_run'
    # Exact operation/version native validation, not a general supported=True.
    validation_ref: str = ''

    def supported(self):
        return (isinstance(self.scope, Scope) and self.scope.valid() and self.design_status == 'accepted'
                and self.implementation_status == 'implemented'
                and self.validation_status == 'native_pass' and _ref(self.validation_ref))


@dataclass(frozen=True)
class Evidence:
    check: str
    stage: CheckStage
    binding: Binding
    observed_at: float
    expires_at: float
    kind: EvidenceKind = EvidenceKind.SYNTHETIC
    result: str = 'unknown'
    contact_epoch: object = field(default=None, repr=False)

    def valid_for(self, check, stage, binding, now):
        return (self.check == check and self.stage is stage and self.binding == binding
                and self.kind in (EvidenceKind.TARGET_NATIVE, EvidenceKind.TARGET_MANUAL)
                and self.result == 'pass' and _fresh(self.observed_at, self.expires_at, now))


@dataclass(frozen=True)
class Requirements:
    """Host-reviewed applicability. Empty PC-G1/unauth sets fail closed.

    Real-client checks MUST be in client_*; PC-G1 never accepts their evidence.
    Authenticated checks may remain pending at the PC1 -> PC2 login handoff.
    """
    precontact: Tuple[str, ...] = ()
    client_unauthenticated: Tuple[str, ...] = ()
    client_authenticated: Tuple[str, ...] = ()

    def valid(self):
        groups = (self.precontact, self.client_unauthenticated, self.client_authenticated)
        if not all(type(group) is tuple and len(group) <= 128 for group in groups):
            return False
        flat = tuple(x for group in groups for x in group)
        return (all(type(group) is tuple for group in groups)
                and bool(self.precontact) and bool(self.client_unauthenticated)
                and all(_ref(x) for x in flat) and len(set(flat)) == len(flat))


@dataclass(frozen=True)
class Readiness:
    # G1/G2 do not open either contact gate or grant G3 authorization.
    g1_status: str = 'partial'
    g1_gaps: Tuple[str, ...] = ('interview_incomplete',)
    g2_gaps: Tuple[str, ...] = ('planning_incomplete',)
    conflicts: Tuple[str, ...] = ()

    def valid(self):
        return (self.g1_status in ('complete', 'partial', 'paused', 'blocked', 'emergency_deferred')
                and all(type(group) is tuple and len(group) <= 128 and all(_ref(x) for x in group)
                        for group in (self.g1_gaps, self.g2_gaps, self.conflicts)))

    def gaps(self):
        return (('G1_INCOMPLETE',) if self.g1_status != 'complete' or self.g1_gaps else ()) + (
            ('G2_INCOMPLETE',) if self.g2_gaps else ()) + (('KNOWN_CONFLICT',) if self.conflicts else ())


@dataclass(frozen=True)
class Recovery:
    backup_verified: bool = False
    rollback_ready: bool = False
    offline_rescue_verified: bool = False
    preserves_later_changes: bool = False


@dataclass(frozen=True)
class Action:
    scope: Scope
    binding: Binding
    plan_ref: str
    facts_at: float
    facts_expires_at: float
    # Exact reviewed semantic diff/impact/protection/acceptance/failure-exit record.
    review_ref: str = ''
    permissions_verified: bool = False
    recovery: Recovery = Recovery()
    facts_contact_epoch: object = field(default=None, repr=False)


@dataclass(frozen=True)
class ApprovalRequest:
    purpose: str
    binding: Binding
    scopes: Tuple[Scope, ...]
    plan_ref: str
    review_ref: str
    evaluated_at: float


@dataclass(frozen=True)
class Decision:
    allowed: bool
    gaps: Tuple[str, ...]
    supported_scopes: Tuple[Scope, ...] = ()
    pending_checks: Tuple[str, ...] = ()
    enforcement_level: str = 'workflow_guard'
    executes: bool = False


@dataclass(frozen=True)
class State:
    phase: Phase = Phase.PC0
    gate: GateState = GateState.CLOSED
    scopes: Tuple[Scope, ...] = ()
    observed_contact: str = 'not_measured'


class WorkflowGuard:
    """In-memory coordinator. Construction and resume ALWAYS close the gate.

    authorize is a trusted-host callback invoked separately for each handoff and
    every exact action. Exceptions, bools, silence, cancellation and timeout deny.
    A contact handoff approves only phase/scope, never a later action or payment.
    """
    def __init__(self, binding: Binding, requirements: Requirements,
                 adapters: Tuple[AdapterSupport, ...] = (),
                 authorize: Optional[Callable[[ApprovalRequest], Reply]] = None,
                 clock: Callable[[], float] = time.monotonic):
        if not isinstance(binding, Binding) or not binding.valid():
            raise ValueError('INVALID_BINDING')
        if not isinstance(requirements, Requirements) or not requirements.valid():
            raise ValueError('INVALID_REQUIREMENTS')
        if type(adapters) is not tuple or not all(isinstance(x, AdapterSupport) for x in adapters):
            raise ValueError('INVALID_ADAPTERS')
        self.binding, self.requirements = binding, requirements
        self.adapters, self.authorize = adapters, authorize
        self._state = State()
        self._generation = 0
        self._contact_epoch = None
        self._clock = clock

    @property
    def state(self):
        return self._state

    @property
    def contact_epoch(self):
        """Capture at the start of a real scoped review, never from saved data.

        None preserves legacy inputs until contact is observed or resumed.
        Local audits/plans and neutral recovery probes do not need this marker.
        """
        return self._contact_epoch

    def supported_scopes(self):
        return tuple(a.scope for a in self.adapters if a.supported())

    def _decision(self, gaps=(), pending=()):
        return Decision(not gaps, tuple(dict.fromkeys(gaps)), self.supported_scopes(), tuple(pending))

    def _approval(self, request):
        # Approval can wait on a human and re-enter the host. Never overwrite a
        # revoke/rebind/resume that happened while that request was outstanding.
        context = (self._generation, self.binding, self.requirements, self.adapters,
                   self.state, self._contact_epoch)
        if not callable(self.authorize):
            return ('HOST_APPROVAL_UNAVAILABLE',), request.evaluated_at
        try:
            started = self._clock()
            reply = self.authorize(request)
            finished = self._clock()
            if (not _finite_time(started) or not _finite_time(finished) or finished < started):
                return ('APPROVAL_CLOCK_INVALID',), request.evaluated_at
        except Exception:
            return ('HOST_APPROVAL_FAILED',), request.evaluated_at
        current = (self._generation, self.binding, self.requirements, self.adapters,
                   self.state, self._contact_epoch)
        try:
            checked_at = request.evaluated_at + (finished - started)
        except OverflowError:
            return ('APPROVAL_CLOCK_INVALID',), request.evaluated_at
        if not _finite_time(checked_at):
            return ('APPROVAL_CLOCK_INVALID',), request.evaluated_at
        if context != current:
            return ('APPROVAL_CONTEXT_CHANGED',), checked_at
        return (() if reply is Reply.APPROVED else ('CURRENT_EXACT_APPROVAL_REQUIRED',)), checked_at

    def _context_valid(self, readiness, evidence, now):
        return (isinstance(readiness, Readiness) and readiness.valid()
                and type(evidence) is tuple and len(evidence) <= 512
                and all(isinstance(e, Evidence) for e in evidence)
                and _finite_time(now))

    def _evidence(self, stage, evidence, now):
        checks = {CheckStage.PRECONTACT: self.requirements.precontact,
                  CheckStage.CLIENT_UNAUTHENTICATED: self.requirements.client_unauthenticated,
                  CheckStage.CLIENT_AUTHENTICATED: self.requirements.client_authenticated}[stage]
        gaps = []
        for check in checks:
            records = tuple(e for e in evidence if e.check == check and e.stage is stage
                            and e.binding == self.binding
                            and e.contact_epoch is self._contact_epoch
                            and e.kind in (EvidenceKind.TARGET_NATIVE, EvidenceKind.TARGET_MANUAL))
            # Latest authoritative observation supersedes older passes, even if
            # the latest is unknown, failed, or expired. Tied conflicts deny.
            # Malformed/future native observations cannot resurrect an old pass.
            valid_times = all(_finite_time(e.observed_at) and e.observed_at <= now for e in records)
            if not records or not valid_times:
                gaps.append('EVIDENCE_REQUIRED:' + check)
                continue
            latest_at = max(e.observed_at for e in records)
            latest = tuple(e for e in records if e.observed_at == latest_at)
            if not all(e.valid_for(check, stage, self.binding, now) for e in latest):
                gaps.append('EVIDENCE_REQUIRED:' + check)
        return tuple(gaps)

    def revoke(self):
        self._generation += 1
        self._state = State(self.state.phase, GateState.REVOKED, (), self.state.observed_contact)

    def record_observed_contact(self):
        """Revoke and require a new scoped control-gap/evidence review.

        Unexpected/past contact remains history. A later approval alone cannot
        restore old evidence; no incident time is guessed from the elapsed clock.
        """
        self._generation += 1
        self._contact_epoch = _ContactEpoch()
        self._state = State(self.state.phase, GateState.REVOKED, (), 'observed')

    def rebind(self, binding):
        if not isinstance(binding, Binding) or not binding.valid():
            raise ValueError('INVALID_BINDING')
        self._generation += 1
        self.binding = binding
        if self._contact_epoch is not None:
            self._contact_epoch = _ContactEpoch()
        self._state = State(observed_contact=self.state.observed_contact)

    def resume(self, saved):
        """Saved phase/approval/evidence never restores runtime permission.

        Retain only conservative contact history; no claim that past use vanished.
        Caller may separately revalidate observations and request fresh handoffs.
        """
        self._generation += 1
        history = 'previous_contact_reported' if isinstance(saved, dict) and (
            saved.get('phase') in (Phase.PC1.value, Phase.PC2.value)
            or saved.get('observed_contact') != 'not_measured') else self.state.observed_contact
        if self._contact_epoch is not None or history != 'not_measured':
            # Never restore an identity from saved input, even in this process.
            self._contact_epoch = _ContactEpoch()
        self._state = State(observed_contact=history)

    def snapshot(self):
        return {'phase': self.state.phase.value, 'gate_state': self.state.gate.value,
                'observed_contact': self.state.observed_contact,
                'runtime_permission_restorable': False}

    def transition(self, phase, scopes, readiness, evidence, now):
        """PC0 -> PC1 -> PC2, with fresh distinct per-target handoffs only."""
        if not self._context_valid(readiness, evidence, now):
            return self._decision(('INVALID_CONTEXT',))
        if phase not in (Phase.PC1, Phase.PC2) or (
            phase is Phase.PC1 and self.state.phase is not Phase.PC0) or (
            phase is Phase.PC2 and (self.state.phase is not Phase.PC1 or self.state.gate is not GateState.OPEN)):
            return self._decision(('INVALID_TRANSITION',))
        if type(scopes) is not tuple or not scopes or len(scopes) > 128 or not all(isinstance(s, Scope) and s.valid() for s in scopes):
            return self._decision(('INVALID_SCOPE',))
        gaps = list(readiness.gaps())
        gaps.extend(self._evidence(CheckStage.PRECONTACT, evidence, now))
        if phase is Phase.PC2:
            gaps.extend(self._evidence(CheckStage.CLIENT_UNAUTHENTICATED, evidence, now))
        for scope in scopes:
            if scope not in self.supported_scopes():
                gaps.append('UNSUPPORTED_OPERATION_SCOPE')
            if scope.contact not in (Contact.CLAUDE, Contact.LOGIN_HANDOFF, Contact.PAYMENT_HANDOFF):
                gaps.append('CONTACT_SCOPE_REQUIRED')
            if phase is Phase.PC1 and (scope.contact is not Contact.CLAUDE or scope.requires_authentication):
                gaps.append('PC1_SCOPE_EXCEEDED')
        if gaps:
            return self._decision(gaps)
        self._generation += 1
        generation = self._generation
        self._state = State(self.state.phase, GateState.AWAITING, (), self.state.observed_contact)
        gaps, checked_at = self._approval(ApprovalRequest('handoff:' + phase.value, self.binding, scopes, '', '', now))
        if not gaps:
            gaps = self._evidence(CheckStage.PRECONTACT, evidence, checked_at)
            if phase is Phase.PC2:
                gaps += self._evidence(CheckStage.CLIENT_UNAUTHENTICATED, evidence, checked_at)
        if gaps:
            if self._generation == generation and self.state.gate is GateState.AWAITING:
                self._state = State(self.state.phase, GateState.CLOSED, (), self.state.observed_contact)
            return self._decision(gaps)
        self._state = State(phase, GateState.OPEN, scopes, self.state.observed_contact)
        return self._decision(pending=self.requirements.client_unauthenticated + self.requirements.client_authenticated
                              if phase is Phase.PC1 else self.requirements.client_authenticated)

    def evaluate(self, action, readiness, evidence, now):
        """G3 eligibility only; caller must enforce the resulting exact scope.

        Read-only audits/plans can continue while G1/G2 are incomplete. Probes and
        changes require the applicable readiness. Login/payment scopes describe
        user handoffs only; the module never authorizes automated credentials or
        purchasing. Neutral endpoints cannot grant Claude contact permissions.
        """
        if not self._context_valid(readiness, evidence, now):
            return self._decision(('INVALID_CONTEXT',))
        if (not isinstance(action, Action) or not isinstance(action.scope, Scope)
                or not action.scope.valid() or not isinstance(action.recovery, Recovery)
                or not isinstance(action.binding, Binding) or not action.binding.valid()):
            return self._decision(('INVALID_ACTION',))
        s = action.scope
        gaps = []
        if action.binding != self.binding:
            gaps.append('TARGET_BINDING_MISMATCH')
        if not _fresh(action.facts_at, action.facts_expires_at, now):
            gaps.append('STALE_OR_INVALID_FACTS')
        if s not in self.supported_scopes():
            gaps.append('UNSUPPORTED_OPERATION_SCOPE')
        if not _ref(action.plan_ref):
            gaps.append('EXACT_PLAN_REQUIRED')
        if action.permissions_verified is not True:
            gaps.append('HOST_OS_PERMISSION_REQUIRED')
        if s.operation not in (Operation.AUDIT, Operation.PLAN):
            gaps.extend(readiness.gaps())
        if s.contact is Contact.NEUTRAL and not s.endpoint_refs:
            gaps.append('EXACT_ENDPOINTS_REQUIRED')
        if s.operation in (Operation.AUDIT, Operation.PLAN) and s.contact is not Contact.LOCAL:
            gaps.append('OFFLINE_OPERATION_REQUIRED')
        if s.operation in (Operation.APPLY, Operation.ROLLBACK) and s.risk is Risk.READ:
            gaps.append('CHANGE_RISK_REQUIRED')
        if s.risk is not Risk.READ:
            if not _ref(action.review_ref):
                gaps.append('EXACT_REVIEW_REQUIRED')
            if not (action.recovery.backup_verified is True and action.recovery.rollback_ready is True):
                gaps.append('VERIFIED_RECOVERY_REQUIRED')
            if s.risk is Risk.CONTROL_CHANNEL and action.recovery.offline_rescue_verified is not True:
                gaps.append('INDEPENDENT_OFFLINE_RESCUE_REQUIRED')
            if s.risk is Risk.IRREVERSIBLE:
                gaps.append('IRREVERSIBLE_HANDOFF_REQUIRED')
        if s.operation is Operation.ROLLBACK and action.recovery.preserves_later_changes is not True:
            gaps.append('LATER_CHANGES_NOT_PROTECTED')
        if s.contact in (Contact.CLAUDE, Contact.LOGIN_HANDOFF, Contact.PAYMENT_HANDOFF):
            if action.facts_contact_epoch is not self._contact_epoch:
                gaps.append('CONTACT_FACTS_REVALIDATION_REQUIRED')
            if self.state.phase is Phase.PC0 or self.state.gate is not GateState.OPEN or s not in self.state.scopes:
                gaps.append('CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE')
            gaps.extend(self._evidence(CheckStage.PRECONTACT, evidence, now))
            if s.requires_authentication or s.contact in (Contact.LOGIN_HANDOFF, Contact.PAYMENT_HANDOFF):
                if self.state.phase is not Phase.PC2:
                    gaps.append('PC2_REQUIRED')
                gaps.extend(self._evidence(CheckStage.CLIENT_UNAUTHENTICATED, evidence, now))
            if s.contact is Contact.PAYMENT_HANDOFF:
                gaps.extend(self._evidence(CheckStage.CLIENT_AUTHENTICATED, evidence, now))
                if not _ref(action.review_ref):
                    gaps.append('CURRENT_PURCHASE_REVIEW_REQUIRED')
        if gaps:
            return self._decision(gaps)
        gaps, checked_at = self._approval(ApprovalRequest('action:' + s.operation.value, self.binding,
                                            (s,), action.plan_ref, action.review_ref, now))
        if not gaps:
            if not _fresh(action.facts_at, action.facts_expires_at, checked_at):
                gaps += ('STALE_OR_INVALID_FACTS',)
            if s.contact in (Contact.CLAUDE, Contact.LOGIN_HANDOFF, Contact.PAYMENT_HANDOFF):
                if action.facts_contact_epoch is not self._contact_epoch:
                    gaps += ('CONTACT_FACTS_REVALIDATION_REQUIRED',)
                gaps += self._evidence(CheckStage.PRECONTACT, evidence, checked_at)
                if s.requires_authentication or s.contact in (Contact.LOGIN_HANDOFF, Contact.PAYMENT_HANDOFF):
                    gaps += self._evidence(CheckStage.CLIENT_UNAUTHENTICATED, evidence, checked_at)
                if s.contact is Contact.PAYMENT_HANDOFF:
                    gaps += self._evidence(CheckStage.CLIENT_AUTHENTICATED, evidence, checked_at)
        return self._decision(gaps)
