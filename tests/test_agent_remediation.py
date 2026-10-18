"""Offline selector regressions; no native capability or operation permission."""
import ast
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import agent_remediation as ar
import clash_inventory
import controller_inventory


def report(*codes):
    return dict(schema_version=ar.INPUT_SCHEMA, target_ref='device-1',
                findings=[dict(code=c) for c in codes])


class SelectionTests(unittest.TestCase):
    def test_implemented_guardian_findings_and_errors_are_mapped(self):
        tree = ast.parse((SCRIPTS / 'guardian.py').read_text(encoding='utf-8'))
        codes = set()
        for node in ast.walk(tree):
            if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
                index = 1 if node.func.id == 'finding' else 0 if node.func.id == 'GuardianError' else None
                if index is not None and len(node.args) > index:
                    value = node.args[index]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        codes.add(value.value)
        self.assertTrue(codes)
        self.assertFalse(codes - ar.FINDING_ACTIONS.keys())
        self.assertFalse(clash_inventory.PUBLIC_ERROR_CODES - ar.FINDING_ACTIONS.keys())
        self.assertFalse(controller_inventory.PUBLIC_ERROR_CODES - ar.FINDING_ACTIONS.keys())

    def test_transaction_and_controller_gates_do_not_become_missing_adapters(self):
        for code in ['AUTHORIZATION_DENIED', 'AUTHORIZATION_REQUIRED',
                     'AUTHENTICATION_HANDOFF_REQUIRED', 'CONTROLLER_AUTH_FAILED',
                     'CONTROLLER_NOT_BOUND', 'RESPONSE_CONTEXT_MISMATCH',
                     'HOST_APPROVAL_UNAVAILABLE', 'HOST_APPROVAL_FAILED',
                     'CURRENT_EXACT_APPROVAL_REQUIRED', 'APPROVAL_CONTEXT_CHANGED',
                     'APPROVAL_CLOCK_INVALID', 'INVALID_APPROVAL_TIMEOUT',
                     'INTERACTIVE_TERMINAL_REQUIRED', 'INVALID_CONTEXT',
                     'NATIVE_CONTEXT_NOT_BOUND', 'CANCELLATION_CHECK_FAILED',
                     'INVALID_CANCELLATION_CALLBACK']:
            with self.subTest(code=code):
                out = ar.select(report(code, 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE'), 'device-1')
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_transaction_and_recovery_cancellation_overrides_repairs(self):
        for code in ['AUTHORIZATION_CANCELLED', 'APPROVAL_CANCELLED', 'APPROVAL_TIMEOUT']:
            with self.subTest(code=code):
                out = ar.select(report(code, 'DNS_PATH_CONFLICT'), 'device-1')
                self.assertEqual([a['action_id'] for a in out['actions']], ['stop'])
                self.assertEqual(out['next_phase'], 'stop')

    def test_transaction_and_recovery_prerequisites_cannot_be_worked_around(self):
        for code in ['INVALID_OR_EXPIRED_PLAN', 'ROLLBACK_CONFLICT',
                     'RECOVERY_REQUIRES_RECONCILIATION', 'EXCLUSIVE_ACCESS_REQUIRED',
                     'IO_FAILURE', 'DEADLINE_EXCEEDED', 'EXACT_RETAINED_PLAN_REQUIRED',
                     'BASE_PROFILE_FILE_MISMATCH', 'PROFILE_DIRECTORY_SCOPE_MISMATCH',
                     'INVALID_REPAIR_REQUEST', 'SELECTED_EXTENSION_NOT_ACTIVE_MERGE',
                     'SELECTED_EXTENSION_NOT_ACTIVE_RULES']:
            with self.subTest(code=code):
                out = ar.select(report(code, 'DNS_PATH_CONFLICT'), 'device-1')
                self.assertIn(code, out['prerequisite_blockers'])
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_emitted_transaction_guards_have_explicit_non_fallback_classification(self):
        capability_gaps = {'PLATFORM_UNSUPPORTED', 'WINDOWS_API_UNAVAILABLE',
                           'UNSUPPORTED_CANDIDATE_KIND', 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE',
                           'UNSUPPORTED_PRODUCT_OR_VERSION', 'UNSUPPORTED_REMEDY',
                           'UNSUPPORTED_EXTENSION_TYPE', 'UNSUPPORTED_ACTIVE_PROFILE_TYPE'}
        for filename in ['transactions.py', 'windows_transactions.py',
                         'recovery_cli.py', 'repair_execution.py', 'repair_cli.py',
                         'config_edit_plan.py', 'rules_extension_plan.py', 'clash_verge_258.py']:
            codes = set()
            tree = ast.parse((SCRIPTS / filename).read_text(encoding='utf-8'))
            for node in ast.walk(tree):
                if (isinstance(node, ast.Call) and node.args
                        and (getattr(node.func, 'id', '') in {'_fail', 'fail', 'TransactionError',
                                                            'RepairError', 'EditPlanError',
                                                            'RulesPlanError', 'OwnershipError'}
                             or getattr(node.func, 'attr', '') == 'TransactionError')):
                    value = node.args[0]
                    if isinstance(value, ast.Constant) and isinstance(value.value, str):
                        codes.add(value.value)
            self.assertTrue(codes, filename)
            for code in sorted(codes):
                with self.subTest(filename=filename, code=code):
                    out = ar.select(report(code, 'DNS_PATH_CONFLICT'), 'device-1')
                    if code in capability_gaps:
                        self.assertEqual(out['actions'][0]['action_id'], 'unsupported')
                        self.assertEqual(out['actions'][0]['agent_fallback'], 'investigate_scoped_repair')
                    elif code == 'PARSER_UNAVAILABLE':
                        self.assertEqual(out['actions'][0]['action_id'], 'dependency')
                    elif code == 'NO_CHANGE':
                        self.assertEqual(out['actions'][0]['action_id'], 'keep')
                        self.assertEqual(out['actions'][0]['agent_fallback'], 'none')
                    else:
                        self.assertIn(out['next_phase'], {'stop', 'resolve_prerequisites'})
                        self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_structured_errors_and_codes_preserve_gates(self):
        for diagnostic in [{'errors': ['PERMISSION_DENIED']},
                           {'errors': [{'code': 'PERMISSION_DENIED', 'detail': 'SECRET'}]},
                           {'code': 'PERMISSION_DENIED'}, {'error_code': 'PERMISSION_DENIED'}]:
            with self.subTest(diagnostic=diagnostic):
                out = ar.select(dict(report('DNS_PATH_CONFLICT'), **diagnostic), 'device-1')
                self.assertIn('PERMISSION_DENIED', out['prerequisite_blockers'])
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
                self.assertNotIn('SECRET', json.dumps(out))

    def test_structured_cancellation_overrides_repairs(self):
        for diagnostic in [{'errors': ['CANCELLED']}, {'errors': [{'code': 'USER_CANCELLED'}]},
                           {'code': 'APPROVAL_CANCELLED'}, {'error_code': 'AUTHORIZATION_CANCELLED'},
                           {'execution_status': 'interrupted'}, {'status': 'cancelled'},
                           {'inventory_readiness': 'interrupted'}, {'cancelled': True}]:
            with self.subTest(diagnostic=diagnostic):
                out = ar.select(dict(report('DNS_PATH_CONFLICT'), **diagnostic), 'device-1')
                self.assertEqual([a['action_id'] for a in out['actions']], ['stop'])

    def test_unexplained_blocked_or_failed_report_does_not_offer_repair(self):
        for key, value in [('execution_status', 'blocked'), ('execution_status', 'failed'),
                           ('status', 'blocked'), ('status', 'failed'),
                           ('inventory_readiness', 'blocked')]:
            with self.subTest(key=key, value=value):
                out = ar.select(dict(report('DNS_PATH_CONFLICT'), **{key: value}), 'device-1')
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_unknown_error_is_not_unknown_capability(self):
        for diagnostic in [{'errors': ['PRIVATE_UNKNOWN_ERROR']},
                           {'errors': [{'code': 'PRIVATE_UNKNOWN_ERROR'}]},
                           {'code': 'PRIVATE_UNKNOWN_ERROR'}, {'error_code': 'PRIVATE_UNKNOWN_ERROR'}]:
            with self.subTest(diagnostic=diagnostic):
                out = ar.select(dict(report('DNS_PATH_CONFLICT'), **diagnostic), 'device-1')
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
                self.assertNotIn('PRIVATE_UNKNOWN_ERROR', json.dumps(out))

    def test_explicit_capability_only_diagnostic_still_allows_investigation(self):
        for diagnostic in [{'errors': ['NATIVE_REPAIR_ADAPTER_UNAVAILABLE']},
                           {'status': 'blocked', 'error_code': 'UNSUPPORTED_PRODUCT_OR_VERSION'}]:
            with self.subTest(diagnostic=diagnostic):
                out = ar.select(dict(report(), **diagnostic), 'device-1')
                self.assertEqual(out['actions'][0]['agent_fallback'], 'investigate_scoped_repair')

    def test_real_report_envelopes_keep_failure_gates_and_do_not_mutate_input(self):
        for schema in ['guardian-report/0.1', 'env-inventory/0.2']:
            with self.subTest(schema=schema):
                inp = ar.guardian.base('audit', 'device-1')
                inp['schema_version'] = schema
                inp['findings'] = [{'code': 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE'}]
                inp['errors'] = [{'code': 'PERMISSION_DENIED'}]
                before = json.dumps(inp, sort_keys=True)
                out = ar.select(inp, 'device-1')
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
                self.assertEqual(json.dumps(inp, sort_keys=True), before)

    def test_failed_or_mixed_blocked_reports_cannot_claim_capability_only(self):
        for inp in [dict(report('NATIVE_REPAIR_ADAPTER_UNAVAILABLE'), status='failed'),
                    dict(report('NATIVE_REPAIR_ADAPTER_UNAVAILABLE', 'DNS_PATH_CONFLICT'), status='blocked'),
                    dict(report('PRIVATE_UNKNOWN_DETAIL'), status='blocked'),
                    dict(report('NATIVE_REPAIR_ADAPTER_UNAVAILABLE'), errors=['PRIVATE_UNKNOWN_ERROR'])]:
            with self.subTest(inp=inp):
                out = ar.select(inp, 'device-1')
                self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_malformed_structured_diagnostics_fail_closed(self):
        for diagnostic in [{'errors': 'PERMISSION_DENIED'}, {'errors': {}}, {'errors': None},
                           {'errors': [None]}, {'errors': [{}]}, {'errors': [{'code': []}]},
                           {'errors': ['TIMEOUT'] * 129}, {'error_code': []}, {'code': False},
                           {'status': []}, {'status': 'PRIVATE_STATUS'},
                           {'execution_status': {}}, {'inventory_readiness': False},
                           {'cancelled': 'true'}, {'missing_fields': 'P06'}]:
            with self.subTest(diagnostic=diagnostic):
                with self.assertRaisesRegex(ar.guardian.GuardianError, 'INPUT_OR_RESPONSE_INVALID'):
                    ar.select(dict(report('DNS_PATH_CONFLICT'), **diagnostic), 'device-1')

    def test_conflict_selects_port_not_rule_mutation(self):
        out = ar.select(report('PROXY_PORT_ASSOCIATION_CONFLICT'), 'device-1')
        self.assertEqual(out['actions'][0]['action_id'], 'proxy-port')
        self.assertEqual(out['actions'][0]['agent_fallback'], 'investigate_scoped_repair')
        self.assertFalse(out['actions'][0]['target_mutation_supported'])
        self.assertIsNone(out['actions'][0]['command_template'])
        self.assertEqual(out['completion'], 'no_repair_performed')

    def test_prepend_has_complete_specific_template(self):
        command = ar.select(report('RULE_PREPEND_REQUIRED'), 'device-1')['actions'][0]['command_template']
        self.assertEqual(command[command.index('--candidate-kind') + 1], 'rules-prepend')
        for arg in ['--app-info', '--profile-index', '--extension-uid', '--base-path']:
            self.assertIn(arg, command)

    def test_unknown_and_missing_adapter_continue_agent_investigation(self):
        for code in ['NEW_FINDING', 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE']:
            out = ar.select(report(code), 'device-1')
            self.assertEqual(out['actions'][0]['kind'], 'agent_investigation')
            self.assertEqual(out['actions'][0]['agent_fallback'], 'investigate_scoped_repair')
            self.assertIn('obtain_required_specific_approval', out['actions'][0]['fallback_requirements'])

    def test_denial_and_security_failures_cannot_route_around_gates(self):
        for code in ['PERMISSION_DENIED', 'AUTHORIZATION_MISSING', 'PRECONTACT_ACTION_REJECTED',
                     'UNSAFE_OR_OFFLINE_PATH', 'TARGET_USER_CONTEXT_MISMATCH', 'TARGET_NOT_BOUND',
                     'PC0_TARGET_FORBIDDEN', 'CONTEXT_CHANGED', 'RUNTIME_NOT_TRUSTED',
                     'HOST_INTEGRATION_INVALID', 'ENDPOINT_NEUTRALITY_UNVERIFIED',
                     'STALE_EVIDENCE_REAUDIT_REQUIRED', 'SNAPSHOT_CHANGED_DURING_AUDIT',
                     'ROUTE_OR_TARGET_NEEDS_CLARIFICATION', 'AUTHORIZATION_SCOPE_MISMATCH',
                     'ACTION_AUTHORIZATION_PENDING', 'CONTEXT_MISMATCH', 'POST_WRITE_VERIFY_FAILED']:
            out = ar.select(report(code, 'NATIVE_REPAIR_ADAPTER_UNAVAILABLE'), 'device-1')
            self.assertEqual(out['next_phase'], 'resolve_prerequisites')
            self.assertTrue(out['prerequisite_blockers'])
            self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))

    def test_cancel_overrides_other_actions(self):
        out = ar.select(report('PROXY_PORT_ASSOCIATION_CONFLICT', 'USER_CANCELLED'), 'device-1')
        self.assertEqual([a['action_id'] for a in out['actions']], ['stop'])
        self.assertEqual(out['next_phase'], 'stop')

    def test_empty_and_missing_never_pass(self):
        for inp in [report(), dict(report(), missing_fields=['P06'])]:
            out = ar.select(inp, 'device-1')
            self.assertFalse(out['environment_pass'])
            self.assertEqual(out['changes'], [])
        self.assertEqual(ar.select(report(), 'device-1')['status'], 'insufficient_evidence')

    def test_target_mismatch(self):
        with self.assertRaisesRegex(ar.guardian.GuardianError, 'TARGET_NOT_BOUND'):
            ar.select(report(), 'other-target')

    def test_commands_and_authority_in_input_are_not_used_or_echoed(self):
        inp = dict(report('RULE_POLICY_MISMATCH'), command='SECRET_COMMAND', authorization=True,
                   apply_supported=True, raw_config='SECRET_CONFIG')
        out = ar.select(inp, 'device-1')
        self.assertNotIn('SECRET', json.dumps(out))
        self.assertEqual(out['authority'], 'none')
        self.assertEqual(out['actions'][0]['command_template'][1], 'scripts/repair_cli.py')
        self.assertEqual(out['actions'][0]['kind'], 'candidate_only')

    def test_unknown_code_not_echoed(self):
        out = ar.select(report('PRIVATE_UNKNOWN_DETAIL'), 'device-1')
        self.assertNotIn('PRIVATE_UNKNOWN_DETAIL', json.dumps(out))
        self.assertIn('UNRECOGNIZED_FINDING', json.dumps(out))

    def test_no_configuration_change_for_inconclusive_or_normal_observations(self):
        out = ar.select(report('FAKE_IP_WITH_WORKING_HTTPS', 'IPV6_TIMEOUT_ONLY'), 'device-1')
        self.assertEqual(len(out['actions']), 1)
        self.assertEqual(out['actions'][0]['kind'], 'no_change')
        self.assertEqual(out['actions'][0]['agent_fallback'], 'none')

    def test_incident_does_not_select_cleanup(self):
        out = ar.select(report('INCIDENT_PRIORITY'), 'device-1')
        self.assertEqual(out['actions'][0]['action_id'], 'incident')

    def test_every_catalog_command_names_shipped_script(self):
        for item in ar.CATALOG.values():
            if item['command_template']:
                self.assertTrue((SCRIPTS.parent / item['command_template'][1]).is_file())

    def test_malformed_input(self):
        for inp in [None, {}, dict(report(), schema_version=[]), dict(report(), schema_version={}), dict(report(), findings=[{'code': 'evil; shell'}]),
                    dict(report(), findings='NOT_A_LIST')]:
            with self.assertRaises(ar.guardian.GuardianError):
                ar.select(inp, 'device-1')

    def test_cli_errors_do_not_echo_arguments(self):
        for args in [['SECRET_COMMAND'], ['catalog', '--SECRET_OPTION', 'SECRET_VALUE']]:
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'agent_remediation.py'), *args],
                                  capture_output=True, text=True)
            self.assertEqual(proc.returncode, 2)
            self.assertNotIn('SECRET', proc.stdout + proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['code'], 'INPUT_OR_RESPONSE_INVALID')

    def test_cli_non_ascii_catalog_under_legacy_stdout_encoding(self):
        env = dict(os.environ, PYTHONIOENCODING='cp1252', PYTHONUTF8='0')
        proc = subprocess.run([sys.executable, str(SCRIPTS / 'agent_remediation.py'), 'catalog'],
                              capture_output=True, env=env)
        self.assertEqual(proc.returncode, 0, proc.stderr.decode('ascii', errors='replace'))
        result = json.loads(proc.stdout.decode('ascii'))
        self.assertEqual(result['actions']['proxy-port']['summary'], ar.CATALOG['proxy-port']['summary'])
        self.assertEqual(result['authority'], 'none')

    def test_cli_only_reads_local_input(self):
        with tempfile.TemporaryDirectory() as tmp:
            p = Path(tmp) / 'report.json'
            p.write_text(json.dumps(report('PROXY_PORT_ASSOCIATION_CONFLICT')))
            before = p.read_bytes()
            proc = subprocess.run([sys.executable, str(SCRIPTS / 'agent_remediation.py'), 'select',
                                   '--input', str(p), '--target-ref', 'device-1'], capture_output=True, text=True)
            self.assertEqual(proc.returncode, 0, proc.stderr)
            self.assertEqual(json.loads(proc.stdout)['changes'], [])
            self.assertEqual(p.read_bytes(), before)
            self.assertEqual(list(Path(tmp).iterdir()), [p])


if __name__ == '__main__':
    unittest.main()
