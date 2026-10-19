"""T22/T25 retained-record integrity and privacy, not response generation.

The seven responses were observed and independently reviewed before integration.
These regressions pin that public evidence and sources; the separate logic suite
consumes normalized facts and did not generate or participate in those dialogues.
"""
from copy import deepcopy
import hashlib
import json
from pathlib import Path
import re
import unittest

from acceptance_runtime_compat import EXPECTED_MANIFEST as COPY_MANIFEST, load as load_copy_compatibility

ROOT = Path(__file__).resolve().parents[1]
COPY = load_copy_compatibility(ROOT)
PACKET = ROOT / 'docs/evidence/local-incident-v1'
PAGE = ROOT / 'docs/evidence/rebuild-local-incident-cases.md'
MANIFEST_SHA256 = 'e49098e2442f95905084d563269d34be4ef99178e10078a9879a6ad276975afa'
PAGE_SHA256 = '57c0be1d6fd953f01ad0de69f08bfc92527c1939ea3fa1341bec0d662d170561'
ORIGINAL_ROWS_SHA256 = '84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9'
ARTIFACT_SHA256 = {'dialogues-projection-public.json': 'be04d06826c162ecb7e2fc68c71342bb849374bc20eb8555f60685a206f2157e', 'independent-review.md': 'b104c249aaa56b6c9d5ff7a3931b77701aef968c59cb4a3c367ed878e6e6e90b'}
SOURCE_SHA256 = {'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md': '6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562', 'skills/claude-guardian/sources/design/D-ENV-v0.3.md': 'ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4', 'docs/implementation-tracker.md': '8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50', 'skills/claude-guardian/SKILL.md': 'f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3', 'skills/claude-guardian/references/contact-and-safety.md': '095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c', 'skills/claude-guardian/references/intake.md': '3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742', 'skills/claude-guardian/references/routes-and-platforms.md': 'dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984', 'skills/claude-guardian/references/incidents-and-integrations.md': '37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2', 'skills/claude-guardian/references/network-and-remedies.md': 'a13f51b7b996bd2a2c3f920b3a944d8b3f8a059e6a28cb921be5cd84b3f6d48b', 'skills/claude-guardian/scripts/interview_flow.py': '691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9', 'AGENTS.md': '32612bdd03fa4c7c7337935b8add82793ca5faa2e1d7f57a1021b1844ae971b6'}
LOGIC_SHA256 = {'tests/test_acceptance_local_incident_cases.py': '22c13c0a917bcf9c9aadae3e3aee4e8a66509bf3837f0e44a5d0d0c2bc82b2e1', 'tests/fixtures/acceptance-local-incident-cases.json': 'f021362b207a6ec29eea7e62a8cf6a7ebbc70eb1797fc2eef5dceeb6d2aed4bc'}
ORIGINAL_CASES = {'T22': {'scenario': 'L4 只处理本机 Code', 'requirement': '留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移', 'verification_layer': 'L+C', 'literal_design_row': '| T22 | L4 只处理本机 Code | 留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移 |', 'literal_tracker_row': '| T22 | L4 只处理本机 Code | 留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移 | L+C | 待建立 |', 'review_result': 'accepted_revalidated'}, 'T25': {'scenario': '本机出现错误或账号受限', 'requirement': '先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号', 'verification_layer': 'L+C', 'literal_design_row': '| T25 | 本机出现错误或账号受限 | 先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号 |', 'literal_tracker_row': '| T25 | 本机出现错误或账号受限 | 先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号 | L+C | 待建立 |', 'review_result': 'accepted_revalidated'}}
SOURCE_MAPPING = {'shipped_skill': 'skills/claude-guardian/SKILL.md', 'contact_and_safety': 'skills/claude-guardian/references/contact-and-safety.md', 'routes_and_platforms': 'skills/claude-guardian/references/routes-and-platforms.md', 'incidents_and_integrations': 'skills/claude-guardian/references/incidents-and-integrations.md', 'network_and_remedies': 'skills/claude-guardian/references/network-and-remedies.md'}
OBSERVED_CONVERSATIONS = [{'scenario': 'expert-local-code', 'case_id': 'T22', 'turns': [{'turn': 1, 'user_sha256': '76f6984db71e5649e783d157ac4d8fce5c1e29b1cd4d64c9ebb7153efcffceb2', 'response_sha256': '4d4be99f4f69dfb45224fbe7840c1a312007ebeeb6fb65ee709d1316dab0b302'}, {'turn': 2, 'user_sha256': '0b77294251d8a5630e65e9adc79e0171b807234842fefdcfa4168ff4eae3d762', 'response_sha256': '5d76604a56e0d980b3fa9470692284fc2c25556d96a610e0ceb4563fb75f8469'}]}, {'scenario': 'local-proxy-error', 'case_id': 'T25', 'turns': [{'turn': 1, 'user_sha256': '3aef27ea8c94b30de2ad19189fbe752ad56827f9671ce9f6db74005b3a3ca268', 'response_sha256': 'aabb641a21c7442258a829db2d0768216436804ee372c1f7610effb67f4eaa03'}, {'turn': 2, 'user_sha256': '6dc619107a44f5692eb9ab5fa86df29fffa1504201d8128064cd8498083e87b4', 'response_sha256': '8ebb68cb2e142b45101c8b4dd1dbda4672800a7f22c182564a7c24e7002b073a'}, {'turn': 3, 'user_sha256': 'c757a78729f46956a797591451aa2cf9b0f9d95521ba9460bc70713b86883447', 'response_sha256': '3831f56b0755ce2268c3f0f9ec919a3554e8b880a482bee6c4db15d25e5b9959'}]}, {'scenario': 'current-restriction', 'case_id': 'T25', 'turns': [{'turn': 1, 'user_sha256': 'c615794fdda3bfd6b40ef04ffc2fe773049de8977ce59936adb331103fed3e8a', 'response_sha256': '66c4424310b9672e358f68aabc60a896162d9ba7589980ce895475cd633fff7d'}, {'turn': 2, 'user_sha256': 'ea7c0efbe41c595afaefe2a09cbfe88babef78ab830922b22296ed903b8c0398', 'response_sha256': 'aac06e8767886a3b4c1fe445b12af85579982d2783d2615bce3030daed06081b'}]}]
PROVENANCE_LIMITS = ['All account, device, operating-system, proxy, project, and incident facts are fictional synthetic user reports, not verified facts about a real person or device.', 'Seven actual responses from three separate synthetic conversations are retained without editing. All user turns were frozen before generation; each follow-up was supplied only when its turn arrived.', 'The supplied source scope was the pinned shipped Skill and ordinary references. The source boundary was instruction-enforced, not physical isolation; this does not prove inaccessible files or an isolated process.', 'No interview helper was invoked in these conversations. Separate normalized runtime evidence must not be attributed to these responders.', 'Source-reading provenance is responder-reported from retained call records, not an independently exported complete tool transcript. One source-read result omitted 329 tokens of cleanup material; that omitted text was not reread or claimed as read. Pinned full files do not imply every section was read.', 'This is offline synthetic dialogue evidence only. No real device, UI, native behavior, target client, network path, current official service/account state, repair, or recovery was verified. No acceptance verdict is supplied.']
SOURCE_PROVENANCE = {'source_reads': 'responder_reported_not_independent_complete_tool_transcript', 'source_boundary': 'instruction_enforced_not_physical_isolation', 'omitted_cleanup_tokens': 329, 'omitted_material_reread': False, 'full_file_hash_proves_full_read': False, 'helper_invoked_in_observed_dialogues': False}
CLAIM_LIMITS = ['All account, device, operating-system, proxy, project, and incident facts are fictional synthetic user reports, not verified facts about a real person or device.', 'Seven actual responses from three separate synthetic conversations are retained without editing. All user turns were frozen before generation; each follow-up was supplied only when its turn arrived.', 'The supplied source scope was the pinned shipped Skill and ordinary references. The source boundary was instruction-enforced, not physical isolation; this does not prove inaccessible files or an isolated process.', 'No interview helper was invoked in these conversations. Separate normalized runtime evidence must not be attributed to these responders.', 'Source-reading provenance is responder-reported from retained call records, not an independently exported complete tool transcript. One source-read result omitted 329 tokens of cleanup material; that omitted text was not reread or claimed as read. Pinned full files do not imply every section was read.', 'Acceptance is limited to original T22/T25 in these frozen L+C scenarios. Seven observed outputs are not a guarantee for unseen prompts or future stochastic responses.', 'Normalized helper input/state/question assertions do not parse user prose or generate the seven retained replies. I/O sentinels are not an operating-system sandbox; module and fixture loading occur outside their boundary.', 'No native, current external service/account, actual client/network, official procedure, repair, recovery or cleanup-operation acceptance. Mac/Windows fixture labels establish normalized logic only; T04 and adjacent cases remain outside this decision.', 'Integrity regression checks retained evidence and current source identity; it does not rerun or generate model responses. Relevant source drift requires renewed semantic review, not automatic hash refresh.']


