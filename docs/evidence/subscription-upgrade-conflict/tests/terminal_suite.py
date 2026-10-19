"""Original terminal behavior assertions with a portable, non-recording loader.
Only the root selection and historical executable log-writing footer are changed.
"""
import copy, json, os, pathlib, sys, unittest
ROOT=pathlib.Path(os.environ['GUARDIAN_TERMINAL_REVIEW_ROOT'])
sys.dont_write_bytecode=True
sys.path.insert(0,str(ROOT/'skills/claude-guardian/scripts'))
import interview_flow as f
TRACE={}
def seed(missing):
 s=f.new_state('device-alias','account-alias')
 known={'billing_channel':'google','status':'active'} if missing=='current_plan' else {'plan':'套餐甲','status':'active'}
 s=f.record_facts(s,[{'question_id':'Q-J01','value':'existing_subscriber'},{'question_id':'Q-C11','value':'upgrade'},{'question_id':'Q-C08','value':'套餐乙'},{'question_id':'Q-P02','value':known}],source='synthetic:initial-known-facts')
 assert f.assessment(s)['upgrade_scope']['current_order_gaps']==[missing]
 q=f.next_question(s);assert q['id']=='Q-P02'
 return f.mark_asked(s,'Q-P02')
def has_origin(obj,component,value,origin):
 if isinstance(obj,dict):
  if (all(obj.get(k)==origin[k] for k in ['state','source','subject_ref','observed_at'])
      and (obj.get('value')==value or isinstance(obj.get('value'),dict) and obj['value'].get(component)==value)):
   return True
  return any(has_origin(v,component,value,origin) for v in obj.values())
 if isinstance(obj,list):return any(has_origin(v,component,value,origin) for v in obj)
 return False
class TerminalRetention(unittest.TestCase):
 def terminal(self,missing,outcome):
  s=seed(missing);old=copy.deepcopy(s);component='billing_channel' if missing=='current_plan' else 'plan';origin=s['facts']['Q-P02'];value=origin['value'][component]
  n=f.record_facts(s,[{'question_id':'Q-P02','value':None,'state':outcome}],source='synthetic:only-asked-gap-'+outcome)
  a=f.assessment(n);TRACE[missing+'-'+outcome]={'before':s,'after':n,'assessment':a,'next_question':f.next_question(n)}
  self.assertEqual(s,old,'public API must not mutate its input')
  self.assertEqual(n['facts']['Q-P02']['state'],outcome)
  self.assertIsNone(n['facts']['Q-P02']['value'],'terminal outcome must not invent the refused/missing value')
  self.assertIsNone(f.next_question(n),'do not repeat refused gap through P02 or A06')
  self.assertEqual(a['G2']['status'],'blocked');self.assertEqual(a['G3']['status'],'blocked')
  self.assertEqual(n['context']['contact_phase'],'PC0');self.assertFalse(n['context']['purchase_completed'])
  self.assertEqual(n['persistence_consent'],{'private_save':False,'export':False,'public_export':False})
  self.assertEqual(n['current_subscription']['status'],'active_reported')
  self.assertEqual(n['facts']['Q-C08']['value'],'套餐乙')
  self.assertEqual(a['upgrade_scope']['current_order_gaps'],[missing],'known complementary field must remain usable')
  self.assertTrue(has_origin(n['facts'],component,value,origin),'known complement must retain original source/time/account/state')
  loaded=f.loads_state(json.dumps(n));self.assertEqual(loaded,n);self.assertEqual(f.assessment(loaded)['upgrade_scope']['current_order_gaps'],[missing])
 def test_wrong_account_is_atomic(self):
  s=seed('current_plan');old=copy.deepcopy(s)
  with self.assertRaises(f.InterviewError):f.record_fact(s,'Q-P02',None,state_name='declined',source='synthetic:wrong-account',subject_ref='other-account')
  self.assertEqual(s,old);TRACE['wrong-account']={'state_unchanged':s==old}
 def test_stale_complement_cannot_be_restored(self):
  s=seed('current_channel');s=f.record_fact(s,'Q-P02',{'plan':'套餐甲','status':'active'},state_name='stale',source='synthetic:stale-order')
  n=f.record_fact(s,'Q-P02',None,state_name='declined',source='synthetic:declined-channel');a=f.assessment(n)
  TRACE['stale-control']={'before':s,'after':n,'assessment':a}
  self.assertEqual(a['upgrade_scope']['current_order_gaps'],['current_plan','current_channel']);self.assertEqual(a['G2']['status'],'blocked');self.assertIsNone(f.next_question(n))
 def test_new_episode_cannot_reuse_old_detail(self):
  s=f.new_state('device-alias','account-alias');s=f.record_fact(s,'Q-J01','first_subscription',source='synthetic:first')
  s=f.report_subscription_conflict(s,source='synthetic:page-1')
  s=f.resolve_subscription_conflict(s,episode_id=s['subscription_review']['episode_id'],account_ref='account-alias',target_ref='device-alias',task_id=s['task_id'],outcome='existing_subscription',answers=[{'question_id':'Q-J01','value':'existing_subscriber'},{'question_id':'Q-P02','value':{'status':'active','page_relation':'same_target','pending_issue':'none_reported','plan':'套餐甲','billing_channel':'google'}}],source='synthetic:correction')
  old_episode=s['subscription_review']['episode_id'];s=f.report_subscription_conflict(s,source='synthetic:page-2')
  self.assertNotEqual(s['subscription_review']['episode_id'],old_episode)
  n=f.record_fact(s,'Q-P02',None,state_name='declined',source='synthetic:decline-new-episode');a=f.assessment(n)
  TRACE['episode-control']={'before':s,'after':n,'assessment':a}
  self.assertEqual(n['subscription_review']['status'],'unresolved');self.assertTrue(n['context']['subscription_conflict']);self.assertIsNone(n['subscription_review']['detail'])
  self.assertEqual(a['G2']['status'],'blocked');self.assertEqual(a['G3']['status'],'blocked');self.assertIsNone(f.next_question(n))
for missing in ['current_plan','current_channel']:
 for outcome in ['declined','unknown','deferred']:
  def test(self,m=missing,o=outcome):self.terminal(m,o)
  setattr(TerminalRetention,'test_'+missing+'_'+outcome,test)
