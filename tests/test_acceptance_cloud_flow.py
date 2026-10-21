"""Cloud acceptance replays for twelve cases without earlier dialogue evidence (interview flow family).

Cases: T14, T30, T32, T41, T52, T56, T68, T85, ENV-T02, ENV-T36, ENV-T92, ENV-T96.

Normalized synthetic host facts only. This is not natural-language parsing, a model evaluation, a native
observation, a purchase, a contact, or proof of any real authorization. Expectations are authored here from the
original requirement text; none is copied from runtime output. Run with --replay to print the actual observations.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
spec = importlib.util.spec_from_file_location('cloud_flow_interview', SCRIPTS / 'interview_flow.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
TIME = '2026-10-21T08:00:00Z'
G3_REASON = ('Interview answers are not specific action authorization; '
             'action and contact gates must be checked separately')
GUIDE = {name: (ROOT / 'skills/claude-guardian' / name).read_text(encoding='utf-8')
         for name in ('SKILL.md', 'references/intake.md', 'references/routes-and-platforms.md',
                      'references/accounts-and-payments.md')}
FORBIDDEN_IO = ('builtins.open', 'io.open', 'os.open', 'socket.socket', 'subprocess.Popen', 'os.system')


def new(task='subscription_preparation'):
    state = f.new_state('flow-device', 'flow-account', task_id='flow-task')
    return f.set_context(state, task=task) if task != 'subscription_preparation' else state


def facts(state, pairs, source):
    return f.record_facts(state, [{'question_id': q, 'value': v} for q, v in pairs], source=source)


def ids(state):
    return [q['id'] for q in f.applicable_questions(state)]


def unresolved(state):
    return [item['id'] for item in f.assessment(state)['G1']['unresolved_fields']]


def drain(state, known, limit=60):
    """Answer every next question with a placeholder; return the ordered ids that were actually asked."""
    asked = []
    for _ in range(limit):
        question = f.next_question(state)
        if question is None:
            break
        asked.append(question['id'])
        state = f.record_fact(state, question['id'], known.get(question['id'], 'synthetic_reported'),
                              source='synthetic:drain')
    return asked, state


def gates(state):
    assessment = f.assessment(state)
    return {'g3': assessment['G3']['status'], 'phase': state['context']['contact_phase'],
            'consent': deepcopy(state['persistence_consent'])}


def record_refused(qid):
    try:
        f.record_fact(new(), qid, 'synthetic', source='synthetic:retired')
    except f.InterviewError as error:
        return str(error)
    return 'accepted'


def observe():
    out = {}

    # T30: one sentence supplies system, plan, account and payment preference together.
    state = facts(new(), [('Q-J01', 'first_subscription'), ('Q-C02', 'macos'), ('Q-C08', 'Pro'),
                          ('Q-C04', 'registered_reported'), ('Q-P06', 'web')], 'synthetic:T30')
    asked, _ = drain(state, {})
    out['T30'] = {'known': sorted(state['facts']), 'first_gap': f.next_question(state)['id'],
                  'unresolved_has_known': [q for q in unresolved(state)
                                           if q in ('Q-J01', 'Q-C02', 'Q-C08', 'Q-C04', 'Q-P06')],
                  'asked_after_batch': asked, 'gates': gates(state)}

    # ENV-T02: device A answers are reused; moving to an unbound device keeps only account/subscription facts.
    a = facts(new('environment'), [('Q-J01', 'existing_subscriber'), ('Q-C02', 'macos'),
                                   ('Q-N01', 'proxy_clash_rule_mode'), ('Q-N02', 'system_proxy')], 'synthetic:ENV-T02')
    asked_a, _ = drain(a, {})
    b = f.begin_task(a, task_id='flow-task-b', task='environment', target_alias='device-b')
    asked_b, _ = drain(b, {})
    out['ENV-T02'] = {'device_a_asked': asked_a, 'device_b_facts': sorted(b['facts']),
                      'device_b_subscription': b['current_subscription']['status'],
                      'device_b_first': f.next_question(b)['id'], 'device_b_asked': asked_b}

    # ENV-T96: stage, OS, route and plan supplied; only the authorization question stays separate.
    state = facts(new(), [('Q-J01', 'first_subscription'), ('Q-C02', 'macos'), ('Q-C05', 'local'),
                          ('Q-C08', 'Pro')], 'synthetic:ENV-T96')
    asked, done = drain(state, {'Q-Z01': 'plan_only'})
    out['ENV-T96'] = {'asked': asked, 'retired_listed': 'Q-C07' in ids(state),
                      'z01': done['facts']['Q-Z01']['value'], 'gates': gates(done)}

    # ENV-T36: first-time subscriber at the environment stage.
    state = facts(new('environment'), [('Q-J01', 'first_subscription')], 'synthetic:ENV-T36')
    asked, _ = drain(state, {})
    out['ENV-T36'] = {'listed_old': [q for q in ('Q-C07', 'Q-P02', 'Q-A06', 'Q-C11', 'Q-C13') if q in ids(state)],
                      'asked_old': [q for q in asked if q in ('Q-C07', 'Q-P02', 'Q-A06', 'Q-C11', 'Q-C13', 'Q-J01')],
                      'journey': f.journey(state)}

    # ENV-T92: a saved old state carrying the retired Q-C07 is refused; first subscription never asks old items.
    old = deepcopy(new())
    old['facts']['Q-C07'] = {}
    refused = False
    try:
        f.validate_state(old)
    except f.InterviewError:
        refused = True
    reply = facts(new(), [('Q-J01', 'first_subscription'), ('Q-C04', 'registered_reported')], 'synthetic:ENV-T92')
    out['ENV-T92'] = {'retired': f.RETIRED, 'saved_c07_refused': refused,
                      'c07_in_schema': 'Q-C07' in f.STATE_SCHEMA['properties']['facts']['properties'],
                      'c07_prompt': f.QUESTION_PROMPTS.get('Q-C07'),
                      'c07_record_refused': record_refused('Q-C07'),
                      'old_entitlement_listed': [q for q in ('Q-P02', 'Q-A06') if q in ids(reply)],
                      'login_fact_state': reply['facts']['Q-C04']['state'], 'gates': gates(reply)}

    # T52: history profile versus a current answer.
    base = f.record_fact(new(), 'Q-C02', 'macos', source='history:profile-2026-09')
    wrong_device = wrong_role = None
    for key, subject in (('device', 'other-device'), ('role', 'flow-account')):
        try:
            f.record_fact(base, 'Q-C02', 'windows', subject_ref=subject, source='user:today')
            outcome = 'accepted'
        except f.InterviewError:
            outcome = 'refused'
        if key == 'device':
            wrong_device = outcome
        else:
            wrong_role = outcome
    flagged = f.record_fact(base, 'Q-C02', 'windows', state_name='conflict', source='user:today')
    clar = f.mark_asked(flagged, 'Q-C02')
    moved = f.begin_task(f.record_fact(base, 'Q-J01', 'existing_subscriber', source='user:today'),
                         task_id='flow-task-b', task='environment', target_alias='device-b')
    other_account = f.begin_task(base, task_id='flow-task-c', task='environment', account_alias='account-b')
    out['T52'] = {'original_untouched': base['facts']['Q-C02']['value'],
                  'other_device_answer': wrong_device, 'wrong_subject_role': wrong_role,
                  'flagged_state': flagged['facts']['Q-C02']['state'],
                  'flagged_keeps_new_source': flagged['facts']['Q-C02']['source'],
                  'after_one_ask_next_is_not_c02': f.next_question(clar)['id'] != 'Q-C02',
                  'new_device_facts': sorted(moved['facts']),
                  'new_device_subscription': moved['current_subscription']['status'],
                  'new_account_facts': sorted(other_account['facts']),
                  'same_target_newer_answer_replaces_value':
                      f.record_fact(base, 'Q-C02', 'windows', source='user:today')['facts']['Q-C02']['value']}

    # T56: completion counts only the applicable branches; no numeric score exists.
    local = f.set_context(new(), route='local', route_selection_basis='explicit_choice')
    vps = f.set_context(new(), route='vps', route_selection_basis='explicit_choice')
    deferred = f.defer_branch(local, 'payment')
    out['T56'] = {'assessment_keys': sorted(f.assessment(local)),
                  'g1_keys': sorted(f.assessment(local)['G1']),
                  'local_route_questions': [q for q in ids(local) if q.startswith('Q-L')],
                  'vps_route_questions': [q for q in ids(vps) if q.startswith('Q-L')],
                  'deferred_branches': f.assessment(deferred)['deferred_branches'],
                  'deferred_payment_reasons': sorted({u['reason'] for u in f.assessment(deferred)['G1']['unresolved_fields']
                                                      if u['id'].startswith(('Q-P', 'Q-A', 'Q-W', 'Q-G'))}),
                  'g1_statuses': sorted({f.assessment(s)['G1']['status'] for s in (local, vps, deferred)})}

    # T85: first-time user does not know which plan: no default top tier, no entitlement question, no purchase.
    state = facts(new(), [('Q-J01', 'first_subscription'), ('Q-C08', 'undecided')], 'synthetic:T85')
    budget = f.set_context(state, budget_needed=True)
    asked, _ = drain(budget, {})
    out['T85'] = {'plan_fact': state['facts']['Q-C08']['value'], 'plan_prompt': f.QUESTION_PROMPTS['Q-C08'],
                  'budget_question_listed': 'Q-P05' in ids(budget),
                  'old_entitlement_listed': [q for q in ('Q-P02', 'Q-A06', 'Q-C11', 'Q-C13') if q in ids(budget)],
                  'gift_card_purchase_question_listed': 'Q-A07' in ids(budget),
                  'asked_old': [q for q in asked if q in ('Q-P02', 'Q-A06', 'Q-C11', 'Q-C13')],
                  'gates': gates(budget)}

    # T14: the user only wants a spec: plan-only, closed gates, no action question granted.
    state = f.record_fact(new(), 'Q-Z01', 'plan_only', source='synthetic:T14')
    assessment = f.assessment(state)
    out['T14'] = {'z01': state['facts']['Q-Z01']['value'], 'g2': assessment['G2'], 'gates': gates(state),
                  'question_requires_action_authorization':
                      f.next_question(state).get('requires_action_authorization')}

    # T32: the user says "banned"; the evidence is a declined card. Triage first identifies the object, and the
    # corrected answers leave no account-suspension incident.
    claimed = f.record_fact(new('billing_issue'), 'Q-C03', 'current_suspension', source='synthetic:T32-claim')
    question = f.next_question(claimed)
    corrected = f.record_fact(claimed, 'Q-H01', 'payment_card', source='synthetic:T32-correction')
    corrected = f.record_fact(corrected, 'Q-C03', 'payment_declined_not_suspension', source='synthetic:T32-correction')
    corrected = f.record_fact(corrected, 'Q-W03', 'card_declined', source='synthetic:T32-correction')
    out['T32'] = {'claimed_g1': f.assessment(claimed)['G1']['status'], 'claimed_stage': f.assessment(claimed)['stage'],
                  'claimed_next_id': question['id'], 'claimed_next_prompt': question['prompt'],
                  'corrected_g1': f.assessment(corrected)['G1']['status'],
                  'corrected_stage': f.assessment(corrected)['stage'],
                  'corrected_facts': {q: corrected['facts'][q]['value'] for q in ('Q-H01', 'Q-C03', 'Q-W03')},
                  'task': corrected['context']['task'], 'gates': gates(corrected)}

    # T41: first-time user without conflict is not asked about old billing; an actual page conflict reopens it.
    state = facts(new(), [('Q-J01', 'first_subscription'), ('Q-C08', 'Pro')], 'synthetic:T41')
    conflict = f.report_subscription_conflict(state, source='synthetic:T41-page', observed_at=TIME, current_reply=True)
    out['T41'] = {'without_conflict': [q for q in ('Q-P02', 'Q-A06') if q in ids(state)],
                  'with_conflict': [q for q in ('Q-P02', 'Q-A06') if q in ids(conflict)],
                  'next_after_conflict': f.next_question(conflict)['id'],
                  'g2': f.assessment(conflict)['G2'], 'gates': gates(conflict)}
    return out


def linux_local():
    """T68 through the real analyzer CLI (outside the no-I/O sentinels)."""
    result = {}
    for declared in ('linux', 'macos'):
        report = {'schema_version': 'guardian-offline/0.1', 'target_ref': 'device-1',
                  'record_kind': 'synthetic_example',
                  'target_binding': {'declared_os': declared, 'desktop_user_relation': 'same',
                                     'filesystem_namespace': 'host_desktop', 'execution_location': 'native_local'},
                  'facts': []}
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / 'input.json'
            path.write_text(json.dumps(report), encoding='utf-8')
            run = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'guardian.py'), 'analyze',
                                  '--target-ref', 'device-1', '--input', str(path)],
                                 capture_output=True, text=True, encoding='utf-8', timeout=30,
                                 env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'))
        output = json.loads(run.stdout)
        result[declared] = {'exit': run.returncode, 'status': output['execution_status'],
                            'codes': [x['code'] for x in output['findings']],
                            'gate': output['contact_control']['gate_state']}
    return result


def replay():
    with patch.object(f, '_now', return_value=TIME):
        out = observe()
    out['T68'] = {'analyzer': linux_local(),
                  'q_c02_prompt': f.QUESTION_PROMPTS['Q-C02']}
    return out


class CloudFlowAcceptanceTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        with ExitStack() as stack:
            stack.enter_context(patch.object(f, '_now', return_value=TIME))
            for target in FORBIDDEN_IO:
                stack.enter_context(patch(target, side_effect=AssertionError('forbidden I/O: ' + target)))
            cls.o = observe()
        cls.linux = linux_local()

    def assert_closed(self, gates):
        self.assertEqual(gates['g3'], 'blocked')
        self.assertEqual(gates['phase'], 'PC0')
        self.assertEqual(gates['consent'], {'private_save': False, 'export': False, 'public_export': False})

    def test_T30_all_supplied_fields_absorbed_and_only_gaps_asked(self):
        o = self.o['T30']
        self.assertEqual(o['known'], ['Q-C02', 'Q-C04', 'Q-C08', 'Q-J01', 'Q-P06'])
        self.assertEqual(o['unresolved_has_known'], [])
        self.assertEqual(o['first_gap'], 'Q-C01')
        for qid in ('Q-J01', 'Q-C02', 'Q-C08', 'Q-C04', 'Q-P06'):
            self.assertNotIn(qid, o['asked_after_batch'])
        self.assert_closed(o['gates'])

    def test_ENV_T02_known_answers_reused_and_only_unbound_device_gap_asked(self):
        o = self.o['ENV-T02']
        for qid in ('Q-J01', 'Q-C02', 'Q-N01', 'Q-N02'):
            self.assertNotIn(qid, o['device_a_asked'])
        self.assertEqual(o['device_b_facts'], ['Q-J01'])
        self.assertEqual(o['device_b_subscription'], 'active_reported')
        self.assertEqual(o['device_b_first'], 'Q-C02')
        self.assertNotIn('Q-J01', o['device_b_asked'])
        self.assertIn('Q-C02', o['device_b_asked'])

    def test_ENV_T96_provided_facts_not_reasked_and_authorization_stays_separate(self):
        o = self.o['ENV-T96']
        for qid in ('Q-J01', 'Q-C02', 'Q-C08', 'Q-C05', 'Q-C07'):
            self.assertNotIn(qid, o['asked'])
        self.assertFalse(o['retired_listed'])
        self.assertIn('Q-Z01', o['asked'])
        self.assertEqual(o['z01'], 'plan_only')
        self.assert_closed(o['gates'])

    def test_ENV_T36_first_time_environment_stage_has_no_old_entitlement_or_owner_questions(self):
        o = self.o['ENV-T36']
        self.assertEqual(o['listed_old'], [])
        self.assertEqual(o['asked_old'], [])
        self.assertEqual(o['journey'], 'first_subscription')

    def test_ENV_T92_retired_question_does_not_revive_and_current_status_is_self_reported(self):
        o = self.o['ENV-T92']
        self.assertEqual(o['retired'], 'Q-C07')
        self.assertTrue(o['saved_c07_refused'])
        self.assertFalse(o['c07_in_schema'])
        self.assertEqual(o['c07_prompt'], 'Retired; never collect account ownership')
        self.assertEqual(o['c07_record_refused'], 'Unknown or retired question ID')
        self.assertEqual(o['old_entitlement_listed'], [])
        self.assertEqual(o['login_fact_state'], 'reported')
        self.assert_closed(o['gates'])
        self.assertIn('Q-C07 永久停用', GUIDE['SKILL.md'])

    def test_T52_history_is_not_adopted_blindly_or_overwritten_across_targets(self):
        o = self.o['T52']
        self.assertEqual(o['original_untouched'], 'macos')
        self.assertEqual(o['other_device_answer'], 'refused')
        self.assertEqual(o['wrong_subject_role'], 'refused')
        self.assertEqual(o['flagged_state'], 'conflict')
        self.assertEqual(o['flagged_keeps_new_source'], 'user:today')
        self.assertTrue(o['after_one_ask_next_is_not_c02'])
        self.assertEqual(o['new_device_facts'], ['Q-J01'])
        self.assertEqual(o['new_device_subscription'], 'active_reported')
        self.assertEqual(o['new_account_facts'], [])
        # Known limit, asserted so it cannot change unnoticed: on the same target a newer answer simply
        # replaces the value unless the host marks it as a conflict.
        self.assertEqual(o['same_target_newer_answer_replaces_value'], 'windows')

    def test_T56_completion_counts_only_applicable_branches_and_has_no_score(self):
        o = self.o['T56']
        self.assertEqual(o['g1_keys'], ['status', 'unresolved_fields'])
        self.assertNotIn('score', ' '.join(o['assessment_keys']).lower())
        self.assertEqual(o['local_route_questions'], ['Q-L01', 'Q-L04'])
        self.assertEqual(o['vps_route_questions'], [])
        self.assertEqual(o['deferred_branches'], ['payment'])
        self.assertEqual(o['deferred_payment_reasons'], ['branch_deferred'])  # deferred, not counted as unasked
        self.assertEqual(o['g1_statuses'], ['partial'])

    def test_T85_unknown_plan_goes_to_comparison_without_default_tier_or_old_entitlement(self):
        o = self.o['T85']
        self.assertEqual(o['plan_fact'], 'undecided')
        self.assertIn('未决定先按用途和预算比较', o['plan_prompt'])
        self.assertTrue(o['budget_question_listed'])
        self.assertEqual(o['old_entitlement_listed'], [])
        self.assertEqual(o['asked_old'], [])
        self.assertFalse(o['gift_card_purchase_question_listed'])
        self.assert_closed(o['gates'])

    def test_T14_spec_only_request_keeps_every_gate_closed(self):
        o = self.o['T14']
        self.assertEqual(o['z01'], 'plan_only')
        self.assertEqual(o['g2'], {'status': 'blocked', 'conditional_plan_only': True})
        self.assert_closed(o['gates'])
        self.assertFalse(o['question_requires_action_authorization'])

    def test_T32_declined_card_is_not_recorded_as_an_account_suspension(self):
        o = self.o['T32']
        self.assertEqual(o['claimed_g1'], 'emergency_deferred')
        self.assertEqual(o['claimed_stage'], 'I0')
        self.assertEqual(o['claimed_next_id'], 'Q-H01')
        self.assertEqual(o['claimed_next_prompt'], '被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？')
        self.assertNotEqual(o['corrected_g1'], 'emergency_deferred')
        self.assertNotEqual(o['corrected_stage'], 'I0')
        self.assertEqual(o['corrected_facts'], {'Q-H01': 'payment_card', 'Q-C03': 'payment_declined_not_suspension',
                                                'Q-W03': 'card_declined'})
        self.assertEqual(o['task'], 'billing_issue')
        self.assert_closed(o['gates'])

    def test_T41_old_billing_questions_open_only_on_an_actual_conflict(self):
        o = self.o['T41']
        self.assertEqual(o['without_conflict'], [])
        self.assertEqual(o['with_conflict'], ['Q-P02'])
        self.assertEqual(o['next_after_conflict'], 'Q-P02')
        self.assertEqual(o['g2']['status'], 'blocked')
        self.assertEqual(o['g2']['reason'], 'subscription_conflict_unresolved')
        self.assert_closed(o['gates'])

    def test_T68_linux_local_is_blocked_not_pretended(self):
        self.assertEqual(self.linux['linux']['exit'], 2)
        self.assertEqual(self.linux['linux']['status'], 'blocked')
        self.assertEqual(self.linux['linux']['codes'], ['UNSUPPORTED_PRODUCT_OR_VERSION'])
        self.assertEqual(self.linux['linux']['gate'], 'closed')
        self.assertEqual(self.linux['macos']['status'], 'completed')
        text = GUIDE['references/routes-and-platforms.md']
        self.assertIn('Scope: macOS and Windows 10/11', text)
        self.assertIn('does not extend the native', text)

    def test_replay_is_deterministic(self):
        self.assertEqual(json.dumps(replay(), sort_keys=True), json.dumps(replay(), sort_keys=True))


if __name__ == '__main__':
    if '--replay' in sys.argv:
        print(json.dumps(replay(), ensure_ascii=True, indent=2, sort_keys=True))
    else:
        unittest.main()
