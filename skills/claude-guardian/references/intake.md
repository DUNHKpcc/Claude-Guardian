# M00: adaptive intake and stable question registry

中文执行摘要：先问订阅阶段，再问系统与当前任务；复用已知答案，一轮一个决策。Q-C07 永久停用；Q-C08 只表示目标套餐；首次订阅无实际矛盾不问旧订阅。下表是稳定 ID 的技术索引，向用户提问时改写成简短中文，不逐行照问。未知、拒答和未适用不能当作通过。

## Scheduling

Read existing task facts first. Ask one decision per turn; at most a few related short facts together. Absorb all useful facts in a reply, skip known/not-applicable items, clarify an ambiguous answer once, then allow unknown, decline, pause, or a limited plan. Never display this entire registry as a form. Structured UI is optional and must obey the actual host's tool contract. Do not change host modes or approval settings to enable UI.

Normal order: Q-J01 → OS/purpose/target plan → account history and route → relevant network/payment prerequisites → route resources/protection → short summary. An urgent compromise, data-loss issue, suspension, identity check, or duplicate charge takes priority. Technical skill changes explanation depth only.

`subscription_journey` is `first_subscription`, `returning_subscription`, `existing_subscriber`, or `unknown`. Explicit first/returning answers establish only reported absence of a current subscription; they do not verify billing. Current subscribers get Q-C11 only if their task is missing. First-time users are not asked whether they want a subscription. Q-C08 means the desired plan, never legacy entitlement. Q-P02/Q-A06 activate only for relevant existing-billing tasks or an actual contradiction. Pure technical diagnosis does not activate a payment survey.

The local route is a proposal until accepted. Record `explicit_choice`, `task_context`, or `accepted_default`; an unaccepted default stays `default_proposal`. Do not infer a route from expertise or owned equipment.

## Fact states and gates

Keep value, state, source, target alias, observation time, applicability, required gate, and missing-evidence reason together. States: `unasked`, `reported`, `observed`, `inferred`, `unknown`, `declined`, `conflict`, `stale`, `not_applicable`. Unknown/declined are not false. Never infer actual residence, payment eligibility, subscription status, bans, or authorization.

- **G1 interview coverage:** every applicable branch handled; unknowns visible. Complete, partial, paused, blocked, or emergency-deferred are distinct outcomes
- **G2 personalized plan:** enough current target, task, route, network/resource/payment/protection facts to plan; otherwise issue a conditional plan
- **G3 action:** exact proposed change or purchase, current prerequisites, scope/price, specific authorization, supported capability, and necessary recovery. Preview operations cannot satisfy execution capability simply by receiving approval

These gates do not replace PC-G1/PC-G2. When a purchase is later completed, update the current state and stop treating the user as still awaiting purchase. Old Q-C08 answers must not silently become new target-plan answers.

## Interruption and resume

真正中断后继续同一任务时，Agent 必须先调用 `resume_interview(state, resume_id=...)`，CLI 使用 `--input <已批准保存的状态> --resume <本次事件别名>`。普通 `loads_state` / `--input` 只是读档或连续轮次，不代表发生中断；不得每轮重启审查。已有 `paused=true` 不能直接改为 false 绕过续接。

保留当前任务的 VM/VPS 选择、原事实来源/时间、保护要求和已发生接触阶段，不能恢复成本机默认值或“从未接触”。尚未接受的本机仍只是候选。事件别名只用于本次重试去重，不是秘密、用户授权或设备身份凭据；宿主为每次真正的新中断使用新别名。

向用户展示一次 `resume_review_prompt` 的相关分组摘要：还是同一目标设备/账号吗，已记录的系统/版本、网络与测试、当前路线资源/访问/共享/恢复、登录和使用地区是否变化；订阅只在本次购买/账单任务相关时纳入。范围包含本路线已记录但尚未展开的条件项，不能因稍后激活某个分支而把旧事实当成新事实；不询问详细地址、凭据或全部问卷。没有可复用的相关环境事实时不加空审查门槛。

