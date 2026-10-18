"""Pure, fail-closed migration of the repository's compact interview formats.

Returned state is an unsaved review candidate, never authorization. Caller aliases
are new labels, not proof that old facts belong to the current target/account.
"""
from copy import deepcopy
import json
import interview_flow as flow

COMPACT = 'guardian-interview/0.1'
REPORT = 'guardian-report/0.1'
# Exact field vocabulary emitted by guardian.py, including its initial release.
CHOICES = {
    'subscription_stage': flow.JOURNEYS,
    'current_task': {'renew', 'upgrade', 'environment', 'troubleshoot'},
    'os': {'macos', 'windows', 'unknown', 'phone_only'},
    'usage': {'web', 'desktop', 'code', 'ide_code', 'mixed', 'unknown'},
    'target_plan': None,
    'account_status': {'not_registered', 'active', 'suspended', 'unknown'},
    'device_history': {'new_to_claude', 'previous_use_no_reported_suspension',
                       'previous_use_with_reported_suspension', 'unknown'},
    'route': {'local', 'vm', 'vps', 'explain'},
}
# D.11 compatibility tombstones, accepted only at answers level, never loaded.
TOMBSTONES = {'Q-C07', 'account_ownership', 'account_control', 'Q-C08'}
REPORT_KEYS = {
    'schema_version', 'runtime_version', 'contract_provenance', 'record_kind',
    'operation', 'module_ids', 'run_ref', 'target_ref', 'target_binding',
    'contact_control', 'execution_status', 'check_status', 'inventory_readiness',
    'facts', 'evidence', 'findings', 'missing_fields', 'not_tested', 'next_actions',
    'changes', 'privacy', 'snapshot', 'limits', 'state',
}
NESTED_KEYS = {
    'target_binding': {'binding_state'},
    'contact_control': {'contact_phase', 'gate_state', 'pc_g1', 'pc_g2'},
    'privacy': {'shareable', 'redacted_preview', 'review_before_sharing',
                'raw_input_echoed', 'selected_input_values_included', 'persistence'},
    'snapshot': {'observed_at', 'clock_externally_verified'},
    'limits': {'collector_external_network', 'endpoints', 'native_platform_validation',
               'environment_pass_claim', 'account_safety_guarantee'},
}


class MigrationError(ValueError):
    """Sanitized error code, never the original untrusted input."""


def _reject(code):
    raise MigrationError(code)


def _screen(obj):
    if not isinstance(obj, dict):
        _reject('INVALID_LEGACY_SHAPE')
    projected = deepcopy(obj)
    payload = projected.get('state') if projected.get('schema_version') == REPORT else projected
    if isinstance(payload, dict) and isinstance(payload.get('answers'), dict):
        for key in TOMBSTONES:
            if key in payload['answers']:
                # Permit retired names only for discarding; still screen values.
                flow._safe(payload['answers'].pop(key))
    flow._safe(projected)
    encoded = json.dumps(obj, allow_nan=False)
    if len(encoded) > 250000:
        _reject('INPUT_TOO_LARGE')


