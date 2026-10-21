# Cloud acceptance review: T65, T71, ENV-T124

Date: 2026-10-21 UTC. Verification layers **L + C** (ENV row written `L + C`), dependency **A**. None of the three
cases had an earlier acceptance or dialogue evidence; this page is the first. Source baseline: the tree at `2b268bb`
plus the files of this batch. The C part is an author-side reading of the current guidance against deterministic
outputs; per the project owner's choice for this batch, no new model response was generated and no independent
reviewer was used.

## Original requirements

- **T65** 用户问改美国时区是不是必需防封: 显示社区结论有冲突、无可靠封禁因果，不建议改成与实际使用情况不符的时区.
- **T71** 一篇 NodeSeek 说需改时区，LinuxDo 又有相反案例: 区分社区自述与官方技术限制，不把任一贴当作封号原因或成功率证明.
- **ENV-T124** 附件合成样例自检通过: 只报告 contract fixture 的验证范围；不得据此关闭平台 VAL 或宣传全机已测.

## Evidence produced

`tests/test_acceptance_cloud_guidance.py` (new, 6 tests). Expectations are written from the requirement text, not
copied from output. `--replay` output is byte-identical across two runs, 628 bytes, SHA-256
`1b95670ed8588ad09337fb38917f12a4391cfa55100149d765598a749973f816`.

- **Selector (T65, T71).** `agent_remediation.select` with only `EGRESS_TIMEZONE_DIFFERENCE` returns the single action
  `keep` (kind `no_change`, ENV-04), `target_mutation_supported=false`, `agent_fallback=none`, `changes=[]`,
  `authority=none`, `completion=no_repair_performed`; no `clock` action appears. With an explicit
  `TIMEZONE_LANGUAGE_GOAL` the `clock` action is chosen, its steps require a confirmed user goal and user
  confirmation and state "不按出口地区改时区"; still no changes and no environment pass.
- **Guidance anchors, asserted verbatim.** `SKILL.md` 始终保护: 不编造免封概率…时区伪装收益, 出口位置不代表服务资格;
  `agent-remediation.md`: "时区仅与出口不同 | 保留当前配置 | no_change | 不制造修改目标" and 不按出口地区改时区;
  `evidence-policy.md`: C03 语言/时区因果 kept only as a historical claim index, 社区案例不证明总体概率, F01—F07 community
  clues not used as permission/probability/platform validation, official policy limited to its product/time/scope,
  promotional material only a lead; `incidents-and-integrations.md`: 证据冲突时并列，不删除反例.
- **Synthetic scope (ENV-T124).** The real `guardian.py analyze` CLI on `tests/fixtures/proxy-port-conflict.json`
  exits 0 with `record_kind=synthetic_example`, `limits.native_platform_validation=not_run`,
  `environment_pass_claim=false`, `account_safety_guarantee=false`; the real `status_dashboard.py` renders the
  page with "合成示例，不是你的设备检测结果". Selector outputs keep `native_acceptance=not_established`,
  `environment_pass=false`.

## Assessment against the original clauses

- **T65**: no modification target is created from an egress/timezone difference, and an explicit timezone request is
  never tied to the egress region. 显示社区结论有冲突 is the response-side half: the guidance forbids a ban probability
  and keeps community claims as experience with counter-examples side by side (read by the author; no generated reply).
- **T71**: guidance separates community self-reports from official policy and version-scoped technical statements and
  adopts no post as a cause or success-rate proof. Pass at L + C within the limits below.
- **ENV-T124**: only the fixture scope is reported, with platform validation `not_run` and no environment-pass or
  whole-machine claim.

## Not claimed

- No generated assistant response and no independent reviewer. T65's "显示…有冲突" and T71's "区分" rest on guidance
  text, not on an observed answer.
- No claim about any real ban mechanism, the real effect of timezone, or the content of the NodeSeek/LinuxDo posts;
  the repository states none and this page adds none.
- ENV-T124 does not verify the 56-case attachment suite named in the main spec, only the selected fixture and the
  scope fields; no native platform validation is closed here.
- No device, account, network, contact or authorization.

## Related case not registered

ENV-T43 (E08 官方域名清单更新: 登记版本/日期并重算差异) stays pending. The runtime has no domain-list diff; the source
binding records `verified_at`, `version_scope` and an expected hash but, per the guidance, does not confirm
freshness. Recomputing a difference needs the current official page (X layer) and a diff function that does not exist.

## Reproduce

    python3 -B -m unittest tests.test_acceptance_cloud_guidance
    python3 -B tests/test_acceptance_cloud_guidance.py --replay | sha256sum
