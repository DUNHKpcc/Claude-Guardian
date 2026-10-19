# Original T75 / T79: explanation depth and subscription status are independent

Status: independently reviewed for both complete original T75/T79 L+C clauses against the twenty-sixth checkout. All runtime, active-guide and source pins remain identical to the frozen twenty-fourth candidate. The six regressions, full replay, substantive C review and supporting checks passed. This isolated review did not edit the repository or acceptance ledger.

## Exact original clauses

| ID | Original scenario | Original requirement, verbatim | Layer |
|---|---|---|---|
| T75 | 技术老手，长期用免费版，首次准备付费 | 仍是 first_subscription，可采用简洁解释；不能推定已有付费权益 | L+C |
| T79 | 不懂技术但已有付费套餐 | 进入已有订阅任务分支，保留新手讲解深度，不进入首次购买分支 | L+C |

D-SPEC §11 contains the authoritative rows. Original §3 and §6 make explanation depth, subscription journey, route and payment choice independent; §D.10 explicitly describes the expert/free-only/first-paid case. Both rows remained pending when prepared. The original 218 IDs, conditions and layers are unchanged.

## What was actually executed

`tests/test_acceptance_experience_status.py` has six regressions and an optional full JSON replay. A trusted host supplies explicit normalized synthetic facts to the existing `interview_flow.py` APIs. The test supplies both the reported journey and the requested explanation preference; it does not infer paid status from skill. Its exact synthetic utterances are retained for transparency:

- T75: “我很熟悉技术，长期只用免费版，从未付费订阅。这次是第一次准备付费，说明尽量简短。”
- T79: “我不懂技术，已经有付费套餐。请一步一步讲。”
- Expertise-only control: “我很熟悉技术，说明尽量简短。”

These texts were **not submitted to a model**. The actual executable inputs are the separately visible normalized fact envelopes. The runtime is not a natural-language parser or explanation renderer. The original L layer is exercised through actual state/question/gate outputs; the C layer is evaluated by the substantive instruction review below. No deterministic model-response claim is made.

The initial reports contain only Q-J01 and Q-C10, or Q-C10 alone in the negative control. Later OS, purpose, registration, plan, route, network and payment facts are separate explicit fixture replies, not deductions from expertise, free use or a paid subscription. A paid subscription does not by itself prove current login or platform eligibility. All plan/region/device labels are synthetic and make no current catalog or actual device claim.

Every expected prompt object and ordered path is handwritten in the regression. Full actual state, next question, applicable questions and assessment are retained throughout Mac- and Windows-labelled paths, an already-supplied-task path and the negative/billing controls. Labels do not mean either platform was inspected. After module imports, sentinels prohibit file, DNS/socket and process calls in the pure replay; this is a callable-path boundary, not OS-level isolation.

## T75: full original condition

1. The exact explicit “never paid, first paid preparation” report becomes `first_subscription`; the separate concise preference becomes Q-C10=`expert_difference_checklist`. Initial next question is Q-C02, without re-asking Q-J01 or invoking the ambiguous-experience Q-J02.
2. Through both complete paths, `current_subscription` remains `none_reported` with the original report source/time. This is a reported absence of paid entitlement, not unknown or an observed billing check. `payment_intent` remains `new_subscription`.
3. The trace asks a new desired plan and relevant first-subscription prerequisites. It never activates Q-P02/A6, an existing-user Q-C11 task interview, retired Q-C07, or a VM/VPS branch merely because of expertise. Registration/login state is separately reported; free-use history is not presented as proof of current authentication.
4. The explanation preference's full fact envelope is retained throughout the path and serialization. It is not re-asked, does not weaken qualification/protection questions, and does not grant any permission. The active host instructions explicitly permit concise expert differences/checklists; the scalar scheduler does not render those explanations itself.
5. The web-payment example ends with Q-W04 deferred as `requires_contact_gate`, G1 partial, G2 conditional/blocked and G3 blocked. No purchase or live entitlement check takes place.
6. A separate expertise-only control leaves subscription unknown. Without an ambiguous-experience report, Q-J01 remains next; with that explicitly supplied host context, the exact Q-J02 clarification is next. Attempting to create a first/current subscription fact with state `inferred` is rejected and leaves the original unknown state unchanged. Expertise does not imply either a first purchase or an existing paid plan.

