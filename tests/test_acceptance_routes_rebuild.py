"""Original T19/T20/T21/T24 offline replays, not model or native certification.

Expected outputs are authored here, independently of interview_flow constants.
The fixture contains normalized synthetic user facts, not an NLP transcript test.
T24 now has normative explicit-resume traces; original acceptance still requires C review.
Run this file with --replay to print the concrete actual projections as JSON.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'route_rebuild_interview_flow',
    ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
flow = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(flow)
FIXTURE = json.loads((ROOT / 'tests/fixtures/acceptance-routes-rebuild.json').read_text(encoding='utf-8'))
TIME = '2026-10-18T04:00:00Z'
REVIEW_TIME = '2026-10-18T04:30:00Z'
SOURCE = 'synthetic:route-case'
G3_REASON = ('Interview answers are not specific action authorization; '
             'action and contact gates must be checked separately')

# Full user-facing strings are pinned, rather than checked for selected words.
PROMPTS = {
    'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
    'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
    'Q-V01': '已有虚拟机还是准备新建？使用什么虚拟化软件？',
    'Q-V02': '宿主与客机各是什么系统/架构？',
    'Q-V03': '可供 VM 使用的内存/磁盘大约多少？已有项目需要保留吗？',
    'Q-V04': '虚拟机怎样联网，代理在宿主还是客机？',
    'Q-V05': '需要共享哪些目录、剪贴板或工具？是否已有账号凭据挂载？',
    'Q-V06': '有没有快照/备份和可用的恢复方式？',
    'Q-S01': 'VPS 是 Claude 工作区，还是仅提供代理出口？',
    'Q-S02': '已有 VPS 还是新建？地区、系统和大致资源是什么？',
    'Q-S03': '是否能正常 SSH？有没有独立的控制台/救援入口？',
    'Q-S04': '上面有生产服务、数据库或未备份项目吗？',
    'Q-S05': '项目和数据能否存到远端？需依赖哪些本机应用或硬件？',
    'Q-S06': '服务器月费、流量和维护成本能接受多少？',
    'Q-S07': '希望终端、Remote-SSH 还是远程浏览器？如何备份和维护？',
}
ROUTE_IDS = {
    'local': ['Q-L01', 'Q-L04'],
    'vm': ['Q-V01', 'Q-V02', 'Q-V03', 'Q-V04', 'Q-V05', 'Q-V06'],
    'vps': ['Q-S01', 'Q-S02', 'Q-S03', 'Q-S04', 'Q-S05', 'Q-S06', 'Q-S07'],
}


def question(qid, branch, *, clarification=False):
    if qid is None:
        return None
    return {'id': qid, 'branch': branch,
            'stage': 'I3' if qid == 'Q-C05' else 'I5',
            'postcontact': False, 'prompt': PROMPTS[qid],
            'clarification': clarification,
            'allowed_outcomes': ['reported', 'unknown', 'declined', 'deferred'],
            'requires_action_authorization': False}


def expected(*, route='local', basis='default_proposal', next_id='Q-C05',
             next_branch='core', unresolved=None, status='partial', clarification=False):
    if unresolved is None:
        unresolved = [{'id': 'Q-C05', 'reason': 'unasked'}]
    confirmed = basis != 'default_proposal'
    return {
        'task_id': 'route-task', 'target_alias': 'route-device',
        'account_alias': 'route-account',
        'route': route, 'route_selection_basis': basis,
        'route_question_ids': ROUTE_IDS[route] if confirmed else [],
        'next_question': question(next_id, next_branch, clarification=clarification),
        'assessment': {
            'stage': ('I3' if not confirmed else 'I5') if unresolved else 'I6',
            'G1': {'status': status, 'unresolved_fields': unresolved},
            'G2': {'status': 'pass' if status == 'complete' else 'blocked',
                   'conditional_plan_only': status != 'complete'},
            'G3': {'status': 'blocked', 'reason': G3_REASON},
            'active_branches': ['core', 'os', 'network'] + ([route] if confirmed else []) + ['protection'],
            'deferred_branches': [],
            'route_confirmation': 'confirmed' if confirmed else 'unconfirmed',
            'current_subscription': {'status': 'active_reported', 'source': SOURCE, 'observed_at': TIME},
        },
        'contact_phase': 'PC0',
        'persistence_consent': {'private_save': False, 'export': False, 'public_export': False},
    }


def project(state):
    """Explicit assertion boundary; includes full question and full assessment."""
    result = {
        'task_id': state['task_id'], 'target_alias': state['target_alias'],
        'account_alias': state['account_alias'],
        'route': state['context']['route'],
        'route_selection_basis': state['context']['route_selection_basis'],
        'route_question_ids': [q['id'] for q in flow.applicable_questions(state)
                               if q['branch'] in {'local', 'vm', 'vps'}],
        'next_question': flow.next_question(state),
        'assessment': flow.assessment(state),
        'contact_phase': state['context']['contact_phase'],
        'persistence_consent': deepcopy(state['persistence_consent']),
    }
    if 'resume_review' in state:
        result['resume_prompt'] = flow.resume_review_prompt(state)
    return result


def base():
    state = flow.new_state('route-device', 'route-account', task_id='route-task')
    state = flow.set_context(state, task='environment')
    return flow.record_facts(state, FIXTURE['common_answers'], source=SOURCE)


def choose(route):
    return flow.record_fact(base(), 'Q-C05', route, source=SOURCE, observed_at=TIME)


def answer(state, item):
    return flow.record_fact(state, item['question_id'], item['value'],
                            source=SOURCE, observed_at=TIME)


def complete(route):
    state = choose(route)
    for item in FIXTURE['route_answers'][route]:
        state = answer(state, item)
    return state


def resumed(route):
    state = complete(route)
    paused = flow.set_context(state, paused=True)
    saved = flow.dumps_state(paused, host_opt_in=True)
    loaded = flow.loads_state(saved)
    return state, paused, loaded, flow.resume_interview(loaded, resume_id='route-resume')


def review(state, response='unchanged', changed_keys=()):
    return flow.record_resume_review(state, resume_id='route-resume', response=response,
                                      changed_keys=changed_keys, source='synthetic:current-review',
                                      reported_at=REVIEW_TIME)


def expected_resumed(route, *, response=None, changed_key=None):
    scope = ['Q-C02', 'Q-C04', 'Q-C06', 'Q-C09', 'Q-N01', 'Q-N02', 'Q-N03', 'Q-N04', 'Q-N06', 'Q-OS03'] + ROUTE_IDS[route]
    result = expected(route=route, basis='explicit_choice', next_id=changed_key, next_branch=route,
                      unresolved=[{'id': changed_key, 'reason': 'stale'}] if changed_key else [],
                      status='partial' if changed_key else 'complete', clarification=bool(changed_key))
    result['assessment']['resume_review'] = {
        'event_id': 'route-resume', 'status': 'pending' if response is None else 'reviewed',
        'response': response, 'scope_keys': scope,
        'changed_keys': [changed_key] if changed_key else [],
        'reported_at': None if response is None else REVIEW_TIME}
    result['resume_prompt'] = None
    if response is None:
        result['assessment']['G2'] = {'status': 'blocked', 'conditional_plan_only': True,
                                      'reason': 'resume_review_required'}
        name, topic = ('虚拟机', '虚拟机资源、网络、共享和恢复条件') if route == 'vm' else ('VPS', '服务器、SSH/救援、数据、费用和使用方式')
        result['resume_prompt'] = {
            'kind': 'resume_review', 'event_id': 'route-resume', 'scope_keys': scope,
            'prompt': f'继续上次的{name}任务：还是原来的目标设备和账号吗；上次记录的系统/版本、语言和时间设置、网络/代理及此前测试、{topic}、账号登录情况、使用地区/跨地区安排（无需详细地址）（含本路线已记录但尚未展开的条件项）有没有变化？可以说没变、具体变化、不确定、暂不回答或稍后再说；换了目标请先说明。',
            'allowed_outcomes': ['unchanged', 'changed', 'unknown', 'declined', 'deferred', 'target_changed'],
            'requires_action_authorization': False}
    return result


def replay():
    """Actual outputs for review; never used to generate expected test values."""
    with patch.object(flow, '_now', return_value=TIME):
        initial = base()
        shown = flow.mark_asked(initial, 'Q-C05')
        no_answer = flow.record_fact(initial, 'Q-C05', state_name='unknown', source=SOURCE, observed_at=TIME)
        accepted = flow.record_fact(initial, 'Q-C05', 'accepted_default', source=SOURCE, observed_at=TIME)
        result = {'T19': {'initial': project(initial), 'shown_without_answer': project(shown),
                          'unknown_answer': project(no_answer), 'accepted_local': project(accepted)}}
        vm = choose('vm')
        vm_questions = []
        for item in FIXTURE['route_answers']['vm']:
            vm_questions.append(flow.next_question(vm))
            vm = answer(vm, item)
        result['T20'] = {'first': project(choose('vm')), 'question_trace': vm_questions,
                         'after_route_answers': project(vm)}
        result['T21'] = {}
        for lifecycle in ('existing', 'new'):
            vps = choose('vps')
            vps = answer(vps, FIXTURE['route_answers']['vps'][0])
            before_server = project(vps)
            vps = flow.record_fact(vps, 'Q-S02', FIXTURE['server_variants'][lifecycle],
                                   source=SOURCE, observed_at=TIME)
            result['T21'][lifecycle] = {'before_server_answer': before_server,
                                       'after_server_answer': project(vps),
                                       'server_fact': deepcopy(vps['facts']['Q-S02'])}
        result['T24'] = {}
        for route, qid in (('vm', 'Q-V04'), ('vps', 'Q-S03')):
            _, paused, loaded, pending = resumed(route)
            unchanged = review(pending)
            changed = review(pending, 'changed', [qid])
            result['T24'][route] = {'paused': project(paused), 'loaded': project(loaded),
                                    'explicit_resume_pending': project(pending),
                                    'current_unchanged_review': project(unchanged),
                                    'current_changed_review': project(changed),
                                    'changed_fact': deepcopy(changed['facts'][qid])}
        return result


class RouteAcceptanceRebuildTests(unittest.TestCase):
    def setUp(self):
        self.resources = ExitStack()
        self.addCleanup(self.resources.close)
        self.resources.enter_context(patch.object(flow, '_now', return_value=TIME))
        # This is intentionally an in-memory pure-function harness, not a fake native adapter.
        for target in ('builtins.open', 'socket.socket', 'subprocess.Popen', 'os.system'):
            self.resources.enter_context(patch(target, side_effect=AssertionError('Offline replay attempted external I/O')))

    def test_T19_unselected_local_is_proposal_and_emits_exact_choice(self):
        state = base()
        self.assertEqual(project(state), expected())
        self.assertNotIn('Q-C05', state['facts'])
        shown = flow.mark_asked(state, 'Q-C05')
        self.assertEqual(project(shown), expected(next_id=None))
        unknown = flow.record_fact(state, 'Q-C05', state_name='unknown', source=SOURCE, observed_at=TIME)
        self.assertEqual(project(unknown), expected(next_id=None,
                         unresolved=[{'id': 'Q-C05', 'reason': 'unknown'}]))
        self.assertEqual(project(state), expected())  # Rendering/updating did not mutate the input.

    def test_T19_explicit_acceptance_confirms_only_local_and_not_permissions(self):
        accepted = flow.record_fact(base(), 'Q-C05', 'accepted_default', source=SOURCE, observed_at=TIME)
        self.assertEqual(project(accepted), expected(basis='accepted_default', next_id='Q-L01',
                         next_branch='local', unresolved=[{'id': qid, 'reason': 'unasked'} for qid in ROUTE_IDS['local']]))
        self.assertEqual(accepted['facts']['Q-C05']['value'], 'accepted_default')
        self.assertEqual(accepted['facts']['Q-C05']['state'], 'reported')

    def test_T20_L0_vm_has_independent_exact_six_question_sequence(self):
        state = choose('vm')
        self.assertEqual(state['facts']['Q-C10']['value'], 'step_by_step_beginner')
        actual_questions = []
        for index, item in enumerate(FIXTURE['route_answers']['vm']):
            unresolved = [{'id': qid, 'reason': 'unasked'} for qid in ROUTE_IDS['vm'][index:]]
            self.assertEqual(project(state), expected(route='vm', basis='explicit_choice',
                             next_id=item['question_id'], next_branch='vm', unresolved=unresolved))
            actual_questions.append(flow.next_question(state))
            state = answer(state, item)
        self.assertEqual(actual_questions, [question(qid, 'vm') for qid in ROUTE_IDS['vm']])
        self.assertEqual(project(state), expected(route='vm', basis='explicit_choice', next_id=None,
                         next_branch='vm', unresolved=[], status='complete'))
        self.assertEqual(state['facts']['Q-V01']['value'], {'lifecycle': 'new', 'hypervisor': 'not_selected'})
        self.assertEqual(state['facts']['Q-C05']['value'], 'vm')
        self.assertEqual(state['facts']['Q-C10']['value'], 'step_by_step_beginner')

    def test_T21_existing_and_new_vps_preserve_choice_and_distinct_server_facts(self):
        for lifecycle in ('existing', 'new'):
            with self.subTest(lifecycle=lifecycle):
                state = choose('vps')
                self.assertEqual(flow.next_question(state), question('Q-S01', 'vps'))
                state = answer(state, FIXTURE['route_answers']['vps'][0])
                self.assertEqual(flow.next_question(state), question('Q-S02', 'vps'))
                value = FIXTURE['server_variants'][lifecycle]
                state = flow.record_fact(state, 'Q-S02', value, source=SOURCE, observed_at=TIME)
                self.assertEqual(project(state), expected(route='vps', basis='explicit_choice',
                                 next_id='Q-S03', next_branch='vps',
                                 unresolved=[{'id': qid, 'reason': 'unasked'} for qid in ROUTE_IDS['vps'][2:]]))
                self.assertEqual(state['facts']['Q-S02'], {
                    'value': value, 'state': 'reported', 'source': SOURCE,
                    'subject_ref': 'route-device', 'observed_at': TIME,
                    'applies_when': 'current task and target', 'required_for': ['intake', 'plan'],
                    'sensitivity': 'low', 'clarification_count': 0, 'blocker_reason': None})
                for item in FIXTURE['route_answers']['vps'][2:]:
                    self.assertEqual(flow.next_question(state), question(item['question_id'], 'vps'))
                    state = answer(state, item)
                self.assertEqual(project(state), expected(route='vps', basis='explicit_choice',
                                 next_id=None, next_branch='vps', unresolved=[], status='complete'))
                self.assertEqual(state['facts']['Q-S02']['value']['lifecycle'], lifecycle)
                before = deepcopy(state)
                with self.assertRaisesRegex(flow.InterviewError, 'No current local default proposal to accept'):
                    flow.record_fact(state, 'Q-C05', 'accepted_default', source=SOURCE, observed_at=TIME)
                self.assertEqual(state, before)

    def test_T24_same_task_retains_route_and_requires_exact_environment_review(self):
        for route in ('vm', 'vps'):
            with self.subTest(route=route):
                before, paused, loaded, pending = resumed(route)
                self.assertEqual(project(paused), expected(route=route, basis='explicit_choice',
                                 next_id=None, next_branch=route, unresolved=[], status='paused'))
                self.assertEqual(loaded, paused)
                with self.assertRaisesRegex(flow.InterviewError, 'Use resume_interview'):
                    flow.set_context(loaded, paused=False)
                self.assertEqual(pending['facts'], before['facts'])
                self.assertEqual(project(pending), expected_resumed(route))
                unchanged = review(pending)
                self.assertEqual(project(unchanged), expected_resumed(route, response='unchanged'))
                self.assertEqual(unchanged['facts'], before['facts'])
                self.assertEqual(flow.resume_interview(unchanged, resume_id='route-resume'), unchanged)

    def test_T24_current_change_invalidates_only_relevant_vm_or_vps_fact(self):
        for route, qid in (('vm', 'Q-V04'), ('vps', 'Q-S03')):
            with self.subTest(route=route):
                before, _, _, pending = resumed(route)
                changed = review(pending, 'changed', [qid])
                self.assertEqual(project(changed), expected_resumed(route, response='changed', changed_key=qid))
                self.assertEqual({key: value for key, value in changed['facts'].items() if key != qid},
                                 {key: value for key, value in before['facts'].items() if key != qid})
                self.assertEqual(changed['facts'][qid], {**before['facts'][qid], 'state': 'stale',
                                 'blocker_reason': 'Reported change since interview interruption', 'clarification_count': 0})
                self.assertEqual(changed['facts']['Q-C05']['value'], route)


if __name__ == '__main__':
    if sys.argv[1:] == ['--replay']:
        print(json.dumps(replay(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        unittest.main()
