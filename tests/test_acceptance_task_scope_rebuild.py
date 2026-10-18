"""T34/T78/T43/T48: normalized offline whole-case trajectories + reviewed guidance.

No arbitrary-language classifier, native device observation or execution authority
is claimed. Expected prompts are handwritten or reused from frozen intake fixtures.
"""
from contextlib import ExitStack
from copy import deepcopy
import itertools
import json
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import test_acceptance_intake_rebuild as prior

f = prior.f
ROOT = Path(__file__).resolve().parents[1]
TIME = '2026-10-18T06:15:00Z'
SOURCE = 'synthetic:task-scope'
G3 = prior.G3
PERMISSIONS = prior.PERMISSIONS
PROMPTS = {
 'Q-J02': '你说用过/是老手：现在还有有效订阅，还是准备开通/重新开通？',
 'Q-C11': '老用户这次主要是续费/升级、调整使用方案，还是检查环境/解决问题？',
 'Q-H01': '被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？',
 'Q-H02': '最近一次与本次任务有关的事件，大约何时发生？目前恢复了吗？',
 'Q-H03': '当时显示什么错误/通知？有可脱敏的原文或局部截图吗？',
 'Q-H04': '出现问题前正在注册、登录、订阅、更新客户端还是执行任务？',
 'Q-H05': '当时在什么设备/环境、通过什么客户端和计费渠道使用？',
 'Q-H06': '是否正在申诉、身份核验或处理退款？有没有官方回复要求你完成的事项？',
 'Q-H07': '之后做过哪些退出、重装、清理或配置修改？有需要保留/导出的数据吗？',
}
EXPOSURE_PROMPT = '可能泄露的是哪类凭据、涉及哪个服务或客户端？只说类别和对象，不要发送密码、令牌或密钥内容。'
EXPOSURE_REMAINING = {
 'Q-H03':'有什么迹象提示凭据可能泄露？只提供脱敏后的提示或现象，不要贴原始秘密或完整日志。',
 'Q-H04':'发现泄露前做过什么相关操作，或把信息发到了哪类位置？不要贴具体秘密或含密链接。',
 'Q-H05':'哪些设备、客户端或自动任务可能使用这类凭据？只列受影响对象，不读取凭据内容。',
 'Q-H06':'是否已经通过官方渠道处理这次泄露，或收到需要完成的保护指示？不知道可以说明。',
}
FOUR = [{'question_id': q, 'value': v} for q,v in (
    ('Q-J01','existing_subscriber'),('Q-C11','environment'),('Q-C02','macos'),('Q-C05','local'))]
ENV_SEQUENCE = ['Q-C01','Q-OS03','Q-C03','Q-C04','Q-C06'] + prior.NETWORK + ['Q-L01','Q-L04'] + ['Q-C12','Q-Z01','Q-C10']
ROUTE_REST = ['Q-C06'] + prior.NETWORK + prior.CHANNEL_CHOICE + prior.CHANNEL_PC0['web'] + ['Q-C12','Q-Z01','Q-C10']


def expected_policy():
    # Independently authored current product requirement; old assertions remain exact.
    return {
        'schema_version': 'guardian-traffic-policy/0.1',
        'requirement_id': 'PRODUCT-IPV4-20261018', 'effective_from': '2026-10-18',
        'policy': 'IPv4_ONLY', 'applies_to': 'claude_target_application_traffic',
        'ipv6_fallback': 'forbidden', 'proxy_outer_transport': 'preserve_existing_independently',
        'control_channels': 'preserve', 'other_applications': 'unchanged',
        'enforcement_status': 'unknown', 'compliance': 'not_established',
        'environment_pass': False, 'apply_supported': False, 'authorization': 'none',
    }


def new():
    return f.new_state('scope-device','scope-account',task_id='scope-task')


def question(qid, *, exposure=False):
    if qid not in PROMPTS:
        return prior.expected_question(qid)
    incident = qid.startswith('Q-H')
    return {'id':qid, 'branch':'incident' if incident else 'core',
            'stage':'I0' if incident else 'I1', 'postcontact':False,
            'prompt':(EXPOSURE_PROMPT if qid=='Q-H01' else EXPOSURE_REMAINING.get(qid,PROMPTS[qid])) if exposure else PROMPTS[qid],
            'clarification':False, 'allowed_outcomes':['reported','unknown','declined','deferred'],
            'requires_action_authorization':False}


