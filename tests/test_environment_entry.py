"""Synthetic entry-contract tests, never native acceptance or authorization."""
import ast
import builtins
from copy import deepcopy
import importlib.util
import io
import os
from pathlib import Path
import socket
import subprocess
import time
import unittest
from unittest.mock import patch


SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
SPEC = importlib.util.spec_from_file_location('environment_entry', SCRIPTS / 'environment_entry.py')
entry = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(entry)


def fixture(route='local'):
    roles = {'local': ['local'], 'vm': ['vm_host', 'vm_guest'], 'vps': ['vps']}
    aliases = {'local': 'target-local', 'vm_host': 'target-host',
               'vm_guest': 'target-guest', 'vps': 'target-remote'}
    return {
        'schema_version': entry.SCHEMA,
        'route': {'choice': route, 'state': 'selected'},
        'targets': [{'role': role, 'target_ref': aliases[role]} for role in roles[route]],
        'network': {'possession': 'present', 'selection': 'selected',
                    'configuration': 'effective', 'path': 'explicit',
                    'resource_ref': 'resource-a'},
        'local_entry': {'kind': 'mixed', 'entry_ref': 'entry-a'},
        'final_egress': {'kind': 'proxy', 'protocol': 'socks5'},
        'client': 'claude_code',
    }


def direct_fixture(route='local'):
    request = fixture(route)
    request['network'] = {'possession': 'none', 'selection': 'direct',
                          'configuration': 'not_applicable', 'path': 'direct'}
    request['local_entry'] = {'kind': 'none'}
    request['final_egress'] = {'kind': 'direct', 'protocol': 'unknown'}
    return request


def status(result, gate):
    return result['gates'][gate]['status']


