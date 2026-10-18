# Explicit interview resume review (T24)

Scope: offline host state and CLI, plus linked Agent guidance. This implements a planning obligation for a genuine interruption. It does not detect a closed application, authorize reads/writes, verify native targets, parse natural language, or certify model behavior. Acceptance status is recorded in the rebuild ledger; the project as a whole remains incomplete.

## Boundary and compatibility

- `loads_state` and ordinary CLI `--input` validate/deserialise only. They do not create resume events, refresh observations, or automatically ask a new review each turn. Persistence consent is cleared as before.
- For an actual interruption, the host calls `resume_interview(state, resume_id="resume-a")`, or adds `--resume resume-a` to `--input`. An explicit paused→active transition through `set_context(paused=False)` now fails; callers must use the resume API. A saved state that remains paused stays paused under a plain load.
- The host supplies a fresh non-identifying label for each real interruption. Repeating the current label is an idempotent retry. A completed event (`reviewed` or `not_required`) cannot be reused to clear a newly explicit pause. The label is metadata, not a secret, nonce, proof of user approval, or device credential. The host still has to identify a genuine interruption; a cooperative pure-data API is not an adversarial-host security boundary.
- Pre-feature schema-1 states without `resume_review` remain accepted and retain ordinary behavior. This is an optional schema-1 extension; older readers that reject unknown top-level fields cannot consume a state containing it. Upgrade the reader together with the writer; do not strip review state to make an old reader accept resumed planning. The interim unpublished WIP shapes are not a compatibility format.
- Actual target/account/task changes use existing `begin_task` semantics, which cannot inherit another binding's review. A changed route/task context refreshes the review only for relevant retained facts, not freshly supplied answers. A completed purchase is an ordinary live transition: completed review retires only when no uncovered non-billing retained keys remain. Otherwise its receipt and those obligations remain, with the new task binding but no current-route prompt. Pending/unresolved environmental review survives. Obsolete billing-only uncertainty becomes not_required if old off-route keys still need tracking; its obsolete response metadata is cleared, while original fact provenance stays intact. Known target-change uncertainty survives even an empty environmental scope. Repeating purchase completion cannot discard these retained obligations.

## APIs

`resume_interview(state, *, resume_id)` copies state, clears pause and persistence permission, keeps route, facts, task identity, asked/deferred history, unrelated blockers and contact phase, and snapshots bounded retained topics. It never runs an external action.

`resume_review_prompt(state)` returns a separate `kind="resume_review"` message, not a new Q ID. Its fields are `event_id`, `scope_keys`, full Chinese `prompt`, six `allowed_outcomes`, and `requires_action_authorization=false`. `next_question` is withheld while this review is pending, except for urgent incident triage. A paused or otherwise blocked state does not emit a review prompt. Empty relevant retained scope yields `not_required` without a question or new gate.

`record_resume_review(state, *, resume_id, response, source, changed_keys=(), reported_at=None)` records a normalized current user report. The host must obtain that report; an old saved answer cannot be relabeled as a new reply. Inputs are validated before any returned state or invalidation; caller state is not mutated. Provenance is kept in explicitly saved private state and omitted from assessment/CLI stdout.

| Response | Effect |
|---|---|
| `unchanged` | Mark the review reported-complete; retain all original fact values, sources and observation times. Existing G1 gaps still block G2. No action/contact gate opens. |
| `changed` | Require a nonempty, duplicate-free canonical `changed_keys` subset of the presented scope; mark only those fields stale and reset their clarification budget. Original evidence remains. Ask their normal stable questions as applicable. |
| `unknown`, `declined`, `deferred` | Preserve facts and record unresolved review; G2 stays conditional and no automatic review loop occurs. The user may later volunteer a fresh reply. |
| `target_changed` | Preserve facts but block reuse of that target's plan. Explicitly rebind with `begin_task`, or record a fresh user correction that it is in fact the same target. A retry, route change or purchase completion cannot silently clear this warning. |

Repeating the same response, changed-key set and source for one event returns the retained result without re-staling facts that have since been refreshed. A different answer after an already successful review requires a new event. An unresolved answer may be resolved by an explicit later reply, including correction of a mistaken target-change report. This is a host/user report contract, not automatic proof that the claimed reply occurred.

## Bounded scope and current replies

The review considers stored reusable `reported/observed/inferred/stale/conflict` facts only:

- Common environment: C02, C04, C06, C09 (region/travel, no detailed address), OS02–OS12, N01–N06, Z04 (backup/rescue)
- Only the selected route: L01–L04, V01–V06, or S01–S07; no route branch is presumed from an unaccepted local proposal
- J01/J02 only for current purchase/billing tasks
- Derived C13, when already retained, reviews the account-bound current plan for a concrete client-feature dependency, including dormant conditions; its prompt does not start purchase or payment questions
- Choice C05, target plan C08, explanation depth C10, preservation C12/Z02, permissions Z01/Z03/Z05 and incident history H are not environment-change invalidation targets

