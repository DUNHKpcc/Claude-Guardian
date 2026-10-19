"""Exact ENV-T79 (L) and ENV-T90 (L+C) offline replay candidates.

No model, engine, real host approval or native network boundary is exercised.
Module/fixture loading occurs before the fail-fast I/O scope. C review is in
docs/evidence/rebuild-enforcement-cases.md, not inferred from matching keywords.
"""
from contextlib import contextmanager, ExitStack
from copy import deepcopy
from dataclasses import asdict
from enum import Enum
import hashlib
import io
import json
from pathlib import Path
import sys
from environment_entry_fixture import local_entry
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import inventory_cli
import remedy_plans
import rule_format_conversion as conversion
import rules_extension_plan as rules
import workflow_guard as workflow

SOURCE = b"payload:\n  - 'DOMAIN,claude.ai'\n  - 'DOMAIN-SUFFIX,anthropic.com'\n"
EXTENSION = b'# synthetic boundary fixture\nprepend: []\nappend: []\ndelete: []\n'
BASE = (b'proxy-groups:\n  - name: approved-group\n    type: select\n'
        b'    proxies: [node-a]\nrules:\n  - DOMAIN,rescue.invalid,Local\n'
        b'  - DOMAIN-SUFFIX,claude.ai,old-group\n'
        b'  - DOMAIN,api.anthropic.com,old-group\n  - MATCH,DIRECT\n')
EXPECTED_OUTPUT = (b'{"version":1,"rules":[{"domain":["claude.ai"]},'
                   b'{"domain_suffix":["anthropic.com"]}]}\n')
EXPECTED_CANDIDATE = (b'# synthetic boundary fixture\nprepend: '
                      b"['DOMAIN,claude.ai,approved-group', "
                      b"'DOMAIN-SUFFIX,anthropic.com,approved-group']\n"
                      b'append: []\ndelete: []\n')
FORBIDDEN_IO = ('builtins.open', 'io.open', 'os.open', 'socket.socket',
                'socket.create_connection', 'socket.getaddrinfo',
                'socket.gethostbyname', 'socket.gethostbyname_ex',
                'socket.gethostbyaddr', 'subprocess.Popen', 'os.system', 'os.popen')


@contextmanager
def offline_only():
    """Test sentinels, deliberately not represented as OS enforcement."""
    with ExitStack() as stack:
        mocks = {name: stack.enter_context(patch(name, side_effect=AssertionError(
            'forbidden fixture I/O: ' + name))) for name in FORBIDDEN_IO}
        yield mocks
        for mock in mocks.values():
            mock.assert_not_called()


def plain(value):
    if isinstance(value, Enum):
        return value.value
    if isinstance(value, dict):
        return {key: plain(item) for key, item in value.items()}
    if isinstance(value, (tuple, list)):
        return [plain(item) for item in value]
    return value


def decision(value):
    # Every public Decision dataclass field is included, including new fields.
    return plain(asdict(value))


def source_binding(raw):
    return {'schema_version': 'guardian-rule-source-binding/0.1',
            'source_ref': 'boundary-source', 'expected_sha256': hashlib.sha256(raw).hexdigest(),
            'evidence_kind': 'user_supplied', 'verified_at': '2026-10-18',
            'version_scope': 'synthetic-pinned-profile', 'purpose': 'offline-boundary-review',
            'client_scope': ['client-a'], 'feature_gate': 'fixture-only',
            'shared_service': False, 'activation_state': 'candidate'}


def compiler_inputs():
    revisions = {'extension': hashlib.sha256(EXTENSION).hexdigest(),
                 'effective': hashlib.sha256(BASE).hexdigest()}
    request = {'schema_version': 'guardian-remedy-plan-input/0.1',
        'target_ref': 'target-a', 'observed_target_ref': 'target-a',
        'route_ref': 'local-route', 'scope_refs': ['workflow-a'], 'template': 'keep-existing',
        'revisions': revisions, 'current_revisions': deepcopy(revisions),
        'revision_refs': {'effective': 'snapshot-a', 'extension': 'snapshot-b'},
        'intent': {'rule_refs': ['rule-a', 'rule-b'], 'egress_group_ref': 'approved-group',
                   'no_direct': 'yes', 'ipv6_goal': 'preserve', 'udp_goal': 'preserve'},
        'facts': {'versions': {'product': 'clash-verge-rev', 'gui': '2.5.8', 'core': '1.19.0'},
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
                    'bootstrap_known': 'yes', 'policy_merge_known': 'yes', 'responsibility': 'mihomo'}}}
    binding = {'schema_version': 'guardian-rules-extension-binding/0.1',
        'operation': 'insert_selected_prepend_rules', 'target_ref': 'target-a',
        'scope_refs': ['workflow-a'], 'layer_ref': 'extension', 'base_layer_ref': 'effective',
        'layer_kind': 'owned-profile-rules-extension', 'placement': 'prepend',
        'group_name': 'approved-group',
        'rules': {'rule-a': {'kind': 'DOMAIN', 'domain': 'claude.ai'},
                  'rule-b': {'kind': 'DOMAIN-SUFFIX', 'domain': 'anthropic.com'}},
        'rule_order': ['rule-a', 'rule-b'], 'protected_rule_indexes': [0]}
    return request, binding


