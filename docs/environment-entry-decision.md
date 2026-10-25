# Environment entry order: product decision, 2026-10-19

Status: candidate integration under regression review. This page records the project owner's new product direction and the implemented entry surfaces below; it is not native device acceptance.

## Required order

Establish the current task, then explicitly choose local, VM or VPS execution. Existing assets and a proposed default are not a choice. Before the choice is current, provide interview, comparison and explanation only: do not inspect the target or start remediation. Subscription-only explanation does not require an environment questionnaire.

After selection, distinguish network resources from the execution location. Collect only necessary enum states and non-identifying aliases: whether resources exist, which path is selected, local proxy entry type, final egress role/protocol, and configuration preparation state. No raw IP, subscription URL, configuration body, password, UUID or token is requested or retained in this projection. The user handles any required sensitive local entry through an appropriate secure path.

No purchase is required for authorized offline inspection after route selection. Unknown resources or direct access remain legitimate states. Imported configuration is not evidence of activation, and a purchased residential exit is not proof of suitability or account safety. A local HTTP/mixed entry and a SOCKS5 upstream exit are separate layers; do not configure Claude Code's HTTP proxy variables with a SOCKS endpoint.

## Profiles and authority

Local and VM routes receive applicable detailed environment checks. VM host and guest declarations and actual bindings remain separate; success on one does not establish the other. VPS currently receives a basic non-intrusive profile. VPS purchase guidance and deployment skills are intentionally deferred to later owner-supplied scope.

Entry eligibility is not authorization. Exact live target bindings, current configuration selection, applicable permissions, precise change review, recovery and the existing contact gates remain necessary. Network probes require their own approved endpoints and scope. Existing recovery obligations must not be silently discarded when the user changes or withdraws a route.

A withdrawn, unknown, declined, stale, conflicting or comparison-only route cannot reuse an earlier confirmed selection. Preserve prior facts with their provenance and invalidate only dependent applicability, bindings and plans. Repeated confirmation of the same unchanged route should remain idempotent.

## Verification obligations

- No target I/O when the route is missing or withdrawn
- Owning a VPS never automatically chooses VPS execution
- Selected local execution with VPS egress remains a local execution route
- No resources, unknown resources and direct selection can retain authorized offline inspection
- No implicit configuration or network-probe approval from a completed questionnaire
- Host/guest and local entry/final exit are not interchangeable
- Sensitive or extra input fields are rejected without echoing their contents
- Historical original specification text and evidence are retained; affected current acceptance conclusions are explicitly re-evaluated

## Candidate entry surfaces and limits

`environment_entry.py` validates a strict, sanitized declaration. A trusted Agent host must assemble that declaration from the user's current explicit choices; the existing interview JSON is not automatically converted into an execution grant. The same declarations are checked again around host callbacks, and retained mutation plans must bind the declaration used when planned.

- `guardian.py check` and `repair_cli.py` accept an explicit `--entry-file`; their current safe file reader is POSIX-only. A reviewed host may supply the dictionary through the documented in-process entry API instead. No Windows command-line file support is implied.
- `inventory_cli.py static-audit` uses the version 2 request envelope with `entry_request`; low-level pure parsers remain data-only helpers.
- `cleanup_cli.py` requires current selection before planning or new quarantine. VPS quarantine is outside the basic non-intrusive profile. Exact retained reconciliation/restoration does not require a new route declaration, but retains its own identity, ownership, conflict and live-approval checks.

Default native adapters still support only their documented platforms and locations. A valid VM/VPS declaration does not create an adapter or prove host/guest identity. Configuration imported into a client is not evidence that the client is using it. A valid entry permits the relevant next review, never actual configuration, network contact, deletion or a safe-account guarantee.

Implementation regression uses synthetic declarations and disposable files only. Original accepted responses and source hashes remain historical evidence; the acceptance tracking files were removed on 2026-10-21 (ADR-010).