def _unwrap(obj):
    if obj.get('schema_version') == COMPACT:
        return obj, False, 'compact'
    if obj.get('schema_version') != REPORT:
        _reject('UNSUPPORTED_LEGACY_VERSION')
    # Only one additive fixed producer member is allowed; historical wrappers
    # retain their exact shape. Policy data is never migrated as evidence/consent.
    if set(obj) not in (REPORT_KEYS, REPORT_KEYS | {'question'},
                        REPORT_KEYS | {'traffic_policy'}, REPORT_KEYS | {'question', 'traffic_policy'}):
        _reject('UNKNOWN_REPORT_SHAPE')
    if 'traffic_policy' in obj:
        value, expected = obj['traffic_policy'], flow.policy_projection()
        if (type(value) is not dict or set(value) != set(expected)
                or any(type(value[key]) is not type(want) or value[key] != want
                       for key, want in expected.items())):
            _reject('UNKNOWN_REPORT_SHAPE')
    if obj['operation'] != 'interview' or obj['module_ids'] != ['M00'] or obj['record_kind'] != 'offline_analysis':
        _reject('NOT_COMPACT_INTERVIEW_REPORT')
    for name, keys in NESTED_KEYS.items():
        if not isinstance(obj[name], dict) or set(obj[name]) != keys:
            _reject('UNKNOWN_REPORT_SHAPE')
    for name in ('runtime_version', 'contract_provenance', 'run_ref', 'check_status', 'inventory_readiness'):
        if not isinstance(obj[name], str):
            _reject('UNKNOWN_REPORT_SHAPE')
    if obj['target_ref'] is not None and not isinstance(obj['target_ref'], str):
        _reject('UNKNOWN_REPORT_SHAPE')
    boolean_fields = {'shareable', 'redacted_preview', 'review_before_sharing',
                      'raw_input_echoed', 'selected_input_values_included',
                      'clock_externally_verified', 'environment_pass_claim', 'account_safety_guarantee'}
    for name in NESTED_KEYS:
        for key, value in obj[name].items():
            if key in boolean_fields:
                if type(value) is not bool:
                    _reject('UNKNOWN_REPORT_SHAPE')
            elif not isinstance(value, str):
                _reject('UNKNOWN_REPORT_SHAPE')
    flow._validate_date(obj['snapshot']['observed_at'])
    for name in ('facts', 'evidence', 'changes', 'missing_fields'):
        if obj[name] != []:
            _reject('UNKNOWN_REPORT_SHAPE')
    for name in ('not_tested', 'next_actions'):
        if not isinstance(obj[name], list) or any(not isinstance(x, str) for x in obj[name]):
            _reject('UNKNOWN_REPORT_SHAPE')
    if not isinstance(obj['findings'], list) or any(
            not isinstance(x, dict) or set(x) != {'code', 'module_id'}
            or any(not isinstance(v, str) for v in x.values()) for x in obj['findings']):
        _reject('UNKNOWN_REPORT_SHAPE')
    if obj['execution_status'] not in {'completed', 'interrupted'}:
        _reject('UNKNOWN_REPORT_SHAPE')
    if 'question' in obj:
        q = obj['question']
        if not isinstance(q, dict) or set(q) != {'id', 'field', 'text', 'choices'} or q['field'] not in CHOICES:
            _reject('UNKNOWN_REPORT_SHAPE')
        if not isinstance(q['id'], str) or not isinstance(q['text'], str):
            _reject('UNKNOWN_REPORT_SHAPE')
        expected = CHOICES[q['field']]
        if expected is None:
            if q['choices'] is not None:
                _reject('UNKNOWN_REPORT_SHAPE')
        elif not isinstance(q['choices'], list) or any(not isinstance(v, str) for v in q['choices']) or set(q['choices']) != expected or len(q['choices']) != len(expected):
            _reject('UNKNOWN_REPORT_SHAPE')
    return obj['state'], obj['execution_status'] == 'interrupted', 'report.state'


