"""Behavioral tests: offline/mocked branches, never native-platform certification."""
import copy
from datetime import datetime, timedelta, timezone
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
SCRIPT = ROOT / "skills/claude-guardian/scripts/guardian.py"
spec = importlib.util.spec_from_file_location("guardian", SCRIPT)
g = importlib.util.module_from_spec(spec)
spec.loader.exec_module(g)


def fixture():
    obj = json.loads((ROOT / "tests/fixtures/proxy-port-conflict.json").read_text())
    for fact in obj["facts"]:
        fact["observed_at"] = datetime.now(timezone.utc).isoformat()
    return obj


class OfflineTests(unittest.TestCase):
    def test_conflict_plan_is_preview(self):
        r = g.analyze(fixture(), "device-1", True)
        self.assertEqual(r["plan"]["diff"][0]["before"], 7890)
        self.assertEqual(r["plan"]["diff"][0]["proposed_after"], 7897)
        self.assertFalse(r["plan"]["executable"])
        self.assertEqual(r["changes"], [])
        self.assertEqual(r["contact_control"]["gate_state"], "closed")
        self.assertEqual(r["check_status"], "unknown")

    def test_target_mismatch(self):
        with self.assertRaisesRegex(g.GuardianError, "TARGET_NOT_BOUND"):
            g.analyze(fixture(), "different-device")

    def test_fact_context_mismatch(self):
        obj = fixture(); obj["facts"][0]["context_ref"] = "other"
        with self.assertRaisesRegex(g.GuardianError, "TARGET_NOT_BOUND"):
            g.analyze(obj, "device-1")

    def test_context_mismatch(self):
        for key, value in [("desktop_user_relation", "different"), ("filesystem_namespace", "sandbox"), ("execution_location", "cloud")]:
            with self.subTest(key=key):
                obj = fixture(); obj["target_binding"][key] = value
                with self.assertRaisesRegex(g.GuardianError, "TARGET_USER_CONTEXT_MISMATCH"):
                    g.analyze(obj, "device-1")

    def test_precontact_rejects_open_gate(self):
        for key, val in [("contact_phase", "contact"), ("gate_state", "open"), ("operation", "probe"), ("url", "https://claude.ai"), ("command", "echo x")]:
            with self.subTest(key=key):
                obj = fixture(); obj[key] = val
                with self.assertRaisesRegex(g.GuardianError, "PRECONTACT_ACTION_REJECTED"):
                    g.analyze(obj, "device-1")

    def test_stale_facts_never_create_diff(self):
        obj = fixture()
        obj["facts"][1]["observed_at"] = (datetime.now(timezone.utc) - timedelta(days=2)).isoformat()
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["plan"]["diff"], [])
        self.assertIn("P06", r["missing_fields"])

    def test_future_clock_is_stale(self):
        obj = fixture(); obj["facts"][1]["observed_at"] = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
        self.assertEqual(g.analyze(obj, "device-1")["facts"][1]["state"], "stale")

    def test_missing_not_pass(self):
        obj = fixture(); obj["facts"] = []
        r = g.analyze(obj, "device-1", True)
        self.assertTrue(r["missing_fields"])
        self.assertEqual(r["check_status"], "unknown")
        self.assertEqual(r["plan"]["diff"], [])
        self.assertEqual(r["limits"]["endpoints"], "unconfigured")

    def test_unknown_not_false(self):
        obj = fixture(); obj["facts"][1].update(state="unknown", value=None)
        self.assertEqual(g.analyze(obj, "device-1", True)["plan"]["diff"], [])

    def test_disabled_system_proxy_is_not_fault(self):
        obj = fixture(); obj["facts"][1]["value"]["enabled"] = False
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["plan"]["diff"], [])
        self.assertNotIn("PROXY_PORT_ASSOCIATION_CONFLICT", str(r["findings"]))

    def test_reported_not_observed(self):
        obj = fixture(); obj["facts"][1]["state"] = "reported"
        self.assertEqual(g.analyze(obj, "device-1", True)["plan"]["diff"], [])

    def test_static_not_runtime(self):
        obj = fixture(); obj["facts"][2]["layer"] = "static_file"
        self.assertEqual(g.analyze(obj, "device-1", True)["plan"]["diff"], [])

    def test_changed_snapshot_prevents_diff(self):
        obj = fixture(); obj["snapshot_state"] = "changed"
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["plan"]["diff"], [])
        self.assertIn("SNAPSHOT_CHANGED_DURING_AUDIT", str(r["findings"]))

    def test_cancel_stops_analysis(self):
        obj = fixture(); obj["cancelled"] = True
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["execution_status"], "interrupted")
        self.assertNotIn("plan", r)
        self.assertEqual(r["facts"], [])

    def test_invalid_schema_unknown_key_and_duplicates(self):
        for change in [lambda o: o.update(schema_version="bogus"), lambda o: o.update(raw_secrets="x"), lambda o: o["facts"].append(copy.deepcopy(o["facts"][0]))]:
            obj = fixture(); change(obj)
            with self.assertRaises(g.GuardianError):
                g.analyze(obj, "device-1")

    def test_ports_and_booleans_strict(self):
        for val in [0, 65536, True, "7890"]:
            obj = fixture(); obj["facts"][1]["value"]["port"] = val
            with self.assertRaises(g.GuardianError):
                g.analyze(obj, "device-1")

    def test_observed_proxy_scalar_rejected(self):
        for value in (None, 123, True, "proxy"):
            for index in (1, 2):
                obj = fixture(); obj["facts"][index]["value"] = value
                with self.assertRaisesRegex(g.GuardianError, "INPUT_OR_RESPONSE_INVALID"):
                    g.analyze(obj, "device-1", True)

    def test_missing_route_prevents_configuration_readiness(self):
        obj = fixture(); obj["facts"] = obj["facts"][:3]
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["inventory_readiness"], "partial")
        self.assertEqual(r["plan"]["diff"], [])

    def test_unknown_snapshot_prevents_configuration_readiness(self):
        obj = fixture(); obj["snapshot_state"] = "unknown"
        r = g.analyze(obj, "device-1", True)
        self.assertEqual(r["inventory_readiness"], "partial")
        self.assertEqual(r["plan"]["diff"], [])

    def test_no_secret_structures(self):
        obj = fixture(); obj["facts"][0]["value"] = {"token": "secret-sentinel"}
        with self.assertRaises(g.GuardianError):
            g.analyze(obj, "device-1")

    def test_redaction(self):
        value = {"secret": "secret-sentinel", "text": "IP 203.0.113.42 IPv6 2001:db8::42 user /Users/Alice/private token=abc123", "other": "C:\\Users\\Alice\\Secrets", "url": "https://example.com?key=secret", "bearer": "Bearer abcdef", "generic": "alice@example.com /tmp/private-config.json"}
        output = json.dumps(g.redact(value))
        for raw in ["secret-sentinel", "203.0.113.42", "2001:db8::42", "Alice", "abc123", "abcdef", "example.com", "private-config", "alice@"]:
            self.assertNotIn(raw, output)


