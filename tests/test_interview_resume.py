"""T24 scoped session-resume review; offline state/CLI tests, no device claims."""
from copy import deepcopy
import importlib.util
import json
import io
import subprocess
import sys
import tempfile
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('resume_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
FIXTURE = json.loads((ROOT / 'tests/fixtures/acceptance-routes-rebuild.json').read_text(encoding='utf-8'))
OLD_TIME = '2026-10-18T04:00:00Z'
REVIEW_TIME = '2026-10-18T04:30:00Z'


def ready(route='vm'):
    s = f.set_context(f.new_state('route-device', 'route-account', task_id='route-task'), task='environment')
    with patch.object(f, '_now', return_value=OLD_TIME):
        s = f.record_facts(s, FIXTURE['common_answers'], source='synthetic:original')
        s = f.record_fact(s, 'Q-C05', route, source='synthetic:original')
        s = f.record_facts(s, FIXTURE['route_answers'][route], source='synthetic:original')
    return s


def reviewed(s, response='unchanged', **kwargs):
    return f.record_resume_review(s, resume_id='resume-a', response=response,
                                  source='synthetic:current-reply', reported_at=REVIEW_TIME, **kwargs)


class ResumeReviewTests(unittest.TestCase):
    def test_plain_load_and_ordinary_roundtrip_do_not_start_resume(self):
        for route in ('vm', 'vps'):
            s = ready(route)
            self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)
            self.assertNotIn('resume_review', s)
            self.assertIsNone(f.resume_review_prompt(s))
            self.assertEqual(f.assessment(s)['G2'], {'status': 'pass', 'conditional_plan_only': False})

    def test_actual_resume_retains_choice_facts_history_and_blocks_personalized_plan(self):
        for route in ('vm', 'vps'):
            with self.subTest(route=route):
                s = f.set_context(ready(route), paused=True, contact_phase='PC2')
                before = deepcopy(s)
                resumed = f.resume_interview(s, resume_id='resume-a')
                self.assertEqual(s, before)
                self.assertEqual(resumed['facts'], s['facts'])
                self.assertEqual(resumed['context']['route'], route)
                self.assertEqual(resumed['context']['route_selection_basis'], 'explicit_choice')
                self.assertEqual(resumed['context']['contact_phase'], 'PC2')
                self.assertFalse(resumed['context']['paused'])
                self.assertEqual(resumed['task_id'], 'route-task')
                self.assertIsNone(f.next_question(resumed))
                self.assertEqual(f.assessment(resumed)['G1']['status'], 'complete')
                self.assertEqual(f.assessment(resumed)['G2'], {'status': 'blocked', 'conditional_plan_only': True,
                                                              'reason': 'resume_review_required'})
                self.assertEqual(f.assessment(resumed)['G3']['status'], 'blocked')
                prompt = f.resume_review_prompt(resumed)
                self.assertEqual(prompt['kind'], 'resume_review')
                self.assertEqual(prompt['event_id'], 'resume-a')
                self.assertEqual(prompt['allowed_outcomes'], ['unchanged', 'changed', 'unknown', 'declined', 'deferred', 'target_changed'])
                self.assertFalse(prompt['requires_action_authorization'])
                self.assertNotIn('Q-C05', prompt['scope_keys'])
                self.assertNotIn('Q-C10', prompt['scope_keys'])
                self.assertNotIn('Q-C12', prompt['scope_keys'])
                self.assertNotIn('Q-Z01', prompt['scope_keys'])
                self.assertNotIn('Q-J01', prompt['scope_keys'])  # Environment task, not billing.
                self.assertFalse(any(resumed['persistence_consent'].values()))

    def test_unconfirmed_default_remains_a_proposal_during_resume(self):
        s = f.set_context(f.new_state('route-device', 'route-account', task_id='route-task'), task='environment')
        s = f.record_facts(s, FIXTURE['common_answers'], source='synthetic:original')
        s = f.resume_interview(s, resume_id='resume-a')
        self.assertEqual(s['context']['route_selection_basis'], 'default_proposal')
        self.assertIn('路线尚未确认（本机只是默认候选）', f.resume_review_prompt(s)['prompt'])
        self.assertEqual(f.assessment(s)['route_confirmation'], 'unconfirmed')
        s = reviewed(s)
        self.assertEqual(f.next_question(s)['id'], 'Q-C05')
        self.assertEqual(f.assessment(s)['route_confirmation'], 'unconfirmed')

    def test_true_unpause_cannot_skip_explicit_review(self):
        s = f.set_context(ready(), paused=True)
        with self.assertRaisesRegex(f.InterviewError, 'Use resume_interview'):
            f.set_context(s, paused=False)
        self.assertTrue(s['context']['paused'])

    def test_unchanged_is_fresh_report_not_new_observations_or_permission(self):
        old = ready()
        s = reviewed(f.resume_interview(old, resume_id='resume-a'))
        self.assertEqual(s['facts'], old['facts'])
        self.assertEqual(s['resume_review']['reported_at'], REVIEW_TIME)
        self.assertEqual(s['resume_review']['source'], 'synthetic:current-reply')
        self.assertEqual(s['resume_review']['status'], 'reviewed')
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['G2'], {'status': 'pass', 'conditional_plan_only': False})
        self.assertEqual(f.assessment(s)['G3']['status'], 'blocked')
        self.assertNotIn('source', f.assessment(s)['resume_review'])

    def test_changed_vm_network_or_vps_ssh_invalidates_only_reported_subset(self):
        for route, qid in (('vm', 'Q-V04'), ('vps', 'Q-S03')):
            old = ready(route)
            pending = f.resume_interview(old, resume_id='resume-a')
            changed = reviewed(pending, 'changed', changed_keys=[qid])
            self.assertEqual(changed['facts'][qid]['state'], 'stale')
            self.assertEqual(changed['facts'][qid]['value'], old['facts'][qid]['value'])
            self.assertEqual(changed['facts'][qid]['observed_at'], OLD_TIME)
            self.assertEqual({k: v for k, v in changed['facts'].items() if k != qid},
                             {k: v for k, v in old['facts'].items() if k != qid})
            self.assertEqual(f.next_question(changed)['id'], qid)
            self.assertTrue(f.next_question(changed)['clarification'])
            self.assertEqual(f.assessment(changed)['G2']['status'], 'blocked')
            self.assertIsNone(f.resume_review_prompt(changed))

    def test_unknown_refused_deferred_target_change_do_not_repeat_prompt(self):
        for response in ('unknown', 'declined', 'deferred', 'target_changed'):
            old = ready()
            s = reviewed(f.resume_interview(old, resume_id='resume-a'), response)
            for _ in range(3):
                s = f.loads_state(f.dumps_state(s, host_opt_in=True))
                s = f.resume_interview(s, resume_id='resume-a')
                self.assertIsNone(f.resume_review_prompt(s))
                self.assertEqual(s['facts'], old['facts'])
                self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')
                self.assertTrue(f.assessment(s)['G2']['conditional_plan_only'])
            if response != 'target_changed':
                # A new explicit reply may resolve uncertainty without an automatic loop.
                self.assertEqual(reviewed(s)['resume_review']['status'], 'reviewed')

    def test_idempotent_event_and_answer_retries_do_not_restale_refreshed_facts(self):
        pending = f.resume_interview(ready(), resume_id='resume-a')
        self.assertEqual(f.resume_interview(pending, resume_id='resume-a'), pending)
        s = reviewed(pending, 'changed', changed_keys=['Q-V04'])
        s = f.record_fact(s, 'Q-V04', 'new_network_report', source='synthetic:refresh', observed_at=REVIEW_TIME)
        self.assertEqual(reviewed(s, 'changed', changed_keys=['Q-V04']), s)
        self.assertEqual(f.resume_interview(s, resume_id='resume-a'), s)
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(f.resume_interview(s, resume_id='resume-b')['resume_review']['status'], 'pending')
        with self.assertRaises(f.InterviewError):
            f.resume_interview(f.set_context(s, paused=True), resume_id='resume-a')
        with self.assertRaises(f.InterviewError):
            reviewed(s, 'unchanged')

    def test_review_scope_cannot_transfer_to_another_task_target_account_or_route(self):
        s = reviewed(f.resume_interview(ready(), resume_id='resume-a'))
        for key in ('task_id', 'target_alias', 'account_alias'):
            bad = deepcopy(s); bad[key] = 'different'
            with self.assertRaises(f.InterviewError):
                f.validate_state(bad)
        for args in ({'task_id': 'new-task', 'task': 'environment'},
                     {'task_id': 'new-task', 'task': 'environment', 'target_alias': 'other-device'},
                     {'task_id': 'new-task', 'task': 'environment', 'account_alias': 'other-account'}):
            self.assertNotIn('resume_review', f.begin_task(s, **args))
        switched = f.record_fact(s, 'Q-C05', 'vps', source='synthetic:explicit-switch', observed_at=REVIEW_TIME)
        self.assertEqual(switched['context']['route'], 'vps')
        self.assertEqual(switched['resume_review']['status'], 'pending')
        self.assertFalse(any(q.startswith('Q-V') for q in switched['resume_review']['scope_keys']))
        self.assertEqual(f.assessment(switched)['G2']['status'], 'blocked')

    def test_invalid_reply_is_atomic_and_does_not_echo_provenance(self):
        s = f.resume_interview(ready(), resume_id='resume-a'); original = deepcopy(s)
        for args in ({'changed_keys': []}, {'changed_keys': ['Q-C05']}, {'changed_keys': ['Q-V04', 'Q-V04']},
                     {'changed_keys': 'Q-V04'}, {'changed_keys': [None]}, {'changed_keys': ['Q-C07']},
                     {'changed_keys': ['Q-OS01']}, {'changed_keys': ['Q-S03']}):
            with self.subTest(args=args), self.assertRaises(f.InterviewError):
                reviewed(s, 'changed', **args)
            self.assertEqual(s, original)
        with self.assertRaises(f.InterviewError):
            f.record_resume_review(s, resume_id='wrong', response='unchanged', source='user')
        with self.assertRaises(f.InterviewError):
            f.record_resume_review(s, resume_id='resume-a', response='unchanged', source='', reported_at=REVIEW_TIME)
        with self.assertRaises(f.InterviewError):
            f.record_resume_review(s, resume_id='resume-a', response='unchanged', source='user', reported_at='bad')
        with self.assertRaises(f.InterviewError):
            f.record_resume_review(s, resume_id='resume-a', response='unchanged', source='token=private-sentinel')
        self.assertEqual(s, original)

    def test_emergency_triage_precedes_review_without_losing_environment_scope(self):
        s = f.record_fact(ready(), 'Q-C04', 'suspended', source='synthetic:incident', observed_at=REVIEW_TIME)
        s = f.resume_interview(s, resume_id='resume-a')
        self.assertIn('Q-V04', s['resume_review']['scope_keys'])
        self.assertEqual(f.next_question(s)['id'], 'Q-H01')
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['G1']['status'], 'emergency_deferred')
        resolved = f.set_context(s, incident_resolved=True)
        self.assertIsNotNone(f.resume_review_prompt(resolved))
        self.assertIsNone(f.next_question(resolved))

    def test_empty_retained_scope_skips_prompt_and_same_event_retry_stays_noop(self):
        original = f.new_state('device', 'account')
        s = f.resume_interview(original, resume_id='resume-a')
        self.assertEqual(s['resume_review']['status'], 'not_required')
        self.assertEqual(s['resume_review']['scope_keys'], [])
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.next_question(s), f.next_question(original))
        self.assertEqual(f.assessment(s)['G2'], f.assessment(original)['G2'])
        s = f.record_fact(s, 'Q-C02', 'macos', source='synthetic:fresh', observed_at=REVIEW_TIME)
        self.assertEqual(f.resume_interview(s, resume_id='resume-a'), s)
        self.assertIsNone(f.resume_review_prompt(s))

    def test_empty_event_fresh_route_choice_is_not_another_interruption(self):
        s = f.resume_interview(f.set_context(f.new_state('route-device', 'route-account'), task='environment'),
                               resume_id='resume-a')
        s = f.record_facts(s, FIXTURE['common_answers'], source='synthetic:fresh')
        s = f.record_fact(s, 'Q-C05', 'vm', source='synthetic:fresh')
        s = f.record_facts(s, FIXTURE['route_answers']['vm'], source='synthetic:fresh')
        self.assertEqual(s['resume_review']['status'], 'not_required')
        self.assertEqual(s['resume_review']['retained_keys'], [])
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        with self.assertRaises(f.InterviewError):
            f.resume_interview(f.set_context(s, paused=True), resume_id='resume-a')
        self.assertEqual(f.resume_interview(f.set_context(s, paused=True), resume_id='resume-b')
                         ['resume_review']['status'], 'pending')

    def test_old_off_route_fact_requires_review_but_new_report_does_not(self):
        for fresh in (False, True):
            s = f.set_context(f.new_state('device', 'account'), task='environment')
            s = f.record_fact(s, 'Q-V04', 'old_network', source='synthetic:old', observed_at=OLD_TIME)
            s = f.resume_interview(s, resume_id='resume-a')
            self.assertEqual(s['resume_review']['status'], 'not_required')
            self.assertEqual(s['resume_review']['scope_keys'], [])
            self.assertEqual(s['resume_review']['retained_keys'], ['Q-V04'])
            if fresh:
                with patch.object(f, '_now', return_value=REVIEW_TIME):
                    s = f.record_fact(s, 'Q-V04', 'new_network', source='synthetic:current')
            else:
                # Same old provenance/time is still retained, including after load/render.
                before = deepcopy(s['resume_review'])
                s = f.loads_state(f.dumps_state(s, host_opt_in=True))
                f.resume_review_prompt(s); f.assessment(s)
                s = f.record_fact(s, 'Q-V04', 'old_network', source='synthetic:old', observed_at=OLD_TIME)
                self.assertEqual(s['resume_review'], before)
            s = f.record_fact(s, 'Q-C05', 'vm', source='synthetic:current', observed_at=REVIEW_TIME)
            self.assertEqual(s['resume_review']['status'], 'not_required' if fresh else 'pending')
            self.assertEqual(s['resume_review']['scope_keys'], [] if fresh else ['Q-V04'])

    def test_newer_historical_import_is_not_a_current_reply_boundary(self):
        s = f.set_context(f.new_state('device', 'account'), task='environment')
        s = f.record_fact(s, 'Q-V04', 'old_network', source='synthetic:oct-1-log',
                          observed_at='2026-10-01T00:00:00Z')
        s = f.resume_interview(s, resume_id='resume-a')
        s = f.record_fact(s, 'Q-V04', 'other_old_network', source='synthetic:oct-2-log',
                          observed_at='2026-10-02T00:00:00Z')
        self.assertEqual(s['resume_review']['retained_keys'], ['Q-V04'])
        s = f.record_fact(s, 'Q-C05', 'vm', source='synthetic:current')
        self.assertEqual(s['resume_review']['status'], 'pending')
        self.assertEqual(s['resume_review']['scope_keys'], ['Q-V04'])
        self.assertEqual(s['facts']['Q-V04']['observed_at'], '2026-10-02T00:00:00Z')

    def test_retained_key_metadata_is_validated_atomically(self):
        original = f.resume_interview(ready(), resume_id='resume-a')
        for keys in (['Q-C07'], ['Q-C05'], ['Q-V04', 'Q-V04'], ['Q-V04', None], 'Q-V04'):
            candidate = deepcopy(original)
            candidate['resume_review']['retained_keys'] = keys
            with self.assertRaises(f.InterviewError):
                f.validate_state(candidate)
            self.assertEqual(original['resume_review']['status'], 'pending')

    def test_purchase_cannot_clear_known_target_change_when_environment_scope_empty(self):
        s = f.set_context(f.new_state('device', 'account'), task='renew')
        s = f.record_fact(s, 'Q-J01', 'existing_subscriber', source='synthetic:old', observed_at=OLD_TIME)
        s = reviewed(f.resume_interview(s, resume_id='resume-a'), 'target_changed')
        s = f.complete_purchase(s, source='synthetic:purchase', observed_at=REVIEW_TIME)
        self.assertEqual(s['resume_review']['scope_keys'], [])
        self.assertEqual(s['resume_review']['response'], 'target_changed')
        self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_target_rebind_required')
        s = f.record_fact(s, 'Q-C05', 'vm', source='synthetic:fresh')
        self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_target_rebind_required')

    def test_dormant_retained_conditionals_cannot_escape_review_on_activation(self):
        for route, qid, changes in (
                ('vm', 'Q-N05', {'existing_test': True}),
                ('local', 'Q-L02', {'compatibility_needed': True}),
                ('local', 'Q-L03', {'integration_used': True}),
                ('vm', 'Q-OS09', {'os_issue': 'app_language'}),
                ('vm', 'Q-Z04', {'change_planned': True})):
            with self.subTest(qid=qid):
                s = ready('vm')
                if route == 'local':
                    s = f.record_fact(s, 'Q-C05', 'local', source='synthetic:route', observed_at=OLD_TIME)
                    for key in ('Q-L01', 'Q-L04'):
                        s = f.record_fact(s, key, 'reported', source='synthetic:old', observed_at=OLD_TIME)
                s = f.record_fact(s, qid, 'retained_conditional', source='synthetic:old', observed_at=OLD_TIME)
                s = f.resume_interview(s, resume_id='resume-a')
                self.assertIn(qid, s['resume_review']['scope_keys'])
                prompt = f.resume_review_prompt(s)
                self.assertIn('含本路线已记录但尚未展开的条件项', prompt['prompt'])
                s = f.set_context(s, **changes)
                self.assertIn(qid, s['resume_review']['scope_keys'])
                self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_review_required')
                s = reviewed(s, 'changed', changed_keys=[qid])
                self.assertEqual(s['facts'][qid]['state'], 'stale')
                self.assertEqual(f.assessment(s)['G2']['status'], 'blocked')

    def test_fresh_conditional_answer_does_not_force_redundant_review(self):
        s = reviewed(f.resume_interview(ready(), resume_id='resume-a'))
        s = f.record_fact(s, 'Q-N05', 'new_current_test_report', source='synthetic:fresh', observed_at=REVIEW_TIME)
        s = f.set_context(s, existing_test=True)
        self.assertNotIn('Q-N05', s['resume_review']['scope_keys'])
        self.assertEqual(s['resume_review']['status'], 'reviewed')
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')

    def test_region_change_is_reviewable_without_detailed_address(self):
        s = f.resume_interview(ready(), resume_id='resume-a')
        self.assertIn('Q-C09', s['resume_review']['scope_keys'])
        self.assertIn('无需详细地址', f.resume_review_prompt(s)['prompt'])
        s = reviewed(s, 'changed', changed_keys=['Q-C09'])
        self.assertEqual(s['facts']['Q-C09']['state'], 'stale')
        self.assertEqual(f.next_question(s)['id'], 'Q-C09')

    def test_completed_purchase_retires_review_without_inventing_interruption(self):
        for outcome in ('unchanged', 'unknown', None):
            s = f.set_context(ready(), task='renew')
            s = f.resume_interview(s, resume_id='resume-a')
            if outcome is not None:
                s = reviewed(s, outcome)
            done = f.complete_purchase(s, source='synthetic:purchase', observed_at=REVIEW_TIME)
            self.assertEqual(done['context']['task'], 'environment')
            self.assertEqual(done['context']['route'], 'vm')
            self.assertEqual(done['current_subscription']['status'], 'active_reported')
            if outcome == 'unchanged':
                self.assertNotIn('resume_review', done)
                self.assertEqual(f.assessment(done)['G2']['status'], 'pass')
            else:
                self.assertEqual(done['resume_review']['status'], 'unresolved' if outcome == 'unknown' else 'pending')
                self.assertNotIn('Q-J01', done['resume_review']['scope_keys'])
                self.assertEqual(f.assessment(done)['G2']['status'], 'blocked')

    def test_purchase_keeps_unreviewed_off_route_obligation_without_current_route_gate(self):
        s = f.set_context(ready(), task='renew')
        s = f.record_fact(s, 'Q-S03', 'old_ssh', source='synthetic:old', observed_at=OLD_TIME)
        s = reviewed(f.resume_interview(s, resume_id='resume-a'))
        receipt = deepcopy(s['resume_review'])
        s = f.complete_purchase(s, source='synthetic:purchase', observed_at=REVIEW_TIME)
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.assessment(s)['G2']['status'], 'pass')
        self.assertEqual(s['resume_review']['status'], 'reviewed')
        for key in ('response', 'source', 'reported_at', 'scope_keys'):
            self.assertEqual(s['resume_review'][key], receipt[key])
        s = f.record_fact(s, 'Q-C05', 'vps', source='synthetic:current')
        s = f.record_facts(s, [a for a in FIXTURE['route_answers']['vps'] if a['question_id'] != 'Q-S03'], source='synthetic:current')
        self.assertEqual(s['facts']['Q-S03']['observed_at'], OLD_TIME)
        self.assertIn('Q-S03', s['resume_review']['scope_keys'])
        self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_review_required')
        self.assertIsNotNone(f.resume_review_prompt(s))

    def test_purchase_empty_billing_scope_keeps_off_route_obligations(self):
        for outcome in (None, 'unknown', 'declined', 'deferred', 'unchanged', 'not_required'):
            with self.subTest(outcome=outcome):
                s = f.set_context(f.new_state('route-device', 'route-account'), task='renew')
                if outcome != 'not_required':
                    s = f.record_fact(s, 'Q-J01', 'existing_subscriber', source='synthetic:old', observed_at=OLD_TIME)
                s = f.record_fact(s, 'Q-S03', 'old_ssh', source='synthetic:old', observed_at=OLD_TIME)
                s = f.resume_interview(s, resume_id='resume-a')
                if outcome not in (None, 'not_required'):
                    s = reviewed(s, outcome)
                s = f.complete_purchase(s, source='synthetic:purchase', observed_at=REVIEW_TIME)
                receipt = deepcopy(s['resume_review'])
                s = f.complete_purchase(s, source='synthetic:purchase', observed_at=REVIEW_TIME)
                self.assertEqual(s['resume_review'], receipt)
                self.assertIsNone(f.resume_review_prompt(s))
                self.assertIn('Q-S03', s['resume_review']['retained_keys'])
                s = f.record_facts(s, FIXTURE['common_answers'], source='synthetic:current')
                s = f.record_fact(s, 'Q-C05', 'vps', source='synthetic:current')
                s = f.record_facts(s, [a for a in FIXTURE['route_answers']['vps'] if a['question_id'] != 'Q-S03'], source='synthetic:current')
                self.assertEqual(s['resume_review']['scope_keys'], ['Q-S03'])
                self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_review_required')
                self.assertEqual(s['facts']['Q-S03']['observed_at'], OLD_TIME)

    def test_target_changed_requires_rebind_or_explicit_current_correction(self):
        s = reviewed(f.resume_interview(ready(), resume_id='resume-a'), 'target_changed')
        self.assertEqual(f.assessment(s)['G2']['reason'], 'resume_target_rebind_required')
        self.assertEqual(f.resume_interview(s, resume_id='resume-a'), s)
        # A fresh explicit correction may say it is still the same target.
        corrected = f.record_resume_review(s, resume_id='resume-a', response='unchanged',
                                           source='synthetic:user-corrected-target-report', reported_at=REVIEW_TIME)
        self.assertEqual(corrected['target_alias'], s['target_alias'])
        self.assertEqual(f.assessment(corrected)['G2']['status'], 'pass')
        rebound = f.begin_task(s, task_id='other-task', task='environment', target_alias='other-device')
        self.assertNotIn('resume_review', rebound)
        self.assertNotIn('Q-V04', rebound['facts'])

    def test_pending_review_survives_load_and_retains_unrelated_blocker(self):
        s = f.resume_interview(f.set_context(ready(), blocked_reason='Need independent recovery'), resume_id='resume-a')
        self.assertEqual(s['context']['blocked_reason'], 'Need independent recovery')
        self.assertIsNone(f.resume_review_prompt(s))
        self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)
        self.assertNotIn('resume_review', f.STATE_SCHEMA['required'])
        self.assertIn('resume_review', f.STATE_SCHEMA['properties'])

    def test_billing_scope_preserves_plan_but_reviews_subscription_change(self):
        s = f.set_context(ready(), task='renew')
        s = f.record_fact(s, 'Q-C08', 'chosen_plan', source='synthetic:plan', observed_at=OLD_TIME)
        s = f.resume_interview(s, resume_id='resume-a')
        self.assertIn('Q-J01', s['resume_review']['scope_keys'])
        self.assertNotIn('Q-C08', s['resume_review']['scope_keys'])
        s = reviewed(s, 'changed', changed_keys=['Q-J01'])
        self.assertEqual(s['current_subscription']['status'], 'unknown')
        self.assertEqual(s['facts']['Q-C08']['value'], 'chosen_plan')


