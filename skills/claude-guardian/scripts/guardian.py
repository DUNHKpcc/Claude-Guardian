#!/usr/bin/env python3
"""Claude-Guardian diagnostic preview. Python stdlib; no network or mutation executor.

This compact contract is reconstructed from ENV-SPEC v0.3 sections 18–20;
it is not the missing historical ENV01_ENV02_Contracts_v0.2.zip.
"""
import argparse
from datetime import datetime, timezone
import ipaddress
import json
import os
from pathlib import Path
import re
import stat
import sys
import time

VERSION = "0.1.0-diagnostic-preview"
INPUT_SCHEMA = "guardian-offline/0.1"
STATES = {"observed", "reported", "derived", "unknown", "blocked", "not_applicable", "not_found_in_scope", "conflict", "stale"}
FACT_IDS = {"H%02d" % n for n in range(1, 8)} | {"S%02d" % n for n in range(1, 17)} | {"P%02d" % n for n in range(1, 25)}
MAX_BYTES = 262144
MAX_AGE = 86400
ALIAS = re.compile(r"[A-Za-z][A-Za-z0-9_-]{0,47}\Z")
SECRET = re.compile(r"(?i)(?:bearer\s+\S+|(?:sk-|ghp_|github_pat_)[A-Za-z0-9_-]+|(?:password|secret|token|api[_-]?key|authorization)\s*[:=]\s*\S+)")
MODULES = ["ENV-%02d" % n for n in range(1, 11)]


class GuardianError(Exception):
    def __init__(self, code, exit_code=2):
        self.code, self.exit_code = code, exit_code


def now():
    return datetime.now(timezone.utc).isoformat()


def alias(value):
    if not isinstance(value, str) or not ALIAS.fullmatch(value):
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    return value


def redact(value):
    """Defense in depth. Raw configuration, credentials and addresses are never needed."""
    if isinstance(value, dict):
        return {k: ("[redacted]" if re.search(r"(?i)password|secret|token|authorization|cookie|credential|api.?key", k) else redact(v)) for k, v in value.items()}
    if isinstance(value, list):
        return [redact(v) for v in value]
    if not isinstance(value, str):
        return value
    value = SECRET.sub("[redacted]", value)
    value = re.sub(r"https?://\S+", "[url-redacted]", value)
    value = re.sub(r"(?:[A-Za-z]:[\\/]|/Users/|/home/|/private/|\\\\)[^\r\n,;]*", "[path-redacted]", value)
    value = re.sub(r"(?<![A-Za-z0-9])/(?:[^\s,;]+)", "[path-redacted]", value)
    value = re.sub(r"[A-Za-z0-9_.+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", "[email-redacted]", value)
    value = re.sub(r"\b(?:\d{1,3}\.){3}\d{1,3}\b", "[address-redacted]", value)
    # Replace IPv6 candidates only when they parse as addresses (timestamps survive).
    def ipv6(match):
        try:
            ipaddress.IPv6Address(match.group(0).split("%", 1)[0])
            return "[address-redacted]"
        except ValueError:
            return match.group(0)
    return re.sub(r"[0-9A-Fa-f:]*:[0-9A-Fa-f:]+(?:%[A-Za-z0-9]+)?", ipv6, value)


def load_json(path):
    # No recursive discovery, symlinks, devices, UNC paths or oversized input.
    if str(path).startswith(("\\\\", "//")):
        raise GuardianError("UNSAFE_OR_OFFLINE_PATH")
    p = Path(path)
    try:
        if any(part.is_symlink() for part in [p, *p.parents]):
            raise GuardianError("UNSAFE_OR_OFFLINE_PATH")
        st = p.stat()
        if not stat.S_ISREG(st.st_mode) or st.st_size > MAX_BYTES:
            raise GuardianError("BUDGET_EXCEEDED")
        with p.open("rb") as stream:
            data = stream.read(MAX_BYTES + 1)
        if len(data) > MAX_BYTES:
            raise GuardianError("BUDGET_EXCEEDED")
        def unique(pairs):
            result = {}
            for key, val in pairs:
                if key in result:
                    raise ValueError("duplicate")
                result[key] = val
            return result
        obj = json.loads(data, object_pairs_hook=unique, parse_constant=lambda _: (_ for _ in ()).throw(ValueError("nonfinite")))
        if not isinstance(obj, dict):
            raise ValueError("object required")
        return obj
    except GuardianError:
        raise
    except (OSError, ValueError, UnicodeError, RecursionError):
        raise GuardianError("INPUT_OR_RESPONSE_INVALID") from None


