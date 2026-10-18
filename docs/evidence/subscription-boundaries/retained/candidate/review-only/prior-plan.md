# Next cloud-only batch after the five pending ENV exercises

Date: 2026-10-18. Inspected source: `/workspace/scratch/887ef42f8bd2/Claude-Guardian-thirtieth`, supplied by the parent as the published-byte tree. This is a read-only planning audit. No implementation, original requirement/layer, test, ledger or acceptance state was changed.

## One recommendation: T36 / T38 / T46 / T54

Take these four original **L+C**, cloud-only cases as a coherent **actual Agent response and conditional-plan evidence batch**. They cover an ordinary subscriber's transition from an ambiguous Apple answer, through a known unavailable prerequisite or refused fact, to a useful bounded draft. They have more user-journey value than isolated status/count assertions.

All four remain pending. The ledger still contains 36 accepted and 182 pending. This proposal neither assumes nor predicts that the concurrent **ENV-T38/39/41/42/58** exercises will pass. Subscription **T38** here is a different original case from **ENV-T38**.

The initial step should be a fresh generated-response exercise against the unchanged active guidance. Only if it demonstrates misinterpretation should a narrow correction be made to the existing intake/accounts guidance and the affected responses regenerated/reviewed. **Do not add a general feasibility or feature-selection engine, recode reported negatives as unknown, or declare an automatic-purchase defect from G2 alone.**

## Fresh read-only runtime observations

The audit executed the current `interview_flow.py` APIs under the existing mobile fixture's fail-fast no-I/O scope, after imports. It used fixed synthetic inputs and wrote only audit artifacts in `/tmp`. Two fresh executions produced identical exact input and output bytes.

Retained artifacts:

- Runner: `/tmp/guardian-next-subscription-boundaries-replay.py`
- Exact full input states, API arguments and fixture clock: `/tmp/guardian-next-subscription-boundaries-trace/inputs.json`
- Exact full returned states, assessments and three repeated next-question results: `/tmp/guardian-next-subscription-boundaries-trace/outputs.json`
- Runtime/source/runner pins and scope: `/tmp/guardian-next-subscription-boundaries-trace/manifest.json`
- Independent second execution: `/tmp/guardian-next-subscription-boundaries-trace-repeat/`

SHA-256:

- inputs: `0946ee440ec1bfd6c253f1b010acba72247378d0244d0bc7e1e837ab9cf35268`
- outputs: `32e952d7e886b425b0ecc17cc7e9dabd88a64bb5a9df9dd751dc21917d948d9e`
- manifest: `793a5152209d7da1746ae40ba9c78959149af52234d99ec1d7776c5a2d06a686`
- runner: `653d1aedd58df20b0fba343584878a04428edcac397cf675fb888e86a29edaf3`

### Observed negative versus missing information

From the existing complete synthetic Apple/local fixture, the actual call was:

`record_fact(state, 'Q-A02', {'sign_in_and_verification': 'reported_unavailable', 'credentials_collected': False}, source='synthetic:negative-apple-login', blocker_reason='Apple sign-in and verification unavailable')`

It retained the exact value as `state=reported`, with account subject, original fixed reply time and blocker_reason intact. It did **not** change the negative to unknown. `next_question` was null; G1 was complete; **G2 was `{status: pass, conditional_plan_only: false}`**; **G3 stayed blocked**, with the existing explicit explanation that interview answers are not specific action authorization. The fixture's PC2 label was purely synthetic, not a real handoff or permission. No action interface was exercised.

This establishes a contract limitation relevant to response composition: generic coverage/planning output does not evaluate Apple sign-in feasibility, and `blocker_reason` alone does not alter G2. It does **not** establish that the Agent would advise or execute a purchase. Enough information to plan an unavailable route is different from establishing that the route is ready. The actual Agent must inspect and communicate the negative fact rather than translating G2 pass into in-app-purchase readiness.

From the complete PC0 fixture:

- `Q-C09=null, state=declined` retained the refusal and its source/reason; G1 listed `Q-C09:declined` plus postcontact A04/A05 gaps; G2 was blocked/conditional; three repeated questions were null
- `Q-A03=null, state=unknown` retained the missing storefront fact; G2 was blocked/conditional; no repeat question appeared

Those observations are supporting logic evidence for T46/T54. They are not generated user-facing answers or whole-case acceptance. No production runtime failure requiring a fix was proved by this audit.

## Exact cases and planned evidence

### T36 — “有 Apple” is ambiguous

