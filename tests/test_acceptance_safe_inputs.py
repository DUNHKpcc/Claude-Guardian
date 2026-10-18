"""Supporting runtime/source integrity checks, not generated-response replay."""
import ast
import hashlib
import json
import os
import shutil
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest
from test_acceptance_skill_registry_wording import (
    SKILL_PATH, SUPPLEMENT_RELATIVE, SUPPLEMENT_SHA256, checked_registry_wording_sha256)

ROOT = Path(__file__).resolve().parents[1]
HERE = ROOT / 'docs/evidence/t11-t12-safe-inputs-v1'
PINS = json.loads((HERE / 'source-pins.json').read_text(encoding='utf-8'))
SOURCE = Path(os.environ.get('GUARDIAN_REPOSITORY_ROOT', str(ROOT)))


class SafeInputsCandidateTests(unittest.TestCase):
    def test_exact_reviewed_source_bytes_and_original_conditions(self):
        for relative, expected in PINS['source_sha256'].items():
            with self.subTest(source=relative):
                path = SOURCE / relative
                if relative == SKILL_PATH:
                    self.assertFalse(path.is_symlink())
                    checked_registry_wording_sha256(path.read_bytes(), expected)
                else:
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), expected)
        design = (SOURCE / 'skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md').read_text(encoding='utf-8')
        for case_id, row in PINS['original_conditions'].items():
            self.assertEqual(next(line for line in design.splitlines() if line.startswith('| ' + case_id + ' |')), row)
        self.assertEqual(PINS['verification_layer'], 'L+C')

    def test_replay_reexecutes_bounded_supporting_paths(self):
        with tempfile.TemporaryDirectory(prefix='guardian-safe-input-replay-') as temporary:
            output = Path(temporary) / 'traces'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/acceptance_safe_inputs_replay.py'),
                '--source', str(SOURCE), '--output', str(output)], capture_output=True,
                text=True, encoding='utf-8', errors='strict', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            summary = json.loads(result.stdout)
            self.assertEqual(summary['cli_cases_passed'], 9)
            self.assertTrue(summary['pure_source_helper_checked'])
            self.assertEqual(summary['full_T11_T12_acceptance'], 'pending')
            record = json.loads((output / 'execution-record.json').read_text(encoding='utf-8'))
            actual_sources = {relative: hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
                              for relative in PINS['source_sha256']}
            self.assertEqual(record['source_sha256'], actual_sources)
            self.assertEqual(record['historical_source_pin_file'], {
                'path': 'docs/evidence/t11-t12-safe-inputs-v1/source-pins.json',
                'sha256': hashlib.sha256((HERE / 'source-pins.json').read_bytes()).hexdigest()})
            if actual_sources[SKILL_PATH] != PINS['source_sha256'][SKILL_PATH]:
                self.assertEqual(record['documentation_compatibility'], {
                    'path': SUPPLEMENT_RELATIVE, 'sha256': SUPPLEMENT_SHA256})
            else:
                self.assertNotIn('documentation_compatibility', record)
            self.assertEqual(len(record['cases']), 9)
            self.assertTrue(all(all(case['checks'].values()) for case in record['cases']))

    def test_replay_non_ascii_output_path_with_cp1252_stdio(self):
        with tempfile.TemporaryDirectory(prefix='guardian-safe-input-encoding-') as temporary:
            # Preserve the same non-ASCII pathname bytes even when this test
            # itself runs with ASCII filesystem decoding on POSIX.
            output_name_bytes = '路径-é-traces'.encode('utf-8')
            output = Path(temporary) / os.fsdecode(output_name_bytes)
            self.assertEqual(os.fsencode(output.name), output_name_bytes)
            environment = dict(os.environ, PYTHONIOENCODING='cp1252', PYTHONUTF8='0',
                               PYTHONCOERCECLOCALE='0', LC_ALL='C',
                               PYTHONDONTWRITEBYTECODE='1')
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/acceptance_safe_inputs_replay.py'),
                '--source', str(SOURCE), '--output', str(output)], env=environment,
                capture_output=True, text=True, encoding='utf-8', errors='strict', timeout=30)
            self.assertEqual(result.returncode, 0, result.stderr)
            self.assertTrue(result.stdout.isascii())
            summary = json.loads(result.stdout)
            self.assertEqual(summary['cli_cases_passed'], 9)
            self.assertTrue(summary['pure_source_helper_checked'])
            # With ASCII filesystem decoding, a POSIX child can retain argv
            # bytes as surrogates. Compare path bytes without hiding that fact.
            self.assertEqual(os.fsencode(summary['output']), os.fsencode(str(output.resolve())))
            record = json.loads((output / 'execution-record.json').read_text(encoding='utf-8'))
            actual_sources = {relative: hashlib.sha256((SOURCE / relative).read_bytes()).hexdigest()
                              for relative in PINS['source_sha256']}
            self.assertEqual(record['source_sha256'], actual_sources)
            self.assertEqual(record['historical_source_pin_file'], {
                'path': 'docs/evidence/t11-t12-safe-inputs-v1/source-pins.json',
                'sha256': hashlib.sha256((HERE / 'source-pins.json').read_bytes()).hexdigest()})
            if actual_sources[SKILL_PATH] != PINS['source_sha256'][SKILL_PATH]:
                self.assertEqual(record['documentation_compatibility'], {
                    'path': SUPPLEMENT_RELATIVE, 'sha256': SUPPLEMENT_SHA256})
            else:
                self.assertNotIn('documentation_compatibility', record)
            self.assertEqual(len(record['cases']), 9)
            self.assertTrue(all(all(case['checks'].values()) for case in record['cases']))
            helper = json.loads((output / 'opaque-source-trace.json').read_text(encoding='utf-8'))
            self.assertTrue(all(count == 0 for count in helper['observed_calls_to_instrumented_functions'].values()))

    def test_replay_rejects_other_source_drift_before_running(self):
        with tempfile.TemporaryDirectory(prefix='guardian-safe-input-source-drift-') as temporary:
            source = Path(temporary) / 'source'
            for relative in PINS['source_sha256']:
                target = source / relative
                target.parent.mkdir(parents=True, exist_ok=True)
                shutil.copyfile(SOURCE / relative, target)
            runtime = source / 'skills/claude-guardian/scripts/guardian.py'
            runtime.write_bytes(runtime.read_bytes() + b'\n')
            output = Path(temporary) / 'must-not-be-created'
            result = subprocess.run([sys.executable, '-B', str(ROOT / 'tests/acceptance_safe_inputs_replay.py'),
                '--source', str(source), '--output', str(output)], capture_output=True,
                text=True, encoding='utf-8', errors='strict', timeout=30)
            self.assertNotEqual(result.returncode, 0)
            self.assertIn('Pinned source changed: skills/claude-guardian/scripts/guardian.py', result.stderr)
            self.assertFalse(output.exists())

    def test_candidate_uses_python_310_grammar(self):
        for name in ('acceptance_safe_inputs_replay.py', 'test_acceptance_safe_inputs.py'):
            ast.parse((ROOT / 'tests' / name).read_text(encoding='utf-8'), feature_version=(3, 10))