def make_guard():
    binding = workflow.Binding('target-a', 'user-a', 'namespace-a', 'profile-a',
                               'config-a', 'network-a', 'runtime-a')
    local = workflow.Scope('ENV-06', workflow.Operation.PLAN, 'offline-plan',
                           'fixture', 'v1', 'fixture-install', 'fixture-platform')
    client = workflow.Scope('ENV-07', workflow.Operation.VERIFY, 'actual-client-hit',
                            'fixture', 'v1', 'fixture-install', 'fixture-platform',
                            contact=workflow.Contact.CLAUDE, endpoint_refs=('claude-scope',))
    # These are deliberately synthetic host assertions to exercise allowed
    # scheduling. No actual adapter, native test or human permission is claimed.
    support = tuple(workflow.AdapterSupport(scope, 'accepted', 'implemented',
                    'native_pass', 'synthetic-declaration') for scope in (local, client))
    approvals = []
    def fixture_reply(request):
        approvals.append(plain(asdict(request)))
        return workflow.Reply.APPROVED
    guard = workflow.WorkflowGuard(binding,
        workflow.Requirements(('preparation',), ('claude-domain-actual-hit',), ()),
        support, fixture_reply, clock=lambda: 20)
    ready = workflow.Readiness('complete', (), (), (), entry_request=local_entry(binding.target))
    preparation = workflow.Evidence('preparation', workflow.CheckStage.PRECONTACT,
        binding, 10, 100, workflow.EvidenceKind.TARGET_MANUAL, 'pass')
    return guard, local, client, ready, preparation, approvals


def replay_domains():
    request, binding = compiler_inputs()
    before = deepcopy((request, binding))
    with offline_only():
        converted = conversion.convert_rule_format(SOURCE, conversion.MIHOMO_CLASSICAL,
            conversion.SING_BOX, ['rule-a', 'rule-b'], source_binding(SOURCE))
        candidate = rules.compile_rules_extension(EXTENSION, BASE, request, binding)
        material = candidate.private_material()
        # Production compiler overlap calculation against exact host selectors:
        # this is an offline intersection, not a real client connection/match.
        hosts = ('claude.ai', 'www.claude.ai', 'notclaude.ai', 'claude.ai.invalid',
                 'anthropic.com', 'api.anthropic.com', 'deep.api.anthropic.com',
                 'notanthropic.com', 'anthropic.com.invalid')
        overlaps = [[host, rules._overlap(('DOMAIN', 'claude.ai'), ('DOMAIN', host)),
                     rules._overlap(('DOMAIN-SUFFIX', 'anthropic.com'), ('DOMAIN', host))]
                    for host in hosts]
        unknown_request = deepcopy(request)
        unknown_request['facts']['rules']['first_match_verified'] = 'unknown'
        unknown_plan = remedy_plans.compile_plan(unknown_request)
        try:
            rules.compile_rules_extension(EXTENSION, BASE, unknown_request, binding)
        except rules.RulesPlanError as exc:
            unknown_compile = str(exc)
        else:
            raise AssertionError('unknown declared rule priority must not yield a candidate')
        guard, local, client, ready, preparation, approvals = make_guard()
        pending = decision(guard.transition(workflow.Phase.PC1, (client,), ready, (preparation,), 20))
        invented_hit = workflow.Evidence('claude-domain-actual-hit',
            workflow.CheckStage.CLIENT_UNAUTHENTICATED, guard.binding, 10, 100,
            workflow.EvidenceKind.SYNTHETIC, 'pass')
        cannot_promote = decision(guard.transition(workflow.Phase.PC2, (client,), ready,
                                                   (preparation, invented_hit), 20))
        result = {'case_id': 'ENV-T79', 'conversion': converted.preview(),
            'output_utf8': converted.private_material()['output_bytes'].decode('utf-8'),
            'candidate_utf8': material['candidate_bytes'].decode('utf-8'),
            'compiler': candidate.preview(), 'offline_exact_host_intersections': overlaps,
            'known_priority_overlaps': plain(material['known_priority_overlaps']),
            'unknown_declared_priority_blockers': unknown_plan['blockers'],
            'unknown_declared_priority_compile': unknown_compile,
            'postcontact_check_schedule': pending, 'synthetic_hit_cannot_satisfy_check': cannot_promote,
            'approval_fixture_calls': approvals}
        assert (request, binding) == before
        return result


