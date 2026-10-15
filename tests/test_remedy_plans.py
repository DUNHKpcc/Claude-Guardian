"""Synthetic offline semantic plans; no native acceptance claims."""
import builtins
from copy import deepcopy
import importlib.util
from pathlib import Path
import socket
import subprocess
import unittest
from unittest.mock import patch

SPEC = importlib.util.spec_from_file_location(
    'remedy_plans', Path(__file__).resolve().parents[1] /
    'skills/claude-guardian/scripts/remedy_plans.py')
r = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(r)


def fixture(template='keep-existing'):
    return {'schema_version': r.SCHEMA, 'target_ref': 'mac-a', 'observed_target_ref': 'mac-a',
            'route_ref': 'local-route', 'scope_refs': ['workflow-a'], 'template': template,
            'revisions': {'effective': 'a' * 64, 'extension': 'b' * 64},
            'revision_refs': {'effective': 'snapshot-a', 'extension': 'snapshot-b'},
            'current_revisions': {'effective': 'a' * 64, 'extension': 'b' * 64},
            'intent': {'rule_refs': ['rule-a'], 'egress_group_ref': 'approved-group',
                       'no_direct': 'yes', 'ipv6_goal': 'preserve', 'udp_goal': 'preserve'},
            'facts': {'versions': {'product': 'clash-verge-rev', 'gui': '2.5.5', 'core': '1.19.0'},
                      'mode': 'rule', 'control': {'dependency_known': 'yes', 'preserved': 'yes',
                                                'rescue_available': 'yes', 'scope_refs': ['control-a']},
                      'rules': {'first_match_verified': 'yes', 'protected_priority_preserved': 'yes',
                                'complete': 'yes'},
                      'ownership': {'known': 'yes', 'persistent_extension_available': 'yes',
                                    'gui_readback_available': 'yes'},
                      'groups': {'approved-group': {'kind': 'group', 'complete': 'yes', 'members': ['node-a']},
                                 'node-a': {'kind': 'proxy', 'protocol': 'socks5', 'complete': 'yes', 'members': []}},
                      'ipv6': 'verified', 'udp': 'verified',
                      'dns': {'nodes': ['resolver', 'bootstrap'],
                              'edges': [{'from': 'resolver', 'to': 'bootstrap', 'path': 'both'}],
                              'complete': 'yes', 'local_preserved': 'yes', 'browser_doh_known': 'yes',
                              'bootstrap_known': 'yes', 'policy_merge_known': 'yes',
                              'responsibility': 'mihomo'}}}


def codes(result):
    return {item['code'] for item in result['blockers']}


