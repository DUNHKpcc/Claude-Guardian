# T16: interrupted progress, completed purchase and partial cleanup

## Original condition and decision

D-SPEC-v0.1.10 §11 T16: **中断后继续 — 恢复不含秘密的进度，检查环境变化，不重复付款或删除**. The unchanged tracker assigns **L+C**. This candidate supplies a composed offline logic replay and an active guidance review for that entire sentence. It does not add an action ledger, runtime feature, native result or change the original requirement. Independent review and integrated validation are still required before any ledger acceptance.

Related original constraints: D-SPEC §7.4 requires approved non-secret progress, relevant environment/subscription review, retained route and no new purchase recommendation after completion; §9 prohibits credential/payment-secret collection. D-ENV §10/ENV-09 requires protected data and recovery; D12 forbids indiscriminate cleanup. Those sources remain unchanged.

## Public composition and observed controls

`tests/test_acceptance_resume_completion.py` loads the installed script modules against `GUARDIAN_AUDIT_ROOT`. The test inputs are synthetic; existing route fixture supplies inputs only. Assertions are literal invariants, not expected values copied from runtime output. `--replay` emits full before/after interview states, questions, grouped review and assessments; cleanup trace intentionally exposes only counts/status and operation names, never private paths, manifest contents or payloads.

1. Start a first-subscription task with a selected Pro plan and complete VM environment. Assert `none_reported` and `subscription_preparation` before a fresh reported completion. `complete_purchase` changes status to `active_reported`, task to environment, purchase intent to completed and payment intent to none. This records a report; it never pays or verifies provider billing.
2. Pause, refuse unapproved serialization, explicitly serialize a non-secret summary, load it and prove pause remains and all save/export permissions reset. Direct unpause is rejected. Host declares an actual interruption through `resume_interview` with a new event alias.
3. The pending review retains exact facts and VM choice but withholds ordinary questions and blocks G2. Host reports a changed Q-V04. Only that exact environment fact becomes stale; original date and every unrelated fact remain. A current answer refreshes that field. Replaying the review does not re-stale it. Another save/load preserves completion. Every stage retains the subscription record, completed purchase, no payment intent, no payment questions and blocked G3.
4. Unknown, declined, deferred and target-changed reports retain blocked planning even if purchase completion is reported afterward. Completing billing cannot discharge environmental uncertainty.
5. Save/load rejects synthetic API-token, bearer-token and card-number sentinels, and public/unknown export scopes. Pure interview tests have file/socket/process sentinels. This proves the exact clean progress and known sensitive-pattern boundaries, not universal secret recognition. Host must normalize aliases and categories and never place actual credentials or full logs into state.
6. In an isolated POSIX temporary tree, create two explicitly selected synthetic Claude data roots, protected source and a separate content-verified backup. A trusted test host assertion accepts the exact target/scope. Approval callback checks operation, exact current document digest and target. Cancel quarantine after the first rename; the error truthfully reports one moved root and recovery ID.
7. Simulate restart using `load_manifest(path, expected_digest, target_ref)` then `reconcile`. Observe partial state and one quarantined root with no rename. Retrying original quarantine raises before any second rename. Missing restore approval raises without movement. With separate restore approval, restore only the moved root. Repeating stale or completed restore and retrying original quarantine all raise; observed rename total stays exactly two (one quarantine, one restoration). Originals, protected source and independent backup retain exact bytes. Reconcile finally reports restored, native acceptance not_run, permanent purge unsupported.

The deletion assertion is backed by actual filesystem observations and rename counts, not just a non-executing assessment. The original operation cannot be replayed after partial work; after restoration the observed retry fails with `TARGET_CHANGED` before writing because the original plan no longer matches. Static inspection also shows a retained-batch `BATCH_ALREADY_EXISTS` guard; this particular replay does not reach that additional branch. A newly created plan is a different operation and still needs fresh scope/approval; no global once-only guarantee is claimed.

## Host responsibility and authority boundary

These APIs are deliberately separate. The host must identify a genuine interruption, retain its approved task summary and private recovery mapping, report billing completion honestly, use `complete_purchase` rather than fabricate a new purchase task, and reconcile uncertain cleanup outcomes before recovery. It must preserve the exact target and independently known plan digest. A restored serialized state, resume alias, receipt or digest is never approval.

The C5 callbacks in this replay are controlled fixture stand-ins for actual host verification and current user approval; their `True` return does not establish a real user's consent. Production host checks must verify target/user/namespace, ownership, inactivity, exclusions, backup and exclusive access. Restore needs its own current approval. There is no payment executor here: the tested no-repeat purchase control is persistent completed state and exclusion of a second purchase workflow, backed by guidance. Provider-side idempotency, ambiguous remote transaction outcomes and actual checkout reconciliation are not established by this test.

