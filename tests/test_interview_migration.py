"""Offline T82/D.11 regressions; no real target or permission verification."""
import copy
import json
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

SCRIPTS = Path(__file__).resolve().parents[1] / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import guardian
import interview_flow as flow
import interview_migration as migration


def compact(**answers):
    return {'schema_version': 'guardian-interview/0.1', 'answers': answers}


def migrate(obj, **kwargs):
    return migration.migrate_legacy(obj, target_alias='device-new', account_alias='account-new', **kwargs)


class MigrationTests(unittest.TestCase):
    def test_actual_fixture_preserves_fields_provenance_without_freshness(self):
        source = json.loads((SCRIPTS.parents[2] / 'tests/fixtures/interview-first.json').read_text())
        result = migrate(source)
        self.assertEqual(result['status'], 'review_required')
        state = flow.validate_state(result['state'])
        self.assertEqual(state['facts']['Q-C02']['value'], 'macos')
        self.assertEqual(state['facts']['Q-C01']['value'], 'web')
        self.assertEqual(state['facts']['Q-J01']['value'], 'first_subscription')
        for fact in state['facts'].values():
            self.assertEqual(fact['state'], 'stale')
            self.assertTrue(fact['source'].startswith('legacy:compact.answers.'))
            self.assertIsNone(fact['observed_at'])
        self.assertEqual(result['confidence'], 'unknown')
        self.assertEqual(result['binding'], 'unverified')

    def test_actual_report_wrapper_uses_named_fields_not_old_question_ids(self):
        report = guardian.interview(compact(os='windows', usage='code'))
        report['question']['id'] = 'Q-C01'  # Initial preview reversed C01/C02.
        result = migrate(report)
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(result['state']['facts']['Q-C02']['value'], 'windows')
        self.assertEqual(result['state']['facts']['Q-C01']['value'], 'code')
        self.assertEqual(result['state']['facts']['Q-C02']['source'], 'legacy:report.state.answers.os')

    def test_retired_fields_removed_without_reinterpretation(self):
        obj = compact(os='macos')
        obj['answers'].update({'Q-C07': 'mine', 'account_ownership': 'organization',
                               'account_control': 'yes', 'Q-C08': 'old paid entitlement'})
        result = migrate(obj)
        self.assertEqual(result['status'], 'review_required')
        self.assertEqual(set(result['discarded_fields']), migration.TOMBSTONES)
        self.assertEqual(set(result['state']['facts']), {'Q-C02'})
        self.assertNotIn('old paid entitlement', json.dumps(result))
        required = flow.assessment(result['state'])['G1']['unresolved_fields']
        self.assertNotIn('Q-C07', [x['id'] for x in required])
        self.assertEqual(result['state']['payment_intent'], 'unresolved')

    def test_only_named_explicit_target_plan_maps_to_new_c08(self):
        obj = compact(target_plan='undecided')
        obj['answers']['Q-C08'] = 'old entitlement'
        self.assertEqual(migrate(obj)['state']['facts']['Q-C08']['value'], 'undecided')

    def test_all_valid_compact_fields_retained_without_account_device_conflation(self):
        result = migrate(compact(subscription_stage='existing_subscriber', current_task='environment',
                                 os='phone_only', usage='mixed', target_plan='compare',
                                 account_status='active', device_history='new_to_claude', route='vps'))
        self.assertEqual(result['status'], 'review_required')
        state = result['state']
        self.assertEqual(state['facts']['Q-C02']['value'], 'mobile_only')
        self.assertEqual(state['facts']['Q-C04']['value'], 'active')
        self.assertEqual(migrate(compact(account_status='not_registered'))['state']['facts']['Q-C04']['value'], 'unregistered')
        self.assertNotIn('Q-C03', state['facts'])
        self.assertEqual(result['review_only'][0]['field'], 'device_history')
        self.assertEqual(state['facts']['Q-C05']['value'], 'vps')
        self.assertEqual(flow.assessment(state)['route_confirmation'], 'unconfirmed')

    def test_first_business_question_and_route_confirmation_cannot_be_bypassed(self):
        state = migrate(compact(subscription_stage='existing_subscriber', route='vps', os='macos'))['state']
        self.assertEqual(flow.next_question(state)['id'], 'Q-J01')
        self.assertTrue(flow.next_question(state)['clarification'])
        self.assertEqual(state['current_subscription']['status'], 'unknown')
        self.assertEqual(state['payment_intent'], 'unresolved')
        self.assertEqual(state['context']['route_selection_basis'], 'default_proposal')
        self.assertEqual(flow.assessment(state)['G2']['status'], 'blocked')
        self.assertEqual(flow.assessment(state)['G3']['status'], 'blocked')

    def test_conflicting_subscription_facts_rejected(self):
        for stage in ('first_subscription', 'returning_subscription'):
            for task in ('renew', 'upgrade'):
                result = migrate(compact(subscription_stage=stage, current_task=task))
                self.assertEqual(result['code'], 'CONFLICTING_SUBSCRIPTION_FACTS')
                self.assertIsNone(result['state'])

    def test_subscribed_but_unregistered_is_a_conflict(self):
        result = migrate(compact(subscription_stage='existing_subscriber', account_status='not_registered'))
        self.assertEqual(result['code'], 'CONFLICTING_SUBSCRIPTION_FACTS')
        self.assertIsNone(result['state'])

    def test_missing_fresh_binding_is_actionable_and_never_inherited(self):
        obj = guardian.interview(compact(os='macos'))
        obj['target_ref'] = 'old-device'
        result = migration.migrate_legacy(obj)
        self.assertEqual(result['code'], 'FRESH_BINDING_REQUIRED')
        self.assertTrue(result['next_step'])
        self.assertIsNone(result['state'])

    def test_report_grants_readiness_and_timestamp_are_not_inherited(self):
        obj = guardian.interview(compact(subscription_stage='existing_subscriber'))
        obj['contact_control'].update(contact_phase='contact', gate_state='open', pc_g1='pass', pc_g2='pass')
        obj['target_binding']['binding_state'] = 'verified'
        obj['privacy']['shareable'] = True
        obj['snapshot']['clock_externally_verified'] = True
        result = migrate(obj)
        state = result['state']
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertFalse(any(state['persistence_consent'].values()))
        self.assertEqual(state['current_subscription']['status'], 'unknown')
        self.assertIsNone(state['facts']['Q-J01']['observed_at'])
        self.assertEqual(flow.assessment(state)['G3']['status'], 'blocked')
        with self.assertRaises(flow.InterviewError):
            flow.dumps_state(state)

    def test_unknown_versions_shapes_and_grant_fields_fail_closed(self):
        invalid = [None, [], {}, {'schema_version': 'future', 'answers': {}},
                   {'answers': {}}, compact(os='linux'), compact(os=True), compact(target_plan=''),
                   compact(arbitrary='x'), {**compact(), 'permissions': True},
                   {**compact(), 'cancelled': 'false'}, flow.new_state('x', 'y')]
        for obj in invalid:
            with self.subTest(obj=obj):
                result = migrate(obj)
                self.assertEqual(result['status'], 'blocked')
                self.assertIsNone(result['state'])
        report = guardian.interview(compact())
        report['target_binding']['unexpected'] = True
        self.assertEqual(migrate(report)['status'], 'blocked')
        for field, value in [('runtime_version', []), ('question', []), ('snapshot', {})]:
            report = guardian.interview(compact())
            report[field] = value
            self.assertEqual(migrate(report)['status'], 'blocked')

    def test_credentials_screened_even_in_discarded_values_never_echoed(self):
        for key in ('target_plan', 'Q-C07', 'Q-C08', 'account_control', 'account_ownership'):
            for secret in ('password=hunter2', 'sk-ant-abcdefghijklmnop', '4111 1111 1111 1111', 'https://user:password@example.test'):
                obj = compact()
                obj['answers'][key] = secret
                result = migrate(obj)
                self.assertEqual(result['status'], 'blocked')
                self.assertNotIn(secret, json.dumps(result))
        self.assertEqual(migrate(compact(password='x'))['status'], 'blocked')

    def test_stale_account_suspension_requires_host_review_before_intake(self):
        result = migrate(compact(account_status='suspended'))
        self.assertEqual(result['review_hints'][0]['code'], 'RECONFIRM_ACCOUNT_SUSPENSION_BEFORE_INTAKE')
        self.assertFalse(result['review_hints'][0]['current_incident_verified'])
        self.assertEqual(result['review_hints'][0]['source'], 'legacy:compact.answers.account_status')
        self.assertEqual(result['state']['context']['incident'], 'none')
        self.assertEqual(result['state']['facts']['Q-C04']['state'], 'stale')
        self.assertEqual(flow.assessment(result['state'])['G3']['status'], 'blocked')
        # Device use history cannot produce an account-suspension instruction.
        device = migrate(compact(device_history='previous_use_with_reported_suspension'))
        self.assertEqual(device['review_hints'], [])
        self.assertEqual(device['state']['context']['incident'], 'none')
        self.assertEqual(migrate(compact(account_status='active'))['review_hints'], [])

    def test_cancelled_state_stays_paused(self):
        obj = {**compact(os='macos'), 'cancelled': True}
        for source in (obj, guardian.interview(obj)):
            state = migrate(source)['state']
            self.assertTrue(state['context']['paused'])
            self.assertIsNone(flow.next_question(state))
            self.assertEqual(flow.assessment(state)['G3']['status'], 'blocked')

    def test_pure_deterministic_unsaved_candidate_and_input_immutable(self):
        obj = compact(os='macos', route='local')
        before = copy.deepcopy(obj)
        with patch('builtins.open', side_effect=AssertionError('Unexpected IO')), \
             patch('socket.socket', side_effect=AssertionError('Unexpected network')), \
             patch('subprocess.run', side_effect=AssertionError('Unexpected process')):
            first = migrate(obj)
            second = migrate(obj)
        self.assertEqual(first, second)
        self.assertEqual(obj, before)
        self.assertFalse(first['saved'])
        self.assertFalse(first['action_executed'])
        first['state']['facts']['Q-C02']['value'] = 'changed'
        self.assertEqual(obj, before)


if __name__ == '__main__':
    unittest.main()
