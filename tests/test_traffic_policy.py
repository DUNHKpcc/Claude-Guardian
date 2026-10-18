"""Offline product-policy tests; never native enforcement evidence."""
import importlib
from pathlib import Path
import sys
import unittest
ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))

class TrafficPolicyAPITests(unittest.TestCase):
    def test_shared_default_exists(self):
        p = importlib.import_module('traffic_policy')
        self.assertEqual(p.policy_projection()['policy'], 'IPv4_ONLY')


from copy import deepcopy
from dataclasses import FrozenInstanceError
import json
import pickle
import subprocess
import tempfile
from unittest.mock import patch

import traffic_policy as policy
import guardian
import interview_flow
import agent_remediation
import remedy_plans
import status_dashboard

EXPECTED = {
    'schema_version': 'guardian-traffic-policy/0.1',
    'requirement_id': 'PRODUCT-IPV4-20261018', 'effective_from': '2026-10-18',
    'policy': 'IPv4_ONLY', 'applies_to': 'claude_target_application_traffic',
    'ipv6_fallback': 'forbidden', 'proxy_outer_transport': 'preserve_existing_independently',
    'control_channels': 'preserve', 'other_applications': 'unchanged',
    'enforcement_status': 'unknown', 'compliance': 'not_established',
    'environment_pass': False, 'apply_supported': False, 'authorization': 'none',
}


def scope():
    return {'schema_version': 'guardian-ipv4-policy-scope/0.1', 'target_ref': 'device-a',
            'application_scope_refs': ['claude-app', 'claude-child'],
            'target_leg_scope_refs': ['proxy-to-target'], 'proxy_outer_scope_refs': ['outer-ipv6'],
            'control_scope_refs': ['codex-control'], 'other_application_scope_refs': ['other-app'],
            'scope_support': 'supported', 'target_outer_separation': 'declared',
            'ipv6_fallback': 'excluded', 'outer_transport_preserved': 'declared',
            'control_channels_preserved': 'declared', 'other_applications_preserved': 'declared',
            'configuration_state': 'current_declared'}


def finding(*codes):
    return {'schema_version': 'guardian-remediation-findings/0.1', 'target_ref': 'device-a',
            'findings': [{'code': code} for code in codes]}