def base(operation, target_ref=None):
    return {
        "schema_version": "guardian-report/0.1", "runtime_version": VERSION,
        "contract_provenance": "reconstructed_from_spec_not_historical_zip",
        "record_kind": "offline_analysis", "operation": operation,
        "module_ids": ["M00"] if operation == "interview" else MODULES,
        "run_ref": "run-preview", "target_ref": target_ref,
        "target_binding": {"binding_state": "needs_confirmation"},
        "contact_control": {"contact_phase": "precontact", "gate_state": "closed", "pc_g1": "not_verified", "pc_g2": "not_run"},
        "execution_status": "completed", "check_status": "unknown", "inventory_readiness": "partial",
        "facts": [], "evidence": [], "findings": [], "missing_fields": [],
        "not_tested": ["ENV-03: live IP/ASN/path tests", "ENV-04: DNS/IPv6/UDP", "ENV-05: browser/WebRTC", "ENV-07: real clients and subprocesses", "ENV-09: cleanup", "ENV-10: failure/rollback validation"],
        "next_actions": [], "changes": [],
        "privacy": {"shareable": False, "redacted_preview": True, "review_before_sharing": True, "raw_input_echoed": False, "selected_input_values_included": True, "persistence": "none_unless_output_requested"},
        "snapshot": {"observed_at": now(), "clock_externally_verified": False},
        "limits": {"collector_external_network": "forbidden", "endpoints": "unconfigured", "native_platform_validation": "not_run", "environment_pass_claim": False, "account_safety_guarantee": False},
    }


def finding(report, code, module="ENV-01"):
    report["findings"].append({"code": code, "module_id": module})


def contact_guard(obj):
    if obj.get("contact_phase", "precontact") != "precontact" or obj.get("gate_state", "closed") != "closed":
        raise GuardianError("PRECONTACT_ACTION_REJECTED", 3)
    if obj.get("operation") in {"probe", "apply", "rollback", "cleanup", "login", "open_claude", "pay"}:
        raise GuardianError("PRECONTACT_ACTION_REJECTED", 3)
    if any(key in obj for key in ("command", "script", "url", "endpoints", "controller", "credentials")):
        raise GuardianError("PRECONTACT_ACTION_REJECTED", 3)


