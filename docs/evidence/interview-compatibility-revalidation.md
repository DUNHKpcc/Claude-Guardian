# Subscription and interview compatibility review: T31, T36, T38, T46, T48, T49, T54, T74, T75, T76, T77, T78, T79, T80, T83

Date: 2026-10-21 UTC. Verification layers **L + C**, dependency **A** (T79 also P). This is the compatibility review
that the `subscription_and_interview_compatibility` group requires after the shared interview runtime and its
compatibility bridge changed. Source baseline: the tree at `2b268bb` plus the review files of this batch. The C part
keeps the retained observed responses and reviews, and adds an author-side reading of the current guidance; it
generates no new model response and has no independent reviewer.

## What stays historical

Every original observed dialogue, normalized replay record and independent review named in the ledger's
`historical_evidence` for these 15 cases is unchanged: `rebuild-history-and-pause.md` (T31),
`subscription-boundaries/CURRENT-REVIEW.md` (T36, T38, T46, T54; the failed T38 v1 stays retained and v2 is the
reviewed one), `rebuild-task-scope-cases.md` (T48, T78), `rebuild-mobile-route.md` (T49, T83),
`rebuild-intake-cases.md` (T74), `rebuild-experience-and-subscription.md` (T75, T79),
`rebuild-subscription-original-cases.md` (T76), `rebuild-upgrade-conflict-cases.md` (T77, T80). The earlier batch-33
preservation record (`batch33-subscription-preservation/`) is also unchanged; it covered the then-existing accepted
cases and is not reused as a current approval. The pinned bytes of the runtime and guides at the time cannot be diffed
(squashed history), so current behavior is assessed by rerunning the deterministic traces and re-reading today's
guidance.

## Rerun on the current tree

| Suite | Cases | Result |
|---|---|---|
| `test_acceptance_history_pause` | T31 | 6 tests OK; replay twice identical, 424,778 bytes, SHA-256 prefix `9270bdbb58accb97`, equal to the recorded replay |
| `test_acceptance_subscription_boundaries` | T36, T38, T46, T54 | 31 tests OK (this suite has no replay mode) |
| `test_acceptance_task_scope_rebuild` | T48, T78 | 15 tests OK; replay prefix `99c11ee14d12e3f0`, equal to the recorded replay |
| `test_acceptance_mobile_route` | T49, T83 | 6 tests OK; replay prefix `927dd88cc3d9fc62`, 1,663,404 bytes, equal to the recorded replay |
| `test_acceptance_intake_rebuild` | T74 | 15 tests OK; replay prefix `d6787994630ceb51`, equal to the recorded replay |
| `test_acceptance_experience_status` | T75, T79 | 6 tests OK; replay prefix `b539ab28356fdea5`, 1,685,973 bytes, equal to the recorded replay |
| `test_acceptance_subscription_original` | T76 | 14 tests OK; replay prefix `46a3a2ab002b14f5`, 4,649,083 bytes, equal to the recorded replay |
| `test_acceptance_subscription_upgrade_conflict` | T77, T80 | 10 tests OK (no replay mode) |

Each replay was produced twice with byte-identical output. A pinned replay hash that is unchanged says the public
state and question output of those traces did not move; the assessment below rests on reading each clause against the
current guidance, not on that equality.

## Current guidance against each case

`SKILL.md` and `references/` as read on 2026-10-21:

| Case | Retained expectation | Current guidance anchor |
|---|---|---|
| T31 | 当前状态和历史经历分开记录，历史事实不自动改变方案 | SKILL 开始方式 item 2: 已报告过去封禁而设备经历缺失时先问 Q-D01，"不推定当前设备也有该经历" |
| T36 | 仅回答"有 Apple"时区分设备、Apple 账户和商店地区 | accounts-and-payments.md: "Apple 设备、可登录账户、商店地区、卡种和内购入口分别核实"; storefront comes from the user's own App Store settings, not from the iCloud page language, device sales region or proxy address |
| T38 | 有 iPhone 但无可登录 Apple ID: 记录付款前提缺失 | same section: 设备 / 账户 / 卡片 are separate checks; "Mac 可兑换的事实不证明目标内购入口可用" |
| T46 | 拒绝提供资格字段: 记录拒绝与阻断范围，不猜测资格、不强迫回答 | accounts-and-payments.md: 用户不愿提供非必要信息就标 unknown 并给条件式结果; intake.md: unknown / declined / deferred keep the unresolved state and end automatic follow-up |
| T48 | 凭据泄露/紧急停用: 最小必要分流优先，其余延期 | SKILL item 2 "紧急事故优先"; intake.md G1 has a distinct emergency-deferred outcome |
| T49 | 选择 VPS 使用但想以手机内购支付: 运行环境与付款设备分开 | contact-and-safety.md: "Phones used for payment need their own preparation; a Mac check cannot pass a phone"; SKILL item 3: 拥有 VPS 不等于选择远程工作区 |
| T54 | 只要方案草案但有关键未知: 条件式/部分草案并列缺口 | accounts-and-payments.md conditional result for unwilling or unknown facts; intake.md G1 "partial" is a distinct outcome; no purchase or high-impact instruction |
| T74 | 明确第一次准备订阅: 问 Q-C08，不问 Q-C07、Q-P02、Q-A06 | SKILL item 4: "Q-C07 永久停用"，"首次订阅无实际冲突时跳过旧套餐/旧渠道题" |
| T75 | 技术老手仍是 first_subscription | SKILL item 2: "技术熟练度不代表付费状态" |
| T76 | 以前订阅过且已到期，准备重订: returning_subscription，问 Q-C08 | intake.md: "以前订阅过，已到期，准备重订 Pro" records `returning_subscription` and keeps the selected Q-C08; no current entitlement is manufactured |
| T77 | 已有订阅明确升级: 不重问开场 | intake.md 已有订阅的明确升级: reuse the opening and task, ask only Q-P02 current plan / original channel and Q-C08 target plan |
| T78 | 只说"老手/用过": 订阅保持 unknown，澄清 Q-J02 | SKILL item 2: "技术熟练度不代表付费状态" |
| T79 | 不懂技术但已有付费套餐: 已有订阅分支，保留新手讲解深度 | same sentence; intake.md existing_subscription branch (Q-J01=existing_subscriber) |
| T80 | 自述首次订阅但购买页显示已有订阅或续费: 标记实际冲突，只澄清相关状态 | intake.md: "只有实际矛盾才开启订阅复核 ... 先保留两方来源和观察时间，只问该提示是否对应这次目标及相关订阅状态" |
| T83 | 首次订阅选择 Apple/Google 内购: 不重问旧订阅 | accounts-and-payments.md Apple branch (device, account, card, in-app entry; PC0 asks non-Claude device and store conditions, the actual in-app entry is after PC1); SKILL item 4 skip rule |

The dated environment-entry order does not change any of these: it applies once an environment task starts, and the
text states that pure subscription explanations are not forced through an environment questionnaire
("纯订阅说明不强迫环境问卷", intake.md) and that urgent triage keeps its priority.

## Assessment

The deterministic traces still reproduce the retained expectations, the retained observed responses stay the
dialogue evidence, and the current guidance contains the matching constraint for each case. Pass for all 15 within
the limits below.

## Not claimed

- No new generated assistant response under today's guidance and no independent reviewer of the current wording.
- No natural-language parsing: the logic traces consume normalized facts supplied by the host.
- No native Mac, Windows, iPhone or Apple/Google account behavior, no real entitlement, price, catalog or payment
  authorization, and no live purchase page.
- T36/T38/T46/T54 keep their historical limit: the failed T38 v1 stays retained; helper controls are labeled offline.
- T77/T80 have no replay hash to compare; their evidence is the 10 passing regressions plus the retained trajectories.

## Reproduce

    for t in history_pause subscription_boundaries task_scope_rebuild mobile_route intake_rebuild experience_status subscription_original subscription_upgrade_conflict; do
      PYTHONPATH=tests python3 -B -m unittest test_acceptance_$t; done
    PYTHONPATH=tests python3 -B tests/test_acceptance_<suite>.py --replay | sha256sum   # for suites with replay