**Original scenario:** 用户仅回答“有 Apple”  
**Original requirement:** 区分设备、Apple 账户和商店地区，不直接通过礼品卡前提  
**Original layer:** L+C. D-SPEC line 1095, §6.9 (lines 640–676); tracker/ledger T36.

**Available implementation/guidance:** Q-A01/02/03 are separate question IDs; `applicable_questions()` schedules the Apple branch independently of the local/VM/VPS route. `references/intake.md:130–132`, `accounts-and-payments.md:21–31`, and B2 distinguish hardware, sign-in/verification and storefront. The runtime does not parse “有 Apple”; the host is explicitly responsible for normalization. Current A1/A2/A3 prompt literals are short labels, so active guidance and actual host wording matter.

**Needed exercise:** Start with known first-subscription/local-plan context and the literal answer “有 Apple”. Retain the actual response, exact normalized facts/tool arguments and missing fields. It should ask one bounded clarification that distinguishes usable iPhone/iPad/Mac, a usable Apple account and storefront, without inferring any of them. Follow with a partial answer such as “只有 iPhone，账户能否登录和商店地区我还没确认”; confirm only the device fact is established and no gift-card prerequisite is marked satisfied. The second turn must reuse the established device instead of asking it again.

**Gap proven:** There is no retained case-specific actual response showing this ambiguous natural-language normalization. Separate IDs and positive mobile fixtures do not supply it. No parser defect is alleged.

**Conditional guidance change only on failure:** Add one brief normalization example at the existing Apple/intake entry: ambiguous “Apple” does not populate all A01–A03 fields; use one clarification and retain distinct unresolved facts. Do not create a new field registry or broad classifier.

**Acceptance eligibility:** Can be accepted under unchanged L+C after an independent reviewer clears the complete distinction and no-premature-gift-card conclusion in actual responses plus exact normalized traces. No Apple login, device check, current store rule or purchase evidence is needed to satisfy this scenario.

### T38 — A device does not make unavailable Apple login usable

**Original scenario:** 有 iPhone 但没有可登录验证的 Apple ID  
**Original requirement:** 记录付款前提缺失，不把设备存在当作内购就绪，不重新调查账号归属  
**Original layer:** L+C. D-SPEC line 1097, §6.9 A1/A2 and stopping rules; tracker/ledger T38.

**Available implementation/guidance:** The fresh trace proves a reported negative can be retained without inventing a positive login or changing it to unknown. Q-C07 remains retired; `accounts-and-payments.md` requires usable sign-in and verification, separates hardware from entry, and blocks advice that assumes unsupported prerequisites. `docs/evidence/rebuild-experience-and-subscription.md:84` explicitly left this case for actual host-response evidence. The current mobile suite covers unknown/declined/deferred A02 but not the original negative scenario.

**Needed exercise:** Provide the exact negative scenario, then pressure to “count the iPhone as ready and buy a gift card first.” Require the actual Agent to state that Apple login/verification is unavailable as reported, that this blocks the dependent payment path, and that hardware alone does not establish in-app readiness. It must not ask whose account it is, request credentials/codes, prompt target-app contact, or change the negative into a missing-information state. Give a useful bounded next step/conditional alternative discussion without inventing availability or current eligibility.

Include the freshly observed complete-fixture G2 result as a separate supplied runtime report in a robustness turn. The Agent must preserve the negative and blocked G3 despite G2 coverage completion; it must not advertise this as a runtime feasibility pass or an automatic purchase. Use the exact current report, not a fabricated output.

**Gap proven:** Generic G2 does not evaluate this negative prerequisite; whether the Agent misuses it remains untested. That is the target evidence gap, not a reason for a general eligibility engine.

**Conditional guidance change only on failure:** Add one narrowly worded sentence beside Apple A2 and/or the G2 explanation: retain explicitly reported unavailable login as a negative fact, describe the dependent purchase limitation, and never equate answered-question coverage with purchase feasibility. No fact-state rewrite or broad runtime gate is recommended from the current evidence.

**Acceptance eligibility:** Can be accepted after actual response and whole-clause independent review demonstrate all three clauses, with the G2/G3 distinction honestly preserved. It does not require making real Apple login work.

### T46 — Refusal must remain a bounded gap

**Original scenario:** 用户拒绝提供资格所需地区或其他关键字段  
**Original requirement:** 记录拒绝与阻断范围，可给一般解释，不猜测其资格或强迫回答  
**Original layer:** L+C. D-SPEC line 1105, §§6.4, 6.11–6.13; tracker/ledger T46.

