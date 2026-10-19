"""Fresh live verification plus explicit, byte-real historical source preservation."""
from contextlib import contextmanager
from copy import deepcopy
import json
import os
import subprocess
import sys
from pathlib import Path
import shutil
import unittest
from unittest.mock import patch

from acceptance_runtime_compat import EXPECTED_MANIFEST, load

ROOT = Path(__file__).resolve().parents[1]
C = load(ROOT)
RECEIPT = C.read_json(ROOT / C.REL / 'replay-receipt.json')


class FactCopyCompatibilityTests(unittest.TestCase):
    @contextmanager
    def current_copy(self):
        with C.historical_source_view(ROOT, EXPECTED_MANIFEST) as copied:
            (copied / C.RUNTIME).write_bytes((ROOT / C.RUNTIME).read_bytes())
            shutil.copytree(ROOT / C.REL, copied / C.REL, copy_function=shutil.copyfile,
                            ignore=shutil.ignore_patterns('__pycache__'))
            yield copied

    def test_exact_transition_preserves_real_historical_bytes(self):
        C.verify_current(ROOT, EXPECTED_MANIFEST)
        with C.historical_source_view(ROOT, EXPECTED_MANIFEST) as historical:
            self.assertEqual(C.digest(historical / C.RUNTIME), C.BEFORE)
            self.assertEqual(C.digest(ROOT / C.RUNTIME), C.AFTER)
            old, new = (historical / C.RUNTIME).read_bytes(), (ROOT / C.RUNTIME).read_bytes()
            self.assertEqual(old.replace(C.OLD_LINE.encode(), C.NEW_LINE.encode(), 1), new)

    def test_thirteen_complete_historical_and_current_semantic_replays(self):
        self.assertEqual(len(RECEIPT['semantic_suites']), 13)
        with C.historical_source_view(ROOT, EXPECTED_MANIFEST) as historical:
            for suite, expected in RECEIPT['semantic_suites'].items():
                with self.subTest(suite=suite):
                    old = C.replay_output(historical, suite, expected=expected)
                    current = C.replay_output(ROOT, suite, expected=expected)
                    self.assertEqual(old, current, 'Complete current state/question/assessment replay changed')
                    C.verify_replay_value(old, expected)
                    C.verify_replay_value(current, expected)
        C.verify_current(ROOT, EXPECTED_MANIFEST)

    @staticmethod
    def resume_non_posix_branch(root):
        # Simulate only the existing decorator outcome. No fake os.name, altered
        # original source, changed state, or substitute cleanup implementation.
        code = """import importlib.util,sys,unittest,json
from pathlib import Path
path=Path(sys.argv[1])/'tests/test_acceptance_resume_completion.py'
spec=importlib.util.spec_from_file_location('resume_skip_control',path)
m=importlib.util.module_from_spec(spec);spec.loader.exec_module(m)
method=m.ResumeCompletionTests.test_partial_cleanup_resume_observes_then_restores_without_redeletion
method.__unittest_skip__=True
method.__unittest_skip_why__='POSIX temporary fixture only'
result=unittest.TestResult()
unittest.defaultTestLoader.loadTestsFromTestCase(m.ResumeCompletionTests).run(result)
print(json.dumps({'trace':m.TRACE,'tests':result.testsRun,'failures':len(result.failures),'errors':len(result.errors),'skipped':[[test._testMethodName,reason] for test,reason in result.skipped]},ensure_ascii=True,sort_keys=True))
sys.exit(not result.wasSuccessful())
"""
        result = subprocess.run([sys.executable, '-B', '-c', code, str(root)],
            cwd=root, env=dict(os.environ, GUARDIAN_AUDIT_ROOT=str(root),
                              PYTHONDONTWRITEBYTECODE='1', PYTHONIOENCODING='utf-8'),
            capture_output=True, check=False)
        if result.returncode:
            raise AssertionError(result.stderr.decode('utf-8'))
        return json.loads(result.stdout.decode('utf-8'))

    def test_resume_non_posix_skip_keeps_complete_historical_and_current_trace(self):
        expected = RECEIPT['semantic_suites'][C.RESUME_SUITE]
        with C.historical_source_view(ROOT, EXPECTED_MANIFEST) as historical:
            old = self.resume_non_posix_branch(historical)
            current = self.resume_non_posix_branch(ROOT)
        self.assertEqual(old, current)
        self.assertEqual({k: v for k, v in current.items() if k != 'trace'},
            {'tests': 4, 'failures': 0, 'errors': 0,
             'skipped': expected['execution_profiles']['nt']['unittest']['skipped']})
        C.verify_replay_value(old['trace'], expected, execution_os_name='nt')
        C.verify_replay_value(current['trace'], expected, execution_os_name='nt')
        # Regression witness: the original POSIX-only verifier rejected this
        # valid complete non-POSIX output, even when old and current were equal.
        old_receipt = {k: v for k, v in expected.items() if k != 'execution_profiles'}
        with self.assertRaisesRegex(AssertionError, 'Semantic replay result mismatch'):
            C.verify_replay_value(current['trace'], old_receipt, execution_os_name='nt')
        if os.name == 'posix':
            full = C.replay_output(ROOT, C.RESUME_SUITE, expected=expected)
            C.verify_replay_value(full, expected)
            self.assertIn('cleanup_resume', full)
            # Comparison only: the verifier never normalizes away this trace.
            self.assertEqual({k: v for k, v in full.items() if k != 'cleanup_resume'}, current['trace'])

    def test_resume_platform_hashes_reject_missing_extra_and_changed_semantics(self):
        expected = RECEIPT['semantic_suites'][C.RESUME_SUITE]
        trace = self.resume_non_posix_branch(ROOT)['trace']
        for platform in ('posix', 'unknown'):
            with self.subTest(platform=platform), self.assertRaises(AssertionError):
                C.verify_replay_value(trace, expected, execution_os_name=platform)
        variants = [deepcopy(trace) for _ in range(3)]
        variants[0].pop('purchase_resume')
        variants[1]['cleanup_resume'] = {'fabricated': True}
        variants[2]['before_reported_completion']['state']['context']['route'] = 'vps'
        for changed in variants:
            with self.subTest(keys=sorted(changed)), self.assertRaises(AssertionError):
                C.verify_replay_value(changed, expected, execution_os_name='nt')

    def test_resume_platform_skip_inventory_is_exact_and_not_a_pass(self):
        expected = RECEIPT['semantic_suites'][C.RESUME_SUITE]
        name, reason = expected['execution_profiles']['nt']['unittest']['skipped'][0]
        no_skip = 'Ran 4 tests in 0.100s\n\nOK\n'
        skipped = name + " (resume.ResumeCompletionTests) ... skipped '" + reason + "'\n" + no_skip
        for newline in ('\n', '\r\n'):
            C.verify_replay_execution(no_skip.replace('\n', newline), expected, execution_os_name='posix')
            C.verify_replay_execution(skipped.replace('\n', newline), expected, execution_os_name='nt')
        for text, platform in [(skipped, 'posix'), (no_skip, 'nt'),
                (skipped.replace(reason, 'unexpected skip'), 'nt'),
                (skipped.replace(name, 'test_other'), 'nt'),
                (skipped.replace('Ran 4', 'Ran 3'), 'nt')]:
            with self.subTest(platform=platform, output=text), self.assertRaises(AssertionError):
                C.verify_replay_execution(text, expected, execution_os_name=platform)

    def test_live_subscription_fifteen_guarded_calls(self):
        self.assertEqual(C.replay_subscription(ROOT), RECEIPT['subscription_calls'])
        self.assertEqual(RECEIPT['subscription_calls']['call_count'], 15)
        self.assertEqual(RECEIPT['subscription_calls']['blocked_io_attempts'], [])

    def test_live_upgrade_163_recorded_calls(self):
        self.assertEqual(C.replay_upgrade(ROOT), RECEIPT['upgrade_calls'])
        self.assertEqual(RECEIPT['upgrade_calls']['call_count'], 163)
        self.assertEqual(RECEIPT['upgrade_calls']['same_recorded_errors'], 6)

    def test_unknown_current_hash_and_additional_code_change_fail_closed(self):
        for replacement in (b'# unreviewed runtime\n', (ROOT / C.RUNTIME).read_bytes() + b'\n# extra change\n'):
            with self.subTest(replacement_digest=C.sha(replacement)), self.current_copy() as copied:
                (copied / C.RUNTIME).write_bytes(replacement)
                with self.assertRaisesRegex(AssertionError, 'Unreviewed current runtime'):
                    C.verify_current(copied, EXPECTED_MANIFEST)

    def test_incorrect_reverse_transition_and_unknown_historical_pin_fail_closed(self):
        with patch.object(C, 'OLD_LINE', C.OLD_LINE.replace('value,', 'None,')):
            with self.assertRaisesRegex(AssertionError, 'Incorrect reconstructed'):
                C.reconstruct_historical_runtime((ROOT / C.RUNTIME).read_bytes())
        with self.assertRaisesRegex(AssertionError, 'Unknown historical runtime'):
            C.verify_historical_pin_on_current(ROOT, C.RUNTIME, '0' * 64, EXPECTED_MANIFEST)

    def test_missing_changed_extra_and_unreviewed_supplement_fail_closed(self):
        for relative in ('manifest.json', 'replay-receipt.json', 'REVIEW.md', 'verify.py'):
            for operation in ('missing', 'changed'):
                with self.subTest(file=relative, operation=operation), self.current_copy() as copied:
                    path = copied / C.REL / relative
                    if operation == 'missing':
                        path.unlink()
                    else:
                        path.write_bytes(path.read_bytes() + b'\n')
                    with self.assertRaises(AssertionError):
                        load(copied)
        with self.current_copy() as copied:
            (copied / C.REL / 'unreviewed.txt').write_text('extra', encoding='utf-8')
            with self.assertRaisesRegex(AssertionError, 'inventory'):
                C.verify_current(copied, EXPECTED_MANIFEST)

    def test_changed_prerequisite_and_historical_packet_fail_closed(self):
        for relative in ('skills/claude-guardian/references/intake.md',
                         'docs/evidence/local-incident-v1/dialogues-projection-public.json',
                         'docs/evidence/subscription-upgrade-conflict/projection.json',
                         'docs/evidence/subscription-boundaries/current-guidance-source-pins.json',
                         'docs/evidence/batch33-subscription-preservation/live-helper-replay.json'):
            with self.subTest(source=relative), self.current_copy() as copied:
                path = copied / relative
                path.write_bytes(path.read_bytes() + b'\n')
                with self.assertRaisesRegex(AssertionError, 'drift|packet changed'):
                    C.verify_current(copied, EXPECTED_MANIFEST)

    def test_changed_replay_state_fails_even_without_receipt_byte_checks(self):
        suite = 'tests/test_acceptance_local_incident_cases.py'
        actual = C.replay_output(ROOT, suite)
        C.verify_replay_value(actual, RECEIPT['semantic_suites'][suite])
        changed = deepcopy(actual)
        changed['T22']['macos']['initial']['state']['context']['route'] = 'vps'
        with self.assertRaisesRegex(AssertionError, 'Semantic replay result mismatch'):
            C.verify_replay_value(changed, RECEIPT['semantic_suites'][suite])


if __name__ == '__main__':
    unittest.main()
