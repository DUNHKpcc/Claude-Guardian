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


def report(*codes):
    return dict(schema_version=ar.INPUT_SCHEMA, target_ref='device-1',
                findings=[dict(code=c) for c in codes])


class SelectionTests(unittest.TestCase):
    def test_rules_task_discovery_does_not_override_barriers_or_no_change(self):
        selected = ar.select(report('RULE_PREPEND_REQUIRED'), 'device-1')
        task = selected['actions'][0]['host_handoff']
        self.assertEqual(task['entry_point'], 'agent_rules_task.prepare_rules_task')
        self.assertFalse(task['execution_authorized'])
        self.assertFalse(task['builtin_apply_supported'])
        self.assertEqual(selected['authority'], 'none')
        for barrier in ('USER_CANCELLED', 'PERMISSION_DENIED', 'ENVIRONMENT_ENTRY_REQUIRED'):
            blocked = ar.select(report('RULE_PREPEND_REQUIRED', barrier), 'device-1')
            self.assertTrue(all(item['agent_fallback'] == 'none' for item in blocked['actions']))
        unchanged = ar.select(report('RULE_PREPEND_REQUIRED', 'NO_CHANGE_TO_EXECUTE'), 'device-1')
        self.assertEqual([item['action_id'] for item in unchanged['actions']], ['no-change'])
        self.assertNotIn('host_handoff', unchanged['actions'][0])
        selected['actions'][0]['host_handoff']['execution_authorized'] = True
        self.assertFalse(ar.CATALOG['plan-prepend']['host_handoff']['execution_authorized'])

    def test_clock_action_aligns_timezone_with_exit(self):
        # Owner rule 2026-10-28 (Issue #15): computer and phone time zones follow the exit IP region.
        clock = ar.CATALOG['clock']
        text = ''.join([clock['summary'], *clock['steps'], *clock['verification']])
        self.assertIn('出口IP所在地区为目标', text)
        self.assertIn('关闭自动设置时区', text)
        self.assertIn('电脑（本机、VM、VPS）和手机的时区', text)
        self.assertNotIn('手机时区保持真实', text)
        self.assertNotIn('不按出口地区改时区', text)

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
        for filename in ['transactions.py',
                         'recovery_cli.py', 'repair_execution.py', 'repair_cli.py',
                         'config_edit_plan.py', 'rules_extension_plan.py', 'clash_verge_258.py', 'native_clash_verge_mac.py']:
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

    def test_prepared_recovery_guards_never_trigger_alternate_mutation(self):
        codes = (
            'BACKUP_CHANGED',
            'BACKUP_DIRECTORY_CHANGED',
            'BACKUP_NOT_PRIVATE',
            'INVALID_RECONCILIATION',
            'LEGACY_RECOVERY_IDENTITY_UNPROVEN',
            'PREPARED_RECOVERY_REQUIRED',
            'RECONCILIATION_STALE',
            'RECOVERY_WITNESS_MISMATCH',
            'STAGING_CHANGED',
            'EXPECTED_RECONCILIATION_REQUIRED',
            'STAGING_RETAINED',
            'STAGING_CLEANUP_FAILED',
            'DESCRIPTOR_CLOSE_FAILED',
        )
        for code in codes:
            for inp in (report(code, 'DNS_PATH_CONFLICT'),
                        report('NATIVE_REPAIR_ADAPTER_UNAVAILABLE', code),
                        dict(report(), errors=[code])):
                with self.subTest(code=code, inp=inp):
                    out = ar.select(inp, 'device-1')
                    self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                    self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
                    self.assertTrue(all(a['command_template'] is None for a in out['actions']))
                    self.assertEqual(out['authority'], 'none')
                    self.assertEqual(out['changes'], [])

    def test_no_change_transport_codes_stop_without_fallback_or_native_claims(self):
        for code in ('NO_CHANGE_TO_RETAIN', 'NO_CHANGE_TO_EXECUTE'):
            for inp in (report(code), report(code, 'DNS_PATH_CONFLICT'),
                        report('NATIVE_REPAIR_ADAPTER_UNAVAILABLE', code),
                        report('UNRECOGNIZED_DIAGNOSTIC', code),
                        dict(report(), errors=[code]),
                        dict(report(), status='blocked', code=code)):
                with self.subTest(code=code, inp=inp):
                    out = ar.select(inp, 'device-1')
                    self.assertEqual(out['next_phase'], 'stop')
                    self.assertEqual(out['status'], 'stopped')
                    self.assertEqual([a['action_id'] for a in out['actions']], ['no-change'])
                    self.assertEqual(out['actions'][0]['kind'], 'no_change')
                    self.assertEqual(out['actions'][0]['agent_fallback'], 'none')
                    self.assertIsNone(out['actions'][0]['command_template'])
                    self.assertEqual(out['actions'][0]['finding_codes'], [code])
                    self.assertEqual(out['prerequisite_blockers'], [])
                    self.assertEqual(out['completion'], 'no_repair_performed')
                    self.assertEqual(out['changes'], [])
                    self.assertEqual(out['authority'], 'none')
                    self.assertEqual(out['native_acceptance'], 'not_established')
                    self.assertFalse(out['environment_pass'])

    def test_no_change_preserves_independent_incident_triage_in_both_orders(self):
        for code in ('NO_CHANGE_TO_RETAIN', 'NO_CHANGE_TO_EXECUTE'):
            for codes in ((code, 'INCIDENT_PRIORITY'), ('INCIDENT_PRIORITY', code)):
                with self.subTest(codes=codes):
                    out = ar.select(report(*codes, 'DNS_PATH_CONFLICT'), 'device-1')
                    self.assertEqual(out['next_phase'], 'stop')
                    self.assertEqual({a['action_id'] for a in out['actions']}, {'no-change', 'incident'})
                    self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
                    incident = next(a for a in out['actions'] if a['action_id'] == 'incident')
                    self.assertEqual(incident['finding_codes'], ['INCIDENT_PRIORITY'])
                    self.assertEqual(incident['kind'], 'clarify')
                    self.assertEqual(out['completion'], 'no_repair_performed')
                    self.assertFalse(out['environment_pass'])
                    cancelled = ar.select(report(*codes, 'USER_CANCELLED'), 'device-1')
                    self.assertEqual([a['action_id'] for a in cancelled['actions']], ['stop'])

    def test_no_change_does_not_hide_cancellation_or_genuine_prerequisite_failure(self):
        for code in ('NO_CHANGE_TO_RETAIN', 'NO_CHANGE_TO_EXECUTE'):
            out = ar.select(report(code, 'USER_CANCELLED'), 'device-1')
            self.assertEqual([a['action_id'] for a in out['actions']], ['stop'])
            for gate in ('STALE_FILE', 'PERMISSION_DENIED', 'ROLLBACK_CONFLICT'):
                with self.subTest(code=code, gate=gate):
                    out = ar.select(report(code, gate, 'DNS_PATH_CONFLICT'), 'device-1')
                    self.assertEqual(out['next_phase'], 'resolve_prerequisites')
                    self.assertIn(gate, out['prerequisite_blockers'])
                    self.assertTrue(all(a['agent_fallback'] == 'none' for a in out['actions']))
            out = ar.select(dict(report(code), status='failed'), 'device-1')
            self.assertEqual(out['next_phase'], 'resolve_prerequisites')
            self.assertIn('DIAGNOSTIC_PREREQUISITES_UNRESOLVED', out['prerequisite_blockers'])

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


