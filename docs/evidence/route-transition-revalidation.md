# Route-transition compatibility review: T19, T22, T25, T26, T33, T34, T53

Date: 2026-10-21 UTC. Verification layers **L + C**, dependency **A**. This is the compatibility review that the
`route_transition` group requires after route choice, withdrawal and resume behavior changed and the dated
environment-entry requirement (PRODUCT-ENTRY-20261019) was added. Source baseline: the tree at `2b268bb` plus the
review files of this batch. The C part keeps the retained observed responses and adds an author-side reading of the
current guidance; it generates no new model response and has no independent reviewer.

## Original requirements (unchanged in the ledger)

| ID | Scenario | Required behavior |
|---|---|---|
| T19 | 未指定部署方案，也无明确远端任务 | 本机仅为默认候选，先询问选择／接受建议；未答时 route 保持 unconfirmed，不是已选本机 |
| T22 | L4 只处理本机 Code | 留在 `R-LOCAL`，缩减基础解释，不自动推荐 VM/VPS 迁移 |
| T25 | 本机出现错误或账号受限 | 先在原方案进行专项诊断，不自动购买 VPS、重建 VM 或迁移账号 |
| T26 | 用户仅提到有 VPS 或装过 VM | 只记资产信息；主动询问实际目标和方案，不把资产当选择，也不静默开始本机部署 |
| T33 | 用户不懂 VM/VPS 区别 | 给简短比较，允许接受本机建议；不进行术语考试，不把不知道当选择 |
| T34 | 方案题未回答或用户跳过 | 未答与跳过都不选择本机；保留 unconfirmed，只允许受限比较／初步建议 |
| T53 | 用户愿意按本机默认建议进行 | 明确接受后才确认本机；只问一次，保存 accepted_default，不变成 explicit 选择 |

## What stays historical

All retained observed responses and their independent reviews are unchanged and remain the ledger's
`historical_evidence`: the T19 clause review in `rebuild-route-cases.md`; seven responses for T22/T25
(`local-incident-v1`); nine responses for T26/T33 (`asset-route-v1`); the T34 trajectories in
`rebuild-task-scope-cases.md`; the T53 trace in `rebuild-intake-cases.md`. They were captured on 2026-10-18/19 under
earlier guides. The pinned bytes of the guides and runtime at that time cannot be diffed (squashed history), so the
current behavior is assessed by rerunning the deterministic traces and re-reading today's guidance.

## Rerun on the current tree

| Evidence | Result |
|---|---|
| `test_acceptance_routes_rebuild` (T19 and the T20/T21/T24 siblings) | 6 tests OK; complete `--replay` twice identical, 61288 bytes, SHA-256 `dd128334df685184abf60fa6c27f24bfed166aca2917ccaea3885768f4bc552f`, equal to the last recorded replay on the historical page |
| `test_acceptance_local_incident_cases` (T22/T25 logic) | 9 tests OK; replay deterministic (two identical runs, 1,080,546 bytes) |
| `test_acceptance_local_incident_evidence`, `test_acceptance_asset_route_evidence` | 31 integrity and privacy tests OK |
| `test_acceptance_asset_route_cases` (T26/T33 logic) | 31 tests OK; replay deterministic (309,833 bytes) |
| `test_acceptance_task_scope_rebuild` (T34 with T43/T48/T78) | 15 tests OK; replay twice identical, equal to the recorded SHA-256 prefix `99c11ee14d12e3f0...` |
| `test_acceptance_intake_rebuild` (T53 with T74/T81) | 15 tests OK; replay twice identical, equal to the recorded SHA-256 prefix `d6787994630ceb51...` |

Replays for T22/T25 and T26/T33 were not hash-pinned by their historical pages, so for those two the evidence is the
passing logic regressions against the frozen fixtures, not a hash comparison. The replay hashes that were pinned
are unchanged, which says the public state and question output of these traces did not move; the assessment below
rests on reading each clause, not on that equality.

## Current observed trace values (T19)

From the current replay: initial `route=local`, `route_selection_basis=default_proposal`, next question Q-C05 with the
prompt "用本机、虚拟机、VPS，还是先比较？本机默认建议。" and no route questions; after the question is shown without an
answer, and after an `unknown` answer, the route stays `default_proposal` with no next question and no route
questions; after an explicit acceptance, `route_selection_basis=accepted_default`, the next question is Q-L01 and the
route questions are `[Q-L01, Q-L04]`. This is the same table the historical page recorded.

## Current guidance against the clauses

`SKILL.md` as read on 2026-10-21:

- 开始方式 item 3: "本机是默认建议，但要问用户接受本机、选择 VM/VPS，还是先比较。三者是独立方案，不是升级顺序。已明确的目标优先；拥有 VPS 不等于选择远程工作区。"
  This carries T19, T26, T33 and T53.
- 环境入口顺序 (2026-10-19): "未选、比较、拒绝、撤回、冲突、陈旧路线只做访谈和解释，不启动目标检查；本机默认建议必须得到明确接受。拥有 VPS 不等于选择 VPS，作为出口的 VPS 不会把本机运行路线变成 VPS。"
  This carries T19, T26, T33, T34 (not selected or comparing means interview and explanation only) and T53 (explicit
  acceptance required, and recorded as acceptance of the default).
- 开始方式 item 2: "紧急事故优先" and the PC0 rule in item 5 carry T25 (diagnose first, no contact or purchase).
- 环境入口顺序: "路线／资源改变必须使旧适用性和计划失效 ... 既有精确恢复义务仍按原回执、目标、保护和本次批准处理，不被新问卷阻断。"
  A change of route invalidates old applicability instead of silently migrating, which fits T22 and T25 (no
  automatic VM/VPS migration).

The dated entry requirement orders route choice before environment inspection. It does not add a question to any of
the seven retained trajectories: the route question is still asked once, and an unanswered, unknown or deferred answer
still leaves the route unconfirmed with inspection not started. No clause is weakened.

## Assessment

- T19, T34, T53: the replayed state and question sequences match the retained expectations and the current guidance
  requires explicit acceptance. Pass.
- T22, T25, T26, T33: the retained observed responses stay the dialogue evidence; the logic regressions for route
  retention, asset envelopes, purpose-before-route, incident priority and blocked action gates pass; the current guidance
  contains the same constraints. Pass.

## Not claimed

- No new generated assistant response under today's `SKILL.md`, and no independent reviewer of the current wording.
- No natural-language parsing: the logic traces consume normalized facts supplied by the host.
- The retained responses are fictional, shared-filesystem, instruction-limited collections and sample only the
  recorded prompts; the T26 route-question gap noted in the historical page stays as recorded.
- No native device, real service state, official support procedure, deployed VM or VPS, or cleanup/recovery claim.

## Reproduce

    for t in routes_rebuild local_incident_cases asset_route_cases task_scope_rebuild intake_rebuild; do
      PYTHONPATH=tests python3 -B -m unittest test_acceptance_$t; PYTHONPATH=tests python3 -B tests/test_acceptance_$t.py --replay | sha256sum; done
    PYTHONPATH=tests python3 -B -m unittest test_acceptance_local_incident_evidence test_acceptance_asset_route_evidence
