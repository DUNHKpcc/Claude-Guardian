# Reconstruction and deferred acceptance

## Basis

On 2026-10-18 the working tree was rebuilt from published commit
`584064fc9c210e684ba4a0e11b79db74f1946155`. The previously described local
23-batch source and patches were not available in this workspace. Two retained
handover documents supply historical scheduling and requirements, not executable
proof. This reconstruction does not claim byte identity with those missing changes.

The baseline full Python suite ran again: 1,034 total, 1,026 passed and 8 skipped.
These are baseline subtests, not 218 complete design-case acceptances.

## Exact checklist

[The 218-case ledger](acceptance-rebuild-ledger.json) preserves every original ID,
scenario, full requirement and literal verification layer from the published
tracker. Its original-row SHA-256 is
`84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`.

Scheduling: 75 cloud-only, 113 native-deferred, 30 conditionally native. All 116
rows containing original native layer N remain in a deferred or conditional
class. Each row retains its later test steps and dependencies. The retained
historical 67 complete-case claims are not imported as fresh accepted cases;
new exact-case evidence and review are required. Existing dated baseline evidence
is retained within its original limits rather than declared invalid.

Mac and Windows execution is deferred at the owner's request. Required follow-up
includes target/runtime identity; proxy/controller ownership; platform DNS,
IPv6 and WebRTC paths; actual client profiles; approved configuration write,
reload and recovery; permissions and cancellation. A hosted CI result or Linux
fixture cannot substitute for the user's native environment. Historical Mac
file-metadata experiments cover only content, mode, group, ordinary xattrs and
ACL within their tested conditions, not different owner/provenance or full app
recovery. Windows write/rollback remains unimplemented.

## Reconstruction discipline

Rebuild a small coherent change set, reproduce a concrete failure, add regression
evidence and rerun the required aggregate checks. Preserve source, patch and
check receipt together in a persistent backup before leaving a batch. GitHub
publication remains a separate verified action under the repository's exact-batch
approval rule. No PR, force push or native-settings modification is implied.

## First-batch boundaries

The rebuilt selector and plan-retention guards are offline control-flow fixes.
They do not open production repair admission. A cancellation or change detected
after a private plan artifact was created returns failure without a successful
current digest; the artifact may remain. It is not blindly removed because its
path could now refer to a different user file. Consequently the original
ENV-T123 no-new-file cancellation condition is still pending, not accepted by
this retention fix. The ledger's complete original requirements are authoritative;
its scheduling steps cannot weaken them.

The frozen first batch ran 1,073 tests: 1,065 passed and eight skipped
(13.229 seconds). Both Node synthetic suites and Python compilation passed.
Two independently built packages were byte-identical, SHA-256
`25df240a43df4d47640a8564bf0a73a4f4cfde7df38e89c0c476dcb33dae5216`.
Independent review reran 166 targeted tests and found no remaining blocking issue.
No complete design-case acceptance or native success is inferred from these counts.

## Second-batch offline checks

Recognized cancellation before export no longer creates a report. Interview
argument/output failures avoid raw private diagnostic text, and existing
credential screening includes GitHub-shaped tokens. Source indexes now separate
the eight historical inputs from the current packaged sources without changing
original source bytes or licensing attribution. Full regression: 1,100 tests,
1,092 passed and eight skipped (13.568 seconds), plus both Node synthetic suites,
compilation and repeatable packaging. ENV-T123 and native acceptance remain open.


## Fourth-batch original-case revalidation

T09, T19, T20 and T21 now have freshly reviewed evidence at their original L+C
layers. See the pinned evidence paths in acceptance-rebuild-ledger.json. This
means deterministic normalized-input replay plus full active-guidance review,
not arbitrary model integration, native deployment or production safety. The
other 214 original cases remain pending; T24 has a reproduced resume review gap.
The historical tracker rows and their exact hash remain unchanged.