def digest(path):
    return hashlib.sha256(path.read_bytes()).hexdigest()


def read_json(path):
    return json.loads(path.read_text(encoding='utf-8'))


def text_digest(text):
    return hashlib.sha256(text.encode('utf-8')).hexdigest()


def require(condition, message):
    if not condition:
        raise ValueError(message)


def check_public_text(text):
    for marker in ('/workspace/', '/home/agent/', '/tmp/', 'codex://', 'library://',
                   'sediment://', 'cloud_browser_handoff'):
        require(marker not in text, 'Private location or handoff metadata')
    require(re.search(r'\b[0-9a-fA-F]{8}-(?:[0-9a-fA-F]{4}-){3}[0-9a-fA-F]{12}\b', text) is None,
            'Private identifier-shaped value')
    require(re.search(r'(?:executor|thread|library_file|session)[_-]id["\x27]?\s*[:=]',
                      text, re.IGNORECASE) is None, 'Private coordination metadata')


def validate_projection(value):
    require(set(value) == {'synthetic', 'source_sha256', 'conversations', 'provenance_limits'},
            'Projection root fields changed')
    require(value['synthetic'] is True, 'Synthetic boundary missing')
    expected_sources = {key: SOURCE_SHA256[path] for key, path in SOURCE_MAPPING.items()}
    require(value['source_sha256'] == expected_sources, 'Dialogue source identity changed')
    require(value['provenance_limits'] == PROVENANCE_LIMITS, 'Provenance limits changed')
    require(isinstance(value['conversations'], list) and len(value['conversations']) == 3,
            'Conversation count changed')
    for conversation, expected in zip(value['conversations'], OBSERVED_CONVERSATIONS):
        require(set(conversation) == {'scenario', 'turns'}, 'Conversation fields changed')
        require(conversation['scenario'] == expected['scenario'], 'Conversation order changed')
        require(isinstance(conversation['turns'], list) and
                len(conversation['turns']) == len(expected['turns']), 'Turn count changed')
        for turn, original in zip(conversation['turns'], expected['turns']):
            require(set(turn) == {'user', 'response', 'response_sha256'}, 'Turn fields changed')
            require(isinstance(turn['user'], str) and isinstance(turn['response'], str),
                    'Turn payload type changed')
            require(text_digest(turn['user']) == original['user_sha256'], 'Frozen user input changed')
            require(text_digest(turn['response']) == original['response_sha256'],
                    'Captured response changed')
            require(turn['response_sha256'] == original['response_sha256'],
                    'Captured response identity changed')
    check_public_text(json.dumps(value, ensure_ascii=False))


