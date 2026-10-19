"""Verify the declared public projection, not the omitted private recorder chain.
Reads only the pinned packet and explicit project source; performs no generation.
"""
import copy
import hashlib
import json
from pathlib import Path, PurePosixPath
import re

MUTATORS = {'new_state', 'record_fact', 'record_facts', 'set_context', 'mark_asked',
            'defer_branch', 'resume_branch', 'complete_purchase', 'resume_interview',
            'record_resume_review', 'report_subscription_conflict',
            'resolve_subscription_conflict', 'begin_task'}
ORIGINAL_ARCHIVE = '119628d5b81e8397e0c6fc01c4160122593ee291319807d0fc2b34e88d81a06e'
SCENARIOS = {'revision3': ['d01', 'd02a', 'd02b', 'd03a', 'd03b', 'd04a', 'd04b',
                          'd05a', 'd05b', 'd06a', 'd06b', 'd06c'],
             'revision4': ['d02b', 'd03b']}


def sha(data):
    return hashlib.sha256(data).hexdigest()


def canonical(value):
    return json.dumps(value, ensure_ascii=False, sort_keys=True,
                      separators=(',', ':')).encode('utf-8')


def read_json(path):
    return json.loads(Path(path).read_text(encoding='utf-8'))


def answer_units(text):
    return [part.strip() for line in text.splitlines()
            for part in re.findall(r'[^。！？]+[。！？]?|[。！？]', line) if part.strip()]


def safe_rel(name):
    path = PurePosixPath(name)
    if not isinstance(name, str) or not name or path.is_absolute() or '..' in path.parts or '\\' in name or ':' in name or path.as_posix() != name:
        raise AssertionError('Unsafe packet path')
    return name


def verify_manifest(packet, expected_manifest_sha256):
    packet = Path(packet)
    raw = (packet / 'manifest.json').read_bytes()
    if sha(raw) != expected_manifest_sha256:
        raise AssertionError('Packet manifest does not match the installed literal pin')
    manifest = json.loads(raw)
    if manifest['format'] != 'guardian-upgrade-conflict-public/2':
        raise AssertionError('Unexpected packet format')
    for relative, digest in manifest['files'].items():
        path = packet / safe_rel(relative)
        if path.is_symlink() or sha(path.read_bytes()) != digest:
            raise AssertionError('Packet member mismatch: ' + relative)
    actual = {p.relative_to(packet).as_posix() for p in packet.rglob('*')
              if p.is_file() and '__pycache__' not in p.parts and p.name != 'manifest.json'}
    if actual != set(manifest['files']):
        raise AssertionError('Packet inventory mismatch')
    return manifest


def load_projection(packet):
    """Expand content-addressed JSON; reject cycles, altered or unused pool objects."""
    values = read_json(Path(packet) / 'values.json')
    expanded, active, used = {}, set(), set()

    def expand(value):
        if isinstance(value, dict):
            if '$value' in value:
                if set(value) != {'$value'}:
                    raise AssertionError('Ambiguous pooled value')
                key = value['$value']
                if key not in values or key in active:
                    raise AssertionError('Missing or cyclic pooled value')
                used.add(key)
                if key not in expanded:
                    active.add(key)
                    result = expand(values[key])
                    active.remove(key)
                    if sha(canonical(result)) != key:
                        raise AssertionError('Pooled value hash mismatch')
                    expanded[key] = result
                return copy.deepcopy(expanded[key])
            return {key: expand(child) for key, child in value.items()}
        if isinstance(value, list):
            return [expand(child) for child in value]
        return value

    result = expand(read_json(Path(packet) / 'projection.json'))
    if used != set(values):
        raise AssertionError('Unused pooled value')
    return result