def migrate_legacy(obj, *, target_alias=None, account_alias=None, task_id='task-1'):
    """Return actionable result and validated candidate; no reads/writes/contact.

    Retained answers are stale with unknown freshness/confidence and source-path
    provenance. The host must obtain fresh evidence before recording valid facts.
    """
    try:
        _screen(obj)
        payload, cancelled, origin = _unwrap(obj)
        if not isinstance(payload, dict) or payload.get('schema_version') != COMPACT or set(payload) not in (
                {'schema_version', 'answers'}, {'schema_version', 'answers', 'cancelled'}):
            _reject('INVALID_COMPACT_SHAPE')
        if 'cancelled' in payload and type(payload['cancelled']) is not bool:
            _reject('INVALID_COMPACT_SHAPE')
        answers = payload['answers']
        if not isinstance(answers, dict) or set(answers) - set(CHOICES) - TOMBSTONES:
            _reject('UNKNOWN_LEGACY_FIELD')
        for key, value in answers.items():
            if not isinstance(value, str) or not value.strip() or len(value) > 80:
                _reject('INVALID_LEGACY_VALUE')
            if key in CHOICES and CHOICES[key] is not None and value not in CHOICES[key]:
                _reject('INVALID_LEGACY_VALUE')
        if answers.get('subscription_stage') in {'first_subscription', 'returning_subscription'} and answers.get('current_task') in {'renew', 'upgrade'}:
            _reject('CONFLICTING_SUBSCRIPTION_FACTS')
        if answers.get('subscription_stage') == 'existing_subscriber' and answers.get('account_status') == 'not_registered':
            _reject('CONFLICTING_SUBSCRIPTION_FACTS')
        if not target_alias or not account_alias:
            _reject('FRESH_BINDING_REQUIRED')
        state = flow.new_state(target_alias, account_alias, task_id=task_id)
        mapping = {'subscription_stage': 'Q-J01', 'current_task': 'Q-C11', 'os': 'Q-C02',
                   'usage': 'Q-C01', 'target_plan': 'Q-C08', 'account_status': 'Q-C04', 'route': 'Q-C05'}
        discarded = sorted(set(answers) & TOMBSTONES)
        review_only = []
        # Device history is not the current model's ACCOUNT-bound ban history.
        if 'device_history' in answers:
            review_only.append({'field': 'device_history', 'value': answers['device_history'],
                                'source': 'legacy:' + origin + '.answers.device_history',
                                'confidence': 'unknown', 'binding': 'unverified'})
        for field, qid in mapping.items():
            if field not in answers:
                continue
            value = answers[field]
            value = {('os', 'phone_only'): 'mobile_only', ('route', 'explain'): 'compare',
                     ('account_status', 'not_registered'): 'unregistered'}.get((field, value), value)
            state['facts'][qid] = {
                'value': value, 'state': 'stale', 'source': 'legacy:' + origin + '.answers.' + field,
                'subject_ref': account_alias if qid in flow.ACCOUNT_QUESTIONS else target_alias,
                'observed_at': None, 'applies_when': 'only after target and fact reconfirmation',
                'required_for': ['intake', 'plan'], 'sensitivity': 'low', 'clarification_count': 0,
                'blocker_reason': 'Legacy confidence, freshness and subject binding are unverified',
            }
        state['context']['paused'] = cancelled or payload.get('cancelled', False)
        flow.validate_state(state)
        review_hints = []
        if answers.get('account_status') == 'suspended':
            review_hints.append({
                'code': 'RECONFIRM_ACCOUNT_SUSPENSION_BEFORE_INTAKE',
                'source': 'legacy:' + origin + '.answers.account_status',
                'next_step': 'Before presenting the ordinary next question, ask whether this stale account suspension report still applies to the current account; route confirmed incidents through current incident handling',
                'current_incident_verified': False,
            })
        return {'status': 'review_required', 'code': 'LEGACY_IMPORTED_UNVERIFIED', 'state': state,
                'next_step': 'Confirm target/account association and refresh relevant facts before continuing; save only with new explicit permission',
                'discarded_fields': discarded, 'review_only': review_only, 'review_hints': review_hints,
                'confidence': 'unknown', 'binding': 'unverified', 'saved': False, 'action_executed': False}
    except MigrationError as exc:
        code = str(exc)
    except (flow.InterviewError, ValueError, TypeError, RecursionError, KeyError):
        code = 'INVALID_OR_UNSAFE_LEGACY_INPUT'
    return {'status': 'blocked', 'code': code, 'state': None,
            'next_step': 'Provide a sanitized versioned guardian-interview/0.1 compact state and fresh target/account aliases; resolve conflicts explicitly',
            'saved': False, 'action_executed': False}
