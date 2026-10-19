"""Pinned loader for the explicit project-only fact-copy compatibility review."""
import hashlib
import importlib.util
import json
from pathlib import Path

REL = 'docs/evidence/fact-copy-compatibility'
EXPECTED_MANIFEST = '95c7bdeaa430a735f1f154d2748f600ccafc6312e5e11f941aa47ada8b599d5e'


def load(root):
    directory = Path(root) / REL
    path = directory / 'manifest.json'
    if path.is_symlink() or not path.is_file() or hashlib.sha256(path.read_bytes()).hexdigest() != EXPECTED_MANIFEST:
        raise AssertionError('Missing or unreviewed fact-copy compatibility manifest')
    manifest = json.loads(path.read_text(encoding='utf-8'))
    verifier = directory / 'verify.py'
    if verifier.is_symlink() or not verifier.is_file() or hashlib.sha256(verifier.read_bytes()).hexdigest() != manifest['files']['verify.py']:
        raise AssertionError('Unreviewed fact-copy verifier must not execute')
    spec = importlib.util.spec_from_file_location('guardian_fact_copy_compatibility', verifier)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    module.verify_current(root, EXPECTED_MANIFEST)
    return module
