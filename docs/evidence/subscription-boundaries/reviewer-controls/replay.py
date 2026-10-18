"""Separate reviewer logic controls; NEVER respondent calls or generated prose.

Explicit UTF-8, Python 3.10-compatible standard library. Reads/imports happen
before the fail-fast pure-call scope; output writes happen afterward. The
instrumentation is an in-process guard, not a machine/network sandbox proof.
"""
import argparse
from contextlib import ExitStack, contextmanager
from copy import deepcopy
import hashlib
import importlib.util
import io
import json
import os
from pathlib import Path
import platform
import socket
import subprocess
import sys
from unittest.mock import patch

sys.dont_write_bytecode = True
BASE = Path(__file__).resolve().parents[1]
CANDIDATE = BASE / "retained/candidate"
GUARDS = (
    "builtins.open", "io.open", "os.open", "pathlib.Path.open",
    "socket.socket", "socket.create_connection", "socket.getaddrinfo",
    "socket.gethostbyname", "socket.gethostbyname_ex", "socket.gethostbyaddr",
    "subprocess.Popen", "subprocess.run", "subprocess.call",
    "subprocess.check_call", "subprocess.check_output", "os.system", "os.popen",
)


def load():
    path = CANDIDATE / "generator-inputs/runtime/interview_flow.py"
    spec = importlib.util.spec_from_file_location("subscription_boundary_reviewer_flow", path)
    module = importlib.util.module_from_spec(spec)
    sys.modules[spec.name] = module
    spec.loader.exec_module(module)
    return module


@contextmanager
def no_io(module, clock, attempted):
    def deny(name):
        def blocked(*args, **kwargs):
            attempted.append(name)
            raise AssertionError("Reviewer pure-call I/O denied: " + name)
        return blocked
    with ExitStack() as stack:
        stack.enter_context(patch.object(module, "_now", return_value=clock))
        for name in GUARDS:
            stack.enter_context(patch(name, side_effect=deny(name)))
        yield


def replay():
    fixtures = json.loads((CANDIDATE / "generator-inputs/helper-inputs/prior-pure-api-inputs.json").read_text(encoding="utf-8"))
    prior = json.loads((CANDIDATE / "review-only/prior-observations/outputs.json").read_text(encoding="utf-8"))
    module = load()
    calls, outputs, attempts = [], {}, []
    for name, fixture in fixtures.items():
        state = deepcopy(fixture["state"])
        original = deepcopy(state)
        with no_io(module, fixture["fixture_clock"], attempts):
            arguments = {"state": deepcopy(state), "question_id": fixture["question_id"],
                         "value": deepcopy(fixture["value"]), "kwargs": deepcopy(fixture["kwargs"])}
            result = module.record_fact(state, fixture["question_id"], fixture["value"], **fixture["kwargs"])
            calls.append({"control_id": name, "call": "record_fact", "arguments": arguments,
                          "return": deepcopy(result), "exception": None, "fixture_clock": fixture["fixture_clock"]})
            assessment = module.assessment(result)
            calls.append({"control_id": name, "call": "assessment", "arguments": {"state": deepcopy(result)},
                          "return": deepcopy(assessment), "exception": None, "fixture_clock": fixture["fixture_clock"]})
            questions = []
            for index in range(3):
                question = module.next_question(result)
                questions.append(question)
                calls.append({"control_id": name, "call": "next_question", "repeat": index + 1,
                              "arguments": {"state": deepcopy(result)}, "return": deepcopy(question),
                              "exception": None, "fixture_clock": fixture["fixture_clock"]})
        if state != original:
            raise AssertionError("Input state mutated: " + name)
        outputs[name] = {"state": result, "assessment": assessment, "next_questions_three_repeats": questions}
    if outputs != prior:
        raise AssertionError("Fresh separate reviewer controls differ from retained prior observations")
    return {"kind": "separate_reviewer_logic_controls", "respondent_calls": False,
            "dialogue_state_replay": False, "model_prose_generated": False,
            "python_version": platform.python_version(), "execution_platform": sys.platform,
            "guard_scope": "Only pure calls after imports; fixture reading and report writing outside guard",
            "guard_targets": list(GUARDS), "blocked_io_attempts": attempts,
            "outputs_equal_retained_prior_observations": True,
            "call_count": len(calls), "calls": calls, "outputs": outputs}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    if args.output.exists():
        raise SystemExit("Refusing to replace a retained reviewer control report")
    report = replay()
    raw = (json.dumps(report, ensure_ascii=True, sort_keys=True, indent=2) + "\n").encode("utf-8")
    args.output.write_bytes(raw)
    print(json.dumps({"kind": report["kind"], "call_count": report["call_count"],
                      "blocked_io_attempts": report["blocked_io_attempts"],
                      "outputs_equal_retained_prior_observations": True,
                      "report_sha256": hashlib.sha256(raw).hexdigest()}, ensure_ascii=True))


if __name__ == "__main__":
    main()
