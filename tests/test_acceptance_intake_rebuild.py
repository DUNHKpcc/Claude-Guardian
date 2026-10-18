"""Original intake cases: normalized offline hosts plus reviewed Agent guidance.

The literal T81 sentence does not name a plan. selected_unspecified preserves
that fourth fact without fabricating Pro/Max or claiming natural-language parsing.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import itertools
import json
import subprocess
import tempfile
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('intake_acceptance_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
TIME = '2026-10-18T05:00:00Z'
SOURCE = 'synthetic:literal-T81'
LITERAL = '第一次开通，Mac，本机，套餐已选好'
FOUR = [{'question_id': q, 'value': v} for q, v in (
    ('Q-J01', 'first_subscription'), ('Q-C02', 'macos'),
    ('Q-C05', 'local'), ('Q-C08', 'selected_unspecified'))]
PLAN_PROMPT = {'id': 'Q-C08', 'branch': 'core', 'stage': 'I2', 'postcontact': False,
    'prompt': '你已经选好套餐；具体是哪一个套餐？', 'clarification': True,
    'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
    'requires_action_authorization': False}
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
PERMISSIONS = {'private_save': False, 'export': False, 'public_export': False}
# Independently written full strings; no expectations are taken from runtime constants.
PROMPTS = {
 'Q-C02': '这次用 Mac 还是 Windows？',
 'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
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
 'Q-A01': 'A1 设备', 'Q-A02': 'A2 Apple 账户', 'Q-A03': 'A3 商店地区',
 'Q-A04': 'A4 App 与内购', 'Q-A05': 'A5 服务账户对应', 'Q-A07': 'A7 礼品卡',
 'Q-A08': 'A8 结账条件', 'Q-A09': 'A9 来源', 'Q-A10': 'A10 后续续费与改区影响',
 'Q-G01': '有可用 Android 设备，并能使用官方 Google Play 与 Claude App 吗？',
 'Q-G02': '有能正常登录验证的 Google 账户吗？Play 国家/地区和付款选项是什么？',
 'Q-G03': '当前购买页能看到目标套餐和可用付款选项吗？',
 'Q-G04': '手机 App 登录的 Claude 是否为这次准备使用的目标账户？',
 'Q-W01': '准备使用的是信用卡/借记卡/企业卡？发行国家或地区是什么？',
 'Q-W02': '结账要求的账单资料能否如实填写？',
 'Q-W03': '是否支持所需的线上/周期付款，出现过拒付或验证提示吗？',
 'Q-W04': '当前结账总额、计费周期和后续续费安排是否符合本次选择？',
 'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
 'Q-L04': 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？',
 'Q-C12': '哪些已有项目、历史、客户端或配置不能动？',
 'Q-Z01': '这次只要讲解/计划，还是允许指定范围的只读检查？',
 'Q-C10': '希望逐步指导，还是直接给检查项和命令？',
}
NETWORK = ['Q-C09', 'Q-N01', 'Q-N02', 'Q-N03', 'Q-N04', 'Q-N06']
CHANNEL_CHOICE = ['Q-P03', 'Q-P04', 'Q-P06', 'Q-P07']
CHANNEL_PC0 = {'apple': ['Q-A01', 'Q-A02', 'Q-A03', 'Q-A07', 'Q-A09', 'Q-A10'],
               'google': ['Q-G01', 'Q-G02'], 'web': ['Q-W01', 'Q-W02', 'Q-W03']}
CHANNEL_LATER = {'apple': ['Q-A04', 'Q-A05', 'Q-A08'], 'google': ['Q-G03', 'Q-G04'], 'web': ['Q-W04']}
TAIL = ['Q-L01', 'Q-L04', 'Q-C12', 'Q-Z01', 'Q-C10']
VALUES = {qid: 'synthetic_reported_not_verified' for qid in PROMPTS}
VALUES.update({'Q-C02': 'macos', 'Q-C01': 'web_writing', 'Q-C08': 'Pro',
    'Q-C03': 'no_suspension_reported', 'Q-C04': 'registered_reported',
    'Q-C05': 'accepted_default', 'Q-Z01': 'plan_only',
    'Q-C12': 'preserve_existing_projects_settings', 'Q-C10': 'step_by_step'})


def expected_question(qid):
    if qid == 'Q-OS03': branch, stage = 'os', 'I2'
    elif qid in NETWORK: branch, stage = 'network', 'I4'
    elif qid.startswith(('Q-P', 'Q-A', 'Q-G', 'Q-W')): branch, stage = 'payment', 'I4'
    elif qid.startswith('Q-L'): branch, stage = 'local', 'I5'
    elif qid in ('Q-C12', 'Q-Z01', 'Q-C10'): branch, stage = 'protection', 'I5'
    else: branch, stage = 'core', 'I2' if qid in ('Q-C02', 'Q-C01', 'Q-C08') else 'I3'
    return {'id': qid, 'branch': branch, 'stage': stage,
        'postcontact': qid in sum(CHANNEL_LATER.values(), []), 'prompt': PROMPTS[qid],
        'clarification': False, 'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
        'requires_action_authorization': False}


def envelope(qid, value, source=SOURCE, state='reported', count=0):
    return {'value': value, 'state': state, 'source': source,
        'subject_ref': 'intake-account' if qid in ('Q-J01', 'Q-C08') else 'intake-device',
        'observed_at': TIME, 'applies_when': 'current task and target',
        'required_for': ['intake', 'plan'], 'sensitivity': 'low',
        'clarification_count': count, 'blocker_reason': None}


def projection(state):
    return {'facts': deepcopy(state['facts']), 'context': deepcopy(state['context']),
        'asked_question_ids': list(state['asked_question_ids']),
        'current_subscription': deepcopy(state['current_subscription']),
        'payment_intent': state['payment_intent'], 'assessment': f.assessment(state),
        'next_question': f.next_question(state), 'persistence_consent': deepcopy(state['persistence_consent'])}


def expected_literal_assessment():
    missing = ['Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04'] + NETWORK + CHANNEL_CHOICE + TAIL
    return {'stage': 'I2', 'G1': {'status': 'partial', 'unresolved_fields': [
        {'id': q, 'reason': 'target_plan_identity_missing' if q == 'Q-C08' else 'unasked'} for q in missing]},
        'G2': {'status': 'blocked', 'conditional_plan_only': True}, 'G3': G3,
        'active_branches': ['core', 'os', 'network', 'payment', 'local', 'protection'],
        'deferred_branches': [], 'route_confirmation': 'confirmed',
        'current_subscription': {'status': 'none_reported', 'source': SOURCE, 'observed_at': TIME}}


def feed(state, sequence, channel='web', plan_clarification=False):
    """Drive a fixed authored path, rejecting an unexpected or extra question."""
    trace = []
    for qid in sequence:
        expected = PLAN_PROMPT if qid == 'Q-C08' and plan_clarification else expected_question(qid)
        actual = f.next_question(state)
        if actual != expected:
            raise AssertionError((qid, expected, actual))
        trace.append(deepcopy(actual))
        state = f.mark_asked(state, qid)
        state = f.record_fact(state, qid, channel if qid == 'Q-P06' else VALUES[qid], source='synthetic:followup', observed_at=TIME)
    return state, trace


def new():
    return f.new_state('intake-device', 'intake-account', task_id='intake-task')


def literal():
    return f.record_facts(new(), FOUR, source=SOURCE)


def reach_plan(state):
    return f.record_facts(state, [{'question_id': 'Q-C01', 'value': 'web_writing'},
        {'question_id': 'Q-OS03', 'value': 'reported_version_not_verified'}], source='synthetic:followup')


class IntakeAcceptanceRebuildTests(unittest.TestCase):
    def setUp(self):
        resources = ExitStack()
        self.addCleanup(resources.close)
        resources.enter_context(patch.object(f, '_now', return_value=TIME))
        for target in ('builtins.open', 'io.open', 'os.open', 'socket.socket', 'subprocess.Popen', 'os.system'):
            resources.enter_context(patch(target, side_effect=AssertionError('Offline acceptance attempted external I/O')))

    def test_T81_literal_retains_selection_and_clarifies_only_missing_identity(self):
        state = literal()
        self.assertEqual(state['facts']['Q-C08']['value'], 'selected_unspecified')
        self.assertEqual(state['facts']['Q-C08']['state'], 'reported')
        self.assertIn({'id': 'Q-C08', 'reason': 'target_plan_identity_missing'},
                      f.assessment(state)['G1']['unresolved_fields'])
        self.assertEqual(f.next_question(reach_plan(state)), PLAN_PROMPT)

    def assert_closed(self, state, phase='PC0'):
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(state['context']['contact_phase'], phase)
        self.assertEqual(state['persistence_consent'], PERMISSIONS)

    def test_T81_all_24_literal_orders_preserve_full_four_fact_envelopes(self):
        for order in itertools.permutations(FOUR):
            before, supplied = new(), deepcopy(list(order))
            state = f.record_facts(before, supplied, source=SOURCE)
            self.assertEqual(state['facts'], {i['question_id']: envelope(i['question_id'], i['value']) for i in FOUR})
            self.assertEqual(state['current_subscription'], {'status': 'none_reported', 'source': SOURCE, 'observed_at': TIME})
            self.assertEqual(state['payment_intent'], 'new_subscription')
            self.assertEqual(f.next_question(state), expected_question('Q-C01'))
            self.assertEqual(f.assessment(state), expected_literal_assessment())
            self.assertEqual(state['context'], {**before['context'], 'route_selection_basis': 'explicit_choice'})
            self.assertEqual(before, new())
            self.assertEqual(supplied, list(order))
            self.assert_closed(state)
        state, trace = feed(literal(), ['Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0['web'] + TAIL, plan_clarification=True)
        self.assertIsNone(f.next_question(state))
        self.assertEqual(f.assessment(state)['G1']['unresolved_fields'], [{'id': 'Q-W04', 'reason': 'requires_contact_gate'}])
        self.assertEqual(state['facts']['Q-C08'], envelope('Q-C08', 'Pro', source='synthetic:followup', count=1))
        self.assert_closed(state)

    def test_T81_clarification_is_bounded_across_ordinary_prompt_retry_and_load(self):
        state = f.record_facts(new(), FOUR[:3], source=SOURCE)
        state = f.mark_asked(reach_plan(state), 'Q-C08')
        state = f.record_fact(state, 'Q-C08', 'selected_unspecified', source=SOURCE, observed_at=TIME)
        self.assertEqual(f.next_question(state), PLAN_PROMPT)
        self.assertEqual(f.next_question(state), PLAN_PROMPT)  # render did not consume it
        shown = f.mark_asked(state, 'Q-C08')
        self.assertEqual(shown['facts']['Q-C08'], envelope('Q-C08', 'selected_unspecified', count=1))
        for current in (shown, f.loads_state(f.dumps_state(shown, host_opt_in=True)),
                        f.record_fact(shown, 'Q-C08', 'selected_unspecified', source=SOURCE, observed_at=TIME)):
            self.assertEqual(current['facts'], shown['facts'])
            self.assertEqual(f.next_question(current), expected_question('Q-C03'))
            self.assertIn({'id': 'Q-C08', 'reason': 'target_plan_identity_missing'}, f.assessment(current)['G1']['unresolved_fields'])
            self.assertEqual(f.assessment(current)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
            self.assert_closed(current)

    def test_T81_explicit_unknown_refusal_deferral_and_named_answers_have_exits(self):
        state = f.mark_asked(reach_plan(literal()), 'Q-C08')
        for outcome in ('unknown', 'declined', 'deferred'):
            current = f.record_fact(state, 'Q-C08', state_name=outcome, source='synthetic:reply', observed_at=TIME)
            self.assertEqual(current['facts']['Q-C08'], envelope('Q-C08', None, source='synthetic:reply', state=outcome, count=1))
            self.assertEqual(f.next_question(current), expected_question('Q-C03'))
            self.assertIn({'id': 'Q-C08', 'reason': outcome}, f.assessment(current)['G1']['unresolved_fields'])
            self.assert_closed(current)
        resolved = f.record_fact(state, 'Q-C08', 'Pro', source='synthetic:explicit-name', observed_at=TIME)
        self.assertEqual(resolved['facts']['Q-C08'], envelope('Q-C08', 'Pro', source='synthetic:explicit-name', count=1))
        self.assertNotIn('Q-C08', [x['id'] for x in f.assessment(resolved)['G1']['unresolved_fields']])

    def test_T81_named_plan_orders_and_nonpurchase_incident_priority_are_preserved(self):
        named = deepcopy(FOUR); named[-1]['value'] = 'Pro'
        for order in itertools.permutations(named):
            state = f.record_facts(new(), list(order), source='synthetic:explicit-named-turn')
            self.assertEqual(state['facts'], {i['question_id']: envelope(i['question_id'], i['value'], source='synthetic:explicit-named-turn') for i in named})
            self.assertNotIn('Q-C08', [x['id'] for x in f.assessment(state)['G1']['unresolved_fields']])
        state = f.record_fact(literal(), 'Q-J01', 'existing_subscriber', source='synthetic:changed-task', observed_at=TIME)
        state = f.set_context(state, task='environment')
        self.assertNotIn('Q-C08', [x['id'] for x in f.applicable_questions(state)])
        urgent = f.set_context(reach_plan(literal()), incident='credential_exposure')
        self.assertEqual(f.next_question(urgent)['id'], 'Q-H01')
        self.assertEqual(f.assessment(urgent)['G1']['status'], 'emergency_deferred')

    def test_T53_accept_default_once_then_entire_remaining_path_without_permission(self):
        state = f.record_fact(new(), 'Q-J01', 'first_subscription', source='synthetic:T53', observed_at=TIME)
        state, _ = feed(state, ['Q-C02', 'Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04'])
        self.assertEqual(f.next_question(state), expected_question('Q-C05'))
        before = deepcopy(state)
        chosen = f.record_fact(state, 'Q-C05', 'accepted_default', source='synthetic:T53-accept', observed_at=TIME)
        self.assertEqual(chosen['facts']['Q-C05'], envelope('Q-C05', 'accepted_default', source='synthetic:T53-accept'))
        self.assertEqual(chosen['context']['route_selection_basis'], 'accepted_default')
        self.assertEqual(chosen['context']['route'], 'local')
        self.assertEqual(f.assessment(chosen)['route_confirmation'], 'confirmed')
        self.assertEqual(state, before)
        chosen, trace = feed(chosen, ['Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0['web'] + TAIL)
        self.assertIsNone(f.next_question(chosen))
        self.assertNotIn('Q-C05', [q['id'] for q in trace])
        self.assert_closed(chosen)
        repeated = f.record_fact(chosen, 'Q-C05', 'accepted_default', source='synthetic:T53-accept', observed_at=TIME)
        self.assertEqual(repeated, chosen)

    def test_T53_inference_and_different_explicit_routes_do_not_accept_default(self):
        for route in ('local', 'vm', 'vps', 'compare'):
            state = f.record_fact(new(), 'Q-C05', route, source='synthetic:choice', observed_at=TIME)
            before = deepcopy(state)
            with self.assertRaisesRegex(f.InterviewError, '^No current local default proposal to accept$'):
                f.record_fact(state, 'Q-C05', 'accepted_default', source='synthetic:wrong', observed_at=TIME)
            self.assertEqual(state, before)
        inferred = f.record_fact(new(), 'Q-C05', 'accepted_default', state_name='inferred', source='synthetic:guess', observed_at=TIME)
        self.assertEqual(f.assessment(inferred)['route_confirmation'], 'unconfirmed')
        self.assertEqual(inferred['context']['route_selection_basis'], 'default_proposal')
        self.assert_closed(inferred)

    def test_T74_complete_first_subscription_branches_exclude_all_old_billing(self):
        for channel in ('apple', 'google', 'web'):
            state = f.record_fact(new(), 'Q-J01', 'first_subscription', source='synthetic:T74', observed_at=TIME)
            state = f.set_context(state, gift_card=channel == 'apple', buying_gift_card=channel == 'apple')
            sequence = ['Q-C02', 'Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C05', 'Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0[channel] + TAIL
            state, questions = feed(state, sequence, channel)
            self.assertIsNone(f.next_question(state))
            self.assertEqual(f.assessment(state)['G1']['unresolved_fields'], [{'id': q, 'reason': 'requires_contact_gate'} for q in CHANNEL_LATER[channel]])
            self.assert_closed(state)
            # Scheduling metadata only: no real contact or permission is performed.
            state = f.set_context(state, contact_phase='PC2')
            state, later = feed(state, CHANNEL_LATER[channel], channel)
            self.assertIsNone(f.next_question(state))
            self.assertEqual(f.assessment(state), {'stage': 'I6', 'G1': {'status': 'complete', 'unresolved_fields': []},
                'G2': {'status': 'pass', 'conditional_plan_only': False}, 'G3': G3,
                'active_branches': ['core', 'os', 'network', 'payment', 'local', 'protection'],
                'deferred_branches': [], 'route_confirmation': 'confirmed',
                'current_subscription': {'status': 'none_reported', 'source': 'synthetic:T74', 'observed_at': TIME}})
            self.assert_closed(state, 'PC2')
            self.assertEqual(questions + later, [expected_question(q) for q in sequence + CHANNEL_LATER[channel]])
            self.assertTrue({'Q-C07', 'Q-P02', 'Q-A06'}.isdisjoint(state['asked_question_ids']))
            self.assertTrue({'Q-C07', 'Q-P02', 'Q-A06'}.isdisjoint(q['id'] for q in f.applicable_questions(state)))

    def test_T74_actual_billing_conflict_is_a_distinct_conditional_branch(self):
        state = f.record_fact(new(), 'Q-J01', 'first_subscription', source='synthetic:T74', observed_at=TIME)
        state = f.set_context(state, billing_channel='apple')
        before = [q['id'] for q in f.applicable_questions(state)]
        after = [q['id'] for q in f.applicable_questions(f.set_context(state, subscription_conflict=True))]
        self.assertEqual([q for q in after if q not in before], ['Q-P02', 'Q-A06'])
        self.assertNotIn('Q-C07', after)


def replay():
    """Actual fixed-time receipts for review, never an expected-output generator."""
    with patch.object(f, '_now', return_value=TIME):
        first = f.record_fact(new(), 'Q-J01', 'first_subscription', source='synthetic:T53', observed_at=TIME)
        ready, prefix = feed(first, ['Q-C02', 'Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04'])
        accepted = f.record_fact(ready, 'Q-C05', 'accepted_default', source='synthetic:T53-accept', observed_at=TIME)
        finished, remaining = feed(accepted, ['Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0['web'] + TAIL)
        output = {'T53': {'utterance': '按本机默认建议来；这里只要计划。', 'prefix_questions': prefix,
            'before_acceptance': projection(ready), 'after_acceptance': projection(accepted),
            'remaining_questions': remaining, 'at_PC0_boundary': projection(finished)}}
        initial = literal()
        finished, questions = feed(initial, ['Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0['web'] + TAIL, plan_clarification=True)
        shown = f.mark_asked(reach_plan(initial), 'Q-C08')
        output['T81'] = {'literal_utterance': LITERAL, 'normalized_current_facts': deepcopy(FOUR),
            'after_single_reply': projection(initial), 'complete_missing_question_sequence': questions,
            'at_PC0_boundary': projection(finished), 'after_identity_question_delivered': projection(shown),
            'same_marker_again': projection(f.record_fact(shown, 'Q-C08', 'selected_unspecified', source=SOURCE, observed_at=TIME)),
            'explicit_exits': {outcome: projection(f.record_fact(shown, 'Q-C08', state_name=outcome, source='synthetic:reply', observed_at=TIME)) for outcome in ('unknown', 'declined', 'deferred')},
            'literal_permutations': [], 'explicit_named_permutations': []}
        for key, answers in (('literal_permutations', FOUR), ('explicit_named_permutations', [
                *deepcopy(FOUR[:-1]), {'question_id': 'Q-C08', 'value': 'Pro'}])):
            for order in itertools.permutations(answers):
                source = SOURCE if key == 'literal_permutations' else 'synthetic:explicit-named-turn'
                output['T81'][key].append({'normalized_input': list(order),
                    'actual': projection(f.record_facts(new(), list(order), source=source))})
        output['T74'] = {}
        for channel in ('apple', 'google', 'web'):
            initial = f.record_fact(new(), 'Q-J01', 'first_subscription', source='synthetic:T74', observed_at=TIME)
            initial = f.set_context(initial, gift_card=channel == 'apple', buying_gift_card=channel == 'apple')
            sequence = ['Q-C02', 'Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C05', 'Q-C06'] + NETWORK + CHANNEL_CHOICE + CHANNEL_PC0[channel] + TAIL
            precontact, trace = feed(initial, sequence, channel)
            final, later = feed(f.set_context(precontact, contact_phase='PC2'), CHANNEL_LATER[channel], channel)
            output['T74'][channel] = {'utterance': '明确第一次准备订阅，还没有提供目标套餐。',
                'initial': projection(initial), 'PC0_questions': trace,
                'at_PC0_boundary': projection(precontact),
                'synthetic_postcontact_questions': later, 'after_all_applicable_answers': projection(final)}
        return output


class IntakeClarificationCLITests(unittest.TestCase):
    """Only dedicated synthetic cloud files; no native or contact execution."""
    def run_reply(self, state, answer=None):
        with tempfile.TemporaryDirectory(prefix='guardian-intake-') as directory:
            root = Path(directory)
            saved, reply, output = root / 'before.json', root / 'answer.json', root / 'after.json'
            original = f.dumps_state(state, host_opt_in=True)
            saved.write_text(original, encoding='utf-8')
            command = [sys.executable, '-B', str(ROOT / 'skills/claude-guardian/scripts/interview_cli.py'),
                       '--input', str(saved), '--output', str(output)]
            if answer is not None:
                reply.write_text(json.dumps(answer), encoding='utf-8')
                command += ['--answer-file', str(reply)]
            result = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(saved.read_text(encoding='utf-8'), original)
            return (result, json.loads(result.stdout),
                    f.loads_state(output.read_text(encoding='utf-8')) if output.exists() else None)

    def pending(self):
        with patch.object(f, '_now', return_value=TIME):
            return reach_plan(literal())

    def test_matching_cli_reply_consumes_identity_clarification_but_render_does_not(self):
        with tempfile.TemporaryDirectory(prefix='guardian-intake-') as directory:
            root = Path(directory)
            with patch.object(f, '_now', return_value=TIME):
                state = reach_plan(literal())
            saved, answer, output = root / 'before.json', root / 'answer.json', root / 'after.json'
            saved.write_text(f.dumps_state(state, host_opt_in=True), encoding='utf-8')
            answer.write_text(json.dumps({'question_id': 'Q-C08', 'value': 'selected_unspecified'}), encoding='utf-8')
            command = [sys.executable, '-B', str(ROOT / 'skills/claude-guardian/scripts/interview_cli.py'), '--input', str(saved)]
            shown = subprocess.run(command, capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(shown.returncode, 0, shown.stderr)
            self.assertEqual(json.loads(shown.stdout)['question'], PLAN_PROMPT)
            self.assertEqual(f.loads_state(saved.read_text(encoding='utf-8'))['facts']['Q-C08']['clarification_count'], 0)
            result = subprocess.run(command + ['--answer-file', str(answer), '--output', str(output)],
                                    capture_output=True, text=True, encoding='utf-8', timeout=10)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(json.loads(result.stdout)['question'], expected_question('Q-C03'))
            after = f.loads_state(output.read_text(encoding='utf-8'))
            self.assertEqual(after['facts']['Q-C08']['clarification_count'], 1)
            self.assertEqual(after['facts']['Q-C08']['value'], 'selected_unspecified')
            self.assertIn({'id': 'Q-C08', 'reason': 'target_plan_identity_missing'}, f.assessment(after)['G1']['unresolved_fields'])

    def test_single_and_batch_marker_replies_spend_once_and_never_reopen(self):
        for batch in (False, True):
            answer = {'question_id': 'Q-C08', 'value': 'selected_unspecified'}
            item = {'answers': [answer]} if batch else answer
            result, public, after = self.run_reply(self.pending(), item)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(public['question'], expected_question('Q-C03'))
            self.assertEqual(after['facts']['Q-C08']['clarification_count'], 1)
            for retry in (None, item):
                result, public, retried = self.run_reply(after, retry)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(public['question'], expected_question('Q-C03'))
                self.assertEqual(retried['facts']['Q-C08']['clarification_count'], 1)
                self.assertEqual(retried['facts']['Q-C08']['value'], 'selected_unspecified')
                if retry is None:
                    self.assertEqual(retried, after)

    def test_named_unknown_declined_deferred_matching_replies_have_exits(self):
        for outcome in ('reported', 'unknown', 'declined', 'deferred'):
            with self.subTest(outcome=outcome):
                answer = {'question_id': 'Q-C08', 'state': outcome,
                          'value': 'Pro' if outcome == 'reported' else None}
                result, public, after = self.run_reply(self.pending(), {'answers': [answer]})
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(public['question'], expected_question('Q-C03'))
                fact = after['facts']['Q-C08']
                self.assertEqual((fact['state'], fact['value'], fact['clarification_count']),
                                 (outcome, answer['value'], 1))
                self.assertEqual(fact['source'], 'user:current-turn')
                unresolved = [i for i in public['assessment']['G1']['unresolved_fields'] if i['id'] == 'Q-C08']
                self.assertEqual(unresolved, [] if outcome == 'reported' else [{'id': 'Q-C08', 'reason': outcome}])
                self.assertEqual(public['assessment']['G3'], G3)

    def test_unrelated_batch_render_and_load_do_not_spend_or_rewrite_marker(self):
        original = self.pending()
        for reply in (None, {'answers': [{'question_id': 'Q-C03', 'value': 'no_suspension_reported'}]}):
            result, public, after = self.run_reply(original, reply)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(public['question'], PLAN_PROMPT)
            self.assertEqual(after['facts']['Q-C08'], original['facts']['Q-C08'])
            result, public, loaded = self.run_reply(after)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(public['question'], PLAN_PROMPT)
            self.assertEqual(loaded, after)

    def test_invalid_batch_never_saves_or_spends_a_clarification(self):
        state = self.pending()
        before = deepcopy(state)
        invalid = {'answers': [{'question_id': 'Q-C08', 'value': 'selected_unspecified'},
                               {'question_id': 'Q-NOT-A-QUESTION', 'value': 'private-invalid-text'}]}
        result, public, after = self.run_reply(state, invalid)
        self.assertEqual(result.returncode, 2)
        self.assertEqual(public, {'status': 'blocked', 'code': 'INVALID_OR_UNAUTHORIZED_INTERVIEW_IO', 'action_executed': False})
        self.assertIsNone(after)
        self.assertEqual(state, before)
        self.assertNotIn('private-invalid-text', result.stdout + result.stderr)

    def test_ordinary_and_stale_plan_prompts_do_not_spend_identity_clarification(self):
        with patch.object(f, '_now', return_value=TIME):
            ordinary = reach_plan(f.record_facts(new(), FOUR[:3], source=SOURCE))
            stale = f.record_fact(self.pending(), 'Q-C08', 'selected_unspecified',
                                  state_name='stale', source=SOURCE, observed_at=TIME)
        for state in (ordinary, f.mark_asked(ordinary, 'Q-C08'), stale):
            if state is not stale and 'Q-C08' in state['asked_question_ids']:
                # Prior ordinary prompt was delivered; it is not the identity prompt.
                self.assertEqual(f.next_question(state), expected_question('Q-C03'))
            else:
                expected = expected_question('Q-C08')
                if state is stale:
                    expected['clarification'] = True
                self.assertEqual(f.next_question(state), expected)
            result, public, after = self.run_reply(state, {'question_id': 'Q-C08', 'value': 'selected_unspecified'})
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertEqual(public['question'], PLAN_PROMPT)
            self.assertEqual(after['facts']['Q-C08']['clarification_count'], 0)


if __name__ == '__main__':
    if sys.argv[1:] == ['--replay']:
        print(json.dumps(replay(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        unittest.main()
