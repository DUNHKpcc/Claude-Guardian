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
| `skills/claude-guardian/scripts/interview_flow.py` | `9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25` |
| `skills/claude-guardian/scripts/cleanup_transactions.py` | `42b1586eae6d67dbdfa59ffb398a445bd717d3da304bc19c3cd64a6b34ea797e` |
| `skills/claude-guardian/scripts/transactions.py` | `53c1fa7a3f2e2fff2737ba3dbe96d0dbe748bfdbbed73b2a7d15f05c723190cd` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/intake.md` | `3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `docs/interview-resume.md` | `0c8325daad9e5d56093819068001617024c226cd934aca8fd195f2c280210691` |
| `tests/fixtures/acceptance-routes-rebuild.json` | `073ad74ba195fd1c72bcab61887f24f1ce5cbeaef6ff6036d9ff76a713154a80` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `tests/test_cleanup_transactions.py` | `6519b87995b16bdc439a1bbad8e0398c315d79e7d5666558b821bf841c65ce06` |
| `docs/cleanup-full-data.md` | `e4688baa07da244413232bffdf767cccb77395567c44f5f2e7b08c1eae1a6c1c` |
| `tests/test_acceptance_resume_completion.py` | `9b4ff7bc7c98a5f5874f853c1cd921edf05709ffd48764413364e239b0fd5e41` |

The integration review found a locale-dependent fixture read. It now requests UTF-8 explicitly; no replay assertion or acceptance condition changed.

Minimum-Python CI found that TestCase.enterContext requires Python 3.11. The equivalent ExitStack plus addCleanup(close) supports 3.10 while preserving the same patch lifetime and assertions.


### Twentyninth subscription-repair preservation review (2026-10-18)

The earlier nineteenth-tree description, four-test result and original construction/rollback statements above describe that historical evidence batch. The twentyninth runtime now includes an optional account-bound `purchase_completion` lifecycle record; the historical statement that that earlier batch added no runtime feature must not be read as a description of this later repair.

An independent reviewer read unchanged D-SPEC §6.11, §6.14, §7.4 and original T16, D-ENV §10/D12, the changed intake/accounts/resume guidance and the actual runtime diff. Fresh baseline and candidate runs each passed all four T16 tests, with zero skips. Each full JSON replay was executed twice from its actual checkout. Baseline replay SHA-256 is `1b645facc060f874fd074fa9b1cd739a641665f275345c9d1a53f23b93780e51` (106789 bytes); current replay is `fda7c117962b94894bc5ee779edaf9392efa3c08e83320bf722bd61bb2dcf1d0` (107884 bytes). Both are repeat-stable. Full current states are not byte-identical to baseline: the only five structural additions are `purchase_resume.{saved,resumed,changed,refreshed,reloaded}.state.purchase_completion`, each exactly `{account_alias: resume-account, source: synthetic:reported-completion, observed_at: 2026-10-18T04:00:00Z, observed: false}`. All pre-existing fields, questions, assessments and the observed cleanup trace remain unchanged. Unittest stderr was retained separately; its elapsed-time text is nondeterministic and is not a JSON replay digest.

The record is limited non-secret lifecycle metadata, not a transaction ID, verified billing, entitlement, identity or operation permission. Independent checks establish exact completion replay after later tasks, same-account device changes, explicit later subscription/plan reports and private save/load, plus rejection of older/same-time conflicting receipts and noninheritance on a different account. Dormant retained Q-C13 is included in interruption review; unresolved review cannot be discarded by a new task/device to revive it. Different or later historical imports cannot discharge staleness or renew a spent clarification; a genuinely current host-classified answer retains its real observation time. Completion still cannot discharge unresolved environmental/target review. G3/contact/save permission remain closed. The original partial-cleanup replay still observes one quarantine rename and one separately approved restore, no second deletion, exact protected/backup bytes, and native acceptance not_run. No provider-side idempotency or real-device cleanup claim is added.

This preserves the complete original T16 L+C conclusion within its trusted-host and controlled synthetic POSIX boundaries. Relevant support reruns passed 207 interview, 92 cleanup, 2 portability, 43 workflow-guard and 24 contact-epoch tests; nine independent preservation checks also passed twice with identical complete trace. These totals supplement the clause review and do not accept any additional original case. The current dependency table is bound to the reviewed twentyninth bytes; full commands, both stdout/stderr streams, structural differences and the before/after pin map are retained with the delivery review receipt.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.


## Reported-negative gate clarification preservation review (2026-10-18 UTC)

An independent read-only review compared the frozen thirty-first baseline and thirty-second candidate. The sole active-source change is the explanatory paragraph after G1/G2/G3 in intake.md; runtime, fixtures and original requirements remain byte-identical. T16 still restores only approved non-secret progress, reviews relevant environmental changes, preserves reported purchase completion and does not restart payment preparation. The controlled temporary POSIX partial-cleanup replay still reconciles before separately approved recovery and does not repeat deletion. A reported answer, saved completion record or synthetic PC2 label never restores permission or clears unresolved environmental review; no provider-side payment idempotency or native cleanup guarantee is added.