class UnknownMemberRejectionTests(unittest.TestCase):
    """ENV-T121: a saved report carrying members outside the release vocabulary is
    rejected at the input boundary, not silently ignored. Markers are synthetic."""
    MARKER = 'SYNTHSECRETQ7Z9K2'
    SCHEMAS = ('guardian-report/0.1', 'env-inventory/0.2')

    def full_report(self, schema):
        import guardian
        obj = guardian.base('audit', 'device-1')
        obj['schema_version'] = schema
        obj['findings'] = [{'code': 'STALE_EVIDENCE_REAUDIT_REQUIRED', 'module_id': 'ENV-01'}]
        obj['facts'] = [{'id': 'S01', 'value': 'macos', 'state': 'observed', 'context_ref': 'device-1',
                         'observed_at': '2026-10-15T00:00:00Z', 'layer': 'os_query', 'source_ref': 'synthetic-os'}]
        return obj

    def test_unknown_members_rejected_without_echo(self):
        places = [(None, 'proxy_password'), (None, 'subscription_url'), (None, 'command'),
                  ('snapshot', 'token'), ('target_binding', 'secret'), ('privacy', 'url'),
                  ('limits', 'endpoint'), ('contact_control', 'password'),
                  ('facts', 'password'), ('findings', 'detail')]
        for schema in self.SCHEMAS:
            for where, key in places:
                with self.subTest(schema=schema, where=where, key=key):
                    obj = self.full_report(schema)
                    holder = obj if where is None else (obj[where][0] if where in ('facts', 'findings') else obj[where])
                    holder[key] = self.MARKER
                    with self.assertRaises(ar.guardian.GuardianError) as ctx:
                        ar.select(obj, 'device-1')
                    self.assertEqual(ctx.exception.code, 'INPUT_OR_RESPONSE_INVALID')

    def test_known_members_report_still_selected(self):
        for schema in self.SCHEMAS:
            with self.subTest(schema=schema):
                self.assertEqual(ar.select(self.full_report(schema), 'device-1')['changes'], [])

    def test_findings_schema_is_unchanged(self):
        """The module's own minimal findings schema keeps its existing contract."""
        self.assertEqual(ar.select(report('STALE_EVIDENCE_REAUDIT_REQUIRED'), 'device-1')['changes'], [])

    def test_cli_rejects_unknown_member_without_echo(self):
        with tempfile.TemporaryDirectory() as tmp:
            source = Path(tmp) / 'report.json'
            obj = self.full_report('guardian-report/0.1')
            obj['proxy_password'] = self.MARKER
            source.write_text(json.dumps(obj), encoding='utf-8')
            result = subprocess.run([sys.executable, str(SCRIPTS / 'agent_remediation.py'), 'select',
                                     '--input', str(source), '--target-ref', 'device-1'],
                                    capture_output=True, text=True)
            self.assertEqual(result.returncode, 2)
            self.assertNotIn(self.MARKER, result.stdout + result.stderr)


if __name__ == '__main__':
    unittest.main()