## T79: full original condition

1. The explicit paid-subscription report becomes `existing_subscriber` / `active_reported`, with its source/time. The separate request for beginner guidance becomes Q-C10=`novice_step_by_step`; no new subscription is inferred from unfamiliarity with technology.
2. When the actual task is missing, the next full object is Q-C11, the existing-subscriber renewal/upgrade/environment/problem question. No new-plan or payment requirement is activated before that task is supplied. **The untouched initial state still has the generic `purchase_intent=subscription_preparation` and `payment_intent=unresolved` labels.** The full replay and assertion preserve those bytes: they are not described as a new purchase request, and no payment branch/action follows from them.
3. An explicit environment-only reply then sets both task intents to `none`. Complete Mac/Windows paths retain the novice preference and active-subscription report while omitting Q-C08 and every payment question. The path asks only relevant environment/account reports, route, network and protection. It finishes with G1 complete/G2 pass for planning only; G3 and contact authority remain closed.
4. A second full path supplies the environment task with the opening facts. Q-C11 is skipped rather than forcing another entry decision, and the beginner preference remains unchanged. This demonstrates reuse, not a special first-time-user flow.
5. Renewal and upgrade controls show that novice guidance does not suppress a legitimate existing-user purchase task: explicit task selection retains active subscription, activates relevant Q-P02/current-billing and Q-C08/target-plan requirements, and records `renew` or `upgrade`, never `new_subscription`. These are bounded branch controls, not whole-case acceptance for T76/T77 or executed billing operations.
6. Changing only the explicit depth preference after either complete fixture leaves the route, subscription, all unrelated fact envelopes, applicable questions and complete assessment unchanged. Thus depth is a delivery preference, not a route selector, payment-state classifier or authority shortcut.

## Explanation-depth guidance: substantive C review

The evidence is more than a retained style label. The active instructions assign the host a concrete presentation responsibility and provide content to fulfil it:

1. **SKILL “开始方式”, instruction 2:** reuse supplied facts, ask the first missing subscription question, and explicitly do not treat technical proficiency as paid status. This supports both inverse cases and prevents an expert shortcut from manufacturing entitlement.
2. **SKILL instruction 3 and intake Scheduling:** route selection is independent, while technical skill changes explanation depth only. A concise expert summary cannot silently select VPS, and a beginner is not forced through a first-purchase branch.
3. **Intake Scheduling, first paragraph:** ask one decision per turn, absorb all useful facts, skip known/not-applicable items, clarify once and allow unknown/refusal/pause/limited plans. A novice gets manageable steps rather than the entire technical registry; an expert does not receive repeated basics merely to satisfy a fixed questionnaire.
4. **Intake journey paragraph:** first/returning answers establish only reported absence; current subscribers receive Q-C11 only if the actual task is missing. Q-C08 means the desired plan, and historical billing is task/conflict-dependent. These operative rules provide the subscription side of both clauses, beyond the chosen fixture values.
5. **Intake Core registry Q-C10 and routes M01 final paragraph:** Q-C10 asks for step-by-step guidance versus checklist/commands. The route guide explicitly offers beginner step-by-step cards, familiar-user short tables and expert difference checklists, while keeping safety gates unchanged. This is the exact intended interpretation of the two retained depth preferences.
6. **Routes M01 terminology card:** explanations use concrete distinctions: web runs in a browser, Desktop is an app, Code is a development tool; subscription/API/store balances are different; a local editor may execute remotely. The short initial choice allows a user to accept the local suggestion without a technical examination. This provides usable beginner explanation content rather than simply recording “novice”.
7. **Routes independent operation cards and their usage contract:** only the selected route is expanded, each step has execution location/prerequisites/evidence/permission/recovery, and the published steps are human guidance rather than automatic execution. The host can present a novice's next step or an expert's relevant differences without deleting safeguards or displaying every module.
8. **Accounts A1, first item:** first subscription is compatible with free-use history; account existence is not subscription. This directly supports T75's reported free-only history and prevents an authentication answer from being treated as a paid plan.
9. **Accounts B1:** first/returning users prepare a desired plan, while current subscribers address their actual renewal/upgrade/environment/fault task. A novice's paid status must therefore direct the same existing-user task branch as any other subscriber; simplified explanations do not restart registration or first purchase.
10. **Original D-SPEC §3, §6.4–6.6 and §D.10:** competence affects depth, not route, subscription stage or required safety checks. Experts can supply summaries and receive gap-focused questions; the explicit expert/free-only example remains first subscription with simplified explanation. The literal T79 row retains novice depth even when paid status is already known.
11. **Intake G1/G2/G3 and contact-and-safety:** an expert does not waive necessary permission; a novice does not gain automatic approval through guidance. Planning coverage, contact, login/payment and persistence are separate. No preference field or complete questionnaire opens them.
12. **Accounts PC0 and handoff/stopping rules:** reports about login/payment remain reports until later permitted checks; actual prices, eligibility, target-account correspondence and payment have their own evidence and approval. This prevents both synthetic complete paths from becoming real purchasing instructions.