def verify_all(packet, live_root, expected_manifest_sha256):
    packet, live_root = Path(packet), Path(live_root)
    verify_manifest(packet, expected_manifest_sha256)
    checks = []

    def eq(label, actual, expected=True):
        if actual != expected:
            raise AssertionError(label + ': ' + repr(actual) + ' != ' + repr(expected))
        checks.append(label)

    pins = read_json(packet / 'current-source-pins.json')
    for relative, digest in pins.items():
        eq('current-source:' + relative, sha((live_root / safe_rel(relative)).read_bytes()), digest)
    clauses = read_json(packet / 'original-clauses.json')
    spec = (live_root / 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8').splitlines()
    for clause in clauses['excerpts']:
        eq('original-clause:' + clause['id'], '\n'.join(spec[clause['start_line'] - 1:clause['end_line']]), clause['text'])
    original_rows = read_json(packet / 'original-ledger-rows.json')
    found = {}

    def rows(value):
        if isinstance(value, dict):
            if value.get('id') in original_rows:
                eq('unique-ledger:' + value['id'], value['id'] not in found)
                found[value['id']] = value
            for child in value.values():
                rows(child)
        elif isinstance(value, list):
            for child in value:
                rows(child)

    rows(read_json(live_root / 'docs/acceptance-rebuild-ledger.json'))
    for case, row in original_rows.items():
        for key in ('id', 'scenario', 'requirement', 'verification_layer'):
            eq('original-ledger:' + case + ':' + key, found[case][key], row[key])
        eq('original-layer:' + case, row['verification_layer'], 'L+C')
    mapping = read_json(packet / 'projection-map.json')
    eq('original-archive-hash', mapping['original_archive']['sha256'], ORIGINAL_ARCHIVE)
    eq('original-archive-members', mapping['original_archive']['members'], 320)
    eq('declared-projection', mapping['claims']['byte_identical_archive'], False)
    eq('no-private-chain-reconstruction', mapping['claims']['publicly_reconstructs_original_archive'], False)
    suite = (packet / 'tests/terminal_suite.py').read_text(encoding='utf-8')
    body = suite[suite.index('TRACE={}'):]
    body_map = next(row for row in mapping['mapping'] if row['public'] == 'tests/terminal_suite.py')
    eq('original-terminal-behavior-body', sha(body.encode('utf-8')), body_map['preserved_behavior_body_sha256'])
    for filename in ('current-source-pins.json',):
        origin = next(row for row in mapping['mapping'] if row['public'] == filename)
        eq('exact-source-extract:' + filename, sha((packet / filename).read_bytes()), origin['original_member_sha256'])
    clause_origin = next(row for row in mapping['mapping'] if row['public'] == 'original-clauses.json')
    eq('relative-clause-source', clauses['source_path'], 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md')
    eq('clause-original-source-hash', clauses['source_sha256'], pins[clauses['source_path']])
    eq('unchanged-clause-content', sha(canonical({k: v for k, v in clauses.items() if k != 'source_path'})), clause_origin['retained_fields_sha256'])
    evidence = load_projection(packet)
    eq('public-format', evidence['format'], 'guardian-public-upgrade-evidence/2')
    eq('generations', set(evidence['generations']), set(SCENARIOS))
    counts, failures, fresh = {}, [], {}
    seen, units, calls = set(), 0, 0
    for generation, scenario_ids in SCENARIOS.items():
        eq('scenario-inventory:' + generation, evidence['generations'][generation]['scenario_ids'], scenario_ids)
        meta = evidence['generations'][generation]
        eq('source-tuple-size:' + generation, len(meta['source_pins']), 16)
        if generation == 'revision4':
            for relative, digest in meta['source_pins'].items():
                eq('fresh-source:' + relative, pins[relative], digest)
        nt = ni = nf = 0
        for sid in scenario_ids:
            history, previous, committed, event_ids = [], None, None, set()
            trajectory = [row for row in evidence['turns'] if (row['generation'], row['scenario']) == (generation, sid)]
            eq('nonempty-trajectory:' + generation + '/' + sid, bool(trajectory))
            for turn in trajectory:
                label = generation + '/' + sid + '/' + str(turn['step'])
                eq('unique-turn:' + label, label not in seen)
                seen.add(label)
                eq('turn-id:' + label, turn['id'], label)
                eq('turn-sequence:' + label, turn['step'], len(history) + 1)
                eq('original-user-text:' + label, sha(turn['user'].encode('utf-8')), turn['original_user_sha256'])
                eq('original-assistant-text:' + label, sha(turn['assistant'].encode('utf-8')), turn['original_assistant_sha256'])
                eq('previous-actual-assistant:' + label, turn['previous_assistant_sha256'], previous)
                eq('public-dialogue-chain:' + label, sha(canonical(history)), turn['public_history_sha256'])
                derived_units = answer_units(turn['assistant'])
                eq('every-answer-unit:' + label, [sha(u.encode('utf-8')) for u in derived_units], [u['sha256'] for u in turn['answer_units']])
                eq('content-review:' + label, all(u['content_verdict'] == 'pass' for u in turn['answer_units']))
                eq('review-rationale:' + label, bool(turn['review']['finding']))
                units += len(derived_units)
                for invocation in turn['invocations']:
                    ni += 1
                    eq('unique-invocation:' + label, invocation['id'] not in event_ids)
                    event_ids.add(invocation['id'])
                    eq('committed-input:' + label, invocation['state_before'], committed)
                    current = copy.deepcopy(committed)
                    for index, call in enumerate(invocation['calls']):
                        calls += 1
                        eq('exact-call-input:' + label, call['state_before'], current)
                        if call['status'] == 'returned':
                            if call['method'] in MUTATORS:
                                current = call['result']
                            if call['method'] == 'assessment':
                                eq('G3-blocked:' + label, call['result']['G3']['status'], 'blocked')
                            if isinstance(current, dict) and 'context' in current:
                                eq('PC0:' + label, current['context']['contact_phase'], 'PC0')
                                eq('no-purchase:' + label, current['context']['purchase_completed'], False)
                                eq('no-save-consent:' + label, current['persistence_consent'], {'private_save': False, 'export': False, 'public_export': False})
                                eq('not-live-observed:' + label, current['current_subscription']['status'] != 'observed_active')
                        else:
                            eq('recorded-call-error:' + label, call['status'], 'raised')
                            eq('failed-last-call:' + label, index, len(invocation['calls']) - 1)
                            eq('failed-invocation:' + label, invocation['status'], 'raised')
                            eq('same-error-type:' + label, call['error_type'], invocation['error_type'])
                            eq('same-error:' + label, call['error'], invocation['error'])
                    if invocation['status'] == 'returned':
                        eq('all-executed-calls-returned:' + label, all(c['status'] == 'returned' for c in invocation['calls']))
                        if invocation['state_committed']:
                            committed = current
                    else:
                        nf += 1
                        eq('no-partial-commit:' + label, invocation['state_committed'], False)
                        eq('failed-exit:' + label, invocation['exit_code'], 2)
                        failures.append((generation, sid, turn['step'], invocation['id'], invocation['error_type'], invocation['error']))
                    eq('atomic-transaction-output:' + label, invocation['state_after'], committed)
                eq('turn-state:' + label, turn['state_after'], committed)
                if generation == 'revision4':
                    fresh[(sid, turn['step'])] = committed
                history.append({'step': turn['step'], 'user': turn['user'], 'assistant': turn['assistant']})
                previous = turn['original_assistant_sha256']
                nt += 1
        counts[generation] = {'turns': nt, 'invocations': ni, 'invocation_failures': nf}
        eq('declared-turn-count:' + generation, nt, meta['turns'])
    eq('complete-turn-inventory', len(seen), len(evidence['turns']))
    eq('revision3-counts', counts['revision3'], {'turns': 42, 'invocations': 60, 'invocation_failures': 7})
    eq('revision4-counts', counts['revision4'], {'turns': 6, 'invocations': 8, 'invocation_failures': 0})
    eq('all-recorded-calls', calls, 186)
    eq('all-answer-units', units, 208)
    eq('retained-failed-turns', [t['id'] for t in evidence['turns'] if t['review']['verdict'] == 'fail'], ['revision3/d02b/2', 'revision3/d02b/3', 'revision3/d03b/2', 'revision3/d03b/3'])
    for sid, component in [('d02b', 'billing_channel'), ('d03b', 'plan')]:
        original = fresh[(sid, 1)]['facts']['Q-P02']
        for step in (2, 3):
            fact = fresh[(sid, step)]['facts']['Q-P02']
            eq('fresh-terminal:' + sid + ':' + str(step), (fact['state'], fact['value']), ('declined', None))
            eq('fresh-preserved-complement:' + sid + ':' + str(step), fact['retained_fields'][component], {**{k: original[k] for k in ('state', 'source', 'subject_ref', 'observed_at')}, 'value': original['value'][component]})
    logic = evidence['logic']
    before, after = logic['terminal_revision3'], logic['terminal_revision4']
    eq('historical-six-failures', before['results'], {'tests': 9, 'failures': 6, 'errors': 0, 'skips': 0})
    eq('current-nine-pass', after['results'], {'tests': 9, 'failures': 0, 'errors': 0, 'skips': 0})
    for gap in ('current_plan', 'current_channel'):
        for state in ('unknown', 'declined', 'deferred'):
            key = gap + '-' + state
            eq('old-double-gap:' + key, before[key]['assessment']['upgrade_scope']['current_order_gaps'], ['current_plan', 'current_channel'])
            eq('new-single-gap:' + key, after[key]['assessment']['upgrade_scope']['current_order_gaps'], [gap])
            eq('new-no-repeat:' + key, after[key]['next_question'], None)
    t80 = logic['all_covered_conflict']
    eq('covered-before', t80['before']['assessment']['G2']['status'], 'pass')
    eq('covered-after-G1', t80['after']['assessment']['G1']['status'], 'complete')
    eq('covered-after-G2', t80['after']['assessment']['G2']['reason'], 'subscription_conflict_unresolved')
    eq('covered-after-G3', t80['after']['assessment']['G3']['status'], 'blocked')
    eq('covered-no-question', t80['after']['question'], None)
    eq('CLI-input-unchanged', t80['cli']['input_unchanged'])
    eq('CLI-no-save', t80['cli']['stdout_json']['saved'], False)
    eq('CLI-no-action', t80['cli']['stdout_json']['action_executed'], False)
    eq('CLI-conflict-not-ready', t80['cli']['stdout_json']['assessment']['G2']['reason'], 'subscription_conflict_unresolved')
    drift = evidence['failures']['revision3_source_drift']
    eq('three-source-drifts', len(drift['drift']), 3)
    eq('source-check-failed', drift['exit_code'], 1)
    eq('old-responder-bundle-unchanged', drift['responder_bundle_unchanged'])
    error = evidence['failures']['revision3_d06b_turn2']
    eq('retained-temporary-error', error['category'], 'TypeError')
    eq('temporary-error-no-mutation', error['state_changed'], False)
    eq('temporary-error-recovered', error['recovered'])
    return {'status': 'pass_for_public_projection_and_exact_source_only', 'checks': len(checks),
            'generations': counts, 'retained_helper_failures': failures,
            'answer_units': units, 'calls': calls}