## Actual active guidance review (C)

- `SKILL.md` §CLI: saving only when explicitly requested; genuine interruption uses `--resume` and intake rules. Default CLI does not pay or clean. Callable POSIX core is distinct from default preview and native adapters.
- `references/intake.md`, Scheduling: current task state reused; completed purchase changes current state instead of continuing awaiting-purchase behavior. Existing subscription technical diagnosis has no payment survey.
- `references/intake.md`, Interruption and resume: host starts a real event, retains route/provenance/contact history, asks scoped changes, stales only related fields, does not recover G3/PC permissions. Unknown/refusal preserves conditional planning. Historical imports cannot be relabeled current replies.
- `references/accounts-and-payments.md`, card and gates paragraphs: do not collect card numbers/CVV/full addresses, do not repeatedly charge, actual payment is user-led after current review. Explicit instruction to record post-purchase state to prevent duplicate buying matches the tested completion state.
- `references/incidents-and-integrations.md`, M13: private backup and independent recovery; multi-root interruption may be partial; reconcile actual locations/content before recovery; never overwrite later changes. Its explicit Agent sequence requires fresh scope checks and separately approved restore. K5 says do not repeat payment when resuming. No contradiction instructs replaying prior cleanup.
- `docs/interview-resume.md`: `loads_state` is not the interruption event; repeated review is idempotent; completion does not erase unresolved environmental/target-change obligations. `docs/cleanup-full-data.md`, Private recovery contract, specifies retained private manifest/digest/target, load → reconcile → new approval, no overwrite on retry and native acceptance not_run; this matches the observed replay.

No active text promises all-host automatic detection, arbitrary secret detection, provider transaction deduplication, or native application cleanup certification. These remain explicit limits rather than inferred evidence.

## Reproduction and rollback

Run against the current nineteenth tree:

```sh
GUARDIAN_AUDIT_ROOT=/path/to/Claude-Guardian-nineteenth PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_resume_completion.py --replay
python -B -m unittest discover -s tests -p test_interview_resume.py -v
python -B -m unittest discover -s tests -p test_cleanup_transactions.py -v
```

Candidate: 4 total/4 passed/0 skipped. Existing resume: 33 total/33 passed/0 skipped. Existing C5: 92 total/92 passed/0 skipped. These counts supplement the scenario assertions, not replace them. No native/user-device actions or network occurred. Candidate adds only one test and this evidence page; rollback removes those files and any future T16 acceptance entry together, preserving runtime and private user progress.

## Exact evidence pins

The following files are hashed against the reviewed current nineteenth bytes. Candidate test is the proposed integrated path; changing any pinned byte requires review before acceptance.

| Path | SHA-256 |
| --- | --- |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/scripts/interview_flow.py` | `0eb24c5fc9b356f145b35b792a13444392f23ea634f618df6886b16aa91beaac` |
| `skills/claude-guardian/scripts/cleanup_transactions.py` | `42b1586eae6d67dbdfa59ffb398a445bd717d3da304bc19c3cd64a6b34ea797e` |
| `skills/claude-guardian/scripts/transactions.py` | `53c1fa7a3f2e2fff2737ba3dbe96d0dbe748bfdbbed73b2a7d15f05c723190cd` |
| `skills/claude-guardian/SKILL.md` | `e34047180a0259a6a14e606f583ef0897c2057f5477e7c16f2aefde7af2fd276` |
| `skills/claude-guardian/references/intake.md` | `24fb26e81ec534f3678a5d081cf126ab1526fffb53df84a96c44f1eb928e9d47` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `cf16e85bfbe2a9ea6a2cc51d88b9f82c85eab29248f289c3ae3990c15cda6cb9` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `docs/interview-resume.md` | `2261f306dcbd357544bcf3261c98e4544be3bc0d3324364936501db89e7e7cfd` |
| `tests/fixtures/acceptance-routes-rebuild.json` | `073ad74ba195fd1c72bcab61887f24f1ce5cbeaef6ff6036d9ff76a713154a80` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `tests/test_cleanup_transactions.py` | `6519b87995b16bdc439a1bbad8e0398c315d79e7d5666558b821bf841c65ce06` |
| `docs/cleanup-full-data.md` | `e4688baa07da244413232bffdf767cccb77395567c44f5f2e7b08c1eae1a6c1c` |
| `tests/test_acceptance_resume_completion.py` | `087c811d8ffdf624f28bf83a3b69c3b334532853d640ab069ab079b92da691ba` |

The integration review found a locale-dependent fixture read. It now requests UTF-8 explicitly; no replay assertion or acceptance condition changed.
