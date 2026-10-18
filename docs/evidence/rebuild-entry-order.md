# Original T29 / T57: subscription-first entry and bounded OS intake

Status: independent full-clause review passed for original T29/T57 (L+C) against the twenty-fifth runtime and active guides on 2026-10-18. All eleven frozen candidate dependency pins match this tree. This evidence is ready for integration; formal acceptance remains recorded separately in the ledger. No production runtime change is included.

## Exact original cases

| ID | Original scenario | Original requirement, verbatim | Layer |
|---|---|---|---|
| T29 | 完整新用户首次进入且未给环境 | 第一问订阅阶段，随后系统/目标套餐/账号经历/方案；不直接给安装付款教程，不通问已有权益 | L+C |
| T57 | 订阅阶段后，电脑系统仍未知 | 系统题仅 **Mac/Windows**（另有手机/未知出口）；不把系统题置于已明确的新入口之前，也没有长平台问卷 | L+C |

The authoritative rows are D-SPEC §11 and the identical original tracker rows. Both remained `pending_revalidation` when prepared; the 218 original IDs, conditions and layers are unchanged. No native OS test is part of these literal routing/content clauses. Describing a Mac or Windows fixture is not observing either platform.

## Actual evidence and host boundary

`tests/test_acceptance_entry_order.py` contains seven deterministic regressions. The runtime is the existing `interview_flow.py`; no production feature or framework is added. A trusted host explicitly normalizes user reports into stable question IDs. The library does not parse the proposed natural-language examples or generate model dialogue. Full expected prompt objects and ordered paths are handwritten in the test rather than read from runtime constants.

A fresh state has only synthetic target/account aliases. No OS, subscription, account history, plan, network, payment or route answer has been supplied. The local default is a proposal, not a selected environment. Responses in the full paths are separate explicit synthetic reports, not inferred from the scenario. The chosen plan is a synthetic label, not a current product/catalog assertion. An answer reporting an unregistered account is not a request to register it.

After import, sentinels deny file access, DNS/socket creation and process launch during the tested pure paths. This verifies absence of those callable I/O attempts on these paths, not OS-level isolation. All states keep PC0, blocked G3, no persistence consent and a traffic projection that does not establish environment acceptance. No phone, computer, account, payment page or network is inspected.

`replay.json` retains complete states, exact next-question objects, applicable requirements and assessments for the Mac/Windows paths, phone/unknown/refusal/deferral exits and supplied-fact control. These are actual callable outputs. `proposed-unrun-dialogues.json` is a future exercise design only: no model response was generated or observed for it.

## T29: every clause

1. **Subscription first.** From the empty fact set, the exact first prompt is Q-J01: first subscription (including free-only history), expired/returning, current subscriber or uncertainty. Current subscription remains unknown until a report is supplied. No installation, checkout tutorial or platform question precedes it.
2. **Then system, target plan, account history and route.** Both complete paths proceed through Q-C02, purpose, only the relevant OS detail, Q-C08, Q-C03, Q-C04 and Q-C05, in that order. The target-plan answer is not reused as an old entitlement. First subscription does not establish registration or absence of account incidents; those remain distinct explicit reports.
3. **Route is a decision.** Before Q-C05 is answered, no local/VM/VPS resource branch runs. The fixture explicitly accepts the local proposal, which activates only the selected local branch. Existing source/time and the acceptance basis remain visible; accepting a route grants no action permission.
4. **Relevant remainder, no premature tutorial.** The trace continues through reported network prerequisites, a subsequently selected web payment channel, local dependencies and protection/explanation preference. Every emitted object is one question, not an install/payment command list. The live checkout check Q-W04 remains absent from facts and appears as `requires_contact_gate`; terminal G1 is partial and G2 blocked. A terminal next-question value of null is not permission to proceed.
5. **No universal old-entitlement survey.** The entire no-conflict first-subscription path excludes Q-C07, Q-P02, Q-A06, Q-C11 and Q-J02. No inferred prior paid status, old plan or old channel appears. This does not prohibit legitimate old-billing questions in a different actual-conflict or existing-billing task.
6. **Already supplied facts are reused.** One explicit batch containing journey, OS/version, purpose, target plan, account reports and local choice skips directly to the genuine next gap Q-C09. Reversing batch order produces the same complete state; values/source/time remain reported and unchanged. Thus the normal order does not become a rigid requirement to re-ask known facts.

