"""Original T01/T02 whole-case L evidence and inspectable C-review receipts.

These are normalized, synthetic cloud-only replays, not an NLP/model evaluation,
native-device observation, purchase, contact, or proof of a real authorization.
L0/L4 change the host's explanation depth via Q-C10, not a new expertise enum.
Run with --replay to inspect actual full states, questions, and assessments.
All expectations below are authored independently of runtime constants/outputs.
"""
from contextlib import ExitStack, contextmanager
from copy import deepcopy
from dataclasses import asdict, replace
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1])).resolve()
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'


def load_module(name, filename):
    spec = importlib.util.spec_from_file_location(name, SCRIPTS / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


f = load_module('intake_basics_acceptance_flow', 'interview_flow.py')
w = load_module('intake_basics_workflow_guard', 'workflow_guard.py')
# Read immutable inputs/guidance before the no-I/O boundary. Fixtures supply
# inputs only; no expected prompt/assessment/state is copied from runtime output.
ROUTE_FIXTURE = json.loads((ROOT / 'tests/fixtures/acceptance-routes-rebuild.json').read_text(encoding='utf-8'))
SPEC_TEXT = (ROOT / 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8')
TRACKER_TEXT = (ROOT / 'docs/implementation-tracker.md').read_text(encoding='utf-8')
INTAKE_GUIDE = (ROOT / 'skills/claude-guardian/references/intake.md').read_text(encoding='utf-8')
ROUTE_GUIDE = (ROOT / 'skills/claude-guardian/references/routes-and-platforms.md').read_text(encoding='utf-8')
TIME = '2026-10-18T07:00:00Z'
LATER = '2026-10-18T07:05:00Z'
T01_SOURCE = 'synthetic:T01-web-writing'
T02_SOURCE = 'synthetic:T02-complete-environment'
DEVICE = 'basics-device'
ACCOUNT = 'basics-account'
TASK = 'basics-task'
PERMISSIONS = {'private_save': False, 'export': False, 'public_export': False}
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
POLICY = {
    'schema_version': 'guardian-traffic-policy/0.1',
    'requirement_id': 'PRODUCT-IPV4-20261018', 'effective_from': '2026-10-18',
    'policy': 'IPv4_ONLY', 'applies_to': 'claude_target_application_traffic',
    'ipv6_fallback': 'forbidden', 'proxy_outer_transport': 'preserve_existing_independently',
    'control_channels': 'preserve', 'other_applications': 'unchanged',
    'enforcement_status': 'unknown', 'compliance': 'not_established',
    'environment_pass': False, 'apply_supported': False, 'authorization': 'none',
}
CONTEXT = {
    'task': 'subscription_preparation', 'incident': 'none', 'incident_resolved': False,
    'incident_origin': 'host', 'account_incident_resolved': False,
    'ambiguous_experience': False, 'subscription_conflict': False,
    'billing_channel': 'unselected', 'route': 'local',
    'route_selection_basis': 'default_proposal', 'contact_phase': 'PC0',
    'os_issue': 'none', 'language_change_needed': False, 'timezone_issue': False,
    'windows10': False, 'compatibility_needed': False, 'budget_needed': False,
    'gift_card': False, 'buying_gift_card': False, 'changing_store_region': False,
    'organization_task': False, 'billing_product_ambiguous': False,
    'existing_test': False, 'integration_used': False, 'change_planned': False,
    'persistence_requested': False, 'purchase_completed': False,
    'paused': False, 'blocked_reason': None,
}
PROMPTS = {
    'Q-J01': '这次是第一次准备订阅（包括只用过免费版）、以前订阅过目前无有效订阅准备重订、当前已有订阅，还是不确定？',
    'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
    'Q-C02': '这次用 Mac 还是 Windows？',
    'Q-C03': '以前 Claude 账号被明确停用/封禁过吗，还是只遇到报错？',
    'Q-C04': '准备用的 Claude 账号注册了吗？已有账号现在能正常登录吗？',
    'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
    'Q-C06': '已有账号通过什么方式登录/接入？不懂名称可描述界面。',
    'Q-C08': '你这次想订阅什么套餐？ 选好了直接说；未决定先按用途和预算比较。',
    'Q-C09': '实际在哪个国家/地区使用？是否有跨地区安排？无需详细地址。',
    'Q-C10': '希望逐步指导，还是直接给检查项和命令？',
    'Q-C11': '老用户这次主要是续费/升级、调整使用方案，还是检查环境/解决问题？',
    'Q-C12': '哪些已有项目、历史、客户端或配置不能动？',
    'Q-OS03': '如果 Mac：macOS 大致版本是什么？',
    'Q-N01': '当前是普通网络直接连接，还是使用代理/VPN/公司网络？软件名称知道就说。',
    'Q-N02': '浏览器、Code、代理分别运行在哪里？使用系统代理、应用代理、TUN 还是不确定？',
    'Q-N03': '网络是否常切换、自动换节点或跨地区？有计划长期固定使用的环境吗？',
    'Q-N04': '还有手机、其他电脑或远程工作区同时/交替使用吗？各自用来做什么？',
    'Q-N05': '已做过哪些网络测试？何时、在哪个设备、用哪个程序测的？',
    'Q-N06': '是否受公司网络、证书、安全软件、代理策略或设备管理限制？',
    'Q-P02': '这次相关的原套餐/旧购买渠道及待处理订单是什么？',
    'Q-P03': '可用于付款的设备有 iPhone/iPad、Android，还是只有电脑？',
    'Q-P04': '已有可用的商店账户/余额、银行卡、企业付款方式，还是尚未准备？',
    'Q-P05': '月费和一次性准备费用能接受什么范围？',
    'Q-P06': '更倾向哪种可行付款方式？需要先比较步骤吗？',
    'Q-P07': '后续准备怎样续费？需要说明账单查看与取消入口吗？',
    'Q-W01': '准备使用的是信用卡/借记卡/企业卡？发行国家或地区是什么？',
    'Q-W02': '结账要求的账单资料能否如实填写？',
    'Q-W03': '是否支持所需的线上/周期付款，出现过拒付或验证提示吗？',
    'Q-W04': '当前结账总额、计费周期和后续续费安排是否符合本次选择？',
    'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
    'Q-L02': '系统/架构是否满足当前客户端要求？',
    'Q-L03': '当前有 MCP、插件、hooks、代理网关或其他开发工具吗？',
    'Q-L04': 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？',
    'Q-Z01': '这次只要讲解/计划，还是允许指定范围的只读检查？',
    'Q-Z03': '允许哪些具体变更，是否需要组织管理员处理？',
    'Q-Z04': '有没有备份、回滚或独立救援条件？',
    'Q-Z05': '是否保存/导出不含秘密的本次进度，还是仅留在当前对话？',
}
NETWORK = ['Q-C09', 'Q-N01', 'Q-N02', 'Q-N03', 'Q-N04', 'Q-N06']
PAYMENT = ['Q-P03', 'Q-P04', 'Q-P06', 'Q-P07', 'Q-W01', 'Q-W02', 'Q-W03']
TAIL = ['Q-L01', 'Q-L04', 'Q-C12', 'Q-Z01']
ACCOUNT_IDS = {'Q-J01', 'Q-C03', 'Q-C04', 'Q-C06', 'Q-C08',
               'Q-P02', 'Q-P03', 'Q-P04', 'Q-P05', 'Q-P06', 'Q-P07',
               'Q-W01', 'Q-W02', 'Q-W03', 'Q-W04'}
T01_VALUES = {
    'Q-C01': 'web_writing', 'Q-C10': 'step_by_step',
    'Q-C02': 'macos', 'Q-OS03': 'synthetic_version_reported',
    'Q-C08': 'Pro', 'Q-C03': 'no_suspension_reported',
    'Q-C04': 'registered_reported', 'Q-C05': 'accepted_default',
    'Q-C06': 'official_login_reported', 'Q-C09': 'region_reported_not_verified',
    'Q-N01': 'existing_proxy_reported', 'Q-N02': 'browser_on_selected_mac_system_proxy_reported',
    'Q-N03': 'stable_network_intended', 'Q-N04': 'no_other_workspaces_reported',
    'Q-N06': 'no_management_restrictions_reported',
    'Q-P02': 'existing_plan_and_web_channel_reported_no_order_problem',
    'Q-P03': 'computer_only', 'Q-P04': 'card_category_only_no_number',
    'Q-P05': 'compare_costs_without_purchase_authorization',
    'Q-P06': 'web', 'Q-P07': 'explain_renewal_and_cancellation',
    'Q-W01': 'debit_card_issuing_region_reported_no_number',
    'Q-W02': 'can_provide_truthful_billing_details_privately',
    'Q-W03': 'recurring_online_support_reported_not_verified',
    'Q-W04': 'synthetic_quote_review_only_no_payment_authorization',
    'Q-L01': 'browser_only_existing_version_reported',
    'Q-L04': 'web_writing_no_local_project_access',
    'Q-C12': 'preserve_existing_projects_settings', 'Q-Z01': 'plan_only',
    'Q-C11': 'upgrade',
}
# T01's current-user arm follows original T77, not the new-purchase survey.
UPGRADE_ORDER = {'plan': 'current-plan-A', 'billing_channel': 'web'}
UPGRADE_PROMPT = '升级所需的当前套餐和原购买渠道是什么？只说已知情况；不确定或暂不回答也可以，无需打开 Claude。'

T02_FLAGS = {'existing_test': True, 'integration_used': True, 'compatibility_needed': True}
T02_INPUT = deepcopy(ROUTE_FIXTURE['common_answers'])
for item in T02_INPUT:
    if item['question_id'] == 'Q-C10':
        item['value'] = 'expert_difference_checklist'
    elif item['question_id'] == 'Q-N02':
        item['value'] = 'browser_and_code_on_selected_mac_proxy_system_and_tun_reported'
    elif item['question_id'] == 'Q-Z01':
        item['value'] = 'plan_only_actions_need_separate_authorization'
    if item['question_id'] in ('Q-C02', 'Q-OS03'):
        item['source'] = 'synthetic:T02-user-device-summary'
T02_INPUT += [{'question_id': qid, 'value': value} for qid, value in (
    ('Q-C11', 'environment'), ('Q-C05', 'local'),
    ('Q-N05', {'program': 'code', 'device': DEVICE, 'result': 'reported_not_observed', 'when': TIME}),
    ('Q-L01', 'existing_official_code_installation_version_reported'),
    ('Q-L04', 'preserve_local_projects_no_remote_migration'),
    ('Q-L02', 'macos_arm64_compatibility_reported_not_verified'),
    ('Q-L03', {'mcp': 'existing_local_integration', 'hooks': 'preserve', 'gateway': 'none_reported'}),
)]
T02_REQUIRED = ['Q-J01', 'Q-C02', 'Q-C01', 'Q-OS03', 'Q-C03', 'Q-C04', 'Q-C06'] + NETWORK + [
    'Q-N05', 'Q-L01', 'Q-L04', 'Q-L02', 'Q-L03', 'Q-C12', 'Q-Z01', 'Q-C10']


def question(qid, *, clarification=False):
    if qid in ('Q-J01', 'Q-C11'):
        branch, stage = 'core', 'I1'
    elif qid == 'Q-OS03':
        branch, stage = 'os', 'I2'
    elif qid in NETWORK + ['Q-N05']:
        branch, stage = 'network', 'I4'
    elif qid.startswith(('Q-P', 'Q-W')):
        branch, stage = 'payment', 'I4'
    elif qid.startswith('Q-L'):
        branch, stage = 'local', 'I5'
    elif qid in ('Q-C12', 'Q-Z01', 'Q-C10', 'Q-Z03', 'Q-Z04', 'Q-Z05'):
        branch, stage = 'protection', 'I5'
    else:
        branch, stage = 'core', 'I2' if qid in ('Q-C01', 'Q-C02', 'Q-C08') else 'I3'
    return {'id': qid, 'branch': branch, 'stage': stage, 'postcontact': qid == 'Q-W04',
            'prompt': PROMPTS[qid], 'clarification': clarification,
            'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
            'requires_action_authorization': False}


def requirement(qid):
    expected = question(qid)
    return {key: expected[key] for key in ('id', 'branch', 'stage', 'postcontact')}


def envelope(qid, value, source, *, state='reported', at=TIME, count=0, blocker=None):
    return {'value': deepcopy(value), 'state': state, 'source': source,
            'subject_ref': ACCOUNT if qid in ACCOUNT_IDS else DEVICE,
            'observed_at': at, 'applies_when': 'current task and target',
            'required_for': ['intake', 'plan'], 'sensitivity': 'low',
            'clarification_count': count, 'blocker_reason': blocker}


def subscription(status, source):
    return {'status': status, 'source': source, 'observed_at': TIME if source else None}


def expected_state(facts=None, *, context=None, asked=(), status='unknown', source=None,
                   payment='unresolved', purchase='subscription_preparation'):
    return {'schema_version': '1.0.0', 'task_id': TASK, 'target_alias': DEVICE,
            'account_alias': ACCOUNT, 'facts': deepcopy(facts or {}),
            'context': {**deepcopy(CONTEXT), **(context or {})},
            'asked_question_ids': list(asked), 'deferred_branches': [],
            'current_subscription': subscription(status, source), 'payment_intent': payment,
            'purchase_intent': purchase, 'persistence_consent': deepcopy(PERMISSIONS)}


def assessment(*, source, status, missing=(), stage='I6', payment=False, confirmed=True):
    return {'traffic_policy': deepcopy(POLICY), 'stage': stage,
            'G1': {'status': 'partial' if missing else 'complete', 'unresolved_fields': deepcopy(list(missing))},
            'G2': {'status': 'blocked' if missing else 'pass', 'conditional_plan_only': bool(missing)},
            'G3': deepcopy(G3), 'active_branches': ['core', 'os', 'network'] + (['payment'] if payment else []) + ['local', 'protection'],
            'deferred_branches': [], 'route_confirmation': 'confirmed' if confirmed else 'unconfirmed',
            'current_subscription': subscription(status, source)}


def project(state):
    return {'state': deepcopy(state), 'question': f.next_question(state),
            'assessment': f.assessment(state), 'applicable_questions': f.applicable_questions(state)}


@contextmanager
def no_external_io():
    with ExitStack() as stack:
        stack.enter_context(patch.object(f, '_now', return_value=TIME))
        for target in ('builtins.open', 'io.open', 'os.open',
                       'socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                       'socket.gethostbyname', 'socket.gethostbyname_ex', 'socket.gethostbyaddr',
                       'subprocess.Popen', 'subprocess.run', 'subprocess.call',
                       'subprocess.check_call', 'subprocess.check_output', 'os.system', 'os.popen'):
            stack.enter_context(patch(target, side_effect=AssertionError('Cloud-only intake attempted external I/O: ' + target)))
        yield


def new():
    return f.new_state(DEVICE, ACCOUNT, task_id=TASK)


def t01_initial():
    return f.record_facts(new(), [{'question_id': 'Q-C01', 'value': 'web_writing'},
        {'question_id': 'Q-C10', 'value': 'step_by_step'}], source=T01_SOURCE)


def t01_sequence(journey):
    if journey == 'existing_subscriber':
        return ['Q-J01', 'Q-C11', 'Q-P02', 'Q-C08']
    return ['Q-J01'] + (['Q-C11'] if journey == 'existing_subscriber' else []) + [
        'Q-C02', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C05', 'Q-C06'] + NETWORK + (
        ['Q-P02'] if journey == 'existing_subscriber' else []) + PAYMENT + TAIL


def t01_required(journey, *, plan='Pro'):
    if journey == 'existing_subscriber':
        return ['Q-P02', 'Q-C08']
    return ['Q-J01', 'Q-C02', 'Q-C01', 'Q-OS03', 'Q-C08', 'Q-C03', 'Q-C04', 'Q-C06'] + NETWORK + (
        ['Q-P02'] if journey == 'existing_subscriber' else []) + (['Q-P05'] if plan == 'undecided' else []) + [
        'Q-P07', 'Q-W01', 'Q-W02', 'Q-W03', 'Q-W04'] + TAIL + ['Q-C10']


def t01_question(qid, journey):
    expected = question(qid)
    if journey == 'existing_subscriber' and qid == 'Q-P02':
        expected['prompt'] = UPGRADE_PROMPT
    return expected


def drive_t01(journey):
    state, trace = t01_initial(), []
    for qid in t01_sequence(journey):
        actual = f.next_question(state)
        if actual != t01_question(qid, journey):
            raise AssertionError({'expected': t01_question(qid, journey), 'actual': actual})
        trace.append(deepcopy(actual))
        state = f.record_fact(f.mark_asked(state, qid), qid,
                              journey if qid == 'Q-J01' else UPGRADE_ORDER if journey == 'existing_subscriber' and qid == 'Q-P02' else T01_VALUES[qid],
                              source=T01_SOURCE, observed_at=TIME)
    trace.append(f.next_question(state))
    return state, trace


def t02_initial():
    return f.set_context(new(), **T02_FLAGS)


def t02_complete():
    return f.record_facts(t02_initial(), deepcopy(T02_INPUT), source=T02_SOURCE)


def expected_t02_state():
    facts = {item['question_id']: envelope(item['question_id'], item['value'], item.get('source', T02_SOURCE)) for item in T02_INPUT}
    return expected_state(facts, context={**T02_FLAGS, 'task': 'environment', 'route_selection_basis': 'explicit_choice'},
                          status='active_reported', source=T02_SOURCE, payment='none', purchase='none')


class IntakeBasicsAcceptanceTests(unittest.TestCase):
    def setUp(self):
        self.io_guard = no_external_io()
        self.io_guard.__enter__()
        self.addCleanup(self.io_guard.__exit__, None, None, None)
        self.maxDiff = None

    def assert_closed(self, state):
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(state['persistence_consent'], PERMISSIONS)
        for scope in ('private_save', 'export', 'public_export'):
            with self.subTest(scope=scope), self.assertRaises(f.InterviewError):
                f.dumps_state(state, scope=scope)

    def assert_t01(self, journey):
        if journey == 'existing_subscriber':
            return self.assert_t01_upgrade()
        initial = t01_initial()
        self.assertEqual(initial, expected_state({
            'Q-C01': envelope('Q-C01', 'web_writing', T01_SOURCE),
            'Q-C10': envelope('Q-C10', 'step_by_step', T01_SOURCE)}))
        self.assertEqual(f.next_question(initial), question('Q-J01'))
        self.assertEqual(f.assessment(initial)['route_confirmation'], 'unconfirmed')
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(initial)))
        self.assert_closed(initial)
        state, trace = drive_t01(journey)
        sequence = t01_sequence(journey)
        self.assertEqual(trace, [question(qid) for qid in sequence] + [None])
        facts = {qid: envelope(qid, value, T01_SOURCE) for qid, value in (
            [('Q-C01', 'web_writing'), ('Q-C10', 'step_by_step')] + [
            (qid, journey if qid == 'Q-J01' else T01_VALUES[qid]) for qid in sequence])}
        status = 'active_reported' if journey == 'existing_subscriber' else 'none_reported'
        task = 'upgrade' if journey == 'existing_subscriber' else 'subscription_preparation'
        payment = {'first_subscription': 'new_subscription', 'returning_subscription': 'resubscribe',
                   'existing_subscriber': 'upgrade'}[journey]
        self.assertEqual(state, expected_state(facts, asked=sequence,
            context={'task': task, 'billing_channel': 'web', 'route_selection_basis': 'accepted_default'},
            status=status, source=T01_SOURCE, payment=payment))
        self.assertEqual(f.assessment(state), assessment(source=T01_SOURCE, status=status, payment=True,
            missing=[{'id': 'Q-W04', 'reason': 'requires_contact_gate'}], stage='I4'))
        self.assertEqual(f.applicable_questions(state), [requirement(q) for q in t01_required(journey)])
        # The exact route prompt intentionally permits a short optional VM/VPS
        # comparison. Only irrelevant resource/account/script branches are absent.
        self.assertIn(question('Q-C05'), trace)
        self.assertFalse(any(q['id'].startswith(('Q-V', 'Q-S', 'Q-I', 'Q-E')) for q in f.applicable_questions(state)))
        self.assertNotIn('Q-C07', state['facts'])
        self.assertNotIn('Q-C07', state['asked_question_ids'])
        self.assertEqual(state['facts']['Q-C10']['value'], 'step_by_step')
        self.assert_closed(state)
        self.assertEqual(f.next_question(state), None)
        self.assertEqual(f.loads_state(json.dumps(state)), state)
        if journey != 'existing_subscriber':
            self.assertTrue({'Q-C11', 'Q-P02', 'Q-A06'}.isdisjoint(state['asked_question_ids']))
        return state

    def assert_t01_upgrade(self):
        """Original T01 classification plus T77's precise current-user scope.

        Historical broad-path replay is retained in dated evidence. These exact
        expected outputs were authored before observing repaired output.
        """
        initial = t01_initial()
        self.assertEqual(initial, expected_state({
            'Q-C01': envelope('Q-C01', 'web_writing', T01_SOURCE),
            'Q-C10': envelope('Q-C10', 'step_by_step', T01_SOURCE)}))
        self.assertEqual(f.next_question(initial), question('Q-J01'))
        self.assertEqual(f.assessment(initial)['route_confirmation'], 'unconfirmed')
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(initial)))
        self.assert_closed(initial)
        state, trace = drive_t01('existing_subscriber')
        sequence = ['Q-J01', 'Q-C11', 'Q-P02', 'Q-C08']
        self.assertEqual(trace, [t01_question(qid, 'existing_subscriber') for qid in sequence] + [None])
        facts = {qid: envelope(qid, value, T01_SOURCE) for qid, value in (
            ('Q-C01', 'web_writing'), ('Q-C10', 'step_by_step'),
            ('Q-J01', 'existing_subscriber'), ('Q-C11', 'upgrade'),
            ('Q-P02', UPGRADE_ORDER), ('Q-C08', 'Pro'))}
        expected = expected_state(facts, asked=sequence, context={'task': 'upgrade'},
                                  status='active_reported', source=T01_SOURCE, payment='upgrade')
        self.assertEqual(state, expected)
        self.assertEqual(f.applicable_questions(state), [requirement(q) for q in ['Q-P02', 'Q-C08']])
        self.assertEqual(f.assessment(state), {
            'traffic_policy': deepcopy(POLICY), 'stage': 'I6',
            'G1': {'status': 'complete', 'unresolved_fields': []},
            'G2': {'status': 'pass', 'conditional_plan_only': False}, 'G3': deepcopy(G3),
            'active_branches': ['payment', 'core'], 'deferred_branches': [],
            'route_confirmation': 'unconfirmed',
            'current_subscription': subscription('active_reported', T01_SOURCE),
            'upgrade_scope': {'current_order_gaps': [], 'billing_feasibility': 'not_established'}})
        self.assertEqual(state['facts']['Q-P02']['value'], {'plan': 'current-plan-A', 'billing_channel': 'web'})
        self.assertEqual(state['facts']['Q-C08']['value'], 'Pro')
        self.assertEqual(state['context']['billing_channel'], 'unselected')
        self.assertEqual(state['context']['route_selection_basis'], 'default_proposal')
        self.assertTrue({'Q-C07', 'Q-A06', 'Q-C13', 'Q-C05'}.isdisjoint(state['facts']))
        self.assertEqual(state['facts']['Q-C10']['value'], 'step_by_step')
        self.assert_closed(state)
        self.assertIsNone(f.next_question(state))
        self.assertEqual(f.loads_state(json.dumps(state)), expected)
        return state

    def test_T01_first_subscription_web_writing_whole_PC0_trace(self):
        self.assert_t01('first_subscription')

    def test_T01_returning_subscription_web_writing_whole_PC0_trace(self):
        self.assert_t01('returning_subscription')

    def test_T01_existing_subscription_upgrade_task_whole_PC0_trace(self):
        self.assert_t01('existing_subscriber')

    def test_T01_target_plan_uncertain_has_relevant_budget_gap_not_forced_purchase(self):
        state, _ = drive_t01('first_subscription')
        changed = f.record_fact(state, 'Q-C08', 'undecided', source='synthetic:T01-plan-comparison', observed_at=LATER)
        expected = deepcopy(state)
        expected['facts']['Q-C08'] = envelope('Q-C08', 'undecided', 'synthetic:T01-plan-comparison', at=LATER)
        self.assertEqual(changed, expected)
        self.assertEqual(f.next_question(changed), question('Q-P05'))
        self.assertEqual(f.assessment(changed), assessment(source=T01_SOURCE, status='none_reported', payment=True,
            missing=[{'id': 'Q-P05', 'reason': 'unasked'}, {'id': 'Q-W04', 'reason': 'requires_contact_gate'}], stage='I4'))
        self.assertEqual(f.applicable_questions(changed), [requirement(q) for q in t01_required('first_subscription', plan='undecided')])
        answered = f.record_fact(f.mark_asked(changed, 'Q-P05'), 'Q-P05', T01_VALUES['Q-P05'], source='synthetic:T01-budget', observed_at=LATER)
        self.assertIsNone(f.next_question(answered))
        self.assertEqual(f.assessment(answered), assessment(source=T01_SOURCE, status='none_reported', payment=True,
            missing=[{'id': 'Q-W04', 'reason': 'requires_contact_gate'}], stage='I4'))
        self.assert_closed(answered)

    def test_T02_expert_preference_alone_does_not_infer_subscription_route_or_permission(self):
        expert = f.record_fact(new(), 'Q-C10', 'expert_difference_checklist',
                               source='synthetic:T02-explanation-preference', observed_at=TIME)
        self.assertEqual(expert, expected_state({
            'Q-C10': envelope('Q-C10', 'expert_difference_checklist', 'synthetic:T02-explanation-preference')}))
        self.assertEqual(f.next_question(expert), question('Q-J01'))
        self.assertEqual(f.assessment(expert)['route_confirmation'], 'unconfirmed')
        self.assertFalse(any(q['branch'] in {'local', 'vm', 'vps'} for q in f.applicable_questions(expert)))
        self.assert_closed(expert)

    def test_T02_complete_expert_batch_reuses_all_facts_without_questions(self):
        before, supplied = t02_initial(), deepcopy(T02_INPUT)
        original, input_copy = deepcopy(before), deepcopy(supplied)
        state = f.record_facts(before, supplied, source=T02_SOURCE)
        self.assertEqual(before, original)
        self.assertEqual(supplied, input_copy)
        self.assertEqual(state, expected_t02_state())
        self.assertEqual(f.next_question(state), None)
        self.assertEqual(f.applicable_questions(state), [requirement(q) for q in T02_REQUIRED])
        self.assertEqual(f.assessment(state), assessment(source=T02_SOURCE, status='active_reported'))
        self.assertEqual(state['asked_question_ids'], [])
        # Already supplied Q-C11, local choice and expert explanation preference
        # remain facts even though not separately asked or currently required.
        self.assertEqual(set(state['facts']), {item['question_id'] for item in T02_INPUT})
        self.assertEqual(state['facts']['Q-C10']['value'], 'expert_difference_checklist')
        self.assertTrue(all(fact['state'] == 'reported' for fact in state['facts'].values()))
        self.assert_closed(state)
        self.assertEqual(f.loads_state(json.dumps(state)), expected_t02_state())
        self.assertEqual(f.next_question(f.loads_state(json.dumps(state))), None)
        # Mutating caller-owned containers cannot silently change recorded facts.
        supplied[-1]['value']['hooks'] = 'caller_changed_after_recording'
        self.assertEqual(state, expected_t02_state())

    def test_T02_complete_batch_order_does_not_change_facts_or_gate_readiness(self):
        batches = [list(reversed(T02_INPUT)), T02_INPUT[8:] + T02_INPUT[:8]]
        for supplied in batches:
            with self.subTest(order=[item['question_id'] for item in supplied]):
                before, input_copy = t02_initial(), deepcopy(supplied)
                original = deepcopy(before)
                state = f.record_facts(before, supplied, source=T02_SOURCE)
                self.assertEqual(state, expected_t02_state())
                self.assertEqual(f.assessment(state), assessment(source=T02_SOURCE, status='active_reported'))
                self.assertIsNone(f.next_question(state))
                self.assertEqual(state['asked_question_ids'], [])
                self.assertEqual(before, original)
                self.assertEqual(supplied, input_copy)
                self.assert_closed(state)

    def test_T02_later_stale_fact_only_reopens_its_scoped_prerequisite(self):
        complete = t02_complete()
        stale = f.record_fact(complete, 'Q-N02', 'previous_proxy_mode_requires_refresh', state_name='stale',
                              source='synthetic:T02-stale-report', observed_at=LATER)
        expected = expected_t02_state()
        expected['facts']['Q-N02'] = envelope('Q-N02', 'previous_proxy_mode_requires_refresh',
                                              'synthetic:T02-stale-report', state='stale', at=LATER)
        self.assertEqual(stale, expected)
        self.assertEqual(f.next_question(stale), question('Q-N02', clarification=True))
        blocked = assessment(source=T02_SOURCE, status='active_reported',
                             missing=[{'id': 'Q-N02', 'reason': 'stale'}], stage='I4')
        self.assertEqual(f.assessment(stale), blocked)
        shown = f.mark_asked(stale, 'Q-N02')
        expected['asked_question_ids'] = ['Q-N02']
        expected['facts']['Q-N02']['clarification_count'] = 1
        self.assertEqual(shown, expected)
        self.assertIsNone(f.next_question(shown))
        self.assertEqual(f.assessment(shown), blocked)
        self.assert_closed(shown)
        refreshed = f.record_fact(shown, 'Q-N02', 'fresh_current_proxy_mode_reported',
                                  source='synthetic:T02-explicit-refresh', observed_at=LATER)
        expected['facts']['Q-N02'] = envelope('Q-N02', 'fresh_current_proxy_mode_reported',
                                              'synthetic:T02-explicit-refresh', at=LATER, count=1)
        self.assertEqual(refreshed, expected)
        self.assertIsNone(f.next_question(refreshed))
        self.assertEqual(f.assessment(refreshed), assessment(source=T02_SOURCE, status='active_reported'))
        self.assert_closed(refreshed)
        self.assertEqual(complete, expected_t02_state())

    def test_T02_later_genuine_change_scope_asks_only_new_authorization_and_recovery(self):
        complete = t02_complete()
        changed = f.set_context(complete, change_planned=True, persistence_requested=True)
        expected = expected_t02_state()
        expected['context'].update(change_planned=True, persistence_requested=True)
        self.assertEqual(changed, expected)
        gaps = [{'id': q, 'reason': 'unasked'} for q in ('Q-Z03', 'Q-Z04', 'Q-Z05')]
        self.assertEqual(f.assessment(changed), assessment(source=T02_SOURCE, status='active_reported', missing=gaps, stage='I5'))
        trace = []
        values = {'Q-Z03': 'review_exact_diff_before_separate_action_approval',
                  'Q-Z04': 'private_backup_and_recovery_plan_not_executed',
                  'Q-Z05': 'yes_private_save_requested'}
        for qid in ('Q-Z03', 'Q-Z04', 'Q-Z05'):
            trace.append(f.next_question(changed))
            self.assertEqual(trace[-1], question(qid))
            changed = f.record_fact(f.mark_asked(changed, qid), qid, values[qid], source='synthetic:T02-later-scope', observed_at=LATER)
            expected['facts'][qid] = envelope(qid, values[qid], 'synthetic:T02-later-scope', at=LATER)
            expected['asked_question_ids'].append(qid)
            self.assertEqual(changed, expected)
            self.assert_closed(changed)
        trace.append(f.next_question(changed))
        self.assertEqual(trace, [question(q) for q in ('Q-Z03', 'Q-Z04', 'Q-Z05')] + [None])
        self.assertEqual(f.assessment(changed), assessment(source=T02_SOURCE, status='active_reported'))
        self.assertEqual(complete, expected_t02_state())

    def test_T02_later_actual_conflict_is_one_bounded_clarification_not_reintake(self):
        complete = t02_complete()
        conflict = f.record_fact(complete, 'Q-N02', 'proxy_mode_reports_disagree', state_name='conflict',
                                 source='synthetic:T02-new-conflict', observed_at=LATER)
        expected = expected_t02_state()
        expected['facts']['Q-N02'] = envelope('Q-N02', 'proxy_mode_reports_disagree', 'synthetic:T02-new-conflict', state='conflict', at=LATER)
        self.assertEqual(conflict, expected)
        self.assertEqual(f.next_question(conflict), question('Q-N02', clarification=True))
        self.assertEqual(f.assessment(conflict), assessment(source=T02_SOURCE, status='active_reported',
            missing=[{'id': 'Q-N02', 'reason': 'conflict'}], stage='I4'))
        shown = f.mark_asked(conflict, 'Q-N02')
        expected['asked_question_ids'] = ['Q-N02']
        expected['facts']['Q-N02']['clarification_count'] = 1
        self.assertEqual(shown, expected)
        self.assertIsNone(f.next_question(shown))
        self.assertIsNone(f.next_question(f.loads_state(json.dumps(shown))))
        resolved = f.record_fact(shown, 'Q-N02', 'browser_and_code_on_selected_mac_system_proxy_confirmed_by_user',
                                 source='synthetic:T02-conflict-resolution', observed_at=LATER)
        expected['facts']['Q-N02'] = envelope('Q-N02', 'browser_and_code_on_selected_mac_system_proxy_confirmed_by_user',
                                             'synthetic:T02-conflict-resolution', at=LATER, count=1)
        self.assertEqual(resolved, expected)
        self.assertIsNone(f.next_question(resolved))
        self.assertEqual(f.assessment(resolved), assessment(source=T02_SOURCE, status='active_reported'))
        self.assert_closed(resolved)
        self.assertEqual(complete, expected_t02_state())

    def test_T02_malformed_late_item_rejects_whole_complete_batch_atomically(self):
        # Q-Z05 sorts after the earlier routing/environment records, exercising
        # a late validation failure as well as preflight-envelope rejection.
        late_items = [
            {'question_id': 'Q-Z05', 'value': 'yes', 'source': 7},
            {'question_id': 'Q-Z05', 'value': 'yes', 'state': []},
            {'question_id': 'Q-Z05', 'value': 'yes', 'host_opt_in': True},
            {'question_id': 'Q-Z05', 'value': 'yes', 'contact_phase': 'PC2'},
            {'question_id': 'Q-Z05', 'value': 'yes', 'persistence_consent': {'private_save': True}},
            {'question_id': 'Q-C07', 'value': 'retired-field'},
            {'question_id': 'Q-OS01', 'value': 'windows'},
            {'question_id': 'Q-Z05', 'value': 'yes', 'subject_ref': 'other-device'},
        ]
        for late in late_items:
            with self.subTest(late=late):
                before, batch = t02_initial(), deepcopy(T02_INPUT) + [late]
                original, input_copy = deepcopy(before), deepcopy(batch)
                with self.assertRaises(f.InterviewError):
                    f.record_facts(before, batch, source=T02_SOURCE)
                self.assertEqual(before, original)
                self.assertEqual(batch, input_copy)
                self.assertEqual(before['facts'], {})
                self.assertEqual(f.next_question(before), question('Q-J01'))
                self.assert_closed(before)
                # An independent valid retry is usable and returns all facts.
                self.assertEqual(f.record_facts(before, deepcopy(T02_INPUT), source=T02_SOURCE), expected_t02_state())

    def test_T02_completeness_cannot_grant_native_contact_or_action_approval(self):
        complete = t02_complete()
        self.assertEqual(f.assessment(complete), assessment(source=T02_SOURCE, status='active_reported'))
        self.assert_closed(complete)
        binding = w.Binding(DEVICE, 'synthetic-user', 'synthetic-namespace', 'synthetic-profile', 'cfg-1', 'net-1', 'v1')
        requirements = w.Requirements(('network',), ('client-path',), ('authenticated-path',))
        scope = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
        client = replace(scope, operation=w.Operation.VERIFY, action='client-check', contact=w.Contact.CLAUDE)
        # Mock adapter eligibility is deliberately isolated from real validation.
        adapters = tuple(w.AdapterSupport(s, 'accepted', 'implemented', 'native_pass', 'synthetic-adapter-claim') for s in (scope, client))
        guard = w.WorkflowGuard(binding, requirements, adapters, clock=lambda: 20)
        ready = w.Readiness('complete', (), (), ())
        self.assertEqual(guard.snapshot(), {'phase': 'precontact', 'gate_state': 'closed',
            'observed_contact': 'not_measured', 'runtime_permission_restorable': False})
        action = w.Action(scope, binding, 'synthetic-plan', 10, 100)
        self.assertEqual(guard.evaluate(action, ready, (), 20), w.Decision(False, ('HOST_OS_PERMISSION_REQUIRED',), (scope, client)))
        # Even with a distinct simulated host permission assertion, the live
        # approval callback remains required; expert answers supply no callback.
        self.assertEqual(guard.evaluate(replace(action, permissions_verified=True), ready, (), 20),
                         w.Decision(False, ('HOST_APPROVAL_UNAVAILABLE',), (scope, client)))
        self.assertEqual(guard.transition(w.Phase.PC1, (client,), ready, (), 20),
                         w.Decision(False, ('EVIDENCE_REQUIRED:network',), (scope, client)))
        self.assertEqual(guard.snapshot(), {'phase': 'precontact', 'gate_state': 'closed',
            'observed_contact': 'not_measured', 'runtime_permission_restorable': False})
        self.assertEqual(complete, expected_t02_state())

    def test_original_rows_and_reviewed_guidance_preserve_whole_case_meaning(self):
        rows = (
            '| T01 | L0 准备订阅用于网页写作 | 先分首次/重订/已有订阅；问目标套餐和相关前提，本机默认建议；不询问账号归属，不推荐无关 VPS/企业开户/脚本 |',
            '| T02 | L4 直接提供完整环境 | 复用信息，不反复问基础问题；仍保留必要授权 |',
        )
        for row in rows:
            self.assertIn(row, SPEC_TEXT)
            self.assertIn(row + ' L+C |', TRACKER_TEXT)
        self.assertIn('Technical skill changes explanation depth only.', INTAKE_GUIDE)
        self.assertIn('An answer is never an action authorization', f.__doc__)
        self.assertIn('A browser-only task does not require Code/Desktop or firewall setup.', ROUTE_GUIDE)
        self.assertIn('解释深度可按新手逐步卡片、熟悉用户简表、专家差异清单调整，安全门槛不随等级变化。', ROUTE_GUIDE)
        self.assertIn('Q-C07 永久停用', INTAKE_GUIDE)
        self.assertIn('完整环境摘要可自动填入初访字段，只补缺口。', SPEC_TEXT)
        self.assertIn('不重复基础教程，也不跳过高风险确认', SPEC_TEXT)


