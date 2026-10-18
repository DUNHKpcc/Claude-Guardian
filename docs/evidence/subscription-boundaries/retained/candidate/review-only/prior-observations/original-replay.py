"""Read-only planning audit: existing normalized interview APIs, synthetic facts.

Uses existing fixture constructors as inputs, not their test verdicts. No model,
native, login, payment, mutation or acceptance result is produced.
"""
import argparse
import hashlib
import json
from pathlib import Path
import platform
import runpy
import sys

parser = argparse.ArgumentParser()
parser.add_argument('--source', type=Path, required=True)
parser.add_argument('--output', type=Path, required=True)
args = parser.parse_args()
root = args.source.resolve()
if args.output.exists():
    raise SystemExit('Output must be a new nonexistent directory')
sys.dont_write_bytecode = True
sys.path.insert(0, str(root / 'tests'))
m = runpy.run_path(str(root / 'tests/test_acceptance_mobile_route.py'))
f = m['f']
inputs = {}
outputs = {}
with m['offline']():
    complete, _ = m['after_separate_handoff']('apple', 'local')
    pc0, _ = m['complete_pc0']('apple', 'local')
    definitions = [
        ('T38_negative_report', complete, 'Q-A02',
         {'sign_in_and_verification': 'reported_unavailable', 'credentials_collected': False},
         {'source': 'synthetic:negative-apple-login',
          'blocker_reason': 'Apple sign-in and verification unavailable'}),
        ('T46_region_refusal', pc0, 'Q-C09', None,
         {'state_name': 'declined', 'source': 'synthetic:region-refusal',
          'blocker_reason': 'Region eligibility not established'}),
        ('T54_unknown_storefront_draft', pc0, 'Q-A03', None,
         {'state_name': 'unknown', 'source': 'synthetic:storefront-unknown'}),
    ]
    for case, state, qid, value, kwargs in definitions:
        inputs[case] = {'state': state, 'question_id': qid, 'value': value,
                        'kwargs': kwargs, 'fixture_clock': m['TIME']}
        result = f.record_fact(state, qid, value, **kwargs)
        outputs[case] = {
            'state': result,
            'assessment': f.assessment(result),
            'next_questions_three_repeats': [f.next_question(result) for _ in range(3)],
        }

def encoded(value):
    return (json.dumps(value, ensure_ascii=True, indent=2, sort_keys=True) + '\n').encode('utf-8')

inputs_raw, outputs_raw = encoded(inputs), encoded(outputs)
paths = ['skills/claude-guardian/scripts/interview_flow.py',
         'tests/test_acceptance_mobile_route.py',
         'skills/claude-guardian/references/accounts-and-payments.md',
         'skills/claude-guardian/references/intake.md',
         'skills/claude-guardian/SKILL.md',
         'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md',
         'skills/claude-guardian/sources/design/D-ENV-v0.3.md',
         'docs/acceptance-rebuild-ledger.json']
manifest = {
    'source_tree': str(root),
    'python_version': platform.python_version(),
    'execution_platform': sys.platform,
    'inputs_sha256': hashlib.sha256(inputs_raw).hexdigest(),
    'outputs_sha256': hashlib.sha256(outputs_raw).hexdigest(),
    'runner_sha256': hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
    'source_hashes': {p: hashlib.sha256((root / p).read_bytes()).hexdigest() for p in paths},
    'boundary': ('Actual pure API observations with synthetic normalized inputs only. '
                 'PC2 is an existing fixture state label, not actual permission or handoff. '
                 'Instrumented no-I/O guard covered the tested pure operations after module loading. '
                 'No generated response, native device, external request, login, payment, '
                 'repository implementation or acceptance promotion was performed.'),
}
args.output.mkdir()
(args.output / 'inputs.json').write_bytes(inputs_raw)
(args.output / 'outputs.json').write_bytes(outputs_raw)
(args.output / 'manifest.json').write_bytes(encoded(manifest))
print(json.dumps(manifest, ensure_ascii=True, indent=2, sort_keys=True))
