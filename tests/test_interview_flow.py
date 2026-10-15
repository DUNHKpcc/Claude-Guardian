"""Pure offline interview regressions; no native platform or payment claims."""
import importlib.util
import json
from pathlib import Path
import unittest

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
