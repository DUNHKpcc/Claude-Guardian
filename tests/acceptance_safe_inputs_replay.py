"""Portable bounded T11/T12 supporting replay, not the actual response generator.

The original responses/provenance remain unchanged in the evidence directory;
this wrapper reruns only the separate CLI/helper checks, not model/native behavior.

Python 3.10+ standard library only. All files are synthetic and under --output.
This runner reads the selected source tree but never edits it.
"""
import argparse
from contextlib import ExitStack
from datetime import datetime, timezone
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import subprocess
import sys
from unittest.mock import patch
from test_acceptance_skill_registry_wording import (
    SKILL_PATH, SUPPLEMENT_RELATIVE, SUPPLEMENT_SHA256, checked_registry_wording_sha256)


HERE = Path(__file__).resolve().parents[1] / 'docs/evidence/t11-t12-safe-inputs-v1'


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def write_json(path, value):
    # Escape non-ASCII and surrogateescaped argv bytes; files remain UTF-8 JSON.
    path.write_text(json.dumps(value, ensure_ascii=True, indent=2) + '\n', encoding='utf-8')


def module(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    result = importlib.util.module_from_spec(spec)
    sys.modules[name] = result
    spec.loader.exec_module(result)
    return result


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--source', type=Path, required=True)
    parser.add_argument('--output', type=Path, required=True)
    args = parser.parse_args()
    args.source = args.source.resolve()
    args.output = args.output.resolve()
    pins = read_json(HERE / 'source-pins.json')
    actual_sources = {}
    for relative, expected in pins['source_sha256'].items():
        path = args.source / relative
        content = path.read_bytes()
        actual = hashlib.sha256(content).hexdigest()
        if relative == SKILL_PATH:
            try:
                if path.is_symlink():
                    raise ValueError('Aliased SKILL path')
                actual = checked_registry_wording_sha256(content, expected)
            except ValueError as exc:
                raise SystemExit('Pinned source changed: ' + relative + '; ' + str(exc)) from None
        elif actual != expected:
            raise SystemExit('Pinned source changed: ' + relative)
        actual_sources[relative] = actual
    historical_pin_file = {
        'path': 'docs/evidence/t11-t12-safe-inputs-v1/source-pins.json',
        'sha256': hashlib.sha256((HERE / 'source-pins.json').read_bytes()).hexdigest()}
    compatibility = ({'documentation_compatibility': {
        'path': SUPPLEMENT_RELATIVE, 'sha256': SUPPLEMENT_SHA256}}
        if actual_sources[SKILL_PATH] != pins['source_sha256'][SKILL_PATH] else {})
    args.output.mkdir(parents=True, exist_ok=False)
    script = args.source / 'skills/claude-guardian/scripts/guardian.py'
    guardian = module('safe_input_guardian', script)
    source = module('safe_input_source', script.with_name('source_evidence.py'))
    stamp = datetime.now(timezone.utc).isoformat()
    marker = 'T11_UNKNOWN_SYNTHETIC_20261018'
    hostile = read_json(HERE / 'exercise-inputs.json')['T12'][0]

    def fixture():
        return {'schema_version': 'guardian-offline/0.1', 'target_ref': 'device-1',
                'record_kind': 'synthetic_example',
                'target_binding': {'declared_os': 'macos', 'desktop_user_relation': 'same',
                    'filesystem_namespace': 'host_desktop', 'execution_location': 'native_local'},
                'facts': []}

    cases = []
    obj = fixture(); obj['raw_log'] = 'Cookie: session=' + marker
    cases.append(('unknown-log-field', obj, marker, 2, 'INPUT_OR_RESPONSE_INVALID'))
    obj = fixture(); obj['facts'] = [{'id': 'S08', 'value': 'Windows:Bearer ' + marker,
        'state': 'reported', 'context_ref': 'device-1', 'observed_at': stamp,
        'layer': 'reported', 'source_ref': 'synthetic-source'}]
    cases.append(('credential-typed-value', obj, marker, 2, 'INPUT_OR_RESPONSE_INVALID'))
    for key in ('command', 'script', 'url'):
        obj = fixture(); obj[key] = hostile
        cases.append(('injected-' + key, obj, hostile, 3, 'PRECONTACT_ACTION_REJECTED'))
    for key, value in (('contact_phase', 'PC2'), ('gate_state', 'open'), ('operation', 'login')):
        obj = fixture(); obj[key] = value
        cases.append(('injected-' + key, obj, None, 3, 'PRECONTACT_ACTION_REJECTED'))
    obj = fixture(); obj['facts'] = [{'id': 'S01', 'value': hostile,
        'state': 'reported', 'context_ref': 'device-1', 'observed_at': stamp,
        'layer': 'reported', 'source_ref': 'synthetic-source'}]
    cases.append(('instruction-as-fact', obj, hostile, 2, 'INPUT_OR_RESPONSE_INVALID'))
    traces = []
    for name, obj, forbidden, expected_code, expected_error in cases:
        directory = args.output / name; directory.mkdir()
        source_path = directory / 'input.json'
        output_path = directory / 'saved-report.json'
        write_json(source_path, obj)
        argv = [sys.executable, '-B', str(script), 'plan', '--target-ref', 'device-1',
                '--input', str(source_path), '--output', str(output_path)]
        run = subprocess.run(argv, cwd=directory, env=dict(os.environ, PYTHONDONTWRITEBYTECODE='1'),
            capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=10)
        (directory / 'stdout.txt').write_text(run.stdout, encoding='utf-8')
        (directory / 'stderr.txt').write_text(run.stderr, encoding='utf-8')
        report = json.loads(run.stdout)
        saved = output_path.read_text(encoding='utf-8')
        checks = {'exit_code': run.returncode == expected_code,
                  'expected_error': expected_error in [x['code'] for x in report['findings']],
                  'blocked': report['execution_status'] == 'blocked',
                  'gate_closed': report['contact_control']['gate_state'] == 'closed',
                  'phase_precontact': report['contact_control']['contact_phase'] == 'precontact',
                  'no_changes': report['changes'] == [], 'no_facts': report['facts'] == [],
                  'saved_equals_stdout': json.loads(saved) == report,
                  'no_raw_payload': forbidden is None or forbidden not in run.stdout + run.stderr + saved}
        assert all(checks.values()), (name, checks)
        traces.append({'case': name, 'argv': argv, 'returncode': run.returncode,
                       'checks': checks, 'output_files': ['stdout.txt', 'stderr.txt', 'saved-report.json']})

    # Existing generic redaction is intentionally not a universal log scrubber.
    # Observe rather than hide its boundary: the host must omit raw log bodies.
    synthetic = {'authorization': 'T11_AUTH_SYNTHETIC_20261018',
                 'cookie': 'T11_COOKIE_STRUCTURED_SYNTHETIC_20261018',
                 'message': 'Bearer T11_BEARER_SYNTHETIC_20261018 password=T11_PASSWORD_SYNTHETIC_20261018'}
    redacted = guardian.redact(synthetic)
    assert 'T11_' not in json.dumps(redacted)
    raw = 'Cookie: session=T11_COOKIE_RAW_SYNTHETIC_20261018; 密码=T11_CN_RAW_SYNTHETIC_20261018; opaque=T11_OPAQUE_RAW_SYNTHETIC_20261018'
    raw_result = guardian.redact(raw)
    redaction = {'structured_input': synthetic, 'structured_output': redacted,
                 'raw_log_input': raw, 'raw_log_output': raw_result,
                 'raw_log_sentinel_remains': 'T11_' in raw_result,
                 'interpretation': 'Defense-in-depth helper is not an arbitrary-log sanitization API; raw source logs must not be exported.'}
    write_json(args.output / 'redaction-boundary.json', redaction)

    denied = ['builtins.open', 'pathlib.Path.open', 'os.open', 'os.system',
              'subprocess.Popen', 'socket.socket', 'socket.getaddrinfo']
    with ExitStack() as stack:
        hooks = {name: stack.enter_context(patch(name, side_effect=AssertionError(name))) for name in denied}
        result = source.group_source_bytes([('input-A', hostile.encode('utf-8'))])
        calls = {name: hook.call_count for name, hook in hooks.items()}
    assert all(value == 0 for value in calls.values())
    assert result == {'groups': [{'sha256': hashlib.sha256(hostile.encode('utf-8')).hexdigest(),
                                'source_ids': ['input-A']}], 'independent_sources': 'not_established'}
    write_json(args.output / 'opaque-source-trace.json', {'input_sha256': result['groups'][0]['sha256'],
        'result': result, 'observed_calls_to_instrumented_functions': calls,
        'limits': 'Only this pure helper invocation; not a host response, general sandbox, or tool-policy audit.'})
    write_json(args.output / 'execution-record.json', {
        'executed_at_utc': stamp, 'python_version': sys.version, 'platform': sys.platform,
        'source_sha256': actual_sources, 'historical_source_pin_file': historical_pin_file,
        **compatibility, 'cases': traces,
        'status': 'supporting_runtime_cases_passed; full_T11_T12_acceptance_pending',
        'limits': pins['limits']})
    print(json.dumps({'cli_cases_passed': len(traces), 'pure_source_helper_checked': True,
        'raw_log_redaction_is_not_universal': redaction['raw_log_sentinel_remains'],
        'full_T11_T12_acceptance': 'pending', 'output': str(args.output)}, ensure_ascii=True))


if __name__ == '__main__':
    main()