当前回答通过 `record_resume_review` / `--resume-review-file` 归一化记录。回答没变保留旧观测时间，另存本次 reported 复核的来源和时间，不能升级成设备实测。回答变化时仅使所报、属于本次范围的稳定字段 ID 失效，再补相应原题；不得失效路线选择、已选套餐、保护选择或动作权限。未知、拒答、稍后再说都停止自动重复此提示，保留条件建议；后续由用户主动补充或更正。已知换目标需 `begin_task` 显式重新绑定；只有用户明确更正“刚才说错，仍是原设备/账号”才能用新的当前回复解除该状态。

未回答或未解决的审查阻止 G2 个性化就绪；通用/条件指导与紧急事故分流仍可进行，紧急事故优先。已完成购买的同会话状态转换不制造新中断；尚未解决的相关环境或目标变化仍保留。复核、路线选择和保存的记录都不能打开 G3、PC-G1/PC-G2 或任何实际操作许可。

宿主须区分当前回复与历史导入：`record_facts` 的整批输入、以及未提供 `observed_at` 的 `record_fact` 表示明确的当前回复；提供 `observed_at` 的 `record_fact` 是保留证据日期的导入，不能因日期较旧记录更新就当作本次回复。不能把历史日志放进当前回复接口来伪造新鲜性。读档、输出或续接事件/复核回复的幂等重试不得刷新事实时间、重获保存同意或将旧记录自动标成已观察；不存在任意 TTL。CLI 先开始真正续接，再处理上下文和本次复核，再吸收本次字段答案，整轮验证失败不保存部分状态。

## Stable question IDs

The following are short prompts/field meanings, not a mandatory sequence. Preserve IDs in progress records. Q-C07 remains a retired tombstone only, never an active question or missing field.

### Core and OS

| ID | Ask or establish only when missing and relevant |
|---|---|
| Q-J01 | First-ever subscription, returning after expiry, currently subscribed, or uncertain? |
| Q-J02 | Clarify ambiguous “experienced/used it before” into current subscription stage |
| Q-C01 | Current goal and Web/Desktop/Code use |
| Q-C02 | Mac or Windows, after subscription stage; alias Q-OS01 |
| Q-C03 | Reported suspension history versus ordinary errors |
| Q-C04 | Existing registration and reported login state; do not open Claude in PC0 |
| Q-C05 | Accept local recommendation, choose VM/VPS, or compare |
| Q-C06 | Existing authentication category; skip unregistered users; no credentials |
| Q-C08 | Desired subscription plan or need for comparison |
| Q-C09 | Actual country/region of use and relevant travel; no street address |
| Q-C10 | Desired explanation depth |
| Q-C11 | Returning/existing user's renewal, upgrade, environment, or incident task |
| Q-C12 | Data, projects, clients, or settings that must be preserved |
| Q-OS01 | Same fact as Q-C02, never ask twice |
| Q-OS02 | Windows version and Edition, distinguishing Single Language |
| Q-OS03 | macOS version; architecture only when needed |
| Q-OS04 | Display language, input method, locale, browser, or app language? |
| Q-OS05 | Exact single-language restriction message, only for display-language trouble |
| Q-OS06 | Timezone symptom: disabled control, error, or reverting value |
| Q-OS07 | Automatic-timezone setting and management/privilege constraints |
| Q-OS08 | Wrong absolute time versus timezone display |
| Q-OS09 | Actual need for a language/timezone change versus usability check |
| Q-OS10 | Windows 10 maintenance/ESU/migration arrangement when relevant |
| Q-OS11 | macOS system-wide versus app-specific setting goal |
| Q-OS12 | Out-of-scope desktop/mobile-only: general guidance or voluntary VM/VPS comparison |

### History and network

| ID | Conditional fact |
|---|---|
| Q-H01 | Which account/service/card/client is restricted? |
| Q-H02 | Relevant event date and recovery status |
| Q-H03 | Sanitized exact error or notice |
| Q-H04 | What action immediately preceded the symptom? Record sequence, not cause |
| Q-H05 | Relevant device/client/environment/billing channel |
| Q-H06 | Pending appeal, identity review, refund, or official request |
| Q-H07 | Prior cleanup/reinstall/configuration changes and data to protect |
| Q-H08 | Relevant reused/changed device/network/payment categories; no blacklist inference |
| Q-N01 | Direct, proxy/VPN, or organization network |
| Q-N02 | Browser, Code, and proxy locations and interception mode |
| Q-N03 | Network switching and intended stable workflow |
| Q-N04 | Other devices and their actual roles |
| Q-N05 | Existing test's date, program, target, and scope |
| Q-N06 | Organization network, certificate, security, or management constraints |