def replay_enforcement():
    guard, local, client, ready, preparation, approvals = make_guard()
    with offline_only():
        initial = {'snapshot': guard.snapshot(), 'state': plain(asdict(guard.state))}
        local_action = workflow.Action(local, guard.binding, 'plan-a', 10, 100,
                                       permissions_verified=True)
        local_decision = decision(guard.evaluate(local_action, workflow.Readiness(), (), 20))
        denied = []
        for surface in ('browser', 'hosted-search', 'mcp', 'shell', 'computer-use', 'connector'):
            scope = workflow.Scope('ENV-07', workflow.Operation.VERIFY, surface,
                'fixture', 'v1', 'fixture-install', 'fixture-platform',
                contact=workflow.Contact.CLAUDE, endpoint_refs=('claude-scope',))
            denied.append([surface, decision(guard.evaluate(workflow.Action(scope, guard.binding,
                'plan-a', 10, 100, permissions_verified=True), ready, (), 20))])
        after_denials = guard.snapshot()
        guard.record_observed_contact()
        observed = guard.snapshot()
        guard.resume({'phase': 'authenticated_use', 'gate_state': 'open_scoped',
                      'observed_contact': 'observed'})
        resumed = {'snapshot': guard.snapshot(), 'state': plain(asdict(guard.state))}
        output, prompt = io.StringIO(), io.StringIO()
        code = inventory_cli.run(['workflow-status'], incoming=io.StringIO(''),
                                 outgoing=output, prompt=prompt)
        return {'case_id': 'ENV-T90', 'initial': initial, 'allowed_local_plan': local_decision,
                'denied_contact_surfaces': denied, 'after_denials': after_denials,
                'observed_contact': observed, 'resumed': resumed,
                'approval_fixture_calls': approvals, 'workflow_cli': json.loads(output.getvalue()),
                'workflow_cli_exit': code, 'workflow_cli_prompt': prompt.getvalue()}


def replay():
    return [replay_domains(), replay_enforcement()]


