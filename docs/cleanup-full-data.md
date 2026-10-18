# C5 explicit full local application-data cleanup core

Status: callable core implemented and independently reviewed against dedicated POSIX temporary trees. Native application cleanup acceptance remains `not_run`. This document is not an original-case acceptance receipt.

C5 adds a separately selected, recoverable local-data cleanup mode. A trusted host can select all verified Claude-owned application-data roots, including histories, configuration and extension data, then call a real filesystem quarantine and an independently approved restore. The default cleanup policy still protects those categories. This slice supplies a callable POSIX core and actual dedicated temporary-tree tests; native ownership discovery, device/user/namespace binding, process inactivity verification, credential stores, browser site data, binary uninstall and permanent purge require separate adapters or explicit handoff. It does not yet provide end-to-end device cleanup.

## API and authorization

`skills/claude-guardian/scripts/cleanup_transactions.py` exports the following APIs. Standard imports from the installed scripts directory and isolated `importlib` file-path loads are supported; the latter loads the exact sibling `transactions.py` without changing `sys.path`.

- `plan(roots, protected_paths, quarantine_directory, target_ref, *, mode=MODE, host_check=None, max_seconds=30, cancelled=lambda: False)` returns a private immutable `CleanupPlan`
- `quarantine(plan, *, authorize=None, host_check=None, exclusive_access=False, max_seconds=30, cancelled=lambda: False)` returns a private immutable `CleanupReceipt`
- `reconcile(plan, recovery_id, *, host_check=None, max_seconds=30, cancelled=lambda: False)` returns a current, read-only location/content observation
- `restore(receipt, *, authorize=None, host_check=None, exclusive_access=False, max_seconds=30, cancelled=lambda: False)` separately authorizes restoration
- `load_manifest(path, expected_digest, target_ref, *, max_seconds=30, cancelled=lambda: False)` reads one exact private manifest and returns its `CleanupPlan`; expected digest is the previously reviewed `plan.digest()`

`MODE` is `C5-full-local-data`. Each root is an exact dictionary with `root_ref`, canonical absolute `path`, and `data_kind` (`cli_app_data` or `desktop_app_data`). Roots preserve selection order. At least one explicit protected path is required. A device alias, path spelling or `data_kind` does not establish ownership. `host_check(target_ref, scope_digest)` must freshly return `verified_inactive_claude_data` only after the host has bound the actual target/device/user/namespace, established exclusive Claude ownership, checked application inactivity, and excluded shared or unknown data, project source, Codex, credentials, keychain data and browser databases. This contract is a host assertion, not a serialized proof. It runs before recursive inspection and around mutations. Failed or unknown checks stop the operation.

`authorize(operation, digest, target_ref)` must return literal `True` for the user's current exact approval: `quarantine` binds the complete plan; `restore_cleanup` binds the current receipt. The host must present exact private paths, scope, consequences and recovery location before obtaining approval. Public previews deliberately omit those private details. `exclusive_access=True` asserts that the host holds its external writer exclusion for the entire call; it is not OS isolation or a lock implementation. Callbacks can reject at later boundaries. Approval for cleanup never authorizes purge, keychain work or an unrelated restore.

## Scope and safety

The core validates explicit lexical paths and every existing ancestor without resolving symlinks. It rejects symlinks, hard-linked files, special files, cross-filesystem roots, unsupported owner/group, xattrs and special modes. Selected roots and their immediate parents must be owned by the effective user/group; selected directories and immediate parents cannot be group/world-writable. The existing quarantine directory itself must be owned by that effective user/group. All ancestor components are opened without following links and their identities are pinned; this does not claim control over arbitrary external writers in common ancestors such as `/tmp`. Quarantine must already exist, be mode 0700 and lie outside all selected and protected trees. Existing protected aliases are rejected without hashing their targets. Missing protected paths remain bound to their observed ancestor chain. Observed protected/quarantine inode aliases and duplicate selected inode identities fail before the aliased node is opened or hashed. The host still must exclude namespace/bind-mount sharing that this exact-path inspection cannot establish; no mount, home or external tree discovery is performed. Data-kind labels never grant deletion authority.

Directory/file identities, relative names, sizes, mode, owner/group, link count, timestamps and file SHA-256 hashes are private manifest data. File contents are never serialized. Each root is moved intact into a private same-filesystem batch. A manifest is written before source changes; each rename has a prepared record first, followed by directory flushes, content/identity readback and a completion record. A normal rename changes the root ctime, which is explicitly allowed; descendant changes remain conflicts. All successful returned renames count as moved even if later readback is cancelled; the error stage distinguishes verification from an unknown move outcome.

