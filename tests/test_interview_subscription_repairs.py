"""Derived T76/T84 regression scope, synthetic only; not whole-case acceptance.

GUARDIAN_SUBSCRIPTION_TEST_ROOT permits exact old-code failure reproduction.
No real account, device, external compatibility claim, payment or permission.
"""
from contextlib import ExitStack
from copy import deepcopy
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(os.environ.get('GUARDIAN_SUBSCRIPTION_TEST_ROOT', Path(__file__).resolve().parents[1]))
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
spec = importlib.util.spec_from_file_location('subscription_repairs_flow', SCRIPTS / 'interview_flow.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)

OLD_TIME = '2026-10-17T08:00:00+00:00'
NOW = '2026-10-18T09:30:00+00:00'
PAYMENT_PREFIXES = ('Q-P', 'Q-A', 'Q-G', 'Q-W', 'Q-I', 'Q-E')
VALUES = {'Q-C01': 'code', 'Q-C02': 'macos', 'Q-C03': 'none_reported',
          'Q-C04': 'registered_login_reported', 'Q-C05': 'local', 'Q-C06': 'email',
          'Q-C08': 'Pro', 'Q-C09': 'supported_region_reported_not_verified',
          'Q-C10': 'concise', 'Q-C12': 'preserve_code_projects_and_configuration',
          'Q-C13': 'Synthetic plan A; feature question supplied by host',
          'Q-OS03': 'macos_version_reported', 'Q-N01': 'proxy_reported',
          'Q-N02': 'code_and_proxy_local_reported', 'Q-N03': 'stable_network_reported',
          'Q-N04': 'selected_device_only', 'Q-N06': 'personal_device_reported',
          'Q-L01': 'desktop_and_code_installed_reported',
          'Q-L02': 'os_and_architecture_compatible_reported', 'Q-L04': 'local_projects_needed',
          'Q-Z01': 'plan_only_no_device_action', 'Q-D02': 'audit_only',
          'Q-X01': 'existing_stable_exit', 'Q-X02': 'own_vps_ip_only', 'Q-M01': 'none',
          'Q-V07': 'omarchy', 'Q-V08': 'lan_bridged', 'Q-V09': 'direct', 'Q-S08': 'vps_own_ip', 'Q-T01': 'none'}


def answer(state, qid, value, **kwargs):
    return f.record_fact(state, qid, value, source='synthetic:subscription-repair', **kwargs)


def base(journey='existing_subscriber', task='network', **context):
    s = f.new_state('audit-device', 'audit-account', task_id='audit-task')
    s = answer(s, 'Q-J01', journey, observed_at=OLD_TIME)
    for qid in ['Q-C02', 'Q-C01', 'Q-C05']:
        s = answer(s, qid, VALUES[qid])
    s = f.set_context(s, task=task, billing_channel='apple', subscription_conflict=False, **context)
    if task == 'cleanup':
        s = answer(s, 'Q-D02', 'audit_only')
        s = answer(s, 'Q-C01', 'desktop_cleanup_keep_code')
    return s


def ids(s):
    return [item['id'] for item in f.applicable_questions(s)]


def complete(s, except_ids=()):
    for _ in range(30):
        pending = [q['id'] for q in f.applicable_questions(s)
                   if q['id'] not in s['facts'] and q['id'] not in except_ids]
        if not pending:
            return s
        for qid in pending:
            s = answer(s, qid, VALUES[qid])
    raise AssertionError('Changing requirements never settled')


class SubscriptionRepairFlowTests(unittest.TestCase):
    def setUp(self):
        self.guards = ExitStack()
        self.addCleanup(self.guards.close)
        self.guards.enter_context(patch.object(f, '_now', return_value=NOW))
        for target in ['socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                       'subprocess.run', 'subprocess.Popen', 'builtins.open', 'pathlib.Path.open']:
            self.guards.enter_context(patch(target, side_effect=AssertionError('Unexpected I/O: ' + target)))

    def assert_no_permission(self, state):
        result = f.assessment(state)
        self.assertEqual(state['context']['contact_phase'], 'PC0')
        self.assertEqual(result['G3']['status'], 'blocked')
        self.assertEqual(state['persistence_consent'], {'private_save': False, 'export': False, 'public_export': False})

    def assert_technical(self, state, needs_plan):
        applicable = ids(state)
        self.assertEqual('Q-C13' in applicable, needs_plan)
        self.assertNotIn('Q-C08', applicable)
        self.assertFalse(any(qid.startswith(PAYMENT_PREFIXES) for qid in applicable))
        self.assertEqual(state['current_subscription']['status'], 'active_reported')
        self.assertEqual(state['purchase_intent'], 'none')
        self.assertEqual(state['payment_intent'], 'none')
        self.assert_no_permission(state)

    def test_t76_plain_returning_reuses_no_subscription_and_target(self):
        s = base('returning_subscription', 'subscription_preparation')
        self.assertIn('Q-C08', ids(s))
        self.assertTrue({'Q-J02', 'Q-P02', 'Q-A06'}.isdisjoint(ids(s)))
        current = deepcopy(s['current_subscription'])
        s = answer(s, 'Q-C08', 'Pro')
        self.assertNotEqual(f.next_question(s)['id'], 'Q-C08')
        self.assertEqual(s['current_subscription'], current)
        self.assertEqual(s['payment_intent'], 'resubscribe')
        self.assert_no_permission(s)

    def test_t76_expired_pending_refund_no_conflict_and_no_purchase_survey(self):
        s = answer(base('returning_subscription', 'subscription_preparation'), 'Q-C08', 'Pro')
        current, target = deepcopy(s['current_subscription']), deepcopy(s['facts']['Q-C08'])
        s = f.set_context(s, task='billing_issue')
        self.assertEqual(ids(s), ['Q-J01', 'Q-P02', 'Q-A06'])
        self.assertEqual(f.next_question(s)['id'], 'Q-P02')
        self.assertEqual(s['current_subscription'], current)
        self.assertEqual(s['facts']['Q-C08'], target)
        self.assertFalse(s['context']['subscription_conflict'])
        self.assertEqual(s['purchase_intent'], 'none')
        self.assertEqual(s['payment_intent'], 'troubleshoot')
        # Complete explicit past-order answer covers A06 without inventing an answer.
        value = {'plan': 'former-plan', 'billing_channel': 'apple',
                 'status': 'expired', 'pending_issue': 'pending_refund'}
        s = answer(s, 'Q-P02', value, observed_at=OLD_TIME)
        self.assertNotIn('Q-A06', ids(s))
        self.assertNotIn('Q-A06', s['facts'])
        self.assertEqual(s['facts']['Q-P02']['observed_at'], OLD_TIME)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assert_no_permission(s)
        s = f.set_context(s, task='subscription_preparation')
        self.assertEqual(s['facts']['Q-C08'], target)
        self.assertEqual(s['current_subscription'], current)
        self.assertNotIn('Q-P02', ids(s))
        self.assertNotIn('Q-A06', ids(s))
        self.assertNotEqual(f.next_question(s)['id'], 'Q-C08')
        self.assertEqual(s['payment_intent'], 'resubscribe')

    def test_t76_refund_needs_no_unrelated_device_or_route(self):
        s = answer(f.new_state('device', 'account'), 'Q-J01', 'returning_subscription')
        s = f.set_context(s, task='billing_issue', billing_channel='apple')
        self.assertEqual(ids(s), ['Q-J01', 'Q-P02', 'Q-A06'])
        s = answer(s, 'Q-P02', {'billing_channel': 'apple', 'status': 'expired',
                              'pending_issue': 'pending_refund'})
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.assessment(s)['route_confirmation'], 'unconfirmed')
        self.assert_no_permission(s)

    def test_t76_unknown_refusal_defer_does_not_repeat_p02_as_a06(self):
        for status in ['unknown', 'declined', 'deferred']:
            s = f.record_fact(base('returning_subscription', 'billing_issue'), 'Q-P02',
                              state_name=status, source='synthetic:bounded')
            self.assertNotIn('Q-A06', ids(s))
            self.assertIsNone(f.next_question(s))
            self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
            self.assert_no_permission(s)

    def test_t76_distinct_controls_and_returning_migration_not_renew_upgrade(self):
        for stage, old in [('first_subscription', False), ('returning_subscription', True), ('existing_subscriber', True)]:
            s = base(stage, 'billing_issue')
            self.assertEqual('Q-P02' in ids(s), old)
            self.assertEqual('Q-A06' in ids(s), old)
            self.assertFalse(s['context']['subscription_conflict'])
        conflict = f.set_context(base('first_subscription', 'billing_issue'), subscription_conflict=True)
        self.assertIn('Q-P02', ids(conflict))
        for task, old in [('change_channel', True), ('renew', False), ('upgrade', False)]:
            s = base('returning_subscription', task)
            self.assertEqual('Q-P02' in ids(s), old)
        with self.assertRaisesRegex(f.InterviewError, 'Old-subscriber task conflicts'):
            f.record_facts(base('returning_subscription'), [{'question_id': 'Q-C11', 'value': 'billing_issue'}], source='synthetic:explicit')

    def test_t76_partial_old_order_never_fabricates_channel_or_a06(self):
        for value in ['old order', {'pending_issue': 'pending_refund'},
                      {'billing_channel': 'apple', 'status': 'expired'},
                      {'billing_channel': ['apple'], 'status': 'expired', 'pending_issue': 'pending_refund'}]:
            with self.subTest(value=value):
                s = answer(base('returning_subscription', 'billing_issue'), 'Q-P02', value)
                self.assertIn('Q-A06', ids(s))
                self.assertNotIn('Q-A06', s['facts'])
        # Host can absorb distinct P02/A06 facts from one actual complete reply.
        s = f.record_facts(base('returning_subscription', 'billing_issue'), [
            {'question_id': 'Q-P02', 'value': 'old plan and old Apple order'},
            {'question_id': 'Q-A06', 'value': 'expired old order; refund pending'}], source='synthetic:one-reply')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(s['facts']['Q-P02']['observed_at'], s['facts']['Q-A06']['observed_at'])

    def test_t76_past_channel_is_not_future_channel_or_active_entitlement(self):
        s = base('returning_subscription', 'change_channel')
        s = answer(s, 'Q-P02', {'plan': 'old-plan', 'billing_channel': 'google',
                              'status': 'expired', 'pending_issue': 'none_reported'})
        self.assertEqual(s['context']['billing_channel'], 'apple')
        self.assertNotIn('Q-A06', ids(s))
        self.assertEqual(s['current_subscription']['status'], 'none_reported')
        self.assertNotIn('Q-C13', s['facts'])

    def test_t76_old_apple_channel_precedes_future_channel_and_partial_web_is_bounded(self):
        s = f.set_context(base('returning_subscription', 'billing_issue'), billing_channel='web')
        s = answer(s, 'Q-P02', {'billing_channel': 'apple', 'status': 'expired'})
        self.assertEqual(f.next_question(s)['id'], 'Q-A06')
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
        self.assertEqual(s['context']['billing_channel'], 'web')
        s = answer(s, 'Q-A06', 'pending_refund')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        s = answer(f.set_context(s, billing_channel='apple'), 'Q-P02',
                   {'billing_channel': 'web', 'status': 'expired'})
        # A materially changed P02 retires the previous order's follow-up itself.
        self.assertEqual(s['facts']['Q-A06']['state'], 'stale')
        self.assertNotIn('Q-A06', ids(s))
        self.assertEqual(f.next_question(s)['id'], 'Q-P02')
        self.assertTrue(f.next_question(s)['clarification'])
        s = f.mark_asked(s, 'Q-P02')
        self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])

    def test_t76_new_billing_task_and_same_reply_order_replacement(self):
        s = base('returning_subscription', 'billing_issue')
        s = f.record_facts(s, [{'question_id': 'Q-P02', 'value': 'old Apple order'},
                               {'question_id': 'Q-A06', 'value': 'old pending refund'}], source='synthetic:old-order')
        updated = f.record_facts(s, [{'question_id': 'Q-A06', 'value': 'new pending refund'},
                                     {'question_id': 'Q-P02', 'value': 'new Apple order'}], source='synthetic:new-order')
        self.assertEqual(updated['facts']['Q-A06']['state'], 'reported')
        self.assertEqual(updated['facts']['Q-A06']['source'], 'synthetic:new-order')
        self.assertIsNone(f.next_question(updated))
        new_task = f.begin_task(updated, task_id='new-bill', task='billing_issue')
        self.assertEqual(new_task['facts']['Q-P02']['state'], 'stale')
        self.assertEqual(new_task['facts']['Q-A06']['state'], 'stale')
        self.assertEqual(f.next_question(new_task)['id'], 'Q-P02')
        self.assertTrue(f.assessment(new_task)['G2']['conditional_plan_only'])

    def test_t76_legacy_apple_migration_independent_of_future_purchase_channel(self):
        for channel in ['web', 'google', 'unselected']:
            s = f.set_context(base('returning_subscription', 'change_channel'), billing_channel=channel)
            s = answer(s, 'Q-P02', {'billing_channel': 'apple', 'status': 'expired'})
            self.assertIn('Q-A06', ids(s))
            self.assertEqual(s['context']['billing_channel'], channel)
            self.assertEqual(s['current_subscription']['status'], 'none_reported')

    def test_t76_unrelated_historical_cleanup_is_not_refund_prerequisite(self):
        s = answer(base('returning_subscription', 'billing_issue'), 'Q-P02',
                   {'billing_channel': 'apple', 'status': 'expired', 'pending_issue': 'pending_refund'})
        for qid, value in [('Q-C03', 'past_suspension'), ('Q-D01', 'past_restriction_on_target')]:
            s = answer(s, qid, value)
            self.assertIsNone(f.next_question(s))
            self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
            self.assertIsNone(f.cleanup_assessment(s))
        urgent = answer(s, 'Q-D01', 'current_restriction_on_target')
        self.assertEqual(ids(urgent), ['Q-H01', 'Q-C04'])

    def test_t84_network_cleanup_environment_hardware_is_independent(self):
        for task in ['network', 'cleanup', 'environment']:
            for hardware in [False, True]:
                for dependency in [False, True]:
                    with self.subTest(task=task, hardware=hardware, dependency=dependency):
                        s = base(task=task, compatibility_needed=hardware, plan_compatibility_needed=dependency)
                        self.assert_technical(s, dependency)
                        self.assertEqual('Q-L02' in ids(s), hardware and task != 'cleanup')
                        s = complete(s, except_ids={'Q-C13'})
                        if dependency:
                            self.assertEqual(f.next_question(s)['id'], 'Q-C13')
                            self.assertIn('当前订阅', f.next_question(s)['prompt'])
                            self.assertIn('功能', f.next_question(s)['prompt'])
                            self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
                        else:
                            self.assertIsNone(f.next_question(s))
                            self.assertEqual(f.assessment(s)['G2']['status'], 'pass')

    def test_t84_known_current_plan_reused_separately_from_target(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C08', 'desired-plan-B')
        s = answer(s, 'Q-C13', 'reported-current-plan-A', observed_at=OLD_TIME)
        old = deepcopy(s['facts']['Q-C13'])
        s = complete(s)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(s['facts']['Q-C13'], old)
        self.assertEqual(s['facts']['Q-C13']['subject_ref'], s['account_alias'])
        self.assertEqual(s['facts']['Q-C08']['value'], 'desired-plan-B')
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.assessment(s)['current_plan_dependency']['compatibility'], 'not_established')
        self.assert_technical(s, True)

    def test_t84_unknown_refusal_defer_not_applicable_stay_conditional_without_loop(self):
        for task in ['network', 'cleanup']:
            for status in ['unknown', 'declined', 'deferred', 'not_applicable']:
                with self.subTest(task=task, status=status):
                    s = complete(base(task=task, plan_compatibility_needed=True), except_ids={'Q-C13'})
                    s = f.record_fact(s, 'Q-C13', state_name=status, source='synthetic:response')
                    self.assertIsNone(f.next_question(s))
                    self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
                    self.assertTrue(f.assessment(s)['current_plan_dependency']['unrelated_planning_available'])
                    self.assert_no_permission(s)
                    if task == 'cleanup':
                        self.assertEqual(f.cleanup_assessment(s)['next_step'], 'scope_inventory')
                        self.assertFalse(f.cleanup_assessment(s)['action_authorized'])

    def test_t84_separate_deferred_dependency_keeps_cleanup_available(self):
        s = f.defer_branch(base(task='cleanup', plan_compatibility_needed=True), 'compatibility')
        s = complete(s, except_ids={'Q-C13'})
        self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
        self.assertEqual(f.cleanup_assessment(s)['next_step'], 'scope_inventory')
        self.assertEqual(f.next_question(f.resume_branch(s, 'compatibility'))['id'], 'Q-C13')

    def test_t84_no_inference_from_expertise_target_channel_or_plan_flag(self):
        for stage in ['unknown', 'first_subscription', 'returning_subscription']:
            s = answer(base(stage, plan_compatibility_needed=True, ambiguous_experience=True), 'Q-C08', 'Pro')
            s = answer(s, 'Q-C10', 'expert')
            self.assertNotIn('Q-C13', ids(s))
            self.assertNotIn('Q-C13', s['facts'])
            self.assertNotEqual(s['current_subscription']['status'], 'active_reported')
        with self.assertRaisesRegex(f.InterviewError, 'Inference'):
            answer(base(plan_compatibility_needed=True), 'Q-C13', 'Pro', state_name='inferred')
        with self.assertRaisesRegex(f.InterviewError, 'target mismatch'):
            answer(base(), 'Q-C13', 'Pro', subject_ref='audit-device')
        for value in ['', ' ', 'selected_unspecified', 1, True, {'plan': 'Pro'}]:
            with self.assertRaises(f.InterviewError):
                answer(base(), 'Q-C13', value)

    def test_t84_optional_context_backward_compatibility_and_strict_validation(self):
        s = f.new_state('device', 'account')
        self.assertNotIn('plan_compatibility_needed', s['context'])
        self.assertNotIn('plan_compatibility_needed', f.STATE_SCHEMA['properties']['context']['required'])
        self.assertEqual(f.loads_state(json.dumps(s))['context'], s['context'])
        self.assertEqual(f.STATE_SCHEMA['properties']['context']['properties']['plan_compatibility_needed'], {'type': 'boolean'})
        for value in [None, 1, 'yes', {}, []]:
            with self.assertRaises(f.InterviewError):
                f.set_context(s, plan_compatibility_needed=value)
        with self.assertRaises(f.InterviewError):
            f.set_context(s, inferred_entitlement=True)

    def test_t84_task_flag_reset_set_context_batch_and_begin_task(self):
        original = answer(base(plan_compatibility_needed=True), 'Q-C13', 'plan-A')
        original_fact = deepcopy(original['facts']['Q-C13'])
        changed = f.set_context(original, task='cleanup')
        self.assertNotIn('plan_compatibility_needed', changed['context'])
        changed = f.record_facts(original, [{'question_id': 'Q-C11', 'value': 'environment'}], source='synthetic:task')
        self.assertNotIn('plan_compatibility_needed', changed['context'])
        changed = f.begin_task(original, task_id='new-task', task='network')
        self.assertNotIn('plan_compatibility_needed', changed['context'])
        self.assertEqual(changed['facts']['Q-C13'], original_fact)
        self.assertNotIn('Q-C13', ids(changed))
        changed = f.set_context(changed, plan_compatibility_needed=True)
        self.assertIn('Q-C13', ids(changed))
        same = f.set_context(original, task='network')
        self.assertTrue(same['context']['plan_compatibility_needed'])
        explicit = f.set_context(original, task='cleanup', plan_compatibility_needed=True)
        self.assertTrue(explicit['context']['plan_compatibility_needed'])

    def test_t84_account_bound_reuse_new_device_and_new_account(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'plan-A', observed_at=OLD_TIME)
        same_account = f.begin_task(s, task_id='new', task='network', target_alias='second-device')
        self.assertEqual(same_account['facts']['Q-C13'], s['facts']['Q-C13'])
        self.assertNotIn('plan_compatibility_needed', same_account['context'])
        new_account = f.begin_task(s, task_id='new', task='network', account_alias='second-account')
        self.assertNotIn('Q-C13', new_account['facts'])
        self.assertEqual(new_account['current_subscription']['status'], 'unknown')
        self.assertNotIn('plan_compatibility_needed', new_account['context'])

    def test_t84_stage_change_invalidation_and_no_old_import_resurrection(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        old = deepcopy(s['facts']['Q-C13'])
        s = answer(s, 'Q-J01', 'returning_subscription')
        self.assertEqual(s['facts']['Q-C13']['state'], 'stale')
        self.assertEqual(s['facts']['Q-C13']['source'], old['source'])
        self.assertEqual(s['facts']['Q-C13']['observed_at'], old['observed_at'])
        s = answer(s, 'Q-J01', 'existing_subscriber')
        s = answer(s, 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        self.assertEqual(s['facts']['Q-C13']['state'], 'stale')
        s = complete(s)
        self.assertEqual(f.next_question(s)['id'], 'Q-C13')
        self.assertTrue(f.next_question(s)['clarification'])
        s = f.mark_asked(s, 'Q-C13')
        self.assertIsNone(f.next_question(s))
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
        s = answer(s, 'Q-C13', 'fresh-plan')
        self.assertEqual(s['facts']['Q-C13']['state'], 'reported')
        self.assertEqual(s['facts']['Q-C13']['observed_at'], NOW)

    def test_t84_stage_staleness_and_actual_conflict_invalidate_current_plan(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        stale = f.invalidate_facts(s, ['Q-J01'], reason='reported expiry')
        self.assertEqual(stale['facts']['Q-C13']['state'], 'stale')
        self.assertEqual(stale['current_subscription']['status'], 'unknown')
        conflict = f.set_context(s, subscription_conflict=True)
        self.assertEqual(conflict['facts']['Q-C13']['state'], 'stale')

    def test_t84_completed_purchase_never_copies_desired_plan_or_old_plan(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        s = answer(s, 'Q-C08', 'new-purchase-target')
        done = f.complete_purchase(s, source='synthetic:reported-purchase', observed_at=NOW)
        self.assertNotIn('plan_compatibility_needed', done['context'])
        self.assertEqual(done['facts']['Q-C13']['state'], 'stale')
        self.assertEqual(done['facts']['Q-C13']['value'], 'old-plan')
        self.assertEqual(done['facts']['Q-C13']['observed_at'], OLD_TIME)
        self.assertEqual(done['purchase_intent'], 'completed')
        self.assertEqual(done['payment_intent'], 'none')
        self.assertNotIn('Q-C13', ids(done))
        self.assertIn('Q-C13', ids(f.set_context(done, plan_compatibility_needed=True)))
        self.assert_no_permission(done)

    def test_t84_completed_purchase_exact_retry_preserves_later_current_plan_and_dependency(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        s = f.complete_purchase(s, source='synthetic:purchase', observed_at=NOW)
        s = f.set_context(s, task='cleanup', plan_compatibility_needed=True)
        s = answer(s, 'Q-C13', 'new-plan')
        retried = f.complete_purchase(s, source='synthetic:purchase', observed_at=NOW)
        self.assertEqual(retried, s)
        self.assertEqual(retried['facts']['Q-C13']['state'], 'reported')
        self.assertTrue(retried['context']['plan_compatibility_needed'])
        self.assertEqual(retried['context']['task'], 'cleanup')

    def test_t84_receipt_retry_after_new_task_and_new_stage_report_keeps_later_evidence(self):
        s = f.complete_purchase(base(), source='synthetic:receipt', observed_at=NOW)
        s = f.begin_task(s, task_id='later-task', task='network')
        s = f.set_context(s, plan_compatibility_needed=True)
        s = answer(s, 'Q-C13', 'new-plan', observed_at='2026-10-18T10:00:00+00:00', current_reply=True)
        exact = f.complete_purchase(s, source='synthetic:receipt', observed_at=NOW)
        self.assertEqual(exact, s)
        s = answer(s, 'Q-J01', 'existing_subscriber', observed_at='2026-10-18T10:05:00+00:00')
        historic = f.complete_purchase(s, source='synthetic:receipt', observed_at=NOW)
        self.assertEqual(historic, s)
        self.assertTrue(historic['context']['plan_compatibility_needed'])
        self.assertEqual(historic['context']['task'], 'network')

    def test_t84_explicit_current_reply_preserves_real_time_but_cannot_predate_stage(self):
        s = answer(base(), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        s = f.complete_purchase(s, source='synthetic:receipt', observed_at=NOW)
        updated = answer(s, 'Q-C13', 'new-plan', observed_at='2026-10-18T09:35:00+00:00', current_reply=True)
        self.assertEqual(updated['facts']['Q-C13']['state'], 'reported')
        self.assertEqual(updated['facts']['Q-C13']['observed_at'], '2026-10-18T09:35:00+00:00')
        old = answer(s, 'Q-C13', 'pre-purchase-plan', observed_at='2026-10-18T08:00:00+00:00', current_reply=True)
        self.assertEqual(old['facts']['Q-C13']['state'], 'stale')
        for invalid in [None, 1, 'yes']:
            with self.assertRaises(f.InterviewError):
                answer(s, 'Q-C13', 'plan', current_reply=invalid)

    def test_t84_first_completion_same_provenance_as_ordinary_stage_is_not_a_retry(self):
        s = base(task='upgrade')
        s = f.record_fact(s, 'Q-J01', 'existing_subscriber', source='synthetic:same-reply', observed_at=NOW)
        self.assertNotIn('purchase_completion', s)
        done = f.complete_purchase(s, source='synthetic:same-reply', observed_at=NOW)
        self.assertTrue(done['context']['purchase_completed'])
        self.assertEqual(done['context']['task'], 'environment')
        self.assertEqual(done['purchase_intent'], 'completed')
        self.assertEqual(done['purchase_completion'], {'account_alias': 'audit-account',
            'source': 'synthetic:same-reply', 'observed_at': NOW, 'observed': False})

    def test_t84_completion_receipt_account_binding_schema_and_old_retry(self):
        s = f.complete_purchase(base(), source='synthetic:receipt', observed_at=NOW)
        restored = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertEqual(restored['purchase_completion'], s['purchase_completion'])
        other_device = f.begin_task(s, task_id='new', task='network', target_alias='other-device')
        self.assertEqual(other_device['purchase_completion'], s['purchase_completion'])
        other_account = f.begin_task(s, task_id='new', task='network', account_alias='other-account')
        self.assertNotIn('purchase_completion', other_account)
        for field, value in [('account_alias', 'wrong-account'), ('source', None), ('observed_at', None), ('observed', 1)]:
            changed = deepcopy(s)
            changed['purchase_completion'][field] = value
            with self.assertRaises(f.InterviewError):
                f.validate_state(changed)
        expired = answer(s, 'Q-J01', 'returning_subscription', observed_at='2026-10-18T10:00:00+00:00')
        retry = f.complete_purchase(expired, source='synthetic:receipt', observed_at=NOW)
        self.assertEqual(retry, expired)
        self.assertEqual(retry['current_subscription']['status'], 'none_reported')
        with self.assertRaises(f.InterviewError):
            f.complete_purchase(s, source='synthetic:older-receipt', observed_at=OLD_TIME)

    def test_t84_different_historical_import_cannot_discharge_staleness(self):
        s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        s = f.complete_purchase(s, source='synthetic:purchase', observed_at=NOW)
        s = f.set_context(s, plan_compatibility_needed=True)
        imported = f.record_fact(s, 'Q-C13', 'different-plan', source='synthetic:different-snapshot',
                                 observed_at='2026-10-18T08:00:00+00:00')
        self.assertEqual(imported['facts']['Q-C13']['state'], 'stale')
        self.assertEqual(imported['facts']['Q-C13']['source'], 'synthetic:different-snapshot')
        self.assertTrue(f.assessment(imported)['G2']['conditional_plan_only'])
        # Even a later imported snapshot is not an explicit current reply.
        later = f.record_fact(imported, 'Q-C13', 'later-plan', source='synthetic:later-snapshot',
                              observed_at='2026-10-18T09:40:00+00:00')
        self.assertEqual(later['facts']['Q-C13']['state'], 'stale')
        asked = f.mark_asked(later, 'Q-C13')
        another = f.record_fact(asked, 'Q-C13', 'another-old-plan', source='synthetic:another-snapshot',
                                observed_at='2026-10-18T09:50:00+00:00')
        self.assertEqual(another['facts']['Q-C13']['clarification_count'], 1)
        self.assertEqual(another['facts']['Q-C13']['state'], 'stale')
        current = answer(later, 'Q-C13', 'current-plan', observed_at='2026-10-18T10:00:00+00:00', current_reply=True)
        self.assertEqual(current['facts']['Q-C13']['state'], 'reported')
        # No prior C13 does not allow a pre-completion plan snapshot either.
        empty = f.complete_purchase(base(), source='synthetic:purchase', observed_at=NOW)
        empty = answer(empty, 'Q-C13', 'old-plan', observed_at=OLD_TIME)
        self.assertEqual(empty['facts']['Q-C13']['state'], 'stale')

    def test_t84_new_task_or_device_cannot_escape_unresolved_plan_review(self):
        for response in [None, 'unknown', 'declined', 'deferred', 'target_changed']:
            for target in [None, 'second-device']:
                with self.subTest(response=response, target=target):
                    s = answer(base(plan_compatibility_needed=True), 'Q-C13', 'retained-plan', observed_at=OLD_TIME)
                    s = f.resume_interview(s, resume_id='unresolved-plan')
                    if response:
                        s = f.record_resume_review(s, resume_id='unresolved-plan', response=response, source='synthetic:review')
                    next_task = f.begin_task(s, task_id='new-task', task='network', target_alias=target)
                    self.assertEqual(next_task['facts']['Q-C13']['state'], 'stale')
                    self.assertEqual(next_task['facts']['Q-C13']['observed_at'], OLD_TIME)
                    next_task = f.set_context(next_task, plan_compatibility_needed=True)
                    next_task = complete(next_task)
                    self.assertTrue(f.assessment(next_task)['G2']['conditional_plan_only'])
                    self.assertEqual(f.next_question(next_task)['id'], 'Q-C13')

    def test_t84_incident_pause_no_cleanup_priorities(self):
        s = base(task='cleanup', plan_compatibility_needed=True)
        stopped = answer(s, 'Q-D02', 'no_cleanup')
        self.assertEqual(ids(stopped), [])
        self.assertIsNone(f.next_question(stopped))
        paused = f.set_context(s, paused=True)
        self.assertIsNone(f.next_question(paused))
        self.assertEqual(f.assessment(paused)['G1']['status'], 'paused')
        for incident in ['credential_exposure', 'suspension', 'data_risk', 'duplicate_charge']:
            urgent = f.set_context(s, incident=incident)
            self.assertTrue(all(qid.startswith('Q-H') for qid in ids(urgent)))
            self.assertNotIn('Q-C13', ids(urgent))
            self.assert_no_permission(urgent)
        device = answer(s, 'Q-D01', 'current_restriction_on_target')
        self.assertEqual(ids(device), ['Q-H01', 'Q-C04'])

    def test_t84_resume_includes_dormant_current_plan_and_preserves_provenance(self):
        s = answer(base(), 'Q-C13', 'plan-A', observed_at=OLD_TIME)
        s = f.set_context(s, paused=True)
        resumed = f.resume_interview(s, resume_id='pause-a')
        self.assertIn('Q-C13', resumed['resume_review']['scope_keys'])
        self.assertIn('当前套餐', f.resume_review_prompt(resumed)['prompt'])
        self.assertIsNone(f.next_question(resumed))
        active = f.set_context(resumed, plan_compatibility_needed=True)
        self.assertIsNone(f.next_question(active))
        reviewed = f.record_resume_review(active, resume_id='pause-a', response='unchanged', source='synthetic:resume')
        self.assertEqual(reviewed['facts']['Q-C13'], s['facts']['Q-C13'])
        self.assertEqual(f.resume_interview(reviewed, resume_id='pause-a'), reviewed)
        self.assert_no_permission(reviewed)

    def test_t84_resume_changed_unknown_declined_deferred_and_target_change(self):
        for response in ['changed', 'unknown', 'declined', 'deferred', 'target_changed']:
            with self.subTest(response=response):
                s = answer(complete(base(plan_compatibility_needed=True)), 'Q-C13', 'old-plan', observed_at=OLD_TIME, correction=True)
                s = f.resume_interview(s, resume_id='pause-b')
                s = f.record_resume_review(s, resume_id='pause-b', response=response,
                                          changed_keys=['Q-C13'] if response == 'changed' else (), source='synthetic:resume')
                self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
                if response == 'changed':
                    self.assertEqual(s['facts']['Q-C13']['state'], 'stale')
                    self.assertEqual(f.next_question(s)['id'], 'Q-C13')
                    self.assertEqual(s['facts']['Q-C13']['observed_at'], OLD_TIME)
                else:
                    self.assertIsNone(f.resume_review_prompt(s))
                    self.assertIsNone(f.next_question(s))


class SubscriptionRepairCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(SCRIPTS / 'interview_cli.py'), *args],
                              capture_output=True, encoding='utf-8', timeout=15,
                              env={**os.environ, 'PYTHONUTF8': '1', 'PYTHONIOENCODING': 'utf-8', 'PYTHONDONTWRITEBYTECODE': '1'})

    def test_cli_optional_context_normal_reply_and_private_save_load(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path, ctx, answer_path, output = [root / name for name in ['input.json', 'context.json', 'reply.json', 'output.json']]
            state = complete(base(), except_ids={'Q-C13'})
            state_path.write_text(f.dumps_state(state, host_opt_in=True), encoding='utf-8')
            ctx.write_text(json.dumps({'plan_compatibility_needed': True}), encoding='utf-8')
            result = self.run_cli('--input', str(state_path), '--context-file', str(ctx), '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertEqual(report['question']['id'], 'Q-C13')
            self.assertFalse(report['action_executed'])
            self.assertEqual(report['assessment']['G2']['status'], 'blocked')
            saved = json.loads(output.read_text(encoding='utf-8'))
            self.assertTrue(saved['context']['plan_compatibility_needed'])
            self.assertNotIn('Q-C13', saved['facts'])
            source = 'synthetic:private-current-plan-source'
            answer_path.write_text(json.dumps({'question_id': 'Q-C13', 'value': 'reported-plan-A', 'source': source}), encoding='utf-8')
            second = root / 'second.json'
            result = self.run_cli('--input', str(output), '--answer-file', str(answer_path), '--output', str(second))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            report = json.loads(result.stdout)
            self.assertIsNone(report['question'])
            self.assertEqual(report['assessment']['G2']['status'], 'pass')
            self.assertEqual(report['assessment']['current_plan_dependency']['compatibility'], 'not_established')
            self.assertNotIn(source, result.stdout + result.stderr)
            saved = json.loads(second.read_text(encoding='utf-8'))
            self.assertEqual(saved['facts']['Q-C13']['source'], source)
            self.assertEqual(saved['facts']['Q-C13']['subject_ref'], saved['account_alias'])
            self.assertFalse(f.loads_state(json.dumps(saved))['persistence_consent']['private_save'])
            # Bound account mismatch and invalid bool fail without partial save.
            for extra in [['--account-ref', 'wrong-account'], ['--context-file', str(ctx)]]:
                ctx.write_text(json.dumps({'plan_compatibility_needed': 'yes'}), encoding='utf-8')
                bad_output = root / 'must-not-save.json'
                bad = self.run_cli('--input', str(second), *extra, '--output', str(bad_output))
                self.assertEqual(bad.returncode, 2)
                self.assertFalse(bad_output.exists())
                self.assertFalse(json.loads(bad.stdout)['action_executed'])

    def test_cli_returning_refund_explicit_task_normalization(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            state_path, ctx, reply, output = [root / name for name in ['state.json', 'context.json', 'reply.json', 'result.json']]
            state = answer(base('returning_subscription', 'subscription_preparation'), 'Q-C08', 'Pro')
            state_path.write_text(f.dumps_state(state, host_opt_in=True), encoding='utf-8')
            ctx.write_text(json.dumps({'task': 'billing_issue'}), encoding='utf-8')
            result = self.run_cli('--input', str(state_path), '--context-file', str(ctx))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertEqual(json.loads(result.stdout)['question']['id'], 'Q-P02')
            reply.write_text(json.dumps({'question_id': 'Q-P02', 'value': {
                'plan': 'former-plan', 'billing_channel': 'apple', 'status': 'expired', 'pending_issue': 'pending_refund'}}), encoding='utf-8')
            result = self.run_cli('--input', str(state_path), '--context-file', str(ctx), '--answer-file', str(reply), '--output', str(output))
            self.assertEqual(result.returncode, 0, result.stdout + result.stderr)
            self.assertIsNone(json.loads(result.stdout)['question'])
            saved = json.loads(output.read_text(encoding='utf-8'))
            self.assertEqual(saved['current_subscription'], state['current_subscription'])
            self.assertEqual(saved['facts']['Q-C08'], state['facts']['Q-C08'])
            self.assertFalse(saved['context']['subscription_conflict'])
            self.assertEqual(saved['payment_intent'], 'troubleshoot')


if __name__ == '__main__':
    unittest.main()
