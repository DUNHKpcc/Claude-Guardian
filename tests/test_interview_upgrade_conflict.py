"""Derived T77/T80 runtime regressions; synthetic, not whole-case acceptance.

GUARDIAN_UPGRADE_TEST_ROOT can point at the exact frozen pre-repair runtime.
No live entitlement, payment, real device, permission, or source-currentness proof.
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

try:
    import jsonschema
except ImportError:
    jsonschema = None

ROOT = Path(os.environ.get('GUARDIAN_UPGRADE_TEST_ROOT', Path(__file__).resolve().parents[1]))
SCRIPTS = ROOT / 'skills/claude-guardian/scripts'
spec = importlib.util.spec_from_file_location('upgrade_conflict_flow', SCRIPTS / 'interview_flow.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)
OLD = '2026-10-18T08:00:00+00:00'
PAGE = '2026-10-18T09:00:00+00:00'
NOW = '2026-10-18T10:00:00+00:00'
LATER = '2026-10-18T11:00:00+00:00'
ORDER = {'plan': 'current-plan-A', 'billing_channel': 'web', 'status': 'active', 'pending_issue': 'none_reported'}
CONFLICT = {**ORDER, 'pending_issue': 'page-shows-renewal-conflicts-with-first-subscription',
            'page_relation': 'same_target'}
FIRST = {'Q-J01': 'first_subscription', 'Q-C02': 'macos', 'Q-C01': 'web',
         'Q-OS03': 'fixture-version', 'Q-C08': 'desired-plan-B', 'Q-C03': 'none_reported',
         'Q-C04': 'registered_login_reported', 'Q-C05': 'local', 'Q-C06': 'email',
         'Q-C09': 'fixture-region', 'Q-N01': 'fixture-proxy', 'Q-N02': 'fixture-local-browser',
         'Q-N03': 'fixture-no-switching', 'Q-N04': 'fixture-selected-device', 'Q-N06': 'fixture-personal-device',
         'Q-P07': 'fixture-renewal-explanation', 'Q-X01': 'existing_stable_exit', 'Q-W01': 'fixture-card-category',
         'Q-W02': 'fixture-truthful-billing', 'Q-W03': 'fixture-recurring-report',
         'Q-W04': 'fixture-total-report', 'Q-L01': 'fixture-browser-metadata',
         'Q-L04': 'fixture-no-local-dependency', 'Q-C12': 'fixture-preserve-all',
         'Q-Z01': 'plan-only', 'Q-C10': 'concise'}


def fact(s, qid, value=None, **kw):
    return f.record_fact(s, qid, value, source=kw.pop('source', 'synthetic:reply'),
                         observed_at=kw.pop('observed_at', OLD), **kw)


def ids(s):
    return [q['id'] for q in f.applicable_questions(s)]


def upgrade(**order):
    return f.record_facts(f.new_state('fixture-device', 'fixture-account', task_id='upgrade-task'), [
        {'question_id': 'Q-J01', 'value': 'existing_subscriber'},
        {'question_id': 'Q-C11', 'value': 'upgrade'},
        {'question_id': 'Q-C08', 'value': 'desired-plan-B'},
        {'question_id': 'Q-P02', 'value': {**ORDER, **order}}], source='synthetic:one-reply')


def first():
    s = f.set_context(f.new_state('fixture-device', 'fixture-account', task_id='first-task'),
                       billing_channel='web', contact_phase='PC2')
    # PC2 is only a synthetic label for complete coverage, never a real handoff.
    for qid, value in FIRST.items():
        s = fact(s, qid, value)
    return s


def pending():
    s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
    return fact(s, 'Q-P02', CONFLICT, source='synthetic:page-details', observed_at=PAGE, current_reply=True)


def resolution(s, outcome='existing_subscription', next_task='upgrade', **overrides):
    order = {**ORDER, 'page_relation': 'same_target'}
    stage = 'existing_subscriber'
    if outcome in {'other_target_page', 'outdated_page'}:
        stage = 'first_subscription'
        order.update(status='none', page_relation='other_target' if outcome == 'other_target_page' else 'outdated')
    answers = [{'question_id': 'Q-J01', 'value': stage}, {'question_id': 'Q-P02', 'value': order}]
    if outcome == 'existing_subscription' and next_task is not None:
        answers.append({'question_id': 'Q-C11', 'value': next_task})
    return {**{'episode_id': s['subscription_review']['episode_id'], 'account_ref': s['account_alias'],
               'target_ref': s['target_alias'], 'task_id': s['task_id'], 'outcome': outcome,
               'answers': answers, 'source': 'synthetic:resolution', 'observed_at': NOW,
               'current_reply': True}, **overrides}


class UpgradeConflictFlowTests(unittest.TestCase):
    def setUp(self):
        guards = ExitStack()
        self.addCleanup(guards.close)
        guards.enter_context(patch.object(f, '_now', return_value=NOW))
        self.io_guards = []
        for name in ['socket.socket', 'socket.create_connection', 'socket.getaddrinfo',
                     'subprocess.run', 'subprocess.Popen', 'builtins.open', 'io.open',
                     'os.open', 'pathlib.Path.open', 'os.system', 'os.popen']:
            self.io_guards.append(guards.enter_context(patch(name, side_effect=AssertionError('Unexpected I/O: ' + name))))

    def tearDown(self):
        for guard in self.io_guards:
            guard.assert_not_called()

    def no_authority(self, s):
        self.assertEqual(f.assessment(s)['G3']['status'], 'blocked')
        self.assertFalse(any(s['persistence_consent'].values()))
        self.assertNotIn('purchase_completion', s)

    def test_original_t77_known_upgrade_avoids_new_purchase_survey(self):
        s = upgrade()
        self.assertIsNone(f.next_question(s))
        self.assertEqual(ids(s), ['Q-P02', 'Q-C08'])
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(s['facts']['Q-P02']['value']['plan'], 'current-plan-A')
        self.assertEqual(s['facts']['Q-C08']['value'], 'desired-plan-B')
        self.assertEqual(s['payment_intent'], 'upgrade')
        self.assertNotIn('Q-C13', s['facts'])
        self.assertEqual(f.assessment(s)['route_confirmation'], 'unconfirmed')
        self.no_authority(s)

    def test_original_t80_describing_complete_conflict_does_not_resolve_it(self):
        s = first()
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        s = f.set_context(s, subscription_conflict=True)
        self.assertEqual(f.next_question(s)['id'], 'Q-P02')
        s = fact(s, 'Q-P02', CONFLICT, observed_at=NOW, current_reply=True)
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
        self.assertEqual(f.assessment(s)['G1']['status'], 'complete')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(s['current_subscription']['status'], 'none_reported')
        self.assertEqual(s['payment_intent'], 'new_subscription')
        self.no_authority(s)

    def test_upgrade_only_missing_current_plan_or_channel_or_target(self):
        for key, expected in [('plan', '当前套餐'), ('billing_channel', '原购买渠道')]:
            s = upgrade(**{key: None})
            question = f.next_question(s)
            self.assertEqual(question['id'], 'Q-P02')
            self.assertIn(expected, question['prompt'])
            self.assertTrue(question['clarification'])
            self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = upgrade()
        del s['facts']['Q-C08']
        self.assertEqual(f.next_question(s)['id'], 'Q-C08')
        self.assertEqual(s['facts']['Q-P02']['value']['plan'], 'current-plan-A')
        self.assertNotIn('Q-C08', s['facts'])

    def test_upgrade_current_plan_reuse_never_copies_desired_plan(self):
        s = fact(upgrade(plan=None), 'Q-C13', 'current-plan-from-reported-compatibility', observed_at=NOW, current_reply=True)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(s['facts']['Q-C08']['value'], 'desired-plan-B')
        s = f.invalidate_facts(s, ['Q-C13'], reason='current plan changed')
        self.assertEqual(f.next_question(s)['id'], 'Q-P02')

    def test_upgrade_comparison_requires_only_use_and_budget(self):
        s = fact(upgrade(), 'Q-C08', 'undecided')
        self.assertEqual(ids(s), ['Q-P02', 'Q-C08', 'Q-C01', 'Q-P05'])
        s = fact(fact(s, 'Q-C01', 'web-writing'), 'Q-P05', 'synthetic-budget-range')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.assessment(s)['upgrade_scope']['billing_feasibility'], 'not_established')
        self.assertEqual(s['facts']['Q-C08']['value'], 'undecided')

    def test_upgrade_channels_remain_distinct_and_do_not_require_old_order_survey(self):
        for channel in ['apple', 'google', 'web']:
            s = f.set_context(upgrade(billing_channel=channel, status=None, pending_issue=None), billing_channel='compare')
            self.assertIsNone(f.next_question(s))
            self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
            self.assertEqual(s['facts']['Q-P02']['value']['billing_channel'], channel)
            self.assertEqual(s['context']['billing_channel'], 'compare')
            self.assertNotIn('Q-A06', ids(s))

    def test_unknown_declined_deferred_are_terminal_without_a06_repeat(self):
        for qid in ['Q-P02', 'Q-C08']:
            for state in ['unknown', 'declined', 'deferred']:
                s = fact(upgrade(billing_channel='apple'), qid, state_name=state)
                self.assertIsNone(f.next_question(s))
                self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
                self.assertNotIn('Q-A06', ids(s))

    def test_partial_current_order_has_one_clarification_through_roundtrip(self):
        s = upgrade(plan=None)
        s = f.mark_asked(s, 'Q-P02')
        s = fact(s, 'Q-P02', {'billing_channel': 'web'}, observed_at=NOW, current_reply=True)
        s = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        self.assertEqual(s['facts']['Q-P02']['clarification_count'], 1)
        with self.assertRaises(f.InterviewError):
            fact(s, 'Q-P02', {'billing_channel': 'web'}, clarification=True)

    def test_explicit_other_tasks_keep_their_real_requirements(self):
        for task in ['environment', 'network', 'cleanup']:
            s = f.set_context(upgrade(), task=task)
            self.assertIn('Q-C02', ids(s))
            self.assertNotIn('Q-C08', ids(s))
            self.assertFalse(any(q.startswith(('Q-P', 'Q-A', 'Q-G', 'Q-W')) for q in ids(s)))
            if task == 'cleanup':
                self.assertIn('Q-D02', ids(s))
            else:
                self.assertIn('Q-N01', ids(s))

    def test_explicit_upgrade_client_dependency_remains_separate_gap(self):
        s = f.set_context(upgrade(), compatibility_needed=True)
        self.assertEqual(ids(s), ['Q-P02', 'Q-C08', 'Q-C02', 'Q-L02'])
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = fact(fact(s, 'Q-C02', 'macos'), 'Q-L02', 'synthetic-client-requirements-reported')
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.no_authority(s)

    def test_emergency_and_pause_still_take_priority(self):
        s = f.set_context(upgrade(), incident='credential_exposure')
        self.assertEqual(f.next_question(s)['id'], 'Q-H01')
        self.assertNotIn('Q-P02', ids(s))
        self.assertEqual(f.assessment(s)['G1']['status'], 'emergency_deferred')
        self.assertIsNone(f.next_question(f.set_context(upgrade(), paused=True)))

    def test_original_sources_and_times_survive_order_replacement_and_reload(self):
        s = pending()
        old = deepcopy(s['subscription_review'])
        s = fact(s, 'Q-P02', {**ORDER, 'pending_issue': 'still-not-resolved'}, observed_at=NOW)
        s = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertEqual(s['subscription_review'], old)
        self.assertEqual(old['original']['Q-J01']['source'], 'synthetic:reply')
        self.assertEqual(old['original']['Q-J01']['observed_at'], OLD)
        self.assertEqual(old['detail']['source'], 'synthetic:page-details')
        self.assertEqual(old['detail']['observed_at'], PAGE)
        self.assertEqual(old['observed_at'], PAGE)
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')

    def test_boolean_cannot_clear_structured_or_legacy_unresolved_episode(self):
        for s in [pending(), {**first(), 'context': {**first()['context'], 'subscription_conflict': True}}]:
            before = deepcopy(s)
            with self.assertRaises(f.InterviewError):
                f.set_context(s, subscription_conflict=False)
            self.assertEqual(s, before)
        ordinary = first()
        self.assertEqual(f.set_context(ordinary, subscription_conflict=False), ordinary)

    def test_same_target_resolution_corrects_journey_and_explicit_task_atomically(self):
        s = pending()
        original = deepcopy(s)
        r = f.resolve_subscription_conflict(s, **resolution(s))
        self.assertEqual(s, original)
        self.assertEqual(r['current_subscription'], {'status': 'active_reported', 'source': 'synthetic:resolution', 'observed_at': NOW})
        self.assertEqual(r['facts']['Q-J01']['value'], 'existing_subscriber')
        self.assertEqual(r['payment_intent'], 'upgrade')
        self.assertEqual(r['subscription_review']['original'], s['subscription_review']['original'])
        self.assertEqual(r['subscription_review']['detail'], s['subscription_review']['detail'])
        self.assertFalse(r['context']['subscription_conflict'])
        self.assertEqual(f.assessment(r)['G2']['status'], 'pass')
        self.assertIsNone(f.next_question(r))
        self.no_authority(r)

    def test_resolution_without_intermediate_details_does_not_invent_original_page_facts(self):
        s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
        self.assertIsNone(s['subscription_review']['detail'])
        r = f.resolve_subscription_conflict(s, **resolution(s))
        self.assertIsNone(r['subscription_review']['detail'])
        self.assertEqual(r['subscription_review']['source'], 'synthetic:page')
        self.assertEqual(r['subscription_review']['resolution']['answers'][1]['value']['page_relation'], 'same_target')

    def test_discovery_without_next_task_asks_one_task_question(self):
        s = pending()
        r = f.resolve_subscription_conflict(s, **resolution(s, next_task=None))
        self.assertEqual(ids(r), ['Q-C11'])
        self.assertEqual(f.next_question(r)['id'], 'Q-C11')
        self.assertEqual(r['payment_intent'], 'unresolved')
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')
        r = fact(r, 'Q-C11', state_name='declined', observed_at=LATER)
        self.assertIsNone(f.next_question(r))
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')

    def test_known_active_resolution_preserves_unknown_upgrade_plan_and_channel_gaps(self):
        s = pending()
        args = resolution(s)
        args['answers'][1]['value'] = {'status': 'active', 'page_relation': 'same_target', 'pending_issue': 'none_reported'}
        r = f.resolve_subscription_conflict(s, **args)
        self.assertFalse(r['context']['subscription_conflict'])
        self.assertEqual(f.journey(r), 'existing_subscriber')
        self.assertEqual(f.next_question(r)['id'], 'Q-P02')
        self.assertEqual(f.assessment(r)['upgrade_scope']['current_order_gaps'], ['current_plan', 'current_channel'])
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')
        self.assertNotIn('plan', r['facts']['Q-P02']['value'])

    def test_other_target_or_outdated_page_preserves_original_journey_and_target(self):
        for outcome in ['other_target_page', 'outdated_page']:
            s = pending()
            r = f.resolve_subscription_conflict(s, **resolution(s, outcome))
            self.assertEqual(r['account_alias'], s['account_alias'])
            self.assertEqual(r['target_alias'], s['target_alias'])
            self.assertEqual(f.journey(r), 'first_subscription')
            self.assertEqual(r['current_subscription']['status'], 'none_reported')
            self.assertEqual(r['payment_intent'], 'new_subscription')
            self.assertEqual(f.assessment(r)['G2']['status'], 'pass')
            self.no_authority(r)

    def test_unknown_declined_deferred_resolution_keeps_conditional_summary(self):
        for outcome in ['unknown', 'declined', 'deferred']:
            s = pending()
            r = f.resolve_subscription_conflict(s, **resolution(s, outcome, answers=[]))
            self.assertEqual(r['facts']['Q-P02']['state'], outcome)
            self.assertTrue(r['context']['subscription_conflict'])
            self.assertEqual(r['subscription_review']['status'], 'unresolved')
            self.assertIsNone(f.next_question(r))
            self.assertEqual(ids(r), ['Q-P02'])
            self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')

    def test_resolution_rejects_wrong_binding_imports_staleness_and_malformed_data_atomically(self):
        s = pending()
        good = resolution(s)
        bad = [{'account_ref': 'other-account'}, {'target_ref': 'other-device'}, {'task_id': 'other-task'},
               {'episode_id': 'not-this-episode'}, {'current_reply': False}, {'current_reply': 1},
               {'observed_at': OLD}, {'observed_at': PAGE}, {'observed_at': '2026-10-18'},
               {'source': ''}, {'outcome': 'resolved'}, {'answers': []}, {'answers': good['answers'][:1]},
               {'answers': good['answers'] + [good['answers'][0]]},
               {'answers': [{'question_id': 'Q-J01', 'value': 'existing_subscriber', 'state': 'inferred'}] + good['answers'][1:]},
               {'answers': [{'question_id': 'Q-J01', 'value': 'first_subscription'}] + good['answers'][1:]}]
        for updates in bad:
            with self.subTest(updates=updates):
                before = deepcopy(s)
                with self.assertRaises(f.InterviewError):
                    f.resolve_subscription_conflict(s, **{**good, **updates})
                self.assertEqual(s, before)
        for key, value in [('pending_issue', 'still_unresolved'), ('status', 'expired'),
                           ('page_relation', 'other_target'), ('plan', ''), ('billing_channel', 'none')]:
            args = deepcopy(good)
            args['answers'][1]['value'][key] = value
            with self.subTest(key=key), self.assertRaises(f.InterviewError):
                f.resolve_subscription_conflict(s, **args)

    def test_resolution_requires_current_evidence_even_newer_import_or_correction(self):
        s = pending()
        s = fact(s, 'Q-P02', ORDER, observed_at=LATER, current_reply=False, correction=True)
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(s, **resolution(s))
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(s, **resolution(s, observed_at=LATER, current_reply=False))

    def test_resolution_retry_is_idempotent_and_cannot_resolve_new_episode(self):
        s = pending()
        args = resolution(s)
        r = f.resolve_subscription_conflict(s, **args)
        r = fact(r, 'Q-C08', 'later-desired-plan', observed_at=LATER)
        self.assertEqual(f.resolve_subscription_conflict(r, **args), r)
        self.assertEqual(f.resolve_subscription_conflict(r, **{**args, 'observed_at': None}), r)
        newer = f.report_subscription_conflict(r, source='synthetic:new-page', observed_at=LATER, current_reply=True)
        self.assertNotEqual(newer['subscription_review']['episode_id'], args['episode_id'])
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(newer, **args)
        self.assertEqual(f.assessment(newer)['G2']['status'], 'blocked')
        self.assertEqual(f.report_subscription_conflict(newer, source='synthetic:new-page', observed_at=LATER, current_reply=True), newer)

    def test_resolution_explicit_technical_next_task_retry_is_safe(self):
        s = pending()
        args = resolution(s, next_task='environment')
        r = f.resolve_subscription_conflict(s, **args)
        self.assertEqual(r['context']['task'], 'environment')
        self.assertEqual(r['payment_intent'], 'none')
        self.assertNotIn('Q-C08', ids(r))
        self.assertEqual(f.resolve_subscription_conflict(r, **args), r)

    def test_new_episode_cannot_use_resolution_time_or_older_report(self):
        s = pending()
        r = f.resolve_subscription_conflict(s, **resolution(s))
        for observed_at in [OLD, PAGE, NOW]:
            with self.assertRaises(f.InterviewError):
                f.report_subscription_conflict(r, source='synthetic:replay', observed_at=observed_at, current_reply=True)
        with self.assertRaises(f.InterviewError):
            f.set_context(r, subscription_conflict=True)

    def test_legacy_invalidation_keeps_original_unresolved_evidence(self):
        s = first()
        s['context']['subscription_conflict'] = True
        r = f.invalidate_facts(s, ['Q-J01'], reason='stale journey')
        self.assertEqual(r['subscription_review']['original']['Q-J01'], s['facts']['Q-J01'])
        self.assertEqual(r['facts']['Q-J01']['state'], 'stale')
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')

    def test_legacy_true_migrates_without_invented_time_false_shape_remains_compatible(self):
        old = first()
        old['context']['subscription_conflict'] = True
        r = f.loads_state(json.dumps(old))
        self.assertIsNone(r['subscription_review']['observed_at'])
        self.assertEqual(r['subscription_review']['status'], 'unresolved')
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')
        self.assertEqual(f.loads_state(f.dumps_state(r, host_opt_in=True)), r)
        fresh = f.new_state('device', 'account')
        self.assertNotIn('subscription_review', f.loads_state(json.dumps(fresh)))
        self.assertNotIn('subscription_review', f.STATE_SCHEMA['required'])

    def test_malformed_loaded_episode_cannot_forge_flag_or_subject(self):
        s = pending()
        bad = deepcopy(s)
        bad['context']['subscription_conflict'] = False
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(bad))
        bad = deepcopy(s)
        bad['subscription_review']['detail']['subject_ref'] = 'another-account'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(bad))
        bad = deepcopy(s)
        bad['subscription_review']['binding']['account_alias'] = 'another-account'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(bad))

    def test_same_account_task_device_rebind_is_dormant_then_blocks_purchase(self):
        s = pending()
        for task in ['environment', 'network', 'cleanup']:
            changed = f.begin_task(s, task_id='technical-task', task=task, target_alias='other-device')
            self.assertEqual(changed['subscription_review'], s['subscription_review'])
            self.assertTrue(changed['context']['subscription_conflict'])
            self.assertFalse(f.assessment(changed)['subscription_review']['blocks_current_task'])
            self.assertNotIn('Q-P02', ids(changed))
            again = f.begin_task(changed, task_id='purchase-task', task='subscription_preparation')
            self.assertEqual(f.assessment(again)['G2']['reason'], 'subscription_conflict_unresolved')
            with self.assertRaises(f.InterviewError):
                f.resolve_subscription_conflict(again, **resolution(s))
        other = f.begin_task(s, task_id='other-target', task='subscription_preparation', account_alias='other-account')
        self.assertNotIn('subscription_review', other)
        self.assertFalse(other['context']['subscription_conflict'])

    def test_completed_purchase_report_does_not_clear_account_contradiction(self):
        s = pending()
        r = f.complete_purchase(s, source='synthetic:reported-completion', observed_at=NOW)
        self.assertTrue(r['context']['subscription_conflict'])
        self.assertEqual(r['subscription_review'], s['subscription_review'])
        self.assertFalse(f.assessment(r)['subscription_review']['blocks_current_task'])
        r = f.begin_task(r, task_id='later-upgrade', task='upgrade')
        self.assertEqual(f.assessment(r)['G2']['reason'], 'subscription_conflict_unresolved')

    def test_resolution_does_not_discharge_unrelated_interruption_review(self):
        s = f.resume_interview(pending(), resume_id='interruption')
        r = f.resolve_subscription_conflict(s, **resolution(s, 'outdated_page'))
        self.assertEqual(r['resume_review']['status'], 'pending')
        self.assertEqual(f.assessment(r)['G2']['status'], 'blocked')
        self.assertEqual(f.assessment(r)['G2']['reason'], 'resume_review_required')

    def test_negative_apple_and_expired_refund_are_not_contradictions(self):
        apple = f.set_context(first(), billing_channel='apple')
        for qid in ['Q-A01', 'Q-A02', 'Q-A03', 'Q-A04', 'Q-A05', 'Q-A10', 'Q-M01']:
            apple = fact(apple, qid, 'no_usable_sign_in_or_verification' if qid == 'Q-A02' else ('none' if qid == 'Q-M01' else 'fixture-report'))
        self.assertEqual(f.assessment(apple)['G2']['status'], 'pass')
        self.assertFalse(apple['context']['subscription_conflict'])
        self.assertEqual(apple['facts']['Q-A02']['state'], 'reported')
        expired = fact(f.new_state('device', 'account'), 'Q-J01', 'returning_subscription')
        expired = f.set_context(expired, task='billing_issue', billing_channel='apple')
        expired = fact(expired, 'Q-P02', {**ORDER, 'billing_channel': 'apple', 'status': 'expired', 'pending_issue': 'pending_refund'})
        self.assertFalse(expired['context']['subscription_conflict'])
        self.assertEqual(f.assessment(expired)['G2']['status'], 'pass')
        self.assertEqual(expired['current_subscription']['status'], 'none_reported')

    def test_first_and_returning_preparation_retain_real_purchase_requirements(self):
        for journey in ['first_subscription', 'returning_subscription']:
            s = fact(f.new_state('device', 'account'), 'Q-J01', journey)
            self.assertIn('Q-C02', ids(s))
            self.assertIn('Q-C08', ids(s))
            self.assertIn('Q-N01', ids(s))
            self.assertNotIn('Q-P02', ids(s))
            self.assertNotIn('Q-A06', ids(s))


    def test_newer_pending_report_retains_original_and_blocks_older_resolution(self):
        s = pending()
        original = deepcopy(s['subscription_review'])
        later = f.report_subscription_conflict(s, source='synthetic:later-page', observed_at=LATER, current_reply=True)
        self.assertEqual(later['subscription_review']['episode_id'], original['episode_id'])
        for key in ['source', 'observed_at', 'original', 'detail']:
            self.assertEqual(later['subscription_review'][key], original[key])
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(later, **resolution(later))
        self.assertIn('latest_report', later['subscription_review'])
        self.assertEqual(later['subscription_review']['latest_report']['observed_at'], LATER)
        self.assertEqual(f.next_question(later)['id'], 'Q-P02')
        before = deepcopy(later)
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(later, **resolution(later))
        self.assertEqual(later, before)
        later = f.loads_state(f.dumps_state(later, host_opt_in=True))
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(later, **resolution(later))
        self.assertEqual(f.assessment(later)['G2']['status'], 'blocked')

    def test_latest_report_retries_never_refresh_or_erase_newer_barrier(self):
        s = pending()
        s = f.report_subscription_conflict(s, source='synthetic:later-page', observed_at=LATER, current_reply=True)
        for source, time in [('synthetic:later-page', LATER), ('synthetic:page', PAGE)]:
            self.assertEqual(f.report_subscription_conflict(s, source=source, observed_at=time, current_reply=True), s)
        with self.assertRaises(f.InterviewError):
            f.report_subscription_conflict(s, source='synthetic:older-unmatched', observed_at=NOW, current_reply=True)
        with self.assertRaises(f.InterviewError):
            f.report_subscription_conflict(s, source='synthetic:same-time-unmatched', observed_at=LATER, current_reply=True)
        resolved_at = '2026-10-18T12:00:00+00:00'
        r = f.resolve_subscription_conflict(s, **resolution(s, observed_at=resolved_at))
        self.assertEqual(f.resolve_subscription_conflict(r, **resolution(s, observed_at=resolved_at)), r)
        self.assertEqual(f.report_subscription_conflict(r, source='synthetic:later-page', observed_at=LATER, current_reply=True), r)
        self.no_authority(r)

    def test_new_episode_gets_current_detail_and_fresh_bounded_clarification(self):
        s = pending()
        s = fact(s, 'Q-P02', {'status': 'active'}, observed_at=NOW, current_reply=True)
        s = f.mark_asked(s, 'Q-P02')
        self.assertEqual(s['facts']['Q-P02']['clarification_count'], 1)
        r = f.resolve_subscription_conflict(s, **resolution(s))
        previous = deepcopy(r['facts']['Q-P02'])
        n = f.report_subscription_conflict(r, source='synthetic:new-episode', observed_at=LATER, current_reply=True)
        self.assertEqual(n['subscription_review']['original']['Q-P02'], previous)
        self.assertIsNone(n['subscription_review']['detail'])
        self.assertEqual(n['facts']['Q-P02']['state'], 'stale')
        self.assertEqual(n['facts']['Q-P02']['clarification_count'], 0)
        self.assertEqual(f.next_question(n)['id'], 'Q-P02')
        n = f.mark_asked(n, 'Q-P02')
        self.assertIsNone(f.next_question(n))
        self.assertEqual(f.assessment(n)['G2']['status'], 'blocked')

    def test_genuinely_current_detail_supplied_before_report_is_reused(self):
        s = first()
        detail = {'status': 'active', 'page_relation': 'same_target'}
        s = fact(s, 'Q-P02', detail, source='synthetic:current-reply', observed_at=PAGE, current_reply=True)
        n = f.report_subscription_conflict(s, source='synthetic:page', observed_at=PAGE, current_reply=True)
        self.assertEqual(n['facts']['Q-P02'], s['facts']['Q-P02'])
        self.assertEqual(n['subscription_review']['detail'], s['facts']['Q-P02'])
        self.assertIsNone(f.next_question(n))
        self.assertEqual(f.assessment(n)['G1']['status'], 'complete')
        self.assertEqual(f.assessment(n)['G2']['status'], 'blocked')

    def test_conflict_status_and_target_detail_is_distinct_from_old_refund_coverage(self):
        for value, expected_gap in [({'billing_channel': 'apple'}, '当前订阅状态'),
                                     ({'status': 'active'}, '对应这次目标账号'),
                                     ({'page_relation': 'same_target'}, '当前订阅状态')]:
            s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
            s = fact(s, 'Q-P02', value, observed_at=NOW, current_reply=True)
            q = f.next_question(s)
            self.assertIsNotNone(q)
            self.assertEqual(q['id'], 'Q-P02')
            self.assertIn(expected_gap, q['prompt'])
            self.assertEqual(f.assessment(s)['G1']['status'], 'partial')
            self.assertEqual(ids(s), ['Q-P02'])
            s = f.mark_asked(s, 'Q-P02')
            self.assertIsNone(f.next_question(s))
            self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
        s = fact(s, 'Q-P02', {'status': 'active', 'page_relation': 'same_target'}, observed_at=NOW, current_reply=True)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G1']['status'], 'complete')
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        self.no_authority(s)

    def test_historical_conflict_detail_import_does_not_cover_new_report(self):
        s = pending()
        n = f.report_subscription_conflict(s, source='synthetic:newer-page', observed_at=LATER, current_reply=True)
        original = deepcopy(n['facts']['Q-P02'])
        n = fact(n, 'Q-P02', CONFLICT, source='synthetic:page-details', observed_at=PAGE)
        self.assertEqual(n['facts']['Q-P02'], original)
        self.assertEqual(f.next_question(n)['id'], 'Q-P02')
        self.assertIsNone(n['subscription_review']['latest_report']['detail'])

    def test_postcompletion_current_plan_gap_preserves_known_channel_and_old_history(self):
        s = upgrade()
        old_order = deepcopy(s['facts']['Q-P02'])
        s = f.complete_purchase(s, source='synthetic:completed-upgrade', observed_at=LATER)
        s = f.begin_task(s, task_id='next-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'desired-plan-C', observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        self.assertEqual(s['facts']['Q-P02'], old_order)
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
        self.assertIn('当前套餐', f.next_question(s)['prompt'])
        self.assertNotIn('购买渠道', f.next_question(s)['prompt'])
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = fact(s, 'Q-C13', 'actual-current-plan-B', observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(s['facts']['Q-P02'], old_order)
        self.assertEqual(s['facts']['Q-C08']['value'], 'desired-plan-C')
        self.assertEqual(s['facts']['Q-C13']['value'], 'actual-current-plan-B')

    def test_postcompletion_newer_import_cannot_replace_current_reply_obligation(self):
        s = f.complete_purchase(upgrade(), source='synthetic:completed-upgrade', observed_at=LATER)
        s = f.begin_task(s, task_id='new-upgrade', task='upgrade')
        fresh_time = '2026-10-18T12:00:00+00:00'
        s = fact(s, 'Q-C08', 'desired-plan-C', observed_at=fresh_time, current_reply=True)
        s = fact(s, 'Q-P02', {**ORDER, 'plan': 'imported-plan'}, source='synthetic:newer-import', observed_at=fresh_time)
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = fact(s, 'Q-P02', {**ORDER, 'plan': 'actually-reported-current-plan'}, observed_at=fresh_time, current_reply=True)
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.complete_purchase(s, source='synthetic:completed-upgrade', observed_at=LATER), s)
        for value in [False, True]:
            with self.assertRaises(f.InterviewError):
                f.set_context(s, current_order_plan_stale=value)

    def test_stale_current_order_exact_and_newer_imports_preserve_obligation_and_budget(self):
        s = upgrade()
        old = deepcopy(s['facts']['Q-P02'])
        s = f.invalidate_facts(s, ['Q-P02'], reason='current order changed')
        s = f.mark_asked(s, 'Q-P02')
        stale = deepcopy(s['facts']['Q-P02'])
        exact = fact(s, 'Q-P02', old['value'], source=old['source'], observed_at=old['observed_at'])
        self.assertEqual(exact['facts']['Q-P02'], stale)
        later = fact(s, 'Q-P02', {**ORDER, 'plan': 'newer-import'}, source='synthetic:import', observed_at=LATER, correction=True)
        self.assertEqual(later['facts']['Q-P02']['state'], 'stale')
        self.assertEqual(later['facts']['Q-P02']['clarification_count'], 1)
        self.assertIsNone(f.next_question(later))
        self.assertEqual(f.assessment(later)['G2']['status'], 'blocked')
        fresh = fact(later, 'Q-P02', {**ORDER, 'plan': 'current-report'}, observed_at=LATER, current_reply=True)
        self.assertEqual(f.assessment(fresh)['G2']['status'], 'pass')
        self.assertEqual(fresh['facts']['Q-P02']['clarification_count'], 1)

    def test_legacy_completion_and_same_account_device_switch_keep_plan_obligation(self):
        s = f.complete_purchase(upgrade(), source='synthetic:completed-upgrade', observed_at=LATER)
        s['context'].pop('current_order_plan_stale', None)  # old schema-1 saved shape
        s = f.loads_state(json.dumps(s))
        self.assertTrue(s['context']['current_order_plan_stale'])
        old = deepcopy(s['facts']['Q-P02'])
        s = f.begin_task(s, task_id='same-account-new-device', task='upgrade', target_alias='other-device')
        self.assertEqual(s['facts']['Q-P02'], old)
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
        other = f.begin_task(s, task_id='different-account', task='subscription_preparation', account_alias='other-account')
        self.assertNotIn('current_order_plan_stale', other['context'])
        self.assertNotIn('Q-P02', other['facts'])

    def test_current_plan_invalidation_does_not_erase_old_refund_evidence(self):
        s = upgrade(billing_channel='apple', status='expired', pending_issue='pending_refund')
        old = deepcopy(s['facts']['Q-P02'])
        s = f.invalidate_facts(s, ['Q-C13'], reason='current plan changed')
        self.assertEqual(s['facts']['Q-P02'], old)
        s = f.set_context(s, task='billing_issue')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(s['facts']['Q-P02'], old)


    def test_new_current_plan_obligation_resets_only_prior_question_budget(self):
        s = upgrade(plan=None)
        s = f.mark_asked(s, 'Q-P02')
        s = fact(s, 'Q-P02', ORDER, observed_at=NOW, current_reply=True)
        self.assertEqual(s['facts']['Q-P02']['clarification_count'], 1)
        old = deepcopy(s['facts']['Q-P02'])
        s = f.complete_purchase(s, source='synthetic:next-completion', observed_at=LATER)
        s = f.begin_task(s, task_id='next-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'next-target', observed_at=LATER, current_reply=True)
        self.assertEqual(s['facts']['Q-P02']['clarification_count'], 0)
        for key in ['value', 'source', 'observed_at', 'subject_ref']:
            self.assertEqual(s['facts']['Q-P02'][key], old[key])
        self.assertEqual(f.next_question(s)['id'], 'Q-P02')
        s = f.mark_asked(s, 'Q-P02')
        self.assertIsNone(f.next_question(f.loads_state(f.dumps_state(s, host_opt_in=True))))
        retried = f.complete_purchase(s, source='synthetic:next-completion', observed_at=LATER)
        self.assertEqual(retried, s)

    def test_malformed_latest_report_rejects_atomically(self):
        s = f.report_subscription_conflict(pending(), source='synthetic:latest', observed_at=LATER, current_reply=True)
        before = deepcopy(s)
        changes = [('source', ''), ('source', True), ('observed_at', None), ('observed_at', PAGE),
                   ('observed_at', 'invalid'), ('binding', {}), ('detail', {}), ('unexpected', True)]
        for key, value in changes:
            bad = deepcopy(s)
            bad['subscription_review']['latest_report'][key] = value
            with self.subTest(key=key, value=value), self.assertRaises(f.InterviewError):
                f.loads_state(json.dumps(bad))
            self.assertEqual(s, before)
        bad = deepcopy(s)
        bad['subscription_review']['latest_report']['binding']['account_alias'] = 'different-account'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(bad))
        bad = deepcopy(s)
        bad['subscription_review']['latest_report']['detail'] = deepcopy(pending()['facts']['Q-P02'])
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(bad))


    def test_interruption_cannot_revive_retained_p02_plan_through_new_task(self):
        s = f.resume_interview(upgrade(), resume_id='upgrade-interruption')
        self.assertIn('Q-P02', s['resume_review']['retained_keys'])
        self.assertIn('Q-P02', s['resume_review']['scope_keys'])
        self.assertIn('当前套餐和原购买渠道', f.resume_review_prompt(s)['prompt'])
        old = deepcopy(s['facts']['Q-P02'])
        for target in [s['target_alias'], 'different-device']:
            n = f.begin_task(s, task_id='later-upgrade', task='upgrade', target_alias=target)
            n = fact(n, 'Q-C08', 'next-target', observed_at=LATER, current_reply=True)
            self.assertEqual(f.assessment(n)['upgrade_scope']['current_order_gaps'], ['current_plan'])
            self.assertEqual(f.assessment(n)['G2']['status'], 'blocked')
            self.assertEqual(f.next_question(n)['id'], 'Q-P02')
            self.assertNotIn('购买渠道', f.next_question(n)['prompt'])
            self.assertEqual(n['facts']['Q-P02']['value'], old['value'])
            n = fact(n, 'Q-P02', old['value'], source=old['source'], observed_at=old['observed_at'])
            self.assertEqual(f.assessment(n)['G2']['status'], 'blocked')
            n = fact(n, 'Q-C13', 'current-plan-after-interruption', observed_at=LATER, current_reply=True)
            self.assertEqual(f.assessment(n)['G2']['status'], 'pass')

    def test_interruption_fresh_p02_and_explicit_unchanged_reuse_are_scoped(self):
        s = f.resume_interview(upgrade(), resume_id='upgrade-interruption')
        old = deepcopy(s['facts']['Q-P02'])
        historical = fact(s, 'Q-P02', old['value'], source=old['source'], observed_at=old['observed_at'])
        self.assertIn('Q-P02', historical['resume_review']['retained_keys'])
        fresh = fact(s, 'Q-P02', old['value'], source='synthetic:current-order', observed_at=LATER, current_reply=True)
        self.assertNotIn('Q-P02', fresh['resume_review']['retained_keys'])
        unchanged = f.record_resume_review(s, resume_id='upgrade-interruption', response='unchanged',
                                          source='synthetic:current-review', reported_at=LATER)
        self.assertEqual(unchanged['facts']['Q-P02'], old)
        n = f.begin_task(unchanged, task_id='later-upgrade', task='upgrade')
        n = fact(n, 'Q-C08', 'next-target', observed_at=LATER, current_reply=True)
        self.assertEqual(f.assessment(n)['G2']['status'], 'pass')
        old_refund = fact(first(), 'Q-J01', 'returning_subscription', observed_at=NOW, current_reply=True)
        old_refund = f.set_context(old_refund, task='billing_issue')
        old_refund = fact(old_refund, 'Q-P02', {**ORDER, 'status': 'expired', 'pending_issue': 'pending_refund'},
                          observed_at=NOW, current_reply=True)
        old_refund = f.resume_interview(old_refund, resume_id='refund-interruption')
        self.assertNotIn('Q-P02', old_refund['resume_review']['retained_keys'])
        self.assertNotIn('Q-P02', old_refund['resume_review']['scope_keys'])

    def test_report_replacement_cannot_lose_later_retained_detail(self):
        s = pending()
        s = f.report_subscription_conflict(s, source='synthetic:next-page', observed_at=NOW, current_reply=True)
        s = fact(s, 'Q-P02', CONFLICT, observed_at=LATER, current_reply=True)
        s = fact(s, 'Q-P02', CONFLICT, observed_at=NOW, current_reply=True, correction=True)
        before = deepcopy(s)
        with self.assertRaises(f.InterviewError):
            f.report_subscription_conflict(s, source='synthetic:late-imported-page',
                                           observed_at='2026-10-18T10:30:00+00:00', current_reply=True)
        self.assertEqual(s, before)
        n = f.report_subscription_conflict(s, source='synthetic:truly-new-page',
                                           observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        with self.assertRaises(f.InterviewError):
            f.resolve_subscription_conflict(n, **resolution(n, observed_at=LATER))

    def test_historical_completion_does_not_stale_later_current_p02_reply(self):
        s = upgrade()
        s = fact(s, 'Q-P02', {**ORDER, 'plan': 'new-current-plan'}, observed_at=LATER, current_reply=True)
        before = deepcopy(s)
        r = f.complete_purchase(s, source='synthetic:older-completion', observed_at='2026-10-18T10:30:00+00:00')
        self.assertEqual(r, before)
        self.assertEqual(f.assessment(r)['G2']['status'], 'pass')
        self.assertIsNone(f.next_question(r))

    def test_scoped_plan_reply_keeps_old_channel_with_its_own_provenance(self):
        s = f.complete_purchase(upgrade(), source='synthetic:completion', observed_at=LATER)
        s = f.begin_task(s, task_id='later-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'next-target', observed_at=LATER, current_reply=True)
        old = deepcopy(s['facts']['Q-P02'])
        s = f.mark_asked(s, 'Q-P02')
        s = fact(s, 'Q-P02', {'plan': 'actual-current-B'}, source='synthetic:new-plan-only',
                 observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        self.assertEqual(s['facts']['Q-P02']['value'], {'plan': 'actual-current-B'})
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], [])
        origin = s['facts']['Q-P02']['retained_fields']['billing_channel']
        self.assertEqual(origin['value'], 'web')
        for key in ['source', 'observed_at', 'subject_ref', 'state']:
            self.assertEqual(origin[key], old[key])
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], [])
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)
        replay = fact(s, 'Q-P02', s['facts']['Q-P02']['value'], source='synthetic:new-plan-only',
                      observed_at='2026-10-18T12:00:00+00:00')
        self.assertEqual(replay, s)
        self.assertEqual(f.assessment(s)['G3']['status'], 'blocked')
        self.assertFalse(any(s['persistence_consent'].values()))
        self.assertEqual(s['purchase_completion']['source'], 'synthetic:completion')

    def test_scoped_channel_reply_keeps_current_plan_original_age(self):
        s = upgrade(billing_channel=None)
        old = deepcopy(s['facts']['Q-P02'])
        s = f.mark_asked(s, 'Q-P02')
        s = fact(s, 'Q-P02', {'billing_channel': 'apple'}, observed_at=LATER, current_reply=True)
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], [])
        self.assertEqual(s['facts']['Q-P02']['retained_fields']['plan']['observed_at'], old['observed_at'])
        s = f.complete_purchase(s, source='synthetic:completion-after-old-plan',
                                observed_at='2026-10-18T10:30:00+00:00')
        s = f.begin_task(s, task_id='next-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'new-target', observed_at=LATER, current_reply=True)
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
        self.assertNotIn('购买渠道', f.next_question(s)['prompt'])
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')

    def test_scoped_conflict_relation_reply_preserves_status_but_never_resolves(self):
        s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
        s = fact(s, 'Q-P02', {'status': 'active'}, source='synthetic:status-only', observed_at=NOW, current_reply=True)
        s = f.mark_asked(s, 'Q-P02')
        s = fact(s, 'Q-P02', {'page_relation': 'same_target'}, source='synthetic:relation-only', observed_at=LATER, current_reply=True)
        self.assertEqual(f.assessment(s)['G1']['status'], 'complete')
        self.assertEqual(s['facts']['Q-P02']['retained_fields']['status']['source'], 'synthetic:status-only')
        self.assertEqual(s['facts']['Q-P02']['retained_fields']['status']['observed_at'], NOW)
        self.assertEqual(f.assessment(s)['G1']['status'], 'complete')
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        self.assertIsNone(f.next_question(s))
        n = f.report_subscription_conflict(s, source='synthetic:new-report',
                                           observed_at='2026-10-18T10:30:00+00:00', current_reply=True)
        n = fact(n, 'Q-P02', {'page_relation': 'same_target'}, observed_at=LATER, current_reply=True)
        self.assertNotIn('retained_fields', n['facts']['Q-P02'])
        self.assertIn('状态', f.next_question(n)['prompt'])
        self.assertEqual(f.assessment(n)['G1']['status'], 'partial')
        self.assertEqual(f.assessment(n)['G2']['status'], 'blocked')

    def test_only_actual_gap_answers_reuse_fields_imports_corrections_and_replacements_do_not(self):
        for options in [{'current_reply': False}, {'current_reply': True, 'correction': True}]:
            s = upgrade(billing_channel=None)
            s = fact(s, 'Q-P02', {'billing_channel': 'apple'}, observed_at=LATER, **options)
            self.assertNotIn('retained_fields', s['facts']['Q-P02'])
            self.assertIn('current_plan', f.assessment(s)['upgrade_scope']['current_order_gaps'])
        s = fact(upgrade(), 'Q-P02', {'plan': 'replacement-plan'}, observed_at=LATER, current_reply=True)
        self.assertNotIn('retained_fields', s['facts']['Q-P02'])
        self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_channel'])
        s = f.complete_purchase(upgrade(), source='synthetic:completion', observed_at=LATER)
        s = f.begin_task(s, task_id='next-upgrade', task='upgrade')
        s = fact(s, 'Q-P02', {'billing_channel': 'apple'}, observed_at=LATER, current_reply=True)
        self.assertNotIn('retained_fields', s['facts']['Q-P02'])
        self.assertIn('current_plan', f.assessment(s)['upgrade_scope']['current_order_gaps'])

    def test_malformed_or_cross_account_retained_fields_are_rejected_atomically(self):
        s = fact(upgrade(billing_channel=None), 'Q-P02', {'billing_channel': 'apple'},
                 observed_at=LATER, current_reply=True)
        before = deepcopy(s)
        for key, value in [('source', ''), ('source', True), ('state', []), ('state', 'stale'),
                           ('subject_ref', 'another-account'), ('value', 'selected_unspecified'),
                           ('observed_at', '2026-10-18T12:00:00+00:00'), ('unexpected', True)]:
            bad = deepcopy(s)
            bad['facts']['Q-P02']['retained_fields']['plan'][key] = value
            with self.subTest(key=key), self.assertRaises(f.InterviewError):
                f.loads_state(json.dumps(bad))
            self.assertEqual(s, before)
        for replacement in [{}, None, [], {'bad': s['facts']['Q-P02']['retained_fields']['plan']}]:
            bad = deepcopy(s)
            bad['facts']['Q-P02']['retained_fields'] = replacement
            with self.assertRaises(f.InterviewError):
                f.loads_state(json.dumps(bad))
        other = f.begin_task(s, task_id='other-account', task='upgrade', account_alias='another-account')
        self.assertNotIn('Q-P02', other['facts'])

    def test_legacy_explicit_stale_c13_invalidates_alternate_plan_without_completion(self):
        for status in ['stale', 'conflict']:
            s = fact(upgrade(), 'Q-C13', 'old-plan', observed_at=NOW, current_reply=True)
            # Historical schema-1 envelope from before the P02 component marker.
            s['facts']['Q-C13'].update(state=status, blocker_reason='current plan changed')
            self.assertNotIn('current_order_plan_stale', s['context'])
            self.assertNotIn('purchase_completion', s)
            self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
            loaded = f.loads_state(json.dumps(s))
            self.assertTrue(loaded['context']['current_order_plan_stale'])
            imported = fact(loaded, 'Q-P02', ORDER, observed_at=LATER)
            self.assertEqual(f.assessment(imported)['G2']['status'], 'blocked')
            fresh = fact(loaded, 'Q-P02', {'plan': 'actual-current-plan'}, observed_at=LATER, current_reply=True)
            self.assertFalse(fresh['context']['current_order_plan_stale'])
            self.assertEqual(f.assessment(fresh)['G2']['status'], 'pass')
            fresh = f.loads_state(f.dumps_state(fresh, host_opt_in=True))
            fresh = f.begin_task(fresh, task_id='same-account-device', task='upgrade', target_alias='second-device')
            fresh = fact(fresh, 'Q-C08', 'new-target', observed_at=LATER, current_reply=True)
            self.assertEqual(f.assessment(fresh)['G2']['status'], 'pass')
            fresh = f.invalidate_facts(fresh, ['Q-C13'], reason='actual later current-plan change')
            self.assertEqual(f.assessment(fresh)['G2']['status'], 'blocked')
        ordinary = upgrade()
        self.assertNotIn('current_order_plan_stale', f.loads_state(json.dumps(ordinary))['context'])
        self.assertEqual(f.assessment(ordinary)['G2']['status'], 'pass')

    def test_discharged_p02_resume_obligation_does_not_reappear_on_new_task(self):
        s = f.resume_interview(upgrade(), resume_id='interruption')
        s = fact(s, 'Q-J01', 'existing_subscriber', observed_at=LATER, current_reply=True)
        s = fact(s, 'Q-P02', {**ORDER, 'plan': 'actually-current'}, observed_at=LATER, current_reply=True)
        self.assertEqual(s['resume_review']['retained_keys'], [])
        self.assertIn('Q-P02', s['resume_review']['scope_keys'])
        old = deepcopy(s['facts']['Q-P02'])
        for target in [s['target_alias'], 'second-device']:
            n = f.begin_task(s, task_id='next-upgrade', task='upgrade', target_alias=target)
            n = fact(n, 'Q-C08', 'new-target', observed_at=LATER, current_reply=True)
            self.assertEqual(n['facts']['Q-P02'], old)
            self.assertEqual(f.assessment(n)['upgrade_scope']['current_order_gaps'], [])
            self.assertEqual(f.assessment(n)['G2']['status'], 'pass')



    def check_terminal_gap(self, missing, retained, expected_gap):
        for terminal in ['unknown', 'declined', 'deferred']:
            with self.subTest(terminal=terminal):
                initial = upgrade(**{missing: None})
                self.assertEqual(f.next_question(initial)['id'], 'Q-P02')
                initial = f.mark_asked(initial, 'Q-P02')
                original = deepcopy(initial)
                old = initial['facts']['Q-P02']
                reply = fact(initial, 'Q-P02', None, state_name=terminal,
                             source='synthetic:terminal-gap', observed_at=LATER, current_reply=True)
                self.assertEqual(initial, original)
                self.assertEqual(f.assessment(reply)['upgrade_scope']['current_order_gaps'], [expected_gap])
                terminal_fact = reply['facts']['Q-P02']
                self.assertIsNone(terminal_fact['value'])
                self.assertEqual(terminal_fact['state'], terminal)
                self.assertEqual(terminal_fact['source'], 'synthetic:terminal-gap')
                self.assertEqual(terminal_fact['observed_at'], LATER)
                self.assertEqual(terminal_fact['clarification_count'], 1)
                origin = terminal_fact['retained_fields'][retained]
                self.assertEqual(origin, {**{key: old[key] for key in ['state', 'source', 'subject_ref', 'observed_at']},
                                          'value': old['value'][retained]})
                self.assertIsNone(f.next_question(reply))
                self.assertEqual(f.assessment(reply)['G2']['status'], 'blocked')
                self.no_authority(reply)
                self.assertEqual(f.loads_state(f.dumps_state(reply, host_opt_in=True)), reply)
                repeat = fact(reply, 'Q-P02', None, state_name=terminal,
                              source='synthetic:terminal-gap', observed_at=LATER, current_reply=True)
                self.assertEqual(repeat, reply)
                # A later volunteered genuine answer can fill just that gap.
                value = {'plan': 'new-current'} if missing == 'plan' else {'billing_channel': 'apple'}
                answered = fact(reply, 'Q-P02', value, observed_at=LATER, current_reply=True)
                self.assertEqual(f.assessment(answered)['upgrade_scope']['current_order_gaps'], [])
                self.assertEqual(answered['facts']['Q-P02']['retained_fields'][retained], origin)
                self.assertEqual(f.assessment(answered)['G2']['status'], 'pass')
                self.no_authority(answered)

    def test_terminal_scoped_plan_gap_retains_channel(self):
        self.check_terminal_gap('plan', 'billing_channel', 'current_plan')

    def test_terminal_scoped_channel_gap_retains_plan(self):
        self.check_terminal_gap('billing_channel', 'plan', 'current_channel')

    def test_terminal_retention_is_not_generic_or_historical_merging(self):
        cases = [(upgrade(), {}), (upgrade(plan=None, billing_channel=None), {}),
                 (upgrade(plan=None), {'current_reply': False}),
                 (upgrade(plan=None), {'correction': True})]
        for state, options in cases:
            reply = fact(state, 'Q-P02', None, state_name='declined', observed_at=LATER,
                         **{'current_reply': True, **options})
            self.assertNotIn('retained_fields', reply['facts']['Q-P02'])
        other = fact(upgrade(), 'Q-A06', None, state_name='declined', current_reply=True)
        self.assertNotIn('retained_fields', other['facts']['Q-A06'])

    def test_terminal_retention_does_not_revive_stale_plan_or_cross_account(self):
        s = f.invalidate_facts(upgrade(billing_channel=None), ['Q-C13'], reason='current plan changed')
        n = fact(s, 'Q-P02', None, state_name='unknown', observed_at=LATER, current_reply=True)
        self.assertNotIn('retained_fields', n['facts']['Q-P02'])
        self.assertEqual(f.assessment(n)['upgrade_scope']['current_order_gaps'], ['current_plan', 'current_channel'])
        s = fact(upgrade(billing_channel=None), 'Q-P02', None, state_name='declined', observed_at=LATER, current_reply=True)
        changed = f.begin_task(s, task_id='other', task='upgrade', account_alias='different-account')
        self.assertNotIn('Q-P02', changed['facts'])
        original = deepcopy(s)
        with self.assertRaises(f.InterviewError):
            fact(s, 'Q-P02', None, state_name='declined', subject_ref='different-account', observed_at=LATER, current_reply=True)
        self.assertEqual(s, original)

    def test_terminal_retained_history_can_stale_without_new_episode_reuse(self):
        s = fact(upgrade(plan=None), 'Q-P02', None, state_name='declined', observed_at=LATER, current_reply=True)
        stale = f.invalidate_facts(s, ['Q-P02'], reason='new order evidence')
        self.assertIsNone(stale['facts']['Q-P02']['value'])
        self.assertEqual(stale['facts']['Q-P02']['retained_fields'], s['facts']['Q-P02']['retained_fields'])
        self.assertEqual(stale['facts']['Q-P02']['state'], 'stale')
        self.assertEqual(f.assessment(stale)['upgrade_scope']['current_order_gaps'], ['current_plan', 'current_channel'])
        newer = f.report_subscription_conflict(s, source='synthetic:new-page',
                    observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        self.assertEqual(newer['subscription_review']['original']['Q-P02'], s['facts']['Q-P02'])
        self.assertEqual(newer['facts']['Q-P02']['state'], 'stale')
        self.assertIn('当前订阅状态', f.next_question(newer)['prompt'])
        self.assertEqual(f.assessment(newer)['G2']['status'], 'blocked')
        self.assertEqual(f.loads_state(f.dumps_state(newer, host_opt_in=True)), newer)

    def test_same_episode_terminal_detail_retains_only_current_complement(self):
        s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
        s = fact(s, 'Q-P02', {'status': 'active'}, observed_at=NOW, current_reply=True)
        s = fact(s, 'Q-P02', None, state_name='deferred', observed_at=LATER, current_reply=True)
        self.assertEqual(s['facts']['Q-P02']['retained_fields']['status']['observed_at'], NOW)
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        newer = f.report_subscription_conflict(s, source='synthetic:new-page',
                    observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
        newer = fact(newer, 'Q-P02', {'page_relation': 'same_target'},
                    observed_at='2026-10-18T13:00:00+00:00', current_reply=True)
        self.assertNotIn('retained_fields', newer['facts']['Q-P02'])
        self.assertIn('当前订阅状态', f.next_question(newer)['prompt'])
        self.assertEqual(f.assessment(newer)['G2']['status'], 'blocked')


    def test_terminal_retained_plan_still_requires_actual_interruption_review(self):
        for when in ['before_interruption', 'during_interruption']:
            with self.subTest(when=when):
                s = upgrade(billing_channel=None)
                if when == 'before_interruption':
                    s = fact(s, 'Q-P02', None, state_name='declined', observed_at=NOW, current_reply=True)
                s = f.resume_interview(s, resume_id='terminal-gap-interruption')
                self.assertIn('Q-P02', s['resume_review']['retained_keys'])
                if when == 'during_interruption':
                    s = fact(s, 'Q-P02', None, state_name='declined', observed_at=NOW, current_reply=True)
                self.assertIn('Q-P02', s['resume_review']['retained_keys'])
                s = f.record_resume_review(s, resume_id='terminal-gap-interruption', response='unknown', source='synthetic:resume')
                s = fact(s, 'Q-P02', {'billing_channel': 'apple'}, observed_at=LATER, current_reply=True)
                self.assertIn('Q-P02', s['resume_review']['retained_keys'])
                s = f.begin_task(s, task_id='new-upgrade', task='upgrade')
                s = fact(s, 'Q-C08', 'new-target')
                self.assertEqual(f.assessment(s)['upgrade_scope']['current_order_gaps'], ['current_plan'])
                self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
                self.assertIn('当前套餐', f.next_question(s)['prompt'])
                self.no_authority(s)


class UpgradeConflictCliTests(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.directory = Path(self.temp.name)

    def write(self, name, value):
        path = self.directory / name
        path.write_text(json.dumps(value, ensure_ascii=False), encoding='utf-8')
        return str(path)

    def cli(self, *args, expected=0):
        run = subprocess.run([sys.executable, '-B', str(SCRIPTS / 'interview_cli.py'), *args],
                             capture_output=True, text=True, encoding='utf-8', timeout=30,
                             env={**os.environ, 'PYTHONIOENCODING': 'cp1252:strict'})
        self.assertEqual(run.returncode, expected, run.stdout + run.stderr)
        self.assertEqual(run.stderr, '')
        result = json.loads(run.stdout)
        self.assertFalse(result['action_executed'])
        return result

    def test_original_t77_cli_complete_upgrade_does_not_ask_os(self):
        with patch.object(f, '_now', return_value=NOW):
            s = upgrade()
        answers = {'answers': [{'question_id': key, 'value': s['facts'][key]['value']}
                               for key in ['Q-J01', 'Q-C11', 'Q-C08', 'Q-P02']]}
        result = self.cli('--answer-file', self.write('answer.json', answers),
                          '--target-ref', 'fixture-device', '--account-ref', 'fixture-account')
        self.assertIsNone(result['question'])
        self.assertEqual(result['assessment']['G2']['status'], 'pass')
        self.assertFalse(result['saved'])

    def test_original_t80_cli_legacy_true_covered_conflict_stays_blocked(self):
        s = first()
        s['context']['subscription_conflict'] = True
        s = fact(s, 'Q-P02', CONFLICT, observed_at=PAGE)
        result = self.cli('--input', self.write('legacy.json', s))
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')
        self.assertFalse(result['saved'])
        self.assertIsNone(result['question'])

    def test_cli_resolution_roundtrip_utf8_private_state_and_idempotence(self):
        s = pending()
        args = resolution(s, source='synthetic:当前答复')
        output = self.directory / 'resolved.json'
        result = self.cli('--input', self.write('pending.json', s),
                          '--subscription-resolution-file', self.write('resolution.json', args), '--output', str(output))
        self.assertTrue(result['saved'])
        self.assertEqual(result['assessment']['G2']['status'], 'pass')
        self.assertEqual(result['assessment']['current_subscription']['source'], 'private-source-retained')
        state = f.loads_state(output.read_text(encoding='utf-8'))
        self.assertEqual(state['subscription_review']['resolution']['source'], 'synthetic:当前答复')
        second = self.directory / 'retry.json'
        self.cli('--input', str(output), '--subscription-resolution-file', str(self.directory / 'resolution.json'), '--output', str(second))
        self.assertEqual(output.read_bytes(), second.read_bytes())

    def test_cli_invalid_resolution_and_boolean_clear_never_save_or_mutate(self):
        s = pending()
        source = self.write('pending.json', s)
        before = Path(source).read_bytes()
        target = self.directory / 'forbidden.json'
        self.cli('--input', source, '--subscription-resolution-file', self.write('wrong.json', resolution(s, account_ref='wrong-account')),
                 '--output', str(target), expected=2)
        self.assertFalse(target.exists())
        self.cli('--input', source, '--context-file', self.write('clear.json', {'subscription_conflict': False}),
                 '--output', str(target), expected=2)
        self.assertFalse(target.exists())
        self.assertEqual(Path(source).read_bytes(), before)

    def test_cli_partial_p02_reply_consumes_only_one_clarification(self):
        with patch.object(f, '_now', return_value=NOW):
            s = upgrade(plan=None)
        output = self.directory / 'partial.json'
        result = self.cli('--input', self.write('partial-source.json', s), '--answer-file',
                          self.write('partial-answer.json', {'question_id': 'Q-P02', 'value': {'billing_channel': 'web'}}),
                          '--output', str(output))
        self.assertIsNone(result['question'])
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')
        saved = f.loads_state(output.read_text(encoding='utf-8'))
        self.assertEqual(saved['facts']['Q-P02']['clarification_count'], 1)
        result = self.cli('--input', str(output))
        self.assertIsNone(result['question'])

    def test_cli_report_conflict_requires_current_provenance_and_emits_only_gap(self):
        output = self.directory / 'pending.json'
        result = self.cli('--input', self.write('first.json', first()), '--subscription-conflict-file',
                          self.write('page.json', {'source': 'synthetic:页面', 'observed_at': PAGE, 'current_reply': True}),
                          '--output', str(output))
        self.assertEqual(result['question']['id'], 'Q-P02')
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')
        state = f.loads_state(output.read_text(encoding='utf-8'))
        self.assertEqual(state['subscription_review']['source'], 'synthetic:页面')
        self.assertEqual(state['subscription_review']['original']['Q-J01']['observed_at'], OLD)


    def test_cli_newer_pending_report_blocks_old_resolution_without_save(self):
        s = pending()
        output = self.directory / 'newer.json'
        result = self.cli('--input', self.write('pending.json', s), '--subscription-conflict-file',
                          self.write('latest.json', {'source': 'synthetic:新的页面', 'observed_at': LATER,
                                                   'current_reply': True}), '--output', str(output))
        self.assertEqual(result['question']['id'], 'Q-P02')
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')
        current = f.loads_state(output.read_text(encoding='utf-8'))
        self.assertEqual(current['subscription_review']['original'], s['subscription_review']['original'])
        self.assertEqual(current['subscription_review']['latest_report']['observed_at'], LATER)
        before = output.read_bytes()
        target = self.directory / 'must-not-save.json'
        self.cli('--input', str(output), '--subscription-resolution-file',
                 self.write('older-resolution.json', resolution(s)), '--output', str(target), expected=2)
        self.assertFalse(target.exists())
        self.assertEqual(output.read_bytes(), before)
        retried = self.directory / 'retry-latest.json'
        self.cli('--input', str(output), '--subscription-conflict-file', str(self.directory / 'latest.json'),
                 '--output', str(retried))
        self.assertEqual(retried.read_bytes(), before)

    def test_cli_conflict_prompt_and_minimal_status_relation_coverage_match(self):
        s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
        source = self.write('pending.json', s)
        result = self.cli('--input', source, '--answer-file', self.write('channel-only.json',
                          {'question_id': 'Q-P02', 'value': {'billing_channel': 'apple'}}))
        self.assertEqual(result['question']['id'], 'Q-P02')
        self.assertIn('订阅状态', result['question']['prompt'])
        self.assertIn('目标账号', result['question']['prompt'])
        result = self.cli('--input', source, '--answer-file', self.write('status-relation.json',
                          {'question_id': 'Q-P02', 'value': {'status': 'active', 'page_relation': 'same_target'}}))
        self.assertIsNone(result['question'])
        self.assertEqual(result['assessment']['G1']['status'], 'complete')
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')

    def test_cli_postcompletion_upgrade_keeps_channel_and_asks_only_current_plan(self):
        with patch.object(f, '_now', return_value=NOW):
            s = f.complete_purchase(upgrade(), source='synthetic:reported-completion', observed_at=LATER)
        s = f.begin_task(s, task_id='later-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'target-C', observed_at=LATER, current_reply=True)
        result = self.cli('--input', self.write('completed.json', s))
        self.assertEqual(result['assessment']['upgrade_scope']['current_order_gaps'], ['current_plan'])
        self.assertEqual(result['question']['id'], 'Q-P02')
        self.assertIn('当前套餐', result['question']['prompt'])
        self.assertNotIn('购买渠道', result['question']['prompt'])
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')


    def test_cli_scoped_plan_answer_preserves_private_older_channel_provenance(self):
        with patch.object(f, '_now', return_value=NOW):
            s = f.complete_purchase(upgrade(), source='synthetic:completion', observed_at=LATER)
        s = f.begin_task(s, task_id='later-upgrade', task='upgrade')
        s = fact(s, 'Q-C08', 'target-C', observed_at=LATER, current_reply=True)
        old = deepcopy(s['facts']['Q-P02'])
        output = self.directory / 'refreshed.json'
        result = self.cli('--input', self.write('partial.json', s), '--answer-file',
                          self.write('plan-only.json', {'question_id': 'Q-P02', 'value': {'plan': '当前套餐B'}}),
                          '--output', str(output))
        self.assertEqual(result['assessment']['upgrade_scope']['current_order_gaps'], [])
        self.assertEqual(result['assessment']['G2']['status'], 'pass')
        self.assertIsNone(result['question'])
        saved = f.loads_state(output.read_text(encoding='utf-8'))
        origin = saved['facts']['Q-P02']['retained_fields']['billing_channel']
        self.assertEqual(origin['source'], old['source'])
        self.assertEqual(origin['observed_at'], old['observed_at'])
        self.assertNotIn(origin['source'], json.dumps(result))

    def test_cli_legacy_stale_c13_keeps_only_current_plan_gap(self):
        with patch.object(f, '_now', return_value=NOW):
            s = fact(upgrade(), 'Q-C13', 'old-current', observed_at=NOW, current_reply=True)
        s['facts']['Q-C13'].update(state='stale', blocker_reason='actual plan change')
        source = self.write('legacy-stale.json', s)
        before = Path(source).read_bytes()
        result = self.cli('--input', source)
        self.assertEqual(result['assessment']['upgrade_scope']['current_order_gaps'], ['current_plan'])
        self.assertEqual(result['assessment']['G2']['status'], 'blocked')
        self.assertNotIn('购买渠道', result['question']['prompt'])
        self.assertEqual(Path(source).read_bytes(), before)


    def check_cli_terminal_gap(self, missing, retained, expected_gap):
        for terminal in ['unknown', 'declined', 'deferred']:
            with self.subTest(terminal=terminal):
                with patch.object(f, '_now', return_value=NOW):
                    initial = upgrade(**{missing: None})
                source = self.write('terminal-initial.json', initial)
                original_bytes = Path(source).read_bytes()
                output = self.directory / ('terminal-' + terminal + '-output.json')
                answer = self.write('terminal-answer.json', {'question_id': 'Q-P02', 'value': None, 'state': terminal})
                result = self.cli('--input', source, '--answer-file', answer, '--output', str(output))
                self.assertEqual(result['assessment']['upgrade_scope']['current_order_gaps'], [expected_gap])
                self.assertEqual(result['assessment']['G2']['status'], 'blocked')
                self.assertEqual(result['assessment']['G3']['status'], 'blocked')
                self.assertIsNone(result['question'])
                saved = f.loads_state(output.read_text(encoding='utf-8'))
                self.assertIsNone(saved['facts']['Q-P02']['value'])
                self.assertEqual(saved['facts']['Q-P02']['state'], terminal)
                origin = saved['facts']['Q-P02']['retained_fields'][retained]
                old = initial['facts']['Q-P02']
                self.assertEqual(origin, {**{key: old[key] for key in ['state', 'source', 'subject_ref', 'observed_at']},
                                          'value': old['value'][retained]})
                self.assertEqual(Path(source).read_bytes(), original_bytes)
                result = self.cli('--input', str(output))
                self.assertEqual(result['assessment']['upgrade_scope']['current_order_gaps'], [expected_gap])
                self.assertIsNone(result['question'])
                self.assertFalse(result['saved'])

    def test_cli_terminal_plan_gap_retains_original_channel(self):
        self.check_cli_terminal_gap('plan', 'billing_channel', 'current_plan')

    def test_cli_terminal_channel_gap_retains_original_plan(self):
        self.check_cli_terminal_gap('billing_channel', 'plan', 'current_channel')


class UpgradeConflictSchemaTests(unittest.TestCase):
    def test_retained_field_schema_is_p02_only_typed_and_closed_without_optional_validator(self):
        schema = f.STATE_SCHEMA['properties']['facts']['properties']['Q-P02']
        self.assertIn('retained_fields', schema['properties'])
        self.assertFalse(f.FACT_SCHEMA['additionalProperties'])
        self.assertNotIn('retained_fields', f.FACT_SCHEMA['properties'])
        for qid, ordinary in f.STATE_SCHEMA['properties']['facts']['properties'].items():
            self.assertFalse(ordinary['additionalProperties'])
            if qid != 'Q-P02':
                self.assertNotIn('retained_fields', ordinary['properties'])
        retained = schema['properties']['retained_fields']
        self.assertFalse(retained['additionalProperties'])
        self.assertEqual((retained['minProperties'], retained['maxProperties']), (1, 1))
        self.assertEqual(set(retained['properties']), {'plan', 'billing_channel', 'status', 'page_relation'})
        for origin in retained['properties'].values():
            self.assertFalse(origin['additionalProperties'])
            self.assertEqual(set(origin['required']), {'value', 'state', 'source', 'subject_ref', 'observed_at'})
            self.assertEqual(origin['properties']['state'], {'enum': ['reported', 'observed']})
            self.assertEqual(origin['properties']['source'], {'type': 'string', 'minLength': 1})
        guard = schema['allOf'][0]
        self.assertEqual(guard['if'], {'required': ['retained_fields']})
        self.assertEqual(guard['then']['anyOf'], [
            {'properties': {'value': {'type': 'object'}, 'state': {'enum': ['reported', 'observed', 'stale', 'conflict']}}},
            {'properties': {'value': {'type': 'null'}, 'state': {'enum': ['unknown', 'declined', 'deferred']}}},
            {'properties': {'value': {'type': 'null'}, 'state': {'enum': ['stale', 'conflict']}}}])
        shadow_guards = guard['then']['allOf']
        self.assertEqual(len(shadow_guards), 4)
        for item in shadow_guards:
            key = item['if']['properties']['retained_fields']['required']
            self.assertEqual(item['then']['properties']['value'], {'not': {'type': 'object', 'required': key}})
        review = f.STATE_SCHEMA['properties']['subscription_review']['properties']
        self.assertEqual(review['original']['properties']['Q-P02'], schema)
        self.assertEqual(review['detail']['anyOf'], [schema, {'type': 'null'}])
        self.assertEqual(review['latest_report']['properties']['detail']['anyOf'], [schema, {'type': 'null'}])

    def schema_states(self):
        with patch.object(f, '_now', return_value=NOW):
            plan = fact(upgrade(plan=None), 'Q-P02', {'plan': 'new-current'}, observed_at=LATER, current_reply=True)
            channel = fact(upgrade(billing_channel=None), 'Q-P02', {'billing_channel': 'apple'}, observed_at=LATER, current_reply=True)
            samples = [('plan', plan), ('channel', channel), ('empty', f.new_state('device', 'account'))]
            for first_field, second_field in [('status', 'page_relation'), ('page_relation', 'status')]:
                values = {'status': 'active', 'page_relation': 'same_target'}
                s = f.report_subscription_conflict(first(), source='synthetic:page', observed_at=PAGE, current_reply=True)
                s = fact(s, 'Q-P02', {first_field: values[first_field]}, observed_at=NOW, current_reply=True)
                s = fact(s, 'Q-P02', {second_field: values[second_field]}, observed_at=LATER, current_reply=True)
                samples.append((first_field, s))
            archived = f.report_subscription_conflict(channel, source='synthetic:new-page', observed_at='2026-10-18T12:00:00+00:00', current_reply=True)
            samples.append(('original-snapshot', archived))
            detail = f.report_subscription_conflict(samples[3][1], source='synthetic:later-page', observed_at=NOW, current_reply=True)
            samples.append(('latest-detail-snapshot', detail))
            initial_detail = deepcopy(detail)
            initial_detail['subscription_review']['detail'] = deepcopy(detail['subscription_review']['latest_report']['detail'])
            samples.append(('initial-detail-snapshot', initial_detail))
            samples.append(('legacy-text', fact(first(), 'Q-P02', 'legacy old-order description')))
            return samples

    @unittest.skipUnless(jsonschema is not None, 'Optional jsonschema validator unavailable; structural schema assertions still run')
    def test_actual_draft202012_validator_accepts_public_states_and_snapshots(self):
        jsonschema.Draft202012Validator.check_schema(f.STATE_SCHEMA)
        validator = jsonschema.Draft202012Validator(f.STATE_SCHEMA)
        for name, s in self.schema_states():
            with self.subTest(name=name):
                f.validate_state(s)
                self.assertEqual(list(validator.iter_errors(s)), [])
                loaded = f.loads_state(f.dumps_state(s, host_opt_in=True))
                self.assertEqual(list(validator.iter_errors(loaded)), [])

    @unittest.skipUnless(jsonschema is not None, 'Optional jsonschema validator unavailable; structural schema assertions still run')
    def test_actual_draft202012_validator_rejects_malformed_retained_fields(self):
        s = self.schema_states()[0][1]
        validator = jsonschema.Draft202012Validator(f.STATE_SCHEMA)
        variants = []
        for field, value in [('retained_fields', {}), ('retained_fields', None), ('state', 'unknown'), ('value', 'text')]:
            bad = deepcopy(s)
            bad['facts']['Q-P02'][field] = value
            variants.append(bad)
        for key, value in [('value', 'unknown-channel'), ('state', 'stale'), ('source', ''), ('source', True),
                           ('subject_ref', 1), ('observed_at', 1), ('unexpected', True)]:
            bad = deepcopy(s)
            bad['facts']['Q-P02']['retained_fields']['billing_channel'][key] = value
            variants.append(bad)
        bad = deepcopy(s)
        bad['facts']['Q-P02']['value']['billing_channel'] = 'web'
        variants.append(bad)
        bad = deepcopy(s)
        bad['facts']['Q-P02']['retained_fields']['status'] = {**bad['facts']['Q-P02']['retained_fields']['billing_channel'], 'value': 'active'}
        variants.append(bad)
        bad = deepcopy(s)
        bad['facts']['Q-P02']['retained_fields']['unsupported'] = bad['facts']['Q-P02']['retained_fields'].pop('billing_channel')
        variants.append(bad)
        for name, value in [('plan', 'selected_unspecified'), ('plan', '   '), ('status', 'invalid'), ('page_relation', 'invalid')]:
            bad = deepcopy(s)
            old = bad['facts']['Q-P02']['retained_fields'].pop('billing_channel')
            bad['facts']['Q-P02']['value'] = {'billing_channel': 'apple'}
            bad['facts']['Q-P02']['retained_fields'][name] = {**old, 'value': value}
            variants.append(bad)
        for index, bad in enumerate(variants):
            with self.subTest(index=index):
                self.assertTrue(list(validator.iter_errors(bad)))
                with self.assertRaises(f.InterviewError):
                    f.validate_state(bad)

    @unittest.skipUnless(jsonschema is not None, 'Optional jsonschema validator unavailable; structural schema assertions still run')
    def test_actual_validator_keeps_generic_facts_and_snapshot_fields_closed(self):
        s = self.schema_states()[0][1]
        validator = jsonschema.Draft202012Validator(f.STATE_SCHEMA)
        for qid in ['Q-A06', 'Q-C13', 'Q-J01']:
            bad = deepcopy(s)
            bad['facts'][qid] = deepcopy(bad['facts']['Q-P02'])
            self.assertTrue(list(validator.iter_errors(bad)))
        for name, s in self.schema_states():
            if 'snapshot' not in name:
                continue
            bad = deepcopy(s)
            review = bad['subscription_review']
            snapshot = (review['original']['Q-P02'] if name == 'original-snapshot' else
                        review['latest_report']['detail'] if name == 'latest-detail-snapshot' else review['detail'])
            snapshot['retained_fields']['unknown'] = {'value': 'invalid'}
            self.assertTrue(list(validator.iter_errors(bad)))
            with self.assertRaises(f.InterviewError):
                f.validate_state(bad)


    @unittest.skipUnless(jsonschema is not None, 'Optional jsonschema validator unavailable; structural schema assertions still run')
    def test_actual_validator_accepts_terminal_and_inactive_retained_history(self):
        validator = jsonschema.Draft202012Validator(f.STATE_SCHEMA)
        with patch.object(f, '_now', return_value=NOW):
            for missing in ['plan', 'billing_channel']:
                for terminal in ['unknown', 'declined', 'deferred']:
                    s = fact(upgrade(**{missing: None}), 'Q-P02', None, state_name=terminal,
                             observed_at=LATER, current_reply=True)
                    self.assertIn('retained_fields', s['facts']['Q-P02'])
                    variants = [s, f.invalidate_facts(s, ['Q-P02'], reason='new order'),
                                f.report_subscription_conflict(s, source='synthetic:new-page',
                                    observed_at='2026-10-18T12:00:00+00:00', current_reply=True)]
                    for item in variants:
                        with self.subTest(missing=missing, terminal=terminal, state=item['facts']['Q-P02']['state']):
                            f.validate_state(item)
                            self.assertEqual(list(validator.iter_errors(item)), [])
                            self.assertEqual(f.loads_state(f.dumps_state(item, host_opt_in=True)), item)
                            self.assertEqual(f.assessment(item)['G2']['status'], 'blocked')

    @unittest.skipUnless(jsonschema is not None, 'Optional jsonschema validator unavailable; structural schema assertions still run')
    def test_actual_validator_rejects_malformed_terminal_retention(self):
        validator = jsonschema.Draft202012Validator(f.STATE_SCHEMA)
        with patch.object(f, '_now', return_value=NOW):
            s = fact(upgrade(plan=None), 'Q-P02', None, state_name='declined', observed_at=LATER, current_reply=True)
        variants = []
        for key, value in [('value', {}), ('value', 'text'), ('value', False),
                           ('state', 'reported'), ('state', 'observed'), ('state', 'unasked'), ('state', 'inferred'),
                           ('retained_fields', {}), ('retained_fields', [])]:
            bad = deepcopy(s); bad['facts']['Q-P02'][key] = value; variants.append(bad)
        for key, value in [('source', ''), ('state', 'unknown'), ('value', 'invalid'), ('unexpected', True)]:
            bad = deepcopy(s); bad['facts']['Q-P02']['retained_fields']['billing_channel'][key] = value; variants.append(bad)
        bad = deepcopy(s)
        bad['facts']['Q-A06'] = bad['facts'].pop('Q-P02')
        variants.append(bad)
        for index, bad in enumerate(variants):
            with self.subTest(index=index):
                self.assertTrue(list(validator.iter_errors(bad)))
                with self.assertRaises(f.InterviewError):
                    f.validate_state(bad)


if __name__ == '__main__':
    unittest.main()
