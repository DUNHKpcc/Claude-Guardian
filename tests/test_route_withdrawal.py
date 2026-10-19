"""Offline route withdrawal: retained facts are not a current target or permission."""
from copy import deepcopy
import importlib.util
import itertools
import json
from pathlib import Path
import unittest
from unittest.mock import patch


ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location(
    'route_withdrawal_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)
OLD = '2026-10-18T01:00:00Z'
NOW = '2026-10-19T01:00:00Z'
ROUTE_FACTS = {'local': 'Q-L04', 'vm': 'Q-V03', 'vps': 'Q-S02'}
DEPENDENCIES = ('Q-N02', 'Q-N05', 'Q-Z01', 'Q-Z03', 'Q-Z04')


def answer(state, qid, value=None, **kwargs):
    with patch.object(f, '_now', return_value=NOW):
        return f.record_fact(state, qid, value, source='synthetic:current', **kwargs)


def selected(route='vm'):
    state = f.set_context(f.new_state('device-a', 'account-a'), task='environment')
    with patch.object(f, '_now', return_value=OLD):
        state = f.record_facts(state, [
            {'question_id': 'Q-J01', 'value': 'existing_subscriber'},
            {'question_id': 'Q-C05', 'value': route},
            {'question_id': 'Q-C02', 'value': 'macos'},
            {'question_id': 'Q-C12', 'value': 'preserve_existing_projects'},
            {'question_id': 'Q-C13', 'value': 'Pro'},
            {'question_id': 'Q-P02', 'value': {'plan': 'Pro', 'billing_channel': 'web'}},
            {'question_id': 'Q-D01', 'value': 'past_restriction_on_target'},
            {'question_id': 'Q-D02', 'value': 'audit_only'},
            {'question_id': ROUTE_FACTS[route], 'value': {'asset': 'existing', 'preserve': True}},
            *({'question_id': qid, 'value': 'old_route_report'} for qid in DEPENDENCIES),
        ], source='synthetic:original')
    return f.set_context(state, existing_test=True, compatibility_needed=True,
                         integration_used=True, change_planned=True,
                         plan_compatibility_needed=True)


class RouteWithdrawalTests(unittest.TestCase):
    def assert_unconfirmed(self, state):
        report = f.assessment(state)
        self.assertEqual(report['route_confirmation'], 'unconfirmed')
        self.assertTrue({'local', 'vm', 'vps'}.isdisjoint(report['active_branches']))
        self.assertEqual(report['G2']['status'], 'blocked')
        self.assertEqual(report['G3']['status'], 'blocked')

    def assert_retained_stale(self, before, after, qids):
        for qid in qids:
            with self.subTest(fact=qid):
                self.assertEqual(after['facts'][qid]['state'], 'stale')
                self.assertTrue(after['facts'][qid]['blocker_reason'])
                for key in ('value', 'source', 'subject_ref', 'observed_at'):
                    self.assertEqual(after['facts'][qid][key], before['facts'][qid][key])

    def test_unresolved_c05_retracts_confirmation_and_preserves_old_evidence(self):
        for status in ('unknown', 'declined', 'deferred', 'unasked', 'stale', 'conflict', 'inferred', 'not_applicable'):
            with self.subTest(status=status):
                before = selected()
                original = deepcopy(before)
                value = 'vm' if status in {'stale', 'conflict', 'inferred', 'not_applicable'} else None
                after = answer(before, 'Q-C05', value, state_name=status)
                self.assert_unconfirmed(after)
                self.assertEqual(after['context']['route'], 'compare')
                self.assertEqual(after['context']['route_selection_basis'], 'default_proposal')
                self.assert_retained_stale(before, after, [ROUTE_FACTS['vm'], *DEPENDENCIES, 'Q-D01', 'Q-D02'])
                for qid in ('Q-J01', 'Q-C02', 'Q-C12', 'Q-C13', 'Q-P02'):
                    self.assertEqual(after['facts'][qid], before['facts'][qid])
                self.assertEqual(after['current_subscription'], before['current_subscription'])
                for flag in ('existing_test', 'compatibility_needed', 'integration_used', 'change_planned'):
                    self.assertFalse(after['context'][flag])
                self.assertFalse(after['context'].get('plan_compatibility_needed', False))
                self.assertEqual(before, original)

    def test_compare_retracts_dependent_plan_and_cannot_accept_a_nonexistent_default(self):
        before = selected()
        compared = answer(before, 'Q-C05', 'compare')
        self.assert_unconfirmed(compared)
        self.assert_retained_stale(before, compared, [ROUTE_FACTS['vm'], *DEPENDENCIES])
        with self.assertRaises(f.InterviewError):
            answer(compared, 'Q-C05', 'accepted_default')
        proposal = f.set_context(compared, route='local', route_selection_basis='default_proposal')
        accepted = answer(proposal, 'Q-C05', 'accepted_default')
        self.assertEqual(f.assessment(accepted)['route_confirmation'], 'confirmed')
        self.assertEqual(accepted['context']['route'], 'local')

    def test_same_time_historical_acceptance_cannot_bypass_missing_local_proposal(self):
        compared = answer(f.new_state('device-a', 'account-a'), 'Q-C05', 'compare', observed_at=OLD)
        before = deepcopy(compared)
        with self.assertRaisesRegex(f.InterviewError, '^No current local default proposal to accept$'):
            answer(compared, 'Q-C05', 'accepted_default', observed_at=OLD)
        self.assertEqual(compared, before)

    def test_invalidating_c05_retracts_its_derived_confirmation(self):
        before = selected('vps')
        after = f.invalidate_facts(before, ['Q-C05'], reason='Current route choice expired')
        self.assert_unconfirmed(after)
        self.assert_retained_stale(before, after, ['Q-C05', ROUTE_FACTS['vps'], *DEPENDENCIES])
        self.assertEqual(after['facts']['Q-C05']['blocker_reason'], 'Current route choice expired')

    def test_route_changes_stale_only_old_route_and_bound_plan_facts(self):
        for old, new in itertools.permutations(ROUTE_FACTS, 2):
            with self.subTest(old=old, new=new):
                before = answer(selected(old), ROUTE_FACTS[new], 'known_unselected_asset')
                after = answer(before, 'Q-C05', new)
                self.assertEqual(after['context']['route'], new)
                self.assertEqual(f.assessment(after)['route_confirmation'], 'confirmed')
                self.assert_retained_stale(before, after, [ROUTE_FACTS[old], *DEPENDENCIES, 'Q-D01', 'Q-D02'])
                self.assertEqual(after['facts'][ROUTE_FACTS[new]], before['facts'][ROUTE_FACTS[new]])

    def test_repeated_same_route_confirmation_does_not_invalidate_facts(self):
        for route in ROUTE_FACTS:
            before = selected(route)
            after = answer(before, 'Q-C05', route)
            self.assertEqual(after['context'], before['context'])
            for qid in before['facts']:
                if qid != 'Q-C05':
                    self.assertEqual(after['facts'][qid], before['facts'][qid])
            self.assertEqual(f.set_context(before, route=route), before)
        accepted = answer(f.new_state('device-a', 'account-a'), 'Q-C05', 'accepted_default')
        accepted = answer(accepted, 'Q-L04', 'local_projects')
        repeated = answer(accepted, 'Q-C05', 'accepted_default')
        self.assertEqual(repeated, accepted)

    def test_first_choice_does_not_stale_fresh_unbound_common_answers(self):
        before = answer(f.new_state('device-a', 'account-a'), 'Q-N02', 'vm_locations')
        after = answer(before, 'Q-C05', 'vm')
        self.assertEqual(after['facts']['Q-N02'], before['facts']['Q-N02'])

    def test_unanswered_local_proposal_survives_terminal_reply_without_confirmation(self):
        for status in ('unknown', 'declined', 'deferred'):
            with self.subTest(status=status):
                proposal = f.new_state('device-a', 'account-a')
                proposal = answer(proposal, 'Q-V03', {'asset': 'existing_vm'})
                before = deepcopy(proposal)
                pending = answer(proposal, 'Q-C05', state_name=status)
                self.assertEqual(pending['context']['route'], 'local')
                self.assertEqual(pending['context']['route_selection_basis'], 'default_proposal')
                self.assert_unconfirmed(pending)
                self.assertEqual(pending['facts']['Q-V03'], before['facts']['Q-V03'])
                pending = f.loads_state(f.dumps_state(pending, host_opt_in=True))
                accepted = answer(pending, 'Q-C05', 'accepted_default')
                self.assertEqual(accepted['context']['route'], 'local')
                self.assertEqual(accepted['context']['route_selection_basis'], 'accepted_default')
                self.assertEqual(f.assessment(accepted)['route_confirmation'], 'confirmed')
                self.assertEqual(f.assessment(accepted)['G3']['status'], 'blocked')
                self.assertEqual(proposal, before)

    def test_unknown_after_any_confirmed_route_requires_a_new_local_proposal(self):
        for route in ('local', 'vm', 'vps', 'accepted_default'):
            with self.subTest(route=route):
                chosen = answer(f.new_state('device-a', 'account-a'), 'Q-C05', route)
                withdrawn = answer(chosen, 'Q-C05', state_name='unknown')
                self.assertEqual(withdrawn['context']['route'], 'compare')
                self.assert_unconfirmed(withdrawn)
                with self.assertRaisesRegex(f.InterviewError, 'No current local default proposal'):
                    answer(withdrawn, 'Q-C05', 'accepted_default')

    def test_context_route_change_cannot_inherit_old_confirmation(self):
        before = selected()
        after = f.set_context(before, route='vps')
        self.assert_unconfirmed(after)
        self.assertEqual(after['context']['route_selection_basis'], 'default_proposal')
        self.assert_retained_stale(before, after, [ROUTE_FACTS['vm'], *DEPENDENCIES])

    def test_context_confirmation_requires_consistent_current_c05(self):
        before = answer(selected(), 'Q-C05', state_name='unknown')
        with self.assertRaisesRegex(f.InterviewError, 'route confirmation'):
            f.set_context(before, route='vm', route_selection_basis='explicit_choice')
        confirmed = answer(before, 'Q-C05', 'vm')
        self.assertEqual(f.assessment(confirmed)['route_confirmation'], 'confirmed')
        self.assertEqual(confirmed['facts']['Q-V03']['state'], 'stale')

    def test_context_comparison_and_basis_withdrawal_invalidate_previous_plan(self):
        before = selected()
        for changes in ({'route': 'compare'}, {'route_selection_basis': 'default_proposal'}):
            with self.subTest(changes=changes):
                after = f.set_context(before, **changes)
                self.assert_unconfirmed(after)
                self.assert_retained_stale(before, after, [ROUTE_FACTS['vm'], *DEPENDENCIES])

    def test_context_only_explicit_task_route_remains_supported(self):
        state = f.set_context(f.new_state('device-a', 'account-a'), task='network',
                              route='vps', route_selection_basis='task_context')
        self.assertEqual(f.assessment(state)['route_confirmation'], 'confirmed')
        self.assertIn('Q-S01', [item['id'] for item in f.applicable_questions(state)])

    def test_explicit_new_route_context_flags_are_current_not_retained(self):
        state = f.set_context(f.new_state('device-a', 'account-a'), task='network',
                              route='vm', route_selection_basis='task_context')
        state = answer(state, 'Q-N05', 'old_vm_test')
        changed = f.set_context(state, route='vps', route_selection_basis='task_context',
                                existing_test=True, compatibility_needed=True,
                                plan_compatibility_needed=True)
        self.assertTrue(changed['context']['existing_test'])
        self.assertTrue(changed['context']['compatibility_needed'])
        self.assertTrue(changed['context']['plan_compatibility_needed'])
        self.assertEqual(changed['facts']['Q-N05']['state'], 'stale')

    def test_legacy_contradictory_saved_confirmation_fails_closed_without_rewriting(self):
        original = selected()
        original['facts']['Q-C05'].update(state='unknown', value=None)
        serialized = json.dumps(original)
        for _ in range(2):
            with self.assertRaisesRegex(f.InterviewError, 'route confirmation'):
                f.loads_state(serialized)
        self.assertEqual(json.dumps(original), serialized)

    def test_roundtrip_after_withdrawal_is_idempotent_without_refreshing_observations(self):
        state = answer(selected(), 'Q-C05', state_name='declined')
        for _ in range(2):
            loaded = f.loads_state(f.dumps_state(state, host_opt_in=True))
            self.assertEqual(loaded, state)
            self.assert_unconfirmed(loaded)
            state = loaded

    def test_resume_binding_and_retained_off_route_facts_survive_withdrawal(self):
        state = f.resume_interview(selected(), resume_id='resume-a')
        state = f.record_resume_review(state, resume_id='resume-a', response='unchanged',
                                       source='synthetic:review', reported_at=NOW)
        after = answer(state, 'Q-C05', state_name='unknown')
        self.assertEqual(after['resume_review']['binding']['route'], 'compare')
        self.assertEqual(after['resume_review']['binding']['route_selection_basis'], 'default_proposal')
        self.assertIn('Q-V03', after['resume_review']['retained_keys'])
        self.assertNotIn('Q-V03', after['resume_review']['scope_keys'])
        self.assertEqual(after['resume_review']['status'], 'pending')
        self.assert_unconfirmed(after)

    def test_current_atomic_reply_can_refresh_new_route_dependencies_in_either_order(self):
        before = selected()
        replies = [{'question_id': 'Q-C05', 'value': 'vps'},
                   {'question_id': 'Q-N02', 'value': 'new_locations'},
                   {'question_id': 'Q-S02', 'value': 'existing_server'}]
        for order in itertools.permutations(replies):
            after = f.record_facts(before, list(order), source='synthetic:current')
            self.assertEqual(after['facts']['Q-N02']['state'], 'reported')
            self.assertEqual(after['facts']['Q-S02']['state'], 'reported')
            self.assertEqual(after['facts']['Q-V03']['state'], 'stale')

    def test_urgent_and_subscription_only_paths_remain_available_after_withdrawal(self):
        state = answer(selected(), 'Q-C05', state_name='unknown')
        urgent = f.set_context(state, incident='credential_exposure')
        self.assertEqual(f.next_question(urgent)['id'], 'Q-H01')
        self.assertEqual(f.assessment(urgent)['G1']['status'], 'emergency_deferred')
        billing = f.set_context(state, task='billing_issue')
        self.assertEqual({item['id'] for item in f.applicable_questions(billing)}, {'Q-J01', 'Q-P02'})

    def test_historical_route_import_cannot_revive_withdrawn_choice(self):
        withdrawn = answer(selected(), 'Q-C05', state_name='unknown')
        after = answer(withdrawn, 'Q-C05', 'vm', observed_at='2026-10-19T02:00:00Z')
        self.assert_unconfirmed(after)
        self.assertEqual(after['facts']['Q-C05']['state'], 'stale')
        self.assertEqual(after['facts']['Q-C05']['observed_at'], '2026-10-19T02:00:00Z')

    def test_old_choice_replay_cannot_replace_a_later_selected_route(self):
        current = answer(selected(), 'Q-C05', 'vps')
        original = deepcopy(current)
        with self.assertRaisesRegex(f.InterviewError, 'Older route evidence'):
            answer(current, 'Q-C05', 'vm', observed_at=OLD)
        self.assertEqual(current, original)
        explicit = answer(current, 'Q-C05', 'vm', observed_at=OLD, current_reply=True)
        self.assertEqual(explicit['context']['route'], 'vm')
        self.assertEqual(explicit['facts']['Q-C05']['observed_at'], OLD)


if __name__ == '__main__':
    unittest.main()
