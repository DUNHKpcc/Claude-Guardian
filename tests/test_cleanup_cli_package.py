"""Installed C5 CLI and true two-interpreter recovery on parent-owned fixtures."""
import hashlib
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
import zipfile
from environment_entry_fixture import local_entry

ROOT = Path(__file__).resolve().parents[1]

# Test-only host code. Never shipped or importable through a production CLI flag.
RUNNER = r'''
import contextlib, fcntl, hashlib, importlib.util, json, os, stat, sys, time
from pathlib import Path
installed, baseline_path, expected_baseline, phase, recovery_id, retained_plan_digest = sys.argv[1:]
before = list(sys.path)
spec = importlib.util.spec_from_file_location('detached_cleanup', Path(installed)/'scripts/cleanup_cli.py')
cli = importlib.util.module_from_spec(spec); spec.loader.exec_module(cli)
assert sys.path == before and 'yaml' not in sys.modules
raw = Path(baseline_path).read_bytes()
assert hashlib.sha256(raw).hexdigest() == expected_baseline
baseline = json.loads(raw)
base = Path(baseline['base'])
assert base.is_absolute() and base.name.startswith('guardian-two-process-')
assert 0 <= time.time()-baseline['created_at'] < 60
assert baseline['uid'] == os.geteuid() and baseline['gid'] == os.getegid()
assert phase in ('quarantine','recover')

def identity(path):
 s = path.lstat()
 assert not stat.S_ISLNK(s.st_mode)
 return [s.st_dev,s.st_ino,s.st_mode,s.st_uid,s.st_gid]

def canonical(value):
 return json.dumps(value,sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()

scope = baseline['scope']
bindings = {k:scope[k] for k in ('backup_ref','host_context_ref')}
expected_scope = hashlib.sha256(canonical({k:scope[k] for k in (
 'roots','protected_paths','quarantine_directory','target_ref','mode')})).hexdigest()
assert scope['roots'] == [{'root_ref':'fixture-app','path':str(base/'app'),'data_kind':'cli_app_data'}]
assert scope['protected_paths'] == [str(base/'protected'),str(base/'backup')]
assert scope['quarantine_directory'] == str(base/'quarantine')
allowed = {'read_hash_scope','save_plan','quarantine'} if phase=='quarantine' else {'read_reconcile','save_receipt','restore_cleanup'}
events = []

class Host:
 def verify(self,target,digest,current_bindings):
  assert target==scope['target_ref'] and digest==expected_scope and current_bindings==bindings
  assert 0 <= time.time()-baseline['created_at'] < 60
  for name in ('','protected','backup','quarantine','writer-lock'):
   assert identity(base/name)==baseline['identities'][name]
  assert (base/'protected/keep').read_bytes()==b'protected'
  assert (base/'backup/data').read_bytes()==b'fixture-data'
  selected=base/'app'
  if not selected.exists():
   if phase=='recover':
    assert len(recovery_id)==32 and all(c in '0123456789abcdef' for c in recovery_id)
    selected=base/'quarantine'/recovery_id/'root-0000'
   else:
    batches=list((base/'quarantine').iterdir());assert len(batches)==1
    selected=batches[0]/'root-0000'
  assert identity(selected)==baseline['identities']['app']
  assert {p.name for p in selected.iterdir()}=={'data'}
  assert identity(selected/'data')==baseline['identities']['app/data']
  assert (selected/'data').read_bytes()==(base/'backup/data').read_bytes()==b'fixture-data'
  events.append('fresh_live_verification')
  return 'verified_inactive_claude_data'
 def approve(self,operation,digest,target,review):
  # Parent authorizes only its own synthetic fixture and this child's stage.
  assert operation in allowed and target==scope['target_ref']
  assert hashlib.sha256(canonical(review)).hexdigest()==digest
  doc=review
  if operation in ('save_plan','save_receipt'):
   assert doc['output_path']==str(base/('plan.json' if operation=='save_plan' else 'receipt.json'))
   doc=doc['document']
  if operation=='read_hash_scope':assert doc==scope
  else:
   assert doc['bindings']==bindings
   plan=doc['material'] if doc['kind']=='plan' else doc['material']['plan']
   assert plan['scope_digest']==expected_scope
   assert [{k:r[k] for k in ('root_ref','path','data_kind')} for r in plan['roots']]==scope['roots']
  events.append(operation)
  return True
 @contextlib.contextmanager
 def exclusive(self,target,digest,current_bindings):
  self.verify(target,digest,current_bindings)
  fd=os.open(base/'writer-lock',os.O_RDONLY|os.O_NOFOLLOW)
  try:
   fcntl.flock(fd,fcntl.LOCK_EX|fcntl.LOCK_NB)
   yield
  finally:
   fcntl.flock(fd,fcntl.LOCK_UN);os.close(fd)
 def cancelled(self):return False

import io
host=Host()
def run(args, *, entry_request=None):
 out=io.StringIO();code=cli.main(args,host=host,stdout=out,entry_request=entry_request)
 assert code==0,out.getvalue()
 assert str(base) not in out.getvalue()
 return json.loads(out.getvalue())
if phase=='quarantine':
 p=run(['plan','--scope',str(base/'scope.json'),'--plan-output',str(base/'plan.json')],entry_request=baseline['entry_request'])
 q=run(['quarantine','--plan-file',str(base/'plan.json'),'--expected-plan-digest',p['document_digest']],entry_request=baseline['entry_request'])
 assert not (base/'app').exists()
 assert 'restore_cleanup' not in events
 result={'phase':phase,'pid':os.getpid(),'plan_digest':p['document_digest'],'recovery_id':q['recovery_id'],'state':q['state']}
else:
 # Digest comes from parent-checked retained bytes, not a restored permission.
 digest=hashlib.sha256(canonical(json.loads((base/'plan.json').read_text(encoding='utf-8')))).hexdigest()
 assert digest==retained_plan_digest
 r=run(['reconcile','--plan-file',str(base/'plan.json'),'--expected-plan-digest',digest,'--receipt-output',str(base/'receipt.json')])
 q=run(['restore','--receipt-file',str(base/'receipt.json'),'--expected-receipt-digest',r['document_digest']])
 assert (base/'app/data').read_bytes()==(base/'backup/data').read_bytes()==b'fixture-data'
 assert (base/'protected/keep').read_bytes()==b'protected'
 assert 'quarantine' not in events and 'restore_cleanup' in events
 result={'phase':phase,'pid':os.getpid(),'state':q['state'],'backup_retained':True,'quarantine_records_retained':(base/'quarantine'/recovery_id/'manifest.json').is_file()}
result['native_acceptance']='not_run';result['verification_calls']=events.count('fresh_live_verification')
print(json.dumps(result,sort_keys=True))
'''


class CleanupCLIPackageTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.tmp = tempfile.TemporaryDirectory(prefix='guardian-cli-package-')
        cls.addClassCleanup(cls.tmp.cleanup)
        cls.root = Path(cls.tmp.name).resolve()
        archive = cls.root/'release.zip'
        subprocess.run([sys.executable,'-B',str(ROOT/'tools/package_skill.py'),'--output',str(archive)],
                       check=True,capture_output=True,timeout=30)
        with zipfile.ZipFile(archive) as z:
            cls.members = z.namelist()
            z.extractall(cls.root/'installed')
        cls.installed = cls.root/'installed/claude-guardian'
        cls.unrelated = cls.root/'unrelated';cls.unrelated.mkdir()

    def test_installed_default_process_has_no_host_authority(self):
        self.assertIn('claude-guardian/scripts/cleanup_cli.py',self.members)
        self.assertFalse(any('fixture_host' in n or n.startswith('tests/') for n in self.members))
        script = self.installed/'scripts/cleanup_cli.py'
        p = subprocess.run([sys.executable,'-I','-S','-B',str(script),'capabilities'],
                           cwd=self.unrelated,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr)
        self.assertFalse(json.loads(p.stdout)['host_adapter_available'])
        for args in (['plan','--scope','/absent/private-scope','--plan-output','/absent/output'],
                     ['quarantine','--plan-file','/absent/private-plan','--expected-plan-digest','0'*64],
                     ['reconcile','--plan-file','/absent/private-plan','--expected-plan-digest','0'*64,'--receipt-output','/absent/receipt'],
                     ['restore','--receipt-file','/absent/private-receipt','--expected-receipt-digest','0'*64]):
            with self.subTest(command=args[0]):
                p = subprocess.run([sys.executable,'-I','-S','-B',str(script)]+args,
                                   cwd=self.unrelated,capture_output=True,text=True,timeout=10)
                self.assertEqual(p.returncode,2,p.stderr)
                self.assertEqual(json.loads(p.stdout)['code'],'HOST_ADAPTER_UNAVAILABLE')
                self.assertEqual(p.stderr,'')
        self.assertEqual(list(self.unrelated.iterdir()),[])

    @unittest.skipUnless(os.name=='posix','Controlled POSIX fixture; not native Windows cleanup')
    def test_true_two_interpreter_fixture_recovery(self):
        with tempfile.TemporaryDirectory(prefix='guardian-two-process-') as directory:
            base=Path(directory).resolve();base.chmod(0o700)
            for name in ('app','backup','protected','quarantine'):(base/name).mkdir(mode=0o700)
            for name in ('app','backup'):
                (base/name/'data').write_bytes(b'fixture-data');(base/name/'data').chmod(0o600)
            (base/'protected/keep').write_bytes(b'protected');(base/'protected/keep').chmod(0o600)
            (base/'writer-lock').write_bytes(b'');(base/'writer-lock').chmod(0o600)
            scope={'schema_version':'guardian-cleanup-operator-scope/0.1','target_ref':'parent-owned-fixture',
                'mode':'C5-full-local-data','roots':[{'root_ref':'fixture-app','path':str(base/'app'),'data_kind':'cli_app_data'}],
                'protected_paths':[str(base/'protected'),str(base/'backup')],'quarantine_directory':str(base/'quarantine'),
                'backup_ref':'parent-created-backup','host_context_ref':'parent-created-context'}
            (base/'scope.json').write_text(json.dumps(scope),encoding='utf-8');(base/'scope.json').chmod(0o600)
            identities={}
            for name in ('','app','app/data','backup','protected','quarantine','writer-lock'):
                st=(base/name).lstat();identities[name]=[st.st_dev,st.st_ino,st.st_mode,st.st_uid,st.st_gid]
            import time
            baseline={'base':str(base),'scope':scope,'identities':identities,'created_at':time.time(),'uid':os.geteuid(),'gid':os.getegid(),
                      'entry_request':local_entry(scope['target_ref'])}
            raw=json.dumps(baseline,sort_keys=True).encode('utf-8')
            baseline_path=base/'parent-baseline.json';baseline_path.write_bytes(raw);baseline_path.chmod(0o600)
            script=base/'fixture-runner.py';script.write_text(RUNNER,encoding='utf-8');script.chmod(0o600)
            prefix=[sys.executable,'-I','-S','-B',str(script),str(self.installed),str(baseline_path),hashlib.sha256(raw).hexdigest()]
            first=subprocess.run(prefix+['quarantine','unused','unused'],cwd=self.unrelated,capture_output=True,text=True,timeout=20)
            self.assertEqual(first.returncode,0,first.stdout+first.stderr)
            a=json.loads(first.stdout);self.assertEqual(a['state'],'quarantined');self.assertFalse((base/'app').exists())
            saved_plan=(base/'plan.json').read_bytes()
            plan_digest=hashlib.sha256(json.dumps(json.loads(saved_plan),sort_keys=True,separators=(',',':'),ensure_ascii=True).encode()).hexdigest()
            self.assertEqual(plan_digest,a['plan_digest'])
            second=subprocess.run(prefix+['recover',a['recovery_id'],a['plan_digest']],cwd=self.unrelated,capture_output=True,text=True,timeout=20)
            self.assertEqual(second.returncode,0,second.stdout+second.stderr)
            b=json.loads(second.stdout);self.assertNotEqual(a['pid'],b['pid'])
            self.assertEqual(b['state'],'restored');self.assertTrue(b['backup_retained']);self.assertTrue(b['quarantine_records_retained'])
            self.assertEqual(saved_plan,(base/'plan.json').read_bytes())
            self.assertEqual((base/'app/data').read_bytes(),b'fixture-data')
            self.assertEqual((base/'backup/data').read_bytes(),b'fixture-data')
            self.assertEqual((base/'protected/keep').read_bytes(),b'protected')
            for result in (a,b):
                self.assertGreater(result['verification_calls'],0);self.assertEqual(result['native_acceptance'],'not_run')


if __name__=='__main__':unittest.main()