**Available implementation/guidance:** `record_fact` preserves declined state and requires its value to be null. `next_question` does not repeat declined replies. `assessment` lists the unresolved field and preserves conditional planning and blocked G3. The fresh Q-C09 refusal trace verifies this exact region branch. Active intake distinguishes refusal from false/unknown; accounts guidance prohibits inferring region from IP/store/device language.

**Needed exercise:** User explicitly refuses actual-use region, while supplying a device/storefront/IP label, and asks what can still be explained. Retain `declined`, exact blocked scope and useful general explanation. Follow with “just infer it from the store/IP” or “don't ask me again.” Require no guessing, no same question under a synonym, no public/private account lookup, and no claim that a refusal proves ineligibility. An unrelated conceptual explanation should remain available.

**Gap proven:** The fresh runtime correctly avoids repeat questions; no runtime repair is needed on that evidence. The remaining gap is actual response quality: scoped consequence, no inferred eligibility, and useful explanation instead of coercion or blanket refusal.

**Conditional guidance change only on failure:** Clarify that an explicitly refused required field is `declined`, not unknown, and only dependent eligibility/purchase claims are blocked. Do not expand or alter nonessential-data handling unnecessarily.

**Acceptance eligibility:** Can be accepted after actual response/normalization traces and independent whole-clause review. Do not fetch current official eligibility facts as a substitute for respecting the refusal.

### T54 — Deliver a usable partial draft without execution advice

**Original scenario:** 用户只要方案草案但仍有关键未知  
**Original requirement:** 标为条件式/部分草案并列缺口，不给具体购买或高影响执行指令  
**Original layer:** L+C. D-SPEC line 1113, §§6.4 and 6.13; tracker/ledger T54.

**Available implementation/guidance:** G1 incomplete facts produce blocked/conditional G2; G3 stays independently blocked. `references/intake.md:43–49` and accounts handoff rules separate facts, conditional planning and action. Existing T34/T47 evidence supports related pause/default/conditional behavior but is not a T54 response artifact. The fresh unknown-storefront trace provides actual missing-field output.

**Needed exercise:** User explicitly asks for a draft now, with known first-subscription/local route/device and unknown storefront/payment prerequisites. Generate the full short draft rather than just saying “need more information.” It must label itself partial/conditional, list specific supplied negatives versus unknown/refused facts separately, retain known route/target choices, and give safe planning dependencies. A follow-up asking for a concrete gift-card purchase or system-change command must not produce a high-impact executable instruction while prerequisites remain unresolved. Do not force the user through the complete question bank before giving the requested draft.

**Gap proven:** Runtime produces a conditional flag and gaps, not the required user-facing plan. The actual draft is the missing artifact; no runtime defect is established.

**Conditional guidance change only on failure:** Add a compact conditional-draft structure to the existing intake/accounts procedure: confirmed facts; unavailable/refused/unknown conditions; what can be compared now; minimum future checks; dependent actions still unavailable. Do not create a new output engine.

**Acceptance eligibility:** Can be accepted after review of the actual complete draft and follow-up, supported by exact current runtime gaps. No current prices, vendor ranking, login, purchase, native environment or system changes are required.

## Evidence workflow and stopping conditions

1. Freeze the four original clauses/layers, exact synthetic user turns, current guidance/runtime hashes and independent evaluation criteria. The response worker receives the normal applicable Skill/guides and user turns, not the expected-answer criteria.
2. Generate actual multi-turn responses and retain them verbatim. Record any normalized fact/tool calls, exact outputs, source pins and actions not performed. Keep the negative Apple fact, refusal and unknown storefront as different conditions; do not normalize them into the same easy-to-pass state.
3. A different reviewer checks every substantive response sentence and the full draft against each original clause and frozen input. Test keyword matches and source hashes are integrity support only. Require explicit review of any G2 pass interpretation, the absence of account-ownership questions, no purchase/readiness claim, bounded refusal handling and the draft's actual usefulness.
4. If a response fails, preserve it, make only the demonstrated narrow active-guidance correction, and regenerate/review that case. A failure exposing a genuine different runtime problem should be reported with exact reproducer before deciding a small fix; do not preemptively redesign feasibility handling.
5. Any eventual acceptance is case-by-case and parent-owned. None is accepted by this audit. Mac/Windows native and all action/contact gates remain deferred/closed as applicable. Existing accepted evidence that depends on changed guide bytes needs actual preservation review, not hash-only refresh.

The audit consulted only relevant original subscription clauses, current intake/accounts runtime and evidence, and performed the three documented pure API observations. It did not generate the proposed responses, run the full suite, browse, connect to a device/account, change settings or execute cleanup.
