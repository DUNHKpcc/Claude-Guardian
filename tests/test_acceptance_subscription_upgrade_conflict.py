"""Pinned project-only T77/T80 public projection; no evidence enters the Skill."""
import hashlib
import atexit
import importlib.util
import json
import os
from pathlib import Path
import sys
from unittest.mock import patch

from acceptance_runtime_compat import EXPECTED_MANIFEST as COPY_MANIFEST, load as load_copy_compatibility

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
COPY = load_copy_compatibility(ROOT)
_HISTORY = COPY.historical_source_view(ROOT, COPY_MANIFEST)
HISTORICAL_ROOT = _HISTORY.__enter__()
atexit.register(_HISTORY.__exit__, None, None, None)


class RetainedUpgradeConflictEvidence(module.RetainedUpgradeConflictEvidence):
    # Only old source identity and its old negative control use genuine historical
    # bytes. Every inherited behavioral replay, terminal, CLI and lifecycle test
    # still uses ROOT, the current candidate. No old packet/test is rewritten.
    def test_public_packet_source_original_clauses_and_all_turn_chains(self):
        COPY.verify_current(ROOT, COPY_MANIFEST)
        with patch.object(module, 'ROOT', HISTORICAL_ROOT):
            super().test_public_packet_source_original_clauses_and_all_turn_chains()

    def test_modified_evidence_manifest_and_live_source_fail_closed(self):
        # Preserve the original drift check where its initial source tuple holds.
        # Separate compatibility controls reject drift in the actual current tree.
        with patch.object(module, 'ROOT', HISTORICAL_ROOT):
            super().test_modified_evidence_manifest_and_live_source_fail_closed()