class TrafficPolicyTests(unittest.TestCase):
    def reject(self, value, code='INVALID_POLICY_SCOPE', **kwargs):
        with self.assertRaisesRegex(policy.TrafficPolicyError, '^' + code + '$'):
            policy.plan_ipv4_only(value, **kwargs)

    def test_default_exact_immutable_and_fresh_projections(self):
        self.assertEqual(policy.policy_projection(), EXPECTED)
        self.assertEqual(policy.TrafficPolicy().policy, 'IPv4_ONLY')
        with self.assertRaises(FrozenInstanceError):
            policy.TrafficPolicy().policy = 'dual_stack'
        with self.assertRaises(TypeError):
            policy.TrafficPolicy(policy='dual_stack')
        projection = policy.policy_projection()
        projection['policy'] = 'dual_stack'
        self.assertEqual(policy.policy_projection(), EXPECTED)

    def test_complete_declarations_never_native_enforcement_or_permission(self):
        plan = policy.plan_ipv4_only(scope())
        view = plan.preview()
        self.assertEqual(view['planning_status'], 'conditional_plan')
        self.assertEqual(view['enforcement_status'], 'unknown')
        self.assertEqual(view['reason_codes'], ['IPV4_ONLY_ENFORCEMENT_UNKNOWN', 'IPV4_ONLY_VERIFICATION_NOT_RUN'])
        for key, value in EXPECTED.items():
            self.assertEqual(view[key], value)
        self.assertEqual(view['evidence'], 'declared_unverified')
        self.assertEqual(view['native_acceptance'], 'not_run')
        self.assertEqual(view['target_binding'], 'not_established')
        self.assertFalse(view['target_mutation_supported'])

    def test_missing_scope_and_unsupported_do_not_downgrade_policy(self):
        view = policy.plan_ipv4_only().preview()
        self.assertEqual(view['planning_status'], 'unresolved')
        self.assertIn('IPV4_ONLY_SCOPE_UNBOUND', view['reason_codes'])
        data = scope(); data['scope_support'] = 'unsupported'
        view = policy.plan_ipv4_only(data).preview()
        self.assertEqual(view['enforcement_status'], 'unsupported')
        self.assertEqual(view['planning_status'], 'unsupported')
        self.assertEqual(view['policy'], 'IPv4_ONLY')
        self.assertEqual(view['ipv6_fallback'], 'forbidden')
        self.assertFalse(view['apply_supported'])

    def test_target_and_outer_ipv6_are_separate(self):
        data = scope()
        material = policy.plan_ipv4_only(data).private_material()
        self.assertEqual(dict(material['declared_scope'])['proxy_outer_scope_refs'], ('outer-ipv6',))
        self.assertEqual(material['planning_status'], 'conditional_plan')
        for field in ('proxy_outer_scope_refs', 'control_scope_refs', 'other_application_scope_refs'):
            data = scope(); data[field] = ['claude-app']
            view = policy.plan_ipv4_only(data).preview()
            self.assertEqual(view['planning_status'], 'blocked')
            self.assertIn('IPV4_ONLY_PRESERVED_SCOPE_CONFLICT', view['reason_codes'])
            self.assertEqual(view['proxy_outer_transport'], 'preserve_existing_independently')

    def test_ipv6_fallback_and_stale_configuration_never_pass(self):
        for field, value, code in [
                ('ipv6_fallback', 'present', 'IPV4_ONLY_INTENT_CONFLICT'),
                ('configuration_state', 'stale', 'IPV4_ONLY_CONFIGURATION_STALE')]:
            data = scope(); data[field] = value
            view = policy.plan_ipv4_only(data).preview()
            self.assertEqual(view['planning_status'], 'blocked')
            self.assertIn(code, view['reason_codes'])
            self.assertFalse(view['environment_pass'])
        data = scope(); data['ipv6_fallback'] = 'unknown'
        self.assertEqual(policy.plan_ipv4_only(data).preview()['planning_status'], 'unresolved')

    def test_missing_preservation_or_scope_cannot_certify(self):
        for field in ['scope_support', 'target_outer_separation', 'outer_transport_preserved',
                      'control_channels_preserved', 'other_applications_preserved', 'configuration_state']:
            data = scope(); data[field] = 'unknown'
            view = policy.plan_ipv4_only(data).preview()
            self.assertEqual(view['planning_status'], 'unresolved')
            self.assertEqual(view['compliance'], 'not_established')
        for field in ['application_scope_refs', 'target_leg_scope_refs']:
            data = scope(); data[field] = []
            self.assertIn('IPV4_ONLY_SCOPE_UNBOUND', policy.plan_ipv4_only(data).preview()['reason_codes'])

    def test_strict_scope_rejects_forged_approval_success_and_policy(self):
        for key, value in [('native_pass', True), ('authorization', True), ('compliance', 'passed'),
                           ('policy', 'dual_stack'), ('AAAA_empty', True), ('curl4_success', True),
                           ('https_success', True), ('ipv6_timeout', True), ('command', 'private')]:
            data = scope(); data[key] = value
            self.reject(data)
        for field in policy._ENUM_FIELDS:
            for value in [True, False, None, 1, 'verified', 'passed', 'PRIVATE-SENTINEL']:
                data = scope(); data[field] = value
                self.reject(data)
        for value in [[], True, {}, 'private']:
            self.reject(value)

    def test_bounded_aliases_refs_and_no_private_error_echo(self):
        for ref in ['private.example.invalid', 'x' * 65, '', 'sk-ant-api03-' + 'x' * 20,
                    '/private/sentinel', True, None]:
            data = scope(); data['application_scope_refs'] = [ref]
            self.reject(data)
        data = scope(); data['application_scope_refs'] *= 2
        self.reject(data, 'DUPLICATE_POLICY_SCOPE')
        data = scope(); data['application_scope_refs'] = ['app-' + str(i) for i in range(65)]
        self.reject(data, 'POLICY_SCOPE_BUDGET_EXCEEDED')
        data = scope()
        for field in policy._REF_FIELDS:
            data[field] = [field.replace('_', '-') + str(i) for i in range(64)]
        self.reject(data, 'POLICY_SCOPE_BUDGET_EXCEEDED')

    def test_private_result_constructor_cannot_forge_passed_status(self):
        private = policy.plan_ipv4_only(scope())
        args = [private._scope, private._reasons, private._planning_status, private._enforcement_status]
        for index, value in [(1, ('PRIVATE-SENTINEL',)), (2, 'passed'), (3, 'verified'),
                             (0, (('private', 'sentinel'),)), (1, ())]:
            bad = list(args); bad[index] = value
            with self.assertRaisesRegex(policy.TrafficPolicyError, '^INVALID_POLICY_PLAN$'):
                policy.PrivatePolicyPlan(*bad)
        with self.assertRaises(FrozenInstanceError):
            private._enforcement_status = 'passed'

    def test_constructor_cannot_remove_conflicts_or_forge_conditional_plan(self):
        data = scope()
        data['control_scope_refs'] = ['claude-app']
        data['ipv6_fallback'] = 'present'
        data['configuration_state'] = 'stale'
        actual = policy.plan_ipv4_only(data)
        self.assertEqual(actual.preview()['planning_status'], 'blocked')
        reasons = ('IPV4_ONLY_ENFORCEMENT_UNKNOWN', 'IPV4_ONLY_VERIFICATION_NOT_RUN')
        for snapshot, selected_reasons, planning, enforcement in [
                (actual._scope, reasons, 'conditional_plan', 'unknown'),
                ((), reasons, 'conditional_plan', 'unknown'),
                (actual._scope, actual._reasons, 'conditional_plan', 'unknown'),
                (actual._scope * 1000, actual._reasons, 'blocked', 'unknown'),
                ((('target_ref', 'device-a', 'extra'),), reasons, 'unresolved', 'unknown')]:
            with self.assertRaisesRegex(policy.TrafficPolicyError, '^INVALID_POLICY_PLAN$'):
                policy.PrivatePolicyPlan(snapshot, selected_reasons, planning, enforcement)

    def test_private_repr_serialization_and_public_projection(self):
        plan = policy.plan_ipv4_only(scope())
        public = json.dumps(plan.preview()) + repr(plan)
        for value in ['device-a', 'claude-app', 'outer-ipv6', 'codex-control']:
            self.assertNotIn(value, public)
        with self.assertRaises(TypeError):
            json.dumps(plan)
        with self.assertRaises(TypeError):
            pickle.dumps(plan)
        material = plan.private_material(); material['policy']['policy'] = 'changed'
        self.assertEqual(plan.private_material()['policy'], EXPECTED)

    def test_snapshot_before_callbacks_and_input_immutability(self):
        data = scope(); original = deepcopy(data)
        def mutate():
            data['application_scope_refs'][:] = ['changed']
            data['ipv6_fallback'] = 'present'
            return False
        plan = policy.plan_ipv4_only(data, cancelled=mutate)
        self.assertEqual(dict(plan.private_material()['declared_scope'])['application_scope_refs'],
                         tuple(original['application_scope_refs']))
        self.assertEqual(plan.preview()['planning_status'], 'conditional_plan')
        policy.plan_ipv4_only(original)
        self.assertEqual(original, scope())

    def test_cancellation_at_every_guard_and_callback_failures(self):
        calls = []
        policy.plan_ipv4_only(scope(), cancelled=lambda: calls.append(1) or False)
        for boundary in range(1, len(calls) + 1):
            count = 0
            def stop():
                nonlocal count
                count += 1
                return count == boundary
            self.reject(scope(), 'CANCELLED', cancelled=stop)
        for callback in [lambda: None, lambda: 0, lambda: (_ for _ in ()).throw(ValueError('PRIVATE'))]:
            self.reject(scope(), 'CANCELLED', cancelled=callback)

    def test_deadlines_initial_and_final(self):
        for seconds in [False, 0, -1, 61, float('inf'), float('nan'), None, '5']:
            self.reject(scope(), 'INVALID_DEADLINE', max_seconds=seconds)
        with patch.object(policy.time, 'monotonic', side_effect=[0, 6]):
            self.reject(scope(), 'DEADLINE_EXCEEDED')
        calls = []
        with patch.object(policy.time, 'monotonic', side_effect=lambda: calls.append(1) or 0):
            policy.plan_ipv4_only(scope())
        with patch.object(policy.time, 'monotonic', side_effect=[0] * (len(calls) - 1) + [6]):
            self.reject(scope(), 'DEADLINE_EXCEEDED')

    def test_no_io_during_policy_planning(self):
        with patch('builtins.open', side_effect=AssertionError('file')), \
             patch('socket.socket', side_effect=AssertionError('network')), \
             patch('subprocess.Popen', side_effect=AssertionError('process')):
            self.assertEqual(policy.plan_ipv4_only(scope()).preview()['policy'], 'IPv4_ONLY')