Multi-root operations are not atomic. `CleanupError` exposes a fixed code, bounded recovery identifier, successful-returned-rename count and stage. Failure may leave a complete or partial batch. Do not infer that an exception means nothing moved. Preserve the private batch; use `reconcile` for current observations and then obtain separate restore approval. A failure while creating the batch or manifest, before any rename, can leave an incomplete empty batch with no loadable manifest; its stage and zero move count report that boundary rather than promising restart recovery from an unwritten record. Once the complete manifest is flushed, source changes can begin. No cleanup callback retries or automatic rollback conceal a primary failure. Restore refuses any existing later target, same-size corruption, changed identity/mode/contents, replaced ancestors or recovery conflicts. Reconciliation records what exists now, not a fabricated historical success. No journals or quarantined data are automatically deleted.

Default budgets are 16 roots, 4096 total entries, 64 MiB total regular-file data, depth 32, and 30 seconds of cooperative checking (maximum 60 seconds). New quarantine plans expire after 600 seconds; recovery does not expire merely because the original plan did. There is no hard OS I/O timeout. Every JSON document is bounded to 4 MiB. Full future manifest, receipt (including both plan and observed inventories) and completion envelopes are reserved before any batch write, so valid entry counts can still be rejected when path lengths make recovery metadata too large. Unknown fields, duplicate JSON keys and malformed direct constructors fail with fixed errors. Cancellation, invalid clocks, backward time and expired cooperative deadlines fail closed, including the exact manifest loader. A synchronous filesystem call itself cannot be forcibly timed out by this library. No claim is made against arbitrary malicious local writers; rename is not a compare-and-swap transaction.

## Design basis and changed product scope

Original D-ENV §10.1–10.6 and D-SPEC §9/M13 require protected default scope, verified ownership, preview, specific authorization, backup/recovery, and honest platform limits. The explicit C5 product decision broadens only the separately selected verified application-data scope; it does not remove default protection or authorize shared/unknown data.

