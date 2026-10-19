"""Original T22/T25 normalized logic evidence, not generated dialogue.

The public fixture is synthetic. --replay emits complete deterministic state,
question, applicable-question and assessment projections for semantic review.
The host remains responsible for concise explanations and useful diagnosis.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

HERE = Path(__file__).resolve().parent
ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', HERE.parent))
SPEC = importlib.util.spec_from_file_location(
    'local_incident_acceptance_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
# Load the test inputs before the pure-runtime no-I/O boundary.
FIXTURE = json.loads((HERE / 'fixtures/acceptance-local-incident-cases.json').read_text(encoding='utf-8'))
TIME = FIXTURE['base_observed_at']
LATER = FIXTURE['incident_observed_at']
FOLLOWUP = FIXTURE['followup_observed_at']
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
PERMISSIONS = {'private_save': False, 'export': False, 'public_export': False}
# Independent exact expectations, not copied from runtime dictionaries.
INCIDENT_PROMPTS = {
    'Q-H01': '被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？',
    'Q-H02': '最近一次与本次任务有关的事件，大约何时发生？目前恢复了吗？',
    'Q-H03': '当时显示什么错误/通知？有可脱敏的原文或局部截图吗？',
    'Q-H04': '出现问题前正在注册、登录、订阅、更新客户端还是执行任务？',
    'Q-H05': '当时在什么设备/环境、通过什么客户端和计费渠道使用？',
    'Q-H06': '是否正在申诉、身份核验或处理退款？有没有官方回复要求你完成的事项？',
    'Q-H07': '之后做过哪些退出、重装、清理或配置修改？有需要保留/导出的数据吗？',
}
INCIDENT_IDS = list(INCIDENT_PROMPTS)


@contextmanager
def offline():
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
                       'subprocess.Popen', 'os.system'):
            stack.enter_context(patch(target, side_effect=deny(target)))
        try:
            yield
        finally:
            # Catch attempted I/O even if the implementation swallowed the error.
            if attempted:
                raise AssertionError('Pure interview I/O sentinel fired: ' + ', '.join(attempted))


def base(os_name='macos', *, missing=()):
    values = {**FIXTURE['common_facts'], **FIXTURE['platform_facts'][os_name]}
    return f.record_facts(
        f.new_state(FIXTURE['target_alias'], FIXTURE['account_alias'], task_id=FIXTURE['task_id']),
        [{'question_id': qid, 'value': deepcopy(value)} for qid, value in values.items() if qid not in missing],
        source=FIXTURE['base_source'])


def question(qid):
    return {'id': qid, 'branch': 'incident', 'stage': 'I0', 'postcontact': False,
            'prompt': INCIDENT_PROMPTS[qid], 'clarification': False,
            'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
            'requires_action_authorization': False}


def snapshot(state):
    return {'state': deepcopy(state), 'next_question': f.next_question(state),
            'applicable_questions': f.applicable_questions(state), 'assessment': f.assessment(state)}


def incident_start(case, original=None):
    data = FIXTURE['incident_cases'][case]
    return f.record_fact(base() if original is None else original, 'Q-C04', data['current_status'],
                         source=data['source'], observed_at=LATER, current_reply=True)


def incident_trace(case, detail_outcome='reported'):
    data = FIXTURE['incident_cases'][case]
    state = incident_start(case)
    trace = []
    for qid in INCIDENT_IDS:
        if f.next_question(state) != question(qid):
            raise AssertionError({'expected': question(qid), 'actual': f.next_question(state)})
        trace.append(snapshot(state))
        state = f.mark_asked(state, qid)
        outcome = detail_outcome if qid == 'Q-H03' else 'reported'
        state = f.record_fact(state, qid,
                             deepcopy(data['answers'][qid]) if outcome == 'reported' else None,
                             state_name=outcome, source=data['source'], observed_at=LATER,
                             current_reply=True,
                             blocker_reason=None if outcome == 'reported' else 'error_detail_not_supplied')
    trace.append(snapshot(state))
    return state, trace


def change_depth(state):
    return f.record_fact(state, 'Q-C10', 'novice_step_by_step',
                         source='synthetic:depth-only-followup', observed_at=FOLLOWUP, current_reply=True)


def replay():
    with offline():
        result = {'kind': 'actual_normalized_API_replay', 'model_dialogue_run': False,
                  'source_pins': deepcopy(FIXTURE['source_pins']),
                  'limits': deepcopy(FIXTURE['limits']), 'T22': {}, 'T25': {}}
        for os_name in FIXTURE['platform_facts']:
            state = base(os_name)
            changed = change_depth(state)
            result['T22'][os_name] = {'initial': snapshot(state), 'depth_only_followup': snapshot(changed),
                                     'reloaded': snapshot(f.loads_state(f.dumps_state(changed, host_opt_in=True)))}
        for case in FIXTURE['incident_cases']:
            state, trace = incident_trace(case)
            result['T25'][case] = {'trace': trace,
                                   'reloaded': snapshot(f.loads_state(f.dumps_state(state, host_opt_in=True)))}
        for outcome in ('unknown', 'declined'):
            state, trace = incident_trace('unknown_error', outcome)
            result['T25']['detail_' + outcome] = {'trace': trace,
                                                 'reloaded': snapshot(f.loads_state(f.dumps_state(state, host_opt_in=True)))}
        partial = base(missing=('Q-N01', 'Q-L01'))
        result['T25']['pending_local_gaps'] = {
            'before': snapshot(partial),
            'current_incidents': {case: snapshot(incident_start(case, partial)) for case in FIXTURE['incident_cases']}}
        return result


class LocalIncidentAcceptanceTests(unittest.TestCase):
    def setUp(self):
        stack = offline()
        stack.__enter__()
        self.addCleanup(stack.__exit__, None, None, None)

    def assert_boundaries(self, state):
        assessment = f.assessment(state)
        self.assertEqual((state['target_alias'], state['account_alias'], state['task_id']),
                         ('local-device', 'local-account', 'local-code-task'))
        self.assertEqual(state['context']['route'], 'local')
        self.assertEqual(state['context']['route_selection_basis'], 'explicit_choice')
        self.assertEqual(assessment['route_confirmation'], 'confirmed')
        self.assertEqual(state['context']['task'], 'environment')
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(state['persistence_consent'], PERMISSIONS)
        self.assertEqual(state['purchase_intent'], 'none')
        self.assertEqual(state['payment_intent'], 'none')
        self.assertEqual(assessment['G3'], G3)
        self.assertFalse(assessment['traffic_policy']['environment_pass'])
        self.assertEqual(assessment['traffic_policy']['authorization'], 'none')
        self.assertEqual(assessment['traffic_policy']['compliance'], 'not_established')
        self.assertEqual(state['deferred_branches'], [])
        self.assertEqual(state['current_subscription'], {
            'status': 'active_reported', 'source': FIXTURE['base_source'], 'observed_at': TIME})
        self.assertFalse(any(item['branch'] in {'vm', 'vps', 'payment', 'cleanup'}
                             for item in f.applicable_questions(state)))

    def assert_fact(self, fact, value, source, observed_at, subject, *, outcome='reported', blocker=None):
        self.assertEqual(fact, {'value': value, 'state': outcome, 'source': source,
                               'subject_ref': subject, 'observed_at': observed_at,
                               'applies_when': 'current task and target', 'required_for': ['intake', 'plan'],
                               'sensitivity': 'low', 'clarification_count': 0, 'blocker_reason': blocker})

    def test_T22_complete_expert_local_code_reuses_facts_on_both_reported_platforms(self):
        for os_name in ('macos', 'windows'):
            with self.subTest(platform=os_name):
                state = base(os_name)
                self.assert_boundaries(state)
                self.assertIsNone(f.next_question(state))
                self.assertEqual(state['asked_question_ids'], [])
                self.assertEqual(f.assessment(state)['G1'], {'status': 'complete', 'unresolved_fields': []})
                self.assertEqual(f.assessment(state)['G2'], {'status': 'pass', 'conditional_plan_only': False})
                self.assertEqual(f.assessment(state)['active_branches'], ['core', 'os', 'network', 'local', 'protection'])
                expected_ids = ['Q-J01', 'Q-C02', 'Q-C01', 'Q-OS03' if os_name == 'macos' else 'Q-OS02',
                                'Q-C03', 'Q-C04', 'Q-C06', 'Q-C09', 'Q-N01', 'Q-N02', 'Q-N03',
                                'Q-N04', 'Q-N06', 'Q-L01', 'Q-L04', 'Q-C12', 'Q-Z01', 'Q-C10']
                self.assertEqual([q['id'] for q in f.applicable_questions(state)], expected_ids)
                self.assert_fact(state['facts']['Q-C10'], 'expert_difference_checklist',
                                 FIXTURE['base_source'], TIME, 'local-device')
                self.assertEqual(set(state['facts']), set(FIXTURE['common_facts']) | set(FIXTURE['platform_facts'][os_name]))

    def test_T22_depth_only_followup_changes_no_route_subscription_or_authority(self):
        for os_name in ('macos', 'windows'):
            original = base(os_name)
            before = deepcopy(original)
            changed = change_depth(original)
            expected = deepcopy(original)
            expected['facts']['Q-C10'].update(value='novice_step_by_step', source='synthetic:depth-only-followup', observed_at=FOLLOWUP)
            self.assertEqual(changed, expected)
            self.assertEqual(original, before)
            self.assertEqual(f.assessment(changed), f.assessment(original))
            self.assertIsNone(f.next_question(changed))
            self.assert_boundaries(changed)

    def test_T25_current_error_restriction_and_review_take_priority_without_rebinding(self):
        original = base()
        before = deepcopy(original)
        for case in ('unknown_error', 'suspended', 'identity_review'):
            with self.subTest(case=case):
                state = incident_start(case, original)
                self.assertEqual(original, before)
                expected = deepcopy(original)
                expected['facts']['Q-C04'].update(value=case, source=FIXTURE['incident_cases'][case]['source'], observed_at=LATER)
                self.assertEqual(state, expected)
                self.assertEqual(f.next_question(state), question('Q-H01'))
                self.assertEqual(f.applicable_questions(state), [
                    {'id': qid, 'branch': 'incident', 'stage': 'I0', 'postcontact': False} for qid in INCIDENT_IDS])
                self.assertEqual(f.assessment(state)['G1'], {'status': 'emergency_deferred',
                    'unresolved_fields': [{'id': qid, 'reason': 'unasked'} for qid in INCIDENT_IDS]})
                self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
                self.assert_boundaries(state)

    def test_T25_complete_triage_retains_all_reports_and_still_does_not_resolve_incident(self):
        original = base()
        for case, data in FIXTURE['incident_cases'].items():
            with self.subTest(case=case):
                state, trace = incident_trace(case)
                self.assertEqual([row['next_question'] for row in trace], [question(qid) for qid in INCIDENT_IDS] + [None])
                for index, row in enumerate(trace):
                    current = row['state']
                    self.assert_boundaries(current)
                    self.assertEqual(current['context'], original['context'])
                    self.assertEqual({qid: current['facts'][qid] for qid in original['facts'] if qid != 'Q-C04'},
                                     {qid: fact for qid, fact in original['facts'].items() if qid != 'Q-C04'})
                    self.assertEqual(current['asked_question_ids'], INCIDENT_IDS[:index])
                    self.assertEqual(row['assessment']['G1'], {'status': 'emergency_deferred',
                        'unresolved_fields': [{'id': qid, 'reason': 'unasked'} for qid in INCIDENT_IDS[index:]]})
                    self.assertEqual(row['assessment']['G2'], {'status': 'blocked', 'conditional_plan_only': True})
                    self.assertEqual(row['assessment']['active_branches'], ['incident'])
                    self.assertEqual(row['assessment']['emergency_deferred_branches'], [])
                    self.assertEqual(row['assessment']['stage'], 'I0' if index < len(INCIDENT_IDS) else 'I6')
                self.assert_fact(state['facts']['Q-C04'], data['current_status'], data['source'], LATER, 'local-account')
                for qid in INCIDENT_IDS:
                    self.assert_fact(state['facts'][qid], data['answers'][qid], data['source'], LATER, 'local-device')
                self.assertFalse(state['context']['incident_resolved'])
                self.assertFalse(state['context']['account_incident_resolved'])
                self.assertEqual(state['facts']['Q-C04']['value'], case)
                self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T25_incident_preempts_existing_local_gaps_without_discarding_them(self):
        partial = base(missing=('Q-N01', 'Q-L01'))
        self.assertEqual(f.next_question(partial)['id'], 'Q-N01')
        self.assertEqual(f.assessment(partial)['G1'], {'status': 'partial', 'unresolved_fields': [
            {'id': 'Q-N01', 'reason': 'unasked'}, {'id': 'Q-L01', 'reason': 'unasked'}]})
        for case in FIXTURE['incident_cases']:
            state = incident_start(case, partial)
            self.assertEqual(f.next_question(state), question('Q-H01'))
            self.assertEqual(f.assessment(state)['emergency_deferred_branches'], ['network', 'local'])
            self.assertEqual(state['deferred_branches'], [])
            self.assertNotIn('Q-N01', state['facts'])
            self.assertNotIn('Q-L01', state['facts'])
            self.assertEqual({qid: fact for qid, fact in state['facts'].items() if qid != 'Q-C04'},
                             {qid: fact for qid, fact in partial['facts'].items() if qid != 'Q-C04'})
            self.assert_boundaries(state)

    def test_T25_missing_or_declined_error_detail_stays_unknown_without_reasking(self):
        for outcome in ('unknown', 'declined'):
            with self.subTest(outcome=outcome):
                state, trace = incident_trace('unknown_error', outcome)
                self.assertEqual([row['next_question'] for row in trace], [question(qid) for qid in INCIDENT_IDS] + [None])
                self.assert_fact(state['facts']['Q-H03'], None,
                                 FIXTURE['incident_cases']['unknown_error']['source'], LATER, 'local-device',
                                 outcome=outcome, blocker='error_detail_not_supplied')
                self.assertEqual(f.assessment(state)['G1'], {'status': 'emergency_deferred',
                    'unresolved_fields': [{'id': 'Q-H03', 'reason': outcome}]})
                self.assertEqual(f.assessment(state)['stage'], 'I0')
                self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
                self.assertEqual(state['facts']['Q-C04']['value'], 'unknown_error')
                self.assert_boundaries(state)
                for _ in range(3):
                    self.assertIsNone(f.next_question(state))
                self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T25_replayed_evidence_does_not_upgrade_or_refresh_local_report(self):
        for case, data in FIXTURE['incident_cases'].items():
            state, _ = incident_trace(case)
            before = deepcopy(state)
            replayed = f.record_fact(state, 'Q-C04', data['current_status'], source=data['source'], observed_at=LATER)
            self.assertEqual(replayed, state)
            self.assertEqual(state, before)
            self.assertEqual(f.loads_state(f.dumps_state(replayed, host_opt_in=True)), replayed)
            self.assert_boundaries(replayed)
            self.assertIsNone(f.next_question(replayed))

    def test_T22_T25_private_serialization_does_not_create_permission(self):
        for state in (base(), incident_trace('suspended')[0]):
            with self.assertRaisesRegex(f.InterviewError, '^Explicit host opt-in for persistence/export is required$'):
                f.dumps_state(state)
            loaded = f.loads_state(f.dumps_state(state, host_opt_in=True))
            self.assertEqual(loaded, state)
            self.assert_boundaries(loaded)
            with self.assertRaisesRegex(f.InterviewError, '^Public export requires a separately reviewed redacted artifact$'):
                f.dumps_state(loaded, host_opt_in=True, scope='public_export')

    def test_T22_T25_full_replay_is_repeat_stable(self):
        first = json.dumps(replay(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        second = json.dumps(replay(), ensure_ascii=False, sort_keys=True, allow_nan=False)
        self.assertEqual(first, second)
        self.assertFalse(json.loads(first)['model_dialogue_run'])


if __name__ == '__main__':
    if '--replay' in sys.argv:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2, allow_nan=False))
    else:
        unittest.main()