def validate_offline(obj, target):
    contact_guard(obj)
    allowed = {"schema_version", "target_ref", "target_binding", "record_kind", "contact_phase", "gate_state", "facts", "cancelled", "snapshot_state"}
    if set(obj) - allowed or obj.get("schema_version") != INPUT_SCHEMA:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    if obj.get("target_ref") != target:
        raise GuardianError("TARGET_NOT_BOUND", 3)
    if obj.get("record_kind") not in {"synthetic_example", "user_supplied_observation"}:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    binding = obj.get("target_binding", {})
    if not isinstance(binding, dict) or set(binding) - {"declared_os", "desktop_user_relation", "filesystem_namespace", "execution_location"}:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    if binding.get("declared_os") not in {"macos", "windows"}:
        raise GuardianError("UNSUPPORTED_PRODUCT_OR_VERSION")
    if binding.get("desktop_user_relation") != "same" or binding.get("filesystem_namespace") != "host_desktop" or binding.get("execution_location") != "native_local":
        raise GuardianError("TARGET_USER_CONTEXT_MISMATCH", 3)
    if "cancelled" in obj and type(obj["cancelled"]) is not bool:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    facts = obj.get("facts", [])
    if not isinstance(facts, list) or len(facts) > 64:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    seen = set()
    for fact in facts:
        if not isinstance(fact, dict) or set(fact) - {"id", "value", "state", "context_ref", "observed_at", "layer", "source_ref", "reason_code", "coverage"}:
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        if fact.get("id") not in FACT_IDS or fact["id"] in seen or fact.get("state") not in STATES:
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        seen.add(fact["id"])
        if fact.get("context_ref") != target:
            raise GuardianError("TARGET_NOT_BOUND", 3)
        if fact.get("layer") not in {"reported", "os_query", "static_file", "runtime", "derived"}:
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        alias(fact.get("source_ref"))
        for qualifier in ("reason_code", "coverage"):
            if qualifier in fact:
                alias(fact[qualifier])
        try:
            stamp = datetime.fromisoformat(fact["observed_at"].replace("Z", "+00:00"))
            if stamp.tzinfo is None:
                raise ValueError("timezone required")
            age = (datetime.now(timezone.utc) - stamp).total_seconds()
        except (KeyError, TypeError, ValueError, AttributeError):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID") from None
        if age > MAX_AGE or age < -300:
            fact["state"] = "stale"
        # Restrict useful semantic structures; unknown keys do not become secret channels.
        if fact["id"] in {"P06", "P09"} and (isinstance(fact.get("value"), dict) or fact["state"] in {"observed", "reported"}):
            val = fact.get("value")
            keys = {"enabled", "port"} if fact["id"] == "P06" else {"selected_instance_port", "port_owner_matches"}
            if not isinstance(val, dict) or set(val) != keys:
                raise GuardianError("INPUT_OR_RESPONSE_INVALID")
            port = val.get("port", val.get("selected_instance_port"))
            flag = val.get("enabled", val.get("port_owner_matches"))
            if type(port) is not int or not 1 <= port <= 65535 or type(flag) is not bool:
                raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        elif isinstance(fact.get("value"), (dict, list)):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        elif not isinstance(fact.get("value"), (str, bool, int, type(None))):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        elif isinstance(fact.get("value"), str) and len(fact["value"]) > 256:
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        if fact["state"] in {"observed", "reported"}:
            if fact["id"] == "S01" and fact.get("value") not in {"macos", "windows"}:
                raise GuardianError("INPUT_OR_RESPONSE_INVALID")
            if fact["id"] == "P11" and fact.get("value") not in {"rule", "global", "direct"}:
                raise GuardianError("INPUT_OR_RESPONSE_INVALID")
            if fact["id"] == "P12" and type(fact.get("value")) is not bool:
                raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    return obj


def inventory_to_offline(obj):
    """Accept this release's minimal native audit as offline evidence, never a gate pass."""
    if obj.get("operation") != "audit" or obj.get("changes") != [] or obj.get("execution_status") != "completed":
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    contact = obj.get("contact_control", {})
    if not isinstance(contact, dict):
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    contact_guard(contact)
    binding = obj.get("target_binding", {})
    if not isinstance(binding, dict) or not isinstance(obj.get("facts"), list):
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    facts = []
    for fact in obj["facts"]:
        if not isinstance(fact, dict):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        sources = fact.get("source_refs", [])
        if not isinstance(sources, list) or not sources:
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        facts.append({key: fact.get(key) for key in ("id", "value", "state", "context_ref", "observed_at", "layer")})
        facts[-1]["source_ref"] = sources[0]
        for qualifier in ("reason_code", "coverage"):
            if qualifier in fact:
                facts[-1][qualifier] = fact[qualifier]
    return {"schema_version": INPUT_SCHEMA, "record_kind": "user_supplied_observation", "target_ref": obj.get("target_ref"), "target_binding": {key: binding.get(key) for key in ("declared_os", "desktop_user_relation", "filesystem_namespace", "execution_location")}, "contact_phase": "precontact", "gate_state": "closed", "snapshot_state": "unknown", "facts": facts}


