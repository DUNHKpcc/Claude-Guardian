# Original T76 / T84: expired returning subscribers and technical-only subscribers

Independent review date: 2026-10-18. Verdict: the complete original T76 and T84 conditions are supported at their unchanged L+C layers by the fixed-fact replay and substantive content/source review below. This is an acceptance recommendation for parent integration; this reviewer did not edit the shared source, original specification, tracker, or ledger.

The review ran against the integrated twenty-ninth tree. All six implementation-owned files exactly match the frozen repair manifest, including runtime SHA-256 `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e`. It does not treat the repair author's passing tests or receipt as full-case acceptance.

## Exact original clauses and layer meaning

| ID | Original scenario | Original requirement, verbatim | Layer |
|---|---|---|---|
| T76 | 以前订阅过，明确已到期，准备重新订阅 | 进入 returning_subscription；询问目标套餐，不重问是否有有效订阅，旧账单仅相关时处理 | L+C |
| T84 | 已有订阅，只修复网络/清理客户端 | 不问想买什么套餐，不把付款列入本次必过项；客户端兼容性确实依赖套餐时才单独查 | L+C |

These are the authoritative D-SPEC §11 rows. Supporting requirements were read in D-SPEC §3.2, §6.5–6.6, §6.8–6.9, §6.11 and the relevant D.2/D.5/D.8 question definitions, plus D-ENV §18.4–18.10. The existing tracker defines L as pure logic/dialogue/fixture and C as content/source review; it does not require native/external execution for these two rows. Neither layer was weakened or replaced. Q-C13 is a derived implementation identifier, not an inserted original-spec clause. All 218 original rows remain unchanged; original-row digest is `84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`.

## What was actually executed

`test_acceptance_subscription_original.py` is an independent 14-test acceptance candidate, authored without importing the repair-test fixture helpers. It explicitly writes expected ordered question paths and exact key question objects, then exercises the real integrated state APIs. Full state, next question, applicable questions, assessment, and grouped resume prompt are retained in every replay snapshot. The normal replay and its repeat are byte-identical.

The meaningful scenario wording is represented by these synthetic inputs: “以前订阅过，已到期，准备重新订阅”; “先处理旧 Apple 订单退款，再重订已选套餐”; “已有订阅，只查网络”; “已有订阅，只规划客户端清理”; and “这次具体功能 F 是否可用取决于当前套餐 A”. These strings were NOT submitted to a model. The executable inputs are explicit normalized journey/task/dependency fact envelopes shown in the test and replay, not claims that the runtime parses natural language. Every plan, feature, OS, device and account label is synthetic. This review does not assert that any particular commercial feature currently depends on a plan.

Pure-API tests use a fixed clock and post-import sentinels against file opens, socket/DNS calls and subprocess calls. These are callable-path guards, not OS-wide isolation. The separate CLI replay genuinely invokes `interview_cli.py` in 13 subprocess commands against synthetic files under the evidence directory. It performs no native/device action, contact, purchase, refund submission or cleanup.

## T76: complete requirement and bounded exits

1. Explicit returning-after-expiry input records `returning_subscription`, reported absence `none_reported`, source/time, and `payment_intent=resubscribe`. Complete Mac- and Windows-labelled paths ask the desired Q-C08 plan after missing OS/purpose details. Q-J01 is not repeated; Q-J02, existing-task Q-C11, Q-P02, Q-A06 and current-plan Q-C13 remain absent. These are platform labels, not native OS tests.
2. If the desired plan is already supplied, it is reused. Unknown, refused and deferred desired-plan replies stop repeat questions and leave a conditional plan; undecided explicitly adds comparison/budget work rather than an invented selection. Neither state turns expiry into current entitlement.
3. Both complete preparation paths stop before actual web checkout: Q-W04 remains `requires_contact_gate`. No request to inspect a live subscription page is made. Exact serialization preserves facts, and an actual interruption plus unchanged grouped review preserves the selected desired plan and original reported expiry without restarting the subscription questionnaire.
4. An explicitly relevant pending refund/restoration activates the old-order path with `subscription_conflict=false`, retaining both expiry and selected future plan. Old Apple/Google/web channels are independent of the proposed future web channel. A complete old-channel/status/pending-issue report covers Q-A06 without fabricating an A06 fact or requiring a new device, store, card, checkout or deployment survey.
5. A partial old Apple order asks only its missing A06 issue even when the proposed future channel is Google. An explicit negative old-issue answer remains negative and does not revive entitlement. A changed partial non-Apple order stales the prior A06 and receives at most one P02 clarification; incomplete evidence cannot become planning readiness.
6. Unknown/refused/deferred P02 does not reappear disguised as A06. Deferring and resuming the payment branch preserves the original expired state and chosen target. Freshly returning from the old-bill subtask to the same resubscription preparation reuses both. The actual CLI independently demonstrates this same old-Apple-bill → resubscription transition.
7. Negative controls distinguish an actual conflict from mere expiry: a first-time bill task without conflict does not activate old billing, while an explicit conflict can. An expired returning user's relevant old bill works without inventing a conflict. All paths retain PC0, blocked G3, and no persistence or operation authority.

