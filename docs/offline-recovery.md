# Offline exact-file recovery

## Implemented scope and prerequisites

`skills/claude-guardian/scripts/recovery_cli.py` is a standalone Python-standard-library
entrypoint for POSIX `transactions.py` applied receipts. It needs neither an Agent,
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
or receipt search occur. There are no default log/export files; rollback alone
creates the engine's staging file and retained private result.

## Failures and crash reconciliation

- A saved receipt is never reusable approval. An expired original plan can still
  recover, but only with a fresh rollback confirmation and matching current state
- Later edits, replaced inodes, parent changes and corrupt backups block recovery;
  do not force overwrite or regenerate snapshots to bypass a conflict
- `prepared.json` means **manual reconciliation required**, including a crash
  after replacement but before `applied.json` is written. The tool never guesses
  whether a commit happened and never replays a prepared receipt
- A write-phase failure/cancellation/crash may occur after the target was restored
  but before a result was persisted. A failure status does not promise no mutation.
  Keep the private batch, inspect the exact target locally and reconcile before
  retrying; never infer safety from the absence of a result file
- Credentials that were revoked, deletions, registry changes, ACLs/xattrs,
  multi-file atomicity and application-effective recovery are outside this scope
- Backups/receipts are never automatically deleted; cleanup requires its own
  explicit approval. Do not send their contents to obtain help

Exit status: 0 for successful inspect/preview/restoration, 2 for blocked/error or
invalid arguments, 130 for an uncaught terminal interrupt. Errors use stable codes
without raw exception messages or file contents.

## Reproducible evidence

```sh
python -B -m unittest discover -s tests -p test_recovery_cli.py -v
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
