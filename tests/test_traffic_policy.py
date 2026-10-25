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
    'schema_version': 'guardian-traffic-policy/0.2', 'policy': 'IPv4_ONLY', 'applies_to': 'whole_machine',
    'ipv6': 'disabled', 'ipv6_fallback': 'forbidden', 'windows_adapter_ipv6': 'disabled_by_default',
    'on_proxy_failure': 'no_direct', 'exceptions': 'explicit_user_request_only',
    'measured_by': 'network_check.py', 'judged_by': 'egress_verifier.py',
}


def finding(*codes):
    return {'schema_version': 'guardian-remediation-findings/0.1', 'target_ref': 'device-a',
            'findings': [{'code': code} for code in codes]}


class PolicyIntegrationTests(unittest.TestCase):
    def test_default_exact_immutable_and_fresh_projections(self):
        self.assertEqual(policy.policy_projection(), EXPECTED)
        first = policy.policy_projection()
        first['policy'] = 'dual_stack'
        self.assertEqual(policy.policy_projection(), EXPECTED)
        with self.assertRaises(FrozenInstanceError):
            policy.TrafficPolicy().policy = 'dual_stack'
        with self.assertRaises(TypeError):
            policy.TrafficPolicy(policy='dual_stack')

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
        for code in ('IPV6_EXIT_OBSERVED', 'LAYER_IPV6_PROBE_FAIL'):
            result = agent_remediation.select(finding(code), 'device-a')
            item = result['actions'][0]
            self.assertEqual(item['action_id'], 'ipv4-only-policy')
            self.assertEqual(item['kind'], 'agent_investigation')
            self.assertEqual(item['command_template'][1], 'scripts/network_check.py')
            self.assertEqual(result['authority'], 'none')

    def test_cancellation_prerequisites_and_no_change_keep_priority(self):
        for code, action in [('USER_CANCELLED', 'stop'), ('NO_CHANGE_TO_EXECUTE', 'no-change')]:
            result = agent_remediation.select(finding(code, 'IPV6_EXIT_OBSERVED'), 'device-a')
            self.assertEqual([a['action_id'] for a in result['actions']], [action])
            self.assertEqual(result['next_phase'], 'stop')
        result = agent_remediation.select(finding('TARGET_MISMATCH', 'IPV6_EXIT_OBSERVED'), 'device-a')
        self.assertTrue(result['prerequisite_blockers'])
        self.assertTrue(all(a['agent_fallback'] == 'none' for a in result['actions']))
        result = agent_remediation.select(finding('IPV6_TIMEOUT_ONLY'), 'device-a')
        self.assertEqual(result['actions'][0]['action_id'], 'keep')
        self.assertFalse(result['environment_pass'])

    def test_imported_policy_claims_do_not_override_current_policy_or_authorize(self):
        report = finding('IPV6_EXIT_OBSERVED')
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
        self.assertEqual(result['traffic_policy'], EXPECTED)
        self.assertFalse(hasattr(remedy_plans, 'compile_ipv4_policy_plan'))

    def test_dashboard_does_not_trust_forged_compliance_or_sample_success(self):
        report = guardian.base('audit', 'device-a')
        report['traffic_policy'] = {'policy': 'dual_stack', 'compliance': 'verified',
                                    'native_pass': True, 'private': '<script>SECRET</script>'}
        # Forged success flags are unknown members: the dashboard now rejects them outright
        # (ENV-T121) instead of ignoring them, so they are asserted separately below. The forged
        # traffic_policy above is a known member and must still never be trusted or echoed.
        for forged in ('AAAA_empty', 'curl4_success', 'https_success', 'ipv6_timeout'):
            with self.subTest(forged=forged), self.assertRaises(status_dashboard.GuardianError):
                status_dashboard.project(dict(report, **{forged: True}))
        view = status_dashboard.project(report)
        self.assertEqual(view['traffic_policy'], EXPECTED)
        self.assertNotEqual(view['overall'], 'verified')
        self.assertFalse(any(c['state'] == 'verified' for c in view['cards']))
        html = status_dashboard.render(report)
        self.assertIn('IPv4_ONLY', html)
        self.assertIn('禁止IPv6回退', html)
        self.assertIn('IPv6 关闭', html)
        self.assertNotIn('SECRET', html)
        report.pop('traffic_policy')
        self.assertEqual(status_dashboard.project(report)['traffic_policy'], EXPECTED)

    def test_fixed_policy_envelope_member_validated_and_legacy_omission_supported(self):
        report = guardian.interview({'schema_version': 'guardian-interview/0.1', 'answers': {}})
        guardian.validate_interview_envelope(report)
        legacy = deepcopy(report); legacy.pop('traffic_policy')
        guardian.validate_interview_envelope(legacy)
        for key, value in [('policy', 'dual_stack'), ('applies_to', 'claude_only'),
                           ('ipv6', 'enabled'), ('on_proxy_failure', 'direct')]:
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
                    ('remedy_plans', "m.policy_projection()")]:
                code = ("import importlib.util,json; s=importlib.util.spec_from_file_location('isolated'," +
                        repr(str(scripts / (name + '.py'))) + ");m=importlib.util.module_from_spec(s);"
                        "s.loader.exec_module(m);print(json.dumps(" + expression + "))")
                result = subprocess.run([sys.executable, '-I', '-S', '-c', code], cwd=tmp,
                                        capture_output=True, text=True)
                self.assertEqual(result.returncode, 0, result.stderr)
                self.assertEqual(json.loads(result.stdout)['policy'], 'IPv4_ONLY')


if __name__ == '__main__':
    unittest.main()