class BoundaryRebuildTests(unittest.TestCase):
    def test_env79_exact_conversion_compiler_and_overlap_outputs(self):
        result = replay_domains()
        self.assertEqual(result['output_utf8'].encode('utf-8'), EXPECTED_OUTPUT)
        self.assertEqual(result['candidate_utf8'].encode('utf-8'), EXPECTED_CANDIDATE)
        self.assertEqual(result['offline_exact_host_intersections'], [
            ['claude.ai', True, False], ['www.claude.ai', False, False],
            ['notclaude.ai', False, False], ['claude.ai.invalid', False, False],
            ['anthropic.com', False, True], ['api.anthropic.com', False, True],
            ['deep.api.anthropic.com', False, True], ['notanthropic.com', False, False],
            ['anthropic.com.invalid', False, False]])
        self.assertEqual(result['known_priority_overlaps'], [
            ['rule-a', 'base', 1, 'DOMAIN-SUFFIX,claude.ai,old-group'],
            ['rule-a', 'base', 3, 'MATCH,DIRECT'],
            ['rule-b', 'base', 2, 'DOMAIN,api.anthropic.com,old-group'],
            ['rule-b', 'base', 3, 'MATCH,DIRECT']])
        self.assertEqual(result['conversion'], {
            'schema_version': 'guardian-rule-conversion-preview/0.1',
            'status': 'converted_predicates_only', 'record_count': 2,
            'exact_count': 1, 'suffix_count': 1, 'output_bytes_count': len(EXPECTED_OUTPUT),
            'apply_supported': False, 'authorization': 'not_required_for_offline_conversion',
            'native_acceptance': 'not_run', 'effective_priority': 'not_established',
            'equivalence_scope': 'canonical_lowercase_ascii_predicates_only',
            'source_authenticity': 'not_established', 'source_freshness': 'not_established',
            'independent_sources': 'not_established'})
        self.assertEqual(result['compiler'], {
            'schema_version': 'guardian-rules-extension-preview/0.1',
            'status': 'candidate_only_blocked', 'apply_supported': False,
            'operation': 'insert_selected_prepend_rules', 'added_rules': 2, 'matched_rules': 0,
            'placement': 'explicit_prepend_before_base_rules', 'known_base_overlap_count': 4,
            'known_append_overlap_count': 0, 'unknown_base_or_append_rule_count': 0,
            'protected_index_coverage': 'caller_declared_unverified', 'other_bytes': 'preserved',
            'append_and_delete': 'unchanged', 'authorization': 'pending', 'native_acceptance': 'not_run',
            'blockers': ['NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED', 'VERSION_CAPABILITY_UNVERIFIED',
                'NATIVE_ACCEPTANCE_NOT_RUN', 'EFFECTIVE_RULE_PRIORITY_UNVERIFIED',
                'BASE_RULE_GRAPH_UNVERIFIED', 'GROUP_GRAPH_UNVERIFIED',
                'PROTECTED_RULE_COVERAGE_UNVERIFIED', 'LATER_MERGE_SCRIPT_EFFECTS_UNVERIFIED',
                'ACTION_AUTHORIZATION_PENDING']})

    def test_env79_actual_hit_remains_a_postcontact_check(self):
        result = replay_domains()
        self.assertEqual(result['unknown_declared_priority_blockers'], [
            {'code': 'NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED', 'state': 'unknown'},
            {'code': 'NATIVE_ACCEPTANCE_NOT_RUN', 'state': 'unknown'},
            {'code': 'VERSION_CAPABILITY_UNVERIFIED', 'state': 'unknown'},
            {'code': 'RULES_FIRST_MATCH_VERIFIED', 'state': 'unknown'}])
        self.assertEqual(result['unknown_declared_priority_compile'], 'SEMANTIC_PLAN_BLOCKED')
        expected = expected_decision(True, (), ('claude-domain-actual-hit',))
        self.assertEqual(result['postcontact_check_schedule'], expected)
        self.assertEqual(result['synthetic_hit_cannot_satisfy_check'],
                         expected_decision(False, ('EVIDENCE_REQUIRED:claude-domain-actual-hit',)))
        self.assertEqual(result['approval_fixture_calls'], [{
            'purpose': 'handoff:controlled_contact', 'binding': expected_binding(),
            'scopes': [expected_scopes()[1]], 'plan_ref': '', 'review_ref': '', 'evaluated_at': 20}])

    def test_env90_complete_public_output(self):
        result = replay_enforcement()
        state = {'phase': 'precontact', 'gate': 'closed', 'scopes': [], 'observed_contact': 'not_measured'}
        snapshot = {'phase': 'precontact', 'gate_state': 'closed', 'observed_contact': 'not_measured',
                    'runtime_permission_restorable': False}
        self.assertEqual(result['initial'], {'snapshot': snapshot, 'state': state})
        self.assertEqual(result['allowed_local_plan'], expected_decision(True))
        for surface, actual in result['denied_contact_surfaces']:
            self.assertEqual(actual, expected_decision(False, (
                'UNSUPPORTED_OPERATION_SCOPE', 'CONTACT_GATE_CLOSED_OR_OUT_OF_SCOPE',
                'EVIDENCE_REQUIRED:preparation')), surface)
        self.assertEqual([item[0] for item in result['denied_contact_surfaces']],
                         ['browser', 'hosted-search', 'mcp', 'shell', 'computer-use', 'connector'])
        self.assertEqual(result['after_denials'], snapshot)
        self.assertEqual(result['observed_contact'], dict(snapshot, gate_state='revoked', observed_contact='observed'))
        self.assertEqual(result['resumed'], {
            'snapshot': dict(snapshot, observed_contact='previous_contact_reported'),
            'state': dict(state, observed_contact='previous_contact_reported')})
        self.assertEqual(result['approval_fixture_calls'], [{
            'purpose': 'action:plan', 'binding': expected_binding(),
            'scopes': [expected_scopes()[0]], 'plan_ref': 'plan-a', 'review_ref': '', 'evaluated_at': 20}])
        self.assertEqual(result['workflow_cli'], {
            'schema_version': 'guardian-inventory-cli-result/1', 'status': 'partial',
            'changes': [], 'contact_phase': 'precontact', 'gate_state': 'closed',
            'permission_restorable': False,
            'boundary': 'Caller-asserted target/user/namespace and local hydrated storage; '
                'terminal response is not authenticated consent or host/OS approval. '
                'No saved grants, OS isolation, controller access, or readiness claim.',
            'workflow': {'phase': 'precontact', 'gate_state': 'closed',
                'observed_contact': 'not_measured', 'scope': 'new_process_default_only',
                'transition_available': False}})
        self.assertEqual(result['workflow_cli_exit'], 0)
        self.assertEqual(result['workflow_cli_prompt'], '')

    def test_replay_is_deterministic(self):
        self.assertEqual(replay(), replay())

    def test_env79_invalid_mixed_source_is_atomic_offline(self):
        for raw in (SOURCE + b"  - 'IP-ASN,13335'\n", b"payload:\n  - 'IP-ASN,13335'\n" + SOURCE.split(b'\n', 1)[1]):
            with self.subTest(raw=raw), offline_only():
                with self.assertRaisesRegex(conversion.ConversionError, '^UNREPRESENTABLE_MATCH$'):
                    conversion.convert_rule_format(raw, conversion.MIHOMO_CLASSICAL,
                        conversion.SING_BOX, ['rule-a', 'rule-b', 'rule-c'], source_binding(raw))

    def test_env79_cancel_and_protected_rule_fail_without_io(self):
        request, binding = compiler_inputs()
        with offline_only():
            with self.assertRaisesRegex(conversion.ConversionError, '^CANCELLED$'):
                conversion.convert_rule_format(SOURCE, conversion.MIHOMO_CLASSICAL,
                    conversion.SING_BOX, ['rule-a', 'rule-b'], source_binding(SOURCE),
                    cancelled=lambda: True)
            binding['protected_rule_indexes'] = [0, 1]
            with self.assertRaisesRegex(rules.RulesPlanError, '^PROTECTED_RULE_PRIORITY_CONFLICT$'):
                rules.compile_rules_extension(EXTENSION, BASE, request, binding)

    def test_env90_host_denial_cancellation_and_missing_permission_stay_workflow_only(self):
        guard, local, client, ready, preparation, approvals = make_guard()
        action = workflow.Action(local, guard.binding, 'plan-a', 10, 100,
                                 permissions_verified=True)
        with offline_only():
            for reply in (workflow.Reply.DENIED, workflow.Reply.CANCELLED,
                          workflow.Reply.TIMEOUT, True, None):
                guard.authorize = lambda request, reply=reply: reply
                self.assertEqual(decision(guard.evaluate(action, ready, (), 20)),
                                 expected_decision(False, ('CURRENT_EXACT_APPROVAL_REQUIRED',)))
            no_permission = workflow.Action(local, guard.binding, 'plan-a', 10, 100)
            self.assertEqual(decision(guard.evaluate(no_permission, ready, (), 20)),
                             expected_decision(False, ('HOST_OS_PERMISSION_REQUIRED',)))
            self.assertEqual(approvals, [])

    def test_env79_same_source_with_suffix_request_does_not_contact_dns(self):
        # Reverse compiler intersection operands, and include an exact-host
        # selector equal to the suffix itself: the production relation must
        # retain the apex without accepting an adjacent textual lookalike.
        with offline_only():
            for host, expected in (('anthropic.com', True), ('api.anthropic.com', True),
                                   ('notanthropic.com', False), ('anthropic.com.invalid', False)):
                self.assertIs(rules._overlap(('DOMAIN', host),
                              ('DOMAIN-SUFFIX', 'anthropic.com')), expected)


def expected_binding():
    return {'target': 'target-a', 'user': 'user-a', 'namespace': 'namespace-a',
            'profile': 'profile-a', 'configuration': 'config-a', 'network': 'network-a',
            'runtime_version': 'runtime-a'}


def expected_scopes():
    common = {'product': 'fixture', 'version': 'v1', 'installation': 'fixture-install',
              'platform': 'fixture-platform', 'risk': 'read', 'requires_authentication': False}
    return [dict(common, module='ENV-06', operation='plan', action='offline-plan',
                 contact='local', endpoint_refs=[]),
            dict(common, module='ENV-07', operation='verify', action='actual-client-hit',
                 contact='claude', endpoint_refs=['claude-scope'])]


def expected_decision(allowed, gaps=(), pending=()):
    return {'allowed': allowed, 'gaps': list(gaps), 'supported_scopes': expected_scopes(),
            'pending_checks': list(pending), 'enforcement_level': 'workflow_guard', 'executes': False}


if __name__ == '__main__':
    if sys.argv[1:] == ['--replay']:
        print(json.dumps(replay(), ensure_ascii=False, indent=2, sort_keys=True))
    else:
        unittest.main()
