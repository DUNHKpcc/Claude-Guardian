# ENV-T81: required controls remain contact blockers

Date: 2026-10-18 UTC. This twelfth-tree subset contains a narrow in-memory
workflow correction, exact offline replay, and active-content review. It makes no
network request, launches no client, changes no host settings, and purchases
nothing. All adapter/target/observation/approval records are synthetic host
fixtures. Original acceptance conditions and layers are unchanged.

## Original whole case and decision

| ID | Original scenario | Original requirement | Original layers |
|---|---|---|---|
| ENV-T81 | 接触前必需项目未知或有真实误直连 | 门禁保持 closed；不是标成可选限制后自动登录/购卡 | L + C |

The row is copied from D-ENV §12.3 and the original implementation tracker.
Relevant complete rules are D-ENV §17.5 and §18.5–18.8, and D-SPEC §6.13.
This page supplies an L replay and a sentence/clause C review for the complete
row. Final eligibility is subject to independent review and parent integration;
test totals alone do not establish acceptance. No N, X or R evidence is claimed
or substituted for another original case's required layers.

Interpret `closed` according to the original §18.8 state model, which includes
`closed`, `eligible_awaiting_user`, `open_scoped` and `revoked`. Before any grant,
missing mandatory preparation or a direct-path conflict leaves literal `closed`.
An invalidated existing grant becomes `revoked`, clears its scopes, and retains
phase/contact history. This is an explicitly non-open state, not a renamed open
scope. An open current snapshot with only a denied action was found insufficient
and repaired; it is not excused as a historical receipt.

## Concrete failure, repair and compatibility

The exact frozen eleventh `workflow_guard.py` was
`8008ae69a05031f5166d36b165597635d460530fa08d7854e4f0256920630f0a`.
The old sequence was:

1. A synthetic, fully supported PC1 handoff with complete declared preparation
   evidence yielded `allowed=true`, `phase=controlled_contact`,
   `gate_state=open_scoped`, and the client scope.
2. A newer authoritative-style `unknown` record for the required fault-blocking
   control was supplied. PC2 and client/login/payment requests were denied, but
   current `State` and `snapshot()` still advertised the open grant.
3. In an initial incomplete repair, simple revocation followed by same-binding
   `rebind` let the old passing evidence reopen the gate. The new failing-first
   retry test caught that separate issue.
4. Approval-wait expiry also needed consistent handling: a declined/cancelled
   reply with a valid elapsed interval could establish an expired grant while
   the action remained denied. The primary approval denial must remain visible,
   and the expired grant must not remain open.

The final correction uses the existing review-epoch mechanism, no new executor,
service, network adapter, schema, API argument, or dependency:

- A structurally valid next-phase handoff or otherwise valid exact action in the
  current grant rechecks that grant's prerequisite basis. PC1 requires its PC-G1
  evidence and readiness; PC2 additionally requires unauthenticated PC-G2 evidence.
- A genuine current prerequisite failure or readiness conflict revokes that
  grant and rotates its in-process review epoch. Old evidence/action facts cannot
  reopen it through rebind, resume, or merely newer timestamps. A new scoped host
  review, fresh applicable facts, and independent handoff approval are needed.
- Revocation retains phase and known contact history. It does not fabricate an
  observation of contact. Repeated already-revoked requests do not rotate again.
- The same barrier applies to approval-wait expiry, including a timed,
  context-unchanged declined reply. The original denial remains the Decision's
  primary reason. Invalid clocks, callback failures and changed/reentrant context
  do not invent an elapsed time or overwrite another state transition.
- Future-stage checks are genuinely pending, not relabeled optional. Missing
  unauthenticated client evidence does not revoke a valid PC1 collection scope;
  missing authenticated checks blocks payment without revoking a valid login
  grant. This preserves the original prohibition on circular login prerequisites.
