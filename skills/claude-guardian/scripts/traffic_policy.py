"""Typed Claude-target IPv4-only requirement and pure conditional planning.

PRODUCT-IPV4-20261018 is a product decision, not host permission or evidence.
No native enforcement adapter exists here. No input can produce a policy pass.
"""
from dataclasses import dataclass, field
import re
import time

# Recognized credential-shape guard; kept stdlib-only so
# legacy file-path imports of standalone producers do not require sys.path edits.
_CREDENTIAL_ALIAS = re.compile(
    r"(?i)(?<![A-Za-z0-9])(?:gh[oprsu]_|github_pat_|sk-(?:ant-)?|xox[baprs]-)"
    r"[A-Za-z0-9_-]{12,}")

REQUIREMENT_ID = 'PRODUCT-IPV4-20261018'
SCHEMA = 'guardian-traffic-policy/0.1'
PLAN_SCHEMA = 'guardian-ipv4-policy-scope/0.1'
MAX_SCOPE_REFS = 64
MAX_TOTAL_REFS = 256
_ALIAS = re.compile(r'[A-Za-z][A-Za-z0-9_-]{0,63}\Z')
_REF_FIELDS = ('application_scope_refs', 'target_leg_scope_refs', 'proxy_outer_scope_refs',
               'control_scope_refs', 'other_application_scope_refs')
_ENUM_FIELDS = {
    'scope_support': ('supported', 'unsupported', 'unknown'),
    'target_outer_separation': ('declared', 'unknown'),
    'ipv6_fallback': ('excluded', 'present', 'unknown'),
    'outer_transport_preserved': ('declared', 'unknown'),
    'control_channels_preserved': ('declared', 'unknown'),
    'other_applications_preserved': ('declared', 'unknown'),
    'configuration_state': ('current_declared', 'stale', 'unknown'),
}
REASON_CODES = (
    'IPV4_ONLY_SCOPE_UNBOUND', 'IPV4_ONLY_SCOPE_UNSUPPORTED',
    'IPV4_ONLY_ENFORCEMENT_UNKNOWN', 'IPV4_ONLY_IPV6_FALLBACK_NOT_EXCLUDED',
    'IPV4_ONLY_PRESERVED_SCOPE_CONFLICT', 'IPV4_ONLY_VERIFICATION_NOT_RUN',
    'IPV4_ONLY_INTENT_CONFLICT', 'IPV4_ONLY_CONFIGURATION_STALE',
)


class TrafficPolicyError(ValueError):
    """Fixed non-sensitive code, with no partial artifact or caller text."""


def _fail(code):
    raise TrafficPolicyError(code) from None


@dataclass(frozen=True, slots=True)
class TrafficPolicy:
    schema_version: str = field(default=SCHEMA, init=False)
    requirement_id: str = field(default=REQUIREMENT_ID, init=False)
    effective_from: str = field(default='2026-10-18', init=False)
    policy: str = field(default='IPv4_ONLY', init=False)
    applies_to: str = field(default='claude_target_application_traffic', init=False)
    ipv6_fallback: str = field(default='forbidden', init=False)
    proxy_outer_transport: str = field(default='preserve_existing_independently', init=False)
    control_channels: str = field(default='preserve', init=False)
    other_applications: str = field(default='unchanged', init=False)
    enforcement_status: str = field(default='unknown', init=False)
    compliance: str = field(default='not_established', init=False)
    environment_pass: bool = field(default=False, init=False)
    apply_supported: bool = field(default=False, init=False)
    authorization: str = field(default='none', init=False)


_DEFAULT = TrafficPolicy()


def policy_projection():
    """Fresh fixed product-policy data; never project caller-supplied pass claims."""
    return {name: getattr(_DEFAULT, name) for name in TrafficPolicy.__dataclass_fields__}


def _alias(value):
    if (type(value) is not str or _ALIAS.fullmatch(value) is None
            or _CREDENTIAL_ALIAS.search(value) is not None):
        _fail('INVALID_POLICY_SCOPE')
    return value


