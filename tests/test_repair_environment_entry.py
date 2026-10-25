"""New route-before-target-read policy; all paths are synthetic and unopened."""
import argparse
import copy
import sys
from pathlib import Path
import unittest
from unittest.mock import patch
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'))
import repair_cli as repair
import repair_execution as execution
import cleanup_cli as cleanup
from environment_entry_fixture import local_entry

class RepairEnvironmentEntryTests(unittest.TestCase):
    def test_preflight_missing_or_withdrawn_entry_reads_no_target(self):
        withdrawn=local_entry();withdrawn['route']['state']='withdrawn'
        for entry in (None, withdrawn, local_entry('other')):
            with self.subTest(entry=entry), patch.object(repair,'_load_request',side_effect=AssertionError('read')), patch.object(repair.tx,'_support',side_effect=AssertionError('support')):
                with self.assertRaisesRegex(repair.RepairError,'ENVIRONMENT_ENTRY_REQUIRED'):
                    repair.preflight('/synthetic/request','/synthetic/target','mac-a',entry_request=entry)
    def test_execute_missing_entry_precedes_plan_read(self):
        with patch.object(execution,'_bound_document',side_effect=AssertionError('plan read')):
            with self.assertRaisesRegex(repair.RepairError,'ENVIRONMENT_ENTRY_REQUIRED'):
                execution.execute(request_path='/synthetic/request',plan_path='/synthetic/plan',plan_digest='unused',target_path='/synthetic/target',target_ref='mac-a',backup_directory='/synthetic/backup')
    def test_preflight_callback_cannot_swap_current_route(self):
        entry=local_entry()
        def cancelled():
            entry['route']['state']='withdrawn'
            return False
        with patch.object(repair,'_load_request',side_effect=AssertionError('read')):
            with self.assertRaisesRegex(repair.RepairError,'ENVIRONMENT_ENTRY_CHANGED'):
                repair.preflight('/synthetic/request','/synthetic/target','mac-a',entry_request=entry,cancelled=cancelled)
    def test_cleanup_plan_missing_entry_precedes_root_scan_and_approval(self):
        args=argparse.Namespace(command='plan',scope='/synthetic/scope',plan_output='/synthetic/output')
        scope={'target_ref':'mac-a'}
        with patch.object(cleanup,'_host'),patch.object(cleanup,'_cancel',return_value=False),patch.object(cleanup,'_load',return_value=scope),patch.object(cleanup,'_scope',return_value=scope),patch.object(cleanup,'_bindings',return_value={}),patch.object(cleanup,'_approval',side_effect=AssertionError('approval')),patch.object(cleanup.core,'plan',side_effect=AssertionError('root scan')):
            with self.assertRaisesRegex(cleanup.CLIError,'ENVIRONMENT_ENTRY_REQUIRED'):
                cleanup.dispatch(args,host=object())
    def test_old_entry_plan_codes_never_fall_back_to_repair(self):
        import agent_remediation
        for code in ('ENVIRONMENT_ENTRY_PLAN_MISMATCH', 'ENVIRONMENT_ENTRY_PLAN_BINDING_REQUIRED'):
            self.assertIn(code, agent_remediation.GROUPS['bind-target'].split())
    def test_generated_environment_commands_include_explicit_entry_file(self):
        import agent_remediation
        for name in ('plan-rules', 'plan-prepend'):
            command = agent_remediation.CATALOG[name]['command_template']
            self.assertEqual(command.count('--entry-file'), 1)
            self.assertEqual(command[command.index('--entry-file') + 1], '<sanitized-entry.json>')
    def test_capabilities_does_not_require_environment_entry(self):
        self.assertEqual(cleanup.dispatch(argparse.Namespace(command='capabilities'))['default_mutations'],'blocked_without_host')

if __name__=='__main__':unittest.main()