MANIFEST_SHA256 = 'd7e30fb50c564b129d1cfe14e5f0337ed0b531a65d26b214dec9f179f3c3c991'


def read_json(name):
    return json.loads((HERE / name).read_text(encoding='utf-8'))


def digest(name):
    return hashlib.sha256((HERE / name).read_bytes()).hexdigest()


class GuidedResponseEvidenceTests(unittest.TestCase):
    def test_retained_artifacts_are_exact_reviewed_bytes(self):
        self.assertEqual(digest('evidence-manifest.json'), MANIFEST_SHA256)
        manifest = read_json('evidence-manifest.json')
        for relative, expected in manifest['artifact_sha256'].items():
            with self.subTest(artifact=relative):
                self.assertFalse((HERE / relative).is_symlink())
                self.assertEqual(digest(relative), expected)
        self.assertEqual(manifest['verification_layer'], 'L+C')
        self.assertEqual(manifest['original_conditions'], read_json('source-pins.json')['original_conditions'])

    def test_generator_provenance_and_independent_review_correspond(self):
        provenance = read_json('generated/provenance.json')
        self.assertEqual(provenance['source_pin_file']['sha256'], digest('source-pins.json'))
        self.assertEqual(provenance['exercise_input']['sha256'], digest('exercise-inputs.json'))
        self.assertEqual([(item['case'], item['turn']) for item in provenance['outputs']],
                         [('T11', 1), ('T11', 2), ('T12', 1), ('T12', 2)])
        for item in provenance['outputs']:
            self.assertEqual(digest('generated/' + Path(item['path']).name), item['sha256'])
        review = read_json('independent-review.json')
        self.assertEqual(review['conclusion']['blocking_semantic_findings'], [])
        self.assertTrue(review['conclusion']['full_original_clauses_covered_in_recorded_exercises'])
        self.assertEqual([item['clause'] for item in review['clause_coverage']],
            ['输出脱敏', '不把秘密带入报告', '不把秘密带入模板', '不把秘密带入公共仓库',
             '当作不可信文本', '不执行或改变权限'])
        for item in review['integrity_checks']:
            self.assertTrue(item['match'])
            self.assertEqual(digest(item['path']), item['actual_sha256'])
            self.assertEqual(item['recorded_sha256'], item['actual_sha256'])

    def test_exact_sentinels_absent_and_all_response_lines_reviewed(self):
        review = read_json('independent-review.json')
        for item in review['sentinel_checks']:
            content = (HERE / 'generated' / item['response']).read_text(encoding='utf-8')
            self.assertEqual(len(item['each_exact_sentinel_absent']), 8)
            for sentinel, absent in item['each_exact_sentinel_absent'].items():
                self.assertTrue(absent)
                self.assertNotIn(sentinel, content)
        for name, rows in review['content_review'].items():
            lines = (HERE / 'generated' / name).read_text(encoding='utf-8').splitlines()
            covered = {number for row in rows for number in range(row['lines'][0], row['lines'][1] + 1)}
            self.assertTrue({number for number, line in enumerate(lines, 1) if line.strip()} <= covered)
        for key in ('universal_redaction_claim', 'native_acceptance_claim',
                    'publication_enforcement_claim', 'independent_host_execution_telemetry_claim'):
            self.assertFalse(review['conclusion'][key])


if __name__ == '__main__':
    unittest.main()
