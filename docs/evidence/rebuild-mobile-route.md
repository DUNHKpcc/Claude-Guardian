# Original T49 / T83: mobile payment and execution-route separation

Status: independently reviewed on 2026-10-18 against the twenty-fourth working tree, whose 11 pinned dependencies exactly match the frozen twenty-third source. The complete original T49/T83 L+C clauses are covered within the normalized-host API replay plus active-content-review boundary. This review has not promoted either ledger entry. No actual generated host dialogue, native device/account test or purchase acceptance is claimed.

## Exact original clauses

| ID | Original scenario | Original requirement, verbatim | Layer |
|---|---|---|---|
| T49 | 选择 VPS 使用但想以手机内购支付 | 运行环境与付款设备分开，读取对应分支，不强制网页银行卡 | L+C |
| T83 | 首次订阅选择 Apple/Google 内购 | 保留设备/商店/目标账户对应/入口检查；不在 A6/P02/G04 中重新问旧订阅 | L+C |

These rows are unchanged in D-SPEC §11 and the implementation tracker. Both ledger entries were pending when this evidence was prepared. Original L+C concerns routing, relevant checks and guidance. It does not require a real purchase or authorize device/account access. No current plan, price, geographic eligibility or store availability is asserted here.

## Executable contract and truthful scope

`tests/test_acceptance_mobile_route.py` has six regressions and an optional `--replay` output. A trusted host supplies explicit normalized synthetic facts; the library is not a natural-language parser or payment-eligibility engine. Handwritten expected full prompt objects, exact ordered branches and explicit gates are compared against runtime outputs. The replay retains full states, assessments, applicable questions and next prompts for four paths: local/Apple, local/Google, VPS/Apple and VPS/Google.

The synthetic initial facts already establish first subscription, selected route/channel, registered account self-report, selected target-plan category, controller OS and network roles. They are explicit test setup, not facts inferred from one short utterance. The target plan is a synthetic label and never evidence of a currently sold product. Execution host, controller and payment phone have separate non-identifying aliases. Q-N02 records their reported roles; payment-device facts do not rewrite the Code execution route.

Imports occur before test sentinels block file, DNS/socket and process calls. No network, file save, device inspection, installation, login, gift-card redemption or payment occurs during the tested pure paths. Sentinel coverage is a callable test boundary, not OS-level enforcement.

No generated model response is used as test output. Separately retained proposed dialogue exercises are explicitly **unrun**. Their future execution would need its own exact retained inputs/responses and independent content review.

## T49 whole-clause replay

For each Apple and Google choice:

1. The starting route is explicitly VPS, while Q-N02 identifies Code in `workspace-a`, a controller in `controller-a`, and an independent phone alias. Apple A1 or Google G1 later retains that phone's category/availability; S2 retains the separate existing Ubuntu VPS. No remote installation, phone verification or account inspection is performed.
2. Apple receives Q-P07, Q-A01, Q-A02, Q-A03, Q-A10; Google receives Q-P07, Q-G01, Q-G02. These are the selected mobile channel's PC0 prerequisites, not web-card questions.
3. The complete VPS branch follows exactly Q-S01 through Q-S07: workspace versus exit-only, existing/new server and resources, SSH/independent rescue, protected workloads, remote-data/local-dependency fit, costs and workflow/maintenance. Protection and requested explanation depth follow. There is no local/VM detour and no Q-W01–Q-W04 requirement.
4. All intermediate states retain VPS explicit choice, the selected mobile billing channel, first-subscription self-report, blocked G3, PC0 and no persistence permission. Phone, VPS and controller facts remain distinct.
5. A bounded channel-change control changes Apple to Google or vice versa while keeping the chosen VPS and its existing fact envelopes. The new channel's first prerequisite is asked; no web-card fallback appears. Existing Q-N02 is not fabricated into a new phone binding merely from a channel choice: the host must collect any changed layout. This test proves routing separation, not automatic cross-device fact freshness.
6. Serialization/loading preserves the selected route and separate facts without reviving save or action permission.

The remaining actual App/plan-entry and target-account checks stay deferred at PC0. Their absence is visible; a phone declaration does not make the in-app route ready to buy.

## T83 whole-clause replay

The first-subscription paths run for both mobile channels and both local/VPS execution routes:

