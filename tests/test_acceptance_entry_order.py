"""Original T29/T57: complete normalized-host entry replays, no model generation.

No text-file fixture reads. Uses Python 3.10-compatible standard-library APIs.
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
SPEC = importlib.util.spec_from_file_location('entry_order_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
TIME = '2026-10-18T09:22:00Z'
SOURCE = 'synthetic:entry-order-user-report'
PROMPTS = {
 'Q-J01': '这次是第一次准备订阅（包括只用过免费版）、以前订阅过目前无有效订阅准备重订、当前已有订阅，还是不确定？',
 'Q-C02': '这次用 Mac 还是 Windows？',
 'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
 'Q-OS02': '如果 Windows：是 Windows 10/11？具体 Edition（Home、Home Single Language、Pro……）是什么？',
 'Q-OS03': '如果 Mac：macOS 大致版本是什么？',
 'Q-OS12': '当前 OS 选项不在 Mac/Windows 内，本次想了解共用规则还是要选 VM/VPS？',
 'Q-C08': '你这次想订阅什么套餐？ 选好了直接说；未决定先按用途和预算比较。',
 'Q-C03': '以前 Claude 账号被明确停用/封禁过吗，还是只遇到报错？',
 'Q-C04': '准备用的 Claude 账号注册了吗？已有账号现在能正常登录吗？',
 'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
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
 'Q-C10': '希望逐步指导，还是直接给检查项和命令？',
}
VALUES = {
 'Q-J01': 'first_subscription',
 'Q-C01': 'plan_first_subscription_and_code_no_installation',
 'Q-OS02': {'version': 'windows_11_reported', 'edition': 'home_reported_not_single_language_inferred'},
 'Q-OS03': 'synthetic_reported_macos_version',
 'Q-OS12': 'limited_common_guidance_only_no_route_selected',
 'Q-C08': 'synthetic_named_target_plan_not_current_catalog_verified',
 'Q-C03': 'none_reported', 'Q-C04': 'unregistered', 'Q-C05': 'accepted_default',
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
 'Q-L01': 'no_target_client_installation_reported', 'Q-L04': 'local_project_access_planned_not_approved',
 'Q-C12': 'preserve_existing_projects_and_settings', 'Q-Z01': 'plan_only', 'Q-C10': 'step_by_step',
}
NETWORK = ['Q-C09', 'Q-N01', 'Q-N02', 'Q-N03', 'Q-N04', 'Q-N06']
PAYMENT = ['Q-P03', 'Q-P04', 'Q-P06', 'Q-P07', 'Q-W01', 'Q-W02', 'Q-W03']
TAIL = ['Q-L01', 'Q-L04', 'Q-C12', 'Q-Z01', 'Q-C10']
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}


def offline():
    stack = ExitStack()
    stack.enter_context(patch.object(f, '_now', return_value=TIME))
    for target in ('builtins.open', 'io.open', 'os.open', 'socket.socket', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        stack.enter_context(patch(target, side_effect=AssertionError('Pure entry replay attempted external I/O')))
    return stack


def initial():
    return f.new_state('device-a', 'account-a', task_id='entry-order-task')


def sequence(os_name):
    return ['Q-J01', 'Q-C02', 'Q-C01', 'Q-OS03' if os_name == 'macos' else 'Q-OS02',
            'Q-C08', 'Q-C03', 'Q-C04', 'Q-C05'] + NETWORK + PAYMENT + TAIL


def expected(qid):
    if qid == 'Q-J01':
        branch, stage = 'core', 'I1'
    elif qid.startswith('Q-OS'):
        branch, stage = 'os', 'I2'
    elif qid in {'Q-C02', 'Q-C01', 'Q-C08'}:
        branch, stage = 'core', 'I2'
    elif qid in {'Q-C03', 'Q-C04', 'Q-C05'}:
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


def trace(os_name):
    state = initial()
    rows = []
    for qid in sequence(os_name):
        if f.next_question(state) != expected(qid):
            raise AssertionError({'expected': expected(qid), 'actual': f.next_question(state)})
        rows.append(snap(state))
        state = f.mark_asked(state, qid)
        state = f.record_fact(state, qid, os_name if qid == 'Q-C02' else VALUES[qid], source=SOURCE)
    rows.append(snap(state))
    return state, rows


def os_exit(kind):
    state = f.record_fact(initial(), 'Q-J01', 'first_subscription', source=SOURCE)
    rows = [snap(state)]
    state = f.mark_asked(state, 'Q-C02')
    if kind == 'mobile_only':
        state = f.record_fact(state, 'Q-C02', kind, source=SOURCE)
    else:
        state = f.record_fact(state, 'Q-C02', state_name=kind, source=SOURCE)
    rows.append(snap(state))
    state = f.record_fact(state, 'Q-C01', VALUES['Q-C01'], source=SOURCE)
    rows.append(snap(state))
    if kind == 'mobile_only':
        state = f.record_fact(state, 'Q-OS12', VALUES['Q-OS12'], source=SOURCE)
        rows.append(snap(state))
    return state, rows


def supplied():
    facts = {'Q-J01': 'first_subscription', 'Q-C02': 'macos', 'Q-C01': VALUES['Q-C01'],
             'Q-OS03': VALUES['Q-OS03'], 'Q-C08': VALUES['Q-C08'], 'Q-C03': VALUES['Q-C03'],
             'Q-C04': 'unregistered', 'Q-C05': 'local'}
    return facts, f.record_facts(initial(), [{'question_id': q, 'value': v} for q, v in facts.items()], source=SOURCE)


def replay():
    with offline():
        facts, state = supplied()
        return {'kind': 'actual_normalized_API_replay', 'model_dialogue_run': False,
                'synthetic_values': VALUES,
                'full_paths': {os_name: trace(os_name)[1] for os_name in ('macos', 'windows')},
                'os_exits': {kind: os_exit(kind)[1] for kind in ('unknown', 'declined', 'deferred', 'mobile_only')},
                'supplied_facts': {'inputs': facts, 'actual': snap(state)}}


class EntryOrderAcceptanceTests(unittest.TestCase):
    def setUp(self):
        stack = offline()
        self.addCleanup(stack.close)

    def assert_boundaries(self, state):
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(state['persistence_consent'], {'private_save': False, 'export': False, 'public_export': False})
        self.assertEqual(f.assessment(state)['traffic_policy']['environment_pass'], False)
        self.assertEqual(f.assessment(state)['traffic_policy']['authorization'], 'none')
        ids = {q['id'] for q in f.applicable_questions(state)}
        self.assertTrue({'Q-C07', 'Q-P02', 'Q-A06', 'Q-C11', 'Q-J02'}.isdisjoint(ids))
        self.assertFalse(any(q.startswith(('Q-V', 'Q-S', 'Q-I', 'Q-E')) for q in ids))

    def test_T29_empty_entry_asks_subscription_stage_before_any_environment_or_tutorial(self):
        state = initial()
        self.assertEqual(state['facts'], {})
        self.assertEqual(f.next_question(state), expected('Q-J01'))
        self.assertEqual(state['current_subscription'], {'status': 'unknown', 'source': None, 'observed_at': None})
        self.assertEqual(f.assessment(state)['route_confirmation'], 'unconfirmed')
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(state)))
        self.assert_boundaries(state)

    def test_T29_complete_mac_and_windows_first_time_paths_preserve_order_and_contact_gap(self):
        for os_name in ('macos', 'windows'):
            state, rows = trace(os_name)
            self.assertEqual([r['question'] for r in rows], [expected(q) for q in sequence(os_name)] + [None])
            for row in rows:
                self.assert_boundaries(row['state'])
                self.assertFalse(row['question'] and row['question']['postcontact'])
            self.assertEqual(f.assessment(state)['G1'], {'status': 'partial', 'unresolved_fields': [{'id': 'Q-W04', 'reason': 'requires_contact_gate'}]})
            self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
            self.assertEqual(state['current_subscription'], {'status': 'none_reported', 'source': SOURCE, 'observed_at': TIME})
            self.assertEqual(state['facts']['Q-C08']['value'], VALUES['Q-C08'])
            self.assertEqual(state['facts']['Q-C04']['value'], 'unregistered')
            self.assertEqual(state['context']['route_selection_basis'], 'accepted_default')
            self.assertEqual(state['facts']['Q-C10']['value'], 'step_by_step')
            self.assertNotIn('Q-W04', state['facts'])
            self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T57_exact_short_os_question_follows_subscription_and_only_relevant_details_appear(self):
        for os_name, only_os in (('macos', 'Q-OS03'), ('windows', 'Q-OS02')):
            state = f.record_fact(initial(), 'Q-J01', 'first_subscription', source=SOURCE)
            self.assertEqual(f.next_question(state), expected('Q-C02'))
            state = f.record_fact(state, 'Q-C02', os_name, source=SOURCE)
            self.assertEqual(f.next_question(state), expected('Q-C01'))
            self.assertEqual([q['id'] for q in f.applicable_questions(state) if q['branch'] == 'os'], [only_os])
            state = f.record_fact(state, 'Q-C01', VALUES['Q-C01'], source=SOURCE)
            self.assertEqual(f.next_question(state), expected(only_os))
            self.assert_boundaries(state)

    def test_T57_unknown_declined_and_deferred_os_are_visible_without_forcing_a_platform(self):
        for kind in ('unknown', 'declined', 'deferred'):
            state, rows = os_exit(kind)
            self.assertEqual([r['question'] for r in rows], [expected(q) for q in ('Q-C02', 'Q-C01', 'Q-C08')])
            self.assertIsNone(state['facts']['Q-C02']['value'])
            self.assertEqual(state['facts']['Q-C02']['state'], kind)
            self.assertIn({'id': 'Q-C02', 'reason': kind}, f.assessment(state)['G1']['unresolved_fields'])
            self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
            self.assertEqual(f.assessment(state)['route_confirmation'], 'unconfirmed')
            self.assertFalse(any(q['branch'] in {'os', 'local', 'vm', 'vps'} for q in f.applicable_questions(state)))
            self.assert_boundaries(state)

    def test_T57_mobile_only_has_one_limited_exit_and_no_inferred_desktop_or_migration(self):
        state, rows = os_exit('mobile_only')
        self.assertEqual([r['question'] for r in rows], [expected(q) for q in ('Q-C02', 'Q-C01', 'Q-OS12', 'Q-C08')])
        self.assertEqual(state['facts']['Q-C02']['value'], 'mobile_only')
        self.assertEqual([q['id'] for q in f.applicable_questions(state) if q['branch'] == 'os'], ['Q-OS12'])
        self.assertEqual(state['facts']['Q-OS12']['value'], 'limited_common_guidance_only_no_route_selected')
        self.assertEqual(f.assessment(state)['route_confirmation'], 'unconfirmed')
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(state)))
        self.assert_boundaries(state)

    def test_T57_supplied_os_does_not_invent_subscription_or_move_it_after_os_questions(self):
        state = f.record_fact(initial(), 'Q-C02', 'macos', source=SOURCE)
        self.assertEqual(f.next_question(state), expected('Q-J01'))
        self.assertEqual(state['current_subscription']['status'], 'unknown')
        self.assertEqual(f.journey(state), 'unknown')
        state = f.record_fact(state, 'Q-J01', 'first_subscription', source=SOURCE)
        self.assertEqual(f.next_question(state), expected('Q-C01'))
        self.assertEqual(state['facts']['Q-C02']['observed_at'], TIME)
        self.assert_boundaries(state)

    def test_T29_T57_supplied_entry_facts_are_absorbed_together_and_not_reasked(self):
        facts, state = supplied()
        self.assertEqual(f.next_question(state), expected('Q-C09'))
        for qid, value in facts.items():
            self.assertEqual(state['facts'][qid]['value'], value)
            self.assertEqual(state['facts'][qid]['source'], SOURCE)
            self.assertEqual(state['facts'][qid]['observed_at'], TIME)
            self.assertEqual(state['facts'][qid]['state'], 'reported')
        reverse = f.record_facts(initial(), [{'question_id': q, 'value': v} for q, v in reversed(list(facts.items()))], source=SOURCE)
        self.assertEqual(reverse, state)
        self.assert_boundaries(state)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    else:
        unittest.main()