All 4 unchanged original tests on this page passed on both trees, with zero skips. Each complete --replay stdout was freshly produced twice per tree; all four byte streams are identical: SHA-256 `fda7c117962b94894bc5ee779edaf9392efa3c08e83320bf722bd61bb2dcf1d0` (107884 bytes). Across the twelve affected pages, 105 original tests and 207 supporting interview regressions passed on each tree. These executed comparisons supplement the full original-clause and active-guidance review, not replace it.

The unchanged helper can report G1 complete and G2 pass/conditional_plan_only=false for an answered negative Apple-login fact; that value remains reported and negative. An independent synthetic control reproduced this on both trees while retaining blocked G3, absent persistence authority, separate PC0 contact gaps, and blocking unknown/refused/deferred, pause and unresolved-resume controls. Its identical complete-output SHA-256 is `239fc78643aa3282342393330fc65ed1fc846e0f7bb89748dd9c6e7a1502f932`. This is an interpretation boundary, not a new eligibility engine, runtime fix, purchase-execution defect or counterfactual eligibility inference.

Only this reviewed current intake dependency pin and this page's corresponding ledger evidence hashes may change. The 218 original clauses and layers, all historical source/response packets and their existing pins, and native/contact/action boundaries remain unchanged. This preservation review adds no accepted case, generated response, actual device/store/account result or action permission; future source drift requires a new scoped review.


## 2026-10-18 batch33 final-revision3 preservation

This dated review preserves the existing original cases and their verification layers; it does not add T77/T80 acceptance or replace older execution/generation history. The complete original clause was reviewed against the current intake guide, full outputs, and reachable authority/lifecycle boundaries.

- T16 (L+C): 中断后继续 — 恢复不含秘密的进度，检查环境变化，不重复付款或删除

The complete deterministic replay remains byte-identical to the published baseline, including all state/fact provenance, applicable questions, bounded exits, G1/G2/G3, route, contact and consent fields. Equality is accompanied by full original-clause/current-guide review, not used as a substitute for it.

Fresh complete replay: `fda7c117962b94894bc5ee779edaf9392efa3c08e83320bf722bd61bb2dcf1d0` (107884 bytes), repeated twice identically. Every full replay also equals the retained revision2 output. Test suite: `tests/test_acceptance_resume_completion.py`; full recursive differences are retained, not filtered.

Current compatibility was reviewed against the 635-file revision3 source freeze SHA-256 `6fbbd10dbe6fb993b1bdda0ea09a897a17a3fa4de83e471a420018c186798bac`. The final change since revision2 is public schema definitions only; all 79 production function/class ASTs, intake guide, CLI and five existing adapted tests are unchanged. Actual schema/runtime roundtrip and malformed/nested/generic controls passed independently. Current preservation receipts include 105 page tests, 282 interview tests, 188 other support tests, 226 C/cp1252 tests, 13 actual CLI commands/12 state inspections, 15 complete current-helper calls and the full known-negative control. These are bounded synthetic/offline checks, not new model dialogue, native-device validation, real billing eligibility or action permission.

Retained prior active dependency SHA-256 values (historical review identity; the current table above names the final reviewed bytes):

- Historical `skills/claude-guardian/scripts/interview_flow.py`: `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e`
- Historical `skills/claude-guardian/references/intake.md`: `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71`

Detailed approved preservation records: [batch33 current-guide/runtime bridge](batch33-subscription-preservation/REVIEW.md). Historical subscription consumed-source/response manifests remain immutable; current compatibility is a separate reviewed record.


### 2026-10-18 revision4 exact-source compatibility

The active dependency rows above identify revision4; prior revision3 review and historical hashes remain in the preceding dated record. The scoped P02 terminal-retention fix preserves a known complement without filling the refused/unknown/deferred gap, re-questioning it, changing provenance, or opening G2/G3. Retained-plan interruption review remains separate. All105 affected page tests pass and all12 complete original-case replays are byte-identical to revision3; complete current helper15-call equality and historical packet18-test integrity also pass. See `batch33-subscription-preservation/preservation-review.md`, its exact freeze/portable receipts and the independent runtime and engineering approval. This is current compatibility evidence, not new model generation or added acceptance; the existing218 clauses/layers and45 accepted statuses are unchanged. Independent source4 runtime and engineering clearance support preservation of the existing45 only; integration application remains separately reviewed and T77/T80 are not newly accepted.


## Current runtime preservation review, 2026-10-19

The runtime pin above now identifies the narrow caller-value copy correction. Prior recorded runs and model responses remain historical; they were not regenerated or relabeled. The prior runtime SHA-256 was `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9`; the current SHA-256 is `9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25`. The only runtime change copies incoming fact values so later caller mutations cannot silently alter recorded evidence.

The [exact-transition compatibility review](fact-copy-compatibility/REVIEW.md) documents newly executed side-by-side normalized replays and unchanged full outputs for the existing supported scenarios. Its strict checker reconstructs and verifies the exact historical source for historical checks, and separately checks the live runtime and mandatory fresh replays. This preserves the original case scope; it does not establish model behavior on new prompts, user-device operation, or a resolution of an actual incident. The mutable-caller regression is separately tested as a newly corrected case.
