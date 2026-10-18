# Observed-contact evidence freshness: scoped reconstruction

2026-10-18 UTC. This addresses the offline stale-evidence subgap of ENV-T81 and
ENV-T89 (D-ENV §18.7–18.8), not their complete original acceptance requirements.
Both cases remain pending in the unchanged original-case ledger. Actual control-gap
handling, real host/network evidence and native operation are not established.

## Reproduced defect

The exact preceding workflow_guard.py bytes had SHA-256
`a22e1fb0db3720acbeceb52789b41cf8f8225ea562ddb9662b6a6f8e62e1f189`.
Synthetic evidence observed at 10, expiring at 100, remained reusable at 20 after
record_observed_contact. A fresh approval reopened PC1, old action facts were
accepted, and an additional incident plus same-binding rebind repeated the defect.
All three reproduced results were allowed=True. Existing 43 workflow tests had
passed because immediate revocation did not test later reopening.

With this patch all three return allowed=False before any approval callback.
The new tests also prove safe recovery with reviewed current evidence at equal
clock timestamps. No actual external service or device was contacted.

## Host contract and compatibility

Evidence adds contact_epoch; Action adds facts_contact_epoch, both default None
and omitted from repr. Existing positional/named calls without incidents retain
their meaning. WorkflowGuard.contact_epoch exposes a read-only in-process marker.
Each observed contact rotates it and revokes scopes. Rebind after an incident and
resume with contact history also rotate it; saved state never restores a marker.

The trusted host captures the current marker when it starts a genuinely new
scoped review of affected control gaps and facts. After that review, it attaches
the captured marker to the new Evidence and Action facts. A later approval must
never relabel old records. Current-epoch evidence still needs matching binding,
stage, native/manual classification, freshness, latest-result consistency and
readiness; actual actions still require appropriate fresh approval.

This is a host assertion, not a credential, cryptographic capability, or proof of
real review. A malicious Python caller is outside the existing trust boundary.
It introduces no inferred incident timestamp, mixed clock domain or arbitrary TTL.
Copies/deserialized markers have different identities and cannot satisfy a live
guard. Snapshot and approval requests remain marker-free. Generic dataclass asdict
has an additive field (None for legacy records); hosts must use an explicit safe
projection rather than export live markers. No existing repository Evidence/Action
serializer or canonical digest consumer was found to require migration.

Only contact evidence/actions require this post-incident identity. Local audit,
planning and separately authorized neutral diagnostics remain usable. Explanations
and conditional Agent guidance do not require a contact permission.

## Regression coverage

24 new tests plus 43 existing workflow tests pass. New cases cover old evidence
with fresh approval, PC1/PC2 incidents, incident-aware rebind/resume, stale action
facts, equal-time recovery, repeated incidents, incident during approval,
cross-instance/fabricated/copied markers, latest failures and tied conflicts,
expiry, cancellation, legacy calls and local/neutral recovery. Twelve time-bound
and 38 inventory-CLI tests also pass. These are deterministic synthetic tests.

Full aggregate: 1,178 tests in 14.406 seconds, 1,170 passed and eight skipped.
Both Node synthetic suites, compilation and whitespace checks passed. Two package
builds matched SHA-256
`1be01bb2ebe08fa589cf43adec74d1f52673a254316708a45879aaba9e368ba3`.
The accepted T09/T19/T20/T21 evidence is unaffected; an added integrity test now
checks all 16 underlying file pins, requiring renewed review when bytes change.

## Reviewed implementation pins and rollback

- workflow_guard.py: `8008ae69a05031f5166d36b165597635d460530fa08d7854e4f0256920630f0a`
- test_workflow_contact_epoch.py: `bbb4010d7d7e74b6ba2f080eae4c853ed0b239f8bf522bea365114c17dfc97fd`

A rollback reverts this library/test addition only; it does not alter user state,
settings or devices. Rolling back restores the demonstrated stale-evidence defect
and must not be interpreted as safe contact admission. No historical lost-code
acceptance claim was reused.
