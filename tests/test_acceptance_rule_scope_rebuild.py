"""Retained observed-response integrity and actual helper replay, not prose generation."""
from copy import deepcopy
from pathlib import Path
import ast
import base64
import difflib
import json
import os
import subprocess
import sys
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(Path(__file__).resolve().parent))
import rule_scope_evidence_replay as replay
DATA = ROOT / 'docs' / 'evidence' / 'rule-scope'
OBS = DATA / 'observed'
CASE_IDS = ('ENV-T38', 'ENV-T39', 'ENV-T41', 'ENV-T42', 'ENV-T58')


def trace_args(call):
    return replay.decode(replay.read_json(OBS / 'traces' / call / 'input.json')['positional_arguments'])


def expected_output(call):
    return replay.read_json(OBS / 'traces' / call / 'output.json')


def private(call):
    return replay.decode(expected_output(call)['private_material'])


class RuleScopeRetainedEvidenceTests(unittest.TestCase):
    def test_exact_original_corpus_manifest_and_all_hashes(self):
        manifest = OBS / 'SHA256SUMS'
        self.assertEqual(replay.sha(manifest.read_bytes()),
                         'da69275c8144b5aa4f423579d36f3cd366bf44e71732084cd45610a17bb15a04')
        names = set()
        for line in manifest.read_text(encoding='utf-8').splitlines():
            digest, name = line.split('  ', 1)
            self.assertFalse(Path(name).is_absolute())
            self.assertNotIn('..', Path(name).parts)
            self.assertNotIn(name, names)
            names.add(name)
            self.assertEqual(replay.sha((OBS / name).read_bytes()), digest, name)
        self.assertEqual(len(names), 134)
        actual = {path.relative_to(OBS).as_posix() for path in OBS.rglob('*') if path.is_file()}
        self.assertEqual(actual, names | {'SHA256SUMS'})
        self.assertEqual(replay.sha((OBS / 'provenance-manifest.json').read_bytes()),
                         'eb801a764897a6acbc5818d2ecf09adbadbfbf230fb8162d99c1f1bd40d6f646')

    def test_inputs_and_original_conditions_match_pre_generation_freeze(self):
        frozen = replay.read_json(DATA / 'pre-generation-freeze-manifest.json')['files']
        for path in (OBS / 'inputs').rglob('*'):
            if path.is_file():
                relative = path.relative_to(OBS / 'inputs').as_posix()
                self.assertEqual(replay.sha(path.read_bytes()), frozen['generator-inputs/' + relative])
        for name in ('original-clauses.json', 'evaluation-rubric.json'):
            self.assertEqual(replay.sha((DATA / name).read_bytes()), frozen['review-only/' + name])
        clauses = replay.read_json(DATA / 'original-clauses.json')
        source = ROOT / clauses['source']['path']
        self.assertEqual(replay.sha(source.read_bytes()), clauses['source']['sha256'])
        source_rows = source.read_text(encoding='utf-8').splitlines(keepends=True)
        tracker_rows = (ROOT / clauses['tracker']['path']).read_text(encoding='utf-8').splitlines(keepends=True)
        for row in clauses['cases']:
            self.assertEqual(source_rows[row['D_ENV_line'] - 1], row['D_ENV_verbatim_row'])
            self.assertEqual(tracker_rows[row['tracker_line'] - 1], row['tracker_verbatim_row'])
            self.assertEqual(row['original_layer'], 'L + C')
        for item in clauses['verbatim_context']:
            start, end = item['lines']
            self.assertEqual(''.join(source_rows[start - 1:end]), item['text'])

    def test_current_sources_equal_exact_snapshots_and_prior_known_pins(self):
        provenance = replay.read_json(OBS / 'provenance-manifest.json')
        prior = replay.read_json(DATA / 'pre-generation-baseline-source-pins.json')['sha256']
        guides = replay.read_json(DATA / 'pre-generation-guidance-source-pins.json')['files']
        self.assertEqual(len(provenance['source_hashes']), 14)
        for source in provenance['source_hashes']:
            name = source['repository_path']
            self.assertEqual(replay.sha((ROOT / name).read_bytes()), source['sha256'], name)
            self.assertEqual((ROOT / name).read_bytes(), (OBS / source['saved_copy']).read_bytes())
            self.assertEqual(source['hash_capture_stage'],
                             'final packaging; no initial pre-call source hash was separately logged')
            if name in guides:
                self.assertEqual(source['sha256'], guides[name]['candidate_sha256'])
            elif name in prior:
                self.assertEqual(source['sha256'], prior[name])

    def test_actual_saved_dialogues_keep_full_prior_turns_and_response_bytes(self):
        scenarios = replay.read_json(OBS / 'inputs/scenarios.json')
        events = [json.loads(line) for line in (OBS / 'events.jsonl').read_text(encoding='utf-8').splitlines()]
        response_events = [item for item in events if item['kind'] == 'response_saved']
        self.assertEqual(len(response_events), 11)
        expected_order = []
        for case_id in scenarios['scenario_order']:
            case = next(item for item in scenarios['cases'] if item['id'] == case_id)
            conversation = '# ' + case_id + '：离线合成对话\n\n' + scenarios['common_context']['notice'] + '\n\n'
            for turn in case['turns']:
                number = turn['turn']
                path = OBS / 'responses' / ('%s-turn-%d.md' % (case_id, number))
                response = path.read_text(encoding='utf-8')
                # Reconstruction concatenates already-written immutable prose. It never generates an answer.
                conversation += '## 第 %d 轮 · 用户\n\n%s\n\n## 第 %d 轮 · Claude-Guardian\n\n' % (number, turn['user'], number)
                conversation += response + '\n\n'
                self.assertEqual(conversation, (OBS / 'conversations' / ('%s-through-turn-%d.md' % (case_id, number))).read_text(encoding='utf-8'))
                expected_order.append((case_id, number))
                event = next(item for item in response_events if item['case_id'] == case_id and item['turn'] == number)
                self.assertEqual(event['sha256'], replay.sha(path.read_bytes()))
        self.assertEqual([(item['case_id'], item['turn']) for item in response_events], expected_order)

    def test_all_22_actual_helper_calls_replay_complete_results_without_mutation_or_io(self):
        results = replay.replay_observed(ROOT, DATA)
        self.assertEqual(len(results), 22)
        self.assertEqual(sum(item['status'] == 'error' for item in results.values()), 2)
        self.assertTrue(all(item['arguments_unchanged'] for item in results.values()))
        self.assertTrue(all(not any(item['instrumented_api_call_counts'].values()) for item in results.values()))

    def test_all_six_complete_candidates_preserve_every_unselected_byte(self):
        selected = {
            'ENV-T39-turn-2-compile': ['DOMAIN,api.workflow.invalid,approved-group'],
            'ENV-T41-turn-2-compile': ['DOMAIN,guardian.ingest.sentry.invalid,approved-group'],
            'ENV-T42-turn-1-compile': ['DOMAIN,api.workflow.invalid,approved-group', 'DOMAIN,downloads.workflow.invalid,approved-group'],
            'ENV-T42-turn-3-compile': ['DOMAIN,api.workflow.invalid,approved-group', 'DOMAIN,downloads.workflow.invalid,approved-group', 'DOMAIN,connector.workflow.invalid,approved-group'],
            'ENV-T58-turn-1-compile': ['DOMAIN,api.workflow.invalid,approved-group'],
        }
        original = (OBS / 'inputs/fixtures/owned-rules-extension.yaml').read_bytes()
        base = (OBS / 'inputs/fixtures/effective-base.yaml').read_bytes()
        for call, rules in selected.items():
            with self.subTest(call=call):
                mat = private(call)
                insertion = ', '.join("'" + rule + "'" for rule in rules).encode('ascii')
                expected = original.replace(b'prepend: []', b'prepend: [' + insertion + b']')
                self.assertEqual(mat['original_bytes'], original)
                self.assertEqual(mat['candidate_bytes'], expected)
                self.assertEqual(trace_args(call)[1], base)
                offset, before, after = mat['byte_insertion']
                self.assertEqual(before, b'')
                self.assertEqual(original[:offset] + after + original[offset:], expected)
        call = 'ENV-T38-turn-2-compile'
        mat = private(call)
        original = (OBS / 'inputs/fixtures/env-t38-config.yaml').read_bytes()
        expected = original.replace(b'DOMAIN,api.workflow.invalid,Old #', b'DOMAIN,api.workflow.invalid,approved-group #')
        self.assertEqual(mat['original_bytes'], original)
        self.assertEqual(mat['candidate_bytes'], expected)
        self.assertEqual(len(mat['policy_token_edits']), 1)
        start, end, old, new = mat['policy_token_edits'][0]
        self.assertEqual(original[start:end], old)
        self.assertEqual(old, b'Old')
        self.assertEqual(new, b'approved-group')
        self.assertEqual(original[:start] + new + original[end:], expected)
        self.assertEqual(original.split(b'rules:\n')[0], expected.split(b'rules:\n')[0])
        for call in list(selected) + ['ENV-T38-turn-2-compile']:
            mat = private(call)
            expected_diff = ''.join(difflib.unified_diff(mat['original_bytes'].decode('utf-8').splitlines(keepends=True),
                mat['candidate_bytes'].decode('utf-8').splitlines(keepends=True), fromfile='original-supplied-snapshot',
                tofile='unapplied-candidate', n=100000))
            directory = OBS / 'traces' / call
            self.assertEqual((directory / 'candidate.yaml').read_bytes(), mat['candidate_bytes'])
            self.assertEqual((directory / 'original.yaml').read_bytes(), mat['original_bytes'])
            self.assertEqual((directory / 'complete.diff').read_text(encoding='utf-8'), expected_diff)

    def test_env39_both_mixed_failures_are_retained_without_partial_planning(self):
        provenance = replay.read_json(OBS / 'provenance-manifest.json')
        calls = [item['call_id'] for item in provenance['actual_helper_call_order'] if item['call_id'].startswith('ENV-T39')]
        self.assertEqual(calls, ['ENV-T39-turn-1-import-domain-first', 'ENV-T39-turn-1-import-cidr-first',
                                'ENV-T39-turn-2-import-exact', 'ENV-T39-turn-2-semantic', 'ENV-T39-turn-2-compile'])
        for order in ('domain-first', 'cidr-first'):
            call = 'ENV-T39-turn-1-import-' + order
            directory = OBS / 'traces' / call
            error = replay.read_json(directory / 'error.json')
            self.assertEqual(error['message'], 'UNSUPPORTED_RULE_RECORD')
            self.assertFalse((directory / 'output.json').exists())
            self.assertFalse((directory / 'candidate.yaml').exists())
            self.assertEqual(trace_args(call)[0], (OBS / 'inputs/fixtures' / ('env-t39-mixed-' + order + '.yaml')).read_bytes())
        independent = trace_args('ENV-T39-turn-2-import-exact')
        self.assertEqual(independent[0], (OBS / 'inputs/fixtures/env-t39-supported-source.txt').read_bytes())
        self.assertEqual(independent[3]['source_ref'], 'source-api-exact')

    def test_env41_all_handwritten_host_outcomes_and_label_boundaries(self):
        rows = replay.read_json(OBS / 'ENV-T41-turn-2-host-matrix.json')['rows']
        expected = {
            'guardian.ingest.sentry.invalid': ('SharedTelemetry', 'approved-group'),
            'other.ingest.sentry.invalid': ('SharedTelemetry', 'SharedTelemetry'),
            'corp.sentry.invalid': ('Corp', 'Corp'), 'sentry.invalid': ('SharedTelemetry', 'SharedTelemetry'),
            'unrelated-sentry.example.invalid': ('General', 'General'),
            'datadoghq.com': ('Work', 'Work'), 'sub.datadoghq.com': ('Work', 'Work'),
            'browser-intake-us5-datadoghq.com': ('DIRECT', 'DIRECT'),
            'sift.invalid': ('Payments', 'Payments'), 'shop.sift.invalid': ('Payments', 'Payments'),
            'rescue.example.invalid': ('DIRECT', 'DIRECT'), 'work.example.invalid': ('General', 'General')}
        self.assertEqual({row['host']: (row['before']['action'], row['after']['action']) for row in rows}, expected)
        for row in rows:
            if row['host'] != 'guardian.ingest.sentry.invalid':
                self.assertEqual(row['before']['rule'], row['after']['rule'])
            if row['host'] in ('browser-intake-us5-datadoghq.com', 'unrelated-sentry.example.invalid'):
                self.assertEqual(row['matching_hypothetical_suffixes'], [])
        # Independently calculate every complete match object, including first index.
        matrix = replay.read_json(OBS / 'ENV-T41-turn-2-host-matrix.json')
        def first(host, rules):
            for index, rule in enumerate(rules):
                fields = rule.split(',')
                kind = fields[0]
                match = kind == 'MATCH' or (kind == 'DOMAIN' and host == fields[1]) or (
                    kind == 'DOMAIN-SUFFIX' and (host == fields[1] or host.endswith('.' + fields[1])))
                if match:
                    return {'index': index, 'rule': rule, 'action': fields[-1]}
            return None
        for row in rows:
            self.assertEqual(row['before'], first(row['host'], matrix['before_rules']))
            self.assertEqual(row['after'], first(row['host'], matrix['after_rules']))
        broad = replay.read_json(OBS / 'ENV-T41-turn-1-keyword-analysis.json')
        self.assertEqual(sum(row['before']['action'] != row['hypothetical_after']['action'] for row in broad['rows']), 10)

    def test_env42_preimport_selection_full_provenance_and_one_feature_delta(self):
        facts = replay.read_json(OBS / 'inputs/fixtures/env-t42-feature-facts.json')
        one = replay.read_json(OBS / 'ENV-T42-turn-1-selection.json')
        three = replay.read_json(OBS / 'ENV-T42-turn-3-selection.json')
        self.assertEqual(one['facts'], facts)
        self.assertEqual([item['source_ref'] for item in one['selected_sources']], ['source-core', 'source-download'])
        self.assertEqual(three['original_facts'], facts)
        revised = deepcopy(facts)
        revised['facts'][2]['enabled'] = True
        self.assertEqual(three['updated_facts'], revised)
        for turn, features in ((1, ('core', 'download')), (3, ('core', 'download', 'connector'))):
            joined_rules, joined_order = {}, []
            for feature in features:
                call = 'ENV-T42-turn-%d-import-feature-%s' % (turn, feature)
                args = trace_args(call)
                source = next(item for item in facts['sources'] if item['feature_alias'] == 'feature-' + feature)
                self.assertEqual(args[0], (OBS / 'inputs' / source['file']).read_bytes())
                self.assertEqual(args[3]['expected_sha256'], source['sha256'])
                self.assertEqual(args[3]['version_scope'], source['version_scope'])
                self.assertEqual(args[3]['source_ref'], source['source_ref'])
                self.assertEqual(args[3]['feature_gate'], source['feature_alias'])
                components = expected_output(call)['binding_components']
                joined_rules.update(components['rules'])
                joined_order.extend(components['rule_order'])
                self.assertEqual(private(call)['source_bytes'], args[0])
            binding = trace_args('ENV-T42-turn-%d-compile' % turn)[3]
            self.assertEqual(binding['rules'], joined_rules)
            self.assertEqual(binding['rule_order'], joined_order)
        self.assertEqual(trace_args('ENV-T42-turn-1-compile')[0], trace_args('ENV-T42-turn-3-compile')[0])
        all_calls = [item['call_id'] for item in replay.read_json(OBS / 'provenance-manifest.json')['actual_helper_call_order']]
        self.assertFalse(any('bridge' in item or 'combined' in item for item in all_calls))

    def test_env58_pending_categories_absent_from_default_and_helper_inputs(self):
        plan = replay.read_json(OBS / 'ENV-T58-turn-1-default-plan.json')
        self.assertEqual(len(plan['selected_default']), 1)
        self.assertEqual(plan['selected_default'][0]['exact_host'], 'api.workflow.invalid')
        self.assertEqual(plan['actual_host_or_endpoint_operations'], [])
        self.assertEqual([item['proposal_ref'] for item in plan['excluded_from_default']],
                         ['proposal-endpoint', 'proposal-dependency', 'proposal-release'])
        self.assertTrue(all(item['adoption_state'] == 'recommendation_pending' and item['default_action'] is None
                            for item in plan['excluded_from_default']))
        for call in ('ENV-T58-turn-1-import-exact', 'ENV-T58-turn-1-semantic', 'ENV-T58-turn-1-compile'):
            text = json.dumps(replay.read_json(OBS / 'traces' / call / 'input.json'), ensure_ascii=True)
            for item in plan['supplied_proposals']['new_proposals']:
                self.assertNotIn(item['proposal_ref'], text)
                self.assertNotIn(item['value'], text)
        self.assertEqual(trace_args('ENV-T58-turn-1-compile')[2]['intent']['rule_refs'], ['rule-core'])

    def test_all_semantic_outputs_preserve_ipv4_conflict_and_native_limits(self):
        semantic = list((OBS / 'traces').glob('*-semantic/output.json'))
        self.assertEqual(len(semantic), 6)
        for path in semantic:
            result = replay.read_json(path)['result']
            policy = result['traffic_policy']
            self.assertIn('IPV4_ONLY_INTENT_CONFLICT', policy['reason_codes'])
            self.assertEqual(policy['compliance'], 'not_established')
            self.assertFalse(result['apply_supported'])
            self.assertEqual([item['kind'] for item in result['proposed_changes']], ['bind_selected_rules'])

    def test_frozen_reviewer_supplement_replays_exactly_and_stays_distinct(self):
        actual = replay.replay_supplement(ROOT, DATA)
        self.assertEqual(len(actual), 10)
        self.assertEqual(actual, replay.read_json(DATA / 'supplemental/observed-results.json'))
        self.assertTrue(all(call.startswith('review-') for call in actual))
        self.assertEqual(actual['review-ENV-T41-protected-selected-host']['error']['message'],
                         'PROTECTED_RULE_PRIORITY_CONFLICT')
        self.assertEqual(actual['review-ENV-T58-fixed-selector-baseline']['output'],
                         actual['review-ENV-T58-fixed-selector-untrusted-fields']['output'])

    def test_independent_review_covers_each_original_clause_and_response_lines(self):
        review = replay.read_json(DATA / 'independent-case-review.json')
        self.assertEqual([item['id'] for item in review['cases']], list(CASE_IDS))
        originals = {item['id']: item for item in replay.read_json(DATA / 'original-clauses.json')['cases']}
        for case in review['cases']:
            self.assertEqual(case['verdict'], 'supported_observed_L_plus_C')
            self.assertEqual(case['original_requirement'], originals[case['id']]['original_requirement'])
            self.assertEqual(case['original_layer'], originals[case['id']]['original_layer'])
            self.assertTrue(case['clause_reviews'])
            covered = {}
            for finding in case['clause_reviews']:
                self.assertTrue(finding['assessment'])
                for citation in finding['response_citations']:
                    path = OBS / citation['path']
                    count = len(path.read_text(encoding='utf-8').splitlines())
                    start, end = citation['lines']
                    self.assertTrue(1 <= start <= end <= count)
                    covered.setdefault(citation['path'], set()).update(range(start, end + 1))
            for path in (OBS / 'responses').glob(case['id'] + '-turn-*.md'):
                nonempty = {i for i, line in enumerate(path.read_text(encoding='utf-8').splitlines(), 1) if line.strip()}
                self.assertTrue(nonempty <= covered[path.relative_to(OBS).as_posix()])

    def test_replay_is_portable_under_cp1252_and_c_locale(self):
        env = dict(os.environ, PYTHONIOENCODING='cp1252', PYTHONUTF8='0',
                   PYTHONCOERCECLOCALE='0', LC_ALL='C', PYTHONDONTWRITEBYTECODE='1')
        command = [sys.executable, '-B', str(ROOT / 'tests/rule_scope_evidence_replay.py')]
        process = subprocess.run(command, cwd=ROOT, env=env, capture_output=True, timeout=60)
        self.assertEqual(process.returncode, 0, process.stderr.decode('ascii', errors='backslashreplace'))
        result = json.loads(process.stdout.decode('ascii'))
        self.assertEqual(len(result['observed_calls']), 22)
        self.assertEqual(len(result['reviewer_supplemental_calls']), 10)
        self.assertEqual(result['observed_calls'], replay.replay_observed(ROOT, DATA))

    def test_reviewer_records_remain_byte_pinned(self):
        manifest = DATA / 'reviewer-data-sha256.json'
        self.assertEqual(replay.sha(manifest.read_bytes()), '6d163b6c57bfbffdf3a220a5b1396365f8302ba282fe23fff095203a1c88ef65')
        for name, digest in replay.read_json(manifest).items():
            self.assertEqual(replay.sha((DATA / name).read_bytes()), digest, name)

    def test_new_review_tools_parse_as_python310(self):
        for name in ('rule_scope_evidence_replay.py', 'test_acceptance_rule_scope_rebuild.py'):
            ast.parse((ROOT / 'tests' / name).read_text(encoding='utf-8'), feature_version=(3, 10))


if __name__ == '__main__':
    unittest.main()
