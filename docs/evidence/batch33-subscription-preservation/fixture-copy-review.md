# Read-only evidence fixture compatibility

2026-10-18. Final aggregate integration found a negative-control error because the retained historical integration-manifest.json is read-only (0444). shutil.copytree preserved that mode, so mutation of the newly created disposable copy failed before the intended hash rejection. The original source file and historical evidence bytes remain unchanged.

Only test fixture construction now uses shutil.copyfile for byte-identical writable temporary copies. That fixture-only correction left the semantic verify_bridge function, strict tuple, source review, manifest verification and negative rejection conditions unchanged. The later public-projection schema update is described separately in PROJECTION.md. A new regression constructs its own read-only source, copies through the same helper, mutates only the copy and checks original bytes remain unchanged. Temporary fixture permissions are restored before cleanup. This does not alter project or user-device permissions.

The original full-suite failure log SHA-256 is ca47670bb63e5776b6fd9e2a8b09f3a78f47e75d5fd30922d3e79921e911c076. After this test-only correction, the bridge suite passes28 tests with zero skips (0.907s, exit0). The separately completed T77/T80 evidence also required adding those two original IDs to the explicit ledger integrity test mapping; all3 ledger tests pass (0.025s, exit0). Final full-suite validation is recorded separately.

Earlier27-test receipts remain historical. The current pinned verifier includes one additional fixture regression; review/pin advancement does not claim that historical verifier bytes changed retroactively.