def _snapshot(scope):
    if scope is None:
        return ()
    fields = {'schema_version', 'target_ref', *_REF_FIELDS, *_ENUM_FIELDS}
    if (type(scope) is not dict or len(scope) != len(fields)
            or any(type(key) is not str for key in scope) or set(scope) != fields):
        _fail('INVALID_POLICY_SCOPE')
    if type(scope['schema_version']) is not str or scope['schema_version'] != PLAN_SCHEMA:
        _fail('INVALID_POLICY_SCOPE')
    result = {'schema_version': PLAN_SCHEMA, 'target_ref': _alias(scope['target_ref'])}
    count = 0
    for key in _REF_FIELDS:
        values = scope[key]
        if type(values) not in (tuple, list) or len(values) > MAX_SCOPE_REFS:
            _fail('POLICY_SCOPE_BUDGET_EXCEEDED')
        copied = tuple(_alias(value) for value in values)
        count += len(copied)
        if len(set(copied)) != len(copied):
            _fail('DUPLICATE_POLICY_SCOPE')
        if count > MAX_TOTAL_REFS:
            _fail('POLICY_SCOPE_BUDGET_EXCEEDED')
        result[key] = copied
    for key, choices in _ENUM_FIELDS.items():
        value = scope[key]
        if type(value) is not str or value not in choices:
            _fail('INVALID_POLICY_SCOPE')
        result[key] = value
    return tuple(sorted(result.items()))


@dataclass(frozen=True, slots=True, repr=False)
class PrivatePolicyPlan:
    _scope: tuple
    _reasons: tuple
    _planning_status: str
    _enforcement_status: str

    def __post_init__(self):
        if (type(self._scope) is not tuple or type(self._reasons) is not tuple
                or len(self._reasons) > len(REASON_CODES)
                or any(type(code) is not str or code not in REASON_CODES for code in self._reasons)
                or len(set(self._reasons)) != len(self._reasons)
                or type(self._planning_status) is not str
                or self._planning_status not in ('conditional_plan', 'unresolved', 'unsupported', 'blocked')
                or type(self._enforcement_status) is not str
                or self._enforcement_status not in ('unknown', 'unsupported')):
            _fail('INVALID_POLICY_PLAN')
        if not {'IPV4_ONLY_ENFORCEMENT_UNKNOWN', 'IPV4_ONLY_VERIFICATION_NOT_RUN'} <= set(self._reasons):
            _fail('INVALID_POLICY_PLAN')
        if self._scope:
            expected_count = 2 + len(_REF_FIELDS) + len(_ENUM_FIELDS)
            if (len(self._scope) != expected_count
                    or any(type(pair) is not tuple or len(pair) != 2
                           or type(pair[0]) is not str for pair in self._scope)
                    or len({pair[0] for pair in self._scope}) != expected_count):
                _fail('INVALID_POLICY_PLAN')
            try:
                snapshot = _snapshot(dict(self._scope))
            except (ValueError, TypeError):
                _fail('INVALID_POLICY_PLAN')
            if snapshot != self._scope:
                _fail('INVALID_POLICY_PLAN')
        if (self._reasons, self._planning_status, self._enforcement_status) != _outcome(self._scope):
            _fail('INVALID_POLICY_PLAN')

    def __repr__(self):
        return '<PrivatePolicyPlan: conditional plan, private scope omitted>'

    def __reduce_ex__(self, protocol):
        raise TypeError('private policy plan serialization disabled')

    def preview(self):
        # Status may downgrade to unsupported, never upgrade to verified/passed.
        result = policy_projection()
        result.update(enforcement_status=self._enforcement_status,
                      planning_status=self._planning_status,
                      reason_codes=list(self._reasons), evidence='declared_unverified',
                      target_binding='not_established', native_acceptance='not_run',
                      proposed_operation='review_scoped_ipv4_only_plan',
                      target_mutation_supported=False)
        return result

    def private_material(self):
        return {'declared_scope': self._scope, 'policy': policy_projection(),
                'reason_codes': self._reasons, 'planning_status': self._planning_status}