def permission_replay():
    """Full actual workflow decisions from the independent authorization boundary."""
    binding = w.Binding(DEVICE, 'synthetic-user', 'synthetic-namespace', 'synthetic-profile', 'cfg-1', 'net-1', 'v1')
    requirements = w.Requirements(('network',), ('client-path',), ('authenticated-path',))
    scope = w.Scope('ENV-01', w.Operation.AUDIT, 'metadata', 'os', 'v1', 'native', 'macos')
    client = replace(scope, operation=w.Operation.VERIFY, action='client-check', contact=w.Contact.CLAUDE)
    adapters = tuple(w.AdapterSupport(s, 'accepted', 'implemented', 'native_pass', 'synthetic-adapter-claim')
                     for s in (scope, client))
    guard = w.WorkflowGuard(binding, requirements, adapters, clock=lambda: 20)
    ready = w.Readiness('complete', (), (), ())
    action = w.Action(scope, binding, 'synthetic-plan', 10, 100)
    before = guard.snapshot()
    decisions = {
        'no_host_permission': guard.evaluate(action, ready, (), 20),
        'no_live_approval_callback': guard.evaluate(replace(action, permissions_verified=True), ready, (), 20),
        'no_contact_evidence': guard.transition(w.Phase.PC1, (client,), ready, (), 20),
    }
    serial = {name: json.loads(json.dumps(asdict(decision), default=lambda item: item.value))
              for name, decision in decisions.items()}
    complete = t02_complete()
    persistence = {}
    for scope_name in ('private_save', 'export', 'public_export'):
        try:
            f.dumps_state(complete, scope=scope_name)
        except f.InterviewError as exc:
            persistence[scope_name] = {'allowed': False, 'error': str(exc)}
        else:
            raise AssertionError('Unapproved persistence unexpectedly succeeded')
    return {'adapter_evidence': 'synthetic declaration solely to isolate approval guards; no native acceptance',
            'before': before, 'decisions': serial, 'after': guard.snapshot(),
            'unapproved_persistence': persistence}


