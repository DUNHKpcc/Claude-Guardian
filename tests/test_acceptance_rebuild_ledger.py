"""Integrity checks only: these do not accept the 218 behavioral cases."""
import hashlib
import json
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]


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

    def test_scheduling_is_not_acceptance(self):
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))
        counts = {}
        for case in ledger['cases']:
            self.assertEqual(case['rebuild_acceptance'], 'pending_revalidation')
            self.assertTrue(case['next_steps'])
            self.assertTrue(case['dependencies'])
            counts[case['scheduling']] = counts.get(case['scheduling'], 0) + 1
            if 'N' in case['verification_layer']:
                self.assertIn(case['scheduling'], ('deferred_native', 'conditional_native'))
        self.assertEqual(counts, {'cloud_only': 75, 'deferred_native': 113, 'conditional_native': 30})


if __name__ == '__main__':
    unittest.main()
