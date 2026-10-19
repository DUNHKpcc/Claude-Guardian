"""Exact current 67-member builder delta, separate from historical acceptance."""
import hashlib
import json

CURRENT_PACKAGE_BUILDER_SHA256 = '91b78bc2d33024941614f7a4b9377df075888b9d02564620ac1cbe4c78754cee'
HISTORICAL_PACKAGE_PROOF_SHA256 = '3c609b1ef9cbb3cc435db6be0913daadf345840716d87c1ee797eaf61cf6c451'
ADDED_ENTRIES = (b'"scripts/macos_metadata_observer.py", ', b'"scripts/environment_entry.py", ', b'"scripts/agent_rules_task.py", ',
                 b'"references/agent-rules-task.md", ')


def verify_current_packager_transition(current, proof_bytes):
    """Reverse exactly four explicit additions; check the entire old builder."""
    if hashlib.sha256(proof_bytes).hexdigest() != HISTORICAL_PACKAGE_PROOF_SHA256:
        raise AssertionError('Historical package proof changed')
    if hashlib.sha256(current).hexdigest() != CURRENT_PACKAGE_BUILDER_SHA256:
        raise AssertionError('Unreviewed current package builder')
    historical = current
    for entry in ADDED_ENTRIES:
        if historical.count(entry) != 1:
            raise AssertionError('Expected each exact package entry once')
        historical = historical.replace(entry, b'', 1)
    proof = json.loads(proof_bytes)
    if hashlib.sha256(historical).hexdigest() != proof['package_builder_sha256']['after']:
        raise AssertionError('Other historical package builder bytes changed')
    return historical
