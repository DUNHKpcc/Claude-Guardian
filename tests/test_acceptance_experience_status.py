"""T75/T79 normalized-host replays: expertise is not subscription or permission.

Explanation generation remains the host's guided responsibility. No model call or
text-file fixture read is made. Python 3.10-compatible standard-library APIs only.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
SPEC = importlib.util.spec_from_file_location('experience_status_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
TIME = '2026-10-18T09:29:00Z'
SOURCE = 'synthetic:experience-and-subscription-current-report'
USER_INPUTS = {
 'T75': '我很熟悉技术，长期只用免费版，从未付费订阅。这次是第一次准备付费，说明尽量简短。',
 'T79': '我不懂技术，已经有付费套餐。请一步一步讲。',
 'expertise_only': '我很熟悉技术，说明尽量简短。',
}
DEPTH = {'T75': 'expert_difference_checklist', 'T79': 'novice_step_by_step'}
JOURNEY = {'T75': 'first_subscription', 'T79': 'existing_subscriber'}
PROMPTS = {
 'Q-J01': '这次是第一次准备订阅（包括只用过免费版）、以前订阅过目前无有效订阅准备重订、当前已有订阅，还是不确定？',
 'Q-J02': '你说用过/是老手：现在还有有效订阅，还是准备开通/重新开通？',
 'Q-C11': '老用户这次主要是续费/升级、调整使用方案，还是检查环境/解决问题？',
 'Q-C02': '这次用 Mac 还是 Windows？',
 'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
 'Q-OS02': '如果 Windows：是 Windows 10/11？具体 Edition（Home、Home Single Language、Pro……）是什么？',
 'Q-OS03': '如果 Mac：macOS 大致版本是什么？',
 'Q-C08': '你这次想订阅什么套餐？ 选好了直接说；未决定先按用途和预算比较。',
 'Q-C03': '以前 Claude 账号被明确停用/封禁过吗，还是只遇到报错？',
 'Q-C04': '准备用的 Claude 账号注册了吗？已有账号现在能正常登录吗？',
 'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
 'Q-C06': '已有账号通过什么方式登录/接入？不懂名称可描述界面。',
 'Q-C09': '实际在哪个国家/地区使用？是否有跨地区安排？无需详细地址。',
 'Q-N01': '当前是普通网络直接连接，还是使用代理/VPN/公司网络？软件名称知道就说。',
 'Q-N02': '浏览器、Code、代理分别运行在哪里？使用系统代理、应用代理、TUN 还是不确定？',
 'Q-N03': '网络是否常切换、自动换节点或跨地区？有计划长期固定使用的环境吗？',
 'Q-N04': '还有手机、其他电脑或远程工作区同时/交替使用吗？各自用来做什么？',
 'Q-N06': '是否受公司网络、证书、安全软件、代理策略或设备管理限制？',
 'Q-P03': '可用于付款的设备有 iPhone/iPad、Android，还是只有电脑？',
 'Q-P04': '已有可用的商店账户/余额、银行卡、企业付款方式，还是尚未准备？',
 'Q-P06': '更倾向哪种可行付款方式？需要先比较步骤吗？',
 'Q-P07': '后续准备怎样续费？需要说明账单查看与取消入口吗？',
 'Q-W01': '准备使用的是信用卡/借记卡/企业卡？发行国家或地区是什么？',
 'Q-W02': '结账要求的账单资料能否如实填写？',
 'Q-W03': '是否支持所需的线上/周期付款，出现过拒付或验证提示吗？',
 'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
 'Q-L04': 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？',
 'Q-C12': '哪些已有项目、历史、客户端或配置不能动？',
 'Q-Z01': '这次只要讲解/计划，还是允许指定范围的只读检查？',
}
VALUES = {
 'Q-C11': 'environment', 'Q-C01': 'code_environment_planning_reported',
 'Q-OS02': {'version': 'windows_11_reported', 'edition': 'home_reported'},
 'Q-OS03': 'synthetic_reported_macos_version',
 'Q-C08': 'synthetic_named_target_plan_not_current_catalog_verified',
 'Q-C03': 'none_reported', 'Q-C04': 'registered_current_login_reported_not_checked',
 'Q-C05': 'accepted_default', 'Q-C06': 'official_login_category_reported',
 'Q-C09': 'synthetic_reported_region_not_eligibility_verified',
 'Q-N01': 'existing_network_reported_not_tested',
 'Q-N02': {'browser': 'device-a', 'code': 'device-a', 'proxy': 'device-a', 'mode': 'reported_existing'},
 'Q-N03': 'stable_network_intended', 'Q-N04': 'no_other_target_reported',
 'Q-N06': 'no_management_restriction_reported',
 'Q-P03': 'computer_reported', 'Q-P04': 'existing_card_category_reported_no_number',
 'Q-P06': 'web', 'Q-P07': 'renewal_and_cancellation_explanation_requested',
 'Q-W01': 'synthetic_card_category_and_issuing_region_report',
 'Q-W02': 'truthful_billing_details_to_be_supplied_privately_by_user',
 'Q-W03': 'recurring_payment_category_reported_not_tested',
 'Q-L01': 'existing_client_metadata_reported_not_executed', 'Q-L04': 'preserve_local_projects',
 'Q-C12': 'preserve_existing_projects_and_settings', 'Q-Z01': 'plan_only',
}
NETWORK = ['Q-C09', 'Q-N01', 'Q-N02', 'Q-N03', 'Q-N04', 'Q-N06']
PAYMENT = ['Q-P03', 'Q-P04', 'Q-P06', 'Q-P07', 'Q-W01', 'Q-W02', 'Q-W03']
TAIL = ['Q-L01', 'Q-L04', 'Q-C12', 'Q-Z01']
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}


def offline():
    stack = ExitStack()
    stack.enter_context(patch.object(f, '_now', return_value=TIME))
    for target in ('builtins.open', 'io.open', 'os.open', 'socket.socket', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        stack.enter_context(patch(target, side_effect=AssertionError('Pure replay attempted external I/O')))
    return stack


def initial(case, supplied_task=False):
    facts = [{'question_id': 'Q-J01', 'value': JOURNEY[case]},
             {'question_id': 'Q-C10', 'value': DEPTH[case]}]
    if supplied_task:
        facts.append({'question_id': 'Q-C11', 'value': 'environment'})
    return f.record_facts(f.new_state('device-a', 'account-a', task_id='experience-task'), facts, source=SOURCE)


def sequence(case, os_name, supplied_task=False):
    return (['Q-C11'] if case == 'T79' and not supplied_task else []) + [
        'Q-C02', 'Q-C01', 'Q-OS03' if os_name == 'macos' else 'Q-OS02'] + (
        ['Q-C08'] if case == 'T75' else []) + ['Q-C03', 'Q-C04', 'Q-C05', 'Q-C06'] + NETWORK + (
        PAYMENT if case == 'T75' else []) + TAIL


def expected(qid):
    if qid in {'Q-J01', 'Q-J02', 'Q-C11'}:
        branch, stage = 'core', 'I1'
    elif qid.startswith('Q-OS'):
        branch, stage = 'os', 'I2'
    elif qid in {'Q-C02', 'Q-C01', 'Q-C08'}:
        branch, stage = 'core', 'I2'
    elif qid in {'Q-C03', 'Q-C04', 'Q-C05', 'Q-C06'}:
        branch, stage = 'core', 'I3'
    elif qid in NETWORK:
        branch, stage = 'network', 'I4'
    elif qid in PAYMENT:
        branch, stage = 'payment', 'I4'
    elif qid.startswith('Q-L'):
        branch, stage = 'local', 'I5'
    else:
        branch, stage = 'protection', 'I5'
    return {'id': qid, 'branch': branch, 'stage': stage, 'postcontact': False,
            'prompt': PROMPTS[qid], 'clarification': False,
            'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
            'requires_action_authorization': False}


def snap(state):
    return {'state': deepcopy(state), 'question': f.next_question(state),
            'applicable': f.applicable_questions(state), 'assessment': f.assessment(state)}


def trace(case, os_name, supplied_task=False):
    state = initial(case, supplied_task)
    rows = []
    for qid in sequence(case, os_name, supplied_task):
        actual = f.next_question(state)
        if actual != expected(qid):
            raise AssertionError({'actual': actual, 'expected': expected(qid)})
        rows.append(snap(state))
        state = f.mark_asked(state, qid)
        state = f.record_fact(state, qid, os_name if qid == 'Q-C02' else VALUES[qid], source=SOURCE)
    rows.append(snap(state))
    return state, rows


def novice_billing(task):
    return f.record_fact(initial('T79'), 'Q-C11', task, source='synthetic:explicit-existing-subscriber-task')


def expertise_only(ambiguous=False):
    state = f.record_fact(f.new_state('device-a', 'account-a'), 'Q-C10', DEPTH['T75'], source=SOURCE)
    return f.set_context(state, ambiguous_experience=True) if ambiguous else state


def replay():
    with offline():
        return {'kind': 'actual_normalized_API_replay', 'model_dialogue_run': False,
                'synthetic_user_inputs_not_model_executed': USER_INPUTS,
                'explicit_later_fixture_answers': VALUES,
                'full_paths': {case + '_' + os_name: trace(case, os_name)[1]
                               for case in ('T75', 'T79') for os_name in ('macos', 'windows')},
                'novice_task_already_supplied': trace('T79', 'macos', supplied_task=True)[1],
                'novice_existing_billing_controls': {task: snap(novice_billing(task)) for task in ('renew', 'upgrade')},
                'expertise_only_controls': {str(ambiguous): snap(expertise_only(ambiguous)) for ambiguous in (False, True)}}


class ExperienceStatusAcceptanceTests(unittest.TestCase):
    def setUp(self):
        stack = offline()
        self.addCleanup(stack.close)

    def assert_boundaries(self, state):
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(state['persistence_consent'], {'private_save': False, 'export': False, 'public_export': False})
        self.assertEqual(f.assessment(state)['traffic_policy']['environment_pass'], False)
        self.assertEqual(f.assessment(state)['traffic_policy']['authorization'], 'none')
        self.assertFalse(state['context']['subscription_conflict'])
        self.assertEqual(state['context']['route'], 'local')
        self.assertNotIn('Q-C07', {q['id'] for q in f.applicable_questions(state)})

    def assert_reports(self, case, state):
        self.assertEqual(f.journey(state), JOURNEY[case])
        self.assertEqual(state['current_subscription'], {'status': 'none_reported' if case == 'T75' else 'active_reported', 'source': SOURCE, 'observed_at': TIME})
        self.assertEqual(state['facts']['Q-C10'], initial(case)['facts']['Q-C10'])
        self.assertNotIn('Q-C10', state['asked_question_ids'])
        self.assertNotIn('Q-J01', state['asked_question_ids'])
        self.assert_boundaries(state)

    def test_T75_expert_free_user_stays_first_subscription_on_complete_paths(self):
        for os_name in ('macos', 'windows'):
            state, rows = trace('T75', os_name)
            self.assertEqual([r['question'] for r in rows], [expected(q) for q in sequence('T75', os_name)] + [None])
            for row in rows:
                self.assert_reports('T75', row['state'])
                self.assertEqual(row['state']['payment_intent'], 'new_subscription')
                ids = {q['id'] for q in row['applicable']}
                self.assertTrue({'Q-P02', 'Q-A06', 'Q-J02', 'Q-C11'}.isdisjoint(ids))
                self.assertFalse(any(q.startswith(('Q-V', 'Q-S')) for q in ids))
            self.assertEqual(f.assessment(state)['G1'], {'status': 'partial', 'unresolved_fields': [{'id': 'Q-W04', 'reason': 'requires_contact_gate'}]})
            self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
            self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T79_novice_existing_subscriber_enters_task_branch_without_first_purchase(self):
        for os_name in ('macos', 'windows'):
            state, rows = trace('T79', os_name)
            self.assertEqual([r['question'] for r in rows], [expected(q) for q in sequence('T79', os_name)] + [None])
            self.assertEqual(rows[0]['state']['purchase_intent'], 'subscription_preparation')
            self.assertEqual(rows[0]['state']['payment_intent'], 'unresolved')
            for index, row in enumerate(rows):
                self.assert_reports('T79', row['state'])
                self.assertNotIn('Q-C08', {q['id'] for q in row['applicable']})
                self.assertFalse(any(q['branch'] == 'payment' for q in row['applicable']))
                if index:
                    self.assertEqual(row['state']['purchase_intent'], 'none')
                    self.assertEqual(row['state']['payment_intent'], 'none')
            self.assertEqual(f.assessment(state)['G1'], {'status': 'complete', 'unresolved_fields': []})
            self.assertEqual(f.assessment(state)['G2'], {'status': 'pass', 'conditional_plan_only': False})
            self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T79_known_environment_task_skips_task_question_and_retains_novice_depth(self):
        state, rows = trace('T79', 'macos', supplied_task=True)
        self.assertEqual([r['question'] for r in rows], [expected(q) for q in sequence('T79', 'macos', True)] + [None])
        for row in rows:
            self.assert_reports('T79', row['state'])
            self.assertNotIn('Q-C11', {q['id'] for q in row['applicable']})
            self.assertEqual(row['state']['purchase_intent'], 'none')
            self.assertEqual(row['state']['payment_intent'], 'none')

    def test_T79_novice_depth_does_not_suppress_legitimate_existing_renewal_or_upgrade(self):
        for task in ('renew', 'upgrade'):
            state = novice_billing(task)
            self.assert_reports('T79', state)
            self.assertEqual(state['context']['task'], task)
            self.assertEqual(state['payment_intent'], task)
            self.assertEqual(f.next_question(state), expected('Q-C02'))
            ids = {q['id'] for q in f.applicable_questions(state)}
            self.assertTrue({'Q-P02', 'Q-C08'}.issubset(ids))
            self.assertNotIn('Q-C11', ids)
            self.assertNotEqual(state['payment_intent'], 'new_subscription')

    def test_T75_expertise_alone_never_establishes_paid_or_first_subscription(self):
        for ambiguous, question in ((False, 'Q-J01'), (True, 'Q-J02')):
            state = expertise_only(ambiguous)
            self.assertEqual(f.journey(state), 'unknown')
            self.assertEqual(state['current_subscription'], {'status': 'unknown', 'source': None, 'observed_at': None})
            self.assertEqual(state['payment_intent'], 'unresolved')
            self.assertEqual(f.next_question(state), expected(question))
            self.assertEqual(f.assessment(state)['G2']['status'], 'blocked')
            self.assert_boundaries(state)
        original = expertise_only()
        for value in ('first_subscription', 'existing_subscriber'):
            with self.assertRaisesRegex(f.InterviewError, "^Inference cannot establish protected facts$"):
                f.record_fact(original, 'Q-J01', value, state_name='inferred', source='synthetic:expertise-is-not-entitlement')
            self.assertEqual(f.journey(original), 'unknown')

    def test_T75_T79_depth_changes_preserve_subscription_route_questions_and_permission(self):
        for case, other in (('T75', 'T79'), ('T79', 'T75')):
            state, _ = trace(case, 'macos')
            before = deepcopy(state)
            changed = f.record_fact(state, 'Q-C10', DEPTH[other], source='synthetic:explicit-new-depth-preference')
            self.assertEqual(state, before)
            self.assertEqual(changed['facts']['Q-C10']['value'], DEPTH[other])
            self.assertEqual({q: v for q, v in changed['facts'].items() if q != 'Q-C10'}, {q: v for q, v in state['facts'].items() if q != 'Q-C10'})
            self.assertEqual(changed['context'], state['context'])
            self.assertEqual(changed['current_subscription'], state['current_subscription'])
            self.assertEqual(f.applicable_questions(changed), f.applicable_questions(state))
            self.assertEqual(f.assessment(changed), f.assessment(state))
            self.assert_boundaries(changed)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    else:
        unittest.main()
