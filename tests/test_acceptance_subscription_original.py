"""Independent original T76/T84 L replay; C is a separate substantive review.

All facts are explicit synthetic reports; strings are not submitted to a model.
No actual subscription/compatibility, native/device, contact, or cleanup evidence.
"""
from contextlib import ExitStack
from copy import deepcopy
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
sys.path.insert(0, str(ROOT/'skills/claude-guardian/scripts'))
import interview_flow as f
NOW = '2026-10-18T09:00:00+00:00'
OLD = '2026-10-17T08:00:00+00:00'
SOURCE = 'synthetic:independent-original-clause'
TRACE = []
PAY = ('Q-P', 'Q-A', 'Q-G', 'Q-W', 'Q-I', 'Q-E')
PLAN_PROMPT = '为判断这次具体客户端功能的套餐依赖：当前订阅是什么套餐，涉及哪项功能？只说已知情况，不确定或暂不回答也可以；无需打开 Claude。'
VALUES = {
 'Q-C02': 'macos', 'Q-C01': 'code', 'Q-OS03': 'synthetic-macos-version',
 'Q-OS02': 'synthetic-windows-version-and-edition', 'Q-C08': 'synthetic-desired-plan-D',
 'Q-C03': 'none_reported', 'Q-C04': 'registered_login_reported', 'Q-C05': 'local',
 'Q-C06': 'email', 'Q-C09': 'synthetic-reported-region-not-verified',
 'Q-N01': 'synthetic-proxy-path', 'Q-N02': 'synthetic-code-and-proxy-local',
 'Q-N03': 'synthetic-no-switching', 'Q-N04': 'synthetic-selected-device',
 'Q-N06': 'synthetic-personal-device', 'Q-L01': 'synthetic-existing-client-metadata',
 'Q-L02': 'synthetic-reported-hardware-compatibility', 'Q-L04': 'synthetic-local-project',
 'Q-C12': 'preserve-code-projects-history-config', 'Q-Z01': 'planning-only',
 'Q-C10': 'step-by-step', 'Q-D02': 'audit_only', 'Q-Z03': 'no-operation-authorized',
 'Q-Z04': 'synthetic-backup-required-before-any-action', 'Q-P07': 'synthetic-renewal-guidance',
 'Q-W01': 'synthetic-card-category', 'Q-W02': 'truthful-billing-only-at-approved-checkout',
 'Q-W03': 'synthetic-online-recurring-report', 'Q-C13': 'synthetic-current-plan-A; synthetic-feature-F'}
NETWORK = ['Q-C02','Q-C01','Q-OS03','Q-C03','Q-C04','Q-C05','Q-C06','Q-C09','Q-N01','Q-N02','Q-N03','Q-N04','Q-N06','Q-L01','Q-L04','Q-C12','Q-Z01','Q-C10']
PREP = ['Q-C02','Q-C01','Q-OS03','Q-C08','Q-C03','Q-C04','Q-C05','Q-C06','Q-C09','Q-N01','Q-N02','Q-N03','Q-N04','Q-N06','Q-P07','Q-W01','Q-W02','Q-W03','Q-L01','Q-L04','Q-C12','Q-Z01','Q-C10']
CLEANUP = ['Q-D02','Q-C02','Q-C01','Q-OS03','Q-C05','Q-C12','Q-Z01']

def record(s, q, value=None, **kw):
    if value is None and not kw.get('state_name'): value=VALUES[q]
    return f.record_fact(s,q,value,source=SOURCE,**kw)

def initial(journey='existing_subscriber', task='network', **context):
    s=f.new_state('synthetic-device','synthetic-account',task_id='synthetic-task')
    s=record(s,'Q-J01',journey,observed_at=OLD)
    return f.set_context(s,task=task,**context)

def ids(s): return [q['id'] for q in f.applicable_questions(s)]

def snap(name,s):
    TRACE.append({'name':name,'state':deepcopy(s),'next_question':f.next_question(s),
                  'applicable_questions':f.applicable_questions(s),'assessment':f.assessment(s),
                  'resume_prompt':f.resume_review_prompt(s)})

