# Entry and environment intake compatibility review: T01, T02, T29, T43, T57, T81, T84

Date: 2026-10-21 UTC. Verification layers **L + C**, dependency **A**. This is the compatibility review that the
`entry_and_environment_intake` group requires after environment-entry ordering and readiness affected intake and
environment-task integration. Source baseline: the tree at `2b268bb` plus the review files of this batch. The C part
keeps the retained responses and reviews and adds an author-side reading of the current guidance; it generates no new
model response and has no independent reviewer.

## Original requirements (unchanged in the ledger)

| ID | Scenario | Required behavior |
|---|---|---|
| T01 | L0 准备订阅用于网页写作 | 先分首次/重订/已有订阅；问目标套餐和相关前提，本机默认建议；不询问账号归属，不推荐无关 VPS/企业开户/脚本 |
| T02 | L4 直接提供完整环境 | 复用信息，不反复问基础问题；仍保留必要授权 |
| T29 | 完整新用户首次进入且未给环境 | 第一问订阅阶段，随后系统/目标套餐/账号经历/方案；不直接给安装付款教程，不通问已有权益 |
| T43 | 开场明确已有订阅，只查本机环境 | 不问新目标套餐或支付渠道；记录本次未处理购买，不将其当成订阅准备默认场景 |
| T57 | 订阅阶段后，电脑系统仍未知 | 系统题仅 Mac/Windows（另有手机/未知出口）；不把系统题置于已明确的新入口之前，也没有长平台问卷 |
| T81 | 一句话说"第一次开通，Mac，本机，套餐已选好" | 同时吸收订阅阶段/系统/方案/目标套餐；只问真正缺口，不顺序重问 |
| T84 | 已有订阅，只修复网络/清理客户端 | 不问想买什么套餐，不把付款列入本次必过项；客户端兼容性确实依赖套餐时才单独查 |

## What stays historical

The retained complete deterministic replays and sentence-level guidance reviews in `rebuild-intake-basics.md` (T01,
T02), `rebuild-entry-order.md` (T29, T57), `rebuild-task-scope-cases.md` (T43), `rebuild-intake-cases.md` (T81) and
`rebuild-subscription-original-cases.md` (T84) are unchanged and remain the ledger's `historical_evidence`. The
earlier `entry-order-limited-revalidation.md` stays a separate historical limited review. The pinned bytes of the
runtime and guides at that time cannot be diffed (squashed history), so current behavior is assessed by rerunning the
traces and re-reading today's guidance.

## Rerun on the current tree

| Suite | Cases | Result |
|---|---|---|
| `test_acceptance_intake_basics` | T01, T02 | 13 tests OK; replay twice identical, 198,896 bytes, SHA-256 prefix `957d126fca5adf2c`, equal to the recorded replay |
| `test_acceptance_entry_order` | T29, T57 | 7 tests OK; replay twice identical, 1,003,659 bytes, prefix `acd4eb95f022fa61`, equal to the recorded replay |
| `test_acceptance_task_scope_rebuild` | T43 | 15 tests OK; replay prefix `99c11ee14d12e3f0`, equal to the recorded replay |
| `test_acceptance_intake_rebuild` | T81 | 15 tests OK; replay prefix `d6787994630ceb51`, 699,463 bytes, equal to the recorded replay |
| `test_acceptance_subscription_original` | T84 | 14 tests OK; replay prefix `46a3a2ab002b14f5`, 4,649,083 bytes, equal to the recorded replay |

The unchanged replay hashes say the public state and question output of these traces did not move; the assessment
rests on reading each clause against the current guidance.

## Current guidance against each case, including the 2026-10-19 entry order

- **Ordinary subscription preparation (T01, T29, T81)**: `SKILL.md` 开始方式 item 2 still makes **Q-J01** (首次 / 重订 /
  已有) the first missing business question, then asks Mac/Windows and purpose; item 3 keeps the local default
  suggestion as something to accept; item 4 keeps "首次订阅无实际冲突时跳过旧套餐/旧渠道题". Nothing asks account ownership
  (Q-C07 is permanently retired) or recommends an unrelated VPS.
- **The new entry order does not displace this**: 环境入口顺序 (2026-10-19) begins "先明确本轮任务和本机／VM／VPS 运行路线" for
  environment checks, and `intake.md` states the order applies to any target check or repair while "纯订阅说明不强迫环境问卷".
  T29's retained sequence (subscription stage first, then system, target plan, account history, route) and T57's
  Mac/Windows-only system question are subscription-preparation intake, so the replay result is unchanged and the
  guidance agrees. T81's single-sentence answer still fills stage, system, route and target plan in one pass.
- **Reuse with retained authorization (T02)**: 环境入口顺序 says route and resource changes invalidate old applicability but
  existing exact recovery duties are not blocked by the new questionnaire, and 入口资格不是许可 (`assess_entry` is not
  permission or native binding evidence); the retained T02 trace keeps required authorization closed.
- **Existing-subscriber tasks (T43, T84)**: item 2 says a clear cleanup task goes straight to target and protection scope
  without a purchase questionnaire; `intake.md` adds that the target plan is checked only when a concrete client feature
  depends on the plan.

## Assessment

The deterministic traces still reproduce the retained expectations, and the current guidance, including the dated entry
order, agrees with each clause. Pass for all seven within the limits below.

## Not claimed

- No new generated assistant response under today's guidance and no independent reviewer of the current wording.
- No natural-language parsing: the traces consume normalized facts supplied by the host.
- No native environment, current plan catalog, real entitlement or purchase authorization.
- The entry order's interaction with other cases is covered by their own reviews, not by this page.

## Reproduce

    for t in intake_basics entry_order task_scope_rebuild intake_rebuild subscription_original; do
      PYTHONPATH=tests python3 -B -m unittest test_acceptance_$t; PYTHONPATH=tests python3 -B tests/test_acceptance_$t.py --replay | sha256sum; done