The C review establishes an existing host instruction contract, not proof of all future model outputs. `proposed-unrun-dialogues.json` retains exact possible dialogue exercises without fabricated responses. If a later review requires actual generated prose, that is additional evidence to collect and independently review, not something these API tests claim to have run.

## Results, reproduction and portability

Six candidate tests passed with zero skips. The same six passed in a subprocess with C locale, UTF-8 mode/coercion disabled and cp1252 standard I/O. Ordinary, repeated and restricted-default-locale/explicit-UTF-8 replays are byte-identical. Test source parses using Python 3.10 grammar and contains no `TestCase.enterContext` or text-file fixture reads. Artifact-authoring text I/O explicitly selects UTF-8.

Supporting current-tree results: 172 interview tests, 15 intake-rebuild tests and 13 intake-basics tests passed, zero skips. Exact commands, environment overrides, interpreter version and logs are retained in `validation.json`. These cloud checks do not claim native Windows or execution under an installed Python 3.10 interpreter.

From the integrated repository root:

```sh
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_experience_status.py -v
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_experience_status.py --replay > experience-status-replay.json
```

For the external candidate, set `GUARDIAN_AUDIT_ROOT` to the source checkout and use the candidate's test path. On PowerShell, set `$env:PYTHONIOENCODING='utf-8'` and `$env:PYTHONDONTWRITEBYTECODE='1'` before Python, preserving UTF-8 if shell redirection re-encodes output. The retained validation wrapper captures subprocess bytes directly. Artifact destinations are chosen by the operator.

## Review boundary and pending adjacent cases

Independent review passed for the entire original T75/T79 clauses at unchanged L+C layers. The substantive host-depth contract and usable beginner/expert content above satisfy the C content/source-review layer; the normalized state paths satisfy the bounded L logic/fixture layer. This does not establish generated prose or universal host behavior. No natural-language parser, generated response, purchase, current entitlement lookup or native platform action is demonstrated.

T76's relevant-old-refund branch remains pending: a returning subscriber's actual billing issue does not inherently create a subscription conflict, and the test must not set a false conflict to force P02/A6. T84's plan-dependent compatibility exception also remains unproven. T36/T38 still require actual host-response evidence; reported negative Apple-login facts must remain negative rather than being changed to unknown. This candidate closes none of those gaps or adds an eligibility framework.

Replay SHA-256: `115d90e32f431ba25fcfc42c1a575df7490f715e97fc8db1569927b3cb71fc90`.

## Exact dependency pins

SHA-256 pins bind the original specification, relevant runtime, active guidance and supporting regressions. All remained identical to the earlier frozen twenty-fourth dependency readback. Aggregate tracker/ledger pages are excluded. The external receipt pins this page rather than creating a self-reference.

