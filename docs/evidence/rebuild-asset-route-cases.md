# T26/T33 — Asset mentions and beginner route choice

Reviewed on 2026-10-19 under the unchanged original **L+C** layers:

- **T26 — 用户仅提到有 VPS 或装过 VM:** 只记资产信息；主动询问实际目标和方案，不把资产当选择，也不静默开始本机部署
- **T33 — 用户不懂 VM/VPS 区别:** 给简短比较，允许接受本机建议；不进行术语考试，不把不知道当选择

The [original design](../../skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md) and [tracker layers](../implementation-tracker.md) remain verbatim. Only T26/T33 receive this new bounded acceptance; the original 218-row identity remains `84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`.

## Observed responses and preserved coverage history

The [public dialogue projection](asset-route-v1/dialogues-projection-public.json) retains nine actual captured synthetic responses, unchanged, across four conversations. The independent [whole-response review](asset-route-v1/final-semantic-review.json) and [summary](asset-route-v1/final-semantic-review.md) support the complete original clauses within these sampled cases and separate normalized tests. They do not claim a single end-to-end integrated conversation or generalize to unseen outputs.

The collection was adaptive, in three stages, not nine replies frozen together up front:

1. **Original six, frozen 01:08:30.769218 UTC.** The first VPS and old-VM conversations each have two replies. They preserve assets/history without selecting a route, ask about actual purpose, and respect deferred choices. Their route-question coverage remains **partial**. The third conversation gives a short local/VM/VPS comparison, asks whether to accept the local recommendation and acknowledges it only after explicit acceptance. T33 is supported in that observed sequence without a terminology exam or treating ignorance as consent
2. **Later two, frozen 01:13:48.926246 UTC.** Each original asset conversation receives a continuation after review of the first six. More specific purposes lead to project-type or material-type questions, with the route still unchosen; neither response asks for a route choice. The T26 route-question gap remains **partial**. Earlier deferral was not clearly withdrawn, so the review does not invent an arbitrary turn-count failure. Separate retrospective source/tool exchanges remained in these two contexts before continuation
3. **Fresh ninth, frozen 01:16:17.577745 UTC.** A new independent context receives a fully specified writing/summary goal and no earlier choice deferral. Its user input explicitly says that the VPS is an asset, not a route choice. The response keeps local as a proposal, protects the existing website, compares the routes and asks whether to accept the local browser direction or keep comparing. This supplies observed route questioning for that input; its explicit asset disclaimer cannot replace the first conversations' ordinary asset mentions, and it does not backfill route questions into the earlier eight replies

The three freeze times are on 2026-10-19. Follow-ups were revealed sequentially. The original six, later two, fresh ninth and earlier partial-coverage conclusions are all retained in the final projection/review; no response was rewritten, replaced or rerun to improve its result.

## Separate normalized logic and the narrow correction

The [fixture](../../tests/fixtures/acceptance-asset-route-cases.json) and [31 regressions](../../tests/test_acceptance_asset_route_cases.py) independently check complete asset envelopes, purpose-before-route questions, goal-known route questions, unconfirmed/unknown/declined/deferred outcomes, comparison followed by an actual local proposal and explicit acceptance, blocked action/contact gates, source/time preservation and immutable replay. Authored fixture wording is an example, not generated dialogue.

These captured dialogues did not report invoking the product helper. The normalized APIs accept host-extracted facts; they do not parse user prose or generate these replies. Comparison wording remains the host's obligation. Mac/Windows labels are synthetic context, not native execution. Pure API I/O sentinels exclude initial source and fixture loading and are not an operating-system sandbox.

The independent review ran 31 candidate tests successfully, retained five failures in the same 31 tests against the frozen predecessor, and passed 293 related interview tests. The five failures expose nested-dictionary, nested-list, batch-last-item, reverse returned-value aliasing and live-state/serialized-record divergence. The sole runtime correction copies the incoming fact value with `deepcopy(value)`; the candidate runtime is `9f5237846756759a90e907eebe096f9263c0d938e78aecf4173fafb3912ede25`, predecessor `691aa0b634ba7ff1d26d3d13a3a9c58a6e43924047c63338b41b832529e3ffa9`. Ordinary guidance is unchanged. Final aggregate regression and prior-source compatibility are separate integration gates; the dialogue verdict does not replace them.

## Provenance, privacy and limits

All subscription, device, asset, project and service facts are fictional user reports. Source separation was instruction-limited on a shared filesystem, with ambient platform instructions and tools; it was not physical isolation. Source reading and absence of helper/network/device operations are retrospective responder reports, not independent raw tool-event exports. The old-VM responder reported a combined read truncated by **4,620 tokens** and subsequent rereads covering the gap. Complete reading remains responder-reported; whole-file hashes alone do not prove it. The fresh context's audit was requested after its response had been captured.

The [manifest](asset-route-v1/evidence-manifest.json) inventories the three original public artifacts, source/logic hashes, all nine input/output hashes, three-stage chronology and bounded claims. [Integrity/privacy regressions](../../tests/test_acceptance_asset_route_evidence.py) check unchanged bytes, original clauses/layers, source identity, timeline and schema, and reject altered responses, inputs, metadata and private-path injection. These checks preserve reviewed records; they do not rerun or generate model output. Relevant source drift requires renewed semantic review, not automatic hash refresh.

No native device, deployed model, installed-package integration, live network/service eligibility, persistent conversation storage or real-operation authorization is established. Evidence does not prove unseen responses, runtime enforcement of all natural-language behavior or whole-project completion. The public packet contains synthetic dialogue, project hashes and review conclusions without private execution paths, identifiers or raw private records. This evidence and its tests remain project-only, outside the installed 63-file Skill package.

Run the scoped checks from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_acceptance_asset_route*.py' -v
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_acceptance_rebuild_ledger.py -v
```