- Malformed context/action/scope, wrong-target or unsupported requests, stale
  action-only facts, missing exact action permission/plan/purchase review, and
  out-of-scope login requests do not revoke an unrelated otherwise valid grant.
  A later valid scoped evaluation still rechecks the supplied controls.
- Independent local planning remains possible while contact is blocked. It is
  separately authorized scheduling, with `executes=false`; it is not a bypass.

The immutable runtime contract remains trusted-host input plus point-in-time
workflow eligibility. The host supplies applicability, target identity, complete
current observations and genuine authorization. This module cannot detect a host
that omits a mandatory requirement, suppresses an observation before reporting it,
forges native adapter declarations, or misclassifies a purchase as a local plan.
There is no OS isolation, native traffic observation, actual consent or automatic
login/payment implementation in this test. A fresh epoch is an in-process review
identity assertion, never proof that the host performed the review.

## Exact L replay and independently written expectations

`tests/test_acceptance_required_controls_rebuild.py` calls the real
`WorkflowGuard.transition`, `evaluate`, `record_observed_contact`, `rebind`,
`resume`, `state` and `snapshot` APIs. Test fixtures construct `Binding`, `Scope`,
`Requirements`, `Readiness`, `Evidence` and `Action` directly. They neither mock
these decisions nor set a gate to open by assignment.

The target is `device-a/user-a/native-a/profile-a/config-a/network-a/runtime-a`.
Two mandatory PC-G1 references are `target-path` and `required-fault-blocking`;
`client-path` is PC-G2 unauthenticated and `authenticated-path` is PC-G2
post-login. Exact supported fixture scopes are a local plan, client check,
official-login handoff, subscription review and gift-card review. The gift-card
scope is explicitly host-classified as a payment handoff; it is not a new
classifier or card-purchase implementation.

All public Decision fields are compared with handwritten expectations:
`allowed`, ordered `gaps`, every complete supported scope, `pending_checks`,
`enforcement_level=workflow_guard` and `executes=false`. State and snapshot are
also compared completely, including scopes, phase, gate, observed-contact history
and `runtime_permission_restorable=false`. The test does not generate expected
outputs by serializing the returned object. Approval requests are checked in
full where reached, and absent callbacks are asserted where prerequisites block.

| Exact scenario | Required observable result |
|---|---|
| Missing or unknown/skipped/not_applicable/blocked/failed mandatory control | PC1 denied with `EVIDENCE_REQUIRED:required-fault-blocking`; direct PC2 invalid; client/login/subscription/gift-card denied; literal closed; no callback |
| Mandatory control also represented as a readiness gap | `G2_INCOMPLETE` blocks all dependent paths; complete evidence does not erase the gap |
| Scoped `device-a-profile-a-direct-path-observed` conflict | `KNOWN_CONFLICT`; no contact/login/payment approval; closed before any grant |
| Newer unknown/fail/expired/future/malformed observation or tied failed record plus old pass, both list orders | Old pass is not resurrected; authoritative observation time, stage, target and result control the decision |
| Wrong source kind/stage/time or any of seven binding dimensions | Required control remains missing; no callback |
| Host records observed contact | Existing review epoch invalidated; `revoked` and `observed`; even newly dated old review records/facts remain rejected |
| Same-binding rebind or saved forged open/approved fields | Permission not restored; old passes rejected; conservative history retained |
| Current review but unresolved direct-path conflict | Conflict still blocks; epoch alone is not readiness |
| New mandatory unknown after a prior valid PC1 | PC2 denied; current grant becomes revoked with no retained scopes; later client/login/payment remain denied |
| Exact valid action in PC1/PC2 discovers a current-grant failure | Revocation and retained phase/history; no pre-failure approval callback |
| Later-stage check missing | PC1 still usable to collect its client evidence; authenticated check remains pending at login and blocks payment |
| Genuine invalidation followed by rebind/resume | Old pass and redated old pass cannot reopen; fresh scoped review can obtain only a new fixture grant; old action facts remain rejected |
| Required control expires during action or PC2 handoff approval | Original required-evidence denial plus revoked prior grant; epoch barrier also blocks stale retry |
| Approval is denied/cancelled/times out/returns an invalid reply while control expires | Primary `CURRENT_EXACT_APPROVAL_REQUIRED` retained; valid elapsed time invalidates expired grant; still-valid grant preserved |
| Invalid elapsed clock | `APPROVAL_CLOCK_INVALID`; no invented expiry or blanket revocation |
| Missing current purchase review or fresh payment approval | No automatic payment; earlier handoffs never supply purchase permission |
| Malformed/unrelated request and independent offline plan | No artificial revocation from unrelated invalid input; no unnecessary gate on safe planning |

