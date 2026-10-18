"""Selected-device cleanup intent is offline planning, never action consent."""
import importlib.util
import json
import itertools
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('device_cleanup_interview', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def initial():
    return f.new_state('device-a', 'account-a')


def answer(s, q, v, **kwargs):
    return f.record_fact(s, q, v, source='user:explicit', **kwargs)


class DeviceCleanupTests(unittest.TestCase):
    def test_past_account_restriction_asks_selected_device_without_inference(self):
        s = answer(initial(), 'Q-C03', 'past_suspension')
        self.assertEqual(f.next_question(s)['id'], 'Q-D01')
        self.assertNotIn('Q-D01', s['facts'])
        self.assertNotIn('cleanup', f.assessment(s))
        s = answer(s, 'Q-D01', 'other_device_only')
        self.assertNotIn('Q-D02', [x['id'] for x in f.applicable_questions(s)])
        self.assertNotIn('Q-D01', [x['id'] for x in f.applicable_questions(s)])

    def test_atomic_route_and_device_answers_are_order_independent(self):
        values = [('Q-C05', 'vm'), ('Q-D01', 'past_restriction_on_target'), ('Q-D02', 'full_claude_data_reset')]
        for order in itertools.permutations(values):
            with self.subTest(order=order):
                s = f.record_facts(initial(), [{'question_id': q, 'value': v} for q, v in order], source='user:batch')
                self.assertEqual(s['facts']['Q-D01']['state'], 'reported')
                self.assertEqual(s['facts']['Q-D02']['state'], 'reported')
                self.assertEqual(f.assessment(s)['cleanup']['requested_level'], 'C5-full-claude-data-reset')

    def test_new_device_episode_refreshes_triage_without_relabeling_account(self):
        s = answer(answer(initial(), 'Q-H01', 'prior episode'), 'Q-C04', 'active')
        s = answer(s, 'Q-D01', 'current_restriction_on_target')
        self.assertEqual(s['facts']['Q-C04']['state'], 'reported')
        self.assertEqual(s['facts']['Q-C04']['value'], 'active')
        self.assertEqual(f.next_question(s)['id'], 'Q-H01')
        self.assertTrue(f.next_question(s)['clarification'])
        s = answer(s, 'Q-H01', 'another account on this device')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        s = answer(s, 'Q-D01', 'past_restriction_on_target')
        self.assertNotEqual(f.next_question(s)['id'], 'Q-H01')

    def test_current_device_episode_preempts_pending_resume(self):
        s = f.resume_interview(answer(initial(), 'Q-D02', 'full_claude_data_reset'), resume_id='event')
        s = answer(s, 'Q-D01', 'current_restriction_on_target')
        self.assertEqual(f.next_question(s)['id'], 'Q-H01')
        self.assertIsNone(f.resume_review_prompt(s))

    def test_task_switch_and_no_cleanup_stop_obsolete_goal_questions(self):
        s = answer(initial(), 'Q-D02', 'full_claude_data_reset')
        for changed in (answer(s, 'Q-C11', 'network'), f.set_context(s, task='network')):
            self.assertNotIn('Q-D02', changed['facts'])
            self.assertFalse(any(x['branch'] == 'cleanup' for x in f.applicable_questions(changed)))
        s = f.begin_task(initial(), task_id='cleanup', task='cleanup')
        s = answer(s, 'Q-D02', 'no_cleanup')
        self.assertIsNone(f.next_question(s))
        self.assertEqual(f.applicable_questions(s), [])

    def test_device_triage_resolution_preserves_truth_and_reopens_only_fresh_episode(self):
        s = answer(initial(), 'Q-C04', 'active')
        s = answer(s, 'Q-D01', 'current_restriction_on_target', observed_at='2026-10-18T01:00:00Z')
        s = answer(s, 'Q-H01', 'other account still restricted')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        s = f.set_context(s, device_incident_resolved=True)
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'scope_inventory')
        self.assertFalse(f.assessment(s)['cleanup']['action_authorized'])
        self.assertEqual(s['facts']['Q-D01']['value'], 'current_restriction_on_target')
        self.assertEqual(s['facts']['Q-C04']['value'], 'active')
        self.assertNotEqual(f.assessment(s)['cleanup']['next_step'], 'incident_triage')
        replay = answer(s, 'Q-D01', 'current_restriction_on_target', observed_at='2026-10-18T01:00:00Z')
        self.assertTrue(replay['context']['device_incident_resolved'])
        fresh = answer(s, 'Q-D01', 'current_restriction_on_target')
        self.assertFalse(fresh['context']['device_incident_resolved'])
        self.assertEqual(f.next_question(fresh)['id'], 'Q-H01')
        self.assertNotIn('device_incident_resolved', initial()['context'])

    def test_resumed_cleanup_cancellation_suppresses_prompt_but_retains_review(self):
        s = f.begin_task(initial(), task_id='cleanup', task='cleanup')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        s = f.resume_interview(s, resume_id='resume-a')
        s = answer(s, 'Q-D02', 'no_cleanup')
        self.assertIsNone(f.next_question(s))
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'none')
        self.assertIn('resume_review', s)
        self.assertEqual(f.assessment(s)['G3']['status'], 'blocked')

    def test_resolution_is_bound_and_cannot_resolve_account_or_credential_incident(self):
        s = answer(initial(), 'Q-D01', 'current_restriction_on_target')
        s = f.set_context(s, device_incident_resolved=True)
        for changed in (f.set_context(s, route='vm', route_selection_basis='explicit_choice'),
                        f.invalidate_facts(s, ['Q-D01'], reason='new evidence')):
            self.assertFalse(changed['context']['device_incident_resolved'])
        for incident in ('credential_exposure', 'data_risk'):
            urgent = f.set_context(s, incident=incident)
            self.assertEqual(f.assessment(urgent)['G1']['status'], 'emergency_deferred')
        account = answer(s, 'Q-C04', 'current_suspension')
        self.assertTrue(f._urgent_incident(account))
        for value in ([], 'true', 1):
            with self.assertRaises(f.InterviewError):
                f.set_context(s, device_incident_resolved=value)
        corrupted = json.loads(json.dumps(s))
        corrupted['facts']['Q-D01']['source'] = 'user:different-evidence'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(corrupted))
        self.assertEqual(f.loads_state(json.dumps(initial()))['facts'], {})

    def test_same_evidence_replay_preserves_resolution_despite_optional_metadata(self):
        s = answer(initial(), 'Q-D01', 'current_restriction_on_target', observed_at='2026-10-18T01:00:00Z', blocker_reason='old note')
        s = answer(s, 'Q-H01', 'other account')
        s = answer(s, 'Q-C04', 'active')
        s = f.set_context(s, device_incident_resolved=True)
        replay = answer(s, 'Q-D01', 'current_restriction_on_target', observed_at='2026-10-18T01:00:00Z')
        self.assertEqual(replay, s)
        self.assertTrue(replay['context']['device_incident_resolved'])

    def test_task_change_retains_resolved_episode_but_dismisses_old_cleanup_offer(self):
        s = answer(initial(), 'Q-D01', 'current_restriction_on_target')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        s = f.set_context(s, device_incident_resolved=True)
        for changed in (f.set_context(s, task='network'), f.begin_task(s, task_id='new', task='network')):
            self.assertTrue(changed['context']['device_incident_resolved'])
            self.assertNotIn('Q-D02', changed['facts'])
        past = answer(initial(), 'Q-D01', 'past_restriction_on_target')
        past = answer(past, 'Q-D02', 'full_claude_data_reset')
        changed = answer(past, 'Q-C11', 'network')
        self.assertEqual(changed['facts']['Q-D01']['value'], 'past_restriction_on_target')
        self.assertNotIn('Q-D02', [x['id'] for x in f.applicable_questions(changed)])
        self.assertEqual(f.assessment(changed)['cleanup']['trigger'], 'none')
        fresh = answer(changed, 'Q-D01', 'past_restriction_on_target')
        self.assertIn('Q-D02', [x['id'] for x in f.applicable_questions(fresh)])
        explicit = answer(changed, 'Q-D02', 'full_claude_data_reset')
        self.assertEqual(f.assessment(explicit)['cleanup']['requested_level'], 'C5-full-claude-data-reset')

    def test_generated_episode_refs_never_look_like_card_data(self):
        cases = [('past_restriction_on_target', '2026-10-18T01:00:00.000012+00:00', {'task': 'network'}, 'cleanup_offer_dismissed_ref'),
                 ('current_restriction_on_target', '2026-10-18T01:00:00.000031+00:00', {'device_incident_resolved': True}, 'device_incident_resolution_ref')]
        for category, timestamp, change, key in cases:
            with self.subTest(category=category):
                s = answer(initial(), 'Q-D01', category, observed_at=timestamp)
                changed = f.set_context(s, **change)
                reference = changed['context'][key]
                self.assertRegex(reference, r'^[0-9a-f]{8}(?:\.[0-9a-f]{8}){7}$')
                self.assertEqual(f.loads_state(json.dumps(changed))['context'][key], reference)
                corrupted = json.loads(json.dumps(changed))
                corrupted['context'][key] = 'a' * 64
                with self.assertRaises(f.InterviewError):
                    f.loads_state(json.dumps(corrupted))
        for value in ('1234567890123456', '1234-5678-9012-3456', 'password=synthetic-value'):
            with self.assertRaises(f.InterviewError):
                answer(initial(), 'Q-H03', value)

    def test_target_history_does_not_follow_account(self):
        s = answer(initial(), 'Q-C03', 'past_suspension')
        self.assertNotIn('cleanup', f.assessment(s))
        s = answer(s, 'Q-D01', 'past_restriction_on_target')
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'select_cleanup_goal')
        s = f.begin_task(s, task_id='next', task='environment', target_alias='device-b')
        self.assertNotIn('Q-D01', s['facts'])
        self.assertNotIn('cleanup', f.assessment(s))

    def test_full_reset_independent_of_every_history(self):
        for history in [None, 'past_restriction_on_target', 'ordinary_error_only', 'other_device_only', 'none_reported']:
            with self.subTest(history=history):
                s = initial()
                if history:
                    s = answer(s, 'Q-D01', history)
                s = answer(s, 'Q-D02', 'full_claude_data_reset')
                a = f.assessment(s)
                self.assertEqual(a['cleanup']['requested_level'], 'C5-full-claude-data-reset')
                self.assertFalse(a['cleanup']['action_authorized'])
                self.assertEqual(a['cleanup']['execution_status'], 'not_run')
                ids = [x['id'] for x in f.applicable_questions(s)]
                self.assertNotIn('Q-J01', ids)
                self.assertNotIn('Q-D01', ids)
                self.assertIn('Q-C12', ids)
                self.assertIn('Q-Z04', ids)
                self.assertNotIn('Q-J01', [x['id'] for x in a['G1']['unresolved_fields']])
                self.assertEqual(a['G3']['status'], 'blocked')

    def test_typed_validation_and_load(self):
        for q in ('Q-D01', 'Q-D02'):
            for value in ('unsupported', [], {}, True):
                with self.subTest(q=q, value=value), self.assertRaises(f.InterviewError):
                    answer(initial(), q, value)
            s = answer(initial(), q, 'none_reported' if q == 'Q-D01' else 'audit_only')
            s['facts'][q]['value'] = ['bad']
            with self.assertRaises(f.InterviewError):
                f.loads_state(json.dumps(s))
            with self.assertRaises(f.InterviewError):
                answer(initial(), q, 'none_reported' if q == 'Q-D01' else 'audit_only', subject_ref='device-b')
            with self.assertRaises(f.InterviewError):
                answer(initial(), q, 'none_reported' if q == 'Q-D01' else 'audit_only', state_name='inferred')

    def test_nonpositive_history_never_offers_cleanup(self):
        for value in ('ordinary_error_only', 'other_device_only', 'none_reported'):
            a = f.assessment(answer(initial(), 'Q-D01', value))
            self.assertEqual(a['cleanup']['trigger'], 'none')
            self.assertEqual(a['cleanup']['requested_level'], 'unselected')
        for status in ('unknown', 'declined', 'stale', 'conflict'):
            value = None if status in ('unknown', 'declined') else 'past_restriction_on_target'
            s = answer(initial(), 'Q-D01', value, state_name=status)
            self.assertEqual(f.assessment(s)['cleanup']['trigger'], 'none')

    def test_current_device_event_not_current_account_incident(self):
        s = answer(initial(), 'Q-D01', 'current_restriction_on_target')
        self.assertEqual(f._account_incident(s), 'none')
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'incident_triage')
        self.assertIn('Q-H01', [x['id'] for x in f.applicable_questions(s)])

    def test_urgent_incident_precedes_explicit_reset(self):
        s = answer(initial(), 'Q-D02', 'full_claude_data_reset')
        s = f.set_context(s, incident='credential_exposure')
        self.assertEqual(f.next_question(s)['id'], 'Q-H01')
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'incident_triage')
        self.assertEqual(f.assessment(s)['G1']['status'], 'emergency_deferred')

    def test_task_account_and_route_changes(self):
        s = answer(answer(initial(), 'Q-D01', 'past_restriction_on_target'), 'Q-D02', 'full_claude_data_reset')
        same = f.begin_task(s, task_id='next', task='environment')
        self.assertIn('Q-D01', same['facts'])
        self.assertNotIn('Q-D02', same['facts'])
        other = f.begin_task(s, task_id='next', task='environment', account_alias='account-b')
        self.assertNotIn('Q-D01', other['facts'])
        for changed in (f.set_context(s, route='vm', route_selection_basis='explicit_choice'), answer(s, 'Q-C05', 'vm')):
            self.assertEqual(changed['facts']['Q-D01']['state'], 'stale')
            self.assertEqual(changed['facts']['Q-D02']['state'], 'stale')
            self.assertNotEqual(f.assessment(changed)['cleanup']['requested_level'], 'C5-full-claude-data-reset')

    def test_cleanup_task_minimal_and_intent_choices(self):
        s = f.begin_task(initial(), task_id='clean', task='cleanup')
        self.assertEqual(s['payment_intent'], 'none')
        self.assertIn('Q-D02', [x['id'] for x in f.applicable_questions(s)])
        for value, level in [('audit_only', 'C0-audit'), ('no_cleanup', 'unselected'), ('other_scope', 'unselected')]:
            a = f.assessment(answer(s, 'Q-D02', value))['cleanup']
            self.assertEqual(a['requested_level'], level)
            self.assertFalse(a['action_authorized'])

    def test_resume_and_serialization(self):
        s = answer(initial(), 'Q-D02', 'full_claude_data_reset')
        loaded = f.loads_state(json.dumps(s))
        self.assertNotIn('resume_review', loaded)
        resumed = f.resume_interview(s, resume_id='resume-a')
        self.assertIn('Q-D02', resumed['resume_review']['scope_keys'])
        self.assertEqual(f.assessment(resumed)['cleanup']['next_step'], 'resume_review')
        reviewed = f.record_resume_review(resumed, resume_id='resume-a', response='unchanged', source='user:now')
        self.assertFalse(f.assessment(reviewed)['cleanup']['action_authorized'])

    def test_old_evidence_cannot_freshen_stale_goal(self):
        s = answer(initial(), 'Q-D02', 'full_claude_data_reset', observed_at='2026-10-18T01:00:00+00:00')
        s = f.invalidate_facts(s, ['Q-D02'], reason='changed_scope')
        replay = answer(s, 'Q-D02', 'full_claude_data_reset', observed_at='2026-10-18T01:00:00+00:00')
        self.assertEqual(replay['facts']['Q-D02']['state'], 'stale')
        self.assertEqual(f.assessment(replay)['cleanup']['requested_level'], 'unselected')
        fresh = answer(s, 'Q-D02', 'full_claude_data_reset', observed_at='2026-10-18T02:00:00+00:00')
        self.assertEqual(f.assessment(fresh)['cleanup']['requested_level'], 'C5-full-claude-data-reset')

    def test_selected_target_question_and_defer_are_bounded(self):
        s = f.record_fact(initial(), 'Q-D01', state_name='unasked')
        q = f.next_question(s)
        self.assertEqual(q['id'], 'Q-D01')
        self.assertIn('device-a', q['prompt'])
        s = f.record_fact(s, 'Q-D01', state_name='declined')
        self.assertNotEqual(f.next_question(s)['id'], 'Q-D01')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        s = f.defer_branch(s, 'cleanup')
        self.assertEqual(f.assessment(s)['cleanup']['next_step'], 'deferred')
        self.assertIsNone(f.next_question(s))

    def test_changed_resume_and_invalid_serialized_binding(self):
        s = answer(initial(), 'Q-D01', 'past_restriction_on_target')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        r = f.resume_interview(s, resume_id='resume-a')
        self.assertIn('清理目标', f.resume_review_prompt(r)['prompt'])
        r = f.record_resume_review(r, resume_id='resume-a', response='changed', changed_keys=['Q-D02'], source='user:now')
        self.assertEqual(f.assessment(r)['cleanup']['requested_level'], 'unselected')
        s['target_alias'] = 'device-b'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(s))

    def test_current_device_history_blocks_personalized_cleanup(self):
        s = answer(initial(), 'Q-D01', 'current_restriction_on_target')
        s = answer(s, 'Q-D02', 'full_claude_data_reset')
        self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
        self.assertEqual(f.assessment(s)['G2']['reason'], 'device_cleanup_incident_triage_required')

    def test_unrelated_routes_and_context_not_history(self):
        s = initial()
        self.assertNotIn('cleanup', f.assessment(s))
        self.assertFalse(any(x['id'].startswith('Q-D') for x in f.applicable_questions(s)))
        s = answer(s, 'Q-H08', 'same_device')
        self.assertNotIn('cleanup', f.assessment(s))
        s = answer(s, 'Q-J01', 'first_subscription')
        self.assertNotIn('Q-D01', s['facts'])


if __name__ == '__main__':
    unittest.main()
