# Diagnostic-preview tests

Run from the repository root:

    PYTHONDONTWRITEBYTECODE=1 python3 -m unittest discover -s tests -v

These tests are newly authored behavioral tests for the reconstructed preview contract. They do not reproduce or claim the historical 56-case contract suite. They run on Linux using synthetic observations and a clearly labeled mocked native-dispatch test. Neither macOS nor Windows native collection has been validated on a real device here.

Coverage includes subscription-first question routing, incident priority, known-answer reuse, cancellation, authorization and target/namespace gates, closed PC0, offline input validation and byte limits, secret/address/path redaction sentinels, source and evidence distinction, unknown/missing/stale/future facts, port-conflict preview, no automatic modification, stable-snapshot requirement, explicit new-file exports, symlink rejection, CLI smoke tests and saved-check-report ingestion.

`fixtures/proxy-port-conflict.json` is synthetic, dated evidence. After 24 hours the runtime deliberately treats it as stale and suppresses its configuration diff. Behavioral tests refresh timestamps in memory; they never rewrite the fixture or purport to refresh real evidence. `fixtures/interview-first.json` demonstrates resume state. A saved interview report or its nested `state` object can be passed directly to `interview --input`; no state is automatically persisted. Cancelled reports require an explicit fresh state to resume.

Native `check` only reads OS family, kernel/build version and current UTC offset using standard-library APIs. Windows edition, macOS product release, hardware versus process architecture, GUI language, proxy settings, installed clients, processes, browser state and all network effects remain uncollected. This is an initial bounded subset of ENV-01/02, not its completed implementation.

`check --output audit.json` produces a report accepted directly by `analyze --input audit.json --target-ref device-1` and `plan --input audit.json --target-ref device-1`. These follow-up commands still classify supplied evidence as independently unverified. No evidence opens the contact gate.

Only explicitly named local, materialized JSON input files are supported. Do not point the input/output options at cloud placeholder files, network-mounted directories, live application configuration or credential stores. Symlinks and UNC syntax are rejected, but this portable preview cannot conclusively identify all network mounts or enforce kernel-level network isolation. No network client is implemented. Redaction is defense in depth, not a promise that arbitrary pasted secrets can always be recognized; inspect a report before sharing it.
