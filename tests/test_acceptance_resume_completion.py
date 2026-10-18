"""Original T16 composed offline replay. No payment or native-device action.
Host must report completion honestly, identify interruption, retain private
recovery metadata and obtain fresh operation approval. Callbacks are fixtures.
"""
from copy import deepcopy
from contextlib import ExitStack
import builtins
import socket
import subprocess
import importlib.util
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1])).resolve()
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import interview_flow as f
import cleanup_transactions as c
FIXTURE = json.loads((ROOT / 'tests/fixtures/acceptance-routes-rebuild.json').read_text(encoding='utf-8'))
OLD = '2026-10-18T04:00:00Z'
NOW = '2026-10-18T08:00:00Z'
TRACE = {}

def ready():
    s = f.set_context(f.new_state('resume-device', 'resume-account', task_id='resume-task'), task='environment')
    with patch.object(f, '_now', return_value=OLD):
        s = f.record_facts(s, FIXTURE['common_answers'], source='synthetic:original')
        s = f.record_fact(s, 'Q-C05', 'vm', source='synthetic:original')
        s = f.record_facts(s, FIXTURE['route_answers']['vm'], source='synthetic:original')
    return s

def view(s):
    return {'state': deepcopy(s), 'question': f.next_question(s),
            'review': f.resume_review_prompt(s), 'assessment': f.assessment(s)}