class LocalIncidentEvidenceTests(unittest.TestCase):
    def test_current_fact_copy_runtime_replays_complete_normalized_evidence(self):
        # A new API execution, explicitly separate from the seven old dialogues.
        suite = 'tests/test_acceptance_local_incident_cases.py'
        receipt = COPY.read_json(ROOT / COPY.REL / 'replay-receipt.json')
        COPY.verify_replay_value(COPY.replay_output(ROOT, suite), receipt['semantic_suites'][suite])

    def test_manifest_and_casepage_bytes_are_pinned(self):
        self.assertFalse((PACKET / 'evidence-manifest.json').is_symlink())
        self.assertFalse(PAGE.is_symlink())
        self.assertEqual(digest(PACKET / 'evidence-manifest.json'), MANIFEST_SHA256)
        self.assertEqual(digest(PAGE), PAGE_SHA256)
        manifest = read_json(PACKET / 'evidence-manifest.json')
        self.assertEqual(manifest['schema_version'], 'guardian-local-incident-evidence/1')
        self.assertEqual(manifest['manifest_role'],
                         'Integration inventory of reviewed public evidence, not a new execution record or independent execution telemetry.')

    def test_exact_public_artifact_inventory_and_bytes(self):
        self.assertEqual({path.name for path in PACKET.iterdir()},
                         set(ARTIFACT_SHA256) | {'evidence-manifest.json'})
        for name, expected in ARTIFACT_SHA256.items():
            with self.subTest(artifact=name):
                path = PACKET / name
                self.assertFalse(path.is_symlink())
                self.assertTrue(path.is_file())
                self.assertEqual(digest(path), expected)
        self.assertEqual(read_json(PACKET / 'evidence-manifest.json')['artifact_sha256'], ARTIFACT_SHA256)

    def test_full_original_conditions_layers_and_218_identity_are_unchanged(self):
        manifest = read_json(PACKET / 'evidence-manifest.json')
        self.assertEqual(manifest['cases'], ORIGINAL_CASES)
        self.assertEqual(manifest['original_rows_sha256'], ORIGINAL_ROWS_SHA256)
        spec = (ROOT / 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8').splitlines()
        tracker = (ROOT / 'docs/implementation-tracker.md').read_text(encoding='utf-8').splitlines()
        original = [line for line in tracker if re.match(r'^\| (?:T\d+|ENV-T\d+) \|', line)]
        self.assertEqual(len(original), 218)
        self.assertEqual(text_digest('\n'.join(original) + '\n'), ORIGINAL_ROWS_SHA256)
        for case_id, case in ORIGINAL_CASES.items():
            self.assertEqual(case['verification_layer'], 'L+C')
            self.assertEqual(next(line for line in spec if line.startswith('| ' + case_id + ' |')),
                             case['literal_design_row'])
            self.assertEqual(next(line for line in tracker if line.startswith('| ' + case_id + ' |')),
                             case['literal_tracker_row'])
            self.assertEqual([part.strip() for part in case['literal_tracker_row'].split('|')[1:5]],
                             [case_id, case['scenario'], case['requirement'], 'L+C'])

    def test_reviewed_current_sources_and_response_source_mapping(self):
        manifest = read_json(PACKET / 'evidence-manifest.json')
        self.assertEqual(manifest['source_sha256'], SOURCE_SHA256)
        self.assertEqual(manifest['dialogue_source_mapping'], SOURCE_MAPPING)
        for relative, expected in SOURCE_SHA256.items():
            with self.subTest(source=relative):
                path = ROOT / relative
                self.assertFalse(path.is_symlink())
                # Old source pins retain their historical meaning. The supplement
                # proves the exact runtime transition and separately replays it.
                COPY.verify_historical_pin_on_current(ROOT, relative, expected, COPY_MANIFEST)
        review = (PACKET / 'independent-review.md').read_text(encoding='utf-8')
        review_pins = dict(re.findall(r'^- `([^`]+)`: `([a-f0-9]{64})`$', review, re.MULTILINE))
        self.assertEqual(review_pins,
                         {**{path: value for path, value in SOURCE_SHA256.items() if path != 'AGENTS.md'},
                          **LOGIC_SHA256})

    def test_normalized_logic_evidence_is_pinned_and_separate(self):
        manifest = read_json(PACKET / 'evidence-manifest.json')
        self.assertEqual(manifest['logic_evidence_sha256'], LOGIC_SHA256)
        for relative, expected in LOGIC_SHA256.items():
            self.assertFalse((ROOT / relative).is_symlink())
            self.assertEqual(digest(ROOT / relative), expected)
        fixture = read_json(ROOT / 'tests/fixtures/acceptance-local-incident-cases.json')
        self.assertEqual(fixture['evidence_kind'],
                         'synthetic_normalized_host_inputs_not_executed_model_dialogue')
        for relative, expected in fixture['source_pins'].items():
            self.assertEqual(SOURCE_SHA256[relative], expected)
        for case_id, case in ORIGINAL_CASES.items():
            self.assertEqual(fixture['original_requirements'][case_id],
                             {'scenario': case['scenario'], 'requirement': case['requirement'], 'layers': 'L+C'})
        self.assertFalse(manifest['source_provenance']['helper_invoked_in_observed_dialogues'])

    def test_seven_actual_turns_preserve_exact_inputs_and_responses(self):
        projection = read_json(PACKET / 'dialogues-projection-public.json')
        validate_projection(projection)
        self.assertEqual([len(c['turns']) for c in projection['conversations']], [2, 3, 2])
        self.assertEqual(read_json(PACKET / 'evidence-manifest.json')['observed_conversations'],
                         OBSERVED_CONVERSATIONS)

    def test_review_preserves_whole_response_verdict_and_limits(self):
        # This asserts retained review identity/coverage labels, not semantic correctness by keywords.
        review = (PACKET / 'independent-review.md').read_text(encoding='utf-8')
        self.assertIn('PASS for original T22 and T25 at their unchanged L+C evidence scope', review)
        self.assertEqual(len(re.findall(r'\*\*Turn [123]: PASS\.\*\*', review)), 7)
        for case in ORIGINAL_CASES.values():
            self.assertIn(case['scenario'], review)
            self.assertIn(case['requirement'], review)
        self.assertIn('9 passed, 0 skipped', review)
        self.assertIn('329-token omission', review)
        self.assertIn('No N/X/R evidence has been added', review)

    def test_provenance_limits_are_explicit_and_no_generation_or_native_claim(self):
        manifest = read_json(PACKET / 'evidence-manifest.json')
        self.assertEqual(manifest['source_provenance'], SOURCE_PROVENANCE)
        self.assertEqual(manifest['claim_limits'], CLAIM_LIMITS)
        self.assertEqual(manifest['evidence_type'],
                         'retained_actual_synthetic_dialogues_plus_independent_semantic_review_and_separate_normalized_logic')
        self.assertEqual(SOURCE_PROVENANCE['omitted_cleanup_tokens'], 329)
        self.assertFalse(SOURCE_PROVENANCE['omitted_material_reread'])
        self.assertFalse(SOURCE_PROVENANCE['full_file_hash_proves_full_read'])
        page = PAGE.read_text(encoding='utf-8')
        self.assertIn('they do not rerun or generate model output', page)
        self.assertIn('No runtime change was necessary', page)
        self.assertIn('Evidence and tests are outside the unchanged installed Skill package', page)

    def test_public_packet_casepage_and_fixture_exclude_private_metadata(self):
        for path in [*PACKET.iterdir(), PAGE,
                     ROOT / 'tests/fixtures/acceptance-local-incident-cases.json']:
            with self.subTest(artifact=path.name):
                check_public_text(path.read_text(encoding='utf-8'))

    def test_changed_response_is_rejected_even_if_embedded_hash_is_updated(self):
        value = read_json(PACKET / 'dialogues-projection-public.json')
        turn = value['conversations'][0]['turns'][0]
        turn['response'] += '\nSynthetic tampered response'
        turn['response_sha256'] = text_digest(turn['response'])
        with self.assertRaisesRegex(ValueError, 'Captured response changed'):
            validate_projection(value)

    def test_input_order_source_and_boundary_changes_are_rejected(self):
        original = read_json(PACKET / 'dialogues-projection-public.json')
        variants = []
        value = deepcopy(original)
        value['conversations'][0]['turns'][0]['user'] += ' changed'
        variants.append(value)
        value = deepcopy(original)
        value['conversations'].reverse()
        variants.append(value)
        value = deepcopy(original)
        value['conversations'][1]['turns'].reverse()
        variants.append(value)
        value = deepcopy(original)
        value['source_sha256']['shipped_skill'] = '0' * 64
        variants.append(value)
        value = deepcopy(original)
        value['provenance_limits'].pop()
        variants.append(value)
        value = deepcopy(original)
        value['synthetic'] = False
        variants.append(value)
        value = deepcopy(original)
        value['conversations'][1]['turns'].pop()
        variants.append(value)
        for value in variants:
            with self.subTest(mutation=variants.index(value)):
                with self.assertRaises(ValueError):
                    validate_projection(value)

    def test_extra_projection_metadata_is_rejected_at_every_level(self):
        original = read_json(PACKET / 'dialogues-projection-public.json')
        for level in ('root', 'conversation', 'turn'):
            with self.subTest(level=level):
                value = deepcopy(original)
                target = value if level == 'root' else value['conversations'][0]
                if level == 'turn':
                    target = target['turns'][0]
                target['extra_metadata'] = 'synthetic-injection'
                with self.assertRaisesRegex(ValueError, 'fields changed'):
                    validate_projection(value)

    def test_privacy_detector_rejects_injected_private_material(self):
        for text in ('/workspace/private/source', '/home/agent/private', '/tmp/private',
                     'codex://threads/private', 'library://private', 'sediment://private',
                     'cloud_browser_handoff', '"thread_id": "synthetic"',
                     '"executor_id": "synthetic"', '"library_file_id": "synthetic"',
                     '00000000-0000-0000-0000-000000000000'):
            with self.subTest(injection=text):
                with self.assertRaises(ValueError):
                    check_public_text(text)


if __name__ == '__main__':
    unittest.main()
