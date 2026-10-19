"""Public T77/T80 projection checks; no model generator or private-record access."""
import ast
import copy
import importlib.util
import json
import os
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest import mock

PACKAGE = Path(__file__).resolve().parents[1]
ROOT = Path(os.environ['GUARDIAN_AUDIT_ROOT']) if 'GUARDIAN_AUDIT_ROOT' in os.environ else PACKAGE.parents[2]
EXPECTED = os.environ['GUARDIAN_UPGRADE_EXPECTED_MANIFEST']
spec = importlib.util.spec_from_file_location('guardian_upgrade_public_verifier', PACKAGE / 'tests/verify_packet.py')
V = importlib.util.module_from_spec(spec)
spec.loader.exec_module(V)
V.verify_manifest(PACKAGE, EXPECTED)
EVIDENCE = V.load_projection(PACKAGE)


def flow():
    scripts = ROOT / 'skills/claude-guardian/scripts'
    sys.path.insert(0, str(scripts))
    try:
        spec = importlib.util.spec_from_file_location('guardian_upgrade_public_current_flow', scripts / 'interview_flow.py')
        module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(module)
        return module
    finally:
        sys.path.pop(0)


def replay_current_calls():
    f, rows = flow(), []
    for turn in EVIDENCE['turns']:
        generation, sid = turn['generation'], turn['scenario']
        if generation == 'revision3' and sid in ('d02b', 'd03b'):
            continue  # Preserved failing revision3 state; never relabeled revision4.
        for invocation in turn['invocations']:
            for index, call in enumerate(invocation['calls']):
                seq, used = iter(call['clock_values']), []

                def now():
                    value = next(seq)
                    used.append(value)
                    return value

                old = f._now
                f._now = now
                before = copy.deepcopy(call['state_before'])
                args, kwargs = copy.deepcopy(call['args']), copy.deepcopy(call['kwargs'])
                if call['method'] != 'new_state':
                    args.insert(0, before)
                try:
                    result = getattr(f, call['method'])(*args, **kwargs)
                    if call['status'] != 'returned' or result != call['result']:
                        raise AssertionError('Current-source compatibility changed: ' + turn['id'] + ' ' + call['method'])
                    status = 'returned_exact'
                except Exception as exc:
                    if call['status'] == 'raised' and type(exc).__name__ == call['error_type'] and str(exc) == call['error']:
                        status = 'same_recorded_error'
                    else:
                        raise
                finally:
                    f._now = old
                if before != call['state_before']:
                    raise AssertionError('Current API mutated an input: ' + turn['id'])
                if used != call['clock_values']:
                    raise AssertionError('Current API consumed different recorded clocks: ' + turn['id'])
                rows.append({'generation': generation, 'scenario': sid, 'turn': turn['step'],
                             'event': invocation['id'], 'call': index, 'method': call['method'],
                             'status': status, 'source_receipt_sha256': invocation['original_record_sha256'],
                             'clock_values_replayed': used})
    return rows