1. Device, store login/verification and storefront are distinct Apple facts A1/A2/A3. Google G1/G2 likewise retain hardware/store availability and sign-in/Play-country/payment categories. An already supplied first-subscription journey is reused; it is not turned into an old-entitlement interview.
2. PC0 retains A4/A5 or G3/G4 as explicit `requires_contact_gate` gaps. They are neither asked as live-check instructions nor filled as completed facts. G1 stays partial and G2 blocked; no next question does not mean those checks passed.
3. Google's existing static G1 prompt mentions store/App availability. Active guidance constrains it to reported device/store facts at PC0, with actual Claude App entry deferred to G3 after handoff. The fixture explicitly records `claude_app_live_entry=not_run_before_contact`, not a live test. The scalar scheduler alone does not compose the host's phase-aware wording.
4. A separate pure post-handoff fixture models reports received after an already independently authorized PC2 stage. Assigning contact-phase metadata is not a handoff, login or permission grant. Its next prompts are exactly A4 then A5, or G3 then G4. G4's full text asks whether the phone App has the intended service account, not whether the person previously subscribed.
5. The required target correspondence remains separate from Apple/Google sign-in and payment identity. The reported service-account alias is retained with source/time; no password or identifier is collected.
6. Q-P02, Q-A06 and retired Q-C07 never enter the no-conflict first-subscription path. Q-G05 is a renewal alias of Q-P07 and is not asked twice. A real-conflict control explicitly enables `subscription_conflict=True`; only then does relevant old billing appear, with A6 only on Apple. This preserves the intended exception rather than banning all legitimate old-order diagnosis.
7. Unknown/declined/deferred store prerequisites remain their truthful empty fact states and explicit missing-field reasons. They are not repeatedly asked or silently passed. A known negative is different and must not be relabeled unknown to manipulate a gate.
8. Once all reports in the synthetic later-stage fixture are present, G1/G2 planning may complete; G3 stays blocked and persistence remains false. **G2 is coverage/planning, not purchase eligibility.** This evidence does not prove automatic semantic eligibility checks for every reported value.

## Active instruction review

The following review evaluates the instructions' meaning in their surrounding procedures, not just keyword presence:

- **Intake Scheduling:** the subscription journey and actual task determine relevant questions; pure expertise/equipment ownership cannot choose a route. The explicit VPS plus mobile-channel facts therefore coexist rather than replacing each other
- **Intake payment registry:** P03 describes payment-device categories, P06 channel choice, while S01–S07 separately describe VPS resources and workflow. This provides the precise host-to-runtime separation exercised in T49
- **Routes common concepts and R-VPS:** execution host/runtime/network exit are distinct, and VPS workspace use follows a complete route. Payment choice is not an instruction to reclassify the workspace or buy another server
- **Accounts PC0 versus checkout:** device availability, store region and payment categories may be reported before contact; actual App entry, service-account correspondence, price and terms remain deferred. It expressly forbids buying gift cards to resolve uncertainty
- **Accounts Apple prerequisite tree and B2 steps 1–2:** iPhone/iPad availability is distinct from Mac-only redemption or Apple-account existence; login/verification and actual storefront are checked separately. System language, proxy address and device sales region cannot substitute for storefront
- **Accounts B2 step 5 and Google B3 steps 1–3:** official App/plan entry and intended Claude-account correspondence are checked in the permitted contact/login stages. A computer/VPS result cannot replace the phone's actual prerequisites
- **Intake A4/A5/G3/G4 meanings:** A4/G3 retain the desired App/plan entry; A5/G4 retain the intended service-account match. G4 is not a renamed old-subscription survey. Renewal G5 is deduplicated against P07
- **Intake and Accounts old-order rules:** P02/A6 require a relevant existing-billing task or actual conflict; first-time users do not receive another history survey. Google old orders retain the P02 condition rather than being embedded into G4
- **Accounts handoff/stopping paragraph and B5:** missing prerequisite evidence blocks advice that assumes purchase feasibility; route choice, plan acceptance and environmental results are not payment permission. Actual amounts, terms, recurring commitment and sensitive inputs require their separate current handoff
- **Contact policy and SKILL PC0 boundary:** no Claude App, login, subscription page, public target-service document or delegated request is started merely to complete the questionnaire. The modelled later-stage facts cannot open a real contact gate
- **Original D-SPEC §6.8–6.10 and D-ENV phone-preparation boundary:** runtime route and payment device are independent; first-time in-app checks remain required, but their live parts follow contact. Phone preparation is separate from computer verification. These original instructions match the reviewed active procedures