class OriginalSubscriptionAcceptance(unittest.TestCase):
    def setUp(self):
        self.stack=ExitStack(); self.addCleanup(self.stack.close)
        self.stack.enter_context(patch.object(f,'_now',return_value=NOW))
        for name in ['socket.socket','socket.create_connection','socket.getaddrinfo','subprocess.run','subprocess.Popen','builtins.open','pathlib.Path.open']:
            self.stack.enter_context(patch(name,side_effect=AssertionError('Unexpected I/O: '+name)))
    def safe(self,s):
        self.assertEqual(s['context']['contact_phase'],'PC0')
        self.assertEqual(f.assessment(s)['G3']['status'],'blocked')
        self.assertTrue(all(v is False for v in s['persistence_consent'].values()))
        self.assertNotIn('Q-C07',ids(s))
    def technical(self,s,needed=False):
        self.safe(s)
        self.assertNotIn('Q-C08',ids(s))
        self.assertFalse(any(q.startswith(PAY) for q in ids(s)))
        self.assertEqual(s['purchase_intent'],'none')
        self.assertEqual(s['payment_intent'],'none')
        self.assertEqual('Q-C13' in ids(s),needed)
    def path(self,s,order,name):
        snap(name+':start',s)
        for qid in order:
            q=f.next_question(s)
            self.assertIsNotNone(q,(name,qid)); self.assertEqual(q['id'],qid,name)
            self.assertFalse(q['requires_action_authorization'])
            self.assertEqual(q['allowed_outcomes'],['reported','unknown','declined','deferred'])
            self.assertFalse(q['clarification'])
            s=record(f.mark_asked(s,qid),qid)
            self.safe(s); snap(name+':'+qid,s)
        return s
    def network(self,needed=False,os_name='macos'):
        s=initial(plan_compatibility_needed=needed)
        order=NETWORK.copy()
        if os_name=='windows':
            s=record(s,'Q-C02','windows'); order.remove('Q-C02'); order[order.index('Q-OS03')]='Q-OS02'
        if needed: order.insert(order.index('Q-C12'),'Q-C13')
        return self.path(s,order,'T84-network-'+os_name+str(needed))
    def cleanup(self,needed=False):
        s=initial(task='cleanup',plan_compatibility_needed=needed)
        order=CLEANUP+(['Q-C13'] if needed else [])
        return self.path(s,order,'T84-cleanup-'+str(needed))

    def test_t76_complete_original_plain_paths(self):
        for os_name in ['macos','windows']:
            s=initial('returning_subscription','subscription_preparation',billing_channel='web')
            sub=deepcopy(s['current_subscription']); self.assertEqual(sub,{'status':'none_reported','source':SOURCE,'observed_at':OLD})
            order=PREP.copy()
            if os_name=='windows':
                s=record(s,'Q-C02','windows'); order.remove('Q-C02'); order[order.index('Q-OS03')]='Q-OS02'
            s=self.path(s,order,'T76-'+os_name)
            self.assertEqual(f.journey(s),'returning_subscription')
            self.assertEqual(s['current_subscription'],sub)
            self.assertEqual(s['payment_intent'],'resubscribe')
            self.assertTrue({'Q-J02','Q-C11','Q-P02','Q-A06','Q-C13'}.isdisjoint(ids(s)))
            self.assertIsNone(f.next_question(s))
            self.assertEqual(f.assessment(s)['G1']['unresolved_fields'],[{'id':'Q-W04','reason':'requires_contact_gate'}])
            self.assertEqual(f.loads_state(f.dumps_state(s,host_opt_in=True)),s)
            s=f.resume_interview(s,resume_id='explicit-interruption')
            self.assertIsNone(f.next_question(s)); self.assertEqual(s['facts']['Q-C08']['value'],VALUES['Q-C08'])
            s=f.record_resume_review(s,resume_id='explicit-interruption',response='unchanged',source=SOURCE)
            self.assertIsNone(f.next_question(s)); self.assertEqual(s['current_subscription'],sub)
            self.safe(s); snap('T76-'+os_name+':resumed',s)
    def test_t76_desired_unknown_decline_defer_compare_and_presupplied(self):
        for state in ['unknown','declined','deferred']:
            s=initial('returning_subscription','subscription_preparation')
            s=record(s,'Q-C02'); s=record(s,'Q-C01'); s=record(s,'Q-OS03')
            self.assertEqual(f.next_question(s)['id'],'Q-C08')
            s=record(s,'Q-C08',state_name=state)
            self.assertNotEqual(f.next_question(s)['id'],'Q-C08')
            self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
            self.assertEqual(s['facts']['Q-C08']['state'],state)
            self.assertTrue({'Q-J02','Q-P02','Q-A06'}.isdisjoint(ids(s))); snap('T76-plan-'+state,s)
        s=record(initial('returning_subscription','subscription_preparation'),'Q-C08','undecided')
        self.assertIn('Q-P05',ids(s)); self.assertEqual(s['facts']['Q-C08']['value'],'undecided')
        named=record(initial('returning_subscription','subscription_preparation'),'Q-C08')
        self.assertEqual(f.next_question(named)['id'],'Q-C02'); snap('T76-already-selected',named)
    def test_t76_relevant_legacy_bill_and_return_to_resubscribe(self):
        for issue in ['pending_refund','restore_old_order']:
            for past in ['apple','google','web']:
                s=record(initial('returning_subscription','subscription_preparation',billing_channel='web'),'Q-C08')
                sub=deepcopy(s['current_subscription']); target=deepcopy(s['facts']['Q-C08'])
                s=f.set_context(s,task='billing_issue')
                self.assertEqual(f.next_question(s)['id'],'Q-P02')
                self.assertFalse(s['context']['subscription_conflict'])
                order={'plan':'synthetic-former-plan','billing_channel':past,'status':'expired','pending_issue':issue}
                s=record(s,'Q-P02',order,observed_at=OLD)
                self.assertIsNone(f.next_question(s)); self.assertEqual(ids(s),['Q-J01','Q-P02'])
                self.assertNotIn('Q-A06',s['facts']); self.assertEqual(f.assessment(s)['G2']['status'],'pass')
                self.assertEqual(s['payment_intent'],'troubleshoot'); self.safe(s); snap('T76-old-'+past+'-'+issue,s)
                s=f.set_context(s,task='subscription_preparation')
                self.assertEqual(s['facts']['Q-C08'],target); self.assertEqual(s['current_subscription'],sub)
                self.assertEqual(s['payment_intent'],'resubscribe'); self.assertTrue({'Q-P02','Q-A06'}.isdisjoint(ids(s)))
                snap('T76-resubscribe-'+past+'-'+issue,s)
    def test_t76_incomplete_negative_unknown_old_order_bounded(self):
        for outcome in ['unknown','declined','deferred']:
            s=initial('returning_subscription','billing_issue',billing_channel='apple')
            s=record(s,'Q-P02',state_name=outcome)
            self.assertIsNone(f.next_question(s)); self.assertNotIn('Q-A06',ids(s))
            self.assertTrue(f.assessment(s)['G2']['conditional_plan_only']); self.safe(s); snap('T76-old-'+outcome,s)
        s=initial('returning_subscription','billing_issue',billing_channel='google')
        s=record(s,'Q-P02',{'billing_channel':'apple','status':'expired'})
        self.assertEqual(f.next_question(s)['id'],'Q-A06')
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
        s=record(s,'Q-A06','no_pending_refund_reported')
        self.assertIsNone(f.next_question(s)); self.assertEqual(s['current_subscription']['status'],'none_reported')
        snap('T76-negative-old-issue',s)
        s=record(s,'Q-P02',{'billing_channel':'web','status':'expired'})
        self.assertEqual(s['facts']['Q-A06']['state'],'stale')
        self.assertEqual(f.next_question(s)['id'],'Q-P02'); self.assertTrue(f.next_question(s)['clarification'])
        s=f.mark_asked(s,'Q-P02'); self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only']); snap('T76-partial-once',s)
    def test_t76_old_bill_branch_defer_and_resume_preserves_goal(self):
        s=record(initial('returning_subscription','billing_issue',billing_channel='apple'),'Q-C08')
        original=deepcopy(s['current_subscription']); goal=deepcopy(s['facts']['Q-C08'])
        s=f.defer_branch(s,'payment'); self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only']); self.safe(s)
        s=f.loads_state(f.dumps_state(s,host_opt_in=True))
        s=f.resume_branch(s,'payment'); self.assertEqual(f.next_question(s)['id'],'Q-P02')
        self.assertEqual(s['current_subscription'],original); self.assertEqual(s['facts']['Q-C08'],goal)
        snap('T76-old-bill-branch-resumed',s)

    def test_t76_actual_conflict_is_separate_from_expiry(self):
        for stage,expected in [('first_subscription',False),('returning_subscription',True),('existing_subscriber',True)]:
            s=initial(stage,'billing_issue',billing_channel='apple')
            self.assertEqual('Q-P02' in ids(s),expected); self.assertFalse(s['context']['subscription_conflict'])
        s=f.set_context(initial('returning_subscription','subscription_preparation'),subscription_conflict=True)
        self.assertIn('Q-P02',ids(s)); self.assertEqual(s['current_subscription']['status'],'none_reported')
        self.safe(s); snap('T76-explicit-conflict-control',s)
    def test_t84_complete_network_and_cleanup_no_purchase(self):
        for os_name in ['macos','windows']:
            s=self.network(os_name=os_name); self.technical(s)
            self.assertIsNone(f.next_question(s)); self.assertEqual(f.assessment(s)['G2']['status'],'pass')
            self.assertEqual(s['current_subscription']['status'],'active_reported')
        s=self.cleanup(); self.technical(s)
        self.assertEqual(f.assessment(s)['G2']['status'],'pass'); self.assertIsNone(f.next_question(s))
    def test_t84_actual_plan_dependency_is_separate_and_nonverifying(self):
        for task in ['network','environment','cleanup']:
            s=self.cleanup() if task=='cleanup' else self.network()
            if task=='environment': s=f.set_context(s,task='environment')
            s=f.set_context(s,plan_compatibility_needed=True)
            self.technical(s,True); q=f.next_question(s)
            self.assertEqual(q,{'id':'Q-C13','branch':'compatibility','stage':'I5','postcontact':False,'prompt':PLAN_PROMPT,'clarification':False,'allowed_outcomes':['reported','unknown','declined','deferred'],'requires_action_authorization':False})
            before=deepcopy(s['facts'])
            s=record(s,'Q-C13'); self.technical(s,True)
            self.assertEqual(s['facts']['Q-C13']['subject_ref'],s['account_alias'])
            self.assertEqual({k:v for k,v in s['facts'].items() if k!='Q-C13'},before)
            self.assertEqual(f.assessment(s)['current_plan_dependency'],{'question_id':'Q-C13','fact_state':'reported','compatibility':'not_established','unrelated_planning_available':True})
            self.assertEqual(f.assessment(s)['G2']['status'],'pass'); self.assertIsNone(f.next_question(s)); snap('T84-feature-'+task,s)
    def test_t84_presupplied_and_negative_feature_report_not_verified(self):
        s=self.network(); s=record(s,'Q-C13','synthetic-current-plan-A; feature-F-unavailable-reported',observed_at=NOW)
        original=deepcopy(s['facts']['Q-C13'])
        s=f.set_context(s,plan_compatibility_needed=True)
        self.assertEqual(s['facts']['Q-C13'],original); self.assertIsNone(f.next_question(s))
        self.technical(s,True)
        self.assertEqual(f.assessment(s)['current_plan_dependency']['compatibility'],'not_established')
        self.assertEqual(f.assessment(s)['G2']['status'],'pass')
        self.assertEqual(s['facts']['Q-C13']['value'],'synthetic-current-plan-A; feature-F-unavailable-reported')
        snap('T84-negative-feature-preserved',s)

    def test_t84_hardware_and_purchase_target_do_not_satisfy_current_plan(self):
        s=self.network(); s=record(s,'Q-C08','synthetic-desired-plan-D')
        s=f.set_context(s,compatibility_needed=True)
        self.assertEqual(f.next_question(s)['id'],'Q-L02'); self.assertNotIn('Q-C13',ids(s))
        s=record(s,'Q-L02'); s=f.set_context(s,plan_compatibility_needed=True)
        self.assertEqual(f.next_question(s)['id'],'Q-C13'); self.assertNotIn('Q-C13',s['facts'])
        self.technical(s,True); snap('T84-hardware-is-not-current-plan',s)
        for bad in ['selected_unspecified','']:
            with self.assertRaises(f.InterviewError): record(s,'Q-C13',bad)
        with self.assertRaises(f.InterviewError): record(s,'Q-C13','synthetic-plan',state_name='inferred')
        with self.assertRaises(f.InterviewError): record(s,'Q-C13','synthetic-plan',subject_ref='different-account')
        for journey in ['first_subscription','returning_subscription','unknown']:
            other=initial(journey,'network',plan_compatibility_needed=True)
            self.assertNotIn('Q-C13',ids(other)); self.assertNotIn('Q-C13',other['facts'])
        for bad in ['true',1,None]:
            with self.assertRaises(f.InterviewError): f.set_context(s,plan_compatibility_needed=bad)
    def test_t84_unknown_refused_deferred_and_not_applicable_conditional(self):
        for status in ['unknown','declined','deferred','not_applicable']:
            for task in ['network','cleanup']:
                s=self.network() if task=='network' else self.cleanup()
                s=f.set_context(s,plan_compatibility_needed=True)
                s=record(s,'Q-C13',state_name=status)
                self.technical(s,True); self.assertIsNone(f.next_question(s))
                self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
                self.assertTrue(f.assessment(s)['current_plan_dependency']['unrelated_planning_available'])
                self.assertIsNone(s['facts']['Q-C13']['value']); snap('T84-'+task+'-'+status,s)
                restored=f.loads_state(f.dumps_state(s,host_opt_in=True)); self.assertEqual(restored,s)
                s=f.set_context(restored,plan_compatibility_needed=False)
                self.assertEqual(f.assessment(s)['G2']['status'],'pass'); self.technical(s)
    def test_t84_dependency_defer_resume_and_stop(self):
        s=self.cleanup(); s=f.set_context(s,plan_compatibility_needed=True)
        s=f.defer_branch(s,'compatibility'); self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only']); self.technical(s,True)
        s=f.resume_branch(s,'compatibility'); self.assertEqual(f.next_question(s)['id'],'Q-C13')
        stopped=f.set_context(s,paused=True); self.assertIsNone(f.next_question(stopped)); self.safe(stopped)
        stopped=record(s,'Q-D02','no_cleanup'); self.assertEqual(ids(stopped),[]); self.assertIsNone(f.next_question(stopped)); self.safe(stopped)
        emergency=f.set_context(s,incident='credential_exposure')
        self.assertEqual(f.next_question(emergency)['id'],'Q-H01'); self.assertNotIn('Q-C13',ids(emergency)); self.safe(emergency)
        snap('T84-deferred',f.defer_branch(s,'compatibility')); snap('T84-stopped',stopped); snap('T84-emergency',emergency)
    def test_t84_resume_keeps_account_plan_but_requires_current_review(self):
        s=self.network(True); fact=deepcopy(s['facts']['Q-C13'])
        s=f.resume_interview(s,resume_id='feature-interruption')
        self.assertIn('Q-C13',s['resume_review']['scope_keys']); self.assertIsNone(f.next_question(s))
        self.assertIn('不涉及购买或付款',f.resume_review_prompt(s)['prompt'])
        for outcome in ['unknown','declined','deferred','target_changed']:
            unresolved=f.record_resume_review(s,resume_id='feature-interruption',response=outcome,source=SOURCE)
            self.assertIsNone(f.resume_review_prompt(unresolved)); self.assertTrue(f.assessment(unresolved)['G2']['conditional_plan_only'])
            self.technical(unresolved,True); snap('T84-resume-'+outcome,unresolved)
        unchanged=f.record_resume_review(s,resume_id='feature-interruption',response='unchanged',source=SOURCE)
        self.assertEqual(unchanged['facts']['Q-C13'],fact); self.assertEqual(f.assessment(unchanged)['G2']['status'],'pass')
        changed=f.record_resume_review(s,resume_id='feature-interruption',response='changed',source=SOURCE,changed_keys=['Q-C13'])
        self.assertEqual(changed['facts']['Q-C13']['state'],'stale'); self.assertEqual(changed['facts']['Q-C13']['observed_at'],fact['observed_at'])
        self.assertEqual(f.next_question(changed)['id'],'Q-C13')
        changed=f.mark_asked(changed,'Q-C13'); self.assertIsNone(f.next_question(changed))
        old=record(changed,'Q-C13',fact['value'],observed_at=fact['observed_at'])
        self.assertEqual(old['facts']['Q-C13']['state'],'stale'); self.assertIsNone(f.next_question(old))
        fresh=record(old,'Q-C13','synthetic-current-plan-B; synthetic-feature-F')
        self.assertEqual(fresh['facts']['Q-C13']['state'],'reported'); self.assertEqual(f.assessment(fresh)['G2']['status'],'pass')
        self.technical(fresh,True); snap('T84-resume-current',fresh)
    def test_t84_dormant_fact_rebinding_and_changed_stage(self):
        s=self.network(True); original=deepcopy(s['facts']['Q-C13'])
        dormant=f.set_context(s,plan_compatibility_needed=False)
        dormant=f.resume_interview(dormant,resume_id='dormant-interruption')
        self.assertIn('Q-C13',dormant['resume_review']['scope_keys'])
        for device,account in [('synthetic-device','synthetic-account'),('other-device','synthetic-account'),('synthetic-device','other-account')]:
            fresh=f.begin_task(dormant,task_id='second-task',task='network',target_alias=device,account_alias=account)
            self.assertFalse(fresh['context'].get('plan_compatibility_needed',False))
            if account=='synthetic-account': self.assertEqual(fresh['facts']['Q-C13']['state'],'stale')
            else: self.assertNotIn('Q-C13',fresh['facts']); self.assertEqual(f.journey(fresh),'unknown')
            self.safe(fresh); snap('T84-rebinding-'+device+'-'+account,fresh)
        for stage in ['returning_subscription','first_subscription','unknown']:
            changed=record(s,'Q-J01',stage)
            self.assertEqual(changed['facts']['Q-C13']['state'],'stale')
            self.assertEqual(changed['facts']['Q-C13']['source'],original['source'])
            self.assertNotIn('Q-C13',ids(changed)); self.safe(changed); snap('T84-stage-'+stage,changed)
        same=f.begin_task(s,task_id='other',task='cleanup',target_alias='other-device')
        self.assertEqual(same['facts']['Q-C13'],original); self.assertNotIn('Q-C13',ids(same))
        changed=f.set_context(s,task='cleanup'); self.assertFalse(changed['context'].get('plan_compatibility_needed',False))
        self.assertNotIn('Q-C13',ids(changed)); snap('T84-task-change',changed)

if __name__=='__main__':
    replay='--replay' in sys.argv
    if replay: sys.argv.remove('--replay')
    suite=unittest.defaultTestLoader.loadTestsFromTestCase(OriginalSubscriptionAcceptance)
    result=unittest.TextTestRunner(verbosity=2,stream=sys.stderr).run(suite)
    if replay: print(json.dumps({'schema':'independent-original-T76-T84/1','fixed_clock':NOW,'snapshots':TRACE,'tests_run':result.testsRun,'passed':result.wasSuccessful(),'limitations':['Trusted host normalized synthetic facts; no free-text model execution','Callable-path sentinels, not OS isolation','No actual plan compatibility, native operation, service contact or purchase']},ensure_ascii=False,indent=2,sort_keys=True))
    sys.exit(0 if result.wasSuccessful() else 1)
