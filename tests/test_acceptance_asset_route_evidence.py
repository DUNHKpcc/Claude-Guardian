"""T26/T33 retained-record integrity, not dialogue generation or semantic scoring.

Nine captured replies have an independent whole-response review. These checks
preserve that reviewed evidence, its adaptive chronology and project-only scope.
The separate normalized API suite neither generated nor ran in those dialogues.
"""
import ast
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
PACKET = ROOT / 'docs/evidence/asset-route-v1'
PAGE = ROOT / 'docs/evidence/rebuild-asset-route-cases.md'
MANIFEST_SHA256 = 'fb42ac1f5c3aa86eb3f97c1bd2fd02f2e5e115a2ffa0f0e78ef5d59aaf6b8547'
PAGE_SHA256 = '8e31a9f34aaa5ed191a2eee6721a7633d9754724da156304a23c75f9dd485459'
ORIGINAL_ROWS_SHA256 = '84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9'
RUNTIME_SHA256 = '9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25'
PREDECESSOR_SHA256 = '691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9'
ARTIFACT_SHA256 = {
    'dialogues-projection-public.json': '34d91c661ae36492f0477c1ea46aa3d0f5d6f2d5f2b88e40ebb853db6c253b12',
    'final-semantic-review.json': '72dbb2e28569405e90471b2b1062b5c338fc503bc765c01ab22b4f32429cdacc',
    'final-semantic-review.md': '1b6de6b44d5762694f16d56adab1c1cfd39c24f6fb1abbae63bcc1cda143c12d',
}
ORIGINAL_CASES = {
    'T26': ('用户仅提到有 VPS 或装过 VM',
            '只记资产信息；主动询问实际目标和方案，不把资产当选择，也不静默开始本机部署'),
    'T33': ('用户不懂 VM/VPS 区别',
            '给简短比较，允许接受本机建议；不进行术语考试，不把不知道当选择'),
}
STAGES = [
    {'stage': 'original_six', 'frozen_at': '2026-10-19T01:08:30.769218Z',
     'turns': [[1, 1], [1, 2], [2, 1], [2, 2], [3, 1], [3, 2]], 'adaptive': False},
    {'stage': 'later_two', 'frozen_at': '2026-10-19T01:13:48.926246Z',
     'turns': [[1, 3], [2, 3]], 'adaptive': True,
     'retrospective_source_tool_exchange_retained_in_context': True},
    {'stage': 'fresh_ninth', 'frozen_at': '2026-10-19T01:16:17.577745Z',
     'turns': [[4, 1]], 'adaptive': True, 'fresh_context': True,
     'goal_fully_specified': True, 'input_explicitly_says_asset_is_not_choice': True},
]


def sha(data):
    return hashlib.sha256(data).hexdigest()


def text_sha(text):
    return sha(text.encode('utf-8'))


def canonical_sha(value):
    return text_sha(json.dumps(value, ensure_ascii=False, sort_keys=True, separators=(',', ':')))


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def require(condition, message):
    if not condition:
        raise ValueError(message)


def trusted_manifest():
    path = PACKET / 'evidence-manifest.json'
    require(not path.is_symlink() and sha(path.read_bytes()) == MANIFEST_SHA256,
            'Reviewed manifest changed; renewed review required')
    return read_json(path)


