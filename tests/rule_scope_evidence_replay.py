"""Replay frozen helper calls only; never generate or edit model responses.

Recorded prose, events, source snapshots, and errors remain immutable. Current
replays add test-level API sentinels, not historical or OS-wide telemetry.
"""
from contextlib import ExitStack
from copy import deepcopy
from dataclasses import fields, is_dataclass
from pathlib import Path
from unittest.mock import patch
import argparse
import base64
import hashlib
import importlib
import json
import sys

ROOT = Path(__file__).resolve().parents[1]
DATA = ROOT / 'docs' / 'evidence' / 'rule-scope'
FORBIDDEN_IO = ('builtins.open', 'io.open', 'os.open', 'socket.socket',
                'socket.create_connection', 'socket.getaddrinfo',
                'socket.gethostbyname', 'socket.gethostbyname_ex',
                'socket.gethostbyaddr', 'subprocess.Popen', 'os.system',
                'os.popen', 'urllib.request.urlopen')
CALLABLES = ('rule_source_import.import_rule_bindings',
             'config_edit_plan.compile_edit_plan',
             'rules_extension_plan.compile_rules_extension',
             'remedy_plans.compile_plan', 'agent_remediation.select')


def sha(raw):
    return hashlib.sha256(raw).hexdigest()


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def decode(value):
    if isinstance(value, list):
        return [decode(item) for item in value]
    if not isinstance(value, dict):
        return value
    if value.get('type') == 'bytes':
        assert set(value) == {'type', 'base64', 'sha256', 'length', 'utf8'}
        raw = base64.b64decode(value['base64'], validate=True)
        assert len(raw) == value['length'] and sha(raw) == value['sha256']
        assert raw.decode('utf-8') == value['utf8']
        return raw
    if value.get('type') == 'tuple':
        assert set(value) == {'type', 'items'}
        return tuple(decode(item) for item in value['items'])
    return {key: decode(item) for key, item in value.items()}


def encode(value):
    if isinstance(value, bytes):
        return {'type': 'bytes', 'base64': base64.b64encode(value).decode('ascii'),
                'sha256': sha(value), 'length': len(value), 'utf8': value.decode('utf-8')}
    if is_dataclass(value):
        return {'type': type(value).__name__,
                'fields': {field.name: encode(getattr(value, field.name)) for field in fields(value)}}
    if isinstance(value, tuple):
        return {'type': 'tuple', 'items': [encode(item) for item in value]}
    if isinstance(value, list):
        return [encode(item) for item in value]
    if isinstance(value, dict):
        return {key: encode(item) for key, item in value.items()}
    if value is None or isinstance(value, (str, bool, int, float)):
        return value
    raise TypeError('Unexpected helper result type')


def load_functions(repo):
    # Module loading precedes instrumentation; it is not falsely claimed I/O-free.
    sys.path.insert(0, str(Path(repo) / 'skills' / 'claude-guardian' / 'scripts'))
    import urllib.request  # noqa: F401
    result = {}
    for name in CALLABLES:
        module, member = name.rsplit('.', 1)
        result[name] = getattr(importlib.import_module(module), member)
    return result


def invoke(trace, functions):
    assert trace['callable'] in functions
    args, kwargs = decode(trace['positional_arguments']), decode(trace['keyword_arguments'])
    assert type(args) is tuple and type(kwargs) is dict
    before = deepcopy((args, kwargs))
    result = None
    with ExitStack() as stack:
        sentinels = {name: stack.enter_context(patch(name, side_effect=AssertionError(
            'Unexpected helper I/O: ' + name))) for name in FORBIDDEN_IO}
        try:
            returned = functions[trace['callable']](*args, **kwargs)
            output = {'return_type': type(returned).__name__}
            if isinstance(returned, dict):
                output['result'] = returned
            else:
                output['repr'] = repr(returned)
                for method in ('preview', 'binding_components', 'private_material'):
                    if hasattr(returned, method):
                        output[method] = getattr(returned, method)()
            result = {'status': 'returned', 'output': encode(output)}
        except Exception as exc:
            result = {'status': 'error', 'error': {'exception_module': type(exc).__module__,
                      'exception_type': type(exc).__name__, 'message': str(exc)}}
        counts = {name: item.call_count for name, item in sentinels.items()}
    assert not any(counts.values()), counts
    assert (args, kwargs) == before, 'Helper mutated supplied arguments'
    result.update({'arguments_unchanged': True, 'instrumented_api_call_counts': counts})
    return result


def replay_observed(repo=ROOT, data=DATA):
    observed = Path(data) / 'observed'
    functions = load_functions(repo)
    provenance = read_json(observed / 'provenance-manifest.json')
    results = {}
    for row in provenance['actual_helper_call_order']:
        trace = read_json(observed / row['input'])
        assert trace['call_id'] == row['call_id']
        actual = invoke(trace, functions)
        expected = read_json(observed / row['output_or_error'])
        if row['kind'] == 'helper_return':
            assert actual['status'] == 'returned'
            assert actual['output'] == expected, row['call_id']
        else:
            assert actual['status'] == 'error'
            assert actual['error'] == {key: expected[key] for key in
                   ('exception_module', 'exception_type', 'message')}, row['call_id']
        results[row['call_id']] = actual
    return results


def replay_supplement(repo=ROOT, data=DATA):
    supplemental = Path(data) / 'supplemental'
    freeze = read_json(supplemental / 'input-freeze.json')
    assert sha((supplemental / 'inputs.json').read_bytes()) == freeze['inputs_sha256']
    for name, expected in freeze['source_sha256'].items():
        assert sha((Path(repo) / name).read_bytes()) == expected, name
    functions = load_functions(repo)
    results = {}
    for trace in read_json(supplemental / 'inputs.json')['calls']:
        actual = invoke(trace, functions)
        expected = trace['expected_review_outcome']
        if expected in ('INVALID_BINDING', 'PROTECTED_RULE_PRIORITY_CONFLICT',
                        'UNSUPPORTED_RULE_RECORD', 'invalid object shape'):
            assert actual['status'] == 'error' and actual['error']['message'] == expected
        elif expected == 'imported_candidate_only':
            assert actual['output']['preview']['status'] == expected
        elif expected == 'same_as_fixed_baseline':
            assert actual['output'] == results['review-ENV-T58-fixed-selector-baseline']['output']
        else:
            assert expected == 'fixed_selection' and actual['status'] == 'returned'
            result = actual['output']['result']
            assert [item['action_id'] for item in result['actions']] == ['plan-rules']
            assert result['changes'] == [] and result['authority'] == 'none'
        results[trace['call_id']] = actual
    return results


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--repo', type=Path, default=ROOT)
    parser.add_argument('--data', type=Path, default=DATA)
    parser.add_argument('--capture-supplement', type=Path)
    args = parser.parse_args()
    if args.capture_supplement is not None:
        result = replay_supplement(args.repo, args.data)
        args.capture_supplement.write_text(json.dumps(result, ensure_ascii=False, indent=2) + '\n',
                                          encoding='utf-8')
    else:
        result = {'scope': 'current helper replay only; no model prose regeneration',
                  'observed_calls': replay_observed(args.repo, args.data),
                  'reviewer_supplemental_calls': replay_supplement(args.repo, args.data)}
        print(json.dumps(result, ensure_ascii=True, sort_keys=True))


if __name__ == '__main__':
    main()