class InterviewTests(unittest.TestCase):
    def test_subscription_first(self):
        self.assertEqual(g.interview({})["question"]["id"], "Q-J01")

    def test_known_first_subscription_skips_old_subscription(self):
        r = g.interview({"answers": {"subscription_stage": "first_subscription"}})
        self.assertEqual(r["question"]["field"], "os")

    def test_existing_subscriber_task(self):
        r = g.interview({"answers": {"subscription_stage": "existing_subscriber"}})
        self.assertEqual(r["question"]["field"], "current_task")

    def test_environment_route_skips_purchase(self):
        answers = {"subscription_stage": "existing_subscriber", "current_task": "environment", "os": "macos", "usage": "web"}
        self.assertEqual(g.interview({"answers": answers})["question"]["field"], "account_status")

    def test_incident_overrides_subscription_question(self):
        r = g.interview({"answers": {"account_status": "suspended"}})
        self.assertNotIn("question", r)
        self.assertIn("INCIDENT_PRIORITY", str(r["findings"]))

    def test_cancel_is_not_permission(self):
        r = g.interview({"cancelled": True})
        self.assertEqual(r["execution_status"], "interrupted")
        self.assertEqual(r["contact_control"]["gate_state"], "closed")

    def test_invalid_interview_state(self):
        with self.assertRaises(g.GuardianError):
            g.interview({"answers": {"owns_account": True}})