class PolicyIntegrationTests(unittest.TestCase):
    def test_report_assessment_and_selection_share_exact_default(self):
        state = interview_flow.new_state('device-a', 'account-a')
        saved = deepcopy(state)
        self.assertEqual(interview_flow.assessment(state)['traffic_policy'], EXPECTED)
        self.assertEqual(state, saved)
        self.assertEqual(guardian.base('analyze', 'device-a')['traffic_policy'], EXPECTED)
        result = agent_remediation.select(finding(), 'device-a')
        self.assertEqual(result['traffic_policy'], EXPECTED)
        self.assertEqual(result['actions'], [])
        self.assertFalse(result['environment_pass'])
        self.assertEqual(interview_flow.assessment(state)['G3']['status'], 'blocked')

    def test_legacy_interview_state_gets_current_policy_without_new_fact_or_permission(self):
        state = interview_flow.new_state('device-a', 'account-a')
        self.assertNotIn('traffic_policy', state)
        raw = interview_flow.dumps_state(state, host_opt_in=True)
        restored = interview_flow.loads_state(raw)
        self.assertEqual(restored['facts'], state['facts'])
        self.assertEqual(restored['context'], state['context'])
        self.assertEqual(interview_flow.assessment(restored)['traffic_policy'], EXPECTED)
        self.assertEqual(interview_flow.assessment(restored)['G3']['status'], 'blocked')

    def test_fixed_policy_action_requires_specific_review_not_native_execute(self):
        for code in policy.REASON_CODES:
            result = agent_remediation.select(finding(code), 'device-a')
            item = result['actions'][0]
            self.assertEqual(item['action_id'], 'ipv4-only-policy')
            self.assertEqual(item['kind'], 'candidate_only')
            self.assertIsNone(item['command_template'])
            self.assertFalse(item['target_mutation_supported'])
            self.assertEqual(result['authority'], 'none')
            self.assertIn('obtain_required_specific_approval', item['fallback_requirements'])
            self.assertIn('not_available', item['builtin_execution'])

    def test_cancellation_prerequisites_and_no_change_keep_priority(self):
        for code, action in [('USER_CANCELLED', 'stop'), ('NO_CHANGE_TO_EXECUTE', 'no-change')]:
            result = agent_remediation.select(finding(code, 'IPV4_ONLY_ENFORCEMENT_UNKNOWN'), 'device-a')
            self.assertEqual([a['action_id'] for a in result['actions']], [action])
            self.assertEqual(result['next_phase'], 'stop')
        result = agent_remediation.select(finding('TARGET_MISMATCH', 'IPV4_ONLY_ENFORCEMENT_UNKNOWN'), 'device-a')
        self.assertTrue(result['prerequisite_blockers'])
        self.assertTrue(all(a['agent_fallback'] == 'none' for a in result['actions']))
        result = agent_remediation.select(finding('IPV6_TIMEOUT_ONLY'), 'device-a')
        self.assertEqual(result['actions'][0]['action_id'], 'keep')
        self.assertFalse(result['environment_pass'])

    def test_imported_policy_claims_do_not_override_current_policy_or_authorize(self):
        report = finding('IPV4_ONLY_SCOPE_UNSUPPORTED')
        report.update(traffic_policy={'policy': 'dual_stack', 'compliance': 'verified'}, authorization=True)
        result = agent_remediation.select(report, 'device-a')
        self.assertEqual(result['traffic_policy'], EXPECTED)
        self.assertEqual(result['authority'], 'none')
        self.assertFalse(result['environment_pass'])

    def test_semantic_policy_is_separate_from_legacy_rule_candidate(self):
        from test_remedy_plans import fixture
        request = fixture()
        result = remedy_plans.compile_plan(request)
        self.assertEqual({r['code'] for r in result['blockers']},
                         {'NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED', 'NATIVE_ACCEPTANCE_NOT_RUN',
                          'VERSION_CAPABILITY_UNVERIFIED'})
        self.assertEqual(len(result['proposed_changes']), 1)
        self.assertEqual(result['proposed_changes'][0]['kind'], 'bind_selected_rules')
        self.assertEqual(result['traffic_policy']['policy'], 'IPv4_ONLY')
        self.assertIn('IPV4_ONLY_INTENT_CONFLICT', result['traffic_policy']['reason_codes'])
        self.assertFalse(result['traffic_policy']['environment_pass'])
        separate = remedy_plans.compile_ipv4_policy_plan(scope()).preview()
        self.assertEqual(separate['planning_status'], 'conditional_plan')
        self.assertEqual(separate['proxy_outer_transport'], 'preserve_existing_independently')
        self.assertFalse(separate['apply_supported'])

    def test_dashboard_does_not_trust_forged_compliance_or_sample_success(self):
        report = guardian.base('audit', 'device-a')
        report['traffic_policy'] = {'policy': 'dual_stack', 'compliance': 'verified',
                                    'native_pass': True, 'private': '<script>SECRET</script>'}
        report.update(AAAA_empty=True, curl4_success=True, https_success=True, ipv6_timeout=True)
        view = status_dashboard.project(report)
        self.assertEqual(view['traffic_policy'], EXPECTED)
        self.assertNotEqual(view['overall'], 'verified')
        self.assertFalse(any(c['state'] == 'verified' for c in view['cards']))
        html = status_dashboard.render(report)
        self.assertIn('IPv4_ONLY', html)
        self.assertIn('禁止IPv6回退', html)
        self.assertIn('保留代理外层IPv6', html)
        self.assertNotIn('SECRET', html)
        report.pop('traffic_policy')
        self.assertEqual(status_dashboard.project(report)['traffic_policy'], EXPECTED)

    def test_fixed_policy_envelope_member_validated_and_legacy_omission_supported(self):
        report = guardian.interview({'schema_version': 'guardian-interview/0.1', 'answers': {}})
        guardian.validate_interview_envelope(report)
        legacy = deepcopy(report); legacy.pop('traffic_policy')
        guardian.validate_interview_envelope(legacy)
        for key, value in [('policy', 'dual_stack'), ('environment_pass', 0),
                           ('apply_supported', True), ('compliance', 'verified')]:
            forged = deepcopy(report); forged['traffic_policy'][key] = value
            with self.assertRaises(guardian.GuardianError):
                guardian.validate_interview_envelope(forged)
        report['traffic_policy']['extra'] = 'private'
        with self.assertRaises(guardian.GuardianError):
            guardian.validate_interview_envelope(report)

    def test_fixed_policy_redaction_roundtrip_never_exempts_arbitrary_authorization(self):
        report = guardian.interview({'schema_version': 'guardian-interview/0.1', 'answers': {}})
        public = guardian.redact(report)
        self.assertEqual(public['traffic_policy'], EXPECTED)
        guardian.validate_interview_envelope(public)
        for value in ['Bearer synthetic-secret', 'approved', True, None]:
            forged = deepcopy(EXPECTED); forged['authorization'] = value
            self.assertEqual(guardian.redact(forged)['authorization'], '[redacted]')
        extra = deepcopy(EXPECTED); extra['private_token'] = 'synthetic-secret'
        self.assertEqual(guardian.redact(extra)['authorization'], '[redacted]')
        self.assertEqual(guardian.redact(extra)['private_token'], '[redacted]')

    def test_policy_html_respects_existing_fail_closed_preview_allowlist(self):
        spec = importlib.util.spec_from_file_location('policy_preview', ROOT / 'tools/render_dashboard_preview.py')
        preview = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(preview)
        html = preview.synthetic_html()
        self.assertIn('IPv4_ONLY', html)
        preview.validate_html(html)
        with self.assertRaises(preview.PreviewError):
            preview.validate_html(html + '<script>private</script>')

    def test_file_path_imports_do_not_depend_on_sys_path_or_test_order(self):
        scripts = ROOT / 'skills/claude-guardian/scripts'
        with tempfile.TemporaryDirectory() as tmp:
            for name, expression in [('guardian', "m.base('audit')['traffic_policy']"),
                    ('interview_flow', "m.assessment(m.new_state('device-a','account-a'))['traffic_policy']"),
                    ('remedy_plans', "m.compile_ipv4_policy_plan().preview()")]:
                code = ("import importlib.util,json; s=importlib.util.spec_from_file_location('isolated'," +
                        repr(str(scripts / (name + '.py'))) + ");m=importlib.util.module_from_spec(s);"
                        "s.loader.exec_module(m);print(json.dumps(" + expression + "))")
                result = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=tmp,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['policy'], 'IPv4_ONLY')


if __name__ == '__main__':
    unittest.main()