def analyze(obj, target, planning=False):
    if obj.get("schema_version") == "env-inventory/0.2":
        obj = inventory_to_offline(obj)
    obj = validate_offline(obj, target)
    report = base("plan" if planning else "analyze", target)
    report["record_kind"] = obj["record_kind"]
    report["target_binding"] = dict(obj["target_binding"], binding_state="supplied_not_independently_verified")
    if obj.get("cancelled"):
        report.update(execution_status="interrupted", inventory_readiness="interrupted")
        finding(report, "USER_CANCELLED")
        return report
    report["facts"] = obj.get("facts", [])
    index = {f["id"]: f for f in report["facts"]}
    report["missing_fields"] = [f for f in ["S01", "P06", "P09", "P11", "P12"] if f not in index or index[f]["state"] not in {"observed", "reported"}]
    if any(f["state"] == "stale" for f in report["facts"]):
        finding(report, "STALE_EVIDENCE_REAUDIT_REQUIRED")
    if obj.get("snapshot_state", "unknown") not in {"stable", "unknown", "changed"}:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    if obj.get("snapshot_state") == "changed":
        finding(report, "SNAPSHOT_CHANGED_DURING_AUDIT")
    report["next_actions"] = ["Resolve missing or stale target facts", "Prepare neutral endpoint proposal; endpoint selection and probe authorization pending"]
    p6, p9 = index.get("P06", {}), index.get("P09", {})
    usable = all(f.get("state") == "observed" and f.get("layer") in {"os_query", "runtime"} for f in (p6, p9))
    conflict = usable and p6["value"]["enabled"] and p9["value"]["port_owner_matches"] and p6["value"]["port"] != p9["value"]["selected_instance_port"]
    configuration_ready = conflict and obj.get("snapshot_state") == "stable" and all(index.get(field, {}).get("state") == "observed" and index.get(field, {}).get("layer") in {"os_query", "runtime"} for field in ("P11", "P12"))
    if conflict:
        finding(report, "PROXY_PORT_ASSOCIATION_CONFLICT", "ENV-02")
        if configuration_ready:
            report["inventory_readiness"] = "ready_for_configuration_plan"
    else:
        finding(report, "NETWORK_EFFECTIVENESS_NOT_TESTED", "ENV-03")
    if planning:
        report["plan"] = {"mode": "preview_only", "executable": False, "requires_fresh_native_audit": True, "diff": [], "validation": ["Reconfirm selected proxy instance and ownership", "Approve neutral endpoints and future probes", "Validate application-specific paths after authorized contact"], "recovery": "No change made. Future edits require recording exact old values and a tested restore method."}
        if configuration_ready:
            report["plan"]["diff"].append({"module_id": "ENV-06", "field": "selected_target.system_proxy.port", "before": p6["value"]["port"], "proposed_after": p9["value"]["selected_instance_port"], "preconditions": ["Revalidate live target, selected instance and active configuration", "Obtain exact-change authorization", "Establish backup and recovery; platform executor not available in this release"]})
        elif conflict:
            finding(report, "PLAN_REQUIRES_STABLE_SNAPSHOT_AND_ROUTE_FACTS", "ENV-06")
        report["next_actions"].append("Review the preview; automatic modification is deferred")
    return report


def native_check(args):
    report = base("audit", args.target_ref)
    report["schema_version"] = "env-inventory/0.2"
    report["module_ids"] = ["ENV-01", "ENV-02"]
    if not args.target_ref or not args.confirm_target:
        raise GuardianError("TARGET_NOT_BOUND", 3)
    alias(args.target_ref)
    if not args.authorize_audit:
        raise GuardianError("AUTHORIZATION_MISSING", 3)
    actual = "macos" if sys.platform == "darwin" else "windows" if sys.platform == "win32" else "unsupported"
    if args.target_os != actual:
        raise GuardianError("TARGET_USER_CONTEXT_MISMATCH", 3)
    if args.target_kind != "local" or args.namespace != "desktop" or args.execution_location != "native_local" or args.user_context != "same":
        raise GuardianError("TARGET_USER_CONTEXT_MISMATCH", 3)
    report["record_kind"] = "device_observation"
    report["target_binding"] = {"binding_state": "bound_by_explicit_operator_attestation", "declared_os": actual, "requested_role": "local_desktop", "execution_location": args.execution_location, "desktop_user_relation": args.user_context, "filesystem_namespace": "host_desktop", "network_namespace": "not_verified"}
    # No process launches or directories scanned. These APIs only describe this process/OS.
    if actual == "windows":
        win = sys.getwindowsversion()
        version = "%s.%s.%s" % (win.major, win.minor, win.build)
    else:
        version = os.uname().release  # Darwin kernel; not mislabeled as macOS product release.
    values = [("S01", actual), ("S02", version), ("S09", int(time.localtime().tm_gmtoff) if hasattr(time.localtime(), "tm_gmtoff") else -time.altzone if time.localtime().tm_isdst else -time.timezone)]
    for field, value in values:
        report["facts"].append({"id": field, "value": value, "state": "observed", "source_refs": ["native-stdlib-os"], "context_ref": args.target_ref, "observed_at": now(), "reason_code": "KERNEL_VERSION_ONLY" if field == "S02" else "READ_ONLY_PROCESS_CONTEXT", "layer": "os_query", "coverage": "current_process_os"})
    report["missing_fields"] = ["S03: Windows edition", "S04: hardware versus process architecture", "S06: desktop UI language", "S08: timezone identifier", "S10: automatic time and timezone", "S13: approved installation inventory", "S14: related running processes", "P01-P24: proxy inventory not implemented"]
    finding(report, "MINIMAL_METADATA_ONLY")
    report["next_actions"] = ["Supply narrowly scoped offline proxy observations", "Complete platform validation before expanding collectors"]
    return report