class EnvironmentEntryTests(unittest.TestCase):
    def test_success_is_entry_eligibility_not_permission_or_observation(self):
        result = entry.assess_entry(fixture())
        for gate in result['gates'].values():
            self.assertEqual(gate['status'], 'eligible_for_existing_gate')
            self.assertIn('EXISTING_SCOPED_ACTION_AUTHORIZATION', gate['host_requirements'])
            self.assertIn('CURRENT_TARGET_USER_NAMESPACE_BINDING', gate['host_requirements'])
        self.assertEqual(result['authorization_status'], 'not_evaluated_use_existing_action_gates')
        self.assertEqual(result['binding_status'], 'not_verified_by_this_module')
        self.assertEqual(result['evidence_level'], 'sanitized_declarations_not_observations')
        self.assertNotIn('approved', result)
        self.assertNotIn('execute', result)

    def test_route_must_be_explicit_and_current_before_every_diagnostic_gate(self):
        for route in ('local', 'vm', 'vps'):
            for state in entry.ROUTE_STATES:
                if state == 'selected':
                    continue
                with self.subTest(route=route, state=state):
                    request = fixture(route)
                    request['route']['state'] = state
                    result = entry.assess_entry(request)
                    self.assertTrue(all(gate['status'] == 'blocked' for gate in result['gates'].values()))
                    self.assertEqual(result['interview_and_explanation'], 'available')
                    self.assertEqual(result['suggested_check_depth'], 'none')
                    self.assertEqual(result['target_scopes'], [])

    def test_compare_unknown_and_none_are_not_route_selections(self):
        for route in ('compare', 'unknown', 'none'):
            request = fixture()
            request['route'] = {'choice': route, 'state': 'selected'}
            result = entry.assess_entry(request)
            self.assertEqual(status(result, 'offline_precheck'), 'blocked')
            self.assertIn('EXPLICIT_CURRENT_ROUTE_SELECTION_REQUIRED',
                          result['gates']['offline_precheck']['gaps'])

    def test_possessing_vps_or_proxy_does_not_select_either(self):
        request = fixture('vps')
        request['route']['state'] = 'unasked'
        request['network']['selection'] = 'unselected'
        result = entry.assess_entry(request)
        self.assertEqual(status(result, 'offline_precheck'), 'blocked')
        request['route']['state'] = 'selected'
        result = entry.assess_entry(request)
        self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')

    def test_no_owned_resource_and_unknown_network_allow_only_offline_precheck(self):
        for possession in ('none', 'unknown'):
            for selection in ('unselected', 'unknown', 'comparing', 'declined', 'conflict', 'stale', 'withdrawn'):
                with self.subTest(possession=possession, selection=selection):
                    request = fixture()
                    request['network'] = {'possession': possession, 'selection': selection,
                                          'configuration': 'unknown', 'path': 'unknown'}
                    request['local_entry'] = {'kind': 'unknown'}
                    request['final_egress'] = {'kind': 'unknown', 'protocol': 'unknown'}
                    result = entry.assess_entry(request)
                    self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')
                    self.assertEqual(status(result, 'configuration'), 'blocked')

    def test_selected_direct_needs_no_purchase_but_retains_probe_authorization(self):
        for possession in ('none', 'unknown', 'present'):
            request = direct_fixture()
            request['network']['possession'] = possession
            result = entry.assess_entry(request)
            self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')

    def test_direct_is_a_terminal_kind_not_a_proxy_protocol(self):
        request = direct_fixture()
        request['final_egress']['protocol'] = 'socks5'
        result = entry.assess_entry(request)
        request = direct_fixture()
        request['local_entry'] = {'kind': 'http', 'entry_ref': 'entry-a'}

    def test_local_and_vm_have_detailed_distinct_declaration_scopes(self):
        local = entry.assess_entry(fixture())
        self.assertEqual(local['suggested_check_depth'], 'detailed')
        vm = entry.assess_entry(fixture('vm'))
        self.assertEqual(vm['target_scopes'], [
            {'role': 'vm_host', 'target_ref': 'target-host', 'check_depth': 'detailed',
             'binding_status': 'declaration_only'},
            {'role': 'vm_guest', 'target_ref': 'target-guest', 'check_depth': 'detailed',
             'binding_status': 'declaration_only'},
        ])
        self.assertEqual(vm['binding_status'], 'not_verified_by_this_module')
        for gate in vm['gates'].values():
            self.assertIn('CURRENT_TARGET_USER_NAMESPACE_BINDING', gate['host_requirements'])

    def test_host_declaration_does_not_stand_in_for_guest(self):
        request = fixture('vm')
        request['targets'] = request['targets'][:1]
        result = entry.assess_entry(request)
        self.assertEqual(status(result, 'offline_precheck'), 'blocked')
        self.assertEqual(result['target_scopes'], [])
        self.assertIn('ROUTE_TARGET_DECLARATIONS_REQUIRED', result['gates']['offline_precheck']['gaps'])

    def test_duplicate_vm_target_alias_is_rejected_not_a_verified_binding(self):
        request = fixture('vm')
        request['targets'][1]['target_ref'] = request['targets'][0]['target_ref']
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_DUPLICATE_TARGET_ALIAS$'):
            entry.assess_entry(request)

    def test_duplicate_roles_are_rejected(self):
        request = fixture('vm')
        request['targets'][1]['role'] = 'vm_host'
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_DUPLICATE_TARGET_ROLE$'):
            entry.assess_entry(request)

    def test_other_machine_or_empty_targets_cannot_replace_selected_target(self):
        for targets in ([], [{'role': 'vps', 'target_ref': 'target-a'}]):
            request = fixture()
            request['targets'] = targets
            self.assertEqual(status(entry.assess_entry(request), 'offline_precheck'), 'blocked')

    def test_vps_is_basic_nonintrusive_and_has_no_automatic_configuration_scope(self):
        result = entry.assess_entry(fixture('vps'))
        self.assertEqual(result['suggested_check_depth'], 'basic_nonintrusive')
        self.assertEqual(status(result, 'configuration'), 'blocked')
        self.assertIn('VPS_CONFIGURATION_OUTSIDE_BASIC_CHECK_SCOPE', result['gates']['configuration']['gaps'])

    def test_absent_or_imported_configuration_can_enter_planning_not_claim_effectiveness(self):
        for state in ('absent', 'imported'):
            request = fixture()
            request['network']['configuration'] = state
            result = entry.assess_entry(request)
            self.assertEqual(status(result, 'configuration'), 'eligible_for_existing_gate')
            self.assertIn('EXACT_REVIEWED_PLAN_AND_SEMANTIC_DIFF', result['gates']['configuration']['host_requirements'])
        self.assertEqual(result['configuration_readiness'], 'imported_effectiveness_unverified')

    def test_imported_configuration_can_be_probed_without_claiming_effectiveness(self):
        request = fixture()
        request['network']['configuration'] = 'imported'
        result = entry.require_entry(request, 'offline_precheck', 'target-local')
        self.assertEqual(result['status'], 'eligible_for_existing_gate')
        self.assertEqual(result['configuration_readiness'], 'imported_effectiveness_unverified')
        self.assertEqual(result['binding_status'], 'not_verified_by_this_module')
        self.assertIn('EXISTING_SCOPED_ACTION_AUTHORIZATION', result['host_requirements'])

    def test_stale_unknown_conflicting_configuration_is_offline_only(self):
        for state in ('stale', 'unknown', 'conflict'):
            request = fixture()
            request['network']['configuration'] = state
            result = entry.assess_entry(request)
            self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')
            self.assertEqual(status(result, 'configuration'), 'blocked')

    def test_proxy_selection_requires_resource_alias_and_availability(self):
        request = fixture()
        del request['network']['resource_ref']
        request = fixture()
        request['network']['possession'] = 'none'
        self.assertIn('SELECTED_RESOURCE_AVAILABILITY_REQUIRED',
                      entry.assess_entry(request)['gates']['configuration']['gaps'])

    def test_http_and_mixed_can_lead_to_final_socks5_proxy(self):
        for kind in ('http', 'mixed'):
            request = fixture()
            request['local_entry']['kind'] = kind
            self.assertEqual(request['final_egress']['protocol'], 'socks5')

    def test_code_cannot_use_socks_listener_directly(self):
        request = fixture()
        request['local_entry']['kind'] = 'socks'
        result = entry.assess_entry(request)
        self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')
        for gate in ('configuration',):
            self.assertEqual(status(result, gate), 'blocked')
            self.assertIn('CLAUDE_CODE_HTTP_MIXED_ENTRY_REQUIRED', result['gates'][gate]['gaps'])
        request['client'] = 'browser'

    def test_tun_path_does_not_mistake_unused_listener_for_code_configuration(self):
        request = fixture()
        request['network']['path'] = 'tun'
        request['local_entry'] = {'kind': 'none'}

    def test_unknown_client_or_final_proxy_never_infers_code_or_egress_support(self):
        for key, value in (('client', 'unknown'), ('final_egress', {'kind': 'proxy', 'protocol': 'unknown'})):
            request = fixture()
            request[key] = value
            result = entry.assess_entry(request)
            self.assertEqual(status(result, 'configuration'), 'blocked')

    def test_route_withdrawal_never_reuses_old_eligibility(self):
        request = fixture('vm')
        old = entry.assess_entry(request)
        for state in ('withdrawn', 'unknown', 'stale', 'conflict'):
            request['route']['state'] = state
            new = entry.assess_entry(request)
            self.assertEqual(new['target_scopes'], [])
            self.assertEqual(new['host_revalidation']['route_unusable'], 'yes')
            self.assertEqual(new['host_revalidation']['performed_by_this_module'], 'none')
            self.assertEqual(set(new['host_revalidation']['on_route_or_target_change']), {
                'INVALIDATE_DEPENDENT_CONFIRMATIONS', 'INVALIDATE_OLD_TARGET_BINDINGS',
                'INVALIDATE_DEPENDENT_PLANS'})

    def test_network_withdrawal_keeps_only_offline_precheck(self):
        request = fixture()
        request['network']['selection'] = 'withdrawn'
        result = entry.assess_entry(request)
        self.assertEqual(status(result, 'offline_precheck'), 'eligible_for_existing_gate')
        self.assertEqual(result['host_revalidation']['network_selection_unusable'], 'yes')

    def test_strict_allowlist_rejects_sensitive_and_authorization_fields_at_every_level(self):
        for location in ('root', 'route', 'target', 'network', 'local_entry', 'final_egress'):
            for field in ('url', 'password', 'uuid', 'raw_config', 'approved', 'executor'):
                with self.subTest(location=location, field=field):
                    request = fixture()
                    node = request if location == 'root' else (request['targets'][0] if location == 'target' else request[location])
                    node[field] = 'private-secret-must-not-be-echoed'
                    with self.assertRaises(entry.InvalidProjection) as error:
                        entry.assess_entry(request)
                    self.assertEqual(str(error.exception), 'E_OBJECT_SHAPE')

    def test_aliases_reject_addresses_urls_uuids_free_text_and_large_values(self):
        bad = ('https://example.invalid/secret', '127.0.0.1', 'target-user@example.invalid',
               'target-123e4567-e89b-12d3-a456-426614174000', 'target-a/b',
               'target-a\npassword=private', 'target-' + 'a' * 10000, 'target-密码',
               'target-' + 'a' * 64, 'a' * 32, '')
        for value in bad:
            request = fixture()
            request['targets'][0]['target_ref'] = value
            with self.assertRaises(entry.InvalidProjection) as error:
                entry.assess_entry(request)
            self.assertEqual(str(error.exception), 'E_ALIAS')
        request = fixture()
        request['network']['resource_ref'] = 'resource.example.invalid'
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_ALIAS$'):
            entry.assess_entry(request)

    def test_invented_states_types_and_schema_fail_closed_without_echo(self):
        paths = (('route', 'state'), ('route', 'choice'), ('network', 'possession'),
                 ('network', 'selection'), ('network', 'configuration'), ('network', 'path'),
                 ('local_entry', 'kind'), ('final_egress', 'kind'), ('final_egress', 'protocol'))
        for path in paths:
            for bad in ('new-unrecognized-private-value', True, 1, None, ['selected']):
                request = fixture()
                request[path[0]][path[1]] = bad
                with self.assertRaisesRegex(entry.InvalidProjection, '^E_ENUM_VALUE$'):
                    entry.assess_entry(request)
        for version in ('guardian-environment-entry-input/9.9', None, True, {}):
            request = fixture()
            request['schema_version'] = version
            with self.assertRaisesRegex(entry.InvalidProjection, '^E_SCHEMA_VERSION$'):
                entry.assess_entry(request)

    def test_missing_fields_and_unbounded_target_list_are_rejected(self):
        for field in fixture():
            request = fixture()
            del request[field]
            with self.assertRaisesRegex(entry.InvalidProjection, '^E_OBJECT_SHAPE$'):
                entry.assess_entry(request)
        request = fixture()
        request['targets'] *= 5
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_TARGET_LIST$'):
            entry.assess_entry(request)

    def test_custom_mapping_and_string_hooks_are_not_executed(self):
        class HostileDict(dict):
            def __iter__(self):
                raise AssertionError('caller mapping executed')
        class HostileString(str):
            def __eq__(self, other):
                raise AssertionError('caller string executed')
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_OBJECT_SHAPE$'):
            entry.assess_entry(HostileDict(fixture()))
        request = fixture()
        request['route']['state'] = HostileString('selected')
        with self.assertRaisesRegex(entry.InvalidProjection, '^E_ENUM_VALUE$'):
            entry.assess_entry(request)

    def test_no_io_no_mutation_and_deterministic_fresh_outputs(self):
        request = fixture('vm')
        original = deepcopy(request)
        with patch.object(builtins, 'open', side_effect=AssertionError('file I/O')), \
                patch.object(io, 'open', side_effect=AssertionError('file I/O')), \
                patch.object(socket, 'socket', side_effect=AssertionError('network I/O')), \
                patch.object(socket, 'getaddrinfo', side_effect=AssertionError('DNS I/O')), \
                patch.object(subprocess, 'Popen', side_effect=AssertionError('process I/O')), \
                patch.object(subprocess, 'run', side_effect=AssertionError('process I/O')), \
                patch.object(os, 'system', side_effect=AssertionError('process I/O')), \
                patch.object(os, 'scandir', side_effect=AssertionError('filesystem I/O')), \
                patch.object(os, 'getenv', side_effect=AssertionError('environment I/O')), \
                patch.object(time, 'time', side_effect=AssertionError('clock read')):
            result = entry.assess_entry(request)
            self.assertEqual(result, entry.assess_entry(request))
        self.assertEqual(request, original)
        result['target_scopes'][0]['target_ref'] = 'target-changed'
        self.assertEqual(request, original)
        fresh = entry.assess_entry(request)
        self.assertEqual(fresh['target_scopes'][0]['target_ref'], 'target-host')

    def test_listener_and_exit_protocol_spellings_match_remedy_semantics(self):
        tree = ast.parse((SCRIPTS / 'remedy_plans.py').read_text(encoding='utf-8'))
        enum_tuples = []
        for node in ast.walk(tree):
            if (isinstance(node, ast.Call) and isinstance(node.func, ast.Name)
                    and node.func.id == '_enum' and len(node.args) == 2
                    and isinstance(node.args[1], ast.Tuple)):
                enum_tuples.append(ast.literal_eval(node.args[1]))
        self.assertIn(entry.FINAL_PROXY_PROTOCOLS, enum_tuples)
        self.assertIn(tuple(kind for kind in entry.LOCAL_ENTRY_KINDS if kind != 'none'), enum_tuples)
        self.assertNotIn('direct', entry.FINAL_PROXY_PROTOCOLS)

    def test_existing_aliases_need_no_new_prefix(self):
        for alias in ('target', 'device', 'host', 'guest', 'Device_A', 'a' + 'Z' * 47):
            request = fixture()
            request['targets'][0]['target_ref'] = alias
            request['network']['resource_ref'] = 'chosen_proxy'
            request['local_entry']['entry_ref'] = 'listener'

    def test_require_entry_selects_exact_operation_and_target(self):
        request = fixture('vm')
        for purpose in ('offline_precheck', 'configuration'):
            result = entry.require_entry(request, purpose, 'target-guest')
            self.assertEqual(result['purpose'], purpose)
            self.assertEqual(result['target_ref'], 'target-guest')
            self.assertEqual(result['target_role'], 'vm_guest')
            self.assertEqual(result['status'], 'eligible_for_existing_gate')
            self.assertEqual(result['binding_status'], 'not_verified_by_this_module')

    def test_require_entry_rejects_wrong_target_even_when_route_is_eligible(self):
        with self.assertRaises(entry.EntryBlocked) as error:
            entry.require_entry(fixture('vm'), 'offline_precheck', 'other-target')
        self.assertEqual(str(error.exception), 'E_ENTRY_BLOCKED')
        self.assertEqual(error.exception.gaps, ('REQUESTED_TARGET_NOT_IN_CURRENT_ROUTE',))
        self.assertNotIn('other-target', repr(error.exception))

    def test_require_entry_cannot_reuse_offline_eligibility_for_automatic_action(self):
        request = fixture()
        request['network']['selection'] = 'unknown'
        entry.require_entry(request, 'offline_precheck', 'target-local')
        for purpose in ('configuration',):
            with self.assertRaises(entry.EntryBlocked) as error:
                entry.require_entry(request, purpose, 'target-local')
            self.assertIn('EXPLICIT_CURRENT_NETWORK_SELECTION_REQUIRED', error.exception.gaps)

    def test_require_entry_rejects_unknown_operation_and_saved_results(self):
        for purpose in ('rollback', 'approved', 'apply', '', True):
            with self.assertRaisesRegex(entry.InvalidProjection, '^E_ENUM_VALUE$'):
                entry.require_entry(fixture(), purpose, 'target-local')

    def test_require_entry_revalidates_after_withdrawal_and_has_no_io(self):
        request = fixture()
        request['route']['state'] = 'withdrawn'
        with patch('builtins.open', side_effect=AssertionError), \
                self.assertRaises(entry.EntryBlocked) as error:
            entry.require_entry(request, 'offline_precheck', 'target-local')
        self.assertIn('EXPLICIT_CURRENT_ROUTE_SELECTION_REQUIRED', error.exception.gaps)


if __name__ == '__main__':
    unittest.main()