def check_public_text(text):
    # Bounded forbidden-marker checks, not a universal secret sanitizer.
    for marker in ('/workspace/', '/home/', '/tmp/', '/Users/', 'codex://',
                   'library://', 'sediment://', 'cloud_browser_handoff',
                   'Bearer ', '-----BEGIN PRIVATE KEY-----'):
        require(marker not in text, 'Private location, credential or handoff metadata')
    require(re.search(r'[A-Za-z]:[\\/](?:Users|Temp)[\\/]', text) is None,
            'Private desktop path')
    require(re.search(r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b', text) is None,
            'Private identifier-shaped value')
    require(re.search(r'(?:executor|thread|library_file|session)[_-]id["\x27]?\s*[:=]',
                      text, re.IGNORECASE) is None, 'Private coordination metadata')


def validate_projection(value):
    manifest = trusted_manifest()
    require(set(value) == {'sources', 'provenance_limits', 'conversations'},
            'Projection root fields changed')
    expected_sources = [{'document': document, 'sha256': manifest['source_sha256'][path]}
                        for document, path in manifest['dialogue_source_mapping'].items()]
    require(value['sources'] == expected_sources, 'Dialogue source identity changed')
    require(canonical_sha(value['provenance_limits']) == manifest['provenance_limits_sha256'],
            'Retrospective provenance or collection boundary changed')
    conversations = value['conversations']
    require(isinstance(conversations, list) and len(conversations) == 4,
            'Conversation count changed')
    index = {(t['conversation'], t['turn']): t for t in manifest['observed_turns']}
    for i, conversation in enumerate(conversations, 1):
        require(set(conversation) == {'turns'}, 'Conversation fields changed')
        turns = conversation['turns']
        require(isinstance(turns, list) and len(turns) == [3, 3, 2, 1][i - 1],
                'Turn count changed')
        for j, turn in enumerate(turns, 1):
            require(set(turn) == {'user', 'response'}, 'Turn fields changed')
            require(isinstance(turn['user'], str) and isinstance(turn['response'], str),
                    'Turn payload type changed')
            require(text_sha(turn['user']) == index[(i, j)]['user_sha256'],
                    'Frozen user input changed')
            require(text_sha(turn['response']) == index[(i, j)]['response_sha256'],
                    'Captured response changed')
    check_public_text(json.dumps(value, ensure_ascii=False))


def validate_review(value):
    manifest = trusted_manifest()
    require(value['projection_sha256'] == ARTIFACT_SHA256['dialogues-projection-public.json'],
            'Reviewed projection identity changed')
    require(value['retained_coverage_history'] == manifest['coverage_history'],
            'Earlier partial coverage or adaptive history changed')
    expected = [(t['conversation'], t['turn'], t['case']) for t in manifest['observed_turns']]
    actual = [(t['conversation'], t['turn'], t['case']) for t in value['individual_response_review']]
    require(actual == expected, 'Whole-response review coverage changed')
    require(set(value['original_cases']) == set(ORIGINAL_CASES), 'Reviewed cases changed')
    for case_id, (scenario, requirement) in ORIGINAL_CASES.items():
        case = value['original_cases'][case_id]
        require((case['scenario'], case['requirement'], case['layers']) ==
                (scenario, requirement, 'L+C'), 'Original requirement or layers changed')
    check_public_text(json.dumps(value, ensure_ascii=False))


class AssetRouteEvidenceTests(unittest.TestCase):
    def test_manifest_and_casepage_bytes_are_pinned(self):
        manifest = trusted_manifest()
        self.assertFalse(PAGE.is_symlink())
        self.assertEqual(sha(PAGE.read_bytes()), PAGE_SHA256)
        self.assertEqual(manifest['schema_version'], 'guardian-asset-route-evidence/1')
        self.assertEqual(manifest['manifest_role'],
                         'Integration inventory of reviewed public evidence, not a new execution record or independent execution telemetry.')

    def test_exact_three_public_artifacts_and_manifest_inventory(self):
        manifest = trusted_manifest()
        self.assertEqual({p.name for p in PACKET.iterdir()},
                         set(ARTIFACT_SHA256) | {'evidence-manifest.json'})
        self.assertEqual(manifest['artifact_sha256'], ARTIFACT_SHA256)
        for name, expected in ARTIFACT_SHA256.items():
            with self.subTest(artifact=name):
                path = PACKET / name
                self.assertFalse(path.is_symlink())
                self.assertTrue(path.is_file())
                self.assertEqual(sha(path.read_bytes()), expected)
                self.assertEqual(path.stat().st_size, manifest['artifact_bytes'][name])

    def test_original_full_requirements_layers_and_218_row_identity(self):
        manifest = trusted_manifest()
        tracker = (ROOT / 'docs/implementation-tracker.md').read_text(encoding='utf-8').splitlines()
        design = (ROOT / 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8').splitlines()
        rows = [line for line in tracker if re.match(r'^\| (?:T\d+|ENV-T\d+) \|', line)]
        self.assertEqual(len(rows), 218)
        self.assertEqual(text_sha('\n'.join(rows) + '\n'), ORIGINAL_ROWS_SHA256)
        self.assertEqual(manifest['original_rows_sha256'], ORIGINAL_ROWS_SHA256)
        self.assertEqual(set(manifest['cases']), set(ORIGINAL_CASES))
        for case_id, (scenario, requirement) in ORIGINAL_CASES.items():
            row = '| ' + case_id + ' | ' + scenario + ' | ' + requirement + ' |'
            expected = {'scenario': scenario, 'requirement': requirement,
                        'verification_layer': 'L+C', 'literal_design_row': row,
                        'literal_tracker_row': row + ' L+C | 待建立 |',
                        'review_result': 'accepted_revalidated'}
            self.assertEqual(manifest['cases'][case_id], expected)
            self.assertIn(expected['literal_design_row'], design)
            self.assertIn(expected['literal_tracker_row'], tracker)

    def test_current_guidance_runtime_and_reviewed_source_correspondence(self):
        manifest = trusted_manifest()
        for relative, expected in manifest['source_sha256'].items():
            with self.subTest(source=relative):
                path = ROOT / relative
                self.assertFalse(path.is_symlink())
                self.assertEqual(sha(path.read_bytes()), expected,
                                 'Relevant source changed: rerun and re-review before repinning')
        projection = read_json(PACKET / 'dialogues-projection-public.json')
        review = read_json(PACKET / 'final-semantic-review.json')
        document_paths = {
            'D-SPEC-v0.1.10.md': 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md',
            'D-ENV-v0.3.md': 'skills/claude-guardian/sources/design/D-ENV-v0.3.md',
            **manifest['dialogue_source_mapping'],
        }
        self.assertEqual(review['project_sources'],
                         [{'document': name, 'sha256': manifest['source_sha256'][path]}
                          for name, path in document_paths.items()])
        self.assertEqual(projection['sources'], review['project_sources'][2:])
        self.assertEqual(manifest['source_sha256']['skills/claude-guardian/scripts/interview_flow.py'],
                         RUNTIME_SHA256)

    def test_normalized_logic_and_authored_examples_remain_separate(self):
        manifest = trusted_manifest()
        self.assertEqual(set(manifest['logic_evidence_sha256']),
                         {'tests/test_acceptance_asset_route_cases.py',
                          'tests/fixtures/acceptance-asset-route-cases.json'})
        for relative, expected in manifest['logic_evidence_sha256'].items():
            self.assertEqual(sha((ROOT / relative).read_bytes()), expected)
        fixture = read_json(ROOT / 'tests/fixtures/acceptance-asset-route-cases.json')
        self.assertEqual(fixture['evidence_kind'], 'synthetic_normalized_host_inputs_not_executed_model_dialogue')
        for case_id, (scenario, requirement) in ORIGINAL_CASES.items():
            self.assertEqual(fixture['original_requirements'][case_id],
                             {'scenario': scenario, 'requirement': requirement, 'layers': 'L+C'})
            self.assertEqual(fixture['host_review_examples'][case_id]['scope'],
                             'Authored review example, never a generated-helper result')
        for relative, expected in fixture['source_pins'].items():
            self.assertEqual(manifest['source_sha256'][relative], expected)

    def test_all_nine_actual_turns_preserve_exact_inputs_and_responses(self):
        projection = read_json(PACKET / 'dialogues-projection-public.json')
        validate_projection(projection)
        self.assertEqual([len(c['turns']) for c in projection['conversations']], [3, 3, 2, 1])
        self.assertEqual(len(trusted_manifest()['observed_turns']), 9)

    def test_adaptive_three_stage_chronology_and_explicit_asset_disclaimer(self):
        manifest = trusted_manifest()
        self.assertEqual(manifest['collection_stages'], STAGES)
        for stage in STAGES:
            observed = [[t['conversation'], t['turn']] for t in manifest['observed_turns']
                        if t['collection_stage'] == stage['stage']]
            self.assertEqual(observed, stage['turns'])
        projection = read_json(PACKET / 'dialogues-projection-public.json')
        self.assertIn('只是告诉你这项资产，不代表我要在那里用 Claude',
                      projection['conversations'][3]['turns'][0]['user'])
        review = read_json(PACKET / 'final-semantic-review.json')
        validate_review(review)
        self.assertEqual(review['retained_coverage_history']['original_six'],
                         'T26 仅部分覆盖；T33 在该序列内满足。')
        self.assertEqual(review['retained_coverage_history']['later_two'],
                         'T26 仍部分覆盖；没有把相关目的澄清强行判为超时失败。')

    def test_retained_independent_review_is_bounded_and_runtime_runs_are_separate(self):
        review = read_json(PACKET / 'final-semantic-review.json')
        validate_review(review)
        self.assertEqual(review['original_cases']['T26']['semantic_verdict'],
                         'satisfied_within_sampled_cases')
        self.assertEqual(review['original_cases']['T33']['semantic_verdict'],
                         'satisfied_within_observed_sequence')
        runtime = review['runtime_and_tests']
        self.assertEqual(runtime['candidate_runtime_sha256'], RUNTIME_SHA256)
        self.assertEqual(runtime['predecessor_runtime_sha256'], PREDECESSOR_SHA256)
        self.assertEqual([(r['tests'], r['failures'], r['errors']) for r in runtime['independent_runs']],
                         [(31, 0, 0), (31, 5, 0), (293, 0, 0)])
        self.assertIn('最终运行时整合验收仍须来源兼容及完整回归门槛', runtime['decision_boundary'])

    def test_retrospective_source_limits_and_no_helper_generation_claim(self):
        provenance = trusted_manifest()['source_provenance']
        self.assertEqual(provenance, {
            'source_reads': 'retrospective_responder_reports_not_independent_raw_tool_event_exports',
            'source_boundary': 'instruction_limited_shared_filesystem_not_physical_isolation',
            'reported_truncated_tokens': 4620,
            'reported_rereads_cover_gap': True,
            'full_file_hash_proves_full_read': False,
            'reported_helper_invoked_in_observed_dialogues': False,
            'helper_generates_observed_responses': False,
        })
        page = PAGE.read_text(encoding='utf-8')
        self.assertIn('they do not rerun or generate model output', page)
        self.assertIn('its explicit asset disclaimer cannot replace', page)
        self.assertIn('Final aggregate regression and prior-source compatibility are separate integration gates', page)

    def test_public_packet_casepage_and_fixture_exclude_private_metadata(self):
        for path in [*PACKET.iterdir(), PAGE,
                     ROOT / 'tests/fixtures/acceptance-asset-route-cases.json']:
            with self.subTest(artifact=path.name):
                check_public_text(path.read_text(encoding='utf-8'))

    def test_evidence_is_outside_explicit_installed_inventory(self):
        # Inspect the real packager's explicit inventory; actual packaging is a
        # separate aggregate gate, not an execution performed by this check.
        tree = ast.parse((ROOT / 'tools/package_skill.py').read_text(encoding='utf-8'))
        assignments = [node for node in ast.walk(tree) if isinstance(node, ast.Assign)
                       and any(isinstance(t, ast.Name) and t.id == 'release_paths' for t in node.targets)]
        self.assertEqual(len(assignments), 1)
        inventory = ast.literal_eval(assignments[0].value)
        source_manifest = read_json(ROOT / 'skills/claude-guardian/sources/manifest.json')
        for source in source_manifest['sources']:
            inventory.append(source['path'])
            inventory.extend(c['path'] for c in source.get('companions', []))
        inventory.append('LICENSE')
        self.assertEqual(len(inventory), 64)
        self.assertEqual(len(set(inventory)), 64)
        # The new read-only observer is the sole release addition since this
        # case packet was captured; historical 63-member records stay intact.
        self.assertEqual(inventory.count('scripts/macos_metadata_observer.py'), 1)
        self.assertEqual(len([p for p in inventory if p != 'scripts/macos_metadata_observer.py']), 63)
        self.assertFalse(any('asset-route' in path or 'asset_route' in path for path in inventory))
        skill = ROOT / 'skills/claude-guardian'
        for path in [*PACKET.iterdir(), PAGE, ROOT / 'tests/test_acceptance_asset_route_evidence.py',
                     ROOT / 'tests/test_acceptance_asset_route_cases.py',
                     ROOT / 'tests/fixtures/acceptance-asset-route-cases.json']:
            self.assertFalse(path.resolve().is_relative_to(skill.resolve()))

    def test_changed_response_is_rejected_without_embedded_hash_trust(self):
        value = read_json(PACKET / 'dialogues-projection-public.json')
        value['conversations'][0]['turns'][0]['response'] += '\nSynthetic altered response'
        with self.assertRaisesRegex(ValueError, 'Captured response changed'):
            validate_projection(value)

    def test_changed_inputs_order_sources_and_provenance_are_rejected(self):
        original = read_json(PACKET / 'dialogues-projection-public.json')
        mutations = [
            lambda v: v['conversations'][0]['turns'][0].update(user='Synthetic altered input'),
            lambda v: v['conversations'].reverse(),
            lambda v: v['conversations'][0]['turns'].reverse(),
            lambda v: v['conversations'][1]['turns'].pop(),
            lambda v: v['sources'][0].update(sha256='0' * 64),
            lambda v: v['provenance_limits'].pop(),
            lambda v: v['provenance_limits'].append('All nine turns were frozen together up front.'),
        ]
        for i, mutate in enumerate(mutations):
            with self.subTest(mutation=i):
                value = deepcopy(original)
                mutate(value)
                with self.assertRaises(ValueError):
                    validate_projection(value)

    def test_extra_metadata_is_rejected_at_every_projection_level(self):
        original = read_json(PACKET / 'dialogues-projection-public.json')
        for level in ('root', 'source', 'conversation', 'turn'):
            with self.subTest(level=level):
                value = deepcopy(original)
                target = {'root': value, 'source': value['sources'][0],
                          'conversation': value['conversations'][0],
                          'turn': value['conversations'][0]['turns'][0]}[level]
                target['extra_metadata'] = 'synthetic-injection'
                with self.assertRaises(ValueError):
                    validate_projection(value)

    def test_review_cannot_erase_partial_history_or_skip_a_response(self):
        original = read_json(PACKET / 'final-semantic-review.json')
        value = deepcopy(original)
        value['retained_coverage_history']['original_six'] = 'Full route-question coverage'
        with self.assertRaisesRegex(ValueError, 'Earlier partial coverage'):
            validate_review(value)
        value = deepcopy(original)
        value['individual_response_review'].pop()
        with self.assertRaisesRegex(ValueError, 'Whole-response review coverage'):
            validate_review(value)
        value = deepcopy(original)
        value['original_cases']['T26']['requirement'] = 'Only record assets'
        with self.assertRaisesRegex(ValueError, 'Original requirement'):
            validate_review(value)

    def test_privacy_detector_rejects_injected_private_material(self):
        for value in ('/workspace/private/source', '/home/example/private', '/tmp/private',
                      '/Users/example/private', 'C:\\Users\\example', 'codex://threads/private',
                      'library://private', 'sediment://private', 'cloud_browser_handoff',
                      '"thread_id": "synthetic"', '"executor_id": "synthetic"',
                      '"library_file_id": "synthetic"', 'Bearer synthetic-token',
                      '-----BEGIN PRIVATE KEY-----',
                      '00000000-0000-0000-0000-000000000000'):
            with self.subTest(injection=value):
                with self.assertRaises(ValueError):
                    check_public_text(value)


if __name__ == '__main__':
    unittest.main()