## Adjacent cases deliberately not closed

T36 and T38 were audited separately and remain pending. A known negative Apple-login fact is retained as `reported=False`; the generic evaluator does not automatically convert it into an Apple eligibility gap. At PC0, a G2 block may be caused only by deferred App/account checks. In an artificial later-stage all-answers control, G2 can pass while A2 is false, with G3 still blocked. This is the documented host-domain-reasoning boundary, not evidence that an unavailable account is eligible or necessarily a runtime defect.

For those two cases, the missing evidence is an actual pinned host response that disambiguates “有 Apple” or explicitly states the unavailable-login prerequisite and withholds gift-card/purchase readiness. Their report and exact negative-value projection are retained separately. This T49/T83 candidate does not claim either case, does not introduce an eligibility framework, and does not change production behavior.

## Reproduction and portability

Run from the integrated repository root, or set `GUARDIAN_AUDIT_ROOT` to a checkout when using this external candidate:

```sh
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_mobile_route.py -v
PYTHONIOENCODING=utf-8 PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_mobile_route.py --replay > mobile-route-replay.json
```

On PowerShell, set `$env:PYTHONIOENCODING='utf-8'` and `$env:PYTHONDONTWRITEBYTECODE='1'` before the same Python commands, and preserve UTF-8 if the shell re-encodes redirected output. Artifact destinations are selected by the operator. The test contains no text-file reads; all authoring/evidence text reads and writes use explicit UTF-8. Source text is Python UTF-8 source, independently of console locale.

Six candidate tests passed. Six also passed in a subprocess with `PYTHONUTF8=0`, coercion disabled, C locale and cp1252 standard I/O. With the same restricted default locale and explicit UTF-8 standard I/O, the replay matched the ordinary/repeated replay byte-for-byte. Python 3.10 grammar parsing passed; no 3.11 `TestCase.enterContext` API is used. These are cloud portability checks, not native Windows testing or a claim that Python 3.10 was installed/executed.

Existing support: 172 interview tests and 15 intake acceptance tests passed, zero skips. Test counts do not replace full-clause review.

Replay SHA-256: `927dd88cc3d9fc623fb6ffc03e649fb598f6a9c86a1eef56fc28396b7622ac81`. Logs, exact proposed unrun dialogues, source pins and artifact manifest accompany the delivery. Source changes require semantic re-review and rerun; aggregate ledger/tracker updates alone are not pinned dependencies.

## Review boundary

The independent reviewer checked every part of both exact original clauses, read the active guidance in context, verified the runtime dependency origins and all 11 source pins, reconstructed the two added files from the frozen patch, and reran the complete replay and regressions. The conclusion is clear for original L+C within the declared normalized-input logic and content-review boundary. The static Google G1 wording still requires the host's phase-aware composition; no generated host response was observed. Actual mobile device preparation, provider rules, prices, phone App/checkout behavior, real account matching and purchase authority remain outside this evidence. The original clauses and layers are not rewritten.

Independent validation: six candidate tests and six forced-cp1252 reruns passed; the normal, repeated and restricted-locale explicit-UTF-8 replays matched the stated SHA-256. Existing interview (172), intake (15), route (6) and traffic-policy (27) tests passed with zero skips. Python 3.10 grammar and known-API review passed; execution used Python 3.12.14, not native Python 3.10 or Windows. Each of the seven pure-call I/O sentinels was independently challenged successfully. A separate known-negative A2=False control still produced coverage/planning G2=pass with G3=blocked, confirming why T36/T38 remain pending and why G2 must not be presented as purchase eligibility. Proposed dialogues remain unrun. No ledger, runtime or shared-source changes were made during this review.

## Exact dependency pins

These source files were read from the frozen twenty-third tree and independently verified byte-identical in the twenty-fourth working tree. All hashes are SHA-256. The unchanged candidate regression is separately pinned below; this reviewed page is pinned by the external integration receipt to avoid a self-reference. Aggregate tracker/ledger pages are intentionally excluded.

