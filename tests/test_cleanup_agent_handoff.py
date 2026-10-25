"""Fixed informational C5 handoff; no actual host access or execution grant."""
import copy
import io
import json
from pathlib import Path
import sys
import subprocess
import tempfile
import zipfile
import unittest
from unittest.mock import patch
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT/'skills/claude-guardian/scripts'))
import agent_remediation as ar
import cleanup_cli as cli
EXPECTED={'capability':'c5_selected_root_quarantine_restore','entry_point':'cleanup_cli.main',
'invocation':'in_process_with_reviewed_live_host','core_module':'cleanup_transactions',
'operations':['plan','quarantine','reconcile','restore'],'selection_required':'C5-full-claude-data-reset',
'operator_mode':'C5-full-local-data','default_host':'unavailable','native_ownership_adapter':'unavailable',
'execution_authorized':False,'permanent_purge':'unsupported','documentation':'references/cleanup-cli-usage.md'}
def report(*codes):
 return {'schema_version':ar.INPUT_SCHEMA,'target_ref':'device-1','findings':[{'code':c} for c in codes]}
class CleanupHandoffTests(unittest.TestCase):
 def test_exact_metadata_has_no_execution_grant(self):
  with patch.object(cli,'main',side_effect=AssertionError('selector executed cleanup')):
   result=ar.select(report('CLEANUP_REQUESTED'),'device-1')
  item=result['actions'][0]
  self.assertEqual(item['host_handoff'],EXPECTED)
  self.assertEqual(item['kind'],'agent_investigation');self.assertIsNone(item['command_template'])
  self.assertFalse(item['target_mutation_supported']);self.assertEqual(result['authority'],'none')
  self.assertEqual(result['changes'],[]);self.assertEqual(result['completion'],'no_repair_performed')
  self.assertNotIn('requested_level',result)
 def test_untrusted_extra_fields_cannot_supply_handoff(self):
  baseline=ar.select(report('CLEANUP_REQUESTED'),'device-1')
  for member in ('host_handoff','authorization','host','operation','requested_level','scope','command'):
   obj=report('CLEANUP_REQUESTED');obj[member]={'private-sentinel':['quarantine',True]};before=copy.deepcopy(obj)
   self.assertEqual(ar.select(obj,'device-1'),baseline);self.assertEqual(obj,before)
   self.assertNotIn('private-sentinel',json.dumps(baseline))
 def test_projection_deep_copy(self):
  result=ar.select(report('CLEANUP_REQUESTED'),'device-1')
  result['actions'][0]['host_handoff']['operations'].append('purge')
  self.assertEqual(ar.select(report('CLEANUP_REQUESTED'),'device-1')['actions'][0]['host_handoff'],EXPECTED)
 def test_cancellation_incident_and_prerequisite_priority(self):
  self.assertEqual([a['action_id'] for a in ar.select(report('CLEANUP_REQUESTED','USER_CANCELLED'),'device-1')['actions']],['stop'])
  self.assertEqual([a['action_id'] for a in ar.select(report('INCIDENT_PRIORITY'),'device-1')['actions']],['incident'])
  for code in sorted(ar.PREREQUISITE_CODES-set(ar.GROUPS['stop'].split())):
   result=ar.select(report('CLEANUP_REQUESTED',code),'device-1')
   self.assertIn(code,result['prerequisite_blockers'])
   item=next(a for a in result['actions'] if a['action_id']=='cleanup')
   self.assertEqual(item['agent_fallback'],'none');self.assertFalse(item['host_handoff']['execution_authorized'])
 def test_real_argument_shapes_without_host_do_not_read(self):
  forms=[['plan','--scope','/absent/scope','--plan-output','/absent/plan'],
   ['quarantine','--plan-file','/absent/plan','--expected-plan-digest','digest'],
   ['reconcile','--plan-file','/absent/plan','--expected-plan-digest','digest','--receipt-output','/absent/receipt'],
   ['restore','--receipt-file','/absent/receipt','--expected-receipt-digest','digest']]
  self.assertEqual([x[0] for x in forms],EXPECTED['operations'])
  for args in forms:
   stream=io.StringIO()
   with patch.object(cli,'_load',side_effect=AssertionError('read without host')):code=cli.main(args,stdout=stream)
   self.assertEqual(code,2);self.assertEqual(json.loads(stream.getvalue())['code'],'HOST_ADAPTER_UNAVAILABLE')
 def test_installed_catalog_documentation_resolves_in_detached_package(self):
  with tempfile.TemporaryDirectory(prefix='guardian-handoff-package-') as tmp:
   base=Path(tmp); archive=base/'skill.zip'
   subprocess.run([sys.executable,'-B',str(ROOT/'tools/package_skill.py'),'--output',str(archive)],check=True,capture_output=True)
   with zipfile.ZipFile(archive) as z:z.extractall(base/'installed')
   installed=base/'installed/claude-guardian'
   result=subprocess.run([sys.executable,'-S','-B',str(installed/'scripts/agent_remediation.py'),'catalog'],cwd=base,check=True,capture_output=True)
   catalog=json.loads(result.stdout.decode('utf-8'))
   handoff=catalog['actions']['cleanup']['host_handoff']
   self.assertEqual(handoff,EXPECTED)
   document=installed/handoff['documentation']
   self.assertTrue(document.is_file(),str(document))
   self.assertIn('cleanup_cli.main',document.read_text(encoding='utf-8'))
   guide=(installed/'references/host-libraries.md').read_text(encoding='utf-8')
   self.assertIn('](cleanup-cli-usage.md)',guide)
   self.assertEqual(catalog['authority'],'none')
 def test_guide_contract(self):
  text=(ROOT/'skills/claude-guardian/references/host-libraries.md').read_text(encoding='utf-8')
  for term in ('cleanup_cli.main','C5-full-claude-data-reset','HOST_ADAPTER_UNAVAILABLE','document_digest','隔离副本','独立备份'):self.assertIn(term,text)
  self.assertNotIn('无清理执行器',text)
  self.assertNotIn('未实现内置清理执行器',json.dumps(ar.CATALOG,ensure_ascii=False))
if __name__=='__main__':unittest.main()
