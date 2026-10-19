"""C5 dispatcher tests using only exclusively owned disposable data."""
import copy
import hashlib
import io
import json
import os
from pathlib import Path
import sys
import tempfile
import unittest
from unittest.mock import patch
import subprocess
import shutil

SCRIPTS = Path(__file__).resolve().parents[1]/'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import cleanup_cli as cli
from cleanup_fixture_host import FixtureHost
from environment_entry_fixture import local_entry

@unittest.skipUnless(os.name == 'posix', 'POSIX synthetic fixture only')
class CleanupCLITests(unittest.TestCase):
    def setUp(self):
        self.host=FixtureHost();self.addCleanup(self.host.close)
        self.base=self.host.base
        self.scope=copy.deepcopy(self.host.scope)
        self.entry=local_entry(self.scope['target_ref'])
        self.scopefile=self.base/'scope.json';self.save(self.scopefile,self.scope)
        self.planfile=self.base/'plan.json';self.receiptfile=self.base/'receipt.json'

    def save(self,path,doc):
        path.write_text(json.dumps(doc),encoding="utf-8");path.chmod(0o600)

    def run_cli(self,args,host=True):
        out=io.StringIO()
        entry=self.entry if args[0] in ('plan','quarantine') else None
        code=cli.main(args,host=self.host if host else None,stdout=out,entry_request=entry)
        result=json.loads(out.getvalue())
        self.assertNotIn(str(self.base),out.getvalue())
        self.assertNotIn('synthetic',out.getvalue())
        return code,result

    def planned(self):
        code,result=self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])
        self.assertEqual(code,0,result);return result['document_digest']

    def quarantined(self):
        digest=self.planned()
        code,result=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        self.assertEqual(code,0,result);return digest,result

    def test_missing_host_blocks_before_selected_root_access(self):
        code,result=self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)],host=False)
        self.assertEqual(result['code'],'HOST_ADAPTER_UNAVAILABLE')
        self.assertFalse(self.planfile.exists());self.assertTrue((self.base/'app').exists())

    def test_validate_and_capabilities_are_nonmutating(self):
        self.assertEqual(self.run_cli(['validate-scope','--scope',str(self.scopefile)],host=False)[0],0)
        self.assertEqual(self.run_cli(['capabilities'],host=False)[1]['native_acceptance'],'not_run')
        self.assertFalse(self.planfile.exists())

    def test_real_roundtrip_and_retained_plan_reconcile(self):
        digest,q=self.quarantined();self.assertFalse((self.base/'app').exists())
        code,r=self.run_cli(['reconcile','--plan-file',str(self.planfile),'--expected-plan-digest',digest,
                             '--receipt-output',str(self.receiptfile)])
        self.assertEqual(code,0,r)
        code,r=self.run_cli(['restore','--receipt-file',str(self.receiptfile),'--expected-receipt-digest',r['document_digest']])
        self.assertEqual(code,0,r);self.assertEqual((self.base/'app/data').read_bytes(),b'synthetic')
        self.assertEqual((self.base/'backup/data').read_bytes(),b'synthetic')
        self.assertEqual((self.base/'protected/keep').read_bytes(),b'protected')
        self.assertTrue(r['quarantine_records_retained']);self.assertTrue(r['independent_backup_retained'])
        ops={e[1] for e in self.host.events if e[0]=='approve'}
        self.assertIn('quarantine',ops);self.assertIn('restore_cleanup',ops)

    def test_wrong_digest_and_denied_approval_do_not_move(self):
        digest=self.planned()
        self.assertNotEqual(self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest','0'*64])[0],0)
        self.host.denied.add('quarantine')
        self.assertNotEqual(self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])[0],0)
        self.assertTrue((self.base/'app').exists())

    def test_no_overwrite_plan_and_bad_manifest(self):
        self.planned();before=self.planfile.read_bytes()
        self.assertNotEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[0],0)
        self.assertEqual(before,self.planfile.read_bytes())
        bad=copy.deepcopy(self.scope);bad['ownership_verified']=True;self.save(self.scopefile,bad)
        self.assertNotEqual(self.run_cli(['validate-scope','--scope',str(self.scopefile)],host=False)[0],0)

    def test_host_active_blocks(self):
        self.host.active=True
        self.assertNotEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[0],0)
        self.assertFalse(self.planfile.exists())

    def test_exclusion_exit_failure_retains_actual_move_outcome(self):
        from contextlib import contextmanager
        @contextmanager
        def broken_exit(*args):
            yield
            raise OSError('private-host-error')
        digest=self.planned(); self.host.exclusive=broken_exit
        code,result=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        self.assertNotEqual(code,0)
        self.assertFalse((self.base/'app').exists())
        self.assertEqual(result['code'],'HOST_EXCLUSION_FAILED')
        self.assertEqual(result['stage'],'after_move_verified')
        self.assertEqual(result['moved_count'],1)
        self.assertIsNotNone(result['recovery_id'])

    def test_denied_read_hash_never_scans(self):
        self.host.denied.add('read_hash_scope')
        with patch.object(cli.core,'plan',side_effect=AssertionError('must not scan')):
            self.assertEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[1]['code'],'AUTHORIZATION_REQUIRED')

    def test_approvals_bind_wrapper_and_private_destination(self):
        digest=self.planned()
        events=[e for e in self.host.events if e[0]=='approve']
        self.assertEqual(events[0][1],'read_hash_scope')
        self.assertEqual(events[-1][1],'save_plan')
        self.assertNotEqual(events[-1][2],digest)
        self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        for event in self.host.events:
            if event[:2]==('approve','quarantine'):self.assertEqual(event[2],digest)

    def test_unknown_flags_duplicate_keys_public_files_and_links_rejected(self):
        self.assertNotEqual(self.run_cli(['capabilities','--yes'],host=False)[0],0)
        self.scopefile.write_text('{"schema_version":1,"schema_version":2}',encoding='utf-8')
        self.assertNotEqual(self.run_cli(['validate-scope','--scope',str(self.scopefile)],host=False)[0],0)
        self.save(self.scopefile,self.scope); self.scopefile.chmod(0o644)
        self.assertNotEqual(self.run_cli(['validate-scope','--scope',str(self.scopefile)],host=False)[0],0)
        self.scopefile.chmod(0o600); link=self.base/'link.json';link.symlink_to(self.scopefile)
        self.assertNotEqual(self.run_cli(['validate-scope','--scope',str(link)],host=False)[0],0)

    def test_output_under_selected_or_protected_tree_is_rejected(self):
        for path in (self.base/'app/plan',self.base/'backup/plan',self.base/'quarantine/plan'):
            self.assertNotEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(path)])[0],0)
            self.assertFalse(path.exists())

    def test_changed_binding_with_old_digest_rejected(self):
        digest=self.planned(); document=json.loads(self.planfile.read_text(encoding="utf-8"))
        document['bindings']['backup_ref']='different-backup';self.save(self.planfile,document)
        self.assertEqual(self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])[1]['code'],'DIGEST_MISMATCH')
        self.assertTrue((self.base/'app').exists())

    def test_cancel_and_callback_exception_are_fixed_and_nonmutating(self):
        self.host.cancelled=lambda:True
        self.assertEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[1]['code'],'CANCELLED')
        self.host.cancelled=lambda:False
        self.host.approve=lambda *a: (_ for _ in ()).throw(RuntimeError('private-path-secret'))
        self.assertEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[1]['code'],'HOST_CALLBACK_FAILED')
        self.assertFalse(self.planfile.exists())

    def test_restore_denial_and_later_target_never_overwrite(self):
        digest,_=self.quarantined()
        code,r=self.run_cli(['reconcile','--plan-file',str(self.planfile),'--expected-plan-digest',digest,'--receipt-output',str(self.receiptfile)])
        self.assertEqual(code,0)
        args=['restore','--receipt-file',str(self.receiptfile),'--expected-receipt-digest',r['document_digest']]
        self.host.denied.add('restore_cleanup');self.assertNotEqual(self.run_cli(args)[0],0)
        self.host.denied.clear();(self.base/'app').mkdir(mode=0o700);(self.base/'app/new').write_bytes(b'later')
        self.assertNotEqual(self.run_cli(args)[0],0);self.assertEqual((self.base/'app/new').read_bytes(),b'later')

    def test_journal_failure_can_reconcile_and_restore_without_requarantine(self):
        digest=self.planned(); real=cli.core._journal
        def journal(fd,name,value):
            if name.endswith('.done.json'):raise OSError('private-journal-error')
            return real(fd,name,value)
        with patch.object(cli.core,'_journal',journal):
            code,r=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        self.assertNotEqual(code,0);self.assertEqual(r['moved_count'],1);self.assertIsNotNone(r['recovery_id'])
        code,r=self.run_cli(['reconcile','--plan-file',str(self.planfile),'--expected-plan-digest',digest,'--receipt-output',str(self.receiptfile)])
        self.assertEqual(code,0)
        self.assertEqual(self.run_cli(['restore','--receipt-file',str(self.receiptfile),'--expected-receipt-digest',r['document_digest']])[0],0)
        self.assertEqual((self.base/'app/data').read_bytes(),b'synthetic')

    def test_wrapper_capacity_is_reserved_before_batch_write(self):
        digest=self.planned()
        with patch.object(cli,'_reserve_wrapper',side_effect=cli.CLIError('DOCUMENT_TOO_LARGE')):
            code,r=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        self.assertNotEqual(code,0);self.assertFalse(list((self.base/'quarantine').iterdir()))

    def test_isolated_file_path_import_has_no_optional_yaml_or_sys_path_change(self):
        code="import importlib.util,sys; before=list(sys.path); s=importlib.util.spec_from_file_location('isolated_cleanup_cli',sys.argv[1]);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);assert before==sys.path;assert 'yaml' not in sys.modules;raise SystemExit(m.main(['capabilities']))"
        p=subprocess.run([sys.executable,'-I','-S','-B','-c',code,str(SCRIPTS/'cleanup_cli.py')],cwd=self.base,capture_output=True,text=True,timeout=10)
        self.assertEqual(p.returncode,0,p.stderr);self.assertFalse(json.loads(p.stdout)['host_adapter_available'])

    def test_real_wrapper_overhead_boundary_exceeds_core_only_budget(self):
        self.planned();doc=json.loads(self.planfile.read_text(encoding="utf-8"))
        plan=doc['material'];bindings=doc['bindings']
        # Search the actual encoder boundary using a reduced synthetic budget.
        low,high=1,cli.core.MAX_DOCUMENT
        while low<high:
            mid=(low+high)//2
            with patch.object(cli.core,'MAX_DOCUMENT',mid):
                try:cli.core._reserve(plan)
                except cli.core.CleanupError:low=mid+1
                else:high=mid
        with patch.object(cli.core,'MAX_DOCUMENT',low):
            cli.core._reserve(plan)
            with self.assertRaises(cli.core.CleanupError):cli._reserve_wrapper(plan,bindings)
        self.assertTrue((self.base/'app').exists())
        self.assertFalse(list((self.base/'quarantine').iterdir()))

    def test_fixture_rejects_outside_root_before_selected_scan(self):
        with tempfile.TemporaryDirectory(prefix='guardian-unselected-') as directory:
            outside=Path(directory).resolve();(outside/'keep').write_bytes(b'outside')
            changed=copy.deepcopy(self.scope);changed['roots'][0]['path']=str(outside)
            self.save(self.scopefile,changed)
            with patch.object(cli.core,'_scan',side_effect=AssertionError('outside scan forbidden')):
                code,r=self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])
            self.assertNotEqual(code,0);self.assertEqual(r['code'],'HOST_CALLBACK_FAILED')
            self.assertEqual((outside/'keep').read_bytes(),b'outside')
            self.assertFalse(self.planfile.exists())

    def test_fixture_rejects_changed_independent_backup(self):
        (self.base/'backup/data').write_bytes(b'changed')
        self.assertNotEqual(self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])[0],0)
        self.assertTrue((self.base/'app').exists());self.assertFalse(self.planfile.exists())

    def test_detached_actual_dispatcher_roundtrip_under_isolated_python(self):
        installed=self.base/'installed';installed.mkdir(mode=0o700)
        for name in ('cleanup_cli.py','cleanup_transactions.py','transactions.py','environment_entry.py'):
            shutil.copyfile(SCRIPTS/name,installed/name)
        helper=Path(__file__).with_name('cleanup_fixture_host.py')
        script=self.base/'runner.py'
        script.write_text("""import importlib.util,sys,json,io
from pathlib import Path
before=list(sys.path)
def load(name,path):
 s=importlib.util.spec_from_file_location(name,path);m=importlib.util.module_from_spec(s);s.loader.exec_module(m);return m
cli=load('detached_cli',Path(sys.argv[1])/'cleanup_cli.py')
fixtures=load('fixtures',sys.argv[2]);host=fixtures.FixtureHost()
entry_fixtures=load('entry_fixtures',Path(sys.argv[2]).with_name('environment_entry_fixture.py'))
entry=entry_fixtures.local_entry(host.scope['target_ref'])
assert before==sys.path and 'yaml' not in sys.modules
try:
 p=host.base;scope=p/'scope.json';scope.write_text(json.dumps(host.scope),encoding="utf-8");scope.chmod(0o600)
 def run(args):
  current_entry=entry if args[0] in ('plan','quarantine') else None
  out=io.StringIO();status=cli.main(args,host=host,stdout=out,entry_request=current_entry);assert status==0,out.getvalue();return json.loads(out.getvalue())
 plan=run(['plan','--scope',str(scope),'--plan-output',str(p/'plan.json')])
 common=['--plan-file',str(p/'plan.json'),'--expected-plan-digest',plan['document_digest']]
 q=run(['quarantine']+common);assert not (p/'app').exists()
 r=run(['reconcile']+common+['--receipt-output',str(p/'receipt.json')])
 result=run(['restore','--receipt-file',str(p/'receipt.json'),'--expected-receipt-digest',r['document_digest']])
 assert (p/'app/data').read_bytes()==(p/'backup/data').read_bytes()==b'synthetic'
 assert (p/'protected/keep').read_bytes()==b'protected'
 assert result['state']=='restored' and result['native_acceptance']=='not_run'
 print('detached roundtrip passed')
finally:host.close()
""",encoding="utf-8")
        p=subprocess.run([sys.executable,'-I','-S','-B',str(script),str(installed),str(helper)],cwd=installed,capture_output=True,text=True,timeout=15)
        self.assertEqual(p.returncode,0,p.stderr+p.stdout)
        self.assertEqual(p.stdout.strip(),'detached roundtrip passed')

    def test_host_context_errors_are_sanitized_with_true_progress(self):
        from contextlib import contextmanager
        for error in (cli.CLIError,cli.core.CleanupError):
            with self.subTest(error=error.__name__):
                @contextmanager
                def broken_exit(*args):
                    yield
                    raise error('private-host-secret')
                digest=self.planned();self.host.exclusive=broken_exit
                code,r=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
                self.assertEqual(r['code'],'HOST_EXCLUSION_FAILED');self.assertEqual(r['moved_count'],1)
                self.assertEqual(r['stage'],'after_move_verified');self.assertIsNotNone(r['recovery_id'])
                # A new fixture is needed because the first payload remains quarantined.
                self.host=FixtureHost();self.addCleanup(self.host.close);self.base=self.host.base
                self.scope=copy.deepcopy(self.host.scope);self.scopefile=self.base/'scope.json';self.save(self.scopefile,self.scope)
                self.planfile=self.base/'plan.json';self.receiptfile=self.base/'receipt.json'

    def test_fixture_rejects_unbacked_file_and_root_replacement(self):
        extra=self.base/'app/extra';extra.write_bytes(b'unbacked')
        args=['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)]
        self.assertNotEqual(self.run_cli(args)[0],0);self.assertFalse(self.planfile.exists())
        extra.unlink();(self.base/'app').rename(self.base/'prior-app')
        (self.base/'app').mkdir(mode=0o700);(self.base/'app/data').write_bytes(b'synthetic')
        self.assertNotEqual(self.run_cli(args)[0],0);self.assertFalse(self.planfile.exists())

    def test_host_interface_property_failure_is_fixed(self):
        class BrokenHost:
            @property
            def verify(self):raise RuntimeError('private-property-sentinel')
        self.host=BrokenHost()
        code,r=self.run_cli(['plan','--scope',str(self.scopefile),'--plan-output',str(self.planfile)])
        self.assertEqual(code,2);self.assertEqual(r['code'],'INVALID_HOST_ADAPTER')
        self.assertFalse(self.planfile.exists())

    def test_save_checks_cancellation_before_write_and_reports_retained_record(self):
        identity=None
        with cli.tx._parent(str(self.planfile)) as (fd,name):identity=cli.core._directory_meta(fd,private=True)
        class Budget:
            def __init__(self,stop):self.count=0;self.stop=stop
            def check(self):
                self.count+=1
                if self.count>=self.stop:raise cli.core.CleanupError('CANCELLED')
        with self.assertRaises(cli.core.CleanupError):cli._save(str(self.planfile),{},identity,Budget(1))
        self.assertFalse(self.planfile.exists())
        with self.assertRaises(cli.core.CleanupError):cli._save(str(self.planfile),{},identity,Budget(2))
        self.assertFalse(self.planfile.exists())
        with self.assertRaises(cli.CLIError) as caught:cli._save(str(self.planfile),{},identity,Budget(3))
        self.assertTrue(caught.exception.private_record_may_exist)
        self.assertEqual(str(caught.exception),'CANCELLED');self.assertTrue(self.planfile.exists())
        self.assertTrue((self.base/'app').exists())

    def test_exclusive_exit_deadline_reports_actual_completed_move(self):
        from contextlib import contextmanager
        digest=self.planned();clock=[100.0]
        @contextmanager
        def late_exit(*args):
            yield
            clock[0]=140.0
        self.host.exclusive=late_exit
        with patch.object(cli.core.time,'monotonic',lambda:clock[0]):
            code,r=self.run_cli(['quarantine','--plan-file',str(self.planfile),'--expected-plan-digest',digest])
        self.assertEqual(code,2);self.assertEqual(r['code'],'DEADLINE_EXCEEDED')
        self.assertEqual(r['moved_count'],1);self.assertEqual(r['stage'],'after_move_verified')
        self.assertIsNotNone(r['recovery_id']);self.assertFalse((self.base/'app').exists())

if __name__=='__main__':unittest.main()
