# Offline exact-file recovery

## Implemented scope and prerequisites

`skills/claude-guardian/scripts/recovery_cli.py` is a standalone Python-standard-library
entrypoint for POSIX `transactions.py` applied receipts and witness-backed prepared
recovery. It needs neither an Agent,
Claude, a network connection, nor additional packages. Keep the script and its
sibling `transactions.py` available locally **before** a disruption. It does not
install anything, contact services, launch applications, scan for receipts, infer
configuration locations, export data, or create Python import caches.

This implements an independent ordinary-terminal route for the exact-file subset
of ENV-10 / ENG-08 / VAL-07 and ENV-T68/T87. It is **not** full VAL-07 acceptance:
Linux synthetic subprocess tests do not establish macOS user-device recovery,
Windows recovery, system settings, native application behavior, or network recovery.
Windows returns `PLATFORM_UNSUPPORTED`; there is no POSIX fallback on Windows.
Windows transaction receipts are not accepted by this entrypoint.

Supported transactions concern one existing single-link regular file owned by the
executing effective user/group, without xattrs, under the existing engine's bounds.
The CLI additionally requires a private (0700), user-owned immediate receipt
parent and a private user/group-owned receipt. Absolute literal paths are required;
no `~`, variables, globbing, dot components or symlink components are resolved.
On macOS `/tmp` may be a symlink: use the independently verified actual private
location, not an alias. The tool never elevates privileges or relaxes permissions.

## Ordinary-terminal workflow

The following paths are illustrative, not locations to create automatically.
Use the exact private batch and target recorded by your trusted original host.
Never substitute paths copied from an untrusted receipt without independently
checking them. Do not paste receipt contents, original bytes, hashes or local
paths into public reports or chats: backups may contain credentials, and hashes
of low-entropy data may be sensitive.

First inspect only the exact receipt you selected:

```sh
python3 /trusted/guardian/skills/claude-guardian/scripts/recovery_cli.py inspect \
  --receipt /private/recovery/0123456789abcdef0123456789abcdef/applied.json
```

This opens only that receipt, parses bounded JSON and prints an
`unverified_candidate` canonical digest. It does **not** open any target or backup
path embedded in the document. It also allows inspection of a `prepared.json`
record, but does not thereby mark it recoverable. This is sufficient to obtain a
candidate digest without an Agent or hand-editing JSON. A locally computed hash
proves neither authenticity, user permission, correct device nor writer exclusion.
Prefer comparison with a digest retained independently by the original trusted
host. If authenticity or the correct target/backup scope is uncertain, stop and
reconcile with trusted records. Do not edit a receipt to bypass a rejection.

With independently established target reference, exact target path and backup
batch, preview recovery (substitute the full 64-character candidate/retained digest):

```sh
python3 /trusted/guardian/skills/claude-guardian/scripts/recovery_cli.py preview \
  --receipt /private/recovery/0123456789abcdef0123456789abcdef/applied.json \
  --receipt-digest FULL_64_CHARACTER_CANONICAL_DIGEST \
  --target-ref YOUR_ORIGINAL_TARGET_REFERENCE \
  --target-path /private/config/exact-file \
  --backup-batch /private/recovery/0123456789abcdef0123456789abcdef
```

The CLI validates the receipt against all explicit inputs before any embedded
file read. Preview checks the current file's full recorded snapshot, parent
identity and bytes, and the original backup hash. Inspect and preview perform no
writes. Their output is content-free, with escaped paths/labels, and must remain
private. Preview verifies exact file bytes only, not the configuration's meaning
or application effect. Review the original change's vetted semantic difference
and potential application effect using your trusted local records before applying.

For actual recovery, run the same command with `rollback` instead of `preview`
from a real terminal. Piped stdin/output and `--yes` are not supported. The CLI:

1. Displays the exact receipt, digest, target, batch and byte hashes
2. Asks you to type `EXCLUSIVE ACCESS ESTABLISHED` plus the newly displayed
   random challenge only after you have saved work
   and prevented **every** other writer (application, GUI, service, sync, etc.)
   for the entire operation; otherwise cancel
3. Asks you to type `ROLLBACK <full receipt digest>` plus a new random challenge
   for this scope
4. Prepares restoration and requests another fresh approval with a different
   random challenge immediately before
   commit, re-reading and validating the selected receipt before and after each
   approval; changed receipt or target fails closed