def snapshot(state):
    return {'state':deepcopy(state), 'assessment':f.assessment(state),
            'next_question':f.next_question(state), 'applicable_questions':f.applicable_questions(state)}


def expected_urgent(first_missing=1):
    return {'traffic_policy': expected_policy(), 'stage':'I0' if first_missing<=7 else 'I6',
        'G1':{'status':'emergency_deferred','unresolved_fields':[
            {'id':f'Q-H{i:02d}','reason':'unasked'} for i in range(first_missing,8)]},
        'G2':{'status':'blocked','conditional_plan_only':True},'G3':G3,
        'active_branches':['incident'],'deferred_branches':[],
        'route_confirmation':'confirmed',
        'current_subscription':{'status':'none_reported','source':SOURCE,'observed_at':TIME},
        'emergency_deferred_branches':['payment','local','protection']}


def feed(state, sequence):
    trace=[]
    for qid in sequence:
        actual=f.next_question(state)
        assert actual==question(qid),(actual,question(qid))
        trace.append(deepcopy(actual))
        state=f.mark_asked(state,qid)
        state=f.record_fact(state,qid,'web' if qid=='Q-P06' else prior.VALUES[qid],source=SOURCE,observed_at=TIME)
    return state,trace


def at_route():
    state=f.record_fact(new(),'Q-J01','first_subscription',source=SOURCE,observed_at=TIME)
    return feed(state,['Q-C02','Q-C01','Q-OS03','Q-C08','Q-C03','Q-C04'])[0]


def at_payment():
    state=f.record_fact(at_route(),'Q-C05','local',source=SOURCE,observed_at=TIME)
    return feed(state,['Q-C06']+prior.NETWORK)[0]