Required-control records below the host boundary are synthetic. In particular,
`TARGET_MANUAL`, `native_pass` and a canned `Reply.APPROVED` exercise the code
branch only. They establish neither real traffic nor approval. The direct-path
incident's scope is a fixture host declaration, not a live detector result.

Module imports occur before `offline_only()`. The actual replay installs fail-fast
sentinels on file opens (`builtins.open`, `io.open`, `os.open`), socket creation,
DNS resolution, `subprocess.Popen`, `os.system` and `os.popen`, and verifies zero
calls afterward. These sentinels are test instrumentation, not OS/network
isolation. JSON output is emitted after the guarded calculations; no test opens a
browser, fetches a domain, runs a client or charges an account.

## C: sentence/clause review of reachable active instructions

This review reads the full relevant sections, follows SKILL's active links, and
compares the meaning of each applicable sentence with the original condition.
It is not a keyword-count test or a claim that every future model response is
mechanically verified. Source snapshots support the requirement; active guidance
supplies the Agent procedure.

| Active location and full applicable statement meaning | Original-clause assessment |
|---|---|
| SKILL start steps 5–7: PC0 precedes service contact; documents/DNS/version commands are not exceptions; unknown unsupported checks stay unknown; inventory is not PC-G1 | Missing required controls cannot be discharged by asking the client or by a successful inventory |
| SKILL workflow paragraph: `workflow_guard` is instantaneous eligibility, not isolation or restorable execution authority | Public Decision/snapshot limits agree with the code; no native promise substitutes for the gate |
| contact-and-safety capability paragraph: unsupported built-in actions require separately scoped investigation and exact authority; Agent work cannot spoof validation or bypass denial | An unsupported control is not permission to improvise automatic login/payment |
| contact-and-safety workflow-boundary paragraph: unrelated apps/restored tabs are not stopped; strict no-egress remains blocked without a tested technical boundary | A strict user goal cannot be relabeled optional merely because the implementation lacks coverage |
| contact-and-safety PC0 sentence: no web/API/auth/download/status/telemetry/documentation contact through DNS/search/version/IDE/delegated paths | Required-control uncertainty does not justify a hidden target-service test |
| contact-and-safety PC-G1 sentences: require actual target/profile/path/families/controls, list every unavailable or unmeasured requirement; inventory/assertions/synthetic tests do not close the gate; irrelevant checks excluded but strict requirements not waived | This is the active explicit non-relabeling rule. Applicability remains the host's responsibility, not an optional flag accepted by the runtime |
| contact-and-safety PC1 sentences: sufficient scoped PC-G1 plus explicit first-contact authorization, exact target/action/destinations/revision/evidence/limits, host permission | Full interview completion, a plan or an old approval cannot authorize contact |
| contact-and-safety PC-G2 and PC2: separate pre-login and post-login tests; defer the latter explicitly; login is not payment; real-path failure pauses payment and returns to diagnosis | Correct staged unknown treatment without a circular prerequisite; real direct-path conflict cannot be an acceptable purchase limitation |
| contact-and-safety existing-subscriber/phone paragraph: each target/device/path has its own preparation | A desktop result cannot waive a phone's payment-path requirements |
| contact-and-safety permissions paragraphs: question/plan/host/OS/contact/payment permissions are separate; silence/cancellation/time/default grant none; host policy wins | Callbacks and exact scopes are separate, no automatic login or purchase escalation |
| contact-and-safety reporting sentences: proposals/applied/verified separated; user reports remain reported; target/config/network/profile/version changes invalidate evidence and handoffs; withdrawal stops new requests | Supports revocation of an obsolete current grant, rather than displaying it as still open after a failed current control |
| contact-and-safety persistence sentences: saved records do not revive permission; missing prerequisites stop dependent actions while independent work may continue; phase/history retained | Rebind/resume cannot launder old passes; local guidance remains available |
| network-and-remedies evidence boundary and layered interpretation: config is not effective behavior; failure/timeout/unknown route differ; listener receipt can still route DIRECT; browser/process/protocol/family evidence has limited scope | A generic successful endpoint or failed request cannot replace a missing mandatory control; direct routing is scoped evidence, not an account-risk diagnosis |
| network-and-remedies ENV-10 paragraph: real fault cases include stop/restart/update/children/dual stack/UDP/control recovery; rule count/connectivity/failed request proves none | Unmeasured required failure-blocking scope stays unmeasured, even if another check passed |
| accounts-and-payments PC0 versus checkout: app entry/account match/tax/period/payment requirements remain deferred; do not buy gift cards to resolve uncertainty | Directly prohibits the original purchase shortcut |
| accounts-and-payments handoff/stopping paragraph: unsupported/unknown device/store/app/plan conditions block feasibility-assuming advice; smallest check first; G3 and PC2 distinct; no pay/redeem/register in preview | A ready-looking environment or route choice does not authorize buying a card or subscription |
| accounts-and-payments A1 output and A2 login steps: uncertain eligibility does not recommend buying/opening/changing region; PC-G1 and exact PC1 permission precede official verification, unauthenticated PC-G2 precedes scoped login; wrong account stops purchase | Prerequisite uncertainty is an actual stop on dependent account actions |
| accounts-and-payments B1/B2: compare conditionally; PC0 app evidence remains pending; missing device/entry/region/account prerequisite prohibits buy-card advice; actual amount and exact purchase approval are separate | Card purchase cannot be used to discover whether the intended subscription is possible |
| accounts-and-payments B3/B5: do not buy Play cards as a test; display exact checkout terms; environment approval is not purchase/redemption approval; user handles payment/secrets; cancellation stops dependent actions | Covers non-Apple purchases and preserves individual approval boundaries |
| accounts-and-payments B7: missing entry means no card purchase; pending/unknown charge means no retry/cross-channel purchase; successful login with failed application networking pauses payment and returns to path verification | No purchase to test or fix an unresolved real path |
| workflow_guard module/class/Requirements/Evidence contracts: host-reviewed applicability, current declared evidence, live separate approvals, no executor/automatic login/payment; invalidation rotates review identity | Runtime behavior supports the above Agent procedure without claiming to police a malicious host or all applications |