The upstream reference was read only at fixed commit `423473db6b618c7e040f1a5a6879bc83e69e8b3b`: [cleanup skill](https://github.com/suyuan2022/suyuan-skill/blob/423473db6b618c7e040f1a5a6879bc83e69e8b3b/claude-cleanup/SKILL.md), [cleanup script](https://github.com/suyuan2022/suyuan-skill/blob/423473db6b618c7e040f1a5a6879bc83e69e8b3b/claude-cleanup/scripts/claude_cleanup.py). It was not executed or copied. Its backup/cleanup workflow informed the review; this core independently implements strict manifests and recoverable moves. Identifier rotation, keychain deletion, timezone/system setup and simplified confirmation are excluded.

## Private recovery contract

`CleanupPlan` and `CleanupReceipt` are immutable private objects. `private_material()` returns a detached dictionary; `repr()` and exceptions do not contain paths, source contents or metadata. `preview()` exposes only fixed states, counts, action digests and generated recovery identifiers. The identifier and digest are not an authorization token. Known credential-shaped aliases are rejected; this is not a promise to detect arbitrary secrets.

A plan binds the actual computed inventories to the target reference, C5 mode, exact selected roots/data-kind declarations, protected/control roots, scope digest, quarantine identity and ancestor identities. The target reference is an opaque host binding, not evidence that a questionnaire has verified a device or namespace. A host must resolve the binding before returning `HOST_OK`.

The private batch is `<quarantine_directory>/<action_id>/`, mode 0700. Its mode-0600 `manifest.json` contains exactly `schema_version`, `plan`, and `batch_identity`. The schema is `guardian-cleanup-batch/0.1`. Selected roots are placed in `root-0000`, `root-0001`, etc., preserving selection order. Prepared and done records use `move-0000.prepared.json` and `move-0000.done.json`; restore attempts use a new generated attempt identifier. Files and relevant directories are flushed. An fsync error is a failure; storage hardware and arbitrary external writer guarantees are not inferred.

A caller retains the private exact manifest path, reviewed `plan.digest()`, and verified target reference. After a restart it can call `load_manifest`, then `reconcile`, display the new private observation and ask for an independent restore authorization. Reconciliation has no approval callback because it is a scoped read, but still requires the fresh ownership/inactivity check. Restoring an expired original plan is permitted; a new quarantine is not. A restored root is never overwritten on retry, and a partial restore requires a newly observed receipt and new exact authorization. No repair of corrupted manifests or forced overwrite is offered.

The returned receipt is a current filesystem observation, not application-level verification. Its state is `quarantined`, `partial`, or `restored`, with original/quarantined root counts. An original-location observation means the selected root exists and matches the intended inode/content/mode contract; it does not prove historical uninterrupted presence. `permanent_purge` is always `unsupported` and `native_acceptance` is always `not_run`.

## Callable integration sequence

A trusted host adapter supplies the actual device/user/namespace binding, explicitly verified root selection and protected paths. It can then use this sequence; these host callbacks are integration obligations, not functions implemented by the core:

```python
import cleanup_transactions as cleanup

planned = cleanup.plan(
    selected_verified_roots, protected_paths, existing_private_quarantine,
    verified_target_ref, host_check=host.verify_inactive_owned_scope,
    cancelled=host.cancelled,
)
# Display planned.private_material() privately and obtain the exact approval.
with host.exclusive_cleanup_access():
    receipt = cleanup.quarantine(
        planned, authorize=host.current_exact_approval,
        host_check=host.verify_inactive_owned_scope,
        exclusive_access=True, cancelled=host.cancelled,
    )
# Keep the private manifest and receipt. Restoration is a new approval:
current = cleanup.reconcile(planned, receipt.recovery_id,
                           host_check=host.verify_inactive_owned_scope)
with host.exclusive_cleanup_access():
    restored = cleanup.restore(
        current, authorize=host.current_exact_restore_approval,
        host_check=host.verify_inactive_owned_scope,
        exclusive_access=True, cancelled=host.cancelled,
    )
```

The actual fixture replay `guardian-rebuild-backups/cleanup-eighteenth-replay.py` supplies only synthetic host assertions for test-created data, exercises these real calls and captures full public previews. It performs a normal two-root roundtrip and an injected first-root completion-journal failure followed by restart manifest loading, reconciliation and independent restore. Its JSON receipts retain per-run identifiers/digests, so their whole-file hashes identify one execution, not a deterministic cross-run digest. Dedicated tests also exercise desktop-only roots and preserve empty directories.

## Evidence and remaining limits

Frozen runtime SHA-256: `42b1586eae6d67dbdfa59ffb398a445bd717d3da304bc19c3cd64a6b34ea797e`.

Frozen test SHA-256: `9fadcace33d559c0b02ae1ceb3b1842fe7b9bcf76c08066b89715753b8059a24`.

| Evidence | Observed result |
|---|---|
| `python -m unittest discover -s tests -p test_cleanup_transactions.py -v` | 92 passed; actual disposable directory/file moves and restore |
| Cleanup plus existing transaction/prepared-recovery/clock suites | 185 passed after final source freeze |
| Isolated Agent file-path import | Fresh `python -I -S -B` imports the exact module and sibling support, exposes all five APIs, leaves `sys.path` unchanged and never accesses fixture inputs |
| Python 3.10 AST grammar and current Python bytecode compilation | Both owned Python files passed |
| Independent schema/interrupt probes | 78 top-level and 720 nested malformed-document cases; eight before/after rename `OSError`/`KeyboardInterrupt` cases; large-Unicode manifest rejection before writes |
| Original and fixed regressions | Initial 55/57 run exposed protected symlink aliases and post-rename move-count reporting. Later malformed protected-path constructors, recovery envelope sizing and invalid clocks were corrected and permanently tested |
| Initial composed eighteenth aggregate | 1645 discovered, eight skipped; five failing underlying-pin subtests in one ledger-integrity method, all for concurrently changed interview files. No other failure was reported. Parent integration must re-review and refresh those pins before a green aggregate claim |
| Native device/application cleanup | `not_run`; no actual user-data cleanup, uninstall, process kill, credential operation, browser database operation, network request or engine contact |

Retained logs and receipts use `guardian-rebuild-backups/cleanup-eighteenth-*`. The first tested source snapshot and initial failures remain retained separately. The runtime borrows only existing descriptor-safe filesystem helpers from `transactions.py`; that module is unchanged by this subset.

This slice is useful callable execution for a verified selection, rather than only a displayed cleanup offer. It does not certify native root discovery, closed application state, complete removal of every local identity, credential/site-data deletion, installation removal, account reset, cross-platform acceptance or end-to-end full cleanup. Those require separately reviewed adapters and their own permissions. The explicit C5 product extension does not retroactively change any original acceptance condition or ledger status.
