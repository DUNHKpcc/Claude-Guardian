"""Pure offline interview regressions; no native platform or payment claims."""
import importlib.util
import json
from pathlib import Path
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location("interview_flow", ROOT / "skills/claude-guardian/scripts/interview_flow.py")
f = importlib.util.module_from_spec(spec)
spec.loader.exec_module(f)


def state(journey="first_subscription", **context):
    s = f.new_state("device-a", "account-a")
    s = f.record_fact(s, "Q-J01", journey, source="user:1")
    return f.set_context(s, **context)


def ids(s):
    return [item["id"] for item in f.applicable_questions(s)]


class InterviewTests(unittest.TestCase):
    def test_accept_default_records_basis_without_second_route_question_or_permission(self):
        original = state()
        saved = json.dumps(original, sort_keys=True)
        chosen = f.record_fact(original, "Q-C05", "accepted_default", source="user:accept")
        self.assertEqual(chosen["context"]["route"], "local")
        self.assertEqual(chosen["context"]["route_selection_basis"], "accepted_default")
        self.assertEqual(chosen["facts"]["Q-C05"]["source"], "user:accept")
        self.assertNotIn("Q-C05", ids(chosen))
        self.assertIn("Q-L01", ids(chosen))
        self.assertEqual(f.assessment(chosen)["route_confirmation"], "confirmed")
        self.assertEqual(f.assessment(chosen)["G3"]["status"], "blocked")
        self.assertEqual(chosen["context"]["contact_phase"], "PC0")
        self.assertFalse(any(chosen["persistence_consent"].values()))
        self.assertEqual(json.dumps(original, sort_keys=True), saved)
        again = f.record_fact(chosen, "Q-C05", "accepted_default", source="user:repeat")
        self.assertNotIn("Q-C05", ids(again))

    def test_accept_default_does_not_replace_another_route_or_explicit_choice(self):
        for route in ("vm", "vps", "compare", "local"):
            chosen = f.record_fact(state(), "Q-C05", route, source="user:choice")
            saved = json.dumps(chosen, sort_keys=True)
            with self.subTest(route=route), self.assertRaises(f.InterviewError):
                f.record_fact(chosen, "Q-C05", "accepted_default", source="user:ambiguous")
            self.assertEqual(json.dumps(chosen, sort_keys=True), saved)

    def test_inferred_default_acceptance_does_not_confirm_route(self):
        chosen = f.record_fact(state(), "Q-C05", "accepted_default", state_name="inferred", source="host:guess")
        self.assertEqual(f.assessment(chosen)["route_confirmation"], "unconfirmed")
        self.assertNotIn("Q-L01", ids(chosen))

    def test_multi_fact_turn_is_absorbed_before_scheduling_with_roles_and_provenance(self):
        original = f.new_state("device-a", "account-a")
        answers = [{"question_id": qid, "value": value} for qid, value in (
            ("Q-J01", "first_subscription"), ("Q-OS01", "macos"),
            ("Q-C05", "local"), ("Q-C08", "Pro"))]
        before = json.dumps((original, answers), sort_keys=True)
        result = f.record_facts(original, answers, source="user:single-turn")
        self.assertEqual(f.next_question(result)["id"], "Q-C01")
        self.assertNotIn("Q-C05", ids(result))
        unresolved = {x["id"] for x in f.assessment(result)["G1"]["unresolved_fields"]}
        self.assertTrue(unresolved.isdisjoint({"Q-J01", "Q-C02", "Q-C05", "Q-C08"}))
        for qid in ("Q-J01", "Q-C02", "Q-C05", "Q-C08"):
            fact = result["facts"][qid]
            self.assertEqual(fact["source"], "user:single-turn")
            self.assertEqual(fact["subject_ref"], "account-a" if qid in ("Q-J01", "Q-C08") else "device-a")
            self.assertIsNotNone(fact["observed_at"])
        self.assertEqual(f.assessment(result)["G3"]["status"], "blocked")
        self.assertFalse(any(result["persistence_consent"].values()))
        self.assertEqual(json.dumps((original, answers), sort_keys=True), before)

    def test_multi_fact_turn_does_not_invent_unspecified_plan(self):
        result = f.record_facts(f.new_state("device-a", "account-a"), [
            {"question_id": "Q-J01", "value": "first_subscription"},
            {"question_id": "Q-C02", "value": "macos"},
            {"question_id": "Q-C05", "value": "accepted_default"}], source="user:turn")
        self.assertNotIn("Q-C08", result["facts"])
        self.assertIn("Q-C08", {x["id"] for x in f.assessment(result)["G1"]["unresolved_fields"]})
        self.assertEqual(result["context"]["route_selection_basis"], "accepted_default")

    def test_multi_fact_initial_turn_order_is_independent_and_offline(self):
        from itertools import permutations
        answers = [{"question_id": qid, "value": value} for qid, value in (
            ("Q-J01", "first_subscription"), ("Q-C02", "macos"),
            ("Q-C05", "accepted_default"), ("Q-C08", "Pro"))]
        expected = None
        with patch.object(f, "_now", return_value="2026-10-15T00:00:00+00:00"), \
                patch("builtins.open", side_effect=AssertionError("no writes or reads")), \
                patch("socket.socket", side_effect=AssertionError("no network")), \
                patch("subprocess.Popen", side_effect=AssertionError("no execution")):
            for order in permutations(answers):
                result = f.record_facts(f.new_state("device-a", "account-a"), list(order), source="user:turn")
                if expected is None:
                    expected = result
                self.assertEqual(result, expected)
                self.assertEqual(f.next_question(result)["id"], "Q-C01")

    def test_multi_fact_turn_rejects_duplicate_alias_and_journey_conflicts(self):
        for pair in (("Q-C02", "Q-C02"), ("Q-C02", "Q-OS01"), ("Q-J01", "Q-J02")):
            original = state()
            before = json.dumps(original, sort_keys=True)
            with self.subTest(pair=pair), self.assertRaises(f.InterviewError):
                f.record_facts(original, [{"question_id": q, "value": "unknown"} for q in pair], source="user:turn")
            self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_multi_fact_existing_task_intent_is_independent_of_journey_order(self):
        from itertools import permutations
        for journey_id in ("Q-J01", "Q-J02"):
            for task, intent in (("upgrade", "upgrade"), ("renew", "renew"), ("network", "none")):
                answers = [{"question_id": journey_id, "value": "existing_subscriber"},
                           {"question_id": "Q-C11", "value": task},
                           {"question_id": "Q-C02", "value": "macos"}]
                expected = None
                with patch.object(f, "_now", return_value="2026-10-15T00:00:00+00:00"):
                    for order in permutations(answers):
                        original = f.new_state("device-a", "account-a")
                        result = f.record_facts(original, list(order), source="user:one-turn")
                        if expected is None:
                            expected = result
                        self.assertEqual(result, expected)
                        self.assertEqual(result["payment_intent"], intent)
                        self.assertEqual(result["context"]["task"], task)
                        self.assertEqual(result["facts"][journey_id]["value"], "existing_subscriber")
                        self.assertEqual(result["facts"]["Q-C11"]["value"], task)
                        self.assertEqual(result["facts"]["Q-C11"]["subject_ref"], "device-a")
                        self.assertEqual(result["context"]["contact_phase"], "PC0")
                        self.assertEqual(f.assessment(result)["G3"]["status"], "blocked")
                        self.assertEqual(original["facts"], {})

    def test_multi_fact_new_subscription_old_user_task_conflict_is_atomic(self):
        for journey_id in ("Q-J01", "Q-J02"):
            for journey in ("first_subscription", "returning_subscription"):
                facts = [{"question_id": journey_id, "value": journey},
                         {"question_id": "Q-C11", "value": "upgrade"}]
                for answers in (facts, list(reversed(facts))):
                    original = f.new_state("device-a", "account-a")
                    before = json.dumps(original, sort_keys=True)
                    with self.assertRaises(f.InterviewError):
                        f.record_facts(original, answers, source="user:conflict")
                    self.assertEqual(json.dumps(original, sort_keys=True), before)
        with self.assertRaises(f.InterviewError):
            f.record_facts(state(), [{"question_id": "Q-C11", "value": "upgrade"}], source="user:conflict")

    def test_multi_fact_turn_invalid_late_fact_is_atomic(self):
        for invalid in ({"question_id": "Q-C07", "value": "owner"},
                        {"question_id": "Q-H03", "value": {"password": "sentinel"}},
                        {"question_id": "Q-C02", "value": "macos", "authorized": True},
                        {"question_id": "Q-C02", "value": "macos", "subject_ref": "other"},
                        {"question_id": "Q-C02", "value": "macos", "state": "invalid"}):
            original = f.new_state("device-a", "account-a")
            before = json.dumps(original, sort_keys=True)
            with self.subTest(invalid=invalid), self.assertRaises(f.InterviewError):
                f.record_facts(original, [{"question_id": "Q-J01", "value": "first_subscription"}, invalid], source="user:turn")
            self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_multi_fact_turn_bounded_envelope_and_sources(self):
        for invalid in (None, {}, [], "text", [None], [{"question_id": []}],
                        [{"question_id": "Q-C02"}] * 96):
            with self.subTest(invalid=invalid), self.assertRaises(f.InterviewError):
                f.record_facts(state(), invalid, source="user:turn")
        with self.assertRaises(f.InterviewError):
            f.record_facts(state(), [{"question_id": "Q-C02", "value": "macos"}])
        result = f.record_facts(state(), [
            {"question_id": "Q-C02", "value": "macos", "source": "user:explicit"},
            {"question_id": "Q-C08", "state": "unknown"}], source="user:shared")
        self.assertEqual(result["facts"]["Q-C02"]["source"], "user:explicit")
        self.assertEqual(result["facts"]["Q-C08"]["state"], "unknown")
        self.assertEqual(result["facts"]["Q-C08"]["source"], "user:shared")

    def test_multi_fact_malformed_state_is_a_fixed_atomic_error(self):
        for invalid_state in ([], {}, True, 1, None, "unsupported"):
            for qid in ("Q-C11", "Q-C05", "Q-J01", "Q-C02"):
                original = f.new_state("device-a", "account-a")
                before = json.dumps(original, sort_keys=True)
                answers = [{"question_id": "Q-C08", "value": "Pro"},
                           {"question_id": qid, "value": "upgrade", "state": invalid_state}]
                with self.subTest(qid=qid, state=invalid_state), self.assertRaisesRegex(f.InterviewError, "^Invalid answer state$"):
                    f.record_facts(original, answers, source="user:turn")
                self.assertEqual(json.dumps(original, sort_keys=True), before)

    def test_complete_registry(self):
        self.assertEqual(len(f.QUESTION_PROMPTS), 95)
        self.assertIn("Q-C07", f.QUESTION_PROMPTS)
        self.assertNotIn("Q-C07", ids(state()))
        with self.assertRaises(f.InterviewError):
            f.record_fact(state(), "Q-C07", "mine", source="user")

    def test_subscription_first_and_reuse(self):
        s = f.new_state("device-a", "account-a")
        self.assertEqual(f.next_question(s)["id"], "Q-J01")
        s = f.record_fact(s, "Q-J01", "first_subscription", source="user:1")
        self.assertEqual(f.next_question(s)["id"], "Q-C02")
        self.assertEqual(s["current_subscription"]["status"], "none_reported")
        self.assertEqual(s["payment_intent"], "new_subscription")
        self.assertEqual(s["current_subscription"]["source"], "user:1")

    def test_experience_never_implies_subscription(self):
        s = f.set_context(f.new_state("device-a", "account-a"), ambiguous_experience=True)
        self.assertEqual(f.journey(s), "unknown")
        self.assertEqual(f.next_question(s)["id"], "Q-J02")
        s = f.record_fact(s, "Q-J02", "existing_subscriber", source="user:2")
        self.assertEqual(f.next_question(s)["id"], "Q-C11")
        self.assertNotIn("Q-J01", ids(s))

    def test_first_and_returning_do_not_get_old_billing(self):
        for journey in ("first_subscription", "returning_subscription"):
            s = state(journey, billing_channel="apple", gift_card=True)
            self.assertNotIn("Q-P02", ids(s))
            self.assertNotIn("Q-A06", ids(s))
            self.assertIn("Q-C08", ids(s))
        self.assertEqual(state("returning_subscription")["payment_intent"], "resubscribe")

    def test_actual_conflict_reopens_only_relevant_old_billing(self):
        s = state(billing_channel="apple", subscription_conflict=True)
        self.assertIn("Q-P02", ids(s))
        self.assertIn("Q-A06", ids(s))

    def test_existing_technical_task_skips_payment(self):
        s = state("existing_subscriber", task="network", billing_channel="apple")
        self.assertNotIn("Q-C11", ids(s))
        self.assertNotIn("Q-C08", ids(s))
        self.assertFalse(any(q.startswith(("Q-P", "Q-A", "Q-W")) for q in ids(s)))

    def test_existing_upgrade_gets_old_channel(self):
        s = state("existing_subscriber", task="upgrade", billing_channel="apple")
        self.assertIn("Q-P02", ids(s))
        self.assertIn("Q-A06", ids(s))
        self.assertIn("Q-C08", ids(s))

    def test_suspension_prioritizes_incident_over_new_purchase(self):
        s = f.record_fact(state(), "Q-C03", "current_suspension", source="user:2")
        self.assertEqual(f.next_question(s)["id"], "Q-H01")
        self.assertTrue(all(q.startswith("Q-H") for q in ids(s)))
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
        s = f.set_context(s, incident_resolved=True)
        self.assertIn("Q-C08", ids(s))

    def test_current_account_incidents_preempt_intake_from_either_answer(self):
        for qid, value in (("Q-C03", "current_suspension"),
                           ("Q-C04", "suspended"),
                           ("Q-C04", "identity_review"),
                           ("Q-C04", "unknown_error")):
            for status in ("reported", "observed"):
                with self.subTest(qid=qid, value=value, status=status):
                    s = f.record_fact(state(), qid, value, state_name=status, source="user:incident")
                    self.assertEqual(f.next_question(s)["id"], "Q-H01")
                    self.assertTrue(all(q.startswith("Q-H") for q in ids(s)))
                    self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
                    self.assertEqual(f.assessment(s)["G3"]["status"], "blocked")
                    resumed = f.loads_state(f.dumps_state(s, host_opt_in=True))
                    self.assertEqual(f.next_question(resumed)["id"], "Q-H01")

    def test_incident_correction_and_staleness_do_not_leave_cached_emergency(self):
        for qid, value, correction in (("Q-C03", "current_suspension", "past_suspension"),
                                        ("Q-C04", "suspended", "active")):
            s = f.record_fact(state(), qid, value, source="user:incident")
            before = json.dumps(s, sort_keys=True)
            for changed in (f.record_fact(s, qid, correction, source="user:correction"),
                            f.invalidate_facts(s, [qid], reason="Current account report needs refresh")):
                with self.subTest(qid=qid, status=changed["facts"][qid]["state"]):
                    self.assertNotEqual(f.assessment(changed)["G1"]["status"], "emergency_deferred")
                    self.assertIn("Q-C08", ids(changed))
                    self.assertEqual(changed["context"]["incident"], "none")
            self.assertEqual(json.dumps(s, sort_keys=True), before)

    def test_history_and_unverified_current_values_do_not_assert_an_emergency(self):
        for qid, value in (("Q-C03", "past_suspension"), ("Q-C03", "past_incident"),
                           ("Q-C04", "active")):
            s = f.record_fact(state(), qid, value, source="user:history")
            self.assertNotEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
            self.assertIn("Q-C08", ids(s))
        for status in ("stale", "conflict", "inferred", "not_applicable"):
            s = f.record_fact(state(), "Q-C04", "suspended", state_name=status, source="host:unverified")
            self.assertNotEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")

    def test_incident_categories_reject_objects_and_do_not_parse_arbitrary_text(self):
        for qid in ("Q-C03", "Q-C04"):
            for value in ([], {}, {"status": "suspended"}):
                with self.subTest(qid=qid, value=value), self.assertRaises(f.InterviewError):
                    f.record_fact(state(), qid, value, source="user:invalid")
            s = f.record_fact(state(), qid, "A historical suspension was resolved", source="user:text")
            self.assertNotEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")

    def test_fresh_incident_reopens_resolution_without_losing_resolved_history(self):
        for qid, value in (("Q-C03", "current_suspension"), ("Q-C04", "suspended")):
            s = f.record_fact(state(), qid, value, source="user:first")
            resolved = f.set_context(s, incident_resolved=True)
            self.assertIn("Q-H08", ids(resolved))
            self.assertIn("Q-C08", ids(resolved))
            reopened = f.record_fact(resolved, qid, value, source="user:new-incident")
            self.assertFalse(reopened["context"]["account_incident_resolved"])
            self.assertEqual(f.assessment(reopened)["G1"]["status"], "emergency_deferred")
            self.assertTrue(resolved["context"]["incident_resolved"])

    def test_account_incident_updates_preserve_independent_host_emergency(self):
        s = f.record_fact(state(incident="data_risk"), "Q-C03", "current_suspension", source="user:1")
        self.assertEqual(s["context"]["incident"], "data_risk")
        s = f.record_fact(s, "Q-C03", "past_suspension", source="user:2")
        self.assertEqual(s["context"]["incident"], "data_risk")
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
        s = f.set_context(s, incident_resolved=True)
        s = f.set_context(s, incident="credential_exposure")
        self.assertFalse(s["context"]["incident_resolved"])
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")

    def test_account_incident_and_resolution_follow_account_not_device(self):
        for resolved in (False, True):
            s = f.record_fact(state(), "Q-C04", "suspended", source="user:account")
            s = f.set_context(s, incident_resolved=resolved)
            changed = f.begin_task(s, task_id="other-device", task="environment", target_alias="device-b")
            self.assertEqual(changed["context"]["account_incident_resolved"], resolved)
            self.assertEqual(f.assessment(changed)["G1"]["status"] == "emergency_deferred", not resolved)
            other = f.begin_task(s, task_id="other-account", task="environment", account_alias="account-b")
            self.assertNotEqual(f.assessment(other)["G1"]["status"], "emergency_deferred")

    def test_resolved_host_event_stays_resolved_after_account_incident_correction(self):
        s = state(incident="data_risk", incident_resolved=True)
        s = f.record_fact(s, "Q-C04", "suspended", source="user:account")
        self.assertTrue(s["context"]["incident_resolved"])
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
        s = f.record_fact(s, "Q-C04", "active", source="user:corrected")
        self.assertTrue(s["context"]["incident_resolved"])
        self.assertNotEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")
        s = f.record_fact(s, "Q-C04", "suspended", source="user:next")
        s = f.set_context(s, incident="data_risk", incident_resolved=True)
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")

    def test_new_incident_refreshes_prior_episode_answers_without_losing_provenance(self):
        s = f.record_fact(state(), "Q-C04", "suspended", source="user:first")
        for number in range(1, 8):
            qid = "Q-H%02d" % number
            s = f.mark_asked(s, qid)
            s = f.record_fact(s, qid, "previous episode", source="user:first-episode")
        s = f.set_context(s, incident_resolved=True)
        before = json.dumps(s, sort_keys=True)
        reopened = f.record_fact(s, "Q-C04", "suspended", source="user:second")
        question = f.next_question(reopened)
        self.assertEqual(question["id"], "Q-H01")
        self.assertTrue(question["clarification"])
        for number in range(1, 8):
            qid = "Q-H%02d" % number
            self.assertEqual(reopened["facts"][qid]["state"], "stale")
            self.assertEqual(reopened["facts"][qid]["source"], "user:first-episode")
            self.assertNotIn(qid, reopened["asked_question_ids"])
        self.assertEqual(json.dumps(s, sort_keys=True), before)
        # A single reply's new incident details survive regardless of answer order.
        answers = [{"question_id": "Q-C04", "value": "suspended"},
                   {"question_id": "Q-H01", "value": "current account"}]
        for order in (answers, list(reversed(answers))):
            updated = f.record_facts(s, order, source="user:second-episode")
            self.assertEqual(updated["facts"]["Q-H01"]["state"], "reported")
            self.assertEqual(f.next_question(updated)["id"], "Q-H02")

    def test_published_schema1_cached_incident_requires_review_before_correction(self):
        # Exact schema/context shape emitted by 584064fc for current_suspension.
        legacy = f.record_fact(state(), "Q-C03", "current_suspension", source="user:legacy")
        for field in f.INCIDENT_CONTEXT_FIELDS:
            legacy["context"].pop(field)
        legacy["context"]["incident"] = "suspension"
        encoded = json.dumps(legacy, sort_keys=True)
        resumed = f.loads_state(encoded)
        self.assertEqual(resumed["context"]["incident_origin"], "legacy_unverified")
        self.assertEqual(resumed["facts"]["Q-C03"]["state"], "stale")
        self.assertEqual(resumed["facts"]["Q-C03"]["source"], "user:legacy")
        self.assertEqual(f.next_question(resumed)["id"], "Q-C03")
        self.assertTrue(f.next_question(resumed)["clarification"])
        self.assertNotEqual(f.assessment(resumed)["G1"]["status"], "emergency_deferred")
        self.assertEqual(f.assessment(resumed)["G2"]["status"], "blocked")
        historical = f.record_fact(resumed, "Q-C03", "past_suspension", source="user:correction")
        self.assertEqual(historical["context"]["incident"], "none")
        self.assertNotEqual(f.assessment(historical)["G1"]["status"], "emergency_deferred")
        current = f.record_fact(resumed, "Q-C03", "current_suspension", source="user:confirmed")
        self.assertEqual(f.next_question(current)["id"], "Q-H01")
        pending = f.record_fact(resumed, "Q-C03", state_name="unknown", source="user:unknown")
        self.assertIsNone(f.next_question(pending))
        self.assertEqual(f.assessment(pending)["G2"]["status"], "blocked")
        changed = f.begin_task(resumed, task_id="device-b", task="environment", target_alias="device-b")
        self.assertEqual(f.next_question(changed)["id"], "Q-C03")
        self.assertEqual(json.dumps(legacy, sort_keys=True), encoded)

    def test_explicit_host_incident_provenance_survives_account_correction(self):
        s = f.record_fact(state(incident="suspension"), "Q-C03", "current_suspension", source="user:1")
        s = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertEqual(s["context"]["incident_origin"], "host")
        s = f.record_fact(s, "Q-C03", "past_suspension", source="user:2")
        self.assertEqual(s["context"]["incident"], "suspension")
        self.assertEqual(f.assessment(s)["G1"]["status"], "emergency_deferred")

    def test_same_host_incident_report_after_resolution_starts_fresh_episode(self):
        s = state(incident="data_risk")
        for number in range(1, 8):
            s = f.record_fact(s, "Q-H%02d" % number, "first episode", source="user:first")
        s = f.set_context(s, incident_resolved=True)
        reopened = f.set_context(s, incident="data_risk")
        self.assertFalse(reopened["context"]["incident_resolved"])
        self.assertEqual(f.assessment(reopened)["G1"]["status"], "emergency_deferred")
        self.assertEqual(f.next_question(reopened)["id"], "Q-H01")
        self.assertTrue(f.next_question(reopened)["clarification"])
        historical = f.set_context(s, incident="data_risk", incident_resolved=True)
        self.assertNotEqual(f.assessment(historical)["G1"]["status"], "emergency_deferred")

    def test_aliases_do_not_repeat(self):
        s = f.record_fact(state(), "Q-OS01", "macos", source="user:1")
        self.assertIn("Q-C02", s["facts"])
        self.assertNotIn("Q-OS01", s["facts"])
        self.assertEqual(f.next_question(s)["id"], "Q-C01")
        s = f.record_fact(s, "Q-Z02", "preserve projects", source="user:2")
        self.assertIn("Q-C12", s["facts"])

    def test_windows_conditionals(self):
        s = f.record_fact(state(), "Q-C02", "windows", source="user")
        self.assertIn("Q-OS02", ids(s))
        self.assertNotIn("Q-OS05", ids(s))
        s = f.set_context(s, timezone_issue=True)
        self.assertTrue(set(f._ids("OS", 6, 8)).issubset(ids(s)))
        self.assertNotIn("Q-OS05", ids(s))
        s = f.set_context(s, os_issue="display_language", windows10=True)
        self.assertTrue({"Q-OS04", "Q-OS05", "Q-OS10"}.issubset(ids(s)))

    def test_macos_and_out_of_scope(self):
        s = f.record_fact(state(os_issue="app_language"), "Q-C02", "macos", source="user")
        self.assertIn("Q-OS03", ids(s))
        self.assertIn("Q-OS11", ids(s))
        self.assertNotIn("Q-OS02", ids(s))
        s = f.record_fact(s, "Q-C02", "mobile_only", source="user")
        self.assertIn("Q-OS12", ids(s))

    def test_route_is_not_inferred_from_default(self):
        s = state()
        self.assertEqual(f.assessment(s)["route_confirmation"], "unconfirmed")
        self.assertFalse(any(q.startswith("Q-L") for q in ids(s)))
        for route, prefix in (("local", "L"), ("vm", "V"), ("vps", "S")):
            chosen = f.record_fact(s, "Q-C05", route, source="user:3")
            self.assertTrue(any(q.startswith("Q-" + prefix) for q in ids(chosen)))
            self.assertEqual(f.assessment(chosen)["route_confirmation"], "confirmed")
            for wrong in {"L", "V", "S"} - {prefix}:
                self.assertFalse(any(q.startswith("Q-" + wrong) for q in ids(chosen)))

    def test_apple_gift_card_branch_and_contact_deferral(self):
        s = state(billing_channel="apple", gift_card=True, buying_gift_card=True)
        self.assertTrue({"Q-A01", "Q-A02", "Q-A03", "Q-A07", "Q-A08", "Q-A09"}.issubset(ids(s)))
        for item in f.applicable_questions(s):
            if item["id"] not in f.POSTCONTACT:
                value = {"Q-J01": "first_subscription", "Q-C04": "unregistered"}.get(item["id"], "done")
                s = f.record_fact(s, item["id"], value, source="user")
        self.assertIsNone(f.next_question(s))
        self.assertIn("requires_contact_gate", [x["reason"] for x in f.assessment(s)["G1"]["unresolved_fields"]])
        s = f.set_context(s, contact_phase="PC1")
        self.assertEqual(f.next_question(s)["id"], "Q-A04")

    def test_other_payment_branches(self):
        for channel, prefix in (("google", "G"), ("web", "W"), ("api", "I"), ("enterprise", "E")):
            s = state(billing_channel=channel)
            self.assertTrue(any(q.startswith("Q-" + prefix) for q in ids(s)))
            self.assertFalse(any(q.startswith("Q-A") for q in ids(s)))
        self.assertNotIn("Q-I02", ids(state(task="api")))
        self.assertIn("Q-I02", ids(state(task="api", organization_task=True)))

    def test_unknown_refusal_deferred_are_not_false_or_reasked(self):
        for status in ("unknown", "declined", "deferred"):
            s = f.record_fact(state(), "Q-C02", state_name=status, source="user")
            self.assertIsNone(s["facts"]["Q-C02"]["value"])
            self.assertNotEqual(f.next_question(s)["id"], "Q-C02")
            self.assertEqual(f.assessment(s)["G1"]["status"], "partial")
            self.assertEqual(f.assessment(s)["G2"]["status"], "blocked")

    def test_asked_is_not_answered(self):
        s = f.mark_asked(state(), "Q-C02")
        self.assertNotEqual(f.next_question(s)["id"], "Q-C02")
        self.assertIn({"id": "Q-C02", "reason": "unasked"}, f.assessment(s)["G1"]["unresolved_fields"])

    def test_bounded_clarification(self):
        s = f.record_fact(state(), "Q-C02", "windows", state_name="conflict", source="user")
        self.assertTrue(f.next_question(s)["clarification"])
        s = f.mark_asked(s, "Q-C02")
        self.assertNotEqual(f.next_question(s)["id"], "Q-C02")
        with self.assertRaises(f.InterviewError):
            f.record_fact(s, "Q-C02", "windows", source="user", clarification=True)

    def test_pause_block_defer(self):
        self.assertIsNone(f.next_question(state(paused=True)))
        self.assertEqual(f.assessment(state(paused=True))["G1"]["status"], "paused")
        self.assertEqual(f.assessment(state(blocked_reason="Need recovery"))["G1"]["status"], "blocked")
        s = f.defer_branch(state(), "core")
        self.assertEqual(f.next_question(s)["branch"], "network")
        self.assertEqual(f.next_question(f.resume_branch(s, "core"))["id"], "Q-C02")

    def test_no_secret_or_inferred_sensitive_facts(self):
        for value in ({"password": "x"}, "sk-ant-abcdefghijklmnopqrst", "4111 1111 1111 1111"):
            with self.assertRaises(f.InterviewError):
                f.record_fact(state(), "Q-H03", value, source="user")
        for qid in ("Q-J01", "Q-C03", "Q-C09", "Q-Z01"):
            with self.assertRaises(f.InterviewError):
                f.record_fact(state(), qid, "unknown", state_name="inferred", source="guess")

    def test_known_token_prefixes_cannot_be_aliases_facts_or_provenance(self):
        for prefix in ('sk-', 'sk-ant-', 'ghp_', 'github_pat_'):
            marker = prefix + 'syntheticPrivateCredential12'
            for field in ('target_alias', 'account_alias', 'task_id'):
                with self.subTest(prefix=prefix, field=field):
                    labels = {'target_alias': 'device-a', 'account_alias': 'account-a', 'task_id': 'task-a'}
                    labels[field] = marker
                    with self.assertRaises(f.InterviewError) as raised:
                        f.new_state(**labels)
                    self.assertNotIn(marker, str(raised.exception))
            for answer in ({'value': marker, 'source': 'user'},
                           {'value': 'sanitized-error-category', 'source': marker}):
                with self.subTest(prefix=prefix, answer=answer), self.assertRaises(f.InterviewError):
                    f.record_fact(state(), 'Q-H03', **answer)

    def test_known_token_aliases_cannot_be_saved_or_resumed(self):
        for prefix in ('ghp_', 'github_pat_'):
            for field in ('target_alias', 'account_alias', 'task_id'):
                with self.subTest(prefix=prefix, field=field):
                    saved = f.new_state('device-a', 'account-a')
                    saved[field] = prefix + 'syntheticPrivateCredential12'
                    with self.assertRaises(f.InterviewError):
                        f.dumps_state(saved, host_opt_in=True)
                    with self.assertRaises(f.InterviewError):
                        f.loads_state(json.dumps(saved))

    def test_ordinary_alias_contract_still_round_trips(self):
        for target, account, task in (('device-a', 'account-a', 'task-1'),
                                      ('github-project', 'ghp-project', '0_local_task'),
                                      ('a' * 80, 'b' * 80, 'c' * 80)):
            with self.subTest(target=target):
                original = f.new_state(target, account, task_id=task)
                resumed = f.loads_state(f.dumps_state(original, host_opt_in=True))
                self.assertEqual(resumed, original)

    def test_target_bound_and_immutable_updates(self):
        s = state()
        with self.assertRaises(f.InterviewError):
            f.record_fact(s, "Q-C02", "windows", source="user", subject_ref="other-device")
        f.record_fact(s, "Q-C02", "windows", source="user")
        self.assertNotIn("Q-C02", s["facts"])

    def test_saved_state_requires_scoped_opt_in_and_resets_permission(self):
        s = state()
        with self.assertRaises(f.InterviewError):
            f.dumps_state(s)
        s = f.record_fact(s, "Q-Z05", "yes", source="user")
        with self.assertRaises(f.InterviewError):
            f.dumps_state(s)
        saved = f.dumps_state(s, host_opt_in=True)
        resumed = f.loads_state(saved)
        self.assertEqual(f.next_question(resumed), f.next_question(s))
        self.assertFalse(resumed["persistence_consent"]["private_save"])
        self.assertEqual(f.assessment(resumed)["G3"]["status"], "blocked")

    def test_reject_invalid_saved_state(self):
        for text in ('{"schema_version":"future"}', '{"x":1,"x":2}', '{"x":NaN}'):
            with self.assertRaises(f.InterviewError):
                f.loads_state(text)
        s = state()
        s["facts"]["Q-C07"] = {}
        with self.assertRaises(f.InterviewError):
            f.validate_state(s)

    def test_purchase_completion_stops_purchase_loop(self):
        s = f.complete_purchase(state(billing_channel="apple"), source="user:done")
        self.assertEqual(s["current_subscription"]["status"], "active_reported")
        self.assertEqual(s["payment_intent"], "none")
        self.assertNotIn("Q-C08", ids(s))
        self.assertFalse(any(q.startswith("Q-A") for q in ids(s)))
        self.assertEqual(f.assessment(s)["G3"]["status"], "blocked")

    def test_selective_refresh_retains_other_known_facts(self):
        s = f.record_fact(state(), "Q-C02", "windows", source="user:1")
        s = f.invalidate_facts(s, ["Q-C02"], reason="User changed machine version")
        self.assertEqual(s["facts"]["Q-C02"]["state"], "stale")
        self.assertEqual(s["facts"]["Q-C02"]["source"], "user:1")
        self.assertEqual(f.journey(s), "first_subscription")
        self.assertEqual(f.next_question(s)["id"], "Q-C02")

    def test_new_task_preserves_identity_but_resets_purchase_target(self):
        s = f.record_fact(state(), "Q-C08", "chosen-plan", source="user")
        s = f.record_fact(s, "Q-C02", "windows", source="user")
        s = f.begin_task(s, task_id="upgrade-2", task="upgrade")
        self.assertNotIn("Q-C08", s["facts"])
        self.assertEqual(s["facts"]["Q-C02"]["value"], "windows")
        self.assertEqual(s["context"]["contact_phase"], "PC0")
        other = f.begin_task(s, task_id="task-3", task="environment", account_alias="account-b")
        self.assertEqual(other["facts"], {})
        self.assertEqual(other["current_subscription"]["status"], "unknown")

    def test_all_relevant_answered_is_coverage_not_action_permission(self):
        s = state("existing_subscriber", task="network", route="local", route_selection_basis="task_context")
        answers = {"Q-J01": "existing_subscriber", "Q-C02": "macos", "Q-C04": "unregistered"}
        for _ in range(100):
            q = f.next_question(s)
            if q is None:
                break
            s = f.record_fact(s, q["id"], answers.get(q["id"], "sanitized answer"), source="user")
        a = f.assessment(s)
        self.assertEqual(a["G1"]["status"], "complete")
        self.assertEqual(a["G2"]["status"], "pass")
        self.assertEqual(a["G3"]["status"], "blocked")

    def test_schema_and_nonfinite_validation(self):
        self.assertEqual(f.STATE_SCHEMA["properties"]["schema_version"]["const"], "1.0.0")
        self.assertNotIn("Q-C07", f.STATE_SCHEMA["properties"]["facts"]["properties"])
        with self.assertRaises(f.InterviewError):
            f.record_fact(state(), "Q-H03", float("nan"), source="user")

    def test_device_change_preserves_subscription_only(self):
        s = f.record_fact(state("existing_subscriber"), "Q-C02", "windows", source="user")
        s = f.begin_task(s, task_id="device-setup", task="environment", target_alias="device-b")
        self.assertEqual(f.journey(s), "existing_subscriber")
        self.assertNotIn("Q-C02", s["facts"])
        self.assertEqual(s["current_subscription"]["status"], "active_reported")

    def test_malformed_enum_fails_cleanly(self):
        with self.assertRaises(f.InterviewError):
            f.set_context(state(), route=[])

    def test_latest_journey_correction_supersedes_other_question(self):
        for first, second in (("Q-J02", "Q-J01"), ("Q-J01", "Q-J02")):
            s = f.new_state("device", "account")
            s = f.record_fact(s, first, "first_subscription", source="user:1")
            s = f.record_fact(s, second, "existing_subscriber", source="user:2")
            self.assertEqual(f.journey(s), "existing_subscriber")
            self.assertEqual(s["current_subscription"]["status"], "active_reported")
            self.assertNotIn(first, s["facts"])
            self.assertEqual(f.next_question(s)["id"], "Q-C11")

    def test_stale_subscription_clears_derived_status(self):
        s = state("existing_subscriber")
        s = f.invalidate_facts(s, ["Q-J01", "Q-J02"], reason="Recheck relevant changed account facts")
        self.assertEqual(f.journey(s), "unknown")
        self.assertEqual(s["current_subscription"]["status"], "unknown")
        self.assertEqual(s["payment_intent"], "unresolved")
        s = f.loads_state(f.dumps_state(s, host_opt_in=True))
        self.assertEqual(s["current_subscription"]["status"], "unknown")

    def test_question_subject_roles_are_enforced(self):
        s = f.new_state("device", "account")
        for qid, value, subject in (("Q-C02", "windows", "account"),
                                    ("Q-J01", "first_subscription", "device"),
                                    ("Q-C02", "windows", "task-1")):
            with self.assertRaises(f.InterviewError):
                f.record_fact(s, qid, value, subject_ref=subject, source="user")

    def test_credential_assignments_and_urls_rejected(self):
        for value in ("password=harmless-test-sentinel", "token: demo", "API_KEY=demo",
                      "https://name:demo@example.test/path", "Authorization: Bearer demo"):
            with self.assertRaises(f.InterviewError):
                f.record_fact(state(), "Q-C01", value, source="user")
        with self.assertRaisesRegex(f.InterviewError, "separately reviewed"):
            f.dumps_state(state(), host_opt_in=True, scope="public_export")

    def test_edited_saved_derived_subscription_is_rejected(self):
        s = state("existing_subscriber")
        s["facts"]["Q-J01"]["state"] = "stale"
        with self.assertRaises(f.InterviewError):
            f.loads_state(json.dumps(s))


if __name__ == "__main__":
    unittest.main()