QUESTIONS = [
    ("subscription_stage", "Q-J01", "这是首次准备订阅、重新订阅，还是已有订阅回访？", ["first_subscription", "returning_subscription", "existing_subscriber", "unknown"]),
    ("current_task", "Q-C11", "这次想续费、升级、检查环境，还是排障？", ["renew", "upgrade", "environment", "troubleshoot"]),
    ("os", "Q-C01", "目标电脑是 macOS 还是 Windows？", ["macos", "windows", "unknown", "phone_only"]),
    ("usage", "Q-C02", "主要使用网页、Desktop、Code，还是 IDE 中的 Code？", ["web", "desktop", "code", "ide_code", "mixed", "unknown"]),
    ("target_plan", "Q-C08", "想订阅什么套餐？也可以先标记未决定", None),
    ("account_status", "Q-C03", "当前账号状态是什么？", ["not_registered", "active", "suspended", "unknown"]),
    ("device_history", "Q-C04", "本次目标电脑是否用过 Claude、是否有过停用经历？", ["new_to_claude", "previous_use_no_reported_suspension", "previous_use_with_reported_suspension", "unknown"]),
    ("route", "Q-C05", "建议本机，也可选择虚拟机或 VPS；希望采用哪种？", ["local", "vm", "vps", "explain"]),
]


def interview(obj):
    if obj.get("schema_version") == "guardian-report/0.1":
        contact = obj.get("contact_control")
        if obj.get("operation") != "interview" or not isinstance(contact, dict) or not isinstance(obj.get("state"), dict):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
        contact_guard(contact)
        if obj.get("execution_status") == "interrupted":
            raise GuardianError("USER_CANCELLED", 3)
        obj = obj["state"]
    contact_guard(obj)
    if set(obj) - {"schema_version", "answers", "cancelled"} or obj.get("schema_version", "guardian-interview/0.1") != "guardian-interview/0.1":
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    answers = obj.get("answers", {})
    if not isinstance(answers, dict) or set(answers) - {q[0] for q in QUESTIONS}:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    for field, _, _, choices in QUESTIONS:
        if field in answers and (not isinstance(answers[field], str) or len(answers[field]) > 80 or (choices and answers[field] not in choices)):
            raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    report = base("interview")
    report["state"] = {"schema_version": "guardian-interview/0.1", "answers": answers}
    if "cancelled" in obj and type(obj["cancelled"]) is not bool:
        raise GuardianError("INPUT_OR_RESPONSE_INVALID")
    if obj.get("cancelled"):
        report.update(execution_status="interrupted", inventory_readiness="interrupted")
        finding(report, "USER_CANCELLED", "M00")
        return report
    if answers.get("account_status") == "suspended":
        report["next_actions"] = ["Prioritize M12 incident review and preserve existing evidence; no new purchase or login test"]
        finding(report, "INCIDENT_PRIORITY", "M12")
        return report
    for field, qid, question, choices in QUESTIONS:
        if field == "current_task" and answers.get("subscription_stage") != "existing_subscriber":
            continue
        if field == "target_plan" and answers.get("subscription_stage") == "existing_subscriber" and answers.get("current_task") in {"environment", "troubleshoot"}:
            continue
        if field in answers:
            continue
        report["question"] = {"id": qid, "field": field, "text": question, "choices": choices}
        report["inventory_readiness"] = "needs_input"
        return report
    report["next_actions"] = ["Bind the actual target and request scoped read-only audit authorization", "Payment and route resource interviews remain outside this diagnostic preview"]
    if answers.get("route") in {"vm", "vps", "explain"} or answers.get("os") in {"unknown", "phone_only"} or answers.get("subscription_stage") == "unknown":
        finding(report, "ROUTE_OR_TARGET_NEEDS_CLARIFICATION", "M00")
        report["inventory_readiness"] = "needs_input"
    return report