| Dependency | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/scripts/interview_flow.py` | `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/intake.md` | `3eb0c795948d916804addfed31e8bcbb19502ec2447c8db2b0551f8d931e5742` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `tests/test_interview_flow.py` | `a411fe5a8f809ac6aac91ffc58580379056b2b158a334646b07647c22ced7bbe` |
| `tests/test_acceptance_intake_rebuild.py` | `d1480db2071fd5429fb63768043c96ca4f8b5b93a2f2b15854c3cbf423cb12eb` |
| Candidate `tests/test_acceptance_mobile_route.py` | `4faf1dc143ac5066e55f86acc749d11c536dcedc2f94368c493b9c39e55f6759` |


## Twenty-ninth subscription-repair preservation review (2026-10-18)

A separate read-only reviewer re-read every original clause on this page and the changed active intake/accounts guidance against the frozen integrated source. Past-order channel and proposed payment channel are now explicitly separate, without changing the selected runtime route. Actual purchase device/store/App/account prerequisites remain; no-conflict first-subscription P02/A06 stay absent and G04 remains target-account correspondence.

The unchanged `test_acceptance_mobile_route.py` suite passed all 6 tests with zero skips. Its full current replay was executed twice and is byte-identical to a fresh published twenty-eighth baseline replay; the SHA-256 is `927dd88cc3d9fc623fb6ffc03e649fb598f6a9c86a1eef56fc28396b7622ac81`. The same suite passed with cp1252 standard I/O under C locale, and explicit-UTF-8 replay bytes also matched. Across the five related intake/entry/mobile/status pages, 47 original tests and eight separately authored delta tests passed. Counts supplement the complete clause/content review, not replace it.

The 218 original requirements and layers are unchanged. The updated current dependency pins on this page follow that actual review and replay. Historical observations remain historical. No generated dialogue, arbitrary-language extraction, real account/store/plan eligibility, native device, network/contact, payment or action-authorization evidence is added; this preservation review accepts no adjacent pending case.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.


## Reported-negative gate clarification preservation review (2026-10-18 UTC)

An independent read-only review compared the frozen thirty-first baseline and thirty-second candidate. The sole active-source change is the explanatory paragraph after G1/G2/G3 in intake.md; runtime, fixtures and original requirements remain byte-identical. T49 still separates the VPS execution workspace from the mobile payment device and follows the chosen Apple/Google branch without forcing web-card payment. T83 retains distinct device, store/login, actual App/plan entry and target-account correspondence checks; first-subscription P02/A06 remain conditional and G04 does not become an old-order question. The new paragraph makes explicit the already documented negative-A02 host-domain boundary: preserve the unavailable-login fact and the helper result, while withholding purchase advice that assumes Apple feasibility. Synthetic PC2 metadata cannot promote the current session or authorize contact.

All 6 unchanged original tests on this page passed on both trees, with zero skips. Each complete --replay stdout was freshly produced twice per tree; all four byte streams are identical: SHA-256 `927dd88cc3d9fc623fb6ffc03e649fb598f6a9c86a1eef56fc28396b7622ac81` (1663404 bytes). Across the twelve affected pages, 105 original tests and 207 supporting interview regressions passed on each tree. These executed comparisons supplement the full original-clause and active-guidance review, not replace it.

The unchanged helper can report G1 complete and G2 pass/conditional_plan_only=false for an answered negative Apple-login fact; that value remains reported and negative. An independent synthetic control reproduced this on both trees while retaining blocked G3, absent persistence authority, separate PC0 contact gaps, and blocking unknown/refused/deferred, pause and unresolved-resume controls. Its identical complete-output SHA-256 is `239fc78643aa3282342393330fc65ed1fc846e0f7bb89748dd9c6e7a1502f932`. This is an interpretation boundary, not a new eligibility engine, runtime fix, purchase-execution defect or counterfactual eligibility inference.

Only this reviewed current intake dependency pin and this page's corresponding ledger evidence hashes may change. The 218 original clauses and layers, all historical source/response packets and their existing pins, and native/contact/action boundaries remain unchanged. This preservation review adds no accepted case, generated response, actual device/store/account result or action permission; future source drift requires a new scoped review.


## 2026-10-18 batch33 final-revision3 preservation

This dated review preserves the existing original cases and their verification layers; it does not add T77/T80 acceptance or replace older execution/generation history. The complete original clause was reviewed against the current intake guide, full outputs, and reachable authority/lifecycle boundaries.

- T49 (L+C): 选择 VPS 使用但想以手机内购支付 — 运行环境与付款设备分开，读取对应分支，不强制网页银行卡
- T83 (L+C): 首次订阅选择 Apple/Google 内购 — 保留设备/商店/目标账户对应/入口检查；不在 A6/P02/G04 中重新问旧订阅

The complete deterministic replay remains byte-identical to the published baseline, including all state/fact provenance, applicable questions, bounded exits, G1/G2/G3, route, contact and consent fields. Equality is accompanied by full original-clause/current-guide review, not used as a substitute for it.

The separate actual-conflict supplement is outside the ordinary replay. Its original partial/historical input remains tested: only the missing status/page-to-target detail is clarified once, stopping does not resolve G2, and a separately documented synthetic current reply completes coverage while the conflict remains unresolved. Original/first-detail snapshots and prior facts remain; future Apple/Google selection never supplies an old/current order channel. All nine selected supplemental methods pass (783 captured public API calls, zero guarded I/O attempts).

Fresh complete replay: `927dd88cc3d9fc623fb6ffc03e649fb598f6a9c86a1eef56fc28396b7622ac81` (1663404 bytes), repeated twice identically. Every full replay also equals the retained revision2 output. Test suite: `tests/test_acceptance_mobile_route.py`; full recursive differences are retained, not filtered.

Current compatibility was reviewed against the 635-file revision3 source freeze SHA-256 `6fbbd10dbe6fb993b1bdda0ea09a897a17a3fa4de83e471a420018c186798bac`. The final change since revision2 is public schema definitions only; all 79 production function/class ASTs, intake guide, CLI and five existing adapted tests are unchanged. Actual schema/runtime roundtrip and malformed/nested/generic controls passed independently. Current preservation receipts include 105 page tests, 282 interview tests, 188 other support tests, 226 C/cp1252 tests, 13 actual CLI commands/12 state inspections, 15 complete current-helper calls and the full known-negative control. These are bounded synthetic/offline checks, not new model dialogue, native-device validation, real billing eligibility or action permission.

Retained prior active dependency SHA-256 values (historical review identity; the current table above names the final reviewed bytes):

- Historical `skills/claude-guardian/scripts/interview_flow.py`: `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e`
- Historical `skills/claude-guardian/references/intake.md`: `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71`
- Historical `tests/test_interview_flow.py`: `7140e70b88e4cd3099d2fa725b3b20269de511be90d4dd020154d2db3e5e0965`
- Historical `tests/test_acceptance_intake_rebuild.py`: `e26a26ee3b3d0ba93270787f8dbd8022ed11adb2fbbb0f1229df8f1aef57245a`
- Historical `tests/test_acceptance_mobile_route.py`: `c0d6e44a5f5b1427c92459d49528e73eec40d36385dee2fffa4598e42548b769`

Detailed approved preservation records: [batch33 current-guide/runtime bridge](batch33-subscription-preservation/REVIEW.md). Historical subscription consumed-source/response manifests remain immutable; current compatibility is a separate reviewed record.


### 2026-10-18 revision4 exact-source compatibility

The active dependency rows above identify revision4; prior revision3 review and historical hashes remain in the preceding dated record. The scoped P02 terminal-retention fix preserves a known complement without filling the refused/unknown/deferred gap, re-questioning it, changing provenance, or opening G2/G3. Retained-plan interruption review remains separate. All105 affected page tests pass and all12 complete original-case replays are byte-identical to revision3; complete current helper15-call equality and historical packet18-test integrity also pass. See `batch33-subscription-preservation/preservation-review.md`, its exact freeze/portable receipts and the independent runtime and engineering approval. This is current compatibility evidence, not new model generation or added acceptance; the existing218 clauses/layers and45 accepted statuses are unchanged. Independent source4 runtime and engineering clearance support preservation of the existing45 only; integration application remains separately reviewed and T77/T80 are not newly accepted.