Dormant conditional facts in the selected route are explicitly included in the grouped review, so later activation of compatibility/integration/existing-test/OS branches cannot silently reuse omitted old facts. Current-plan dependency activation alone cannot bypass this review. A changed C13 becomes stale with its provenance/time retained; unknown/refused/deferred review keeps only conditional planning. Task changes clear the optional plan_compatibility_needed flag, which the host must explicitly re-establish for the new concrete question. Same-account device changes may retain C13; account changes cannot. Subscription-stage changes and reported purchase completion stale the old plan rather than copying a desired plan into it. A new task or same-account device change cannot discard an unresolved C13 review and revive the old reported plan: C13 is retained as stale. An optional account-bound purchase_completion receipt (source/time/observed, plus account alias) distinguishes an actually processed completion from an ordinary J01 self-report. It survives same-account tasks/devices and private serialization, never a new account, and is absent from old/default states. Exact replay of that receipt preserves subsequent fresh plan evidence and task conditions, even after a new task; older or same-time conflicting receipts fail closed. Ordinary same-time J01 is not a completion retry; historical plan imports cannot clear stale obligations or renew a spent clarification. Existing cleanup/incident/pause and action/contact controls retain priority.

Old off-route facts are tracked as retained, but are not presented or treated as reviewed until their route becomes relevant.

`record_facts` and `record_fact` with `observed_at` omitted mean a new explicit current reply. They may retire that field from the still-retained set used for a later binding change. `record_fact` with a supplied `observed_at` defaults to a timestamped evidence import; only a genuinely current reply may use the optional strict boolean `current_reply=True` while preserving its real observation time. This trusted-host classification is not proof of freshness, target identity or permission, and cannot make a pre-subscription-stage plan current. By default, even an imported Oct 2 observation replacing an Oct 1 observation stays retained across an Oct 18 interruption. Relative timestamp ordering is not proof of a current reply. Current-batch envelopes reject observation timestamps. Rendering, ordinary loads, and resume/review retries cannot retire retained keys or refresh observation times. Re-submitting an answer file is instead an explicit current-reply operation, so hosts must not use it as a transport retry for historical answers. Hosts must not route historical data through a current-reply interface.

## Optional saved record

| Field | Why it exists |
|---|---|
| `event_id` | Identify idempotent retries of one interruption |
| `binding` | Exact task ID, target/account aliases, task type, route and choice basis; prevent transfer to another context |
| `scope_keys` | Snapshot of the grouped topics actually presented for this binding; these alone may be invalidated by `changed` |
| `retained_keys` | Bounded remaining pre-event environment keys, including off-route facts; distinguish retained evidence from new explicit replies during later binding changes. Only explicit current replies retire keys. |
| `status` | Distinguish pending, reviewed, unresolved and empty-scope not_required |
| `response`, `changed_keys` | Preserve the reported outcome and exact invalidation subset |
| `source`, `reported_at` | Separate this current user report's provenance/time from original observation dates |

The runtime validates exact record keys, enums, canonical whitelist membership, duplicates, subset rules, dates, provenance screening and binding equality. JSON schema exposes the shape; runtime cross-field checks remain authoritative. None of these fields is action authority. No extra timestamp or expiration interval is invented.

## CLI examples and failure behavior

Use only an approved private state path; `--output` explicitly requests a new saved file and never overwrites an existing file.

```sh
python skills/claude-guardian/scripts/interview_cli.py --input private-state.json --resume resume-a --output private-pending.json
python skills/claude-guardian/scripts/interview_cli.py --input private-pending.json --resume-review-file current-review.json --answer-file current-answers.json --output private-reviewed.json
```

A normalized `current-review.json` for a VM network change is:

```json
{"resume_id":"resume-a","response":"changed","source":"user:current-turn","changed_keys":["Q-V04"]}
```

`reported_at` is optional timezone-aware ISO report metadata, not authority or freshness proof. The review file accepts only the documented keys. CLI order: load and alias check → optional explicit resume → context → current review → current answers → question/assessment → optional save. This lets a changed field be refreshed in that same current reply, without marking the new answer stale afterward.

With no `--resume`, ordinary saved-state turns keep their previous behavior. Either resume flag requires `--input`; mismatched targets/events, old unpause bypass, malformed envelopes, bad changed-key sets and unsafe provenance use the existing sanitized failure and save no partial state. Cancellation before save uses the existing cancelled result. Review provenance is absent from stdout. `resume_review` appears in output only when the state contains that feature; it is the pending prompt or null when no prompt is due. Existing output failures report whether an already authorized save happened.

## Reproduction and rollback

```sh
python -m unittest discover -s tests -p test_interview_resume.py -v
python -m unittest discover -s tests -p 'test_interview*.py' -v
python -m unittest discover -s tests -p test_acceptance_routes_rebuild.py -v
python tests/test_acceptance_routes_rebuild.py --replay
```

Before this change, complete VM/VPS → pause → save/load → direct unpause produced no review and G2 pass using original facts. The new normative trace rejects direct unpause, preserves the explicit route, asks the exact scoped review with G2 blocked, then handles unchanged and selectively changed replies. The route evidence page pins concrete expected/actual output and reviews active guidance. Tests use synthetic in-memory state and temporary CLI files only; no model, device, VM/VPS deployment or native permission is tested.

Rollback requires restoring the related interview code, schema, CLI and guidance together. Preserve private progress records; an older reader cannot consume the optional record. Do not drop a pending/unresolved review or fabricate fresh facts to evade this incompatibility. Rebuilding the reader-compatible summary needs explicit relevant fact review. Revert refreshed accepted-case evidence hashes together with their exact pinned artifact, or mark those rows pending until re-reviewed.