def replay():
    """Actual receipts only; this function never creates expected test outputs."""
    with no_external_io():
        result = {'evidence_scope': 'cloud_only normalized synthetic L trajectories; requires independent C review; native and live model not_run', 'T01': {}}
        for journey in ('first_subscription', 'returning_subscription', 'existing_subscriber'):
            terminal, trace = drive_t01(journey)
            result['T01'][journey] = {'host_context': 'L0: 网页写作，逐步说明；订阅阶段未提供，先分流',
                                     'initial': project(t01_initial()), 'full_question_trace_including_terminal': trace,
                                     'terminal_PC0': project(terminal)}
        before = t02_initial()
        complete = t02_complete()
        conflict = f.record_fact(complete, 'Q-N02', 'proxy_mode_reports_disagree', state_name='conflict',
                                 source='synthetic:T02-new-conflict', observed_at=LATER)
        result['T02'] = {'host_context': 'L4: 已有订阅，只处理所选本机完整环境；专家差异清单，所有动作另行授权',
                         'normalized_single_reply': deepcopy(T02_INPUT), 'before': project(before),
                         'after_complete_reply': project(complete), 'question_trace_including_terminal': [f.next_question(complete)],
                         'later_genuine_scope_gap': project(f.set_context(complete, change_planned=True, persistence_requested=True)),
                         'later_genuine_conflict': project(conflict),
                         'conflict_after_one_clarification': project(f.mark_asked(conflict, 'Q-N02'))}
        result['T02']['independent_authorization_boundary'] = permission_replay()
        return result


if __name__ == '__main__':
    if sys.argv[1:] == ['--replay']:
        print(json.dumps(replay(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        unittest.main()