| Dependency | SHA-256 |
|---|---|
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/intake.md` | `3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/scripts/interview_flow.py` | `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `tests/test_acceptance_intake_basics.py` | `43826153de254466367fadd3c9f279ef47896a25935de723fbe22b5486ac1bdb` |
| `tests/test_acceptance_intake_rebuild.py` | `d1480db2071fd5429fb63768043c96ca4f8b5b93a2f2b15854c3cbf423cb12eb` |
| `tests/test_interview_flow.py` | `a411fe5a8f809ac6aac91ffc58580379056b2b158a334646b07647c22ced7bbe` |
| Candidate `tests/test_acceptance_experience_status.py` | `65ae3f20f12c8ebe070d1747b8b35d4bf98c7f0fc69a2717536c990c5324ec15` |


## Twenty-ninth subscription-repair preservation review (2026-10-18)

A separate read-only reviewer re-read every original clause on this page and the changed active intake/accounts guidance against the frozen integrated source. Expert free-only history remains first_subscription/none_reported; paid novice status retains the existing-task branch and beginner depth. The documented generic initial intent labels remain visible until the actual task is supplied. C13 requires explicit existing status and a real task dependency; expertise or the flag alone cannot establish entitlement.

The unchanged `test_acceptance_experience_status.py` suite passed all 6 tests with zero skips. Its full current replay was executed twice and is byte-identical to a fresh published twenty-eighth baseline replay; the SHA-256 is `115d90e32f431ba25fcfc42c1a575df7490f715e97fc8db1569927b3cb71fc90`. The same suite passed with cp1252 standard I/O under C locale, and explicit-UTF-8 replay bytes also matched. Across the five related intake/entry/mobile/status pages, 47 original tests and eight separately authored delta tests passed. Counts supplement the complete clause/content review, not replace it.

The 218 original requirements and layers are unchanged. The updated current dependency pins on this page follow that actual review and replay. Historical observations remain historical. No generated dialogue, arbitrary-language extraction, real account/store/plan eligibility, native device, network/contact, payment or action-authorization evidence is added; this preservation review accepts no adjacent pending case.


## Subsequent T76/T84 acceptance (2026-10-18)

The pending statements in the earlier review describe that historical checkpoint.
The frozen twenty-ninth repair now has a separate complete original L+C review
for [T76/T84](rebuild-subscription-original-cases.md), including explicit expired
old bills and the narrowly applicable current-plan question. This does not
retroactively change earlier observations or establish actual commercial
compatibility, entitlement, native behavior or action authority.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.


## Reported-negative gate clarification preservation review (2026-10-18 UTC)

An independent read-only review compared the frozen thirty-first baseline and thirty-second candidate. The sole active-source change is the explanatory paragraph after G1/G2/G3 in intake.md; runtime, fixtures and original requirements remain byte-identical. T75 still treats an explicit expert/free-only/first-paid report as first_subscription with concise explanation and no inferred prior entitlement. T79 still uses the existing-subscriber task branch while preserving novice explanation depth and avoiding first-purchase preparation. The documented initial generic intent labels remain unchanged until the actual task is reported. Answered coverage does not infer eligibility, paid status, route choice or authorization from proficiency.

All 6 unchanged original tests on this page passed on both trees, with zero skips. Each complete --replay stdout was freshly produced twice per tree; all four byte streams are identical: SHA-256 `115d90e32f431ba25fcfc42c1a575df7490f715e97fc8db1569927b3cb71fc90` (1689774 bytes). Across the twelve affected pages, 105 original tests and 207 supporting interview regressions passed on each tree. These executed comparisons supplement the full original-clause and active-guidance review, not replace it.

The unchanged helper can report G1 complete and G2 pass/conditional_plan_only=false for an answered negative Apple-login fact; that value remains reported and negative. An independent synthetic control reproduced this on both trees while retaining blocked G3, absent persistence authority, separate PC0 contact gaps, and blocking unknown/refused/deferred, pause and unresolved-resume controls. Its identical complete-output SHA-256 is `239fc78643aa3282342393330fc65ed1fc846e0f7bb89748dd9c6e7a1502f932`. This is an interpretation boundary, not a new eligibility engine, runtime fix, purchase-execution defect or counterfactual eligibility inference.