### Payment branches

| ID | Conditional fact |
|---|---|
| Q-P01 | Subscription versus API/third-party billing only if ambiguous |
| Q-P02 | Relevant old plan/channel/order; not a first-subscriber default |
| Q-P03 | Available payment device categories |
| Q-P04 | Available store balance/card/company payment category |
| Q-P05 | Budget when comparing or addressing a price conflict |
| Q-P06 | Choice among actually feasible channels |
| Q-P07 | Future renewal/billing/cancellation guidance |
| Q-A01 | Accessible iPhone/iPad versus Mac-only redemption capability |
| Q-A02 | Apple account sign-in/verification availability; no ownership survey |
| Q-A03 | Actual App Store storefront region |
| Q-A04 | Official app and desired in-app plan entry; defer live check until handoff |
| Q-A05 | Correct target Claude account correspondence, post-contact |
| Q-A06 | Conditional old-order issue; same gate as Q-P02 |
| Q-A07 | Gift-card status, formal type, issuing region; no code |
| Q-A08 | Checkout total coverage and additional payment requirement, post-contact |
| Q-A09 | Seller/source verification if buying a card |
| Q-A10 | Renewal and, only if changing region, effects on other Apple services |
| Q-G01 | Android plus usable official Play/store app |
| Q-G02 | Google sign-in availability, Play region, payment category |
| Q-G03 | Actual plan and payment entry, deferred until contact |
| Q-G04 | Target Claude account match; old-plan questions retain Q-P02 gate |
| Q-G05 | Renewal guidance; deduplicate Q-P07 |
| Q-W01 | Card category and issuing region; no number/BIN required |
| Q-W02 | Ability to supply truthful billing details privately at checkout |
| Q-W03 | Online/recurring support and relevant decline/verification symptom |
| Q-W04 | Actual total, billing period, and renewal commitment |
| Q-I01 | API platform and billed organization/project |
| Q-I02 | Specific project usage/payment authority, only for organization tasks |
| Q-I03 | Personal development versus service for others |
| Q-I04 | Budget, cap, and alert goals |
| Q-E01 | Actual enterprise settlement need |
| Q-E02 | Responsibility for enterprise verification/payment/maintenance |

### Environment and delivery

| ID | Conditional fact |
|---|---|
| Q-L01 | Existing client installation method/version, without launching it |
| Q-L02 | Relevant OS/architecture compatibility, reusing known OS |
| Q-L03 | Active MCP/plugins/hooks/gateway components |
| Q-L04 | Local project, software, GUI, or hardware dependencies |
| Q-L05 | Management and allowed changes; reuse Q-N06 |
| Q-V01 | Existing/new VM and hypervisor |
| Q-V02 | Separate host/guest OS and architecture |
| Q-V03 | VM resources and protected projects |
| Q-V04 | VM networking and proxy location |
| Q-V05 | Shared folders, clipboard, tool and credential mounts; no secret values |
| Q-V06 | Snapshot/backup and restore scope |
| Q-S01 | VPS workspace or merely proxy exit? |
| Q-S02 | Existing/new server, region, OS, and resources |
| Q-S03 | SSH access and independent rescue channel; no keys/passwords |
| Q-S04 | Production workloads and unbacked-up data |
| Q-S05 | Remote-data acceptability and local dependencies |
| Q-S06 | Server, traffic, and maintenance budget if needed |
| Q-S07 | Terminal/Remote-SSH/remote-browser workflow and maintenance |
| Q-Z01 | Explanation/plan versus authorized target read scope |
| Q-Z02 | Detailed preservation scope; reuse Q-C12 |
| Q-Z03 | Specific proposed changes and administrator requirements |
| Q-Z04 | Backup/rollback/rescue prerequisites |
| Q-Z05 | Permission for private sanitized persistence/export |
