# C5 callable CLI adapter candidate (2026-10-18)

This isolated candidate adds `cleanup_cli.py`, its tests and a test-only host. It does not change the existing cleanup core, shared eighteenth tree, release manifest or original acceptance ledger. It is not native application cleanup acceptance.

## Actual capability

`main(argv, *, host=None, stdout=None)` dispatches capabilities, validate-scope, plan, quarantine, reconcile and restore. Ordinary script invocation has no host adapter: selected-root planning, mutation and reconciliation stop with `HOST_ADAPTER_UNAVAILABLE`. Structural validation reads only the explicitly selected private operator document. No arbitrary plugin/module import, environment authority or blanket yes/verified/exclusive flag exists.

With an independently reviewed host, this is real filesystem execution: selected active roots move into private recoverable quarantine, and separate current approval permits restoration. The adapter reports retained quarantine records and independent backup as a **fresh host assertion**, never proof supplied by the CLI. Removing all selected active roots does not mean discovering every Claude object, erasing backups or permanently purging storage. `permanent_purge=unsupported` and `native_acceptance=not_run` remain fixed.

The test-only `FixtureHost()` creates its own private temporary tree; it accepts no caller paths. It independently retains exact selected-root/data identities, fixed scope digest and original/backup contents. Changed roots, added unbacked files, outside scope, corrupt backup and protected changes fail. Its assertions establish only this synthetic fixture, with no actual application or competing fixture writer; it is excluded from production packaging and cannot be selected by a command-line switch.

## Contracts and commands

Operator scope JSON (`guardian-cleanup-operator-scope/0.1`, <=64 KiB) has exact fields: schema_version, target_ref, mode, ordered roots, protected_paths, quarantine_directory, backup_ref, host_context_ref. Core limits continue to apply. Binding references require live host lookup; they are not evidence or credentials.

- `plan --scope FILE --plan-output NEW_FILE`: current read/hash approval, live host verification, core inventory, wrapper-envelope capacity reservation and exact private save approval
- `quarantine --plan-file FILE --expected-plan-digest DIGEST`: private plan read, exact wrapper digest, fresh host binding/backup verification, current quarantine approval and host-held writer exclusion
- `reconcile --plan-file FILE --expected-plan-digest DIGEST --receipt-output NEW_FILE`: uses retained complete wrapper plan, the core's on-disk manifest verification and current location observation, then independently approved private receipt save
- `restore --receipt-file FILE --expected-receipt-digest DIGEST`: exact current private wrapper receipt, live verification, separate restore approval and exclusion

The plan-based reconcile path is an intentional smaller adapter surface than the initial proposal's separate manifest-loader flags. Its retained-plan format is designed for process restart with newly re-established host authority and the core's exact batch manifest; no permission survives serialization. The observed tests reload the plan within a single process, so an actual separate-process restart remains unverified. A missing/corrupt wrapper is not repaired by guessing bindings. The underlying core's separately callable load_manifest remains unchanged.

Host interface: `verify(target_ref, core_scope_digest, bindings)` returns HOST_OK only after actual scope/ownership/inactivity/backup checks; `approve(operation, wrapper_or_private_save_review_digest, target_ref, private_review)` returns literal True only for that exact current decision; `exclusive(target_ref, scope_digest, bindings)` holds actual exclusion across the whole mutation; `cancelled()` returns an actual boolean. An Agent can connect a reviewed current conversation-approval bridge; the adapter itself does not manufacture one or require an extra redundant terminal confirmation.

Core callbacks first check the original core digest/operation/target, then map to the full immutable wrapper review digest covering backup/context references. Private save approval additionally binds the exact output path. No raw private review is printed to ordinary stdout; the host must display it in a verified private channel. A host is trusted integration code, not a sandbox against malicious in-process Python. Its verification work itself must be freshly authorized for the exact read/inspection scope; a goal selection is not that authorization. Repeated approve calls revalidate the same still-live exact operation consent; they do not request fabricated blanket approvals or permit a model to substitute True. Revocation and changed scope must immediately deny further steps.

## Safety and recovery

Private input/output is bounded, same-user/group, mode0600 under mode0700 directories, no symlinks/hardlinks/unsupported metadata and no overwrite. Output cannot be in selected, protected or quarantine trees. Output parent identity is rechecked. Persistence checks cancellation/deadline after serialization, immediately before exclusive creation and after readback. A failure after a write attempt reports `private_record_may_exist=true`; it never deletes the record or claims no side effect. Existing descriptor-safe core helpers handle traversal and file snapshots. Cooperative checks use a shared 30-second wrapper budget as well as core checks; synchronous kernel I/O is not forcibly timed out.

Before root mutation, reserve the worst-case future receipt including wrapper overhead, duplicated inventories and widest root ctime/metadata. Core-only capacity is insufficient. Plan/receipt wrappers contain no saved authorization. Cancellation, host failure and invalid input produce fixed public errors. Primary core exceptions retain recovery ID, stage and successful-move count even if exclusion cleanup also fails or suppresses them. A host context failure after a successful mutation is sanitized and reports the actual verified move result, not zero progress. Final deadline/cancellation checks also run after exclusion exit and public projection; expiry preserves the actual completed-move recovery metadata.

The wrapper does not create or verify a real-device independent backup itself. Its host must do so and must refuse unsupported scope. The synthetic adapter verifies its independently retained backup. Scope validation alone never authorizes reads of selected root contents.

## Evidence

True initial failing-first log: `/tmp/guardian-cleanup-cli-proposal/failing-first.log` (module absent). Additional genuine exclusion-exit failure: `exclusion-failing-first.log` (actual move but missing recovery metadata). Independent reviewer counterexamples cover outside fixture roots, incomplete backup coverage, changed root identity and arbitrary host-context exception types; all received corrections and permanent tests.

Current focused command: `python -B -m unittest discover -s tests -p test_cleanup_cli.py -v` (26 tests at final review freeze). Actual disposable-fixture tests cover private plan/quarantine/restart-style retained-plan reconciliation/restore, protected and backup bytes, precise approval digests, denial, no-overwrite, scope aliases, cancellation, fixed private errors, journal failures and exact wrapper encoding boundary. Detached copies of the three runtime modules execute all four operations under `python -I -S -B`, without sys.path changes or optional YAML. This is detached installation testing, not a claim that the unchanged package manifest already includes the new CLI.

Independent review and parent release integration remain required. No original native condition is accepted by this candidate. Actual device/user/namespace binding, Claude root discovery, application inactivity and exclusion need real reviewed host adapters; Windows support is not inferred from POSIX fixtures.