D-ENV §17.5 distinguishes truly optional unselected capability from a user-required
fault-blocking objective: the former may be reported as a known limit; the latter
requires insufficient-evidence/configuration status until tested. §18.5 requires
preparation plus absence of known conflict, explicitly postpones real-client
checks, and pauses payment on a later real-path problem. §18.7 records prior
contact without erasing it; §18.8 invalidates affected handoffs. D-SPEC §6.13
forbids spending money to resolve unknown prerequisites. These meanings are all
preserved; no native or external-source refresh was necessary for this L+C row.

## Reproduction and results

Run from this exact twelfth tree with UTF-8 source files:

```sh
PYTHONDONTWRITEBYTECODE=1 python -B -m unittest discover -s tests -p test_acceptance_required_controls_rebuild.py -v
PYTHONDONTWRITEBYTECODE=1 python -B tests/test_acceptance_required_controls_rebuild.py --replay
PYTHONPATH=tests PYTHONDONTWRITEBYTECODE=1 python -B -m unittest test_workflow_guard test_workflow_contact_epoch test_acceptance_boundary_rebuild test_acceptance_required_controls_rebuild -v
```

- 23 focused tests pass; 98 combined workflow/contact-epoch/prior-boundary/new
  tests pass, with no skips and no edits to existing assertions.