class RemedyPlansTests(unittest.TestCase):
    def test_valid_projection_is_not_native_acceptance(self):
        result = r.compile_plan(fixture())
        self.assertEqual(result['status'], 'blocked')
        self.assertFalse(result['apply_supported'])
        self.assertEqual(codes(result), {'NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED',
                                        'NATIVE_ACCEPTANCE_NOT_RUN', 'VERSION_CAPABILITY_UNVERIFIED'})
        self.assertEqual(len(result['proposed_changes']), 1)

    def test_all_four_templates_have_concrete_semantics(self):
        expected = {'keep-existing': 'bind_selected_rules',
                    'explicit-rule': 'selected_application_proxy_binding',
                    'tun-rule': 'scoped_tun_route_intent',
                    'scoped-compatibility': 'scoped_compatibility_intent'}
        for template in r.TEMPLATES:
            with self.subTest(template=template):
                req = fixture(template)
                req['facts']['explicit'] = {'entry_ref': 'entry-a', 'kind': 'mixed', 'adoption': 'yes'}
                req['intent']['compatibility_action'] = 'restrict-webrtc'
                result = r.compile_plan(req)
                self.assertIn(expected[template], {item['kind'] for item in result['proposed_changes']})

    def test_no_input_mutation_or_io(self):
        req = fixture('tun-rule')
        original = deepcopy(req)
        with patch.object(builtins, 'open', side_effect=AssertionError('file access')), \
             patch.object(socket, 'socket', side_effect=AssertionError('network')), \
             patch.object(subprocess, 'Popen', side_effect=AssertionError('process')):
            first = r.compile_plan(req)
            second = r.compile_plan(req)
        self.assertEqual(req, original)
        self.assertEqual(first, second)
        first['revision_refs']['effective'] = 'snapshot-c'
        first['dns_checks']['nodes'].append('other')
        self.assertEqual(req, original)

    def test_target_revision_and_cancellation_stop_proposals(self):
        for field, value, expected in (
                ('observed_target_ref', 'other-mac', 'TARGET_MISMATCH'),
                ('current_revisions', {'effective': 'c' * 64}, 'STALE_REVISIONS'),
                ('cancelled', True, 'CANCELLED')):
            with self.subTest(field=field):
                req = fixture()
                req[field] = value
                result = r.compile_plan(req)
                self.assertIn(expected, codes(result))
                self.assertEqual(result['proposed_changes'], [])

    def test_unknown_version_and_projection_facts(self):
        req = fixture()
        req['facts'] = {}
        result = r.compile_plan(req)
        self.assertIn('VERSION_UNKNOWN', codes(result))
        self.assertIn('DNS_GRAPH_MISSING', codes(result))
        self.assertIn('CONTROL_DEPENDENCY_KNOWN', codes(result))
        self.assertIn('EGRESS_GRAPH_INCOMPLETE', codes(result))
        self.assertEqual(result['dns_checks']['normal'], 'unknown')

    def test_control_path_overlap_and_absent_rescue(self):
        req = fixture('tun-rule')
        req['facts']['control']['scope_refs'] = ['workflow-a']
        req['facts']['control']['preserved'] = 'no'
        req['facts']['control']['rescue_available'] = 'no'
        result = r.compile_plan(req)
        self.assertTrue({'CONTROL_SCOPE_OVERLAP', 'CONTROL_PRESERVED', 'CONTROL_RESCUE_AVAILABLE'} <= codes(result))

    def test_dns_normal_and_failure_loops(self):
        for path in ('normal', 'failure', 'both'):
            with self.subTest(path=path):
                req = fixture()
                req['facts']['dns']['edges'].append({'from': 'bootstrap', 'to': 'resolver', 'path': path})
                result = r.compile_plan(req)
                for branch in ('normal', 'failure'):
                    self.assertEqual('DNS_' + branch.upper() + '_CYCLE' in codes(result), path in (branch, 'both'))

    def test_local_dns_and_full_policy_preservation(self):
        req = fixture()
        req['facts']['dns']['local_preserved'] = 'no'
        req['facts']['dns']['policy_merge_known'] = 'unknown'
        result = r.compile_plan(req)
        self.assertIn('DNS_LOCAL_PRESERVED', codes(result))
        self.assertIn('DNS_POLICY_MERGE_KNOWN', codes(result))
        self.assertIn('never deep-merge', result['dns_checks']['policy_rule'])

    def test_nested_direct_fallback_and_group_cycle(self):
        req = fixture()
        req['facts']['groups']['node-a'] = {'kind': 'group', 'complete': 'yes', 'members': ['direct-terminal', 'approved-group']}
        req['facts']['groups']['direct-terminal'] = {'kind': 'direct', 'complete': 'yes', 'members': []}
        result = r.compile_plan(req)
        self.assertIn('DIRECT_FALLBACK', codes(result))
        self.assertIn('EGRESS_GRAPH_CYCLE', codes(result))

    def test_unknown_member_is_not_safe_terminal(self):
        req = fixture()
        del req['facts']['groups']['node-a']
        self.assertIn('EGRESS_GRAPH_INCOMPLETE', codes(r.compile_plan(req)))

    def test_modes_and_socks_not_silently_rewritten(self):
        req = fixture('explicit-rule')
        req['facts']['mode'] = 'global'
        req['facts']['explicit'] = {'entry_ref': 'entry-a', 'kind': 'socks', 'adoption': 'unknown'}
        result = r.compile_plan(req)
        self.assertIn('RULE_MODE_CONFLICT', codes(result))
        self.assertIn('HTTP_MIXED_ENTRY_UNCONFIRMED', codes(result))
        self.assertNotIn('selected_application_proxy_binding', {x['kind'] for x in result['proposed_changes']})

    def test_combined_mode_needs_loop_and_exclusion_evidence(self):
        req = fixture('tun-rule')
        req['facts']['explicit'] = {'kind': 'http', 'entry_ref': 'entry-a', 'adoption': 'yes'}
        result = r.compile_plan(req)
        self.assertIn('COMBINED_MODE_LOOP_EXCLUSIONS_UNVERIFIED', codes(result))
        self.assertIn('TUN_VPN_VM_COMPATIBLE', codes(result))

    def test_ipv6_and_udp_unknown_never_become_guarantees(self):
        req = fixture('tun-rule')
        req['facts']['ipv6'] = 'unknown'
        req['facts']['udp'] = 'unsupported'
        req['intent']['ipv6_goal'] = 'block'
        result = r.compile_plan(req)
        self.assertTrue({'IPV6_PATH_UNVERIFIED', 'UDP_PATH_UNVERIFIED'} <= codes(result))
        changes = [x for x in result['proposed_changes'] if x['kind'] == 'scoped_protocol_intent']
        self.assertFalse(changes[0]['system_wide_guarantee'])

    def test_compatibility_preserves_outer_ipv6(self):
        req = fixture('scoped-compatibility')
        req['intent']['compatibility_action'] = 'ipv4-only'
        result = r.compile_plan(req)
        self.assertIn('OUTER_NODE_ADDRESS_FAMILY_DEPENDENCY_UNKNOWN', codes(result))
        change = next(x for x in result['proposed_changes'] if x['kind'] == 'scoped_compatibility_intent')
        self.assertFalse(change['whole_machine'])
        self.assertIn('certificate_validation', change['preserve'])

    def test_diagnostic_rules_require_removal(self):
        req = fixture()
        req['intent']['diagnostic_rule_refs'] = ['neutral-rule']
        result = r.compile_plan(req)
        self.assertTrue(next(x for x in result['proposed_changes'] if x['kind'] == 'temporary_diagnostic_rules')['removal_required'])

    def test_strict_input_rejects_raw_config_secret_or_commands(self):
        mutations = [lambda q: q.update(command='do-something'),
                     lambda q: q['facts'].update(secret='private'),
                     lambda q: q['intent'].update(egress_group_ref='https://private.example'),
                     lambda q: q.update(schema_version='next-version'),
                     lambda q: q.update(cancelled='yes'),
                     lambda q: q.update(scope_refs=[]),
                     lambda q: q['facts'].update(mode=True),
                     lambda q: q['facts']['dns']['edges'].append({'from': 'missing', 'to': 'resolver', 'path': 'normal'}),
                     lambda q: q['revisions'].update(effective='not-a-hash')]
        for mutate in mutations:
            with self.subTest(mutation=mutate):
                req = fixture()
                mutate(req)
                with self.assertRaises(r.InvalidProjection) as error:
                    r.compile_plan(req)
                self.assertNotIn('private', str(error.exception))

    def test_private_digests_never_enter_result(self):
        import json
        result = r.compile_plan(fixture())
        self.assertNotIn('a' * 64, json.dumps(result))
        self.assertNotIn('b' * 64, json.dumps(result))
        self.assertEqual(result['revision_refs']['effective'], 'snapshot-a')

    def test_revision_aliases_reject_hashes_and_cross_source_collisions(self):
        for value in ('a' * 64, 'b' * 64, 'c' * 64, 'A' * 64):
            with self.subTest(value=value[:1]):
                req = fixture()
                req['revision_refs']['effective'] = value
                with self.assertRaises(r.InvalidProjection):
                    r.compile_plan(req)
        req = fixture()
        req['revision_refs'] = dict(req['revisions'])
        with self.assertRaises(r.InvalidProjection):
            r.compile_plan(req)
        req = fixture()
        req['current_revisions']['extension'] = 'f' * 64
        req['revision_refs']['effective'] = req['current_revisions']['extension']
        with self.assertRaises(r.InvalidProjection):
            r.compile_plan(req)

    def test_compatibility_rule_binding_still_requires_rule_mode(self):
        req = fixture('scoped-compatibility')
        req['facts']['mode'] = 'direct'
        req['intent']['compatibility_action'] = 'restrict-webrtc'
        self.assertIn('RULE_MODE_CONFLICT', codes(r.compile_plan(req)))

    def test_control_claim_without_scopes_remains_unknown(self):
        req = fixture()
        del req['facts']['control']['scope_refs']
        result = r.compile_plan(req)
        self.assertIn('CONTROL_SCOPE_REFS_MISSING', codes(result))
        self.assertEqual(result['protected_control_path']['status'], 'unknown')

    def test_untyped_empty_group_unknown_protocol_and_named_direct(self):
        req = fixture()
        for node, expected in [
                ({'complete': 'yes', 'members': []}, 'EGRESS_NODE_TYPE_UNKNOWN'),
                ({'kind': 'group', 'complete': 'yes', 'members': []}, 'EMPTY_EGRESS_GROUP'),
                ({'kind': 'proxy', 'protocol': 'unknown', 'complete': 'yes', 'members': []}, 'EGRESS_PROTOCOL_UNKNOWN'),
                ({'kind': 'direct', 'complete': 'yes', 'members': []}, 'DIRECT_FALLBACK')]:
            req['facts']['groups']['node-a'] = node
            self.assertIn(expected, codes(r.compile_plan(req)))

    def test_backup_and_rollback_are_requirements_not_execution(self):
        result = r.compile_plan(fixture())
        self.assertTrue(result['requirements']['backup'])
        self.assertTrue(result['requirements']['rollback'])
        self.assertNotIn('commands', result)
        self.assertNotIn('patch', result)


if __name__ == '__main__':
    unittest.main()
