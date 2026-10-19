# T22/T25 — Local Code scope and targeted incident diagnosis

Reviewed on 2026-10-19 under the unchanged original **L+C** layers:

- **T22 — L4 只处理本机 Code:** 留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移
- **T25 — 本机出现错误或账号受限:** 先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号

The [original design rows](../../skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md) and [tracker layers](../implementation-tracker.md) are preserved verbatim. Only T22/T25 receive new acceptance; the original 218-row identity remains `84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`.

## Observed responses and independent review

The [public dialogue projection](local-incident-v1/dialogues-projection-public.json) retains seven actual assistant responses, unchanged, with frozen synthetic user turns supplied sequentially across three conversations. The [independent review](local-incident-v1/independent-review.md) considers every complete response against all original clauses and relevant active guidance:

- **expert-local-code, two turns (T22):** a compact local-terminal difference checklist preserves the chosen route and expert depth; a later request expands only two named topics. Neither response proposes VM/VPS migration
- **local-proxy-error, three turns (T25):** diagnose the reported 403's response source on the original local route, then the reported local CONNECT policy denial. Unknown rule/upstream status and declined further logs stay unknown; the next step remains a bounded future local inspection, not a purchase, rebuild, account migration or unapproved repair
- **current-restriction, two turns (T25):** preserve work and existing evidence, distinguish the notice's observation time from suspension onset, and prepare a minimal incident summary. The cause and current official process remain unknown; no environment migration or local cleanup is presented as a service-side suspension remedy

All device, account, project and log facts are fictional user reports. They are not verified facts about an actual user or machine. The public projection and review contain no private execution metadata or raw private records.

## Separate normalized logic evidence

[The synthetic fixture](../../tests/fixtures/acceptance-local-incident-cases.json) and [nine logic regressions](../../tests/test_acceptance_local_incident_cases.py) check exact state/question/assessment behavior: local route and explanation-depth retention, depth-only changes, incident priority, preserved facts and unknown/declined outcomes, deferred ordinary gaps, blocked action gates, persistence/export permission, no inferred resolution, and stable replays.

The helper was **not invoked in these observed conversations**. It consumes normalized host facts and neither parses the synthetic user prose nor generates these responses. Its Mac/Windows labels and identity-review control do not establish Windows dialogue/native coverage or accept T04. No runtime change was necessary. API I/O sentinels are not an OS sandbox; source/fixture loading precedes the sentinel boundary.

## Provenance, integrity and limits

Source reading is responder-reported from retained records, not an independently exported complete tool transcript. The source-access restriction was instruction-enforced, not physical/process isolation. One source-read result omitted **329 tokens of cleanup material**; that text was not reread, and its exact omitted bytes are not established. Whole-file hashes do not prove every section was read. The independent review found the omission non-material to these two rows because relevant route/incident guidance was available and no cleanup operation was proposed; no cleanup case is accepted.

The [manifest](local-incident-v1/evidence-manifest.json) pins the two unchanged public artifacts, original design/tracker identity, active guidance, logic evidence, exact input/response hashes and these limits. [Integrity/privacy regressions](../../tests/test_acceptance_local_incident_evidence.py) pin the manifest and this page, check the seven-turn structure and source correspondence, and reject altered input/output, changed boundaries, extra metadata and private-path injection. These tests preserve reviewed evidence; **they do not rerun or generate model output**. Relevant source drift requires renewed semantic review, not merely refreshed hashes.

Acceptance is limited to the recorded original T22/T25 L+C scenarios. No native device, current account/service state, official support procedure, real client/proxy behavior, IPv4 enforcement, network isolation, repair or recovery was verified. Seven observed outputs do not guarantee other prompts or future stochastic responses. No additional N/X/R condition is imposed on these unchanged rows. Evidence and tests are outside the unchanged installed Skill package.

Run the scoped checks from the repository root:

```sh
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p 'test_acceptance_local_incident*.py' -v
PYTHONDONTWRITEBYTECODE=1 python -m unittest discover -s tests -p test_acceptance_rebuild_ledger.py -v
```