## T84: complete requirement and compatibility exception

1. Complete existing-subscriber network paths on both OS labels and the cleanup-only path contain no desired-plan Q-C08 and no payment-prefix requirements. Both purchase/payment intents are `none`, while current subscription remains `active_reported`; “no purchase this task” is not “no paid subscription”. G2 pass means enough reported information for planning only.
2. Hardware compatibility alone asks Q-L02 and does not ask a plan. A desired Q-C08 plan does not satisfy current entitlement. Only explicit current subscription plus a network/environment/cleanup task plus the host's concrete actual dependency flag activates the separate Q-C13 prompt. Exact prompt, branch, stage, allowed unknown/refusal/defer outcomes and `requires_action_authorization=false` are asserted.
3. Supplying Q-C13 changes only its own account-bound fact envelope. An already-supplied current plan is reused with its original source/time. A reported feature-unavailable description is preserved without being converted into success. Even with the information complete, the output explicitly says `compatibility=not_established` and `unrelated_planning_available=true`. No catalog, live entitlement or ability to use a feature is inferred.
4. Unknown, refused, deferred and not-applicable plan answers are null-valued, do not repeat, and leave the dependency conditional. Unrelated cleanup/network planning remains available. Branch-specific defer/resume works; removing a genuinely irrelevant dependency returns the ordinary planning path. A stop/no-cleanup response, pause or urgent incident takes priority. None opens cleanup authority.
5. First/returning/unknown subscription journeys do not become existing subscribers merely because the dependency flag is set. Q-C13 rejects inferred entitlement, an empty value, target-only `selected_unspecified`, and another account's binding. The flag rejects non-boolean values. No desired-purchase-plan or payment prerequisites are introduced as a workaround.
6. Actual interruptions include retained current-plan facts, even while the dependency is dormant. Unchanged review preserves observation time. Unknown/refused/deferred/changed-target review stops automatic review prompts and leaves planning conditional. A changed plan becomes stale; a single clarification is bounded, historical replay cannot revive it, and a genuine current reply restores only reported information.
7. New task switches clear the relevance flag. Same-account/new-device valid plan reports may be retained, but unresolved reviews keep them stale. New accounts inherit neither the plan nor subscription state. Subscription-stage changes stale the old current plan while retaining its provenance, and the exception becomes inactive. These are lifecycle controls, not external account operations.

## Actual current-plan CLI proof

`replay_original_cli.py` creates an independently constructed, complete old technical fixture, then runs the actual integrated CLI:

- `--input old-technical.json --resume independent-interruption --output pending.json` creates a pending bounded review including Q-C13
- A `--resume-review-file` reporting only changed Q-C13 leaves that fact stale with its old observation time and emits the current-plan clarification
- A standard `--answer-file` containing a genuinely current normalized Q-C13 report records reported state, supplied source, and an ingestion timestamp bounded by the actual subprocess start/end; G2 planning passes, while compatibility stays `not_established`, G3 stays blocked and purchase/payment remain none
- Unknown, refused, deferred and not-applicable CLI answers end automatic repetition without resolving the dependency; a fresh fact cannot clear an unresolved grouped review
- CLI envelopes containing `observed_at` or `current_reply` are rejected atomically with exit 2 and no output state
- Three further commands exercise explicit old-bill context, complete old Apple order, and return to the retained resubscription target

There are 13 actual CLI commands and 12 saved-state inspections. The full argv, output objects, return codes, stderr and execution intervals are in `original-cli-replay.json`. The real CLI does not consume a hidden freshness bypass: its ordinary answer operation already means a new normalized current reply. Hosts must not relabel historical evidence or transport retries as new replies. An ingestion time does not independently prove entitlement, feature compatibility or speaker identity.

## Substantive C content/source review

This is a semantic review of active instructions, not a keyword scan or a count of tests:

