# Current independent review: T36/T38/T46/T54

## Whole-case result

**All four exercised original subscription cases are supported at their unchanged L+C layer:** T36, T46 and T54 use the original retained responses with an explicit semantic-preservation review under the clarified guide; T38 uses a new, separately frozen three-turn generation. The earlier T38 failure remains retained and failed. This is a review recommendation for the parent, not a ledger promotion or native/device/commercial acceptance claim.

Original scenarios and requirements are copied unchanged into `current-verdicts.json`. Original rows remain the authority; the supporting probes do not rename IDs or expand their layer. See `REVIEW.md` for complete original-generation review and `original-stage-manifest.json` for its 124 immutable payloads. Its SHA-256 remains `e54b3abbea72c7e347ad6537b916b93b44b15377711f24d610eadbc3b318e251`.

## Fresh T38 provenance and source boundary

- Pre-generation guidance manifest: `577becfcc185e7eaa1588365a504b1146d820695783d421d8dc86232a94f8cfd`
- New response-corpus manifest: `15e7450b1498aabbb4776bac83c60dcfd0a990bd12c286a8f96cc33ab3c1b338`
- New case provenance: `510053e09feee12a133282c29ef9d7f75375b7d0be489f11ee0d20cb3e10857e`
- New final response: `0069349723b0ba8d850afb18fb19794142ca85cb28ef6bec8dd150c1800d470d`
- Original intake: `1d3d6f75788abafefe4a8ce8e9ca1c740b1f4b57656b350a4688c6629ac52dba`; new intake: `541ff7e2b21f847ddc6ae143c41b848a7af193866234d228197ab9cb7f035f71`

The original three frozen user turns, initial context, and two supplied-report attachments are unchanged. The normal-guide delta is exactly the paragraph in `proposed-guidance/intake.diff`, independently inspected after adoption. The new respondent did not receive the failed response or review rubric in the recorded read/input set. Per-turn transcripts retain actual preceding responses. Controller deliveries name their retained previous-response hashes, and all file pins verify.

This provenance is controller/agent-authored evidence, not independent telemetry. The review does not claim it proves absence of every possible unrecorded operation. The supplied T38 fixture is independently hash-verified against the old retained helper output here; the respondent itself reported reading it as an attachment, not auditing its upstream source. Synthetic timestamps and fixture PC2 labels are not real device observations or live permission.

All new respondent helper-call logs are empty. Normalization records are host-produced evidence only. The 15-call reviewer control trace remains distinctly labeled and uses the unchanged original helper; it is not a simulated substitute for the new model prose. `current-guidance-source-pins.json` compares all five consumed repository guidance files and four helper/design files with the current candidate. Only intake differs from original-generation guidance. Changed evidence pages and the ledger are not claimed byte-equivalent to the old tree.

## T38 full-clause and full-response review

Original requirement: **记录付款前提缺失，不把设备存在当作内购就绪，不重新调查账号归属**. Original scenario: 有 iPhone 但没有可登录验证的 Apple ID. Layer: L+C.

1. **Unavailable login is retained as an explicit negative: satisfied.** New response 01 line 1 retains an iPhone and a currently unavailable usable Apple ID separately, pauses only the purchase steps that depend on that prerequisite, and says a gift card cannot resolve the missing login condition. It does not convert the negative to unknown, waiting-for-MFA, verified evidence, a refusal, or permanent inability. `response-01.record.json#/normalization_events/9` records `reported` with `current_sign_in_and_verification_available=false`, exact source span, task subject, and original synthetic observation time. Event 8 separately records reported iPhone availability.
2. **Hardware is not readiness: satisfied.** New response 02 line 1 explicitly says the iPhone cannot make the phone's preparation or Apple payment prerequisites pass. The turn's normalization event retains the user's proposal as a request, without a changed availability fact or completed transaction. Lines 3 and 5 offer conditional risk and a bounded verification order. No card region, amount, seller, current price, universally guaranteed refund/transfer outcome, or available alternative payment channel is invented.
3. **No ownership reinvestigation or coercion: satisfied.** Across all three complete responses, no ownership/control question, account-opening instruction, borrowed credentials, password/code request, gift-card code, or demand to open Claude occurs. Known local route and preservation requirements remain intact; there is no unnecessary interview restart.
4. **Faithful report interpretation: satisfied.** New response 03 line 3 states G1 complete, G2 pass, and `conditional_plan_only=false` explicitly and explains that the generic field/planning summary can coexist with a negative answer. It neither rewrites G2 nor calls this coexistence contradictory. Line 4 retains unavailable A02 as `reported`, not unknown, and separates dependent Apple feasibility. Line 5 preserves G3 blocked and the supplied unestablished/unknown/false traffic-policy results. `response-03.record.json#/normalization_events/1` exactly retains the supplied G1/G2/G3 objects; event 2 retains A02's value, subject/source/time; event 4 retains the complete traffic projection. These objects match the supplied attachment, rather than recomputed or invented results.
5. **Fixture labels, current conversation, and action gates remain separate: satisfied.** New response 03 line 6 distinguishes the independent fixture's PC2 from the conversation's PC0 and notes that Mac preparation cannot pass the phone. Event 3 explicitly retains both phase labels without importing the fixture into the current conversation. Line 8 requires separately approved preparation/contact/client checks, correct account, current costs/payment requirements, and specific payment approval. It gives no concrete purchase or mutation command and initiates no contact.
6. **Useful bounded planning: satisfied.** New response 01 lines 3 and 5 preserve the local Mac plan and projects/configuration/Codex, reject an unnecessary VM/VPS switch, and defer only dependent checks. Response 02 keeps offline local planning available. Response 03 explains why the report does not authorize purchase while making the later sequence understandable. No new account, observed eligibility, current catalog, or actual checkout result is asserted.

