# Cloud acceptance review: T14, T30, T32, T52, T56, T68, ENV-T02, ENV-T36, ENV-T92, ENV-T96

Date: 2026-10-21 UTC. Verification layers **L + C** (ENV rows written `L + C`), dependency **A**. None of these ten
cases had an earlier acceptance or dialogue evidence; this page is the first. Source baseline: the tree at `2b268bb`
plus the files of this batch. The C part is an author-side reading of the current guidance against the
deterministic outputs; per the project owner's choice for this batch, no new model response was generated and no
independent reviewer was used.

## Evidence produced

`tests/test_acceptance_cloud_flow.py` (new, 13 tests) drives the real `interview_flow` API and, for T68, the real
`guardian.py analyze` CLI with fixed synthetic host facts, under fail-fast sentinels on `builtins.open`, `io.open`,
`os.open`, `socket.socket`, `subprocess.Popen` and `os.system` (the T68 CLI run is outside the sentinels because it is
a subprocess). The expectations are written in the test from the original requirement text, not copied from output.
`--replay` prints the actual observations: two runs are byte-identical, 5,975 bytes, SHA-256
`730e1ff2181325fca7c0cecc72b58e5271f8d129d09292355ecab14b7c5c929d`. The same module also holds checks for T41 and T85
(see "Related checks not registered").

Three first-draft expectations were corrected after reading the real public contract; none relaxed an original
clause: the retired Q-C07 keeps a tombstone prompt ("Retired; never collect account ownership") and is rejected as a
fact rather than being absent from the prompt table; a suspension claim surfaces through the triage question Q-H01
instead of a stored context flag; a deferred branch stays listed with reason `branch_deferred` instead of leaving the
active set.

## Cases