def _outcome(snapshot, guard=lambda: None):
    """Canonical result derivation also validates direct result construction."""
    values = dict(snapshot)
    reasons = []
    planning_status = 'conditional_plan'
    enforcement_status = 'unknown'

    def reason(code):
        if code not in reasons:
            reasons.append(code)

    if (not values or not values.get('application_scope_refs')
            or not values.get('target_leg_scope_refs')):
        reason('IPV4_ONLY_SCOPE_UNBOUND')
        planning_status = 'unresolved'
    if values.get('scope_support') == 'unsupported':
        reason('IPV4_ONLY_SCOPE_UNSUPPORTED')
        enforcement_status = 'unsupported'
        planning_status = 'unsupported'
    elif values.get('scope_support') != 'supported':
        reason('IPV4_ONLY_ENFORCEMENT_UNKNOWN')
        planning_status = 'unresolved'
    selected = set(values.get('application_scope_refs', ())) | set(values.get('target_leg_scope_refs', ()))
    preserved = set()
    for key in ('proxy_outer_scope_refs', 'control_scope_refs', 'other_application_scope_refs'):
        guard()
        preserved.update(values.get(key, ()))
    if selected & preserved:
        reason('IPV4_ONLY_PRESERVED_SCOPE_CONFLICT')
        planning_status = 'blocked'
    if values.get('ipv6_fallback') != 'excluded':
        reason('IPV4_ONLY_IPV6_FALLBACK_NOT_EXCLUDED')
        if values.get('ipv6_fallback') == 'present':
            reason('IPV4_ONLY_INTENT_CONFLICT')
            planning_status = 'blocked'
        elif planning_status == 'conditional_plan':
            planning_status = 'unresolved'
    if values.get('configuration_state') == 'stale':
        reason('IPV4_ONLY_CONFIGURATION_STALE')
        planning_status = 'blocked'
    for key, expected in (('target_outer_separation', 'declared'),
                          ('outer_transport_preserved', 'declared'),
                          ('control_channels_preserved', 'declared'),
                          ('other_applications_preserved', 'declared'),
                          ('configuration_state', 'current_declared')):
        guard()
        if values.get(key) != expected:
            reason('IPV4_ONLY_ENFORCEMENT_UNKNOWN')
            if planning_status == 'conditional_plan':
                planning_status = 'unresolved'
    # Even complete declarations do not prove enforcement, fallback exclusion,
    # current host identity or native acceptance. No successful pass path exists.
    reason('IPV4_ONLY_ENFORCEMENT_UNKNOWN')
    reason('IPV4_ONLY_VERIFICATION_NOT_RUN')
    return tuple(reasons), planning_status, enforcement_status


def plan_ipv4_only(scope=None, *, max_seconds=5, cancelled=lambda: False):
    """Plan under declarations; actual host binding/enforcement remain unverified.

    application_scope_refs includes selected related subprocesses when applicable.
    target_leg_scope_refs includes proxy-to-Claude-target address-family selection.
    Preserved refs are separate: proxy outer transport may remain IPv6. A planner
    cannot make that separation true by accepting the caller's declarations.
    """
    if type(max_seconds) not in (int, float) or not 0 < max_seconds <= 60:
        _fail('INVALID_DEADLINE')
    deadline = time.monotonic() + max_seconds
    snapshot = _snapshot(scope)  # Freeze all bounded caller data before callbacks.

    def guard():
        try:
            stopped = cancelled()
        except Exception:
            _fail('CANCELLED')
        if type(stopped) is not bool or stopped:
            _fail('CANCELLED')
        if time.monotonic() >= deadline:
            _fail('DEADLINE_EXCEEDED')

    guard()
    reasons, planning_status, enforcement_status = _outcome(snapshot, guard)
    result = PrivatePolicyPlan(snapshot, tuple(reasons), planning_status, enforcement_status)
    guard()
    return result
