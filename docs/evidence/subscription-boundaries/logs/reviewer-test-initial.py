"""Integrity/control regressions, not regenerated prose or all-case acceptance.

Uses explicit UTF-8 and Python 3.10-compatible standard-library interfaces.
The original T38 failure is deliberately retained and asserted as a failure.
"""
import ast
import builtins
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import socket
import subprocess
import sys
import unittest

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
C = BASE / "retained/candidate"
R = BASE / "retained/responses"
CASES = {"T36": 2, "T38": 3, "T46": 3, "T54": 2}


def read(path):
    return json.loads(path.read_text(encoding="utf-8"))


def sha(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def record(case, turn):
    stem = "record-{:02}.json" if case == "T36" else "response-{:02}.record.json" if case == "T38" else "evidence-{:02}.json"
    return read(R / case / stem.format(turn))


def retained_path(original):
    for prefix, root in (("/tmp/guardian-subscription-boundaries-candidate/", C),
                         ("/tmp/guardian-subscription-boundaries-responses/", R)):
        if original.startswith(prefix):
            return root / original[len(prefix):]
    raise AssertionError("Unexpected consumed source: " + original)


def load_runner():
    spec = importlib.util.spec_from_file_location("boundary_reviewer_control_runner", BASE / "reviewer-controls/replay.py")
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


class RetainedSubscriptionBoundaryEvidence(unittest.TestCase):
    def test_frozen_manifest_and_every_payload(self):
        self.assertEqual(sha(C / "manifest.json"), "177c0a336fed5d093761ee56f9fdc546edca10211b7bd0efcbb98d494fdf80dd")
        manifest = read(C / "manifest.json")
        self.assertEqual(len(manifest["payloads"]), 43)
        for entry in manifest["payloads"]:
            self.assertEqual(sha(C / entry["path"]), entry["sha256"], entry["path"])
            self.assertEqual((C / entry["path"]).stat().st_size, entry["size_bytes"])
        self.assertEqual(sha(C / "review-only/prior-observations/manifest.json"), manifest["prior_trace_pins"]["manifest.json"])

    def test_actual_response_manifest_and_verbatim_records(self):
        self.assertEqual(sha(R / "manifest.json"), "afbfc9a1ab842f8978c4924bc37bc0a15cd2ac731768e4ea24cc249f567e5c35")
        manifest = read(R / "manifest.json")
        self.assertEqual(len(manifest["files"]), 25)
        for rel, expected in manifest["files"].items():
            self.assertEqual(sha(R / rel), expected, rel)
        for case, count in CASES.items():
            for turn in range(1, count + 1):
                text = (R / case / "response-{:02}.md".format(turn)).read_text(encoding="utf-8")
                self.assertEqual(record(case, turn)["agent_response_verbatim"], text)

    def test_staged_inputs_and_retained_prior_responses(self):
        deliveries = {(x["case"], x["turn"]): x for x in read(R / "controller-delivery.json")["deliveries"]}
        self.assertEqual(len(deliveries), 10)
        for case, count in CASES.items():
            prior_times = []
            for turn in range(1, count + 1):
                rec = record(case, turn)
                current = read(C / "generator-inputs/scenarios" / case / "turn-{:02}.json".format(turn))
                self.assertEqual(rec["received_transcript"][-1]["content"], current["content"])
                for source in rec["input_files_and_sha256"]:
                    self.assertEqual(sha(retained_path(source["path"])), source["sha256"])
                    self.assertNotIn("/review-only/", source["path"])
                    if "/scenarios/" in source["path"] and "/turn-" in source["path"]:
                        self.assertIn("/" + case + "/", source["path"])
                        self.assertLessEqual(int(Path(source["path"]).stem[-2:]), turn)
                    if "/attachments/" in source["path"]:
                        self.assertEqual((case, turn), ("T38", 3))
                prior_times.append(deliveries[(case, turn)]["delivered_at_utc"])
                if turn > 1:
                    previous = R / case / "response-{:02}.md".format(turn - 1)
                    self.assertEqual(deliveries[(case, turn)]["previous_response_sha256"], sha(previous))
                    self.assertIn({"role": "assistant", "content": previous.read_text(encoding="utf-8")},
                                  [{"role": x["role"], "content": x["content"]} for x in rec["received_transcript"]])
            self.assertEqual(prior_times, sorted(prior_times))

    def test_original_rows_layers_and_current_pin_comparison(self):
        clauses = read(C / "review-only/original-clauses.json")["cases"]
        spec_lines = (C / "review-only/sources/D-SPEC-v0.1.10.md").read_text(encoding="utf-8").splitlines()
        tracker_lines = (C / "review-only/sources/implementation-tracker.md").read_text(encoding="utf-8").splitlines()
        for clause in clauses:
            self.assertEqual(spec_lines[clause["design_line_number"] - 1], clause["design_line_verbatim"])
            self.assertEqual(tracker_lines[clause["tracker_line_number"] - 1], clause["tracker_line_verbatim"])
            self.assertEqual(clause["ledger_row_verbatim_object"]["verification_layer"], "L+C")
            self.assertEqual(clause["ledger_row_verbatim_object"]["rebuild_acceptance"], "pending_revalidation")
        comparison = read(BASE / "source-comparison.json")
        self.assertEqual([x["relative_path"] for x in comparison["source_comparisons"] if not x["equal"]],
                         ["docs/acceptance-rebuild-ledger.json"])
        self.assertTrue(all(comparison["original_rows_unchanged"].values()))

    def test_host_events_keep_negative_unknown_and_declined_distinct(self):
        t36 = record("T36", 2)["normalization_events"]
        self.assertEqual([(t36[i]["question_id_if_applicable"], t36[i]["fact_state_if_recorded"], t36[i]["value_if_recorded"])
                          for i in (1, 2, 3)], [("Q-A01", "reported", "iPhone"), ("Q-A02", "unknown", None), ("Q-A03", "unknown", None)])
        negative = record("T38", 1)["normalization_events"][2]
        self.assertEqual(negative["fact_state_if_recorded"], "reported")
        self.assertEqual(negative["value_if_recorded"], {"currently_usable_sign_in_and_verification": False})
        refused = record("T46", 1)["normalization_events"][8]
        self.assertEqual((refused["question_id_if_applicable"], refused["fact_state_if_recorded"], refused["value_if_recorded"]), ("Q-C09", "declined", None))
        t54 = record("T54", 1)["normalization_events"]
        self.assertEqual(t54[8]["fact_state_if_recorded"], "reported")
        self.assertEqual(t54[8]["value_if_recorded"], {"sign_in_and_verification_available": False})
        self.assertEqual((t54[9]["fact_state_if_recorded"], t54[9]["value_if_recorded"]), ("unknown", None))
        self.assertEqual((t54[10]["fact_state_if_recorded"], t54[10]["value_if_recorded"]), ("declined", None))

    def test_no_fabricated_respondent_helper_calls_or_live_fixture_import(self):
        for case, count in CASES.items():
            for turn in range(1, count + 1):
                self.assertEqual(record(case, turn)["helper_call_log"], [])
                self.assertEqual(record(case, turn)["boundary_activity_log"]["helper_operations_actually_run"], [])
        supplied = read(C / "generator-inputs/attachments/T38-turn-03-supplied-report.json")
        old = read(C / "review-only/prior-observations/outputs.json")["T38_negative_report"]
        self.assertEqual(supplied, old)
        self.assertEqual(record("T38", 3)["supplied_external_attachments"]["report"], supplied)
        self.assertEqual(supplied["assessment"]["G1"]["status"], "complete")
        self.assertEqual(supplied["assessment"]["G2"], {"status": "pass", "conditional_plan_only": False})
        self.assertEqual(supplied["assessment"]["G3"]["status"], "blocked")

    def test_every_retained_response_line_and_sentence_reviewed(self):
        annotations = read(BASE / "claim-review.json")
        found = {(x["artifact"], x["line"]): x for x in annotations["claims"]}
        count = 0
        for case, turns in CASES.items():
            for turn in range(1, turns + 1):
                rel = case + "/response-{:02}.md".format(turn)
                for number, line in enumerate((R / rel).read_text(encoding="utf-8").splitlines(), 1):
                    if line.strip():
                        count += 1
                        item = found[(rel, number)]
                        self.assertEqual(item["verbatim"], line)
                        self.assertEqual("".join(x["verbatim"] for x in item["sentences"]), line)
        self.assertEqual(count, annotations["line_review_count"])
        self.assertEqual(len(found), count)

    def test_semantic_failure_is_retained_not_promoted(self):
        verdict = read(BASE / "verdicts.json")
        self.assertEqual({k: v["verdict"] for k, v in verdict["case_verdicts"].items()},
                         {"T36": "satisfied", "T38": "failed", "T46": "satisfied", "T54": "satisfied"})
        self.assertFalse(verdict["case_verdicts"]["T38"]["runtime_bug_demonstrated"])
        self.assertFalse(verdict["case_verdicts"]["T38"]["execution_or_contact_failure_demonstrated"])
        self.assertTrue(all(not x["acceptance_promoted"] for x in verdict["case_verdicts"].values()))

    def test_separate_fresh_controls_preserve_exact_results_and_gates(self):
        fresh = load_runner().replay()
        retained = read(BASE / "reviewer-controls/actual-control-report.json")
        self.assertEqual(fresh["outputs"], retained["outputs"])
        self.assertEqual(fresh["calls"], retained["calls"])
        self.assertFalse(fresh["respondent_calls"])
        self.assertFalse(fresh["model_prose_generated"])
        self.assertEqual(fresh["call_count"], 15)
        self.assertEqual(fresh["blocked_io_attempts"], [])
        negative = fresh["outputs"]["T38_negative_report"]
        self.assertEqual(negative["state"]["facts"]["Q-A02"]["state"], "reported")
        self.assertEqual(negative["state"]["facts"]["Q-A02"]["value"]["sign_in_and_verification"], "reported_unavailable")
        self.assertEqual(negative["assessment"]["G2"], {"status": "pass", "conditional_plan_only": False})
        for name, qid, state in (("T46_region_refusal", "Q-C09", "declined"), ("T54_unknown_storefront_draft", "Q-A03", "unknown")):
            item = fresh["outputs"][name]
            self.assertEqual(item["state"]["facts"][qid]["state"], state)
            self.assertIsNone(item["state"]["facts"][qid]["value"])
            self.assertEqual(item["assessment"]["G2"], {"status": "blocked", "conditional_plan_only": True})
        for item in fresh["outputs"].values():
            self.assertEqual(item["assessment"]["G3"]["status"], "blocked")
            self.assertEqual(item["next_questions_three_repeats"], [None, None, None])

    def test_no_io_guard_fails_fast_on_representative_entrypoints(self):
        runner = load_runner()
        module = runner.load()
        attempts = []
        with runner.no_io(module, "2026-10-18T09:10:00Z", attempts):
            for call in (lambda: builtins.open("not-accessed"), lambda: io.open("not-accessed"),
                         lambda: os.open("not-accessed", os.O_RDONLY), lambda: Path("not-accessed").open(),
                         lambda: socket.socket(), lambda: socket.getaddrinfo("not-accessed.invalid", 80),
                         lambda: subprocess.run(["not-executed"]), lambda: os.system("not-executed")):
                with self.assertRaisesRegex(AssertionError, "Reviewer pure-call I/O denied"):
                    call()
        self.assertEqual(len(attempts), 8)

    def test_python310_syntax_and_explicit_utf8_artifacts(self):
        for path in (BASE / "reviewer-controls/replay.py", Path(__file__)):
            ast.parse(path.read_text(encoding="utf-8"), filename=path.name, feature_version=(3, 10))
        for path in BASE.rglob("*.json"):
            read(path)


if __name__ == "__main__":
    unittest.main()