def parser():
    root = argparse.ArgumentParser(description=__doc__)
    root.add_argument("--version", action="version", version=VERSION)
    subs = root.add_subparsers(dest="command", required=True)
    for command in ("interview", "check", "analyze", "plan"):
        sub = subs.add_parser(command)
        sub.add_argument("--output", help="Explicitly save redacted JSON to a NEW local file; never overwrites")
        if command != "check":
            sub.add_argument("--input", required=command in {"analyze", "plan"}, help="Local interview state, guardian-offline/0.1 fixture, or saved check report; never a live config")
        if command != "interview":
            sub.add_argument("--target-ref", required=True, help="Task alias, not username or hostname")
        if command == "check":
            sub.add_argument("--target-os", choices=["macos", "windows"], required=True)
            sub.add_argument("--target-kind", choices=["local", "vm", "vps"], default="local")
            sub.add_argument("--namespace", choices=["desktop", "sandbox", "guest", "remote", "unknown"], default="unknown")
            sub.add_argument("--execution-location", choices=["native_local", "cloud", "ssh", "wsl", "virtualized", "unknown"], default="unknown")
            sub.add_argument("--user-context", choices=["same", "different", "unknown"], default="unknown")
            sub.add_argument("--confirm-target", action="store_true")
            sub.add_argument("--authorize-audit", action="store_true")
    return root


def save_new(path, text):
    p = Path(path)
    if str(path).startswith(("//", "\\\\")) or any(part.is_symlink() for part in [p, *p.parents]):
        raise GuardianError("UNSAFE_OR_OFFLINE_PATH", 3)
    try:
        fd = os.open(str(p), os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
        with os.fdopen(fd, "w", encoding="utf-8") as stream:
            stream.write(text)
    except OSError:
        raise GuardianError("OUTPUT_SAVE_FAILED", 3) from None


def main(argv=None):
    args = parser().parse_args(argv)
    code = 0
    try:
        target = getattr(args, "target_ref", None)
        if target:
            alias(target)
        if args.command == "check":
            report = native_check(args)
        else:
            obj = load_json(args.input) if args.input else {}
            report = interview(obj) if args.command == "interview" else analyze(obj, target, args.command == "plan")
    except KeyboardInterrupt:
        report = base(args.command)
        report.update(execution_status="interrupted", inventory_readiness="interrupted")
        finding(report, "USER_CANCELLED")
    except GuardianError as error:
        report = base(args.command)
        report.update(execution_status="blocked", inventory_readiness="blocked")
        finding(report, error.code)
        code = error.exit_code
    except Exception:
        report = base(args.command)
        report.update(execution_status="failed", inventory_readiness="blocked")
        finding(report, "COLLECTOR_INTERNAL_FAILURE")
        code = 4
    text = json.dumps(redact(report), ensure_ascii=False, indent=2) + "\n"
    if args.output:
        try:
            save_new(args.output, text)
        except GuardianError as error:
            finding(report, error.code)
            code = error.exit_code
            text = json.dumps(redact(report), ensure_ascii=False, indent=2) + "\n"
    sys.stdout.write(text)
    return code


if __name__ == "__main__":
    raise SystemExit(main())
