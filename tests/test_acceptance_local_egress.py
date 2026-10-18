"""T23: explicit local runtime with a VPS egress, offline host-normalized facts.
This is not natural-language parsing, remote installation or native evidence.
"""
from contextlib import ExitStack
from copy import deepcopy
import builtins
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest
from unittest.mock import patch
ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT',Path(__file__).resolve().parents[1])).resolve()
sys.path.insert(0,str(ROOT/'skills/claude-guardian/scripts'))
import interview_flow as f
TIME = '2026-10-18T08:00:00Z'
SOURCE = 'synthetic:local-code-vps-exit'
ANSWERS = [
 ('Q-J01','existing_subscriber'),('Q-C02','macos'),('Q-C01','local_code_only'),
 ('Q-OS03','synthetic_version'),('Q-C03','no_incident_reported'),('Q-C04','active'),
 ('Q-C06','official_login_reported'),('Q-C09','region_reported_not_verified'),
 ('Q-N01',{'kind':'proxy','egress_role':'vps_exit_only','egress_alias':'exit-a'}),
 ('Q-N02',{'code_runtime':'selected_local_device','proxy_client':'selected_local_device','egress':'exit-a','remote_workspace':'none'}),
 ('Q-N03','stable_exit_planned'),('Q-N04','no_other_workspace'),('Q-N06','no_management_reported'),
 ('Q-L01',{'client':'Code','installation':'reported_existing','version':'not_verified'}),
 ('Q-L04','local_projects_required'),('Q-C12','preserve_local_projects_and_settings'),
 ('Q-Z01','plan_only'),('Q-C10','direct_checks')]
TRACE={}

def base():
    s=f.set_context(f.new_state('local-device','account-a',task_id='local-task'),task='environment')
    with patch.object(f,'_now',return_value=TIME):
        s=f.record_facts(s,[{'question_id':q,'value':v} for q,v in ANSWERS],source=SOURCE)
    return s

def local():
    return f.record_fact(base(),'Q-C05','local',source=SOURCE,observed_at=TIME)

def capture(s):
    return {'state':deepcopy(s),'question':f.next_question(s),'assessment':f.assessment(s),
            'applicable_questions':f.applicable_questions(s)}

class LocalEgressTests(unittest.TestCase):
    def setUp(self):
        stack=self.enterContext(ExitStack())
        for obj,name in ((builtins,'open'),(os,'open'),(socket,'socket'),(subprocess,'Popen')):
            stack.enter_context(patch.object(obj,name,side_effect=AssertionError('Offline composition attempted external I/O')))

    def assert_local_closed(self,s):
        self.assertEqual(s['context']['route'],'local')
        self.assertEqual(s['context']['route_selection_basis'],'explicit_choice')
        req=f.applicable_questions(s)
        self.assertEqual([q['id'] for q in req if q['branch']=='local'],['Q-L01','Q-L04'])
        self.assertFalse(any(q['id'].startswith(('Q-S','Q-V','Q-P','Q-A','Q-G','Q-W')) for q in req))
        self.assertEqual(f.assessment(s)['G3'],{'status':'blocked','reason':'Interview answers are not specific action authorization; action and contact gates must be checked separately'})
        self.assertEqual(s['context']['contact_phase'],'PC0')
        self.assertEqual(s['payment_intent'],'none')
        self.assertTrue(all(v is False for v in s['persistence_consent'].values()))

    def test_complete_local_code_with_vps_egress(self):
        s=local(); self.assert_local_closed(s)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2'],{'status':'pass','conditional_plan_only':False})
        for q in ('Q-N01','Q-N02'):
            self.assertEqual(s['facts'][q]['value'],dict(ANSWERS)[q])
            self.assertEqual(s['facts'][q]['state'],'reported')
            self.assertEqual(s['facts'][q]['source'],SOURCE)
            self.assertEqual(s['facts'][q]['observed_at'],TIME)
        TRACE['local_code_exit']=capture(s)

    def test_egress_asset_does_not_silently_select_route(self):
        s=base()
        self.assertEqual(s['context']['route_selection_basis'],'default_proposal')
        self.assertEqual(f.next_question(s)['id'],'Q-C05')
        self.assertEqual(f.assessment(s)['G2']['status'],'blocked')
        self.assertFalse(any(q['id'].startswith(('Q-S','Q-V')) for q in f.applicable_questions(s)))
        TRACE['route_not_yet_selected']=capture(s)

    def test_saved_local_route_and_changed_exit_remain_local(self):
        s=local()
        with self.assertRaises(f.InterviewError): f.dumps_state(s)
        saved=f.loads_state(f.dumps_state(s,host_opt_in=True))
        self.assertEqual(saved,s)
        resumed=f.resume_interview(saved,resume_id='exit-review')
        self.assert_local_closed(resumed)
        self.assertIsNone(f.next_question(resumed))
        self.assertEqual(f.assessment(resumed)['G2']['status'],'blocked')
        changed=f.record_resume_review(resumed,resume_id='exit-review',response='changed',changed_keys=['Q-N01','Q-N02'],source='synthetic:current-exit-change',reported_at=TIME)
        self.assert_local_closed(changed)
        for q in ('Q-N01','Q-N02'): self.assertEqual(changed['facts'][q]['state'],'stale')
        for q in s['facts']:
            if q not in ('Q-N01','Q-N02'): self.assertEqual(changed['facts'][q],s['facts'][q])
        self.assertEqual(f.next_question(changed)['id'],'Q-N01')
        self.assertEqual(f.assessment(changed)['G2']['status'],'blocked')
        TRACE['changed_exit']=capture(changed)

    def test_incomplete_local_installation_does_not_offer_remote_setup(self):
        s=local(); del s['facts']['Q-L01']
        self.assert_local_closed(s)
        question=f.next_question(s)
        self.assertEqual(question['id'],'Q-L01')
        self.assertEqual(question['prompt'],'目标客户端安装了吗？用哪种方式安装、版本是什么？')
        self.assertEqual(f.assessment(s)['G2']['status'],'blocked')
        TRACE['missing_local_metadata']=capture(s)

if __name__=='__main__':
    replay='--replay' in sys.argv
    if replay: sys.argv.remove('--replay')
    result=unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(LocalEgressTests))
    if replay: print(json.dumps(TRACE,ensure_ascii=False,sort_keys=True,indent=2))
    sys.exit(not result.wasSuccessful())