1. SKILL “开始方式” requires reuse before asking, explicitly distinguishes first/expired-returning/current subscription, prohibits inferring paid status from expertise, sends explicit cleanup to target/protection work, and retains PC0. It links the live intake and accounts guides where the detailed rule is implemented.
2. Intake Scheduling preserves one decision per turn and bounded unknown/refusal/pause exits. Its journey paragraph makes first/returning absence reported, says Q-C08 is the desired plan, activates P02/A06 only for relevant billing/conflict, and excludes payment questionnaires from pure diagnosis. This supports each normal-path prohibition, not merely the test's chosen values.
3. Intake “已到期用户的相关旧账单（T76）” names the exact expired/selected-future-plan/refund situation. It explicitly normalizes the legacy task as `billing_issue`, preserves `none_reported` provenance and Q-C08, and prohibits fabricating `existing_subscriber` or a contradiction to reach that branch. It identifies missing old-order categories, separates actual old channel from future channel, avoids duplicated A06, bounds incomplete/unknown answers, and returns to the retained resubscription goal.
4. Accounts “Relevant old bills after expiry” repeats the operative distinction at the M03 handoff: a refund explanation does not require a phone, store region, gift card, checkout or deployment questionnaire. The actual refund policy/access/submission is separately scoped; no guarantee or submission is implied by interview readiness. B1 separately establishes first/returning target selection versus existing users' actual technical/billing goals.
5. Intake “仅在实际问题需要时确认当前套餐（T84）” assigns a concrete host obligation to establish actual feature dependence before setting the flag. It does not treat ordinary cleanup/network tasks, hardware facts, the desired plan, payment channel or the flag alone as entitlement. Its exact short question asks current plan and involved feature, reuses explicit current facts, and never copies Q-C08.
6. That T84 section gives usable unknown/refusal/defer instructions, explicitly preserves conditional dependent advice while unrelated cleanup/network planning continues, and keeps compatibility unestablished pending permitted evidence. A synthetic current-plan label cannot be presented as verified eligibility. The selected-device cleanup section repeats the exception's narrow scope and states it is not a prerequisite to unrelated cleanup.
7. Intake and `docs/interview-resume.md` distinguish current replies from historical imports, retain account/source/time binding, require fresh relevance for new tasks, and preserve stale obligations across dormant resume and account/device changes. The current-reply option is described as trusted-host classification, not freshness proof, identity verification or permission. Actual CLI proof above checks the normal route, rather than assuming the direct API flag proves CLI usability.
8. The fact-state/G1/G2/G3 sections keep coverage, personalized planning and action authority separate; explicit negative/unknown reports are not converted into successful entitlement. Original D-SPEC §6.11 likewise forbids inferred effective subscription and distinguishes desired versus current plan and old versus future channel. The runtime follows that separation.
9. Accounts “PC0 versus checkout”, SKILL step 5 and contact-and-safety prohibit live entitlement inspection, Claude page/app opening, login checks, DNS/docs access or purchases in PC0. Current product rules and prices remain pending until permitted checks. D-ENV §18.10 specifically says existing subscribers can diagnose/plan cleanup without pretending it is first-ever contact or restarting Claude. Thus the compatibility exception is an information dependency, not a loophole for service contact.
10. The cited original T76/T84 rows and supporting sections substantively match the live guidance and replay. This review adds neither a live eligibility framework nor a product-plan compatibility claim. The original clauses and L+C layers remain intact.

The C layer establishes that the active host contract supplies the required behavior and usable question/exit instructions. It does not claim to have generated and graded model responses or prove universal future host compliance. No generated dialogue is part of this evidence.

## Results, reproduction, limits and integration

- Independent original-case tests: 14 passed, zero skips
- Fixed-fact replay: 385 full snapshots; repeat byte-identical
- Actual integrated CLI: 13 commands passed their expected success/rejection outcomes; 12 saved-state inspections
- Forced C locale with UTF-8/coercion disabled and cp1252 standard I/O: the same 14 tests passed
- Independently rerun repair regressions on the integrated tree: 35 passed
- Both independent scripts parse with Python 3.10 grammar; actual interpreter was Python 3.12.14. No installed Python 3.10 execution or native Windows claim is made
- Every one of the six integrated repair-owned files matches the frozen candidate manifest. This reviewer did not change source/ledger files or perform contact, settings, cleanup or native actions

From an integrated repository root after copying the candidate test to `tests/test_acceptance_subscription_original.py`:

```sh
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_subscription_original.py -v
PYTHONUTF8=1 PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_subscription_original.py --replay > original-replay.json
```

