"""ADR-026: traceable tiered authorization records. Offline state tests only."""
from copy import deepcopy
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('authorization_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)

USER = 'user:turn-1'
SCOPE_ACTIONS = ['readonly_diagnosis', 'backup_export', 'rollback_fuse', 'allow_rules', 'install_tun']


def base(route='vm', basis='explicit_choice'):
    s = f.new_state('guest-a', 'acct-a', task_id='task-a')
    return f.set_context(s, route=route, route_selection_basis=basis)


def scoped(route='vm', actions=SCOPE_ACTIONS):
    return f.record_scope_confirmation(base(route), source=USER, allowed_actions=actions,
                                       safeguards=['independent_access', 'snapshot'], preserved=['projects'])


class ScopeTests(unittest.TestCase):
    def test_tier_catalog_matches_the_documented_tiers(self):
        for action in ('readonly_diagnosis', 'research', 'dry_run'):
            self.assertEqual(f.authorization_action_tier(action), 'A')
        for action in ('allow_rules', 'install_tun', 'bbr_temporary', 'ssh_forward'):
            self.assertEqual(f.authorization_action_tier(action), 'B')
        for action in ('default_outbound_block', 'killswitch_enable', 'bbr_persist', 'ssh_config_change',
                       'payment', 'credential_handling', 'data_cleanup', 'claude_contact'):
            self.assertEqual(f.authorization_action_tier(action), 'C')
        self.assertEqual(f.authorization_action_tier('something_new'), 'C')
        self.assertEqual(f.authorization_action_tier(None), 'C')

    def test_scope_needs_an_explicit_route_and_a_user_source(self):
        with self.assertRaisesRegex(f.InterviewError, 'Confirm a route'):
            f.record_scope_confirmation(base(basis='default_proposal'), source=USER, allowed_actions=SCOPE_ACTIONS)
        for bad in ('agent:self', 'host:x', '', None, 'user:', 'USER:turn'):
            with self.subTest(bad=bad), self.assertRaisesRegex(f.InterviewError, 'explicit reply'):
                f.record_scope_confirmation(base(), source=bad, allowed_actions=SCOPE_ACTIONS)

    def test_scope_cannot_contain_tier_c_or_unknown_actions(self):
        for bad in (['killswitch_enable'], ['readonly_diagnosis', 'payment'], ['invented_action'], [], 'allow_rules'):
            with self.subTest(bad=bad), self.assertRaises(f.InterviewError):
                f.record_scope_confirmation(base(), source=USER, allowed_actions=bad)
        with self.assertRaises(f.InterviewError):
            f.record_scope_confirmation(base(), source=USER, allowed_actions=SCOPE_ACTIONS, safeguards=['telepathy'])
        with self.assertRaises(f.InterviewError):
            f.record_scope_confirmation(base(), source=USER, allowed_actions=SCOPE_ACTIONS, preserved='projects')

    def test_new_scope_replaces_the_old_one_and_keeps_history(self):
        s = scoped()
        s = f.record_scope_confirmation(s, source='user:turn-2', allowed_actions=['readonly_diagnosis'])
        statuses = [x['status'] for x in s['authorization']['scopes']]
        self.assertEqual(statuses, ['revoked', 'active'])
        self.assertEqual(f.authorization_summary(s)['scope'], 'active')

    def test_answers_alone_never_create_a_record(self):
        s = f.record_fact(base(), 'Q-V07', 'omarchy', source='user:turn-1')
        self.assertNotIn('authorization', s)
        self.assertEqual(f.authorization_summary(s), {})
        self.assertNotIn('authorization', f.assessment(s))


class PlanTests(unittest.TestCase):
    def test_plan_must_be_tier_b_and_inside_the_scope(self):
        s = scoped()
        s = f.record_plan_approval(s, plan_id='plan-1', steps=['backup_export', 'rollback_fuse', 'allow_rules'], source=USER)
        self.assertEqual(s['authorization']['plans'][0]['status'], 'approved')
        for bad in (['default_outbound_block'], ['readonly_diagnosis'], ['bbr_temporary'], ['allow_rules', 'payment'], []):
            with self.subTest(bad=bad), self.assertRaises(f.InterviewError):
                f.record_plan_approval(s, plan_id='plan-2', steps=bad, source=USER)

    def test_plan_needs_a_current_scope_and_a_user_source_and_a_new_id(self):
        with self.assertRaisesRegex(f.InterviewError, 'scope confirmation'):
            f.record_plan_approval(base(), plan_id='p', steps=['allow_rules'], source=USER)
        s = scoped()
        with self.assertRaisesRegex(f.InterviewError, 'explicit reply'):
            f.record_plan_approval(s, plan_id='p', steps=['allow_rules'], source='agent:me')
        s = f.record_plan_approval(s, plan_id='p', steps=['allow_rules'], source=USER)
        with self.assertRaisesRegex(f.InterviewError, 'already used'):
            f.record_plan_approval(s, plan_id='p', steps=['allow_rules'], source=USER)

    def test_plan_results_are_traceable_and_idempotent(self):
        s = f.record_plan_approval(scoped(), plan_id='p', steps=['allow_rules'], source=USER)
        s = f.record_plan_result(s, 'p', status='completed', source='agent:run-1')
        self.assertEqual(s['authorization']['plans'][0]['result_source'], 'agent:run-1')
        self.assertEqual(f.record_plan_result(s, 'p', status='completed', source='agent:run-1'), s)
        with self.assertRaisesRegex(f.InterviewError, 'approved plan'):
            f.record_plan_result(s, 'p', status='failed', source='agent:run-2')
        with self.assertRaises(f.InterviewError):
            f.record_plan_result(s, 'nope', status='completed', source='agent:run-1')
        for bad in ('done', None):
            with self.assertRaises(f.InterviewError):
                f.record_plan_result(s, 'p', status=bad, source='agent:run-1')
        with self.assertRaises(f.InterviewError):
            f.record_plan_result(f.record_plan_approval(scoped(), plan_id='q', steps=['allow_rules'], source=USER),
                                 'q', status='completed', source='nobody')


class CheckTests(unittest.TestCase):
    def test_tier_a_is_allowed_in_scope_only(self):
        self.assertFalse(f.authorization_check(base(), 'readonly_diagnosis')['allowed'])
        self.assertEqual(f.authorization_check(base(), 'readonly_diagnosis')['reason'], 'scope_not_active')
        self.assertTrue(f.authorization_check(scoped(), 'readonly_diagnosis')['allowed'])

    def test_tier_b_needs_an_approved_plan_that_lists_the_action(self):
        s = scoped()
        self.assertEqual(f.authorization_check(s, 'allow_rules')['reason'], 'no_approved_plan')
        s = f.record_plan_approval(s, plan_id='p', steps=['allow_rules'], source=USER)
        self.assertTrue(f.authorization_check(s, 'allow_rules')['allowed'])
        self.assertEqual(f.authorization_check(s, 'install_tun')['reason'], 'no_approved_plan')
        done = f.record_plan_result(s, 'p', status='completed', source='agent:r')
        self.assertFalse(f.authorization_check(done, 'allow_rules')['allowed'])

    def test_tier_c_needs_a_confirmation_and_is_consumed_once(self):
        s = scoped()
        self.assertEqual(f.authorization_check(s, 'default_outbound_block')['reason'], 'confirmation_required')
        s = f.request_critical_confirmation(s, action='default_outbound_block',
                                            reason='switch default outbound to block', rollback='automatic_fuse')
        self.assertEqual(f.authorization_check(s, 'default_outbound_block')['reason'], 'confirmation_pending')
        self.assertEqual(f.authorization_summary(s)['pending_confirmations'], [{'id': 'c-1', 'action': 'default_outbound_block'}])
        s = f.resolve_critical_confirmation(s, 'c-1', decision='confirmed', source='user:turn-9')
        self.assertTrue(f.authorization_check(s, 'default_outbound_block')['allowed'])
        s = f.use_critical_confirmation(s, 'default_outbound_block')
        self.assertEqual(s['authorization']['confirmations'][0]['status'], 'used')
        self.assertFalse(f.authorization_check(s, 'default_outbound_block')['allowed'])
        with self.assertRaisesRegex(f.InterviewError, 'No usable confirmation'):
            f.use_critical_confirmation(s, 'default_outbound_block')

    def test_cancelled_or_modified_confirmation_grants_nothing(self):
        for decision in ('cancelled', 'modified'):
            s = f.request_critical_confirmation(scoped(), action='killswitch_enable', reason='enable', rollback='automatic_fuse')
            s = f.resolve_critical_confirmation(s, 'c-1', decision=decision, source=USER)
            self.assertFalse(f.authorization_check(s, 'killswitch_enable')['allowed'], decision)

    def test_confirmation_rules(self):
        s = scoped()
        with self.assertRaisesRegex(f.InterviewError, 'tier C'):
            f.request_critical_confirmation(s, action='allow_rules', reason='x', rollback='none')
        with self.assertRaises(f.InterviewError):
            f.request_critical_confirmation(s, action='bbr_persist', reason='x', rollback='maybe')
        with self.assertRaises(f.InterviewError):
            f.request_critical_confirmation(s, action='bbr_persist', reason='', rollback='none')
        with self.assertRaisesRegex(f.InterviewError, 'scope confirmation'):
            f.request_critical_confirmation(base(), action='bbr_persist', reason='x', rollback='none')
        s = f.request_critical_confirmation(s, action='bbr_persist', reason='persist bbr', rollback='manual_documented')
        with self.assertRaisesRegex(f.InterviewError, 'explicit reply'):
            f.resolve_critical_confirmation(s, 'c-1', decision='confirmed', source='agent:me')
        with self.assertRaises(f.InterviewError):
            f.resolve_critical_confirmation(s, 'c-1', decision='maybe', source=USER)
        s = f.resolve_critical_confirmation(s, 'c-1', decision='confirmed', source=USER)
        with self.assertRaisesRegex(f.InterviewError, 'pending'):
            f.resolve_critical_confirmation(s, 'c-1', decision='cancelled', source=USER)

    def test_user_only_actions_are_never_allowed_even_when_confirmed(self):
        for action in sorted(f.USER_ONLY_ACTIONS):
            s = f.request_critical_confirmation(scoped(), action=action, reason='user does it', rollback='none')
            s = f.resolve_critical_confirmation(s, 'c-1', decision='confirmed', source=USER)
            check = f.authorization_check(s, action)
            self.assertFalse(check['allowed'], action)
            self.assertEqual(check['reason'], 'user_performs_this')
        self.assertEqual(f.authorization_check(scoped(), 'payment')['reason'], 'user_performs_this')

    def test_unknown_action_is_tier_c(self):
        check = f.authorization_check(scoped(), 'invented_action')
        self.assertEqual((check['tier'], check['allowed']), ('C', False))


class InvalidationTests(unittest.TestCase):
    def full(self):
        s = f.record_plan_approval(scoped(), plan_id='p', steps=['allow_rules'], source=USER)
        return f.request_critical_confirmation(s, action='killswitch_enable', reason='enable', rollback='automatic_fuse')

    def test_route_change_retires_the_scope_without_restoring_it(self):
        s = f.set_context(self.full(), route='vps', route_selection_basis='explicit_choice')
        self.assertFalse(f.authorization_check(s, 'readonly_diagnosis')['allowed'])
        self.assertEqual(f.authorization_summary(s)['scope'], 'stale')
        self.assertEqual(s['authorization']['scopes'][0]['status'], 'stale')
        self.assertEqual(s['authorization']['plans'][0]['status'], 'stale')
        self.assertEqual(s['authorization']['confirmations'][0]['status'], 'stale')
        s = f.set_context(s, route='vm', route_selection_basis='explicit_choice')
        # Going back to the old route does not revive it: the user must confirm a new scope.
        self.assertEqual(f.authorization_summary(s)['scope'], 'stale')
        self.assertFalse(f.authorization_check(s, 'readonly_diagnosis')['allowed'])

    def test_withdrawn_route_choice_retires_the_scope(self):
        s = f.set_context(self.full(), route_selection_basis='default_proposal')
        self.assertFalse(f.authorization_check(s, 'readonly_diagnosis')['allowed'])
        self.assertEqual(s['authorization']['scopes'][0]['status'], 'stale')

    def test_resume_stales_everything_and_requires_reconfirmation(self):
        s = f.resume_interview(self.full(), resume_id='event-1')
        auth = s['authorization']
        self.assertEqual([x['status'] for x in auth['scopes']], ['stale'])
        self.assertEqual(auth['plans'][0]['status'], 'stale')
        self.assertEqual(auth['confirmations'][0]['status'], 'stale')
        for action in ('readonly_diagnosis', 'allow_rules', 'killswitch_enable'):
            self.assertFalse(f.authorization_check(s, action)['allowed'], action)
        s = f.record_scope_confirmation(s, source='user:turn-3', allowed_actions=['readonly_diagnosis'])
        self.assertTrue(f.authorization_check(s, 'readonly_diagnosis')['allowed'])
        self.assertFalse(f.authorization_check(s, 'allow_rules')['allowed'])

    def test_a_scope_for_another_target_does_not_apply(self):
        s = scoped()
        other = deepcopy(s)
        other['target_alias'] = 'guest-b'
        self.assertFalse(f.authorization_check(other, 'readonly_diagnosis')['allowed'])

    def test_round_trip_keeps_the_record_and_it_is_not_a_resume(self):
        s = self.full()
        loaded = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertEqual(loaded, s)
        self.assertTrue(f.authorization_check(loaded, 'allow_rules')['allowed'])

    def test_tampered_saved_records_are_refused(self):
        raw = json.loads(f.dumps_state(self.full(), host_opt_in=True))
        cases = {
            'agent_source': lambda r: r['authorization']['scopes'][0].__setitem__('source', 'agent:me'),
            'tier_c_in_scope': lambda r: r['authorization']['scopes'][0]['allowed_actions'].append('payment'),
            'tier_a_in_plan': lambda r: r['authorization']['plans'][0]['steps'].append('readonly_diagnosis'),
            'unknown_plan_scope': lambda r: r['authorization']['plans'][0].__setitem__('scope_id', 'scope-9'),
            'two_active': lambda r: r['authorization']['scopes'].append(deepcopy(r['authorization']['scopes'][0]) | {'scope_id': 'scope-2'}),
            'extra_key': lambda r: r['authorization'].__setitem__('grant', True),
            'bad_status': lambda r: r['authorization']['confirmations'][0].__setitem__('status', 'granted'),
        }
        for name, mutate in cases.items():
            with self.subTest(name=name):
                bad = deepcopy(raw)
                mutate(bad)
                with self.assertRaises(f.InterviewError):
                    f.loads_state(json.dumps(bad))


class AssessmentTests(unittest.TestCase):
    def test_summary_is_exposed_but_g3_stays_blocked(self):
        s = f.record_plan_approval(scoped(), plan_id='p', steps=['allow_rules'], source=USER)
        s = f.request_critical_confirmation(s, action='killswitch_enable', reason='enable', rollback='automatic_fuse')
        a = f.assessment(s)
        self.assertEqual(a['G3']['status'], 'blocked')
        summary = a['authorization']
        self.assertEqual(summary['scope'], 'active')
        self.assertTrue(summary['binding_valid'])
        self.assertEqual(summary['plans'], {'approved': 1})
        self.assertEqual(summary['pending_confirmations'], [{'id': 'c-1', 'action': 'killswitch_enable'}])
        self.assertIn('not an execution grant', summary['note'])

    def test_schema_describes_the_section(self):
        prop = f.STATE_SCHEMA['properties']['authorization']
        self.assertEqual(set(prop['required']), {'scopes', 'plans', 'confirmations'})


if __name__ == '__main__':
    unittest.main()