The no-tutorial clause is evaluated jointly: actual prompt outputs contain only the bounded interview, and the operative instructions below require interviewing and conditional planning before installation/payment. This is not a claim that every possible model continuation has been observed.

## T57: every clause

1. **Short Mac/Windows question.** Once the subscription stage is explicitly supplied and OS is missing, the next full object contains exactly `这次用 Mac 还是 Windows？`, with unknown/decline/defer outcomes. It does not enumerate a long list of desktop systems or ask language/timezone/version questions together.
2. **Correct entry ordering.** With no facts, Q-J01 comes first. If OS was supplied before the subscription stage, Q-J01 is still next; supplying the stage then skips the already known OS question. If both stage and OS are known, the batch control likewise skips both. OS knowledge never establishes payment status.
3. **Only relevant detail.** A Mac reply activates only Q-OS03; a Windows reply activates only Q-OS02. Neither activates unrelated language, timezone, management or Windows-10 maintenance questions without its separate context. The full paths demonstrate that the single version/Edition follow-up does not expand into the complete platform registry.
4. **Unknown/refusal/deferral exits.** These remain distinct empty fact states with the exact unresolved OS reason. Q-C02 is not re-asked, no desktop is guessed, no OS-specific branch activates and G2 remains conditional/blocked. The host may give bounded guidance; it cannot equate a missing OS with consent or readiness.
5. **Phone-only exit.** A normalized `mobile_only` report activates the single Q-OS12 limited-common-guidance versus voluntary VM/VPS comparison question. The explicit fixture chooses limited common guidance; no desktop OS is fabricated, no migration is selected and the local proposal stays unconfirmed. This is a routing exit, not phone/native support acceptance.

`applicable_questions` intentionally returns internal branch requirements to the host. It is not a user-facing form. The actual next-question API and the active presentation instructions below are the relevant no-long-questionnaire evidence.

## Substantive active-guidance review

This review reads the operative sentences in their surrounding procedures, not just matching IDs or keywords.

- **D-SPEC §6.1 and §6.5:** first establish subscription journey, then Mac/Windows, purpose/desired plan, account history and route. Every relevant prerequisite needs an answer or visible gap before personalized implementation. The requirement is coverage without presenting the whole library at once
- **D-SPEC §6.3–6.4:** reuse current explicit facts with their target/time; absorb multiple facts at once. A sandbox's Linux is not the user's OS. Unknown answers get bounded assistance/exit, rather than synonym loops or inferred facts. Plan selection, host permissions and payment authorization remain separate
- **D-SPEC §6.6:** the actual first prompt distinguishes first/returning/current subscription and does not ask whether everyone wants a subscription. Known journey/task is reused. The following system question is Mac or Windows; Windows version/Edition and Mac version are limited follow-ups, and architecture is conditional on real compatibility needs. Language/timezone are not default changes
- **SKILL “开始方式” and “首问示例”:** the first missing normal business question is subscription stage; explicit facts skip it. Each turn uses one principal decision with a few related facts at most. The entire registry is not shown. Local remains a recommendation until accepted; expertise and owned assets cannot select the environment or establish paid status
- **Intake “Scheduling”, first two paragraphs:** read the existing task, absorb all useful fields, skip known/not-applicable facts, use one focused clarification and permit unknown, decline, pause or a limited plan. The stated normal order is Q-J01, OS/purpose/target plan, history/route, relevant network/payment and protection. Urgent incidents can preempt this normal nonurgent scenario
- **Intake journey and target-plan paragraphs:** first/returning reports establish reported absence only; Q-C08 is the desired plan, not historical entitlement. Q-P02/A6 are relevant-existing-billing or actual-conflict conditionals. Unknown desired-plan identity cannot be guessed. These clauses support the negative history controls without suppressing necessary current prerequisites
- **Intake Core/OS registry:** Q-C02 is Mac/Windows after journey, Q-OS01 is its alias, Q-OS02/03 provide only pertinent platform detail, Q-OS12 is the out-of-scope/mobile exit. Separate issue/context predicates activate language, time and maintenance follow-ups. The test checks the actual resulting applicable set, not just those descriptions
- **Intake fact states and gates:** unknown, declined and other unresolved states remain visible; never infer residence, paid status, eligibility or authority. G1 covers applicable questions; G2 is conditional when facts are missing; G3 requires a specific action and independent authority. Ordinary interview completion does not establish PC-G1/PC-G2
- **Routes R-LOCAL and M01:** native desktop scope is Mac/Windows; mobile-only and unsupported desktops get clearly limited general guidance or an optional choice, without a forced migration. The introductory choice is short; a user need not pass a terminology exam. Only the selected route is expanded
- **Accounts PC0 and payment handoff:** permitted pre-contact reports are device/store/payment categories. Actual target App/checkout, amounts, current terms and sensitive input belong to separately approved later stages. Missing information does not justify buying cards, opening accounts or running purchase experiments
- **Contact-and-safety phase and permission boundaries:** question answers and plan acceptance do not authorize device reads, target-service contact, login, installation or payment. Denial/unknown capability stops dependent operations. No tool call is justified solely by a scalar prompt or a completed questionnaire