class TaskScopeAcceptanceTests(unittest.TestCase):
    def setUp(self):
        stack=ExitStack();self.addCleanup(stack.close)
        stack.enter_context(patch.object(f,'_now',return_value=TIME))
        for target in ('builtins.open','io.open','os.open','socket.socket','subprocess.Popen','os.system'):
            stack.enter_context(patch(target,side_effect=AssertionError('Offline case attempted I/O')))

    def assert_closed(self,state):
        self.assertEqual(f.assessment(state)['G3'],G3)
        self.assertEqual(state['context']['contact_phase'],'PC0')
        self.assertEqual(state['persistence_consent'],PERMISSIONS)

    def test_T34_unanswered_shown_skipped_and_compare_keep_only_conditional_plan(self):
        original=at_route()
        self.assertEqual(f.next_question(original),question('Q-C05'))
        self.assertEqual(f.next_question(original),question('Q-C05'))
        self.assertNotIn('Q-C05',original['facts'])
        for outcome in ('unanswered','unknown','declined','deferred','compare'):
            state=f.mark_asked(original,'Q-C05')
            if outcome!='unanswered':
                state=f.record_fact(state,'Q-C05','compare' if outcome=='compare' else None,
                                    state_name='reported' if outcome=='compare' else outcome,
                                    source=SOURCE,observed_at=TIME)
            self.assertEqual(f.next_question(state),question('Q-C06'))
            state,trace=feed(state,ROUTE_REST)
            self.assertIsNone(f.next_question(state))
            expected={'traffic_policy': expected_policy(), 'stage':'I3','G1':{'status':'partial','unresolved_fields':[
                {'id':'Q-C05','reason':'unasked' if outcome=='unanswered' else 'route_unconfirmed' if outcome=='compare' else outcome},
                {'id':'Q-W04','reason':'requires_contact_gate'}]},
                'G2':{'status':'blocked','conditional_plan_only':True},'G3':G3,
                'active_branches':['core','os','network','payment','protection'],'deferred_branches':[],
                'route_confirmation':'unconfirmed',
                'current_subscription':{'status':'none_reported','source':SOURCE,'observed_at':TIME}}
            if outcome=='compare':
                expected['G1']['unresolved_fields']=[{'id':'Q-W04','reason':'requires_contact_gate'},
                                                   {'id':'Q-C05','reason':'route_unconfirmed'}]
            self.assertEqual(f.assessment(state),expected)
            self.assertEqual(state['context']['route_selection_basis'],'default_proposal')
            self.assertEqual(state['context']['route'],'compare' if outcome=='compare' else 'local')
            self.assertFalse(any(q['branch'] in {'local','vm','vps'} for q in f.applicable_questions(state)))
            if outcome!='unanswered':
                fact=prior.envelope('Q-C05','compare' if outcome=='compare' else None,
                                    source=SOURCE,state='reported' if outcome=='compare' else outcome)
                fact.update(subject_ref='scope-device',observed_at=TIME)
                self.assertEqual(state['facts']['Q-C05'],fact)
            loaded=f.loads_state(f.dumps_state(state,host_opt_in=True))
            self.assertEqual(loaded,state)
            self.assertIsNone(f.next_question(loaded))
            self.assertEqual(f.assessment(loaded),expected)
            self.assert_closed(state)

    def test_T78_experience_only_is_unknown_and_gets_one_concise_journey_question(self):
        for utterance in ('我是老手','用过'):
            state=f.set_context(new(),ambiguous_experience=True)
            self.assertEqual(f.journey(state),'unknown')
            self.assertEqual(state['current_subscription'],{'status':'unknown','source':None,'observed_at':None})
            self.assertEqual(state['facts'],{})
            self.assertEqual(f.next_question(state),question('Q-J02'))
            self.assertEqual(state['payment_intent'],'unresolved')
            self.assertEqual(f.next_question(f.loads_state(f.dumps_state(state,host_opt_in=True))),question('Q-J02'))
            for outcome in ('unknown','declined','deferred'):
                result=f.record_fact(f.mark_asked(state,'Q-J02'),'Q-J02',state_name=outcome,source=SOURCE,observed_at=TIME)
                self.assertEqual(f.journey(result),'unknown')
                self.assertEqual(result['current_subscription'],{'status':'unknown','source':SOURCE,'observed_at':TIME})
                self.assertEqual(f.next_question(result),question('Q-C02'))
                self.assertEqual(f.next_question(result),question('Q-C02'))
                self.assertEqual(f.assessment(result)['G2'],{'status':'blocked','conditional_plan_only':True})
                self.assert_closed(result)

    def test_T78_explicit_subscription_answers_not_expertise_choose_branch(self):
        initial=f.set_context(new(),ambiguous_experience=True)
        for value,status,intent,next_id in (
            ('first_subscription','none_reported','new_subscription','Q-C02'),
            ('returning_subscription','none_reported','resubscribe','Q-C02'),
            ('existing_subscriber','active_reported','unresolved','Q-C11')):
            state=f.record_fact(f.mark_asked(initial,'Q-J02'),'Q-J02',value,source=SOURCE,observed_at=TIME)
            self.assertEqual(state['current_subscription'],{'status':status,'source':SOURCE,'observed_at':TIME})
            self.assertEqual(state['payment_intent'],intent)
            self.assertEqual(f.journey(state),value)
            self.assertEqual(f.next_question(state),question(next_id))
            self.assertNotIn('Q-J01',[q['id'] for q in f.applicable_questions(state)])
            self.assert_closed(state)
        with self.assertRaisesRegex(f.InterviewError,'^Inference cannot establish protected facts$'):
            f.record_fact(initial,'Q-J02','existing_subscriber',state_name='inferred',source='synthetic:guess',observed_at=TIME)
        self.assertEqual(initial['current_subscription']['status'],'unknown')
        self.assertEqual(f.next_question(initial),question('Q-J02'))

    def test_T43_literal_opening_records_no_purchase_in_all_orders(self):
        for order in itertools.permutations(FOUR):
            state=f.record_facts(new(),list(order),source=SOURCE)
            self.assertEqual(state['purchase_intent'],'none')
            self.assertEqual(state['payment_intent'],'none')
            self.assertEqual(state['context']['task'],'environment')
            self.assertEqual(state['current_subscription'],{'status':'active_reported','source':SOURCE,'observed_at':TIME})
            self.assertEqual(f.next_question(state),question('Q-C01'))
            self.assertEqual(set(state['facts']),{'Q-J01','Q-C11','Q-C02','Q-C05'})
            for item in FOUR:
                expected=prior.envelope(item['question_id'],item['value'],source=SOURCE)
                expected.update(subject_ref='scope-account' if item['question_id']=='Q-J01' else 'scope-device',observed_at=TIME)
                self.assertEqual(state['facts'][item['question_id']],expected)
            self.assert_closed(state)

    def test_T43_entire_local_environment_path_has_no_purchase_topic(self):
        state=f.record_facts(new(),FOUR,source=SOURCE)
        state,trace=feed(state,ENV_SEQUENCE)
        self.assertIsNone(f.next_question(state))
        self.assertEqual(f.assessment(state),{
            'traffic_policy': expected_policy(), 'stage':'I6','G1':{'status':'complete','unresolved_fields':[]},
            'G2':{'status':'pass','conditional_plan_only':False},'G3':G3,
            'active_branches':['core','os','network','local','protection'],
            'deferred_branches':[],'route_confirmation':'confirmed',
            'current_subscription':{'status':'active_reported','source':SOURCE,'observed_at':TIME}})
        self.assertEqual([q['id'] for q in trace],ENV_SEQUENCE)
        self.assertEqual((state['purchase_intent'],state['payment_intent']),('none','none'))
        self.assert_closed(state)

    def test_T43_load_save_current_context_and_new_task_preserve_evidence(self):
        state=f.record_facts(new(),FOUR,source=SOURCE)
        old=deepcopy(state);old['purchase_intent']='subscription_preparation'
        old['payment_intent']='unresolved'
        before=deepcopy(old)
        for current in (f.loads_state(json.dumps(old)),json.loads(f.dumps_state(old,host_opt_in=True)),
                        f.set_context(old,task='environment'),
                        f.record_fact(old,'Q-J01','existing_subscriber',source=SOURCE,observed_at=TIME)):
            self.assertEqual((current['purchase_intent'],current['payment_intent']),('none','none'))
            self.assertEqual(current['facts'],state['facts'])
            self.assertEqual(current['current_subscription'],state['current_subscription'])
        self.assertEqual(old,before)
        purchase=f.complete_purchase(at_payment(),source='synthetic:completed',observed_at=TIME)
        for current in (purchase,f.loads_state(f.dumps_state(purchase,host_opt_in=True)),f.set_context(purchase,task='environment')):
            self.assertEqual(current['purchase_intent'],'completed')
            self.assertEqual(current['payment_intent'],'none')
        following=f.begin_task(purchase,task_id='environment-2',task='environment')
        self.assertEqual((following['purchase_intent'],following['payment_intent']),('none','none'))
        renewed=f.begin_task(following,task_id='renew-3',task='renew')
        self.assertEqual((renewed['purchase_intent'],renewed['payment_intent']),('subscription_preparation','renew'))
        self.assertNotIn('Q-C08',renewed['facts'])

    def test_T43_invalid_batches_and_ambiguous_task_cannot_relabel_state(self):
        state=new();before=deepcopy(state)
        with self.assertRaises(f.InterviewError):
            f.record_facts(state,FOUR+[{'question_id':'bad','value':'synthetic'}],source=SOURCE)
        self.assertEqual(state,before)
        for task in ([],{},'invalid'):
            with self.assertRaises(f.InterviewError):
                f.set_context(state,task=task)
            self.assertEqual(state,before)
        for outcome in ('unknown','declined','deferred','inferred'):
            current=f.record_fact(state,'Q-C11','environment' if outcome=='inferred' else None,
                                  state_name=outcome,source=SOURCE,observed_at=TIME)
            self.assertEqual(current['purchase_intent'],'subscription_preparation')
            self.assertEqual(current['context']['task'],'subscription_preparation')

    def test_T43_explicit_task_round_trips_do_not_keep_stale_none_intent(self):
        environment=f.record_facts(new(),FOUR,source=SOURCE)
        for task,intent in (('renew','renew'),('upgrade','upgrade'),
                            ('change_channel','change_channel'),('subscription_preparation','unresolved')):
            for current in (f.set_context(environment,task=task),
                            f.record_fact(environment,'Q-C11',task,source=SOURCE,observed_at=TIME),
                            f.begin_task(environment,task_id='next-task',task=task)):
                self.assertEqual((current['purchase_intent'],current['payment_intent']),('subscription_preparation',intent))
                returned=f.set_context(current,task='environment')
                self.assertEqual((returned['purchase_intent'],returned['payment_intent']),('none','none'))
        completed=f.complete_purchase(at_payment(),source='synthetic:done',observed_at=TIME)
        next_purchase=f.set_context(completed,task='renew',purchase_completed=False)
        self.assertEqual((next_purchase['purchase_intent'],next_purchase['payment_intent']),('subscription_preparation','renew'))

    def test_T48_exposure_prompt_names_category_and_service_without_requesting_secret(self):
        state=f.set_context(at_payment(),incident='credential_exposure')
        self.assertEqual(f.next_question(state),question('Q-H01',exposure=True))

    def test_T48_other_unresolved_themes_are_explicitly_postponed_not_user_deferred(self):
        state=f.set_context(at_payment(),incident='credential_exposure')
        result=f.assessment(state)
        self.assertEqual(result['emergency_deferred_branches'],['payment','local','protection'])
        self.assertEqual(result['deferred_branches'],[])
        self.assertEqual(state['deferred_branches'],[])

    def test_T48_zero_and_one_answer_allow_early_guidance_with_no_routine_survey(self):
        before=at_payment()
        self.assertEqual(f.next_question(before),question('Q-P03'))
        urgent=f.set_context(before,incident='credential_exposure')
        self.assertEqual(urgent['facts'],before['facts'])
        one=f.record_fact(urgent,'Q-H01','service_alias: credential_category',source=SOURCE,observed_at=TIME)
        for state,next_id in ((urgent,'Q-H01'),(one,'Q-H02')):
            result=f.assessment(state)
            self.assertEqual(result,expected_urgent(1 if next_id=='Q-H01' else 2))
            self.assertEqual(result['G1']['status'],'emergency_deferred')
            self.assertEqual(result['G2'],{'status':'blocked','conditional_plan_only':True})
            self.assertEqual(result['active_branches'],['incident'])
            self.assertEqual(result['emergency_deferred_branches'],['payment','local','protection'])
            self.assertEqual(f.next_question(state),question(next_id,exposure=True))
            self.assertEqual([q['id'] for q in f.applicable_questions(state)],['Q-H01','Q-H02','Q-H03','Q-H04','Q-H05','Q-H06','Q-H07'])
            self.assert_closed(state)

    def test_T48_complete_exposure_and_suspension_traces_preserve_routine_answers(self):
        before=at_payment()
        for kind in ('credential_exposure','suspension'):
            state=(f.set_context(before,incident=kind) if kind=='credential_exposure' else
                   f.record_fact(before,'Q-C03','current_suspension',source='synthetic:urgent-now'))
            retained=deepcopy(state['facts'])
            for qid in ('Q-H01','Q-H02','Q-H03','Q-H04','Q-H05','Q-H06','Q-H07'):
                self.assertEqual(f.next_question(state),question(qid,exposure=kind=='credential_exposure'))
                self.assertEqual(f.assessment(state)['G1']['status'],'emergency_deferred')
                state=f.mark_asked(state,qid)
                state=f.record_fact(state,qid,'synthetic_sanitized_current_incident_fact',source=SOURCE,observed_at=TIME)
            self.assertIsNone(f.next_question(state))
            self.assertEqual({q:state['facts'][q] for q in retained},retained)
            self.assertEqual(f.assessment(state)['G1'],{'status':'emergency_deferred','unresolved_fields':[]})
            self.assertEqual(f.assessment(state)['G2'],{'status':'blocked','conditional_plan_only':True})
            self.assert_closed(state)
            resolved=f.set_context(state,incident_resolved=True)
            self.assertNotIn('emergency_deferred_branches',f.assessment(resolved))
            self.assertEqual(f.next_question(resolved),{
                'id':'Q-H08','branch':'incident','stage':'I3','postcontact':False,
                'prompt':'本次是否沿用当时的设备/网络/付款工具？哪些变了？','clarification':False,
                'allowed_outcomes':['reported','unknown','declined','deferred'],'requires_action_authorization':False})
            resolved=f.record_fact(resolved,'Q-H08','no_further_change_reported',source=SOURCE,observed_at=TIME)
            self.assertEqual(f.next_question(resolved),question('Q-P03'))
            self.assertEqual({q:resolved['facts'][q] for q in retained},retained)

    def test_T48_unknown_refusal_deferral_and_not_applicable_do_not_resolve_or_loop(self):
        for outcome in ('unknown','declined','deferred','not_applicable'):
            state=f.set_context(at_payment(),incident='credential_exposure')
            for qid in ('Q-H01','Q-H02','Q-H03','Q-H04','Q-H05','Q-H06','Q-H07'):
                self.assertEqual(f.next_question(state),question(qid,exposure=True))
                state=f.record_fact(f.mark_asked(state,qid),qid,state_name=outcome,source=SOURCE,observed_at=TIME)
            self.assertIsNone(f.next_question(state))
            loaded=f.loads_state(f.dumps_state(state,host_opt_in=True))
            self.assertEqual(loaded,state)
            self.assertIsNone(f.next_question(loaded))
            self.assertFalse(state['context']['incident_resolved'])
            self.assertEqual(f.assessment(state)['G1'],{'status':'emergency_deferred','unresolved_fields':
                [] if outcome=='not_applicable' else [{'id':f'Q-H{i:02d}','reason':outcome} for i in range(1,8)]})
            self.assert_closed(state)