Only this reviewed current intake dependency pin and this page's corresponding ledger evidence hashes may change. The 218 original clauses and layers, all historical source/response packets and their existing pins, and native/contact/action boundaries remain unchanged. This preservation review adds no accepted case, generated response, actual device/store/account result or action permission; future source drift requires a new scoped review.


## 2026-10-18 batch33 final-revision3 preservation

This dated review preserves the existing original cases and their verification layers; it does not add T77/T80 acceptance or replace older execution/generation history. The complete original clause was reviewed against the current intake guide, full outputs, and reachable authority/lifecycle boundaries.

- T75 (L+C): 技术老手，长期用免费版，首次准备付费 — 仍是 first_subscription，可采用简洁解释；不能推定已有付费权益
- T79 (L+C): 不懂技术但已有付费套餐 — 进入已有订阅任务分支，保留新手讲解深度，不进入首次购买分支

All complete OS, supplied-task, expertise-only and renew controls equal the published baseline. Only the explicit upgrade control changes (9 full structural differences), preserving novice depth, active-reported current subscription and provenance while asking current plan/channel before target. It does not become a first-purchase branch or verify billing feasibility.

Fresh complete replay: `b539ab28356fdea5c36943de0adec53c33d10d1e6abba954f3340db8bf5a1a84` (1685973 bytes), repeated twice identically. Every full replay also equals the retained revision2 output. Test suite: `tests/test_acceptance_experience_status.py`; full recursive differences are retained, not filtered.

Current compatibility was reviewed against the 635-file revision3 source freeze SHA-256 `6fbbd10dbe6fb993b1bdda0ea09a897a17a3fa4de83e471a420018c186798bac`. The final change since revision2 is public schema definitions only; all 79 production function/class ASTs, intake guide, CLI and five existing adapted tests are unchanged. Actual schema/runtime roundtrip and malformed/nested/generic controls passed independently. Current preservation receipts include 105 page tests, 282 interview tests, 188 other support tests, 226 C/cp1252 tests, 13 actual CLI commands/12 state inspections, 15 complete current-helper calls and the full known-negative control. These are bounded synthetic/offline checks, not new model dialogue, native-device validation, real billing eligibility or action permission.

Retained prior active dependency SHA-256 values (historical review identity; the current table above names the final reviewed bytes):

- Historical `skills/claude-guardian/references/intake.md`: `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71`
- Historical `skills/claude-guardian/scripts/interview_flow.py`: `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e`
- Historical `tests/test_acceptance_intake_basics.py`: `6645ba02aa87dca93c9dfa2a3e97c35eae3fb63e75aa3374990cb51d4092a15d`
- Historical `tests/test_acceptance_intake_rebuild.py`: `e26a26ee3b3d0ba93270787f8dbd8022ed11adb2fbbb0f1229df8f1aef57245a`
- Historical `tests/test_interview_flow.py`: `7140e70b88e4cd3099d2fa725b3b20269de511be90d4dd020154d2db3e5e0965`
- Historical `tests/test_acceptance_experience_status.py`: `f04873668963011820bb20f3ce0f45ce35d5b75cde1d26456dc2e47dfc7b4dc4`

Detailed approved preservation records: [batch33 current-guide/runtime bridge](batch33-subscription-preservation/REVIEW.md). Historical subscription consumed-source/response manifests remain immutable; current compatibility is a separate reviewed record.


### 2026-10-18 revision4 exact-source compatibility

The active dependency rows above identify revision4; prior revision3 review and historical hashes remain in the preceding dated record. The scoped P02 terminal-retention fix preserves a known complement without filling the refused/unknown/deferred gap, re-questioning it, changing provenance, or opening G2/G3. Retained-plan interruption review remains separate. All105 affected page tests pass and all12 complete original-case replays are byte-identical to revision3; complete current helper15-call equality and historical packet18-test integrity also pass. See `batch33-subscription-preservation/preservation-review.md`, its exact freeze/portable receipts and the independent runtime and engineering approval. This is current compatibility evidence, not new model generation or added acceptance; the existing218 clauses/layers and45 accepted statuses are unchanged. Independent source4 runtime and engineering clearance support preservation of the existing45 only; integration application remains separately reviewed and T77/T80 are not newly accepted.
