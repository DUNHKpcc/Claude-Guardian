"""Historical T77/T80 evidence pins and separate direct-current regressions.

No old source approval is presented as current acceptance.
"""
import hashlib
import atexit
import importlib.util
import json
import os
from pathlib import Path
import sys
import unittest
from unittest.mock import patch

from acceptance_runtime_compat import (EXPECTED_MANIFEST as COPY_MANIFEST,
                                       historical_baseline, load as load_copy_compatibility)

ROOT = Path(os.environ['GUARDIAN_AUDIT_ROOT']) if 'GUARDIAN_AUDIT_ROOT' in os.environ else Path(__file__).resolve().parents[1]
PACKET = Path(os.environ['GUARDIAN_UPGRADE_PACKET']) if 'GUARDIAN_UPGRADE_PACKET' in os.environ else ROOT / 'docs/evidence/subscription-upgrade-conflict'
EXPECTED_MANIFEST = 'cc7d25b302de2ebfa1d265fafb689a3b90768c9f8db4feb25ee68a199dea2fa2'
raw = (PACKET / 'manifest.json').read_bytes()
if hashlib.sha256(raw).hexdigest() != EXPECTED_MANIFEST:
    raise AssertionError('Installed T77/T80 evidence manifest pin mismatch')
manifest = json.loads(raw)
for relative, expected in manifest['files'].items():
    path = Path(relative)
    if path.is_absolute() or '..' in path.parts:
        raise AssertionError('Unsafe evidence member')
    if hashlib.sha256((PACKET / path).read_bytes()).hexdigest() != expected:
        raise AssertionError('Installed T77/T80 evidence member mismatch: ' + relative)
os.environ['GUARDIAN_AUDIT_ROOT'] = str(ROOT)
os.environ['GUARDIAN_UPGRADE_EXPECTED_MANIFEST'] = EXPECTED_MANIFEST
spec = importlib.util.spec_from_file_location('guardian_retained_upgrade_conflict_tests', PACKET / 'tests/test_upgrade_conflict_evidence.py')
module = importlib.util.module_from_spec(spec)
sys.modules[spec.name] = module
spec.loader.exec_module(module)
_BASELINE = historical_baseline(ROOT)
HISTORICAL_BASELINE_ROOT = _BASELINE.__enter__()
atexit.register(_BASELINE.__exit__, None, None, None)
COPY = load_copy_compatibility(HISTORICAL_BASELINE_ROOT)
_HISTORY = COPY.historical_source_view(HISTORICAL_BASELINE_ROOT, COPY_MANIFEST)
HISTORICAL_ROOT = _HISTORY.__enter__()
atexit.register(_HISTORY.__exit__, None, None, None)


class HistoricalUpgradeConflictEvidence(unittest.TestCase):
    """Original source identities and retained evidence remain strictly historical."""

    def test_historical_public_packet_source_original_clauses_and_all_turn_chains(self):
        COPY.verify_current(HISTORICAL_BASELINE_ROOT, COPY_MANIFEST)
        with patch.object(module, 'ROOT', HISTORICAL_ROOT):
            module.RetainedUpgradeConflictEvidence.test_public_packet_source_original_clauses_and_all_turn_chains(self)

    def test_historical_modified_evidence_manifest_and_source_fail_closed(self):
        with patch.object(module, 'ROOT', HISTORICAL_ROOT):
            module.RetainedUpgradeConflictEvidence.test_modified_evidence_manifest_and_live_source_fail_closed(self)

    test_historical_pooled_semantics_reject_tampering_cycles_and_missing_values = module.RetainedUpgradeConflictEvidence.test_pooled_semantics_reject_tampering_cycles_and_missing_values
    test_historical_run_results_preserved_as_declared_projections = module.RetainedUpgradeConflictEvidence.test_historical_run_results_preserved_as_declared_projections
    test_historical_public_inventory_excludes_private_envelopes_and_handles = module.RetainedUpgradeConflictEvidence.test_public_inventory_excludes_private_envelopes_and_handles
    test_historical_python310_syntax_for_public_tests = module.RetainedUpgradeConflictEvidence.test_python310_syntax_for_public_tests


class CurrentUpgradeConflictRuntimeRegressions(unittest.TestCase):
    """These four original behavioral tests still execute ROOT, the current code."""

    test_current_163_recorded_calls = module.RetainedUpgradeConflictEvidence.test_historical_successes_and_fresh_calls_compatible_with_current_source
    test_current_original_nine_terminal_assertions = module.RetainedUpgradeConflictEvidence.test_original_terminal_assertions_on_current_runtime
    test_current_all_fields_conflict_api_and_real_readonly_cli = module.RetainedUpgradeConflictEvidence.test_all_fields_covered_conflict_api_and_real_readonly_cli
    test_current_46_lifecycle_states_and_review_obligation = module.RetainedUpgradeConflictEvidence.test_lifecycle_states_validate_and_preserve_actual_review_obligation


# Every original retained test is routed exactly once, without skipped methods.
_RETAINED_TEST_NAMES = {
    'test_public_packet_source_original_clauses_and_all_turn_chains',
    'test_modified_evidence_manifest_and_live_source_fail_closed',
    'test_pooled_semantics_reject_tampering_cycles_and_missing_values',
    'test_historical_run_results_preserved_as_declared_projections',
    'test_public_inventory_excludes_private_envelopes_and_handles',
    'test_python310_syntax_for_public_tests',
    'test_historical_successes_and_fresh_calls_compatible_with_current_source',
    'test_original_terminal_assertions_on_current_runtime',
    'test_all_fields_covered_conflict_api_and_real_readonly_cli',
    'test_lifecycle_states_validate_and_preserve_actual_review_obligation',
}
if set(unittest.defaultTestLoader.getTestCaseNames(module.RetainedUpgradeConflictEvidence)) != _RETAINED_TEST_NAMES:
    raise AssertionError('Retained upgrade test inventory changed')