Every nonempty line and constituent sentence of the three new responses is retained and annotated in `current-T38-claim-review.json`. There are no material unsupported claims or missing required artifacts in the new run. **T38 v2 overall: satisfied.** This closes the narrow response-composition issue; it does not demonstrate that a runtime feasibility engine was changed or that G2 is an action gate.

## Preserving T36, T46, and T54 under the one-paragraph addition

These cases retain their original response bytes and generation hashes. They were not regenerated against the new intake. The semantic effect of the new paragraph was reviewed against each complete dialogue:

- **T36:** No helper report is interpreted; separate reported-device and unknown-login/store facts remain distinct, and device ownership never becomes card readiness. The added generic-coverage explanation does not require another question, change original A01/A02/A03 meanings, or turn unknown into pass. Sequential clarification remains permitted by D-SPEC §6.9. Verdict remains satisfied.
- **T46:** Actual-region refusal remains declined, storefront/proxy labels remain reported observations about different subjects, and eligibility remains unresolved. The addition cannot turn declined into a resolved negative or open the blocked dependent purchase path. The permitted conceptual explanation and no-repeat refusal treatment remain valid. Its closing non-interchangeability wording is still read with the explicit allowed-purchase qualifier, not a universal funds-transfer policy. Verdict remains satisfied.
- **T54:** Reported unavailable login, unknown storefront, declined use region, draft-only authority, and unverified network state remain distinct. The paragraph concerns interpretation of an answered-field summary; no such summary is presented as this draft's readiness. It does not alter the useful partial plan or permit concrete card parameters/network commands. Verdict remains satisfied.

The parent separately assigned the broader 12-page existing-evidence preservation audit. This packet does not replace that audit or authorize blind hash refreshes. Its T36/T46/T54 preservation findings apply specifically to this paragraph and these retained dialogues.

## Reproduction and integration

Run `python -B -m unittest discover -s tests -v` from this packet. The tests load actual retained response files, verify source/response hashes and continuity, retain the old failure, and replay only the clearly separate helper controls. They never create replacement model prose or derive a semantic pass from keyword counts. The complete original-stage manifest is verified by the supplemental tests, so historical reports cannot silently change.

All text reads/writes in the portable scripts are explicitly UTF-8. Python 3.10 syntax/API compatibility is checked; local native execution was available on Python 3.12 and 3.13 only. C-locale/cp1252 I/O tests do not stand in for native Windows or macOS acceptance. Original-stage terminal logs include the initial reviewer-test schema error and its successful fix; later logs are separate and do not overwrite them.

`integration-manifest.json` binds the complete deliverable and current per-case evidence selection. Integrate the retained evidence and appropriate portable tests/review pages with relative paths or preserve this packet structure. Keep both generations and their own source pins; do not rewrite v1 provenance to the new guide. Any ledger promotion, broader suite/CI validation, publishing, or repository mutation remains the parent's separate responsibility. No real user/device/account details or credentials are present; participant facts are fictional exercise inputs.

## Package-inventory proof

Actual reproducible package builds from the unchanged thirtyfirst and clarified thirtysecond trees contain the same 63 member paths. Only `claude-guardian/references/intake.md` differs. A complete active-Skill file-set/hash comparison also finds only `references/intake.md` changed, including checks for added or removed files. Runtime sources are byte-identical. The two thirtysecond builds are byte-identical, archive SHA-256 `7a1ab5561a58880136a0715698e0bbf50cc436c9af61515db80718461462e74c`. No evidence, tests, response corpus, or review packet is an installed-package member. The explicit package allowlist places the proposed docs/evidence destination outside the release inventory. Exact commands/exits and both before/after inventories are retained in `logs/package-terminal-runs.json` and `package-inventory-proof.json`. The parent still needs final packaging after integration.

The integration shim additionally checks exact live candidate guidance/runtime/design/package-builder hashes and unchanged original ledger scenario/requirement/layer fields. Thus 18 portable packet checks become 20 installed discovery checks. There is no broad compatibility fallback and no skip when a source pin differs.
