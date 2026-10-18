"""Original T82 full-clause normalized-host L replay; no native/UI claim.

The supported boundary is the compact guardian-interview/0.1 producer vocabulary
and its exact guardian-report/0.1 wrapper, plus explicit discard-only tombstones.
It is not a migration promise for arbitrary or invented historical state shapes.
Run with --replay for inspectable synthetic states, prompts and assessments.
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

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1])).resolve()
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
# Ordinary script imports resolve siblings exactly as the published host API does.
sys.path.insert(0, str(SCRIPTS))
import interview_flow as f
import interview_migration as m
import guardian

TIME = '2026-10-18T08:00:00Z'
SOURCE = 'synthetic:T82-current-reply'
DEVICE, ACCOUNT, TASK = 'legacy-device', 'legacy-account', 'legacy-task'
BASE = {
    'subscription_stage': 'existing_subscriber', 'current_task': 'environment',
    'os': 'macos', 'usage': 'web', 'account_status': 'active', 'route': 'local',
}
# This is an independently specified compatibility boundary, not runtime constants.
TOMBSTONES = {'Q-C07': 'old_owner_sentinel', 'account_ownership': 'old_org_sentinel',
              'account_control': 'old_control_sentinel', 'Q-C08': 'old_entitlement_sentinel'}
MAPPING = {'subscription_stage': 'Q-J01', 'current_task': 'Q-C11', 'os': 'Q-C02',
           'usage': 'Q-C01', 'account_status': 'Q-C04', 'route': 'Q-C05'}
ACCOUNT_IDS = {'Q-J01', 'Q-C04'}
PERMISSIONS = {'private_save': False, 'export': False, 'public_export': False}
G3 = {'status': 'blocked', 'reason': 'Interview answers are not specific action authorization; action and contact gates must be checked separately'}
# Full expected wording is authored here so renamed ownership questions cannot
# pass merely by avoiding a substring or retaining an otherwise permitted ID.
STEPS = [
    ('Q-J01', 'existing_subscriber', '这次是第一次准备订阅（包括只用过免费版）、以前订阅过目前无有效订阅准备重订、当前已有订阅，还是不确定？', 'core', 'I1'),
    ('Q-C11', 'environment', '老用户这次主要是续费/升级、调整使用方案，还是检查环境/解决问题？', 'core', 'I1'),
    ('Q-C02', 'macos', '这次用 Mac 还是 Windows？', 'core', 'I2'),
    ('Q-C01', 'web', '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？', 'core', 'I2'),
    ('Q-OS03', 'synthetic_version_reported', '如果 Mac：macOS 大致版本是什么？', 'os', 'I2'),
    ('Q-C03', 'no_suspension_reported', '以前 Claude 账号被明确停用/封禁过吗，还是只遇到报错？', 'core', 'I3'),
    ('Q-C04', 'active', '准备用的 Claude 账号注册了吗？已有账号现在能正常登录吗？', 'core', 'I3'),
    ('Q-C05', 'local', '用本机、虚拟机、VPS，还是先比较？本机默认建议。', 'core', 'I3'),
    ('Q-C06', 'official_login_reported', '已有账号通过什么方式登录/接入？不懂名称可描述界面。', 'core', 'I3'),
    ('Q-C09', 'region_reported_not_verified', '实际在哪个国家/地区使用？是否有跨地区安排？无需详细地址。', 'network', 'I4'),
    ('Q-N01', 'existing_network_reported', '当前是普通网络直接连接，还是使用代理/VPN/公司网络？软件名称知道就说。', 'network', 'I4'),
    ('Q-N02', 'browser_and_proxy_on_selected_device', '浏览器、Code、代理分别运行在哪里？使用系统代理、应用代理、TUN 还是不确定？', 'network', 'I4'),
    ('Q-N03', 'stable_network_intended', '网络是否常切换、自动换节点或跨地区？有计划长期固定使用的环境吗？', 'network', 'I4'),
    ('Q-N04', 'no_other_workspaces_reported', '还有手机、其他电脑或远程工作区同时/交替使用吗？各自用来做什么？', 'network', 'I4'),
    ('Q-N06', 'no_management_restrictions_reported', '是否受公司网络、证书、安全软件、代理策略或设备管理限制？', 'network', 'I4'),
    ('Q-L01', 'existing_browser_only_reported', '目标客户端安装了吗？用哪种方式安装、版本是什么？', 'local', 'I5'),
    ('Q-L04', 'web_only_no_local_project_access', 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？', 'local', 'I5'),
    ('Q-C12', 'preserve_all_existing_data', '哪些已有项目、历史、客户端或配置不能动？', 'protection', 'I5'),
    ('Q-Z01', 'plan_only', '这次只要讲解/计划，还是允许指定范围的只读检查？', 'protection', 'I5'),
    ('Q-C10', 'concise_checklist', '希望逐步指导，还是直接给检查项和命令？', 'protection', 'I5'),
]


def compact(extra=None):
    return {'schema_version': 'guardian-interview/0.1', 'answers': {**BASE, **(extra or {})}}


def migrate(obj):
    return m.migrate_legacy(obj, target_alias=DEVICE, account_alias=ACCOUNT, task_id=TASK)


@contextmanager
def offline():
    # Inputs/modules are already in memory; the tested operation cannot read,
    # write, contact a service or launch a process, even accidentally.
    with ExitStack() as stack:
        stack.enter_context(patch.object(f, '_now', return_value=TIME))
        for target in ('builtins.open', 'io.open', 'socket.socket', 'socket.create_connection',
                       'subprocess.run', 'subprocess.Popen', 'os.system'):
            stack.enter_context(patch(target, side_effect=AssertionError('Unexpected operation in offline T82 replay')))
        yield


def run_trace(obj):
    imported = migrate(obj)
    if imported['status'] != 'review_required':
        raise AssertionError(imported)
    state = imported['state']
    trace = []
    for qid, value, prompt, branch, stage in STEPS:
        actual = f.next_question(state)
        expected = {'id': qid, 'branch': branch, 'stage': stage, 'postcontact': False,
                    'prompt': prompt, 'clarification': qid in MAPPING.values(),
                    'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
                    'requires_action_authorization': False}
        if actual != expected:
            raise AssertionError({'expected': expected, 'actual': actual})
        before = f.assessment(state)
        state = f.mark_asked(state, qid)
        # This represents a new explicit reply, never automatic trust in import.
        state = f.record_fact(state, qid, value, source=SOURCE)
        trace.append({'question': actual, 'assessment_before': before,
                      'state_after': deepcopy(state), 'assessment_after': f.assessment(state)})
    return {'input': deepcopy(obj), 'import': imported, 'steps': trace,
            'final_state': state, 'final_question': f.next_question(state),
            'final_assessment': f.assessment(state)}


class LegacyRetirementAcceptance(unittest.TestCase):
    def assert_retirement_absent(self, state):
        self.assertTrue(set(state['facts']).isdisjoint(TOMBSTONES))
        self.assertTrue(set(state['asked_question_ids']).isdisjoint(TOMBSTONES))
        self.assertNotIn('Q-C07', [i['id'] for i in f.applicable_questions(state)])
        self.assertNotIn('Q-C07', [i['id'] for i in f.assessment(state)['G1']['unresolved_fields']])
        encoded = json.dumps(state, ensure_ascii=False)
        for sentinel in TOMBSTONES.values():
            self.assertNotIn(sentinel, encoded)
        self.assertNotIn('account_ownership', encoded)
        self.assertNotIn('account_control', encoded)

    def test_exact_supported_tombstones_drop_only_their_values(self):
        cases = [{}, *({name: value} for name, value in TOMBSTONES.items()), TOMBSTONES]
        with offline():
            clean = migrate(compact())
            for tombstones in cases:
                with self.subTest(tombstones=list(tombstones)):
                    source = compact(tombstones); original = deepcopy(source)
                    result = migrate(source)
                    self.assertEqual(result['status'], 'review_required')
                    self.assertEqual(result['discarded_fields'], sorted(tombstones))
                    self.assertEqual(result['state'], clean['state'])
                    self.assertEqual(result['review_only'], [])
                    self.assertEqual(result['review_hints'], [])
                    self.assertEqual(source, original)
                    self.assert_retirement_absent(result['state'])
                    for sentinel in TOMBSTONES.values():
                        self.assertNotIn(sentinel, json.dumps(result))

    def test_retained_fields_remain_stale_not_permission_or_ownership(self):
        with offline():
            result = migrate(compact(TOMBSTONES)); state = result['state']
            expected = {}
            for field, qid in MAPPING.items():
                expected[qid] = {
                    'value': BASE[field], 'state': 'stale',
                    'source': 'legacy:compact.answers.' + field,
                    'subject_ref': ACCOUNT if qid in ACCOUNT_IDS else DEVICE,
                    'observed_at': None, 'applies_when': 'only after target and fact reconfirmation',
                    'required_for': ['intake', 'plan'], 'sensitivity': 'low',
                    'clarification_count': 0,
                    'blocker_reason': 'Legacy confidence, freshness and subject binding are unverified',
                }
            self.assertEqual(state['facts'], expected)
            self.assertEqual(result['confidence'], 'unknown')
            self.assertEqual(result['binding'], 'unverified')
            self.assertEqual(state['current_subscription'], {'status': 'unknown', 'source': None, 'observed_at': None})
            self.assertEqual(state['payment_intent'], 'unresolved')
            self.assertEqual(state['context']['contact_phase'], 'PC0')
            self.assertEqual(state['context']['route_selection_basis'], 'default_proposal')
            self.assertEqual(state['persistence_consent'], PERMISSIONS)
            self.assertFalse(result['saved']); self.assertFalse(result['action_executed'])
            self.assertEqual(f.assessment(state)['G2']['status'], 'blocked')
            self.assertEqual(f.assessment(state)['G3'], G3)
            self.assertEqual(f.next_question(state)['id'], 'Q-J01')
            self.assertTrue(f.next_question(state)['clarification'])

    def test_complete_refresh_trace_never_renames_or_requires_retired_question(self):
        with offline():
            baseline = run_trace(compact())
            for extension in ({'Q-C07': TOMBSTONES['Q-C07']},
                              {'account_ownership': TOMBSTONES['account_ownership']},
                              {'account_control': TOMBSTONES['account_control']}, TOMBSTONES):
                with self.subTest(extension=list(extension)):
                    replay = run_trace(compact(extension))
                    self.assertEqual(replay['steps'], baseline['steps'])
                    self.assertEqual(replay['final_state'], baseline['final_state'])
                    self.assertIsNone(replay['final_question'])
                    assessment = replay['final_assessment']
                    self.assertEqual(assessment['stage'], 'I6')
                    self.assertEqual(assessment['G1'], {'status': 'complete', 'unresolved_fields': []})
                    self.assertEqual(assessment['G2'], {'status': 'pass', 'conditional_plan_only': False})
                    self.assertEqual(assessment['G3'], G3)
                    self.assertEqual(assessment['active_branches'], ['core', 'os', 'network', 'local', 'protection'])
                    final = replay['final_state']
                    self.assertEqual(final['asked_question_ids'], [x[0] for x in STEPS])
                    self.assertEqual(final['payment_intent'], 'none')
                    self.assertEqual(final['purchase_intent'], 'none')
                    self.assertEqual(final['persistence_consent'], PERMISSIONS)
                    self.assertEqual(final['context']['contact_phase'], 'PC0')
                    for step in replay['steps']:
                        self.assert_retirement_absent(step['state_after'])
                    for fact in final['facts'].values():
                        self.assertEqual(fact['state'], 'reported')
                        self.assertEqual(fact['source'], SOURCE)
                        self.assertEqual(fact['observed_at'], TIME)

    def test_exact_report_wrapper_discards_old_prompt_and_preserves_named_fields(self):
        # Produce a real wrapper, then add the documented compatibility fields to
        # its compact payload. The producer itself never emitted these fields.
        wrapper = guardian.interview(compact())
        wrapper['state']['answers'].update(TOMBSTONES)
        # Historical question IDs/text are advisory output, not imported facts.
        wrapper['question'] = {'id': 'Q-C07', 'field': 'route',
                               'text': '旧归属问句，不能恢复',
                               'choices': ['local', 'vm', 'vps', 'explain']}
        for with_policy in (False, True):
            source = deepcopy(wrapper)
            if not with_policy:
                source.pop('traffic_policy', None)
            with self.subTest(with_policy=with_policy), offline():
                result = migrate(source)
                self.assertEqual(result['status'], 'review_required')
                self.assertEqual(result['discarded_fields'], sorted(TOMBSTONES))
                self.assertEqual(result['state']['facts']['Q-C02']['source'], 'legacy:report.state.answers.os')
                self.assertNotIn('旧归属问句', json.dumps(result, ensure_ascii=False))
                replay = run_trace(source)
                self.assertEqual(replay['final_assessment']['G1']['status'], 'complete')
                self.assertEqual(replay['final_assessment']['G2']['status'], 'pass')
                self.assert_retirement_absent(replay['final_state'])

    def test_old_entitlement_never_populates_new_plan(self):
        with offline():
            no_target = migrate(compact({'Q-C08': 'old_entitlement_sentinel'}))
            self.assertNotIn('Q-C08', no_target['state']['facts'])
            explicit = migrate(compact({'Q-C08': 'old_entitlement_sentinel', 'target_plan': 'Pro'}))
            self.assertEqual(explicit['state']['facts']['Q-C08']['value'], 'Pro')
            self.assertEqual(explicit['state']['facts']['Q-C08']['state'], 'stale')
            self.assertEqual(explicit['state']['facts']['Q-C08']['source'], 'legacy:compact.answers.target_plan')
            self.assertEqual(explicit['state']['current_subscription']['status'], 'unknown')

    def test_clean_load_and_actual_resume_do_not_revive_retirement(self):
        with offline():
            state = run_trace(compact(TOMBSTONES))['final_state']
            # This is in-memory serialization only, with no save permission added.
            loaded = f.loads_state(json.dumps(state))
            self.assertEqual(loaded, state)
            self.assertIsNone(f.next_question(loaded))
            self.assertEqual(f.assessment(loaded)['G2']['status'], 'pass')
            resumed = f.resume_interview(loaded, resume_id='synthetic-interruption')
            prompt = f.resume_review_prompt(resumed)
            self.assertIsNotNone(prompt)
            self.assertNotIn('Q-C07', resumed['resume_review']['scope_keys'])
            self.assertNotIn('归属', json.dumps(prompt, ensure_ascii=False))
            self.assertNotIn('控制权', json.dumps(prompt, ensure_ascii=False))
            # Same-target association review is separate from account ownership.
            resumed = f.record_resume_review(resumed, resume_id='synthetic-interruption',
                                             response='unchanged', source='synthetic:T82-resume')
            self.assertEqual(f.assessment(resumed)['G2']['status'], 'pass')
            self.assertEqual(resumed['facts'], state['facts'])
            self.assertEqual(resumed['persistence_consent'], PERMISSIONS)
            self.assertEqual(f.assessment(resumed)['G3'], G3)
            self.assert_retirement_absent(resumed)

    def test_current_loader_and_mutators_reject_retired_fact_or_asked_id(self):
        with offline():
            state = migrate(compact())['state']; original = deepcopy(state)
            invalid = []
            for name in ('Q-C07', 'account_ownership', 'account_control'):
                bad = deepcopy(state); bad['facts'][name] = deepcopy(bad['facts']['Q-C02']); invalid.append(bad)
                bad = deepcopy(state); bad['asked_question_ids'].append(name); invalid.append(bad)
                with self.subTest(name=name):
                    with self.assertRaises(f.InterviewError): f.record_fact(state, name, 'old', source=SOURCE)
                    with self.assertRaises(f.InterviewError): f.mark_asked(state, name)
            for bad in invalid:
                with self.assertRaises(f.InterviewError): f.loads_state(json.dumps(bad))
            self.assertEqual(state, original)

    def test_unsupported_shapes_synonyms_and_invalid_values_fail_closed(self):
        unsupported = [
            {'Q-C07': 'mine'}, {'answers': {'Q-C07': 'mine'}},
            {'schema_version': 'future', 'answers': {'Q-C07': 'mine'}},
            {**compact(), 'account_ownership': 'mine'},
            compact({'owner': 'mine'}), compact({'account_owner': 'mine'}),
            compact({'accountOwnership': 'mine'}), compact({'账号归属': 'mine'}),
            compact({'Q-C07': None}), compact({'account_control': True}),
            compact({'account_ownership': {'value': 'mine'}}), compact({'Q-C07': ''}),
            compact({'Q-C07': 'x' * 81}), f.new_state(DEVICE, ACCOUNT),
        ]
        with offline():
            for obj in unsupported:
                with self.subTest(obj=obj):
                    result = migrate(obj)
                    self.assertEqual(result['status'], 'blocked')
                    self.assertIsNone(result['state'])
                    self.assertFalse(result['saved']); self.assertFalse(result['action_executed'])
            for name in TOMBSTONES:
                result = migrate(compact({name: 'password=synthetic_secret_sentinel'}))
                self.assertEqual(result['status'], 'blocked')
                self.assertIsNone(result['state'])
                self.assertNotIn('synthetic_secret_sentinel', json.dumps(result))

    def test_missing_binding_and_genuine_missing_fact_still_block(self):
        with offline():
            # Aliases provide bounded association labels, never owner authority.
            missing = m.migrate_legacy(compact(TOMBSTONES))
            self.assertEqual(missing['code'], 'FRESH_BINDING_REQUIRED')
            self.assertIsNone(missing['state'])
            final = run_trace(compact(TOMBSTONES))['final_state']
            for status in ('unknown', 'declined', 'deferred'):
                state = f.record_fact(final, 'Q-N01', state_name=status, source=SOURCE)
                actual = f.assessment(state)
                self.assertEqual(actual['G1'], {'status': 'partial', 'unresolved_fields': [{'id': 'Q-N01', 'reason': status}]})
                self.assertEqual(actual['G2']['status'], 'blocked')
                self.assertEqual(actual['G3'], G3)
                self.assertIsNone(f.next_question(state))
                self.assert_retirement_absent(state)


if __name__ == '__main__':
    if '--replay' in sys.argv:
        with offline():
            replay = run_trace(compact(TOMBSTONES))
        print(json.dumps(replay, ensure_ascii=False, indent=2))
    else:
        unittest.main()