5. Restores original bytes and mode, verifies them and retains the backup and a
   private rollback result in the exact batch

These prompts are human workflow confirmation, **not proof** of OS permissions,
authenticity, writer exclusion, application quiescence or device identity. The
invoking person is the trusted host. The CLI cannot stop or discover writers and
does not claim an advisory lock prevents them. POSIX rename is not compare-and-swap;
if you cannot actually establish exclusive access, do not use rollback. A malicious
local caller/terminal controller is outside this boundary, as with the library.

Each prompt discards pending terminal input before displaying its fresh random
challenge. Do not paste answers ahead of time: later prompts require their own
newly displayed challenge. Each prompt defaults to a 60-second deadline; `--approval-timeout 1..300` changes
this. Empty input, any nonmatching response, EOF, Ctrl-C, or deadline expiry stops
approval. The engine may report callback cancellation as `AUTHORIZATION_CANCELLED`.
These are input deadlines, **not hard filesystem I/O timeouts**. Hung storage or
filesystem calls may block; use a trusted local filesystem. No automatic retries
or receipt search occur. There are no default log/export files; the two restoration
verbs create only the engine's staging file and retained private recovery records.

## Selected prepared receipt: observe, then separately authorize

When an apply stopped after replacing the target but before writing `applied.json`,
keep the exact private batch. `inspect` remains selected-receipt-only. The new
`reconcile` verb requires the same independently established scope as `preview`:

```sh
python3 /trusted/guardian/skills/claude-guardian/scripts/recovery_cli.py reconcile \
  --receipt /private/recovery/0123456789abcdef0123456789abcdef/prepared.json \
  --receipt-digest FULL_64_CHARACTER_CANONICAL_RECEIPT_DIGEST \
  --target-ref YOUR_ORIGINAL_TARGET_REFERENCE \
  --target-path /private/config/exact-file \
  --backup-batch /private/recovery/0123456789abcdef0123456789abcdef
```

This performs no writes. It checks the exact selected journal, private original
backup, batch identity, target parent and target snapshot. Its private summary
includes a `classification`, byte hashes, mode and `reconciliation_digest`, without
original/proposed content or base64. A successful observation is not proof of a
successful historical apply. In particular:

- `prepared_candidate_observed`: a version-2 prepared receipt's staged-file
  identity matches the current candidate within the core's documented rename
  limits; this is the sole candidate eligible for separately authorized restoration
- `original_observed`: the original full snapshot is still present; no restoration
  is needed through this path
- `legacy_identity_unproven`: a version-1 prepared receipt cannot establish the
  candidate's identity; restoration through this path is refused
- `applied_observed`: use the existing applied-receipt preview/rollback workflow
- `restore_not_committed` / `restored_candidate_observed`: a selected
  `restore-<32 lowercase hex>.prepared.json` witness describes the observed state
  of a restoration attempt; neither permits replaying that attempt
- `conflict`: preserve the current target and investigate the exact mismatch;
  do not regenerate evidence to force an overwrite

Initial candidate recognition tolerates rename's ctime change while matching the
staged identity and supported content/metadata. It does not prove uninterrupted
history or defeat inode reuse under arbitrary interference. Writer exclusion is
still a real host prerequisite; the complete observation after reconciliation is
then bound and rechecked without that historical ambiguity being called success.

Keep the observed digest in the same private review. To restore an eligible
candidate, use `restore-prepared` with all the exact flags above and
`--reconciliation-digest FULL_64_CHARACTER_RECONCILIATION_DIGEST`. It recomputes
the observation and requires an exact match **before** asking for approval. This
digest is the canonical digest of `{"recovery_digest": <receipt digest>,
"observation": <complete core observation>}`, including receipt/backup/target
snapshots and batch identity; it is not merely a hash of the displayed subset.
It is integrity data, never authorization. No saved approval is loaded.

The real-terminal workflow then asks for `EXCLUSIVE ACCESS ESTABLISHED` and twice
for `RESTORE_PREPARED <full reconciliation digest>`, each with its own fresh random
challenge. The separate operation and complete snapshot binding are rechecked
before and after each approval and immediately before replacement. Receipt,
backup or target changes, including same-content inode substitutions, stop the
operation. A changed digest requires renewed investigation and review; do not
automatically substitute a new digest into a retry. This restores original bytes
and mode only, retains the original prepared receipt, and creates a restoration
witness/result. It never manufactures an `applied.json` receipt or retries apply.