class ResumeCLITests(unittest.TestCase):
    def run_cli(self, *args):
        return subprocess.run([sys.executable, str(ROOT / 'skills/claude-guardian/scripts/interview_cli.py'),
                               *map(str, args)], capture_output=True, encoding='utf-8', timeout=10)

    def put(self, root, name, value):
        path = root / name
        path.write_text(json.dumps(value), encoding='utf-8')
        return path

    def test_plain_load_and_explicit_resume_are_distinct(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); saved = self.put(root, 'old.json', ready())
            ordinary = self.run_cli('--input', saved)
            self.assertEqual(ordinary.returncode, 0, ordinary.stdout)
            self.assertNotIn('resume_review', json.loads(ordinary.stdout))
            output = root / 'resumed.json'
            resumed = self.run_cli('--input', saved, '--resume', 'resume-a', '--output', output)
            self.assertEqual(resumed.returncode, 0, resumed.stdout)
            result = json.loads(resumed.stdout)
            self.assertEqual(result['resume_review'], f.resume_review_prompt(f.resume_interview(ready(), resume_id='resume-a')))
            self.assertEqual(result['assessment']['G2']['reason'], 'resume_review_required')
            self.assertFalse(result['action_executed'])
            state = f.loads_state(output.read_text(encoding='utf-8'))
            self.assertEqual(state['facts'], ready()['facts'])
            repeat = self.run_cli('--input', output, '--resume', 'resume-a')
            self.assertEqual(json.loads(repeat.stdout)['resume_review'], result['resume_review'])
            self.assertFalse(json.loads(repeat.stdout)['saved'])

    def test_review_reply_and_changed_fact_answer_in_same_turn_are_atomic(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); saved = self.put(root, 'old.json', ready('vps'))
            reply = self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': 'changed',
                             'source': 'synthetic-private-review-source', 'changed_keys': ['Q-S03'],
                             'reported_at': REVIEW_TIME})
            answer = self.put(root, 'answer.json', {'question_id': 'Q-S03', 'value': 'fresh_current_access_report'})
            output = root / 'new.json'
            result = self.run_cli('--input', saved, '--resume', 'resume-a', '--resume-review-file', reply,
                                  '--answer-file', answer, '--output', output)
            self.assertEqual(result.returncode, 0, result.stdout)
            self.assertNotIn('synthetic-private-review-source', result.stdout + result.stderr)
            data = json.loads(result.stdout)
            self.assertIsNone(data['resume_review'])
            self.assertEqual(data['assessment']['G2']['status'], 'pass')
            self.assertEqual(data['assessment']['G3']['status'], 'blocked')
            state = f.loads_state(output.read_text(encoding='utf-8'))
            self.assertEqual(state['facts']['Q-S03']['state'], 'reported')
            self.assertEqual(state['facts']['Q-S03']['value'], 'fresh_current_access_report')
            self.assertEqual(state['resume_review']['source'], 'synthetic-private-review-source')
            repeat = self.run_cli('--input', output, '--resume', 'resume-a', '--resume-review-file', reply)
            self.assertEqual(json.loads(repeat.stdout)['assessment']['G2']['status'], 'pass')

    def test_unresolved_response_does_not_repeat_and_can_receive_fresh_correction(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); saved = self.put(root, 'old.json', ready())
            reply = self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': 'unknown', 'source': 'synthetic:reply'})
            output = root / 'unresolved.json'
            result = self.run_cli('--input', saved, '--resume', 'resume-a', '--resume-review-file', reply, '--output', output)
            self.assertEqual(result.returncode, 0, result.stdout)
            repeat = self.run_cli('--input', output)
            data = json.loads(repeat.stdout)
            self.assertIsNone(data['resume_review'])
            self.assertEqual(data['assessment']['G2']['reason'], 'resume_review_unresolved')
            self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': 'unchanged', 'source': 'synthetic:fresh-correction'})
            resolved = self.run_cli('--input', output, '--resume-review-file', reply)
            self.assertEqual(json.loads(resolved.stdout)['assessment']['G2']['status'], 'pass')

    def test_unpause_requires_resume_and_does_not_reset_contact_history(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            saved = self.put(root, 'paused.json', f.set_context(ready(), paused=True, contact_phase='PC2'))
            context = self.put(root, 'context.json', {'paused': False})
            denied = self.run_cli('--input', saved, '--context-file', context)
            self.assertEqual(denied.returncode, 2)
            output = root / 'new.json'
            good = self.run_cli('--input', saved, '--resume', 'resume-a', '--context-file', context, '--output', output)
            self.assertEqual(good.returncode, 0, good.stdout)
            self.assertEqual(f.loads_state(output.read_text(encoding='utf-8'))['context']['contact_phase'], 'PC2')

    def test_invalid_resume_input_is_sanitized_and_never_saves(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); saved = self.put(root, 'old.json', ready()); output = root / 'never.json'
            reply = self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': 'unchanged', 'source': 'synthetic:reply'})
            cases = [('--resume', 'resume-a'), ('--resume-review-file', reply),
                     ('--input', saved, '--resume', 'private/path'),
                     ('--input', saved, '--resume', 'resume-a', '--target-ref', 'different'),
                     ('--input', saved, '--resume-review-file', reply)]
            for args in cases:
                result = self.run_cli(*args, '--output', output)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse(output.exists())
            for payload in ({'resume_id': 'wrong', 'response': 'unchanged', 'source': 'synthetic:reply'},
                            {'resume_id': 'resume-a', 'response': 'changed', 'source': 'synthetic:reply', 'changed_keys': ['Q-C05']},
                            {'resume_id': 'resume-a', 'response': 'unchanged', 'source': 'token=private-sentinel'},
                            {'resume_id': 'resume-a', 'response': 'unchanged', 'source': 'synthetic:reply', 'authorized': True}):
                self.put(root, 'reply.json', payload)
                result = self.run_cli('--input', saved, '--resume', 'resume-a', '--resume-review-file', reply, '--output', output)
                self.assertEqual(result.returncode, 2, result.stdout)
                self.assertFalse(output.exists())
                self.assertNotIn('private-sentinel', result.stdout + result.stderr)
                self.assertEqual(result.stderr, '')

    def test_cli_triage_precedence_and_deferred_review_without_implicit_save(self):
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve()
            incident = f.record_fact(ready(), 'Q-C04', 'suspended', source='synthetic:current')
            saved = self.put(root, 'incident.json', incident)
            before = set(root.iterdir())
            result = self.run_cli('--input', saved, '--resume', 'resume-a')
            self.assertEqual(result.returncode, 0, result.stdout)
            data = json.loads(result.stdout)
            self.assertEqual(data['question']['id'], 'Q-H01')
            self.assertIsNone(data['resume_review'])
            self.assertEqual(data['assessment']['G1']['status'], 'emergency_deferred')
            self.assertEqual(set(root.iterdir()), before)
            for response in ('declined', 'deferred'):
                saved = self.put(root, 'old.json', ready())
                reply = self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': response, 'source': 'synthetic:reply'})
                output = root / (response + '.json')
                result = self.run_cli('--input', saved, '--resume', 'resume-a', '--resume-review-file', reply, '--output', output)
                self.assertEqual(result.returncode, 0, result.stdout)
                retry = self.run_cli('--input', output, '--resume', 'resume-a')
                data = json.loads(retry.stdout)
                self.assertIsNone(data['resume_review'])
                self.assertEqual(data['assessment']['G2']['reason'], 'resume_review_unresolved')

    def test_cancel_before_resume_save_and_help_remain_safe(self):
        spec = importlib.util.spec_from_file_location('resume_cli', ROOT / 'skills/claude-guardian/scripts/interview_cli.py')
        cli = importlib.util.module_from_spec(spec)
        with patch.object(sys, 'path', [str(ROOT / 'skills/claude-guardian/scripts'), *sys.path]):
            spec.loader.exec_module(cli)
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp).resolve(); saved = self.put(root, 'old.json', ready())
            for name in ('resume_interview', 'record_resume_review', 'resume_review_prompt'):
                output = io.StringIO()
                reply = self.put(root, 'reply.json', {'resume_id': 'resume-a', 'response': 'unchanged', 'source': 'synthetic:reply'})
                with patch.object(cli.flow, name, side_effect=KeyboardInterrupt), patch.object(cli.sys, 'stdout', output), \
                        patch.object(cli.guardian, 'save_new') as save:
                    self.assertEqual(cli.main(['--input', str(saved), '--resume', 'resume-a',
                                               '--resume-review-file', str(reply), '--output', str(root / 'new.json')]), 3)
                    save.assert_not_called()
                self.assertEqual(json.loads(output.getvalue()), {'status': 'cancelled', 'action_executed': False})
        help_result = self.run_cli('--help')
        self.assertEqual(help_result.returncode, 0)
        self.assertIn('--resume-review-file', help_result.stdout)


if __name__ == '__main__':
    unittest.main()
