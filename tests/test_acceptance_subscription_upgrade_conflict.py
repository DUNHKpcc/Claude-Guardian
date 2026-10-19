"""Pinned project-only T77/T80 public projection; no evidence enters the Skill."""
import hashlib
import importlib.util
import json
import os
from pathlib import Path
import sys

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
RetainedUpgradeConflictEvidence = module.RetainedUpgradeConflictEvidence