class TaskScopeCLITests(unittest.TestCase):
    def test_old_environment_state_load_and_save_corrects_only_task_labels(self):
        with patch.object(f,'_now',return_value=TIME):
            state=f.record_facts(new(),FOUR,source=SOURCE)
        state['purchase_intent']='subscription_preparation';state['payment_intent']='unresolved'
        with tempfile.TemporaryDirectory(prefix='guardian-task-scope-') as directory:
            saved=Path(directory)/'before.json';output=Path(directory)/'after.json'
            original=json.dumps(state,ensure_ascii=False);saved.write_text(original,encoding='utf-8')
            result=subprocess.run([sys.executable,'-B',str(ROOT/'skills/claude-guardian/scripts/interview_cli.py'),
                '--input',str(saved),'--output',str(output)],capture_output=True,text=True,encoding='utf-8',timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            self.assertEqual(json.loads(result.stdout)['question'],question('Q-C01'))
            after=json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual((after['purchase_intent'],after['payment_intent']),('none','none'))
            self.assertEqual(after['facts'],state['facts'])
            self.assertEqual(after['current_subscription'],state['current_subscription'])
            self.assertEqual(saved.read_text(encoding='utf-8'),original)

    def test_immediate_incident_output_projects_postponement_without_waiting_for_details(self):
        with patch.object(f,'_now',return_value=TIME):
            state=f.set_context(at_payment(),incident='credential_exposure')
        with tempfile.TemporaryDirectory(prefix='guardian-task-scope-') as directory:
            saved=Path(directory)/'before.json';saved.write_text(f.dumps_state(state,host_opt_in=True),encoding='utf-8')
            result=subprocess.run([sys.executable,'-B',str(ROOT/'skills/claude-guardian/scripts/interview_cli.py'),
                '--input',str(saved)],capture_output=True,text=True,encoding='utf-8',timeout=10)
            self.assertEqual(result.returncode,0,result.stderr)
            actual=json.loads(result.stdout)
            self.assertEqual(actual['question'],question('Q-H01',exposure=True))
            expected=expected_urgent()
            expected['current_subscription']['source']='private-source-retained'
            self.assertEqual(actual,{'schema_version':'guardian-intake-result/1','question':question('Q-H01',exposure=True),
                'assessment':expected,'contact_control':'host_authorization_required','action_executed':False,'saved':False})


def replay():
    """Full actual receipts; tests use independent authored expectations above."""
    with patch.object(f,'_now',return_value=TIME):
        output={}
        base=at_route();output['T34']={'unanswered_before_delivery':snapshot(base),'variants':{}}
        for outcome in ('unanswered','unknown','declined','deferred','compare'):
            state=f.mark_asked(base,'Q-C05')
            if outcome!='unanswered':
                state=f.record_fact(state,'Q-C05','compare' if outcome=='compare' else None,
                    state_name='reported' if outcome=='compare' else outcome,source=SOURCE,observed_at=TIME)
            initial=snapshot(state);state,questions=feed(state,ROUTE_REST)
            output['T34']['variants'][outcome]={'input_outcome':outcome,'after_route_turn':initial,
                'remaining_questions':questions,'final':snapshot(state),
                'loaded':snapshot(f.loads_state(f.dumps_state(state,host_opt_in=True)))}
        output['T78']={}
        for utterance in ('我是老手','用过'):
            state=f.set_context(new(),ambiguous_experience=True)
            outcomes={}
            for outcome in ('unknown','declined','deferred','first_subscription','returning_subscription','existing_subscriber'):
                answer={'value':None,'state_name':outcome} if outcome in ('unknown','declined','deferred') else {'value':outcome}
                current=f.record_fact(f.mark_asked(state,'Q-J02'),'Q-J02',source=SOURCE,observed_at=TIME,**answer)
                outcomes[outcome]=snapshot(current)
            output['T78'][utterance]={'normalized_context':{'ambiguous_experience':True},'initial':snapshot(state),'outcomes':outcomes}
        initial=f.record_facts(new(),FOUR,source=SOURCE);final,questions=feed(initial,ENV_SEQUENCE)
        old=deepcopy(initial);old['purchase_intent']='subscription_preparation';old['payment_intent']='unresolved'
        output['T43']={'literal':'我已有订阅，这次只检查 Mac 本机环境。','normalized_input':FOUR,
            'initial':snapshot(initial),'remaining_questions':questions,'final':snapshot(final),
            'legacy_saved_state':old,'loaded_legacy':snapshot(f.loads_state(json.dumps(old))),
            'permutations':[{'input':list(order),'actual':snapshot(f.record_facts(new(),list(order),source=SOURCE))}
                for order in itertools.permutations(FOUR)]}
        base=at_payment();output['T48']={'before_incident':snapshot(base),'incidents':{},'exits':{}}
        for kind in ('credential_exposure','suspension'):
            state=(f.set_context(base,incident=kind) if kind=='credential_exposure' else
                   f.record_fact(base,'Q-C03','current_suspension',source='synthetic:urgent-now'))
            initial=snapshot(state);steps=[]
            for qid in ('Q-H01','Q-H02','Q-H03','Q-H04','Q-H05','Q-H06','Q-H07'):
                expected=question(qid,exposure=kind=='credential_exposure')
                assert f.next_question(state)==expected
                state=f.record_fact(f.mark_asked(state,qid),qid,'synthetic_sanitized_current_incident_fact',source=SOURCE,observed_at=TIME)
                steps.append({'delivered_question':expected,'after_answer':snapshot(state)})
            unresolved=snapshot(state);state=f.set_context(state,incident_resolved=True)
            resolved=snapshot(state);state=f.record_fact(state,'Q-H08','no_further_change_reported',source=SOURCE,observed_at=TIME)
            output['T48']['incidents'][kind]={'initial':initial,'steps':steps,'all_fields_but_not_resolved':unresolved,
                'explicitly_resolved':resolved,'after_historical_change_check':snapshot(state)}
        for outcome in ('unknown','declined','deferred','not_applicable'):
            state=f.set_context(base,incident='credential_exposure')
            for qid in ('Q-H01','Q-H02','Q-H03','Q-H04','Q-H05','Q-H06','Q-H07'):
                state=f.record_fact(f.mark_asked(state,qid),qid,state_name=outcome,source=SOURCE,observed_at=TIME)
            output['T48']['exits'][outcome]=snapshot(state)
        return output


if __name__=='__main__':
    if sys.argv[1:]==['--replay']:
        print(json.dumps(replay(),ensure_ascii=False,indent=2,sort_keys=True))
    else:
        unittest.main()
