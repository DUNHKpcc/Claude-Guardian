"""Integrity checks only: these do not accept the 218 behavioral cases."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]

# Explicit cases and original layer spellings; scheduling does not imply acceptance.
ACCEPTED = {
    **{case: ('docs/evidence/rebuild-entry-order.md', 'L+C', ['L', 'C'])
       for case in ('T29', 'T57')},
    **{case: ('docs/evidence/rebuild-mobile-route.md', 'L+C', ['L', 'C'])
       for case in ('T49', 'T83')},
    **{case: ('docs/evidence/rebuild-history-and-pause.md', 'L+C', ['L', 'C'])
       for case in ('T31', 'T47')},
    'T82': ('docs/evidence/rebuild-legacy-retirement.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-t03-t05-guided-responses.md', 'L+C', ['L', 'C'])
       for case in ('T03', 'T05')},
    'T16': ('docs/evidence/rebuild-resume-completion.md', 'L+C', ['L', 'C']),
    'T23': ('docs/evidence/rebuild-local-egress.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-intake-basics.md', 'L+C', ['L', 'C'])
       for case in ('T01', 'T02')},
    'T18': ('docs/evidence/rebuild-t18-appeal-facts.md', 'L+C', ['L', 'C']),
    'T09': ('docs/evidence/rebuild-source-dedup.md', 'L+C', ['L', 'C']),
    **{case: ('docs/evidence/rebuild-route-cases.md', 'L+C', ['L', 'C'])
       for case in ('T19', 'T20', 'T21', 'T24')},
    **{case: ('docs/evidence/rebuild-intake-cases.md', 'L+C', ['L', 'C'])
       for case in ('T53', 'T74', 'T81')},
    **{case: ('docs/evidence/rebuild-task-scope-cases.md', 'L+C', ['L', 'C'])
       for case in ('T34', 'T43', 'T48', 'T78')},
    'ENV-T40': ('docs/evidence/rebuild-env40-composition.md', 'L + R', ['L', 'R']),
    'ENV-T79': ('docs/evidence/rebuild-enforcement-cases.md', 'L', ['L']),
    'ENV-T81': ('docs/evidence/rebuild-required-controls-case.md', 'L + C', ['L', 'C']),
    'ENV-T90': ('docs/evidence/rebuild-enforcement-cases.md', 'L + C', ['L', 'C']),
}


class AcceptanceRebuildLedgerTests(unittest.TestCase):
    def test_all_original_conditions_and_layers_are_preserved(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        original = [line for line in (ROOT / 'docs/implementation-tracker.md').read_text(encoding='utf-8').splitlines()
                    if re.match(r'^\| (?:T\d+|ENV-T\d+) \|', line)]
        self.assertEqual(len(original), 218)
        self.assertEqual(ledger['original_rows_sha256'], hashlib.sha256(('\n'.join(original) + '\n').encode()).hexdigest())
        cases = ledger['cases']
        self.assertEqual(len(cases), 218)
        self.assertEqual(len({case['id'] for case in cases}), 218)
        for case, line in zip(cases, original):
            expected = [value.strip() for value in line.split('|')[1:-1]]
            self.assertEqual([case['id'], case['scenario'], case['requirement'], case['verification_layer']], expected[:4])

    def test_accepted_evidence_underlying_pins_are_current(self):
        # Hashes are invalidation signals, not substitutes for L+C review.
        expected_counts = {
            'docs/evidence/rebuild-entry-order.md': 11,
            'docs/evidence/rebuild-mobile-route.md': 11,
            'docs/evidence/rebuild-history-and-pause.md': 12,
            'docs/evidence/rebuild-legacy-retirement.md': 14,
            'docs/evidence/rebuild-resume-completion.md': 15,
            'docs/evidence/rebuild-local-egress.md': 7,
            # T18 retained artifact and guide hashes have their own evidence suite.
            'docs/evidence/rebuild-intake-basics.md': 18,
            'docs/evidence/rebuild-env40-composition.md': 17,
            'docs/evidence/rebuild-route-cases.md': 15,
            'docs/evidence/rebuild-source-dedup.md': 4,
            'docs/evidence/rebuild-enforcement-cases.md': 16,
            'docs/evidence/rebuild-intake-cases.md': 15,
            'docs/evidence/rebuild-required-controls-case.md': 13,
            'docs/evidence/rebuild-task-scope-cases.md': 17,
        }
        for path, count in expected_counts.items():
            page = (ROOT / path).read_text(encoding='utf-8')
            pins = re.findall(r'^\| `([^`]+)` \| `([0-9a-f]{64})` \|$', page, re.MULTILINE)
            self.assertEqual(len(pins), count)
            self.assertEqual(len({name for name, _ in pins}), count)
            for name, digest in pins:
                with self.subTest(evidence=path, reviewed_file=name):
                    self.assertEqual(hashlib.sha256((ROOT / name).read_bytes()).hexdigest(), digest,
                                     'Relevant bytes changed: rerun and re-review L+C before refreshing pins')

    def test_scheduling_is_not_acceptance(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        counts = {}
        for case in ledger['cases']:
            accepted = case['id'] in ACCEPTED
            self.assertEqual(case['rebuild_acceptance'], 'accepted_revalidated' if accepted else 'pending_revalidation')
            if accepted:
                expected_path, original_layer, reviewed_layers = ACCEPTED[case['id']]
                self.assertEqual(case['verification_layer'], original_layer)
                evidence = case['evidence']
                self.assertEqual(evidence['path'], expected_path)
                self.assertEqual(evidence['layers'], reviewed_layers)
                self.assertEqual(evidence['sha256'], hashlib.sha256((ROOT / expected_path).read_bytes()).hexdigest())
                self.assertTrue(evidence['boundary'])
            else:
                self.assertNotIn('evidence', case)
            self.assertTrue(case['next_steps'])
            self.assertTrue(case['dependencies'])
            counts[case['scheduling']] = counts.get(case['scheduling'], 0) + 1
            if 'N' in case['verification_layer']:
                self.assertIn(case['scheduling'], ('deferred_native', 'conditional_native'))
        self.assertEqual(counts, {'cloud_only': 75, 'deferred_native': 113, 'conditional_native': 30})


if __name__ == '__main__':
    unittest.main()