class ResumeCompletionTests(unittest.TestCase):
    def setUp(self):
        if self._testMethodName != "test_partial_cleanup_resume_observes_then_restores_without_redeletion":
            stack = self.enterContext(ExitStack())
            for obj, name in ((builtins,"open"),(os,"open"),(socket,"socket"),(subprocess,"Popen")):
                stack.enter_context(patch.object(obj,name,side_effect=AssertionError("Pure replay attempted external I/O")))

    def test_completed_purchase_save_resume_changed_environment(self):
        pending = f.set_context(ready(), task='subscription_preparation')
        pending = f.record_fact(pending, 'Q-J01', 'first_subscription', source='synthetic:before-purchase', observed_at=OLD)
        pending = f.record_fact(pending, 'Q-C08', 'Pro', source='synthetic:selected-plan', observed_at=OLD)
        self.assertEqual(pending['current_subscription']['status'], 'none_reported')
        self.assertEqual(pending['purchase_intent'], 'subscription_preparation')
        s = f.complete_purchase(pending, source='synthetic:reported-completion', observed_at=OLD)
        TRACE['before_reported_completion'] = view(pending)
        self.assertEqual(s['current_subscription']['status'], 'active_reported')
        self.assertEqual(s['purchase_intent'], 'completed')
        self.assertEqual(s['payment_intent'], 'none')
        s = f.set_context(s, paused=True)
        original = deepcopy(s)
        with self.assertRaises(f.InterviewError):
            f.dumps_state(s)
        serialized = f.dumps_state(s, host_opt_in=True)
        self.assertEqual(s, original)
        loaded = f.loads_state(serialized)
        self.assertTrue(loaded['context']['paused'])
        self.assertTrue(all(v is False for v in loaded['persistence_consent'].values()))
        with self.assertRaises(f.InterviewError):
            f.set_context(loaded, paused=False)
        resumed = f.resume_interview(loaded, resume_id='interruption-a')
        self.assertEqual(resumed['facts'], loaded['facts'])
        self.assertEqual(resumed['context']['route'], 'vm')
        self.assertIsNone(f.next_question(resumed))
        self.assertEqual(f.assessment(resumed)['G2']['status'], 'blocked')
        self.assertIn('Q-V04', f.resume_review_prompt(resumed)['scope_keys'])
        changed = f.record_resume_review(resumed, resume_id='interruption-a', response='changed',
                    changed_keys=['Q-V04'], source='synthetic:current-review', reported_at=NOW)
        self.assertEqual(changed['facts']['Q-V04']['state'], 'stale')
        for key in resumed['facts']:
            if key != 'Q-V04':
                self.assertEqual(changed['facts'][key], resumed['facts'][key])
        self.assertEqual(changed['facts']['Q-V04']['observed_at'], OLD)
        with patch.object(f, '_now', return_value=NOW):
            refreshed = f.record_fact(changed, 'Q-V04', 'changed synthetic isolated network', source='synthetic:current')
        retry = f.record_resume_review(refreshed, resume_id='interruption-a', response='changed',
                    changed_keys=['Q-V04'], source='synthetic:current-review', reported_at=NOW)
        self.assertEqual(retry, refreshed)
        reloaded = f.loads_state(f.dumps_state(retry, host_opt_in=True))
        for state in (loaded, resumed, changed, refreshed, reloaded):
            self.assertEqual(state['purchase_intent'], 'completed')
            self.assertEqual(state['payment_intent'], 'none')
            self.assertTrue(state['context']['purchase_completed'])
            self.assertEqual(state['current_subscription'], s['current_subscription'])
            self.assertEqual(f.assessment(state)['G3']['status'], 'blocked')
            self.assertFalse(any(q['id'].startswith(('Q-P', 'Q-A')) for q in f.applicable_questions(state)))
        TRACE['purchase_resume'] = {k: view(v) for k,v in [('saved',loaded),('resumed',resumed),('changed',changed),('refreshed',refreshed),('reloaded',reloaded)]}

    def test_secret_and_unapproved_export_rejected(self):
        s = ready()
        for secret in ('sk-ant-' + 'x'*32, 'Bearer ' + 'x'*40, '4111111111111111'):
            with self.subTest(kind=secret[:3]):
                bad = deepcopy(s)
                bad['facts']['Q-V04']['value'] = secret
                with self.assertRaises(f.InterviewError):
                    f.dumps_state(bad, host_opt_in=True)
                with self.assertRaises(f.InterviewError):
                    f.loads_state(json.dumps(bad))
        for scope in ('public_export', 'unrecognized'):
            with self.assertRaises(f.InterviewError):
                f.dumps_state(s, host_opt_in=True, scope=scope)
        self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)

    def test_unknown_or_target_change_cannot_clear_resume(self):
        for response in ('unknown','declined','deferred','target_changed'):
            s = f.resume_interview(ready(), resume_id='interruption-a')
            s = f.record_resume_review(s, resume_id='interruption-a', response=response,
                    source='synthetic:current-review', reported_at=NOW)
            s = f.complete_purchase(s, source='synthetic:reported-completion', observed_at=NOW)
            self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
            self.assertEqual(f.assessment(s)['G3']['status'], 'blocked')
            self.assertEqual(s['resume_review']['response'], response)

    @unittest.skipUnless(os.name == 'posix', 'POSIX temporary fixture only')
    def test_partial_cleanup_resume_observes_then_restores_without_redeletion(self):
        with tempfile.TemporaryDirectory(prefix='guardian-t16-') as tmp:
            base = Path(tmp).resolve(); base.chmod(0o700)
            roots = [base/'app-one', base/'app-two']
            payloads = [b'synthetic history config extensions', b'synthetic desktop data']
            for path, data in zip(roots,payloads):
                path.write_bytes(data); path.chmod(0o600)
            protected = base/'protected'; protected.mkdir(mode=0o700)
            keep = protected/'source'; keep.write_bytes(b'untouched source')
            backup = base/'independent-backup'; backup.mkdir(mode=0o700)
            for i,data in enumerate(payloads):
                (backup/str(i)).write_bytes(data)
                self.assertEqual((backup/str(i)).read_bytes(),data)
            q = base/'quarantine'; q.mkdir(mode=0o700)
            target = 'resume-device'
            host_calls, approvals, moves = [], [], []
            def host(t,d):
                self.assertEqual(t,target); self.assertRegex(d,r'^[0-9a-f]{64}$')
                host_calls.append((t,d)); return c.HOST_OK
            plan = c.plan([{'root_ref':'root-'+str(i),'path':str(p),'data_kind':'cli_app_data'} for i,p in enumerate(roots)], [str(protected),str(backup)],str(q),target,host_check=host)
            def authorize(document, operation):
                def callback(op,digest,t):
                    self.assertEqual((op,digest,t),(operation,document.digest(),target))
                    approvals.append(op); return True
                return callback
            rename = c.os.rename
            def watched(*args,**kwargs):
                moves.append((args[0],args[1])); return rename(*args,**kwargs)
            with patch.object(c.os,'rename',side_effect=watched):
                with self.assertRaises(c.CleanupError) as caught:
                    c.quarantine(plan,host_check=host,authorize=authorize(plan,'quarantine'),exclusive_access=True,
                                 cancelled=lambda: not all(p.exists() for p in roots))
                error = caught.exception
                self.assertEqual(error.moved_count,1); self.assertEqual(len(moves),1)
                loaded = c.load_manifest(str(q/error.recovery_id/'manifest.json'),plan.digest(),target)
                partial = c.reconcile(loaded,error.recovery_id,host_check=host)
                self.assertEqual(partial.preview()['state'],'partial')
                self.assertEqual(partial.preview()['quarantined_count'],1)
                self.assertEqual(len(moves),1)
                # A retry of the original operation is rejected before another move.
                with self.assertRaises(c.CleanupError):
                    c.quarantine(loaded,host_check=host,authorize=authorize(loaded,'quarantine'),exclusive_access=True)
                self.assertEqual(len(moves),1)
                # Loading/reconciling does not restore authorization.
                with self.assertRaises(c.CleanupError):
                    c.restore(partial,host_check=host,exclusive_access=True)
                self.assertEqual(len(moves),1)
                restored = c.restore(partial,host_check=host,authorize=authorize(partial,'restore_cleanup'),exclusive_access=True)
                self.assertEqual(restored.preview()['state'],'restored'); self.assertEqual(len(moves),2)
                for receipt in (partial,restored):
                    with self.assertRaises(c.CleanupError):
                        c.restore(receipt,host_check=host,authorize=authorize(receipt,'restore_cleanup'),exclusive_access=True)
                    self.assertEqual(len(moves),2)
                with self.assertRaises(c.CleanupError):
                    c.quarantine(loaded,host_check=host,authorize=authorize(loaded,'quarantine'),exclusive_access=True)
                self.assertEqual(len(moves),2)
            for path,data in zip(roots,payloads): self.assertEqual(path.read_bytes(),data)
            self.assertEqual(keep.read_bytes(),b'untouched source')
            for i,data in enumerate(payloads): self.assertEqual((backup/str(i)).read_bytes(),data)
            final = c.reconcile(loaded,error.recovery_id,host_check=host)
            self.assertEqual(final.preview()['state'],'restored')
            TRACE['cleanup_resume']={'initial_moves':1,'final_moves':len(moves),'quarantined_count_at_resume':1,
                'final_state':'restored','protected_unchanged':True,'payloads_restored':True,
                'missing_approval_rejected':True,'original_operation_retries_rejected':True,
                'stale_restore_rejected':True,'native_acceptance':final.preview()['native_acceptance'],
                'permanent_purge':final.preview()['permanent_purge'],'approval_operations':approvals}

if __name__ == '__main__':
    replay = '--replay' in sys.argv
    if replay: sys.argv.remove('--replay')
    result = unittest.TextTestRunner(verbosity=2).run(unittest.defaultTestLoader.loadTestsFromTestCase(ResumeCompletionTests))
    if replay: print(json.dumps(TRACE,ensure_ascii=False,sort_keys=True,indent=2))
    sys.exit(not result.wasSuccessful())
