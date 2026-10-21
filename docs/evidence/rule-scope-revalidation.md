# Rule-scope compatibility review: ENV-T38, ENV-T39, ENV-T41, ENV-T42, ENV-T58

Date: 2026-10-21 UTC. Verification layers **L + C** for all five, dependency **A**. This is the compatibility review
that the `rule_scope_compatibility` group requires after the selector and guidance bytes changed. Source baseline: the
tree at `2b268bb` plus the uncommitted review files of this batch. The C part is an author-side reading of the current
guidance against the retained responses; it adds no new model response and no independent reviewer.

## Original requirements

From `docs/evidence/rebuild-rule-scope-guided-responses.md` (D-ENV v0.3 §12.1), unchanged in the ledger:

| ID | Scenario | Required behavior |
|---|---|---|
| ENV-T38 | Mihomo 收到 fingerprint: chrome | 识别为证书指纹字段语义不匹配；不自动改写节点 TLS 配置 |
| ENV-T39 | 网站 /21 与官方 Inbound /23 混用 | 保留流量方向；不把 Outbound 清单直接编成客户端默认目标规则 |
| ENV-T41 | 关键词 datadog/sentry/sift 命中其他业务 | 默认不产生跨业务宽泛规则，保留原有策略 |
| ENV-T42 | 某可选功能关闭或版本不使用相应域名 | 按功能门控，不强制探测/修改该依赖 |
| ENV-T58 | 新增 recommendation_pending 项尚未确认 | 不得因为 D01—D12 已接受，就把尚待评审的新端点/依赖/发布范围编译成默认 apply 动作 |

## What stays historical

The corpus of 11 model-authored responses, 22 recorded helper calls, six whole candidate triples, both mixed-CIDR
error records and the independent line-by-line review (`docs/evidence/rule-scope/`) is unchanged. Its
`SHA256SUMS`, provenance manifest, `independent-case-review.json` and reviewer data hashes still match the pins on the
historical page.

Of the 21 pins on that page, these differ today: `SKILL.md`, `references/agent-remediation.md`,
`references/network-and-remedies.md`, `scripts/agent_remediation.py`, `scripts/guardian.py`, and the two test
files `tests/rule_scope_evidence_replay.py` and `tests/test_acceptance_rule_scope_rebuild.py`. The four helpers that
produced the 22 recorded calls (`rule_source_import.py`, `config_edit_plan.py`, `rules_extension_plan.py`,
`remedy_plans.py`) and `traffic_policy.py` / `source_evidence.py` are byte-identical. The git history was squashed, so
the pinned bytes of the changed files cannot be diffed; the changes are assessed by rerunning behavior and re-reading
the guidance.

## Rerun on the current tree

- `python3 -B -m unittest discover -s tests -p test_acceptance_rule_scope_rebuild.py`: 18 tests, OK. They verify the
  immutable corpus bytes, original clauses and layers, all 22 complete results and errors, the six candidate byte
  differences, host outcomes, pending-category exclusion, the preserved IPv4 conflict and the ten separately frozen
  controls.
- `python3 -B tests/rule_scope_evidence_replay.py` twice: identical output, 87472 bytes, SHA-256
  `c8b490afb99c1a6e032cf92e6e7df9e7410a50d939be1df8bbeba1b83addfd60`. The replay reconstructs the recorded calls under
  fail-fast I/O sentinels; it generates no model prose.
- The selector change of this cycle (`75dc6fb`, unknown report members rejected at the boundary) is not exercised by
  the 22 recorded calls, which are helper calls. It is covered by `UnknownMemberRejectionTests` in
  `tests/test_agent_remediation.py` and by the cross-path matrix of `docs/evidence/input-boundary-revalidation.md`.

## Current guidance against each clause

Read on 2026-10-21 in `references/network-and-remedies.md` and `references/agent-remediation.md`:

- **ENV-T38**: "`fingerprint: chrome` 属于字段语义不匹配；其适用代理协议中的 `client-fingerprint` 才是客户端 uTLS 参数 ...
  不自动改名覆盖已有合法 `client-fingerprint`，不编造证书哈希 ... 不得靠 `skip-cert-verify`、关闭校验或安装自签根证书补救。独立规则候选须保持全部 TLS 字节不变"
  (network-and-remedies.md:61).
- **ENV-T39**: `160.79.104.0/23` and `2607:6bc0::/48` are service Inbound, `160.79.104.0/21` is platform Outbound;
  direction is relative to Anthropic; "也不能把平台 Outbound 清单编成客户端默认目标规则"; the 2026-10-15 source date is kept and a new
  exact CIDR needs independent verification (network-and-remedies.md:63; agent-remediation.md:233).
- **ENV-T41**: shared services cannot be collected by `datadog/sentry/sift` keywords or an equally cross-business wide suffix; only
  verified, explicitly chosen entries become candidates; existing rules, policy and telemetry switches are kept
  (agent-remediation.md:230).
- **ENV-T42**: a feature the user turned off stays "closed", a dependency the version does not use is "not applicable";
  they are not turned into unknown, required or blocking items (agent-remediation.md:228).
- **ENV-T58**: accepted D01—D12 directions continue; new `recommendation_pending` endpoints, dependencies and wider
  publication stay for review and enter no default probe, install or apply; "先放入默认计划再问执行许可也不合格"
  (agent-remediation.md:231).

All five statements say the same thing as the original clauses; none was weakened by the later whole-device proxy
default or the entry-order additions in `SKILL.md`.

## Assessment

The recorded helper behavior still reproduces exactly, and the current guidance carries each of the five clauses.
The retained responses remain the observed evidence for the dialogue behavior. Pass for all five within the limits
below.

## Not claimed

- No new generated assistant response under today's `SKILL.md` and references, and no independent reviewer of the
  current wording. If a later model dialogue contradicts a clause, this review does not cover it.
- No current external fact: the Inbound/Outbound ranges are the frozen 2026-10-15 source values, not a fresh check.
- No native, live-engine or effective-routing claim; candidates stay candidate-only.
- No claim for helper inputs outside the 22 recorded calls and ten controls.

## Reproduce

    python3 -B -m unittest discover -s tests -p test_acceptance_rule_scope_rebuild.py -v
    python3 -B tests/rule_scope_evidence_replay.py | sha256sum
