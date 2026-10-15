# Legacy interview migration (T82 / D.11)

`skills/claude-guardian/scripts/interview_migration.py` is a pure host API. It does
not replace `interview_cli.py` resume handling, execute an action, read files,
contact services, obtain permissions, or save the returned candidate.

## Supported inputs and evidence

Supported formats are the explicit `guardian-interview/0.1` compact object with
`answers` and optional boolean `cancelled`, and the `guardian-report/0.1` interview
wrapper emitted by `guardian.py`. The wrapper's exact required fields and nested
key sets are checked; only its optional `question` field is allowed additionally.
The current repository fixture is `tests/fixtures/interview-first.json`. The
initial producer at commit `60e7461` used the same named answer vocabulary but
misassigned some question IDs. Migration therefore uses named answer fields,
never the wrapper's question ID or inferred text meaning.

Unversioned objects, future versions, arbitrary question-ID dictionaries, current
full interview states, unknown fields, malformed values, and non-interview reports
are rejected. Use `interview_flow.loads_state` for a current full state. Do not
invent a historical full-state schema or rename a version to make it importable.
No automatic CLI migration fallback is installed by this change.

The only compatibility extensions inside compact `answers` are these bounded
D.11 tombstones: `Q-C07`, `account_ownership`, `account_control`, and `Q-C08`.
These keys are accepted solely to discard their historical values. They are not
claims that the compact producer previously emitted them. Unknown synonyms are
rejected instead of heuristically interpreted. Credential screening runs even on
discarded values; output reports field names, never their discarded contents.

## Host API

```python
from interview_migration import migrate_legacy

result = migrate_legacy(
    parsed_private_legacy_object,
    target_alias="device-a", account_alias="account-a", task_id="task-a",
)
if result["status"] == "review_required":
    candidate = result["state"]
    # Review target association and refresh relevant facts with the user.
    # No saving, system action, contact or purchase is authorized here.
```

`blocked` returns no state, a sanitized code, and an actionable next step. The
caller must supply fresh non-identifying aliases; saved target bindings cannot
satisfy this requirement. Aliases label a review candidate, not verified device
identity. Missing bindings, conflicting subscription stages/tasks, malformed data,
and unsafe values cannot produce a partially accepted state.

`review_required` returns a state validated by the current `validate_state`, plus
unknown confidence/binding, discarded field names, and any review-only evidence and bounded host review hints.
All retained answers are `stale`, carry their original format/field source path,
and have `observed_at=None`. Import time is never substituted for observation
time. The compact format contains no trustworthy per-answer provenance or
freshness. Review the existing values rather than starting an empty questionnaire;
use current `record_fact` only after obtaining relevant fresh evidence.

## Semantic and permission boundaries

- `subscription_stage`, `os`, `usage`, explicit named `target_plan`,
  `account_status`, `current_task`, and `route` retain their categorical meaning
  as stale evidence. Phone-only maps to `mobile_only`, not a supported desktop.
- A historical question-ID `Q-C08` answer represents old entitlement, never the
  new purchase target. Only the compact schema's explicit `target_plan` maps to
  new `Q-C08`. No owner/control answer establishes subscription or payment intent.
- Device history stays separately in `review_only`: it cannot safely become the
  current model's account-bound `Q-C03`. No cross-device/account attribution is
  guessed. The host must review this evidence separately before dropping it.
- First/returning subscription plus an existing-plan renew/upgrade task is
  rejected as conflicting, as is current subscription with an unregistered account.
  The host must obtain an explicit correction.
- A chosen VPS/VM/local route survives as a stale preference; no route is confirmed
  by import. `accepted_default`, multi-field natural-language parsing, and current
  full-state migration are outside this compact-format API.
- Subscription status remains unknown, payment intent unresolved, contact PC0,
  all persistence consents false, and G3 blocked. Saved wrapper gates, readiness,
  target bindings, timestamps and privacy flags are ignored as authority.
- A stale `account_status=suspended` emits the review hint
  `RECONFIRM_ACCOUNT_SUSPENSION_BEFORE_INTAKE`. The host must ask whether this
  report still applies to the current account **before presenting the ordinary
  next intake question**. A confirmed current incident enters current incident
  handling. The candidate itself does not assert a current emergency: its incident
  context remains `none`, and the old account answer remains stale. Device-history
  suspension reports do not produce this account-level hint. Hosts must inspect
  `review_hints` alongside the candidate; blindly calling `next_question` first
  would miss this required review handoff.
- Cancellation remains paused. The host must explicitly resume its workflow.
- Secret screening is defense in depth, not proof of universal redaction. Supply
  only sanitized private categorical input. Never publish migration state or
  review-only evidence automatically. Save/export requires fresh scoped consent.

The candidate cannot skip the first required subscription clarification or confirm
its target association through stale imported values. Reverification is still
required; this module does not perform native device/account verification.

## Validation and limits

Run `python -m unittest discover -s tests -p test_interview_migration.py -v`.
Tests cover actual compact input and report output, original swapped question IDs,
retirement semantics, valid-field provenance, conflicts, credentials (including
retired fields), missing binding, unknown schema/shape, stale facts, route and
G2/G3 barriers, canceled inputs, no saving, no clock freshness, input immutability,
and deterministic operation with file/network/process calls blocked.

These are offline unit regressions for part of T82 / D.11 and ENG-10, not claims
of complete M00 coverage, actual UI migration, native verification, or platform
certification. Rollback consists of removing these three new files; no existing
saved state or executable entrypoint is modified.
