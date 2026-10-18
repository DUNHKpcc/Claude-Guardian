"""Retained original subscription T36/T38/T46/T54 L+C review evidence checks.

Load the portable retained-evidence tests from the documented packet location.
Actual model prose stays in retained files; no canned response generator exists.
See docs/evidence/subscription-boundaries/CURRENT-REVIEW.md for semantic review.
"""
import importlib.util
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
PACKET = ROOT / 'docs/evidence/subscription-boundaries'


def load(name, filename):
    spec = importlib.util.spec_from_file_location(name, PACKET / 'tests' / filename)
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


OriginalEvidence = load('subscription_boundary_original_evidence', 'test_subscription_boundaries_evidence.py')
CurrentEvidence = load('subscription_boundary_current_evidence', 'test_subscription_boundaries_current.py')
RetainedSubscriptionBoundaryEvidence = OriginalEvidence.RetainedSubscriptionBoundaryEvidence
CurrentSubscriptionBoundaryReview = CurrentEvidence.CurrentSubscriptionBoundaryReview


class SubscriptionBoundaryInstalledCandidatePins(unittest.TestCase):
    def test_exact_live_guidance_runtime_and_design_pins(self):
        pins = json.loads((PACKET / 'current-guidance-source-pins.json').read_text(encoding='utf-8'))
        for entry in pins['pins']:
            actual = hashlib.sha256((ROOT / entry['relative_path']).read_bytes()).hexdigest()
            self.assertEqual(actual, entry['current_sha256'], entry['relative_path'])
        proof = json.loads((PACKET / 'package-inventory-proof.json').read_text(encoding='utf-8'))
        self.assertEqual(hashlib.sha256((ROOT / 'tools/package_skill.py').read_bytes()).hexdigest(),
                         proof['package_builder_sha256']['after'])

    def test_original_live_ledger_clauses_and_layers_unchanged(self):
        current = json.loads((PACKET / 'current-verdicts.json').read_text(encoding='utf-8'))['case_verdicts']
        ledger = json.loads((ROOT / 'docs/acceptance-rebuild-ledger.json').read_text(encoding='utf-8'))

        def find(value, case):
            if isinstance(value, dict):
                if value.get('id') == case:
                    yield value
                for child in value.values():
                    yield from find(child, case)
            elif isinstance(value, list):
                for child in value:
                    yield from find(child, case)

        for case, review in current.items():
            found = list(find(ledger, case))
            self.assertEqual(len(found), 1)
            original = review['original']['ledger_row_verbatim_object']
            for key in ('id', 'scenario', 'requirement', 'verification_layer'):
                self.assertEqual(found[0][key], original[key], case + ':' + key)