class FileAndCLITests(unittest.TestCase):
    def run_cli(self, *args, cwd=None):
        return subprocess.run([sys.executable, str(SCRIPT), *args], cwd=cwd, capture_output=True, text=True, timeout=10, env=dict(os.environ, PYTHONDONTWRITEBYTECODE="1"))

    def test_interview_smoke_no_persistence(self):
        with tempfile.TemporaryDirectory() as d:
            result = self.run_cli("interview", cwd=d)
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["question"]["id"], "Q-J01")
            self.assertEqual(list(Path(d).iterdir()), [])

    def test_interview_report_round_trip(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "state.json"
            first = self.run_cli("interview", "--input", str(ROOT / "tests/fixtures/interview-first.json"), "--output", str(output))
            second = self.run_cli("interview", "--input", str(output))
            self.assertEqual(first.returncode, 0)
            self.assertEqual(second.returncode, 0)
            self.assertEqual(json.loads(first.stdout)["question"], json.loads(second.stdout)["question"])

    def test_fixture_cli_smoke(self):
        result = self.run_cli("analyze", "--target-ref", "device-1", "--input", str(ROOT / "tests/fixtures/proxy-port-conflict.json"))
        self.assertEqual(result.returncode, 0)
        self.assertEqual(json.loads(result.stdout)["record_kind"], "synthetic_example")

    def test_missing_file_structured_error(self):
        result = self.run_cli("analyze", "--target-ref", "device-1", "--input", "/no/such/file")
        self.assertEqual(result.returncode, 2)
        self.assertIn("INPUT_OR_RESPONSE_INVALID", result.stdout)
        self.assertNotIn("/no/such/file", result.stdout)

    def test_linux_cannot_claim_mac(self):
        args = g.parser().parse_args(["check", "--target-ref", "device-1", "--target-os", "macos", "--confirm-target", "--authorize-audit", "--namespace", "desktop", "--execution-location", "native_local", "--user-context", "same"])
        with patch.object(g.sys, "platform", "linux"):
            with self.assertRaisesRegex(g.GuardianError, "TARGET_USER_CONTEXT_MISMATCH"):
                g.native_check(args)

    def test_authorization_required_before_collection(self):
        args = g.parser().parse_args(["check", "--target-ref", "device-1", "--target-os", "macos", "--confirm-target"])
        with self.assertRaisesRegex(g.GuardianError, "AUTHORIZATION_MISSING"):
            g.native_check(args)

    def test_mocked_native_report_to_analysis_and_plan(self):
        # Mocking macOS dispatch on Linux verifies control flow, NOT native API validity.
        args = g.parser().parse_args(["check", "--target-ref", "device-1", "--target-os", "macos", "--confirm-target", "--authorize-audit", "--namespace", "desktop", "--execution-location", "native_local", "--user-context", "same"])
        with patch.object(g.sys, "platform", "darwin"):
            report = g.native_check(args)
        for planning in (False, True):
            result = g.analyze(copy.deepcopy(report), "device-1", planning)
            self.assertEqual(len(result["facts"]), 3)
            self.assertEqual(result["facts"][1]["reason_code"], "KERNEL_VERSION_ONLY")
            self.assertEqual(result["facts"][1]["coverage"], "current_process_os")
            self.assertEqual(result["limits"]["native_platform_validation"], "not_run")
            self.assertEqual(result["contact_control"]["gate_state"], "closed")
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "audit.json"; p.write_text(json.dumps(report))
            result = self.run_cli("plan", "--target-ref", "device-1", "--input", str(p))
            self.assertEqual(result.returncode, 0)
            self.assertEqual(json.loads(result.stdout)["plan"]["diff"], [])

    def test_inventory_open_gate_rejected(self):
        report = g.base("audit", "device-1")
        report["schema_version"] = "env-inventory/0.2"
        report["contact_control"]["gate_state"] = "open"
        with self.assertRaisesRegex(g.GuardianError, "PRECONTACT_ACTION_REJECTED"):
            g.analyze(report, "device-1")

    def test_confirmation_required(self):
        args = g.parser().parse_args(["check", "--target-ref", "device-1", "--target-os", "macos", "--authorize-audit"])
        with self.assertRaisesRegex(g.GuardianError, "TARGET_NOT_BOUND"):
            g.native_check(args)

    def test_explicit_save_and_no_overwrite(self):
        with tempfile.TemporaryDirectory() as d:
            output = Path(d) / "report.json"
            first = self.run_cli("interview", "--output", str(output))
            self.assertEqual(first.returncode, 0)
            content = output.read_text()
            second = self.run_cli("interview", "--output", str(output))
            self.assertEqual(second.returncode, 3)
            self.assertEqual(output.read_text(), content)
            self.assertIn("OUTPUT_SAVE_FAILED", second.stdout)
            if os.name != "nt":
                self.assertEqual(output.stat().st_mode & 0o777, 0o600)

    def test_bad_json_and_duplicate_keys(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "input.json"
            for value in ['{"x":1,"x":2}', '{', '{"x":NaN}']:
                p.write_text(value)
                with self.assertRaises(g.GuardianError):
                    g.load_json(p)

    def test_file_budget(self):
        with tempfile.TemporaryDirectory() as d:
            p = Path(d) / "big.json"; p.write_text("x" * (g.MAX_BYTES + 1))
            with self.assertRaisesRegex(g.GuardianError, "BUDGET_EXCEEDED"):
                g.load_json(p)

    def test_symlinks_rejected(self):
        with tempfile.TemporaryDirectory() as d:
            target = Path(d) / "input.json"; target.write_text("{}")
            link = Path(d) / "link.json"
            try:
                link.symlink_to(target)
            except OSError:
                self.skipTest("symlink creation unavailable")
            with self.assertRaisesRegex(g.GuardianError, "UNSAFE_OR_OFFLINE_PATH"):
                g.load_json(link)
            with self.assertRaisesRegex(g.GuardianError, "UNSAFE_OR_OFFLINE_PATH"):
                g.save_new(link, "new")
            self.assertEqual(target.read_text(), "{}")

    def test_no_mutation_or_network_commands(self):
        for command in ["apply", "probe", "rollback", "cleanup", "login"]:
            self.assertEqual(self.run_cli(command).returncode, 2)


if __name__ == "__main__":
    unittest.main()