For the external evidence packet, set `GUARDIAN_AUDIT_ROOT` to the checkout and run the same-named test or `replay_original_cli.py` from the packet. CLI authoring uses explicit UTF-8. The validation receipt retains exact executed commands and paths. Pure replay digest: `104ba54ce67d0a7c09d738dcb9b80aeff8d263a60397c3ca932e1f3fcf084221`. CLI replay digest: `fe56d48980c6eecafe052d53f8289dea158cda84ac6c858d1fd8d8e7a465806c`.

Acceptance covers both complete original L+C clauses within the existing repository's layer definitions. It does not close native/network/write/recovery cases, prove current commercial compatibility, establish entitlement, execute a refund/payment, or manufacture generated prose. Existing accepted-case revalidation and whole-suite pin reconciliation remain separate parent work; this review does not claim the full repository suite is green.

Integration should add this page and its independent test, then update only the reviewed T76/T84 statuses with these evidence references. The older T75/T79 page's statement that T76/T84 were pending was true at that earlier review: preserve it and append a dated pointer to this new full review, rather than rewriting historical observations. Older strict schema-1 consumers may reject populated additive fields; upgrade the reader, never strip unresolved obligations. Rollback should restore the six owned files as a unit and withdraw acceptance tied to their changed semantics.

## Exact dependency pins

Pins bind the reviewed source, runtime and active instructions. Tracker/ledger aggregation is excluded from the invariant dependency table; their original clauses/layers were separately checked. The external receipt pins this page and avoids a self-reference.

| Dependency | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/intake.md` | `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/scripts/interview_flow.py` | `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e` |
| `skills/claude-guardian/scripts/interview_cli.py` | `003b9a31c01395be446e658d0ddac6a898172a9008981a302d7f8d8d5e324a91` |
| `skills/claude-guardian/scripts/guardian.py` | `f15f01a1a26406ff30c523577569d599f662f18f6ad4b1fab0a99d7b2afaddfa` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `docs/interview-resume.md` | `0c8325daad9e5d56093819068001617024c226cd934aca8fd195f2c280210691` |
| `tests/test_interview_subscription_repairs.py` | `6d055244b184d3c96974c3090f7d0fe8b70def3197ca11e7ea6e6e7a01a6022f` |
| `tests/test_acceptance_subscription_original.py` | `adc62f1ed88c122f1c1805c1703297affc1a161f996e57f22f4cf1ff57ac6cf0` |
| External `replay_original_cli.py` | `efd12b563915d4509382bf19a0f925909aa1e992216fd28580d35603976631bc` |


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.


## Reported-negative gate clarification preservation review (2026-10-18 UTC)

An independent read-only review compared the frozen thirty-first baseline and thirty-second candidate. The sole active-source change is the explanatory paragraph after G1/G2/G3 in intake.md; runtime, fixtures and original requirements remain byte-identical. T76 still records returning_subscription and reported expiry, asks or reuses the desired plan, does not re-ask effective subscription, and treats old bills only when actually relevant. T84 still excludes purchase/payment prerequisites from ordinary existing-subscriber network/cleanup tasks and asks account-bound Q-C13 only for an actual concrete plan-dependent feature. A reported negative feature/prerequisite remains a known fact; neither answered coverage nor the dependency flag establishes compatibility or entitlement.

All 14 unchanged original tests on this page passed on both trees, with zero skips. Each complete --replay stdout was freshly produced twice per tree; all four byte streams are identical: SHA-256 `104ba54ce67d0a7c09d738dcb9b80aeff8d263a60397c3ca932e1f3fcf084221` (4651901 bytes). Across the twelve affected pages, 105 original tests and 207 supporting interview regressions passed on each tree. These executed comparisons supplement the full original-clause and active-guidance review, not replace it.

The unchanged helper can report G1 complete and G2 pass/conditional_plan_only=false for an answered negative Apple-login fact; that value remains reported and negative. An independent synthetic control reproduced this on both trees while retaining blocked G3, absent persistence authority, separate PC0 contact gaps, and blocking unknown/refused/deferred, pause and unresolved-resume controls. Its identical complete-output SHA-256 is `239fc78643aa3282342393330fc65ed1fc846e0f7bb89748dd9c6e7a1502f932`. This is an interpretation boundary, not a new eligibility engine, runtime fix, purchase-execution defect or counterfactual eligibility inference.

Only this reviewed current intake dependency pin and this page's corresponding ledger evidence hashes may change. The 218 original clauses and layers, all historical source/response packets and their existing pins, and native/contact/action boundaries remain unchanged. This preservation review adds no accepted case, generated response, actual device/store/account result or action permission; future source drift requires a new scoped review.