These instructions supply the presentation and domain-reasoning portions of the original C layer. The callable library supplies deterministic scheduling/fact/gate evidence. Neither part is described as an unrestricted natural-language implementation or native validation.

## Results and reproduction

Seven candidate tests passed with zero skips. A second subprocess under C locale, `PYTHONUTF8=0`, disabled locale coercion and cp1252 standard I/O also passed all seven. With the same restricted default locale but explicit UTF-8 standard I/O, the full replay equals the ordinary/repeated replay byte-for-byte. Test source parses using Python 3.10 grammar and uses no Python 3.11 `TestCase.enterContext`; it performs no text-file fixture reads. Authoring/evidence text reads and writes explicitly select UTF-8.

Supporting current-tree suites passed: 172 interview tests, 15 intake reconstruction tests and 13 intake-basics tests, zero skips. Counts supplement the complete clause mapping; they are not acceptance by themselves. Exact commands, environment overrides, interpreter version and logs are retained in `validation.json`. These are cloud compatibility checks, not native Windows or an actual Python 3.10 interpreter run.

From an integrated repository root:

```sh
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_entry_order.py -v
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_entry_order.py --replay > entry-order-replay.json
```

For the external candidate, set `GUARDIAN_AUDIT_ROOT` to the checkout and run this candidate's test path. On PowerShell, set `$env:PYTHONIOENCODING='utf-8'` and `$env:PYTHONDONTWRITEBYTECODE='1'` before running Python; preserve UTF-8 if shell redirection re-encodes output. The retained cloud validation wrapper captures subprocess output as bytes, avoiding shell re-encoding. Artifact destinations are operator-selected.

Replay SHA-256: `acd4eb95f022fa61aa96d1df95262c7c4dadcaf754231fae5c0cae9b35022afc`.

## Review and scope limits

The candidate author prepared the tests and reviewed guidance. An independent reviewer checked every original T29/T57 clause, exact callable outputs, substantive active instructions and the normalized-host boundary against the twenty-fifth tree; no blocking defect was found. The independent rerun passed all seven candidate tests and the 172/15/13 supporting suites with zero skips. Forced cp1252 standard I/O under an ASCII default locale passed, explicit UTF-8 replays matched the frozen bytes, and Python 3.10 grammar/known-API checks passed. A further run without the Python 3.11 TestCase context helpers also passed; this is not a Python 3.10 interpreter or native-platform execution claim. Neither native platform behavior, account registration, current catalog/eligibility, actual purchase nor any unobserved model response is accepted by this evidence. T36/T38 retain their missing actual host-response evidence; known negative facts must not be changed into unknown just to obtain a coverage block. Later-queue findings are separate and are not acceptance changes in this candidate.

## Exact dependency pins