- The final new suite also runs against the exact frozen eleventh runtime bytes,
  preserving failures rather than changing the old tree. The recorded old-tree
  log distinguishes the discovered production defect from intermediate fixes.
- Two independent replay invocations produce byte-identical complete JSON.
- Both owned Python files pass Python 3.10 grammar parsing and current-runtime
  compilation. Full aggregate/Node/package publication checks belong to the
  composed parent batch and are not inferred from these focused results.

Artifacts retained under `/tmp/guardian-required-controls-twelfth/` include
`first-tests.log`, `failing-first-revocation.log`, `failing-first-retry.log`,
`failing-first-cancel-expiry.log`, `frozen-eleventh-regression.log`,
`focused-tests.log`, `related-tests.log`, `compile.log`, `replay.json`,
`replay-second.json`, `reproduce-retained-gate.py`,
`retained-gate-counterexample.json` and `retained-gate-fixed.json`.
The receipt supplies exact artifact digests and the owned delta against frozen
eleventh source bytes. New files are absent on that base; do not identify current
content with the local baseline Git HEAD.

## Underlying evidence pins

Pins cover runtime, executable assertions, active instructions and immutable
original conditions. This page and operational ledger are excluded to avoid hash
cycles. Historical evidence is not silently overwritten. The parent must refresh
prior accepted ENV-T79/90 workflow pins after independent re-review of this delta.

| Relative path | SHA-256 |
|---|---|
| `tests/test_acceptance_required_controls_rebuild.py` | `0f331ca6934281daa213bebdc7acecfb9278edfe67b0b9c1bc4442be19e7991d` |
| `skills/claude-guardian/scripts/workflow_guard.py` | `68aa99db78a70d0387a3901d4f3ba25a9c4dcee19fa2ff3a584706419ccfeed0` |
| `tests/test_workflow_guard.py` | `635b39b747724477efc782eeea129c818bbfb11639d2ad0a83aa4438e8ce2587` |
| `tests/test_workflow_contact_epoch.py` | `bbb4010d7d7e74b6ba2f080eae4c853ed0b239f8bf522bea365114c17dfc97fd` |
| `tests/test_acceptance_boundary_rebuild.py` | `b5604c118e9c11fea9d03c19e75efdae4acb53f7bb0df3bd2ac4db38842621fd` |
| `skills/claude-guardian/SKILL.md` | `958c27324e41d46dc2977d60db285b26994bcd5aa6691ae61263be7469765d6e` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/network-and-remedies.md` | `fd65f7c88263a1ba83496f915d28623a93ef826ef1f1cebee55c43b83cd60b4c` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `cf16e85bfbe2a9ea6a2cc51d88b9f82c85eab29248f289c3ae3990c15cda6cb9` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `docs/implementation-tracker.md` | `8056f8d999a73a66dcdb7960dd724cd9e0c7404d769b00650e6936f21703fd50` |

## Limits and recovery of this code change

This is whole-row L+C evidence within the stated workflow/host boundary. It is not
native detection of a real direct path, a certified network firewall, authenticated
user consent, universal purchase classification or evidence for full project
completion. No runtime outcome infers that a user has actually logged in, paid,
been protected from arbitrary background requests, or suffered account sanction.

Reverting this narrow code delta and its new tests/doc is a source rollback only;
it performs no user-system recovery. The prior erroneous current-gate behavior
would return, so preserve the regression evidence when reviewing any rollback.
The parent owns acceptance-ledger integration and publication; this page changes
neither original case definitions nor unrelated accepted rows.
