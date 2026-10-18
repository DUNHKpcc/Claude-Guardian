# Integration handoff

Current whole-case verdicts: T36 satisfied, T38 v2 satisfied, T46 satisfied, T54 satisfied, all original L+C. Historical T38 v1 remains failed and immutable. See CURRENT-REVIEW.md, current-verdicts.json, and the original REVIEW.md; do not flatten their generation provenance.

Recommended layout:

1. Copy this whole packet unchanged to docs/evidence/subscription-boundaries
2. Copy integration/test_acceptance_subscription_boundaries.py to tests/test_acceptance_subscription_boundaries.py
3. Include that module in normal unittest discovery. It loads 18 portable packet tests and adds 2 strict live source/ledger-clause checks, with no skips or source-pin fallback
4. The parent owns exact ledger promotion, broader preservation/CI validation, source-manifest updates and publishing. This reviewer changed none of those shared files

Final checks: 18/18 portable packet tests on Python 3.12 UTF-8, Python 3.12 C-locale/cp1252, and Python 3.13; installed-layout shim 20/20 under UTF-8 and C-locale/cp1252. Earlier baseline support suites passed 129 tests per mode. Exact stdout/stderr, commands, environment overrides and exits are in logs/final-terminal-runs.json, logs/terminal-runs.json and logs/package-terminal-runs.json. Historical reviewer-test schema failures remain retained with the exact initial test source and successful correction history.

No local Python 3.10 interpreter was available: compatible syntax and APIs were checked, not native 3.10 execution. No native Mac/Windows/mobile behavior, actual policy/commercial eligibility, live network isolation, accounts, credentials, transactions or source operations are established.

Actual before/after packages have the same 63 members, with only intake.md changed; complete 62-file active Skill inventories agree except intake. Two clarified-candidate packages are byte-identical. All retained response/review evidence stays outside the installed package. Parent must repeat final packaging after integration.

The integration manifest is a content-addressed inventory, not a claim of whole-tree Git provenance or external write authorization. Keep generation-specific original manifests and the failed v1 stage. No test generates a canned replacement response.
