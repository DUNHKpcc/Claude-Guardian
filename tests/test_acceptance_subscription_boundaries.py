"""Retained original subscription T36/T38/T46/T54 L+C review evidence checks.

Load the portable retained-evidence tests from the documented packet location.
Actual model prose stays in retained files; no canned response generator exists.
Historical review stays in docs/evidence/subscription-boundaries/CURRENT-REVIEW.md.
Historical compatibility is retained in batch33-subscription-preservation/REVIEW.md.
The new exact runtime transition is reviewed in fact-copy-compatibility/REVIEW.md.
"""
import importlib.util
import atexit
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

from acceptance_runtime_compat import EXPECTED_MANIFEST as COPY_MANIFEST, load as load_copy_compatibility

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
PACKET = ROOT / 'docs/evidence/subscription-boundaries'
COPY = load_copy_compatibility(ROOT)
# Old approvals inspect real historical bytes; current execution is tested separately.
_HISTORY = COPY.historical_source_view(ROOT, COPY_MANIFEST)
HISTORICAL_ROOT = _HISTORY.__enter__()
atexit.register(_HISTORY.__exit__, None, None, None)


# This pins one sanitized historical-preservation projection, not raw approval identity.
# Complete historical/current source tuple checks remain strict; see bridge PROJECTION.md.
BRIDGE = Path('docs/evidence/batch33-subscription-preservation')
BRIDGE_MANIFEST_SHA256 = '71c7b62c7f55a59d0d9556ea3ea605a162bc2e919f5bf7e223769ef731f0284e'


def load_current_preservation(root=HISTORICAL_ROOT):
    directory = root / BRIDGE
    manifest_path = directory / 'manifest.json'
    if (not manifest_path.is_file() or manifest_path.is_symlink()
            or hashlib.sha256(manifest_path.read_bytes()).hexdigest() != BRIDGE_MANIFEST_SHA256):
        raise AssertionError('Missing or unreviewed current-preservation manifest')
    manifest = json.loads(manifest_path.read_text(encoding='utf-8'))
    verifier = directory / 'verify.py'
    if (not verifier.is_file() or verifier.is_symlink()
            or hashlib.sha256(verifier.read_bytes()).hexdigest() != manifest['files']['verify.py']):
        raise AssertionError('Unreviewed preservation verifier must not execute')
    spec = importlib.util.spec_from_file_location('subscription_current_preservation', verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    module.PINNED_MANIFEST_SHA256 = BRIDGE_MANIFEST_SHA256
    module.PINNED_LOADER = load_current_preservation
    return module


Preservation = load_current_preservation()
class HistoricalSubscriptionPreservationBridgeControls(Preservation.SubscriptionPreservationBridgeControls):
    """Original checks on explicitly reconstructed historical source bytes."""


# Verify all historical bytes before importing their retained test modules.
Preservation.verify_bridge(HISTORICAL_ROOT, BRIDGE_MANIFEST_SHA256)


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
    def test_current_fact_copy_runtime_replays_all_fifteen_guarded_calls(self):
        receipt = COPY.read_json(ROOT / COPY.REL / 'replay-receipt.json')
        self.assertEqual(COPY.replay_subscription(ROOT), receipt['subscription_calls'])

    def test_exact_live_guidance_runtime_and_design_pins(self):
        # Historical equality is checked on actual reconstructed historical bytes.
        # The separately pinned supplement binds the precise live transition.
        COPY.verify_current(ROOT, COPY_MANIFEST)
        Preservation.verify_bridge(HISTORICAL_ROOT, BRIDGE_MANIFEST_SHA256)
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
