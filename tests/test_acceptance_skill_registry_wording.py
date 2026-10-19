"""Exact one-off SKILL wording compatibility, never historical regeneration.

The independent review covers only the exact registry-count wording deletion.
Every other source byte and all historical evidence remain strictly pinned.
"""
import hashlib
import json
from pathlib import Path
import unittest
from unittest.mock import patch
from acceptance_runtime_compat import historical_baseline

ROOT = Path(__file__).resolve().parents[1]
SKILL_PATH = 'skills/claude-guardian/SKILL.md'
SUPPLEMENT_RELATIVE = 'docs/evidence/skill-registry-wording-compatibility.json'
SUPPLEMENT = ROOT / SUPPLEMENT_RELATIVE
SUPPLEMENT_SHA256 = '36428311925b3ab54ec4be34d0e7654d60b6ac640c3aebef09a1259488a86d9d'
OLD_SHA256 = 'e34047180a0259a6a14e606f583ef0897c2057f5477e7c16f2aefde7af2fd276'
NEW_SHA256 = 'f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3'
BEFORE = '97 个问题 ID 按条件调度，Q-C07 始终停用。'.encode('utf-8')
AFTER = '问题 ID 按条件调度，Q-C07 始终停用。'.encode('utf-8')


def checked_registry_wording_sha256(content, historical_sha256):
    """Return actual bytes' digest, accepting only this reviewed old/new pair."""
    if SUPPLEMENT.is_symlink() or not SUPPLEMENT.is_file():
        raise ValueError('Missing or aliased registry-wording review')
    raw = SUPPLEMENT.read_bytes()
    if hashlib.sha256(raw).hexdigest() != SUPPLEMENT_SHA256:
        raise ValueError('Unreviewed registry-wording supplement')
    review = json.loads(raw)
    expected_change = {'path': SKILL_PATH, 'historical_sha256': OLD_SHA256,
        'current_sha256': NEW_SHA256, 'before': BEFORE.decode('utf-8'),
        'after': AFTER.decode('utf-8'), 'occurrences': 1}
    if (review['schema_version'] != 'guardian-skill-registry-wording/1'
            or review['change'] != expected_change
            or review['review']['status'] != 'independently_reviewed'
            or review['review']['decision'] != 'compatible_for_exact_documentation_delta'
            or review['review']['blocking_findings'] != []
            or not review['review']['reviewed_at_utc']
            or not review['review']['reviewer_reference']):
        raise ValueError('Registry-wording compatibility is not established')
    if historical_sha256 != OLD_SHA256:
        raise ValueError('Unreviewed historical SKILL source pin')
    actual = hashlib.sha256(content).hexdigest()
    if actual not in (OLD_SHA256, NEW_SHA256):
        raise ValueError('Unreviewed SKILL source bytes')
    original = content if actual == OLD_SHA256 else content.replace(AFTER, BEFORE, 1)
    if (original.count(BEFORE) != 1
            or hashlib.sha256(original).hexdigest() != OLD_SHA256
            or original.replace(BEFORE, AFTER, 1).count(AFTER) != 1
            or hashlib.sha256(original.replace(BEFORE, AFTER, 1)).hexdigest() != NEW_SHA256):
        raise ValueError('SKILL change is not the single reviewed wording replacement')
    return actual


class RegistryWordingCompatibilityTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        # Exact release fixture for retained-source checks, never live acceptance.
        context = historical_baseline(ROOT)
        cls.HISTORICAL_ROOT = context.__enter__()
        cls.addClassCleanup(context.__exit__, None, None, None)

    def test_historical_document_has_exact_count_free_wording(self):
        path = self.HISTORICAL_ROOT / SKILL_PATH
        self.assertFalse(path.is_symlink())
        content = path.read_bytes()
        self.assertEqual(checked_registry_wording_sha256(content, OLD_SHA256), NEW_SHA256)
        self.assertNotIn(BEFORE, content)
        self.assertEqual(content.count(AFTER), 1)

    def test_exact_old_bytes_remain_historical_and_reconstructable(self):
        current = (self.HISTORICAL_ROOT / SKILL_PATH).read_bytes()
        old = current.replace(AFTER, BEFORE, 1)
        self.assertEqual(checked_registry_wording_sha256(old, OLD_SHA256), OLD_SHA256)
        self.assertEqual(old.replace(BEFORE, AFTER, 1), current)

    def test_unreviewed_drift_and_other_count_edits_fail_closed(self):
        current = (self.HISTORICAL_ROOT / SKILL_PATH).read_bytes()
        for changed in (current + b'\n', current.replace(b'PC0', b'PC1', 1),
                        current.replace(AFTER, BEFORE.replace(b'97', b'98'), 1),
                        current + AFTER, current.replace(AFTER, b'', 1),
                        current.replace('Q-C07 始终停用'.encode('utf-8'),
                                        'Q-C07 可以恢复'.encode('utf-8'), 1)):
            with self.subTest(digest=hashlib.sha256(changed).hexdigest()):
                with self.assertRaises(ValueError):
                    checked_registry_wording_sha256(changed, OLD_SHA256)
        with self.assertRaises(ValueError):
            checked_registry_wording_sha256(current, '0' * 64)

    def test_unpinned_or_missing_review_fails_closed(self):
        current = (self.HISTORICAL_ROOT / SKILL_PATH).read_bytes()
        with patch(__name__ + '.SUPPLEMENT_SHA256', '0' * 64):
            with self.assertRaises(ValueError):
                checked_registry_wording_sha256(current, OLD_SHA256)
        with patch(__name__ + '.SUPPLEMENT', ROOT / 'nonexistent-registry-wording-review.json'):
            with self.assertRaises(ValueError):
                checked_registry_wording_sha256(current, OLD_SHA256)

    def test_current_entry_guidance_is_outside_the_old_wording_bridge(self):
        current = (ROOT / SKILL_PATH).read_bytes()
        self.assertNotEqual(hashlib.sha256(current).hexdigest(), NEW_SHA256)
        with self.assertRaisesRegex(ValueError, 'Unreviewed SKILL source bytes'):
            checked_registry_wording_sha256(current, OLD_SHA256)
        # Current acceptance of four cases lives in the separate entry review;
        # rejection here is required, not a compatibility failure to bypass.


if __name__ == '__main__':
    unittest.main()
