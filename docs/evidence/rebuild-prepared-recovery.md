# Tenth batch: witness-backed exact-file recovery

Scope: ENV-09 / M13, shared transaction milestone D, and original-receipt conflict
handling. This is a bounded POSIX file recovery capability, not native application
or system repair admission. PC0 and the production native-session gate are
unchanged; Windows writes remain unsupported.

## Gap and evidence

The ninth historical evidence remains scoped to its fixed published commit
`293d856`. This batch supersedes the prepared-recovery capability gap **only for
newly created version-2 receipts**. Legacy prepared receipts remain non-restorable.
These recovery tests do not promote any earlier acceptance claim. Changed
supporting guidance must undergo its own explicit content/case re-review before
any accepted evidence pin is refreshed.

The fresh failing-first test generated an apply whose target replacement
succeeded but whose applied.json write failed. The original backup and prepared
record survived, but there was no reconciliation API. The new regression first
failed on that missing API, then passed with actual separately authorized
restoration of the exact witnessed file. It never synthesizes applied.json.

Independent review also reproduced an important first-WIP defect: modifying the
prepared record or original backup during apply's last approval still allowed the
replacement. Readback of the private record, complete backup/record snapshots,
and batch-path identity rechecks now block those mutations before replacement.
The reviewer's failing/fixed synthetic runs are retained with the batch evidence.

## Public core contract

- `apply` now emits `exact-file-recovery/2`. Before rename, it persists the exact
  staged inode/device, content hash/size, mode/owner/group, timestamps and generated
  basename, together with the private batch identity. The stage and its containing
  directory are synced first; the prepared record and batch directory are synced
  next. After final apply approval, the original backup and prepared record are
  reopened and their full snapshots/digest and batch identity rechecked. The stage,
  original target and parent are also rechecked before rename
- `reconcile(recovery, *, receipt_path, target_ref, target_path, backup_batch)` is
  read-only and deterministic. Explicit caller scope is checked before embedded
  paths are read. It reopens exactly the selected private record and original.bin,
  validates the journal and backup, and returns a private content-free observation
  containing their full snapshots, the current target snapshot, and classification
- `restore_prepared(recovery, observation, *, target_ref, authorize=None,
  exclusive_access=False)` only accepts `prepared_candidate_observed` from a
  version-2 prepared record. Two distinct `restore_prepared` approvals bind
  `digest({'recovery_digest': digest(recovery), 'observation': observation})`.
  Prior apply approval cannot authorize this operation. Receipt, backup, batch,
  parent, current target and stage are rechecked after approval and before commit
- Existing v1 applied receipts retain strict full-snapshot rollback admission;
  new v2 applied receipts additionally validate their staging witness. Ordinary
  rollback and prepared restoration both persist a separate immutable
  `restore-<32 lowercase hex>.prepared.json` before the restoration rename, and
  write `rollback-<same id>.json` only after readback. The restore witness is
  created after the final approval, preserving cancellation without new journals
- Post-write exceptions remain failures. Stable error, batch ID, restore-attempt
  ID when available, and a separate cleanup code survive interruption or cleanup
  failure. No success is returned merely because original bytes are now present

Read-only classifications are `original_observed`, `applied_observed`,
`legacy_identity_unproven`, `restore_not_committed`,
`restored_candidate_observed`, and `conflict`. Only
`prepared_candidate_observed` permits the new separately approved restore.
Observation of already restored bytes does not rewrite them or manufacture the
missing historical completion record. The complete selected restore witness
remains available for inspection when its completion journal fails.

## Identity, metadata and boundedness

Content equality does not establish identity. A same-content foreign inode,
changed parent, altered receipt/backup identity, changed observed ctime, or foreign
stage is rejected. A foreign stage is retained rather than removed by filename.
Successful rename no longer triggers an unnecessary unlink of the former stage
pathname; a later unrelated file at that name is preserved.

Rename itself can change ctime. Initial staged-candidate recognition therefore
compares every retained snapshot field except ctime, then binds the entire newly
observed target snapshot, including ctime, to the fresh restoration approvals.
This is an observation followed by a new scoped action, not proof of uninterrupted
historical ownership. Host-enforced writer exclusion and trusted private evidence
remain mandatory. No portable inode witness can prove absence of arbitrary
interference, inode reuse or in-place ABA edits across an unobserved interval.

