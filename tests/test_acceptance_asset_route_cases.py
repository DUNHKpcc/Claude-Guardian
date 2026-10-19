"""Original T26/T33 normalized interview evidence; no generated dialogue claim.

Expected facts, complete state changes, prompts and assessments are independently
specified below. --replay emits actual deterministic receipts for private review.
GUARDIAN_AUDIT_ROOT can select a read-only frozen implementation for regression
comparison; fixture and test expectations always come from this test directory.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import shutil
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
import urllib.request

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', HERE.parent))
FLOW_PATH = ROOT / 'skills/claude-guardian/scripts/interview_flow.py'
SPEC = importlib.util.spec_from_file_location('asset_route_acceptance_flow', FLOW_PATH)
f = importlib.util.module_from_spec(SPEC)
# A frozen comparison root is read-only, including Python cache artifacts.
_previous_bytecode_policy = sys.dont_write_bytecode
sys.dont_write_bytecode = True
try:
    SPEC.loader.exec_module(f)
finally:
    sys.dont_write_bytecode = _previous_bytecode_policy
FIXTURE = json.loads((HERE / 'fixtures/acceptance-asset-route-cases.json').read_text(encoding='utf-8'))
SOURCE_CONTENTS = {path: (ROOT / path).read_bytes() for path in FIXTURE['source_pins']}
RUNTIME_PIN = hashlib.sha256(FLOW_PATH.read_bytes()).hexdigest()
TIME, ASSET_TIME, LATER = (FIXTURE[k] for k in ('base_observed_at', 'asset_observed_at', 'reply_observed_at'))
SOURCE = FIXTURE['base_source']
PERMISSIONS = {'private_save': False, 'export': False, 'public_export': False}
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
PROMPTS = {
    'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
    'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
    'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
}
# Exact normalized context contract, not obtained from the module under test.
CONTEXT = {
    'task': 'environment', 'incident': 'none', 'incident_resolved': False,
    'incident_origin': 'host', 'account_incident_resolved': False,
    'ambiguous_experience': False, 'subscription_conflict': False,
    'billing_channel': 'unselected', 'route': 'local', 'route_selection_basis': 'default_proposal',
    'contact_phase': 'PC0', 'os_issue': 'none', 'language_change_needed': False,
    'timezone_issue': False, 'windows10': False, 'compatibility_needed': False,
    'budget_needed': False, 'gift_card': False, 'buying_gift_card': False,
    'changing_store_region': False, 'organization_task': False,
    'billing_product_ambiguous': False, 'existing_test': False, 'integration_used': False,
    'change_planned': False, 'persistence_requested': False, 'purchase_completed': False,
    'paused': False, 'blocked_reason': None,
}
TRAFFIC = {
    'schema_version': 'guardian-traffic-policy/0.1',
    'requirement_id': 'PRODUCT-IPV4-20261018', 'effective_from': '2026-10-18',
    'policy': 'IPv4_ONLY', 'applies_to': 'claude_target_application_traffic',
    'ipv6_fallback': 'forbidden', 'proxy_outer_transport': 'preserve_existing_independently',
    'control_channels': 'preserve', 'other_applications': 'unchanged',
    'enforcement_status': 'unknown', 'compliance': 'not_established',
    'environment_pass': False, 'apply_supported': False, 'authorization': 'none',
}


@contextmanager
def offline():
    """Only wrap pure API calls; fixture/import/read and replay output are outside."""
    attempted = []

    def deny(target):
        def blocked(*args, **kwargs):
            attempted.append(target)
            raise AssertionError('Pure interview attempted external I/O: ' + target)
        return blocked

    with ExitStack() as stack:
        stack.enter_context(patch.object(f, '_now', return_value=TIME))
        for target in ('builtins.open', 'io.open', 'os.open', 'os.popen',
                       'socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                       'socket.gethostbyname', 'socket.gethostbyaddr', 'socket.getnameinfo',
                       'subprocess.Popen', 'subprocess.run', 'os.system',
                       'os.remove', 'os.unlink', 'os.rename', 'os.replace', 'os.mkdir',
                       'os.rmdir', 'shutil.rmtree', 'urllib.request.urlopen'):
            stack.enter_context(patch(target, side_effect=deny(target)))
        try:
            yield attempted
        finally:
            if attempted:
                raise AssertionError('Pure interview I/O sentinel fired: ' + ', '.join(attempted))


def envelope(qid, value, *, source=SOURCE, at=TIME, outcome='reported'):
    account = qid in {'Q-J01', 'Q-C03', 'Q-C04', 'Q-C06'}
    return {'value': deepcopy(value), 'state': outcome, 'source': source,
            'subject_ref': 'asset-account' if account else 'asset-device',
            'observed_at': at, 'applies_when': 'current task and target',
            'required_for': ['intake', 'plan'], 'sensitivity': 'low',
            'clarification_count': 0, 'blocker_reason': None}


def expected_state(*, goal=False, case=None):
    facts = {qid: envelope(qid, value) for qid, value in FIXTURE['common_facts'].items()}
    if goal:
        facts['Q-C01'] = envelope('Q-C01', FIXTURE['goal'])
    if case:
        item = FIXTURE['asset_cases'][case]
        facts.update({qid: envelope(qid, value, source=item['source'], at=ASSET_TIME)
                      for qid, value in item['facts'].items()})
    return {'schema_version': '1.0.0', 'task_id': 'asset-route-task',
            'target_alias': 'asset-device', 'account_alias': 'asset-account',
            'facts': facts, 'context': deepcopy(CONTEXT), 'asked_question_ids': [],
            'deferred_branches': [], 'current_subscription': {
                'status': 'active_reported', 'source': SOURCE, 'observed_at': TIME},
            'payment_intent': 'none', 'purchase_intent': 'none',
            'persistence_consent': deepcopy(PERMISSIONS)}


def expected_question(qid):
    if qid is None:
        return None
    return {'id': qid, 'branch': 'local' if qid == 'Q-L01' else 'core',
            'stage': {'Q-C01': 'I2', 'Q-C05': 'I3', 'Q-L01': 'I5'}[qid],
            'postcontact': False, 'prompt': PROMPTS[qid], 'clarification': False,
            'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
            'requires_action_authorization': False}


def expected_assessment(*, goal=False, outcome='unasked', accepted=False):
    gaps = ([] if goal else [{'id': 'Q-C01', 'reason': 'unasked'}])
    gaps += ([{'id': 'Q-L01', 'reason': 'unasked'}, {'id': 'Q-L04', 'reason': 'unasked'}]
             if accepted else [{'id': 'Q-C05', 'reason': outcome}])
    return {'traffic_policy': deepcopy(TRAFFIC),
            'stage': 'I2' if not goal else 'I5' if accepted else 'I3',
            'G1': {'status': 'partial', 'unresolved_fields': gaps},
            'G2': {'status': 'blocked', 'conditional_plan_only': True}, 'G3': deepcopy(G3),
            'active_branches': ['core', 'os', 'network'] + (['local'] if accepted else []) + ['protection'],
            'deferred_branches': [], 'route_confirmation': 'confirmed' if accepted else 'unconfirmed',
            'current_subscription': {'status': 'active_reported', 'source': SOURCE, 'observed_at': TIME}}


def base(*, goal=False):
    values = deepcopy(FIXTURE['common_facts'])
    if goal:
        values['Q-C01'] = FIXTURE['goal']
    return f.record_facts(f.new_state('asset-device', 'asset-account', task_id='asset-route-task'),
                          [{'question_id': qid, 'value': value} for qid, value in values.items()], source=SOURCE)


def assets(case, *, goal=False, original=None):
    item = FIXTURE['asset_cases'][case]
    state = base(goal=goal) if original is None else original
    for qid, value in item['facts'].items():
        state = f.record_fact(state, qid, deepcopy(value), source=item['source'], observed_at=ASSET_TIME)
    return state


def reply(state, value=None, *, outcome='reported'):
    return f.record_fact(state, 'Q-C05', value, state_name=outcome,
                         source='synthetic:route-reply', observed_at=LATER, current_reply=True)


def snapshot(state):
    return {'state': deepcopy(state), 'next_question': f.next_question(state),
            'applicable_questions': f.applicable_questions(state), 'assessment': f.assessment(state)}


def compare_proposal_acceptance():
    before = assets('mixed_assets', goal=True)
    compared = reply(before, 'compare')
    # Host actually explains the choices and offers local. This does not record
    # user agreement and does not fabricate a new Q-C05 reply or an explanation.
    proposed = f.set_context(compared, route='local', route_selection_basis='default_proposal')
    accepted = f.record_fact(proposed, 'Q-C05', 'accepted_default',
                             source='synthetic:accept-actual-local-proposal',
                             observed_at='2026-10-19T00:03:00Z', current_reply=True)
    return before, compared, proposed, accepted


def replay():
    with offline() as attempted:
        result = {'kind': 'actual_normalized_API_replay', 'model_dialogue_run': False,
                  'source_pins': deepcopy(FIXTURE['source_pins']), 'runtime_sha256': RUNTIME_PIN,
                  'limits': deepcopy(FIXTURE['limits']), 'T26': {}, 'T33': {}}
        for case in FIXTURE['asset_cases']:
            state = assets(case)
            goal = f.record_fact(state, 'Q-C01', FIXTURE['goal'],
                                 source='synthetic:actual-goal-reply', observed_at=LATER)
            result['T26'][case] = {'asset_only': snapshot(state), 'actual_goal_reply': snapshot(goal),
                                   'private_roundtrip': snapshot(f.loads_state(f.dumps_state(goal, host_opt_in=True)))}
        for outcome in ('unknown', 'declined', 'deferred'):
            state = reply(assets('mixed_assets', goal=True), outcome=outcome)
            result['T33'][outcome] = snapshot(state)
        result['T33']['compare_then_actual_local_proposal_then_accept'] = [snapshot(s) for s in compare_proposal_acceptance()]
        original = assets('mixed_assets', goal=True)
        payload = {'nested': {'details': ['owned_server_reported']}}
        recorded = f.record_fact(original, 'Q-S02', payload, source='synthetic:isolation', observed_at=LATER)
        prior = deepcopy(recorded)
        serialized_before = f.dumps_state(recorded, host_opt_in=True)
        payload['nested']['details'].append('caller_mutated_after_recording')
        result['preservation_receipt'] = {
            'recorded_before_caller_mutation': snapshot(prior),
            'recorded_after_caller_mutation': snapshot(recorded),
            'same_state': recorded == prior,
            'same_serialization': f.dumps_state(recorded, host_opt_in=True) == serialized_before,
            'previous_serialization_still_original': f.loads_state(serialized_before) == prior}
        result['io_boundary'] = {'attempted_calls': list(attempted),
                                  'scope': 'pure interview APIs only; fixture reads and JSON output excluded'}
        return result


class AssetRouteAcceptanceTests(unittest.TestCase):
    def setUp(self):
        boundary = offline()
        boundary.__enter__()
        self.addCleanup(boundary.__exit__, None, None, None)

    def assert_route_closed(self, state):
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(state['persistence_consent'], PERMISSIONS)
        self.assertEqual(state['payment_intent'], 'none')
        self.assertEqual(state['purchase_intent'], 'none')
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(f.assessment(state)['traffic_policy'], TRAFFIC)

    def assert_asset_case(self, case):
        state = assets(case)
        before = deepcopy(state)
        self.assertEqual(state, expected_state(case=case))
        self.assertEqual(f.next_question(state), expected_question('Q-C01'))
        self.assertEqual(f.assessment(state), expected_assessment())
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(state)))
        self.assertEqual(state, before)
        self.assert_route_closed(state)

    def test_original_T26_T33_clauses_layers_and_source_pins(self):
        for path, digest in FIXTURE['source_pins'].items():
            self.assertEqual(hashlib.sha256(SOURCE_CONTENTS[path]).hexdigest(), digest)
        text = SOURCE_CONTENTS['skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md'].decode('utf-8')
        for qid, clause in FIXTURE['original_requirements'].items():
            self.assertIn(f"| {qid} | {clause['scenario']} | {clause['requirement']} |", text)
            self.assertEqual(clause['layers'], 'L+C')

    def test_T26_vps_asset_without_goal_preserves_exact_state_and_asks_goal(self):
        self.assert_asset_case('vps_only')

    def test_T26_vm_history_without_goal_preserves_exact_state_and_asks_goal(self):
        self.assert_asset_case('vm_history_only')

    def test_T26_mixed_assets_without_goal_do_not_select_any_route(self):
        self.assert_asset_case('mixed_assets')

    def test_T26_known_goal_is_reused_and_exact_route_question_is_next(self):
        for case in FIXTURE['asset_cases']:
            with self.subTest(case=case):
                state = assets(case, goal=True)
                self.assertEqual(state, expected_state(goal=True, case=case))
                self.assertEqual(f.next_question(state), expected_question('Q-C05'))
                self.assertEqual(f.assessment(state), expected_assessment(goal=True))
                self.assert_route_closed(state)

    def test_T26_actual_goal_reply_preserves_every_asset_envelope(self):
        original = assets('mixed_assets')
        expected = deepcopy(original)
        expected['facts']['Q-C01'] = envelope('Q-C01', FIXTURE['goal'], source='synthetic:goal', at=LATER)
        result = f.record_fact(original, 'Q-C01', FIXTURE['goal'], source='synthetic:goal', observed_at=LATER)
        self.assertEqual(result, expected)
        self.assertEqual(original, expected_state(case='mixed_assets'))
        self.assertEqual(f.next_question(result), expected_question('Q-C05'))
        self.assertEqual(f.assessment(result), expected_assessment(goal=True))

    def test_T26_showing_route_question_neither_answers_nor_confirms(self):
        original = assets('mixed_assets', goal=True)
        expected = deepcopy(original)
        expected['asked_question_ids'] = ['Q-C05']
        shown = f.mark_asked(original, 'Q-C05')
        self.assertEqual(shown, expected)
        self.assertIsNone(f.next_question(shown))
        self.assertEqual(f.assessment(shown), expected_assessment(goal=True))
        self.assertEqual(original, expected_state(goal=True, case='mixed_assets'))

    def test_T26_expertise_followup_does_not_turn_asset_into_route(self):
        original = assets('mixed_assets', goal=True)
        expected = deepcopy(original)
        expected['facts']['Q-C10'] = envelope('Q-C10', 'expert_short_checklist', source='synthetic:depth', at=LATER)
        result = f.record_fact(original, 'Q-C10', 'expert_short_checklist', source='synthetic:depth', observed_at=LATER)
        self.assertEqual(result, expected)
        self.assertEqual(f.next_question(result), expected_question('Q-C05'))
        self.assertEqual(f.assessment(result), expected_assessment(goal=True))

    def test_T26_asset_mentions_preserve_preexisting_explicit_local_choice(self):
        original = reply(base(goal=True), 'local')
        expected = deepcopy(original)
        item = FIXTURE['asset_cases']['mixed_assets']
        for qid, value in item['facts'].items():
            expected['facts'][qid] = envelope(qid, value, source=item['source'], at=ASSET_TIME)
        result = assets('mixed_assets', original=original)
        self.assertEqual(result, expected)
        self.assertEqual(f.next_question(result), expected_question('Q-L01'))
        self.assertEqual(f.assessment(result), expected_assessment(goal=True, accepted=True))
        self.assertFalse(any(q['branch'] in {'vm', 'vps'} for q in f.applicable_questions(result)))
        self.assert_route_closed(result)

    def test_T26_batch_assets_and_goal_are_absorbed_without_route_inference(self):
        original = base()
        item = FIXTURE['asset_cases']['mixed_assets']
        answers = [{'question_id': qid, 'value': deepcopy(value)} for qid, value in item['facts'].items()]
        answers.append({'question_id': 'Q-C01', 'value': FIXTURE['goal']})
        with patch.object(f, '_now', return_value=ASSET_TIME):
            result = f.record_facts(original, answers, source=item['source'])
        expected = expected_state(case='mixed_assets')
        expected['facts']['Q-C01'] = envelope('Q-C01', FIXTURE['goal'], source=item['source'], at=ASSET_TIME)
        self.assertEqual(result, expected)
        self.assertEqual(f.next_question(result), expected_question('Q-C05'))
        self.assertEqual(original, expected_state())

    def test_T26_wrong_asset_subject_is_rejected_without_mutation(self):
        original = assets('mixed_assets', goal=True)
        before = deepcopy(original)
        with self.assertRaisesRegex(f.InterviewError, 'Fact target mismatch'):
            f.record_fact(original, 'Q-S02', {'asset': 'owned_vps'}, source='synthetic:wrong-target', subject_ref='other-device', observed_at=LATER)
        self.assertEqual(original, before)

    def test_T26_secret_asset_detail_is_rejected_atomically(self):
        original = base()
        before = deepcopy(original)
        with self.assertRaises(f.InterviewError):
            f.record_facts(original, [
                {'question_id': 'Q-C01', 'value': FIXTURE['goal']},
                {'question_id': 'Q-S02', 'value': {'private_key': 'synthetic_rejected_marker'}}], source='synthetic:unsafe')
        self.assertEqual(original, before)

    def test_T26_single_asset_nested_dict_is_detached_from_caller(self):
        original = base()
        payload = {'resources': {'reported': ['server_exists']}}
        expected = deepcopy(original)
        expected['facts']['Q-S02'] = envelope('Q-S02', payload, source='synthetic:mutable', at=ASSET_TIME)
        result = f.record_fact(original, 'Q-S02', payload, source='synthetic:mutable', observed_at=ASSET_TIME)
        payload['resources']['reported'].append('caller_changed_later')
        self.assertEqual(result, expected)
        self.assertEqual(original, expected_state())

    def test_T26_single_asset_list_is_detached_from_caller(self):
        original = base()
        payload = ['installed_vm_before', {'current_route': 'undecided'}]
        expected = deepcopy(original)
        expected['facts']['Q-V01'] = envelope('Q-V01', payload, source='synthetic:mutable-list', at=ASSET_TIME)
        result = f.record_fact(original, 'Q-V01', payload, source='synthetic:mutable-list', observed_at=ASSET_TIME)
        payload[1]['current_route'] = 'caller_changed_later'
        payload.append('another_caller_change')
        self.assertEqual(result, expected)

    def test_T26_batch_final_asset_value_is_detached_from_caller(self):
        original = base()
        payload = {'history': ['installed_vm_before'], 'current_route': {'value': 'undecided'}}
        answers = [{'question_id': 'Q-C01', 'value': FIXTURE['goal']}, {'question_id': 'Q-V01', 'value': payload}]
        with patch.object(f, '_now', return_value=ASSET_TIME):
            result = f.record_facts(original, answers, source='synthetic:mutable-batch')
        expected = deepcopy(original)
        expected['facts']['Q-C01'] = envelope('Q-C01', FIXTURE['goal'], source='synthetic:mutable-batch', at=ASSET_TIME)
        expected['facts']['Q-V01'] = envelope('Q-V01', payload, source='synthetic:mutable-batch', at=ASSET_TIME)
        answers[1]['value']['history'].append('caller_changed_later')
        self.assertEqual(result, expected)
        self.assertEqual(original, expected_state())

    def test_T26_returned_asset_value_does_not_mutate_caller_input(self):
        payload = {'resources': [{'reported': 'server_exists'}]}
        before = deepcopy(payload)
        result = f.record_fact(base(), 'Q-S02', payload, source='synthetic:result-mutation', observed_at=ASSET_TIME)
        result['facts']['Q-S02']['value']['resources'][0]['reported'] = 'changed_result'
        self.assertEqual(payload, before)

    def test_T26_scalar_fact_and_private_serialization_keep_recorded_value(self):
        payload = 'owned_vps_reported'
        state = f.record_fact(base(), 'Q-S02', payload, source='synthetic:scalar', observed_at=ASSET_TIME)
        saved = f.dumps_state(state, host_opt_in=True)
        expected = deepcopy(state)
        payload = 'caller_reassigned'
        state['facts']['Q-S02']['value'] = 'returned_state_mutated'
        self.assertEqual(f.loads_state(saved), expected)
        self.assertEqual(expected['facts']['Q-S02']['value'], 'owned_vps_reported')

    def test_T26_serialized_receipt_and_live_fact_agree_after_caller_mutation(self):
        payload = {'asset': {'reported': ['owned_vps']}}
        result = f.record_fact(base(), 'Q-S02', payload, source='synthetic:serialized-isolation', observed_at=ASSET_TIME)
        saved = f.dumps_state(result, host_opt_in=True)
        payload['asset']['reported'].append('caller_changed_later')
        self.assertEqual(f.dumps_state(result, host_opt_in=True), saved)
        self.assertEqual(f.loads_state(saved), result)

    def assert_terminal(self, outcome):
        original = assets('mixed_assets', goal=True)
        result = reply(original, outcome=outcome)
        expected = deepcopy(original)
        expected['facts']['Q-C05'] = envelope('Q-C05', None, source='synthetic:route-reply', at=LATER, outcome=outcome)
        self.assertEqual(result, expected)
        for _ in range(3):
            self.assertIsNone(f.next_question(result))
            self.assertEqual(f.assessment(result), expected_assessment(goal=True, outcome=outcome))
        self.assertEqual(f.loads_state(f.dumps_state(result, host_opt_in=True)), expected)
        self.assert_route_closed(result)
        self.assertEqual(original, expected_state(goal=True, case='mixed_assets'))

    def test_T33_unknown_is_not_a_choice_and_is_not_a_repeated_quiz(self):
        self.assert_terminal('unknown')

    def test_T33_declined_is_not_a_choice_and_stops_automatic_repetition(self):
        self.assert_terminal('declined')

    def test_T33_deferred_is_not_a_choice_and_stops_automatic_repetition(self):
        self.assert_terminal('deferred')

    def test_T33_compare_has_exact_unconfirmed_state_and_no_remote_questions(self):
        original = assets('mixed_assets', goal=True)
        compared = reply(original, 'compare')
        expected = deepcopy(original)
        expected['facts']['Q-C05'] = envelope('Q-C05', 'compare', source='synthetic:route-reply', at=LATER)
        expected['context']['route'] = 'compare'
        self.assertEqual(compared, expected)
        self.assertIsNone(f.next_question(compared))
        self.assertEqual(f.assessment(compared), expected_assessment(goal=True, outcome='route_unconfirmed'))
        self.assert_route_closed(compared)

    def test_T33_actual_local_proposal_then_acceptance_is_not_an_extra_quiz(self):
        original, compared, proposed, accepted = compare_proposal_acceptance()
        expected_proposal = deepcopy(compared)
        expected_proposal['context']['route'] = 'local'
        self.assertEqual(proposed, expected_proposal)
        self.assertEqual(proposed['facts'], compared['facts'])
        self.assertEqual(f.assessment(proposed), expected_assessment(goal=True, outcome='route_unconfirmed'))
        expected_accepted = deepcopy(proposed)
        expected_accepted['context']['route_selection_basis'] = 'accepted_default'
        expected_accepted['facts']['Q-C05'] = envelope('Q-C05', 'accepted_default', source='synthetic:accept-actual-local-proposal', at='2026-10-19T00:03:00Z')
        self.assertEqual(accepted, expected_accepted)
        self.assertEqual(f.next_question(accepted), expected_question('Q-L01'))
        self.assertEqual(f.assessment(accepted), expected_assessment(goal=True, accepted=True))
        self.assertNotIn('Q-C05', [q['id'] for q in f.applicable_questions(accepted)])
        self.assertFalse(any(q['branch'] in {'vm', 'vps'} for q in f.applicable_questions(accepted)))
        self.assert_route_closed(accepted)
        self.assertEqual(original, expected_state(goal=True, case='mixed_assets'))

    def test_T33_unknown_can_later_accept_the_current_local_proposal(self):
        unknown = reply(assets('mixed_assets', goal=True), outcome='unknown')
        accepted = reply(unknown, 'accepted_default')
        expected = deepcopy(unknown)
        expected['context']['route_selection_basis'] = 'accepted_default'
        expected['facts']['Q-C05'] = envelope('Q-C05', 'accepted_default', source='synthetic:route-reply', at=LATER)
        self.assertEqual(accepted, expected)
        self.assertEqual(f.next_question(accepted), expected_question('Q-L01'))
        self.assertEqual(f.assessment(accepted), expected_assessment(goal=True, accepted=True))
        self.assert_route_closed(accepted)

    def test_T33_explicit_local_after_comparison_preserves_explicit_basis(self):
        compared = reply(assets('mixed_assets', goal=True), 'compare')
        explicit = reply(compared, 'local')
        expected = deepcopy(compared)
        expected['context'].update(route='local', route_selection_basis='explicit_choice')
        expected['facts']['Q-C05'] = envelope('Q-C05', 'local', source='synthetic:route-reply', at=LATER)
        self.assertEqual(explicit, expected)
        self.assertEqual(f.assessment(explicit), expected_assessment(goal=True, accepted=True))

    def test_T33_accept_default_cannot_overwrite_other_choice_or_missing_proposal(self):
        for route in ('local', 'vm', 'vps', 'compare'):
            with self.subTest(route=route):
                chosen = reply(assets('mixed_assets', goal=True), route)
                before = deepcopy(chosen)
                with self.assertRaisesRegex(f.InterviewError, '^No current local default proposal to accept$'):
                    reply(chosen, 'accepted_default')
                self.assertEqual(chosen, before)
                self.assert_route_closed(chosen)

    def test_T33_inferred_acceptance_does_not_create_user_agreement(self):
        original = assets('mixed_assets', goal=True)
        inferred = reply(original, 'accepted_default', outcome='inferred')
        expected = deepcopy(original)
        expected['facts']['Q-C05'] = envelope('Q-C05', 'accepted_default', source='synthetic:route-reply', at=LATER, outcome='inferred')
        self.assertEqual(inferred, expected)
        self.assertEqual(f.assessment(inferred), expected_assessment(goal=True, outcome='inferred'))
        self.assertIsNone(f.next_question(inferred))
        self.assert_route_closed(inferred)

    def test_T33_accepted_default_exact_replay_preserves_original_receipt(self):
        *_, accepted = compare_proposal_acceptance()
        before = deepcopy(accepted)
        replayed = f.record_fact(accepted, 'Q-C05', 'accepted_default', source='synthetic:accept-actual-local-proposal', observed_at='2026-10-19T00:03:00Z')
        self.assertEqual(replayed, before)
        loaded = f.loads_state(f.dumps_state(replayed, host_opt_in=True))
        self.assertEqual(loaded, before)
        self.assertEqual(f.next_question(loaded), expected_question('Q-L01'))
        self.assert_route_closed(loaded)

    def test_T33_private_serialization_requires_scoped_opt_in(self):
        state = assets('mixed_assets', goal=True)
        before = deepcopy(state)
        with self.assertRaisesRegex(f.InterviewError, 'Explicit host opt-in'):
            f.dumps_state(state)
        with self.assertRaisesRegex(f.InterviewError, 'Public export requires'):
            f.dumps_state(state, host_opt_in=True, scope='public_export')
        saved = f.dumps_state(state, host_opt_in=True)
        expected_saved = deepcopy(before)
        expected_saved['persistence_consent']['private_save'] = True
        self.assertEqual(json.loads(saved), expected_saved)
        self.assertEqual(f.loads_state(saved), before)
        self.assertEqual(state, before)

    def test_T33_deferred_core_branch_preserves_assets_and_choice_gap(self):
        state = assets('mixed_assets', goal=True)
        deferred = f.defer_branch(state, 'core')
        expected = deepcopy(state)
        expected['deferred_branches'] = ['core']
        self.assertEqual(deferred, expected)
        self.assertIsNone(f.next_question(deferred))
        assessment = f.assessment(deferred)
        self.assertEqual(assessment['route_confirmation'], 'unconfirmed')
        self.assertEqual(assessment['G2'], {'status': 'blocked', 'conditional_plan_only': True})
        self.assertIn({'id': 'Q-C05', 'reason': 'branch_deferred'}, assessment['G1']['unresolved_fields'])
        resumed = f.resume_branch(deferred, 'core')
        self.assertEqual(resumed, state)
        self.assertEqual(f.next_question(resumed), expected_question('Q-C05'))
        self.assert_route_closed(resumed)

    def test_T33_render_and_returned_snapshot_do_not_mutate_state(self):
        state = assets('mixed_assets', goal=True)
        before = deepcopy(state)
        captured = snapshot(state)
        captured['state']['facts']['Q-S02']['value']['resources']['known'].append('snapshot_only')
        captured['assessment']['G1']['unresolved_fields'].clear()
        self.assertEqual(state, before)
        self.assertEqual(f.assessment(state), expected_assessment(goal=True))


if __name__ == '__main__':
    emit_replay = '--replay' in sys.argv
    if emit_replay:
        sys.argv.remove('--replay')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(AssetRouteAcceptanceTests))
    if emit_replay:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    sys.exit(not result.wasSuccessful())