Version-1 applied receipts remain compatible with `preview`/`rollback`. Version-1
prepared receipts remain read-only and cannot be upgraded by editing their schema.
Existing `preview`/`rollback` still reject every prepared receipt. Noncandidate
`restore-prepared` requests return a blocked result without terminal prompts or
target writes. Exit 0 from `reconcile` means observation completed, even when the
classification is `conflict`; it does not imply permission or readiness.

For Agent orchestration, the matching library calls are `reconcile(recovery,
receipt_path=..., target_ref=..., target_path=..., backup_batch=...)` and
`restore_prepared(recovery, observation, target_ref=..., authorize=...,
exclusive_access=True)`. The trusted host must obtain the actual, current,
specific user authorization and verify real writer exclusion. Its callback must
bind operation `restore_prepared`, the exact operation digest above, and target
on both checks. Arbitrary true callbacks, saved JSON grants, a digest, or terminal
automation are not user authorization. No production native repair adapter is
opened by this API; the ordinary terminal is the independent fallback when the
Agent is unavailable. Prepare and verify that local route before any disruption.

## Failures and crash reconciliation

- A saved receipt is never reusable approval. An expired original plan can still
  recover, but only with a fresh rollback confirmation and matching current state
- Later edits, replaced inodes, parent changes and corrupt backups block recovery;
  do not force overwrite or regenerate snapshots to bypass a conflict
- `prepared.json` requires explicit reconciliation. Only a version-2
  `prepared_candidate_observed` result can enter the separately authorized
  `restore-prepared` path above; legacy/ambiguous/conflicting states stay read-only
- A write-phase failure/cancellation/crash may occur after the target was restored
  but before a result was persisted. A failure status does not promise no mutation.
  Keep the private batch, inspect the exact target locally and reconcile before
  retrying; never infer safety from the absence of a result file
- On a write-phase error, validated opaque `recovery_id` and `attempt_id` may
  identify the retained batch and `restore-<attempt_id>.prepared.json`. A failed
  witness write can leave no such witness; an ID alone is not proof it exists.
  Inspect the exact selected file if retained, then use independently established
  scope for `reconcile`. A `restored_candidate_observed` result is an observation,
  not a retroactive success receipt and not permission to write again
- A fixed `cleanup_code` of `STAGING_RETAINED`, `STAGING_CLEANUP_FAILED` or
  `DESCRIPTOR_CLOSE_FAILED` accompanies the primary error when applicable.
  Retained staging material may contain private bytes; preserve it for scoped
  investigation rather than assuming cleanup completed or automatically deleting it
- Credentials that were revoked, deletions, registry changes, ACLs/xattrs,
  multi-file atomicity and application-effective recovery are outside this scope
- Backups/receipts are never automatically deleted; cleanup requires its own
  explicit approval. Do not send their contents to obtain help

Exit status: 0 for completed inspect/preview/reconcile or successful restoration, 2 for blocked/error or
invalid arguments, 130 for an uncaught terminal interrupt. Errors use stable codes
without raw exception messages or file contents.

## Reproducible evidence

```sh
python -B -m unittest discover -s tests -p test_recovery_cli.py -v
python -B -m unittest discover -s tests -p test_prepared_recovery_cli.py -v
```

Tests generate transactions in a separate producer process inside dedicated
`TemporaryDirectory` roots, then run recovery in another process (including a
PTY for the exact terminal workflow). Coverage includes successful restoration,
no-approval/piped-input rejection, queued-paste rejection, each cancellation point,
prompt timeout,
corrupt receipts/backups, explicit scope mismatch, symlink/hardlink/FIFO/oversize
receipt rejection, no embedded-path reads during inspect, stale target and
same-byte inode replacement, edits during final approval, expired plans,
write failure, and real producer crashes before and after target replacement
with only prepared state retained. The unsupported-Windows gate is a synthetic
branch test, not Windows certification. Actual user configuration is untouched.

The prepared CLI suite additionally exercises explicit read-only reconciliation,
exact operation-digest binding, legacy refusal, two separately approved restore
checks, same-content receipt/backup/target replacement, edits at every prompt,
precommit witness failure, and post-replacement result-journal failure. These
failure injections keep real terminal confirmation intact. The last case verifies
restored bytes despite the error, retains a selected witness, and only observes
it on the next invocation. See `docs/evidence/rebuild-prepared-recovery-cli.md`
for the frozen scope, receipts and source pins.