Target and original backup reads remain limited to 4 MiB. Private journals have
the separately bounded MAX_DOCUMENT ceiling because their base64 proposal can
exceed 4 MiB. A full 4 MiB proposal is tested end-to-end through reconciliation and
restoration. No public JSON shape accepts arbitrary code, path expansion or
unbounded nested evidence. These APIs preserve the existing single-link regular
file, executing owner/group, mode and no-xattr restrictions. They do not claim
preservation of original inode/timestamps or metadata classes the old writer
refuses.

## Validation status

The initial focused run passed 36 new synthetic recovery tests, existing 42
transaction tests and existing 20 recovery CLI tests. New cases include independent
child-process exits before commit, immediately after rename and before the applied
journal; target-directory fsync failure; both restoration journal gaps; legacy
admission; source/backup/batch tampering and same-bytes inode swaps; snapshot-bound
authorization/cancellation; foreign staging retention; descriptor cleanup errors;
and maximum-size journal loading. All mutations are in dedicated temporary trees.

The later focused run passed 38/38 tests. Independent review also reproduced a
long-path gap where apply could create a journal that the recovery path API could
not reopen. Apply and restoration now reserve the longest generated record path
before authorization/new writes. A real Linux temporary-tree regression covers
the maximum supported 4,096-character generated journal path end-to-end, and an
over-budget regression confirms there is no authorization or target mutation.
The frozen core source SHA-256 at this checkpoint is
`ee59d886f36cca3010acdfa104b87e2116c3a33a6e603701fe6e1e7a3e98e8b4`.

A final independent boundary review reproduced a second reopenability problem:
with a 4 MiB proposal and legal long Unicode paths, prepared.json fit the document
ceiling while the larger applied.json did not. The old WIP returned success but
could neither load its applied receipt nor roll back through the public API.
A fresh regression first reproduced that outcome. All journals now use the same
bounded compact JSON encoding as canonical digests, and apply/rollback/restoration
preflight both future applied and restore-prepared envelopes using maximum allowed
snapshot integer widths. Oversized future evidence is rejected before first
approval or batch creation; document/target limits are unchanged. Normal full-size
proposals remain supported. The focused suite then passed 39/39 tests, including
the real descriptor-relative Unicode fixture. The corrected core SHA-256 is
`53c1fa7a3f2e2fff2737ba3dbe96d0dbe748bfdbbed73b2a7d15f05c723190cd`.

The first aggregate run discovered 1,394 tests with 8 skips and 14 failures, all in
the unchanged guard-classification regression because newly introduced recovery
errors needed explicit non-fallback Agent handling. This interim result is retained
rather than represented as a successful full run. The subsequent aggregate discovered 1,399 tests with 8 skips and one failure: a
changed SKILL guidance hash required explicit route-evidence re-review. The new
runtime, recovery and selector cases passed; the evidence gate was not bypassed.
Eight Node lifecycle scenarios, compilation, diff checks and repeated packaging
passed at this runtime checkpoint. The two packages were byte-identical with
SHA-256 `4a876ee224f8a22c88249285ea7872fb44de87ceb4fa5a61135bb175182e8703`.
Final aggregate and independent-review evidence is recorded by the batch owner
separately after the route review.

Process exits and injected I/O failures are not sudden-power-loss tests. fsync
ordering is checked, but storage-cache/filesystem crash durability is not certified.
No Mac/Windows native recovery, real configuration, GUI/service reload, network
routing, Claude contact or user-device acceptance was performed.

Rollback of this code batch is removal of its transaction/API/test changes and
CLI integration, without modifying retained user backup/journal files. Existing
private records must not be silently rewritten or downgraded.

After this bounded-envelope correction, Node's eight synthetic lifecycle cases,
compilation, diff checks and repeated packaging passed again. The final two
packages are byte-identical with SHA-256
`56876940c43f8229846df06902de98bd447b972696e2b46e035088524053dd44`.
The exact final aggregate result and independent clearance are retained with the
batch owner's final evidence; earlier failing runs remain available.

Final post-correction aggregate: 1,400 discovered, 1,392 passed and 8 skipped
in 27.996 seconds on this Linux environment. The core focused suite passed all
39 cases. Independent replays cleared the evidence-tampering, generated-path
and future-document-budget defects at the corrected source hash above. None of
these results substitutes for native-device or sudden-power-loss acceptance.
