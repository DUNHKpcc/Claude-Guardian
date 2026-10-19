"""Retained original subscription T36/T38/T46/T54 L+C review evidence checks.

Load the portable retained-evidence tests from the documented packet location.
Actual model prose stays in retained files; no canned response generator exists.
Historical review stays in docs/evidence/subscription-boundaries/CURRENT-REVIEW.md.
Historical compatibility is retained in batch33-subscription-preservation/REVIEW.md.
The old fact-copy transition is now checked only on its fixed historical source.
Current runtime regression checks are separate and do not renew acceptance.
"""
import importlib.util
import atexit
import hashlib
import json
import os
from pathlib import Path
import sys
import unittest

from acceptance_runtime_compat import (EXPECTED_MANIFEST as COPY_MANIFEST,
                                       historical_baseline, load as load_copy_compatibility)

ROOT = Path(os.environ.get('GUARDIAN_AUDIT_ROOT', Path(__file__).resolve().parents[1]))
PACKET = ROOT / 'docs/evidence/subscription-boundaries'
_BASELINE = historical_baseline(ROOT)
HISTORICAL_BASELINE_ROOT = _BASELINE.__enter__()
atexit.register(_BASELINE.__exit__, None, None, None)
COPY = load_copy_compatibility(HISTORICAL_BASELINE_ROOT)
# Old approvals inspect real historical bytes; current execution is tested separately.
_HISTORY = COPY.historical_source_view(HISTORICAL_BASELINE_ROOT, COPY_MANIFEST)
HISTORICAL_ROOT = _HISTORY.__enter__()
atexit.register(_HISTORY.__exit__, None, None, None)


# This pins one sanitized historical-preservation projection, not raw approval identity.
# Complete historical/current source tuple checks remain strict; see bridge PROJECTION.md.
BRIDGE = Path('docs/evidence/batch33-subscription-preservation')
BRIDGE_MANIFEST_SHA256 = '71c7b62c7f55a59d0d9556ea3ea605a162bc2e919f5bf7e223769ef731f0284e'


METADATA_OBSERVER_PACKAGER_SHA256 = '1ea4db679625908ca0a9ad103aa79309421725e0cc4d17f7c8d046291572f37b'
HISTORICAL_PACKAGE_PROOF_SHA256 = '3c609b1ef9cbb3cc435db6be0913daadf345840716d87c1ee797eaf61cf6c451'


def verify_metadata_observer_packager_transition(current, proof_bytes):
    """Reverse only the exact observer entry; retain the entire old builder pin."""
    if hashlib.sha256(proof_bytes).hexdigest() != HISTORICAL_PACKAGE_PROOF_SHA256:
        raise AssertionError('Historical package proof changed')
    if hashlib.sha256(current).hexdigest() != METADATA_OBSERVER_PACKAGER_SHA256:
        raise AssertionError('Unreviewed current package builder')
    entry = b'"scripts/macos_metadata_observer.py", '
    if current.count(entry) != 1:
        raise AssertionError('Expected the single exact observer manifest entry')
    historical = current.replace(entry, b'', 1)
    proof = json.loads(proof_bytes)
    if hashlib.sha256(historical).hexdigest() != proof['package_builder_sha256']['after']:
        raise AssertionError('Other historical package builder bytes changed')
    return historical


def load_historical_preservation(root=HISTORICAL_ROOT):
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
    spec = importlib.util.spec_from_file_location('subscription_historical_preservation', verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.ROOT = root
    module.PINNED_MANIFEST_SHA256 = BRIDGE_MANIFEST_SHA256
    module.PINNED_LOADER = load_historical_preservation
    return module


Preservation = load_historical_preservation()
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
class HistoricalRetainedSubscriptionBoundaryEvidence(OriginalEvidence.RetainedSubscriptionBoundaryEvidence):
    """Frozen original evidence and its old retained controls, not current acceptance."""


class HistoricalSupplementalSubscriptionBoundaryReview(CurrentEvidence.CurrentSubscriptionBoundaryReview):
    """The packet's historical v2 'current' review, not the present repository."""



class HistoricalSubscriptionBoundarySourcePins(unittest.TestCase):
    def test_historical_guidance_runtime_design_and_64_member_builder_pins(self):
        # Historical equality is checked on actual reconstructed historical bytes.
        # The old supplement binds only its fixed historical fact-copy transition.
        COPY.verify_current(HISTORICAL_BASELINE_ROOT, COPY_MANIFEST)
        Preservation.verify_bridge(HISTORICAL_ROOT, BRIDGE_MANIFEST_SHA256)
        # Historical packaging added one observer, without rewriting earlier proof
        # or normalizing any other builder bytes into an apparent match.
        verify_metadata_observer_packager_transition(
            (HISTORICAL_BASELINE_ROOT / 'tools/package_skill.py').read_bytes(),
            (PACKET / 'package-inventory-proof.json').read_bytes(),
        )

class CurrentSubscriptionBoundaryRuntimeTests(unittest.TestCase):
    """Direct current runtime regressions; historical prose is not regenerated."""

    def test_current_runtime_replays_all_fifteen_guarded_calls(self):
        receipt = COPY.read_json(ROOT / COPY.REL / 'replay-receipt.json')
        self.assertEqual(COPY.replay_subscription(ROOT), receipt['subscription_calls'])

    def test_current_ledger_original_clauses_and_layers_unchanged(self):
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
