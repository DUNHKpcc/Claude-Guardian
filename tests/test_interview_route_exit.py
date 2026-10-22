"""ADR-018: route, egress-source and mobile questions. Offline state tests only."""
import importlib.util
import json
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('route_exit_flow', ROOT / 'skills/claude-guardian/scripts/interview_flow.py')
f = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(f)

NEW = ('Q-X01', 'Q-X02', 'Q-M01', 'Q-V07', 'Q-V08', 'Q-S08')


def base(route='local', basis='explicit_choice', **context):
    s = f.new_state('route-device', 'route-account', task_id='route-task')
    return f.set_context(s, route=route, route_selection_basis=basis, **context)


def ids(s):
    return [q['id'] for q in f.applicable_questions(s)]


def answer(s, qid, value, **kwargs):
    return f.record_fact(s, qid, value, source='synthetic:route-exit', **kwargs)


class RouteExitQuestionTests(unittest.TestCase):
    def test_registry_prompts_and_values(self):
        for qid in NEW:
            self.assertIn(qid, f.QUESTION_PROMPTS)
            self.assertTrue(f.QUESTION_PROMPTS[qid].strip())
            self.assertIn(qid, f.ROUTE_EXIT_VALUES)
        self.assertEqual(f.ROUTE_EXIT_VALUES['Q-X01'],
                         {'airport', 'self_built', 'residential_carpool', 'existing_stable_exit', 'undecided'})
        self.assertEqual(f.ROUTE_EXIT_VALUES['Q-V08'], {'lan_bridged', 'shared_nat', 'other'})

    def test_local_route_asks_egress_source_and_residential_only_for_self_built(self):
        s = base('local')
        self.assertIn('Q-X01', ids(s))
        self.assertNotIn('Q-X02', ids(s))
        s = answer(s, 'Q-X01', 'airport')
        self.assertNotIn('Q-X02', ids(s))
        s = answer(s, 'Q-X01', 'self_built', correction=True)
        self.assertIn('Q-X02', ids(s))
        for other in ('Q-V07', 'Q-V08', 'Q-S08', 'Q-M01'):
            self.assertNotIn(other, ids(s))

    def test_vm_route_asks_guest_os_nic_and_egress(self):
        s = base('vm')
        for qid in ('Q-V07', 'Q-V08', 'Q-X01'):
            self.assertIn(qid, ids(s))
        self.assertNotIn('Q-S08', ids(s))
        s = answer(s, 'Q-X01', 'self_built')
        self.assertIn('Q-X02', ids(s))

    def test_vps_route_asks_exit_kind_and_not_the_relay_source(self):
        s = base('vps')
        self.assertIn('Q-S08', ids(s))
        for qid in ('Q-X01', 'Q-X02', 'Q-V07', 'Q-V08'):
            self.assertNotIn(qid, ids(s))

    def test_unconfirmed_default_route_does_not_ask_route_specific_questions(self):
        s = base('local', basis='default_proposal')
        for qid in ('Q-X01', 'Q-X02', 'Q-V07', 'Q-V08', 'Q-S08'):
            self.assertNotIn(qid, ids(s))

    def test_mobile_question_follows_in_app_purchase_or_mobile_only(self):
        self.assertIn('Q-M01', ids(base('local', billing_channel='apple')))
        self.assertIn('Q-M01', ids(base('local', billing_channel='google')))
        self.assertNotIn('Q-M01', ids(base('local', billing_channel='web')))
        s = answer(base('local'), 'Q-C02', 'mobile_only')
        self.assertIn('Q-M01', ids(s))

    def test_invalid_values_are_rejected_and_unknown_is_a_state(self):
        for qid in NEW:
            for bad in ('sanitized answer', 5, ['x']):
                with self.subTest(qid=qid, bad=bad), self.assertRaisesRegex(f.InterviewError, 'Invalid route or exit category'):
                    answer(base('vm'), qid, bad)
            ok = answer(base('vm'), qid, sorted(f.ROUTE_EXIT_VALUES[qid])[0])
            self.assertEqual(ok['facts'][qid]['state'], 'reported')
        unknown = answer(base('vm'), 'Q-X01', None, state_name='unknown')
        self.assertEqual(unknown['facts']['Q-X01']['state'], 'unknown')
        asked = []
        walker = unknown
        for _ in range(80):
            question = f.next_question(walker)
            if question is None:
                break
            asked.append(question['id'])
            walker = f.mark_asked(walker, question['id'])
        self.assertNotIn('Q-X01', asked)  # a terminal unknown is not asked again

    def test_loaded_state_with_invalid_value_is_refused(self):
        s = answer(base('vm'), 'Q-V08', 'lan_bridged')
        raw = json.loads(f.dumps_state(s, host_opt_in=True))
        raw['facts']['Q-V08']['value'] = 'whatever'
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(raw))

    def test_round_trip_keeps_new_facts(self):
        s = base('vm')
        for qid, value in (('Q-V07', 'omarchy'), ('Q-V08', 'lan_bridged'), ('Q-X01', 'self_built'), ('Q-X02', 'with_residential_exit')):
            s = answer(s, qid, value)
        self.assertEqual(f.loads_state(f.dumps_state(s, host_opt_in=True)), s)

    def test_schema_enumerates_the_values(self):
        props = f.STATE_SCHEMA['properties']['facts']['properties']
        for qid in NEW:
            self.assertEqual(set(props[qid]['properties']['value']['enum']) - {None}, set(f.ROUTE_EXIT_VALUES[qid]))

    def test_route_change_stales_route_bound_facts(self):
        s = base('vm')
        s = answer(s, 'Q-V07', 'omarchy')
        s = answer(s, 'Q-X01', 'self_built')
        s = f.set_context(s, route='vps', route_selection_basis='explicit_choice')
        self.assertEqual(s['facts']['Q-V07']['state'], 'stale')
        self.assertEqual(s['facts']['Q-X01']['state'], 'stale')


if __name__ == '__main__':
    unittest.main()