class RetainedUpgradeConflictEvidence(unittest.TestCase):
    def test_public_packet_source_original_clauses_and_all_turn_chains(self):
        result = V.verify_all(PACKAGE, ROOT, EXPECTED)
        self.assertEqual(result['answer_units'], 208)
        self.assertEqual(result['generations']['revision3']['turns'], 42)
        self.assertEqual(result['generations']['revision4']['turns'], 6)
        self.assertEqual(result['calls'], 186)
        self.assertEqual(len(result['retained_helper_failures']), 7)

    def test_historical_successes_and_fresh_calls_compatible_with_current_source(self):
        actual = replay_current_calls()
        self.assertEqual(actual, EVIDENCE['current_replay']['calls'])
        self.assertEqual(len(actual), 163)
        self.assertEqual({r['scenario'] for r in actual if r['generation'] == 'revision3'},
                         {'d01', 'd02a', 'd03a', 'd04a', 'd04b', 'd05a', 'd05b', 'd06a', 'd06b', 'd06c'})
        self.assertEqual({r['scenario'] for r in actual if r['generation'] == 'revision4'}, {'d02b', 'd03b'})
        self.assertEqual(sum(r['status'] == 'same_recorded_error' for r in actual), 6)

    def test_original_terminal_assertions_on_current_runtime(self):
        # Only the import root and log-writing footer were projected; assertions are exact.
        code = "import importlib.util,unittest,sys; s=importlib.util.spec_from_file_location('public_terminal',sys.argv[1]); m=importlib.util.module_from_spec(s); s.loader.exec_module(m); r=unittest.TestResult(); unittest.defaultTestLoader.loadTestsFromTestCase(m.TerminalRetention).run(r); print(r.testsRun,len(r.failures),len(r.errors),len(r.skipped)); sys.exit(not r.wasSuccessful())"
        env = dict(os.environ, GUARDIAN_TERMINAL_REVIEW_ROOT=str(ROOT),
                   PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='cp1252:strict')
        result = subprocess.run([sys.executable, '-B', '-c', code, str(PACKAGE / 'tests/terminal_suite.py')],
                                capture_output=True, env=env, check=False)
        self.assertEqual(result.returncode, 0, result.stderr.decode('cp1252'))
        self.assertEqual(result.stdout.decode('ascii').strip(), '9 0 0 0')

    def test_all_fields_covered_conflict_api_and_real_readonly_cli(self):
        proof, f = EVIDENCE['logic']['all_covered_conflict'], flow()
        for stage in ('before', 'after'):
            self.assertEqual(f.assessment(proof[stage]['state']), proof[stage]['assessment'])
            self.assertEqual(f.next_question(proof[stage]['state']), proof[stage]['question'])
        with tempfile.TemporaryDirectory() as temp:
            path = Path(temp) / 'synthetic-input.json'
            path.write_text(json.dumps(EVIDENCE['logic']['all_covered_cli_input'], ensure_ascii=False), encoding='utf-8')
            before = path.read_bytes()
            env = dict(os.environ, PYTHONIOENCODING='cp1252:strict', PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'skills/claude-guardian/scripts/interview_cli.py'),
                                     '--input', str(path)], capture_output=True, env=env, check=False)
            self.assertEqual(result.returncode, 0, result.stderr.decode('utf-8'))
            self.assertEqual(path.read_bytes(), before)
            self.assertEqual(json.loads(result.stdout.decode('utf-8')), proof['cli']['stdout_json'])

    def test_lifecycle_states_validate_and_preserve_actual_review_obligation(self):
        evidence, f = EVIDENCE['logic']['lifecycle_revision4'], flow()
        count = 0

        def visit(value):
            nonlocal count
            if isinstance(value, dict):
                if value.get('schema_version') == '1.0.0' and 'facts' in value:
                    f.validate_state(value)
                    self.assertEqual(f.loads_state(json.dumps(value, ensure_ascii=False)), value)
                    count += 1
                else:
                    for child in value.values():
                        visit(child)
            elif isinstance(value, list):
                for child in value:
                    visit(child)

        visit(evidence)
        self.assertEqual(count, 46)
        for order in ('terminal-before-interruption', 'terminal-during-interruption'):
            row = evidence[order]
            self.assertIn('Q-P02', row['initial_interruption']['resume_review']['retained_keys'])
            self.assertIn('Q-P02', row['channel_only']['resume_review']['retained_keys'])
            self.assertEqual(f.assessment(row['new_task'])['upgrade_scope']['current_order_gaps'], ['current_plan'])
            self.assertEqual(f.assessment(row['fresh_plan'])['upgrade_scope']['current_order_gaps'], [])
            self.assertEqual(row['actual_unchanged_review']['facts']['Q-P02']['retained_fields'],
                             row['initial_interruption']['facts']['Q-P02']['retained_fields'])
        for qid, schema in f.STATE_SCHEMA['properties']['facts']['properties'].items():
            if qid != 'Q-P02':
                self.assertIs(schema['additionalProperties'], False)
                self.assertNotIn('retained_fields', schema['properties'])
        for component in ('plan', 'channel'):
            for state in ('unknown', 'declined', 'deferred'):
                row = evidence[component + '-' + state]
                self.assertIsNone(f.next_question(row['terminal']))
                self.assertIsNone(f.next_question(row['repeat']))
                self.assertEqual(row['terminal']['facts']['Q-P02']['retained_fields'], row['repeat']['facts']['Q-P02']['retained_fields'])
                self.assertEqual(f.assessment(row['fresh'])['upgrade_scope']['current_order_gaps'], [])
                self.assertEqual(f.assessment(row['fresh'])['G3']['status'], 'blocked')

    def test_modified_evidence_manifest_and_live_source_fail_closed(self):
        with tempfile.TemporaryDirectory() as temp:
            packet = Path(temp) / 'packet'
            shutil.copytree(PACKAGE, packet, ignore=shutil.ignore_patterns('__pycache__'))
            V.verify_manifest(packet, EXPECTED)
            target = packet / 'projection.json'
            original = target.read_bytes()
            target.write_bytes(original + b' ')
            with self.assertRaisesRegex(AssertionError, 'Packet member mismatch: projection.json'):
                V.verify_manifest(packet, EXPECTED)
            target.write_bytes(original)
            (packet / 'manifest.json').write_bytes((packet / 'manifest.json').read_bytes() + b' ')
            with self.assertRaisesRegex(AssertionError, 'literal pin'):
                V.verify_manifest(packet, EXPECTED)
        target, read = ROOT / 'skills/claude-guardian/scripts/interview_flow.py', Path.read_bytes

        def changed(path):
            data = read(path)
            return data + b'\n# simulated drift\n' if path == target else data

        with mock.patch.object(Path, 'read_bytes', changed):
            with self.assertRaisesRegex(AssertionError, 'current-source:skills/claude-guardian/scripts/interview_flow.py'):
                V.verify_all(PACKAGE, ROOT, EXPECTED)

    def test_pooled_semantics_reject_tampering_cycles_and_missing_values(self):
        original = V.read_json(PACKAGE / 'values.json')
        key = next(iter(original))
        real_read = V.read_json
        for replacement, message in [({'changed': True}, 'hash mismatch'),
                                     ({'$value': key}, 'cyclic'),
                                     ({'$value': '0' * 64}, 'Missing')]:
            altered = {**original, key: replacement}

            def fake_read(path):
                return altered if Path(path).name == 'values.json' else real_read(path)

            with mock.patch.object(V, 'read_json', fake_read):
                with self.assertRaisesRegex(AssertionError, message):
                    V.load_projection(PACKAGE)

    def test_historical_run_results_preserved_as_declared_projections(self):
        summary = EVIDENCE['historical_runs']
        for name, count in [('independent-terminal', 9), ('initial12', 12), ('revision1_11', 11), ('schema7', 7), ('owned82', 82)]:
            row = summary[name]
            self.assertEqual({k: row[k] for k in ('tests', 'failures', 'errors', 'skips')},
                             {'tests': count, 'failures': 0, 'errors': 0, 'skips': 0})
            self.assertRegex(row['original_log_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(summary['sources_unchanged'])
        mapping = V.read_json(PACKAGE / 'projection-map.json')
        self.assertFalse(mapping['claims']['byte_identical_archive'])
        self.assertFalse(mapping['claims']['publicly_reconstructs_original_archive'])

    def test_public_inventory_excludes_private_envelopes_and_handles(self):
        self.assertFalse((PACKAGE / 'evidence.zip').exists())
        # Split only these detection literals so the scanner can cover its own source.
        forbidden = ('/' + 'root/', '/' + 'workspace/', '/' + 'home/', '/' + 'opt/',
                     '_' + '_external_', 'cloud_browser' + '_handoff', 'agent' + '-registration',
                     'agent' + '_id', 'readable' + '_paths', 'state_input' + '_sha256',
                     'stdout' + '_path', 'request' + '_path', 'file-service' + '://', 'sediment' + '://')
        for path in PACKAGE.rglob('*'):
            if not path.is_file() or '__pycache__' in path.parts:
                continue
            raw = path.read_text(encoding='utf-8')
            name = path.relative_to(PACKAGE).as_posix()
            for marker in forbidden:
                self.assertNotIn(marker, raw, name + ': ' + marker)
            self.assertNotRegex(raw, r'file_[A-Za-z0-9]{12,}|' + '/' + r'tmp/[^\s"\\]+')
        self.assertEqual(set(EVIDENCE['generations']), {'revision3', 'revision4'})
        for turn in EVIDENCE['turns']:
            self.assertEqual(set(turn), {'id', 'generation', 'scenario', 'step', 'user', 'assistant',
                             'original_user_sha256', 'original_assistant_sha256', 'original_turn_record_sha256',
                             'original_context_sha256', 'previous_assistant_sha256', 'public_history_sha256',
                             'review', 'answer_units', 'invocations', 'state_after'})

    def test_python310_syntax_for_public_tests(self):
        for path in (PACKAGE / 'tests').glob('*.py'):
            ast.parse(path.read_text(encoding='utf-8'), filename=path.name, feature_version=(3, 10))
