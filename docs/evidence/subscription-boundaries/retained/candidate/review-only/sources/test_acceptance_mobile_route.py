"""Original T49/T83 complete normalized-host replays; not live phone/payment tests.

All expectations are literal fixture requirements, not runtime-generated values.
No test text-file reads are used. Python 3.10-compatible stdlib APIs only.
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
SPEC = importlib.util.spec_from_file_location('mobile_route_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
TIME = '2026-10-18T09:10:00Z'
SOURCE = 'synthetic:mobile-route-current-report'
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
CONSENT = {'private_save': False, 'export': False, 'public_export': False}
PROMPTS = {
 'Q-P07': '后续准备怎样续费？需要说明账单查看与取消入口吗？',
 'Q-A01': 'A1 设备', 'Q-A02': 'A2 Apple 账户', 'Q-A03': 'A3 商店地区',
 'Q-A04': 'A4 App 与内购', 'Q-A05': 'A5 服务账户对应',
 'Q-A10': 'A10 后续续费与改区影响',
 'Q-G01': '有可用 Android 设备，并能使用官方 Google Play 与 Claude App 吗？',
 'Q-G02': '有能正常登录验证的 Google 账户吗？Play 国家/地区和付款选项是什么？',
 'Q-G03': '当前购买页能看到目标套餐和可用付款选项吗？',
 'Q-G04': '手机 App 登录的 Claude 是否为这次准备使用的目标账户？',
 'Q-S01': 'VPS 是 Claude 工作区，还是仅提供代理出口？',
 'Q-S02': '已有 VPS 还是新建？地区、系统和大致资源是什么？',
 'Q-S03': '是否能正常 SSH？有没有独立的控制台/救援入口？',
 'Q-S04': '上面有生产服务、数据库或未备份项目吗？',
 'Q-S05': '项目和数据能否存到远端？需依赖哪些本机应用或硬件？',
 'Q-S06': '服务器月费、流量和维护成本能接受多少？',
 'Q-S07': '希望终端、Remote-SSH 还是远程浏览器？如何备份和维护？',
 'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
 'Q-L04': 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？',
 'Q-C12': '哪些已有项目、历史、客户端或配置不能动？',
 'Q-Z01': '这次只要讲解/计划，还是允许指定范围的只读检查？',
 'Q-C10': '希望逐步指导，还是直接给检查项和命令？',
}
COMMON = {
 'Q-J01': 'first_subscription', 'Q-C02': 'macos',
 'Q-OS03': 'synthetic_controller_version_reported', 'Q-C01': 'code_environment_and_first_subscription_plan',
 'Q-C08': 'synthetic_selected_plan_not_current_catalog_verification',
 'Q-C03': 'no_suspension_reported', 'Q-C04': 'registered_reported',
 'Q-C06': 'official_login_category_reported', 'Q-C09': 'region_reported_not_verified',
 'Q-N01': 'existing_proxy_reported_not_tested',
 'Q-N03': 'stable_network_intended', 'Q-N04': 'payment_phone_separate_from_code_workspace',
 'Q-N06': 'no_management_restrictions_reported',
}
VALUES = {
 'Q-P07': 'same_channel_management_guidance_requested_no_renewal_action',
 'Q-A01': {'device_alias': 'phone-a', 'type': 'iphone', 'availability': 'reported'},
 'Q-A02': {'sign_in_and_verification': 'reported_available', 'credentials_collected': False},
 'Q-A03': {'storefront': 'synthetic_reported_storefront', 'source_kind': 'user_store_settings_report'},
 'Q-A04': {'official_app_entry': 'reported_visible', 'desired_plan_entry': 'reported_visible'},
 'Q-A05': {'service_account_alias': 'mobile-account', 'correspondence': 'reported_match'},
 'Q-A10': {'renewal': 'requested_explanation', 'changing_store_region': False},
 'Q-G01': {'device_alias': 'phone-g', 'type': 'android', 'play_available': 'reported',
            'claude_app_live_entry': 'not_run_before_contact'},
 'Q-G02': {'sign_in_and_verification': 'reported_available', 'play_country': 'synthetic_reported_storefront',
            'payment_category': 'reported_existing_store_method'},
 'Q-G03': {'official_app_entry': 'reported_visible', 'desired_plan_entry': 'reported_visible'},
 'Q-G04': {'service_account_alias': 'mobile-account', 'correspondence': 'reported_match'},
 'Q-S01': 'workspace_not_exit_only',
 'Q-S02': {'server_alias': 'workspace-a', 'lifecycle': 'existing', 'os': 'ubuntu_reported',
            'resources': 'reported_existing_resources', 'region': 'reported_not_verified'},
 'Q-S03': {'ssh': 'reported_available', 'independent_rescue': 'reported_available_not_tested'},
 'Q-S04': 'preserve_all_existing_services_and_projects',
 'Q-S05': 'remote_project_use_reported_no_data_copy_approved',
 'Q-S06': 'existing_server_budget_reported_no_new_purchase',
 'Q-S07': 'remote_ssh_planned_backup_and_maintenance_not_executed',
 'Q-L01': 'existing_local_code_metadata_reported_not_executed',
 'Q-L04': 'preserve_local_projects',
 'Q-C12': 'preserve_projects_configuration_and_control_channel',
 'Q-Z01': 'plan_only', 'Q-C10': 'concise_checklist',
}
PC0 = {'apple': ['Q-P07', 'Q-A01', 'Q-A02', 'Q-A03', 'Q-A10'],
       'google': ['Q-P07', 'Q-G01', 'Q-G02']}
LATER = {'apple': ['Q-A04', 'Q-A05'], 'google': ['Q-G03', 'Q-G04']}
ROUTES = {'local': ['Q-L01', 'Q-L04'], 'vps': ['Q-S01', 'Q-S02', 'Q-S03', 'Q-S04', 'Q-S05', 'Q-S06', 'Q-S07']}
TAIL = ['Q-C12', 'Q-Z01', 'Q-C10']


def offline():
    stack = ExitStack()
    stack.enter_context(patch.object(f, '_now', return_value=TIME))
    for target in ('builtins.open', 'io.open', 'os.open', 'socket.socket', 'socket.getaddrinfo', 'subprocess.Popen', 'os.system'):
        stack.enter_context(patch(target, side_effect=AssertionError('Pure interview attempted external I/O')))
    return stack


def start(channel, route='vps'):
    values = {**COMMON, 'Q-C05': route, 'Q-P06': channel,
        'Q-N02': {'code_runtime': 'workspace-a' if route == 'vps' else 'controller-a',
                  'controller': 'controller-a', 'payment_device': 'phone-a' if channel == 'apple' else 'phone-g'}}
    return f.record_facts(f.new_state('selected-runtime', 'mobile-account', task_id='mobile-task'),
        [{'question_id': q, 'value': v} for q, v in values.items()], source=SOURCE)


def expected_question(qid):
    if qid.startswith('Q-S'): branch, stage = 'vps', 'I5'
    elif qid.startswith('Q-L'): branch, stage = 'local', 'I5'
    elif qid in TAIL: branch, stage = 'protection', 'I5'
    else: branch, stage = 'payment', 'I4'
    return {'id': qid, 'branch': branch, 'stage': stage,
        'postcontact': qid in LATER['apple'] + LATER['google'], 'prompt': PROMPTS[qid],
        'clarification': False, 'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
        'requires_action_authorization': False}


def snap(state):
    return {'state': deepcopy(state), 'question': f.next_question(state),
        'applicable_questions': f.applicable_questions(state), 'assessment': f.assessment(state)}


def feed(state, sequence):
    trace = []
    for qid in sequence:
        actual = f.next_question(state)
        expected = expected_question(qid)
        if actual != expected:
            raise AssertionError({'actual': actual, 'expected': expected})
        trace.append(snap(state))
        state = f.mark_asked(state, qid)
        state = f.record_fact(state, qid, VALUES[qid], source=SOURCE, observed_at=TIME)
    trace.append(snap(state))
    return state, trace


def complete_pc0(channel, route='vps'):
    return feed(start(channel, route), PC0[channel] + ROUTES[route] + TAIL)


def after_separate_handoff(channel, route='vps'):
    state, _ = complete_pc0(channel, route)
    # Pure fixture for reports received after an already separately authorized
    # handoff. This metadata assignment performs/grants no real handoff or login.
    state = f.set_context(state, contact_phase='PC2')
    return feed(state, LATER[channel])


def replay():
    with offline():
        result = {'kind': 'actual_normalized_API_replay', 'model_dialogue_run': False,
            'synthetic_prior_context': COMMON, 'cases': {}}
        for route in ('vps', 'local'):
            for channel in ('apple', 'google'):
                before, pc0 = complete_pc0(channel, route)
                later, post = after_separate_handoff(channel, route)
                result['cases'][route + '_' + channel] = {'initial': snap(start(channel, route)),
                    'pc0': pc0, 'post_handoff_fixture': post,
                    'loaded_after': snap(f.loads_state(f.dumps_state(later, host_opt_in=True)))}
        return result


class MobileRouteAcceptanceTests(unittest.TestCase):
    def setUp(self):
        stack = offline()
        self.addCleanup(stack.close)

    def assert_boundary(self, state, route, channel, phase='PC0'):
        self.assertEqual(state['context']['route'], route)
        self.assertEqual(state['context']['route_selection_basis'], 'explicit_choice')
        self.assertEqual(state['context']['billing_channel'], channel)
        self.assertEqual(state['context']['contact_phase'], phase)
        self.assertEqual(f.assessment(state)['G3'], G3)
        self.assertEqual(state['persistence_consent'], CONSENT)
        self.assertEqual(state['current_subscription'], {'status': 'none_reported', 'source': SOURCE, 'observed_at': TIME})
        self.assertEqual(state['payment_intent'], 'new_subscription')
        self.assertEqual(f.assessment(state)['traffic_policy']['environment_pass'], False)
        self.assertEqual(f.assessment(state)['traffic_policy']['authorization'], 'none')
        questions = f.applicable_questions(state)
        self.assertFalse(any(q['id'].startswith('Q-W') for q in questions))
        self.assertTrue({'Q-P02', 'Q-A06', 'Q-C07'}.isdisjoint(q['id'] for q in questions))
        self.assertTrue({'Q-P02', 'Q-A06', 'Q-C07'}.isdisjoint(state['asked_question_ids']))

    def test_T49_both_mobile_channels_keep_complete_vps_path_without_web_cards(self):
        for channel in ('apple', 'google'):
            state, trace = complete_pc0(channel)
            self.assertEqual([row['question'] for row in trace],
                [expected_question(q) for q in PC0[channel] + ROUTES['vps'] + TAIL] + [None])
            for row in trace:
                self.assert_boundary(row['state'], 'vps', channel)
                route_ids = [q['id'] for q in row['applicable_questions'] if q['branch'] in ('local', 'vm', 'vps')]
                self.assertEqual(route_ids, ROUTES['vps'])
            phone_q = 'Q-A01' if channel == 'apple' else 'Q-G01'
            self.assertEqual(state['facts'][phone_q]['value'], VALUES[phone_q])
            self.assertEqual(state['facts']['Q-S02']['value'], VALUES['Q-S02'])
            self.assertNotEqual(state['facts'][phone_q]['value']['device_alias'], state['facts']['Q-S02']['value']['server_alias'])
            self.assertEqual(state['facts']['Q-N02']['value']['code_runtime'], 'workspace-a')
            self.assertEqual(state['facts']['Q-N02']['value']['controller'], 'controller-a')
            self.assertEqual(state['facts']['Q-N02']['value']['payment_device'], state['facts'][phone_q]['value']['device_alias'])
            self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T49_changing_mobile_channel_preserves_existing_workspace_and_no_web_fallback(self):
        for original, other in (('apple', 'google'), ('google', 'apple')):
            state, _ = complete_pc0(original)
            switched = f.record_fact(state, 'Q-P06', other, source='synthetic:explicit-channel-change', observed_at=TIME)
            self.assert_boundary(switched, 'vps', other)
            for q in ROUTES['vps'] + ['Q-C05', 'Q-N02']:
                self.assertEqual(switched['facts'][q], state['facts'][q])
            self.assertEqual(f.next_question(switched), expected_question('Q-G01' if other == 'google' else 'Q-A01'))
            # Existing N02 remains a reported old layout; a channel choice cannot
            # fabricate a new phone binding. Host obtains any changed layout.
            self.assertEqual(switched['facts']['Q-P06']['value'], other)
            self.assertEqual(state['context']['billing_channel'], original)

    def test_T83_device_store_and_target_entry_are_distinct_requirements(self):
        for route in ('local', 'vps'):
            for channel in ('apple', 'google'):
                state, _ = complete_pc0(channel, route)
                self.assert_boundary(state, route, channel)
                self.assertIsNone(f.next_question(state))
                self.assertEqual(f.assessment(state)['G1'], {'status': 'partial', 'unresolved_fields':
                    [{'id': q, 'reason': 'requires_contact_gate'} for q in LATER[channel]]})
                self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
                for q in LATER[channel]:
                    self.assertNotIn(q, state['facts'])
                    self.assertNotIn(q, state['asked_question_ids'])
                stored = ['Q-A01', 'Q-A02', 'Q-A03'] if channel == 'apple' else ['Q-G01', 'Q-G02']
                for q in stored:
                    self.assertEqual(state['facts'][q]['value'], VALUES[q])
                if channel == 'google':
                    self.assertEqual(state['facts']['Q-G01']['value']['claude_app_live_entry'], 'not_run_before_contact')

    def test_T83_full_post_handoff_fixture_asks_match_not_old_subscription(self):
        for route in ('local', 'vps'):
            for channel in ('apple', 'google'):
                state, trace = after_separate_handoff(channel, route)
                self.assertEqual([row['question'] for row in trace], [expected_question(q) for q in LATER[channel]] + [None])
                for row in trace:
                    self.assert_boundary(row['state'], route, channel, 'PC2')
                self.assertEqual(f.assessment(state)['G1'], {'status': 'complete', 'unresolved_fields': []})
                self.assertEqual(f.assessment(state)['G2'], {'status': 'pass', 'conditional_plan_only': False})
                q = 'Q-A05' if channel == 'apple' else 'Q-G04'
                self.assertEqual(state['facts'][q]['value']['service_account_alias'], 'mobile-account')
                self.assertEqual(state['facts'][q]['state'], 'reported')
                self.assertEqual(state['facts'][q]['source'], SOURCE)
                self.assertEqual(state['facts'][q]['observed_at'], TIME)
                self.assertNotIn('Q-G05', state['asked_question_ids'])
                self.assertEqual(f.loads_state(f.dumps_state(state, host_opt_in=True)), state)

    def test_T83_unknown_declined_or_deferred_store_prerequisite_remains_visible(self):
        for channel, qid in (('apple', 'Q-A02'), ('apple', 'Q-A03'), ('google', 'Q-G02')):
            completed, _ = after_separate_handoff(channel)
            for status in ('unknown', 'declined', 'deferred'):
                state = f.record_fact(completed, qid, state_name=status, source='synthetic:prerequisite-unavailable')
                self.assertEqual(f.assessment(state)['G1'], {'status': 'partial', 'unresolved_fields': [{'id': qid, 'reason': status}]})
                self.assertEqual(f.assessment(state)['G2'], {'status': 'blocked', 'conditional_plan_only': True})
                self.assertIsNone(f.next_question(state))
                self.assert_boundary(state, 'vps', channel, 'PC2')

    def test_T83_old_orders_activate_only_for_explicit_actual_conflict(self):
        for channel in ('apple', 'google'):
            state, _ = complete_pc0(channel)
            self.assert_boundary(state, 'vps', channel)
            conflict = f.set_context(state, subscription_conflict=True)
            ids = [q['id'] for q in f.applicable_questions(conflict)]
            self.assertIn('Q-P02', ids)
            self.assertEqual('Q-A06' in ids, channel == 'apple')
            self.assertEqual(conflict['context']['route'], 'vps')
            self.assertEqual(f.assessment(conflict)['G3'], G3)
            self.assertNotIn('Q-P02', state['facts'])
            self.assertFalse(state['context']['subscription_conflict'])


if __name__ == '__main__':
    if '--replay' in sys.argv:
        print(json.dumps(replay(), ensure_ascii=False, sort_keys=True, indent=2))
    else:
        unittest.main()