| Case | Original requirement | Observed (replay) | Guidance anchor read 2026-10-21 |
|---|---|---|---|
| T14 | 用户只要 spec: 不运行登录、支付、系统修改或清理脚本 | `Q-Z01=plan_only`: G2 `blocked` with `conditional_plan_only`, G3 `blocked`, phase PC0, no persistence consent, the next question does not require action authorization | SKILL: "默认 CLI 和访谈 assessment 不执行清理"; item 5 PC0 (no client launch, no login); item 6 no ad-hoc commands around gates |
| T30 | 一句话提供系统、方案、账号与付款偏好: 同时吸收全部字段，只追问缺口 | five facts (J01, C02, C08, C04, P06) stored in one call; none unresolved; first gap Q-C01; none of the five is ever asked while the rest of the flow is drained; gates closed | intake.md: "Absorb all useful facts in a reply, skip known/not-applicable items"; SKILL item 2 "先复用已有事实，再补缺口" |
| T32 | 用户称"被封"实为卡片拒付: 先辨识对象/提示，转付款诊断，不能定为 Claude 账号停用 | the claim `current_suspension` yields G1 `emergency_deferred`, stage I0 and the next question Q-H01 ("被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？"); after the object is recorded as `payment_card`, C03 corrected and W03=`card_declined`, G1 is no longer emergency-deferred and the task is `billing_issue` | SKILL item 2 "紧急事故优先"; accounts-and-payments.md asks card category, region, truthful billing details and "relevant decline symptoms" |
| T52 | 历史画像与当前答案冲突: 先区分是否不同设备/账号或时点，不盲目采用旧记忆或静默覆盖 | an answer for another device and one with the wrong subject role are refused; a host-flagged conflict stays `conflict` with the newer source and asks the clarification once; a new device keeps only the subscription fact (`Q-J01`), a new account keeps nothing; the original state object is not mutated | intake.md: "同账号换设备可保留有效套餐事实，新账号不继承"; states include `conflict`/`stale`; "Old Q-C08 answers must not silently become new target-plan answers" |
| T56 | 用整个问题库计算"完成率": 只算适用分支覆盖，不要求填未选路线，不使用问卷分数当免封评分 | the assessment has no score field; G1 holds only `status` and `unresolved_fields`; local route adds Q-L01/Q-L04 and a VPS route adds none; a deferred payment branch shows reason `branch_deferred` and is not counted as unasked | intake.md G1: "every applicable branch handled; unknowns visible. Complete, partial, paused, blocked, or emergency-deferred are distinct"; SKILL 始终保护 "不编造免封概率" |
| T68 | 本机 Linux 用户启动首次访谈: 明确本机平台首批未覆盖，不假装支持 Linux 本机 | analyzer with `declared_os=linux`, native local: exit 2, `blocked`, `UNSUPPORTED_PRODUCT_OR_VERSION`, gate closed; the macOS control completes. Q-C02 asks only Mac or Windows | routes-and-platforms.md: "Scope: macOS and Windows 10/11"; a Linux remote server "does not extend the native desktop collector matrix"; SKILL item 3 offers VM/VPS as separate plans |
| ENV-T02 | 用户已提供系统/Clash 模式/旧设备信息: 复用全部已知答案，只问未绑定设备的缺口 | device A: J01, C02, N01, N02 never asked again; moving to device B keeps J01 and the `active_reported` subscription, drops the device-bound answers, and starts at Q-C02 | same intake.md sentence on same-account device change; SKILL item 2 |
| ENV-T36 | 首次订阅者在环境阶段: 不恢复账号归属问项，不重复问已有订阅/旧套餐 | in an `environment` task with `first_subscription`, none of Q-C07, Q-P02, Q-A06, Q-C11, Q-C13 is listed or asked and Q-J01 is not repeated | SKILL item 4 "首次订阅无实际冲突时跳过旧套餐/旧渠道题"; "Q-C07 永久停用" |
| ENV-T92 | 旧问题与本轮前置规则同时加载: Q-C07 不复活；首次订阅不问旧权益；当前是否正常仅自述，不提前启动 Claude 求证 | a saved state carrying a Q-C07 fact is refused; Q-C07 is absent from the state schema and cannot be recorded (`Unknown or retired question ID`); P02/A06 not listed; the login fact is `reported`, never `observed`; gates closed | SKILL item 4 and item 5 (PC0: no client run, `claude --version`, or delegated Claude tool) |
| ENV-T96 | 已提供订阅阶段、OS、路线与套餐: 复用已有事实，只请求缺少的检查授权，不重问 Q-J01/Q-C02/Q-C08 或恢复 Q-C07 | with J01, C02, C05, C08 supplied none of them (nor Q-C07) is asked during the whole drain; the separate check-scope question Q-Z01 is asked and recorded as `plan_only`; G3 stays blocked, PC0 | intake.md absorb-and-skip rule; contact-and-safety.md keeps question answers, plan acceptance and authorization distinct |

## Assessment

Each case's retained expectation holds in the actual output, and the current guidance contains the matching constraint.
Pass for all ten at their original layers (L + C) within the limits below.

## Not claimed

- No generated assistant response and no independent reviewer: C rests on the guidance text and the deterministic
  behavior, which is thinner than the observed-dialogue evidence of the restored cases.
- No natural-language parsing. The flow consumes normalized facts; the host must supply them, flag conflicts and
  corrections (T52, T32), and phrase questions.
- T52 known limit, asserted in the test so it cannot change unnoticed: on the same target a newer answer replaces the
  stored value unless the host marks it `conflict`.
- ENV-T96 and ENV-T02 do not claim a minimal question list: other genuinely missing facts (task, network, protection
  scope) are still asked; the claim is only that supplied facts are not asked again.
- T68 shows the analyzer blocks a declared Linux local target; it does not provide Linux guidance content itself.
- No native device, real account, real purchase, contact or authorization.

## Related checks not registered

The module also exercises T41 (old-billing questions open only on an actual subscription conflict: none without a
conflict, Q-P02 first with one, G2 blocked) and T85 (an undecided plan is kept as `undecided` with the "未决定先按用途和预算比较"
prompt, a budget question is available, no old-entitlement or gift-card-purchase question appears). Both original rows
carry the X layer (current external facts), which this page does not establish, so they stay pending.

## Reproduce

    PYTHONPATH=tests python3 -B -m unittest test_acceptance_cloud_flow
    PYTHONPATH=tests python3 -B tests/test_acceptance_cloud_flow.py --replay | sha256sum