SHA-256 pins bind the original specification, relevant implementation, operative guidance and supporting regressions. Aggregate tracker/ledger pages are deliberately excluded. The external receipt pins this page to avoid a self-reference.

| Dependency | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/scripts/interview_flow.py` | `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/intake.md` | `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `tests/test_interview_flow.py` | `7140e70b88e4cd3099d2fa725b3b20269de511be90d4dd020154d2db3e5e0965` |
| `tests/test_acceptance_intake_rebuild.py` | `e26a26ee3b3d0ba93270787f8dbd8022ed11adb2fbbb0f1229df8f1aef57245a` |
| `tests/test_acceptance_intake_basics.py` | `6645ba02aa87dca93c9dfa2a3e97c35eae3fb63e75aa3374990cb51d4092a15d` |
| Candidate `tests/test_acceptance_entry_order.py` | `dddec93b13acd22cb94b86cebcad7228e88a2dc1addae6f4b55fac9fc51df5d5` |


## Twenty-ninth subscription-repair preservation review (2026-10-18)

A separate read-only reviewer re-read every original clause on this page and the changed active intake/accounts guidance against the frozen integrated source. Empty entry remains subscription-first, with the same short Mac/Windows question and only pertinent detail. The new explicitly scoped old-bill/current-plan paths do not add a generic entitlement or platform survey.

The unchanged `test_acceptance_entry_order.py` suite passed all 7 tests with zero skips. Its full current replay was executed twice and is byte-identical to a fresh published twenty-eighth baseline replay; the SHA-256 is `acd4eb95f022fa61aa96d1df95262c7c4dadcaf754231fae5c0cae9b35022afc`. The same suite passed with cp1252 standard I/O under C locale, and explicit-UTF-8 replay bytes also matched. Across the five related intake/entry/mobile/status pages, 47 original tests and eight separately authored delta tests passed. Counts supplement the complete clause/content review, not replace it.

The 218 original requirements and layers are unchanged. The updated current dependency pins on this page follow that actual review and replay. Historical observations remain historical. No generated dialogue, arbitrary-language extraction, real account/store/plan eligibility, native device, network/contact, payment or action-authorization evidence is added; this preservation review accepts no adjacent pending case.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.


## Reported-negative gate clarification preservation review (2026-10-18 UTC)

An independent read-only review compared the frozen thirty-first baseline and thirty-second candidate. The sole active-source change is the explanatory paragraph after G1/G2/G3 in intake.md; runtime, fixtures and original requirements remain byte-identical. T29 remains subscription-first, then the short system/purpose/desired-plan/history/route path, with supplied facts reused and no immediate installation/payment tutorial or universal entitlement survey. T57 still asks only Mac/Windows plus its bounded phone/unknown exits and relevant later detail. Explaining a completed helper projection does not reorder entry, replace unanswered fields, or open contact.

All 7 unchanged original tests on this page passed on both trees, with zero skips. Each complete --replay stdout was freshly produced twice per tree; all four byte streams are identical: SHA-256 `acd4eb95f022fa61aa96d1df95262c7c4dadcaf754231fae5c0cae9b35022afc` (1003659 bytes). Across the twelve affected pages, 105 original tests and 207 supporting interview regressions passed on each tree. These executed comparisons supplement the full original-clause and active-guidance review, not replace it.

The unchanged helper can report G1 complete and G2 pass/conditional_plan_only=false for an answered negative Apple-login fact; that value remains reported and negative. An independent synthetic control reproduced this on both trees while retaining blocked G3, absent persistence authority, separate PC0 contact gaps, and blocking unknown/refused/deferred, pause and unresolved-resume controls. Its identical complete-output SHA-256 is `239fc78643aa3282342393330fc65ed1fc846e0f7bb89748dd9c6e7a1502f932`. This is an interpretation boundary, not a new eligibility engine, runtime fix, purchase-execution defect or counterfactual eligibility inference.

Only this reviewed current intake dependency pin and this page's corresponding ledger evidence hashes may change. The 218 original clauses and layers, all historical source/response packets and their existing pins, and native/contact/action boundaries remain unchanged. This preservation review adds no accepted case, generated response, actual device/store/account result or action permission; future source drift requires a new scoped review.
