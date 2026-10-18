"""Supplemental v2 evidence checks; the immutable v1 failure remains intact.

Python 3.10-compatible; UTF-8 file reads explicit. No response generation.
"""
import ast
import hashlib
import json
from pathlib import Path
import unittest

BASE = Path(__file__).resolve().parents[1]
OLD = BASE / "retained/candidate"
NEW = BASE / "retained/v2-responses"
GUIDE = BASE / "retained/v2-guidance"


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def resolve_input(path):
    for prefix, root in (("/tmp/guardian-subscription-boundaries-candidate/", OLD),
                         ("/tmp/guardian-subscription-boundaries-v2-guidance/", GUIDE)):
        if path.startswith(prefix):
            return root / path[len(prefix):]
    raise AssertionError("Unexpected v2 consumed input: " + path)


class CurrentSubscriptionBoundaryReview(unittest.TestCase):
    def test_entire_original_review_stage_is_immutable(self):
        self.assertEqual(sha(BASE / "original-stage-manifest.json"), "e54b3abbea72c7e347ad6537b916b93b44b15377711f24d610eadbc3b318e251")
        manifest = read(BASE / "original-stage-manifest.json")
        self.assertEqual(len(manifest["files"]), 124)
        for rel, expected in manifest["files"].items():
            self.assertEqual(sha(BASE / rel), expected, rel)
        self.assertEqual(read(BASE / "verdicts.json")["case_verdicts"]["T38"]["verdict"], "failed")

    def test_new_manifests_prose_and_exact_one_paragraph_delta(self):
        self.assertEqual(sha(GUIDE / "manifest.json"), "577becfcc185e7eaa1588365a504b1146d820695783d421d8dc86232a94f8cfd")
        self.assertEqual(sha(NEW / "manifest.json"), "15e7450b1498aabbb4776bac83c60dcfd0a990bd12c286a8f96cc33ab3c1b338")
        for rel, expected in read(NEW / "manifest.json")["files"].items():
            self.assertEqual(sha(NEW / rel), expected, rel)
        self.assertEqual(sha(GUIDE / "intake.md"), "541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71")
        self.assertEqual((GUIDE / "intake.md").read_bytes(), (BASE / "proposed-guidance/intake-after.md").read_bytes())
        old = (OLD / "generator-inputs/references/intake.md").read_text(encoding="utf-8")
        new = (GUIDE / "intake.md").read_text(encoding="utf-8")
        addition = next(x for x in new.splitlines() if x.startswith("解释现有访谈辅助器的汇总时"))
        self.assertEqual(new.replace("\n" + addition + "\n", "", 1), old)
        for turn in (1, 2, 3):
            rec = read(NEW / "T38" / "response-{:02}.record.json".format(turn))
            response = NEW / "T38" / "response-{:02}.md".format(turn)
            self.assertEqual(rec["agent_response_verbatim"], response.read_text(encoding="utf-8"))
            self.assertEqual(rec["response_sha256"], sha(response))

    def test_blinded_sequential_inputs_and_current_guide_pins(self):
        deliveries = {x["turn"]: x for x in read(NEW / "controller-delivery.json")["deliveries"]}
        for turn in (1, 2, 3):
            rec = read(NEW / "T38" / "response-{:02}.record.json".format(turn))
            text = read(OLD / "generator-inputs/scenarios/T38" / "turn-{:02}.json".format(turn))["content"]
            self.assertEqual(rec["received_transcript"][-1]["content"], text)
            self.assertEqual(rec["helper_call_log"], [])
            self.assertEqual(rec["boundary_activity_log"]["helper_operations_actually_run"], [])
            for entry in rec["input_files_and_sha256"]:
                self.assertEqual(sha(resolve_input(entry["path"])), entry["sha256"])
                self.assertNotIn("/review-only/", entry["path"])
                self.assertNotIn("/guardian-subscription-boundaries-responses/", entry["path"])
                self.assertNotEqual(entry["path"], "/tmp/guardian-subscription-boundaries-candidate/generator-inputs/references/intake.md")
                if "/turn-" in entry["path"]:
                    self.assertLessEqual(int(Path(entry["path"]).stem[-2:]), turn)
                if "/attachments/" in entry["path"]:
                    self.assertEqual(turn, 3)
            if turn > 1:
                prior = NEW / "T38" / "response-{:02}.md".format(turn - 1)
                self.assertEqual(deliveries[turn]["previous_response_sha256"], sha(prior))
                self.assertIn(prior.read_text(encoding="utf-8"), [x["content"] for x in rec["received_transcript"] if x["role"] == "assistant"])
                self.assertLess(deliveries[turn - 1]["delivered_at_utc"], deliveries[turn]["delivered_at_utc"])
        for pin in read(BASE / "current-guidance-source-pins.json")["pins"]:
            self.assertTrue(pin["equal"])
            self.assertEqual(pin.get("consumed_sha256", pin.get("original_control_or_spec_sha256")), pin["current_sha256"])

    def test_exact_negative_and_report_values_stay_in_separate_subjects(self):
        first = read(NEW / "T38/response-01.record.json")["normalization_events"]
        self.assertEqual(first[8]["question_id_if_applicable"], "Q-A01")
        self.assertEqual(first[9]["question_id_if_applicable"], "Q-A02")
        self.assertEqual(first[9]["fact_state_if_recorded"], "reported")
        self.assertEqual(first[9]["value_if_recorded"], {"current_sign_in_and_verification_available": False})
        self.assertEqual(first[9]["observed_at"], "2026-10-18T10:01:00Z")
        fixture = read(OLD / "generator-inputs/attachments/T38-turn-03-supplied-report.json")
        last = read(NEW / "T38/response-03.record.json")["normalization_events"]
        self.assertEqual(last[1]["value_if_recorded"], {k: fixture["assessment"][k] for k in ("G1", "G2", "G3")})
        fact = fixture["state"]["facts"]["Q-A02"]
        self.assertEqual(last[2]["value_if_recorded"], fact["value"])
        for key in ("source", "observed_at", "subject_ref"):
            self.assertEqual(last[2][key], fact[key])
        self.assertEqual(last[2]["fact_state_if_recorded"], "reported")
        self.assertEqual(last[3]["value_if_recorded"], {"fixture_contact_phase": "PC2", "conversation_contact_phase": "PC0"})
        self.assertEqual(last[4]["value_if_recorded"], fixture["assessment"]["traffic_policy"])

    def test_new_full_prose_review_and_case_selection(self):
        annotation = read(BASE / "current-T38-claim-review.json")
        by_line = {(x["artifact"], x["line"]): x for x in annotation["claims"]}
        count = 0
        for turn in (1, 2, 3):
            rel = "retained/v2-responses/T38/response-{:02}.md".format(turn)
            for number, line in enumerate((BASE / rel).read_text(encoding="utf-8").splitlines(), 1):
                if line.strip():
                    count += 1
                    item = by_line[(rel, number)]
                    self.assertEqual(item["verbatim"], line)
                    self.assertEqual("".join(x["verbatim"] for x in item["sentences"]), line)
        self.assertEqual(count, annotation["line_review_count"])
        self.assertEqual(annotation["material_exceptions"], [])
        current = read(BASE / "current-verdicts.json")
        self.assertEqual(set(current["case_verdicts"]), {"T36", "T38", "T46", "T54"})
        self.assertTrue(current["all_current_whole_cases_supported"])
        self.assertFalse(current["ledger_promoted"])
        old = read(BASE / "verdicts.json")["case_verdicts"]
        for case, verdict in current["case_verdicts"].items():
            self.assertEqual(verdict["verdict"], "satisfied")
            self.assertEqual(verdict["verification_layer"], "L+C")
            self.assertEqual(verdict["original"], old[case]["original"])
            for rel, expected in verdict["response_files"].items():
                self.assertEqual(sha(BASE / rel), expected)
            if case != "T38":
                self.assertEqual(verdict["generation_intake_sha256"], "1d3d6f75788abafefe4a8ce8e9ca1c740b1f4b57656b350a4688c6629ac52dba")

    def test_supplemental_python310_syntax(self):
        ast.parse(Path(__file__).read_text(encoding="utf-8"), feature_version=(3, 10))

    def test_actual_package_inventory_only_changes_intake_and_excludes_evidence(self):
        proof = read(BASE / "package-inventory-proof.json")
        before = proof["inventory"]["before"]["members"]
        after = proof["inventory"]["after-a"]["members"]
        self.assertEqual(set(before), set(after))
        self.assertEqual(len(after), 63)
        self.assertEqual([name for name in sorted(before) if before[name] != after[name]],
                         ["claude-guardian/references/intake.md"])
        self.assertEqual(proof["inventory"]["after-a"]["archive_sha256"],
                         proof["inventory"]["after-b"]["archive_sha256"])
        self.assertTrue(proof["after_reproducible"])
        self.assertFalse(proof["evidence_in_installed_package"])
        self.assertFalse(any("/evidence/" in name or "/tests/" in name or "subscription-boundaries" in name for name in after))
        trees = proof["complete_active_skill_inventory"]
        self.assertEqual(set(trees["before"]), set(trees["after"]))
        self.assertEqual([name for name in sorted(trees["before"]) if trees["before"][name] != trees["after"][name]],
                         ["references/intake.md"])


if __name__ == "__main__":
    unittest.main()
