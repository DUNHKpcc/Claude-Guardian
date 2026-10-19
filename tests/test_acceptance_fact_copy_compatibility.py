"""Fresh live verification plus explicit, byte-real historical source preservation."""
from contextlib import contextmanager
from copy import deepcopy
import json
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
                    old = C.replay_output(historical, suite)
                    current = C.replay_output(ROOT, suite)
                    self.assertEqual(old, current, 'Complete current state/question/assessment replay changed')
                    C.verify_replay_value(old, expected)
                    C.verify_replay_value(current, expected)
        C.verify_current(ROOT, EXPECTED_MANIFEST)

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
