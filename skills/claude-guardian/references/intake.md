# M00: adaptive intake and stable question registry

中文执行摘要：先问订阅阶段，再问系统与当前任务；复用已知答案，一轮一个决策。Q-C07 永久停用；Q-C08 只表示目标套餐；首次订阅无实际矛盾不问旧订阅。下表是稳定 ID 的技术索引，向用户提问时改写成简短中文，不逐行照问。未知、拒答和未适用不能当作通过。

## Scheduling

Read existing task facts first. Ask one decision per turn; at most a few related short facts together. Absorb all useful facts in a reply, skip known/not-applicable items, clarify an ambiguous answer once, then allow unknown, decline, pause, or a limited plan. Never display this entire registry as a form. Structured UI is optional and must obey the actual host's tool contract. Do not change host modes or approval settings to enable UI.

Normal subscription-preparation order: Q-J01 → OS/purpose/target plan → account history and route → relevant network/payment prerequisites → route resources/protection → short summary. An urgent compromise, data-loss issue, suspension, identity check, or duplicate charge takes priority. Technical skill changes explanation depth only.

`subscription_journey` is `first_subscription`, `returning_subscription`, `existing_subscriber`, or `unknown`. Explicit first/returning answers establish only reported absence of a current subscription; they do not verify billing. Current subscribers get Q-C11 only if their task is missing. First-time users are not asked whether they want a subscription. Q-C08 means the desired plan, never legacy entitlement. Q-P02/Q-A06 activate only for relevant existing-billing tasks or an actual contradiction. Pure technical diagnosis does not activate a payment survey.

### 已到期用户的相关旧账单（T76）

“以前订阅过，已到期，准备重订 Pro，但先处理旧 Apple 订单退款”仍记录 `returning_subscription` 和原 `none_reported` 的来源/时间，保留已选 Q-C08，不制造冲突或当前有效权益。宿主将明确的旧退款/恢复任务归一为 `set_context(task="billing_issue")`；明确的旧渠道迁移可用 `change_channel`。普通重订不展开旧账单；不要将 returning 的 renew/upgrade 组合自动解释成已确认任务。Q-C11 的整批矛盾校验不变，不能为通过校验伪造 existing_subscriber。

仅处理相关旧账单时，按缺口问 Q-P02 和 Apple 条件 Q-A06；不把新购设备、商店地区、礼品卡、续费、结账或运行方案问卷作为解释退款的前提。宿主一次吸收完整旧订单答复：Q-P02 可保存明确提供的旧 plan（相关时）、billing_channel、status、pending_issue 类别；后三项明确时覆盖 A06，不自动生成额外事实。例：`{"plan":"原套餐","billing_channel":"apple","status":"expired","pending_issue":"pending_refund"}`。未说明的项不能补造；自由文本仍兼容，可按同一真实答复分别记录 P02/A06，保留其真实来源/时间。P02 未知、拒答或延期后不换成 A06 重复同一追问，只给带缺口的说明。旧购买渠道来自旧账单自述，不能从拟用的新渠道推定；已明确的旧 Apple 渠道优先于未来网页/Google/未选渠道，仍按缺口走 A06。结构化但未完整的非 Apple 旧订单在 P02 最多澄清一次；不因 reported 部分对象就宣称依赖已齐。P02 描述的订单发生实质变化或被标为陈旧时，旧 A06 不得替新订单补缺口；同一答复用整批接口先处理 P02，再吸收新的 A06。明确新账单/渠道迁移任务会复核保留的旧订单事实。历史设备清理建议不成为退款说明的前提，当前事故和明确启用的清理任务仍优先。

完成这段问诊后回到同一任务的 `subscription_preparation`，复用已选目标和无有效订阅自述，继续真正重订前提；明确的新任务仍用 `begin_task`，不继承旧购买目标。`billing_issue` 的 payment_intent 为 troubleshoot，仅表示账单问题；不授权扣款、申请退款或访问账户。具体退款规则、状态和官方入口仍须在获准范围内核验，不能承诺退款。依据：[D-SPEC §5.5、§6.8–6.9、§6.11、D.5–D.6、T76](../sources/design/D-SPEC-v0.1.10.md)。

### 仅在实际问题需要时确认当前套餐（T84）

Q-C13 是新增的派生实现 ID，依据 D-SPEC §6.4/§6.11/T84；原文 ID、Q-C08 目标套餐和 Q-L02 系统/架构问题不变。只有明确当前已有订阅，并且 network/environment/cleanup 的具体客户端功能问题确实依赖套餐时，宿主显式设置可选 `plan_compatibility_needed=true`。普通网络/清理没有这个条件，不问当前套餐，也不展开支付问卷。仅有技术熟练度、设备、付款渠道、目标套餐或此标志，都不能证明当前权益。

问一个短问题：“为判断这次具体客户端功能的套餐依赖，当前订阅是什么套餐，涉及哪项功能？”已明确的当前套餐直接复用，不能复制 Q-C08。Q-C13 使用标准事实信封、账号绑定、独立来源/观测时间；reported/observed 的非空套餐描述可补足这项信息，不验证套餐在售或该功能可用，禁止 inferred 权益，也不接受目标选择专用的 selected_unspecified 充当当前套餐；不知道名称用 unknown。未知/拒答/延期保持空值并停止自动重复；当前依赖仍为条件建议。只延期这项可用 `defer_branch(state, "compatibility")`；不阻断无关网络说明或清理清单规划，实际清理仍过自己的保护与操作门禁。not_applicable 不能在依赖标志仍为 true 时冒充套餐已知；若实际无此依赖，宿主应撤销该条件。

每次改变任务或 `begin_task` 都清除该标志，新问题由宿主重新确认是否相关；同账号换设备可保留有效套餐事实，新账号不继承。订阅阶段变化、订阅事实失效、实际订阅冲突或报告购买完成使旧 Q-C13 陈旧并保留原来源/时间，不能从新目标猜已生效套餐。历史相同证据重放不能恢复陈旧事实；更换来源或导入另一份较新快照也不能解除已有的陈旧义务，不重置已经消耗的澄清次数；早于最新订阅阶段观测的导入同样保持陈旧。当前新答复可按真实来源更新；不要将历史导入伪装成当前答复。精确重放同一购买完成来源/时间/状态时不重置随后已经给出的新套餐、任务或条件。真正中断后的分组复核包含已保留的当前套餐，即使依赖暂未展开，避免稍后打开条件就使用漏审的旧事实。新任务或同账号换设备不能通过丢弃未解决的复核来复活旧套餐：相关旧 Q-C13 保留但标为 stale。无需为此重新问整套订阅/支付问卷。

该上下文键在默认输出中省略，旧 schema-1 状态仍接受。`complete_purchase` 仅在实际报告完成后另留可选 `purchase_completion`，内容限账号别名、来源、观测时间和是否 observed；它是同账号生命周期去重记录，不是账单核验、交易号、订阅资格或权限。普通 J01 自述即使来源/时间相同，也不冒充已经处理过的完成事件。同一完成证据跨新任务/同账号设备重放不改变后来的任务、订阅或套餐；旧于已保留完成记录或同时间矛盾的元数据拒绝，不能复活已到期状态。新账号不继承；历史完成记录不能覆盖更晚的订阅/套餐观察。包含新键、Q-C13 或完成记录时，旧的严格读取器可能拒绝，须同步升级读取器，不能剥除未解决事实来假装就绪。CLI 直接沿用 `--context-file` 的布尔字段、`--answer-file` 的正常 Q-C13 回复和原有批准私有保存/续接路径，没有旁路。完成 Q-C13 不建立真实功能兼容性；在 PC0 只复用已提供自述/获准快照，不能让用户打开 Claude 查询权益，需实时资料时保留待获准核验。事故、no_cleanup、暂停始终优先，G3 和所有接触/操作权限不变。依据：[D-SPEC §6.4、§6.11、D.8、T84](../sources/design/D-SPEC-v0.1.10.md)、[D-ENV §18.4–18.10](../sources/design/D-ENV-v0.3.md)。

用户说“套餐已选好”但未提供名称时，宿主将Q-C08记录为`reported`、保留值`selected_unspecified`，同时吸收本轮其他明确事实；不得猜成Pro/Max，也不把已选误写成尚未决定。仅在目标套餐适用且身份仍缺失时，同一Q-C08最多澄清一次：“你已经选好套餐；具体是哪一个套餐？”这不是重问是否选好。该值保留选择事实但不能满足套餐身份或G2就绪。直接调用接口的宿主在实际送达后调用`mark_asked`消耗既有澄清次数；CLI在完整有效的当前回复确实回答正在等待的Q-C08身份澄清时消耗次数，普通套餐问题或无关回复不消耗这次身份澄清。仅输出/读档不消耗或重置次数，重复未命名回复也不重启循环。之后明确给出名称则正常替换；若明确未知、拒答或延期，沿用该字段的空值状态替换契约并停止追问，不声称还保留先前完整值。若名称早已在有效上下文中明确，复用其原来源/时间，不用这句未命名回复覆盖它。宿主负责上述自然语言归一化；脚本不解析自由文本、不验证套餐当前可售或授权购买。

The local route is a proposal until accepted. Record `explicit_choice`, `task_context`, or `accepted_default`; an unaccepted default stays `default_proposal`. Do not infer a route from expertise or owned equipment.

Q-C05未回答、跳过、未知、拒答或延期时，保留未确认的候选；只给路线比较或带缺口的初步建议，不按本机开始部署，也不把停止追问当作已接受。仅说“我是老手/用过”由宿主标记`ambiguous_experience=true`，当前订阅仍unknown，用Q-J02简短澄清一次；熟练度只改变讲解深度。未知/拒答/延期后不重复追问，不能猜成当前付费。

明确已有订阅且只查本机环境时，一轮吸收订阅阶段、environment任务、系统与local选择，复用已知事实，不问新目标套餐或付款渠道。`purchase_intent=none`与`payment_intent=none`表示本次未处理购买，不表示没有订阅。旧保存记录中的任务标签按当前明确任务归一化，不改订阅证据的来源/时间；同任务的已完成购买仍保留completed，明确新任务由`begin_task`重置其任务标签，不拿旧目标套餐作新购买目标。

凭据泄露/当前停用优先进入最小事故分流；`emergency_deferred_branches`只列因事故暂缓的其他未完成主题，区别于用户主动延期的`deferred_branches`，不修改其已答事实。泄露使用原Q-H01—Q-H07的凭据语境，仅问类别、服务、脱敏迹象、受影响组件与已有保护状态，不问秘密值、无关账单或退款；未知/拒答/不适用可直接记录。发现泄露立即停止助手自己尚未发送的重试和新请求，说明官方保护入口与影响；不等七题答齐才给保护建议。实际撤销凭据、停止用户任务、退出会话或接触服务仍按独立权限处理，不能借紧急状态打开G3或接触门禁。按[事故处理卡](incidents-and-integrations.md#incident-triage-m12)先给最小必要指导，其他细节只在依赖它的步骤补充；只有明确报告本次事故已处理后才恢复此前任务，不把未知/拒答当作事故解决。

## Fact states and gates

Keep value, state, source, target alias, observation time, applicability, required gate, and missing-evidence reason together. States: `unasked`, `reported`, `observed`, `inferred`, `unknown`, `declined`, `conflict`, `stale`, `not_applicable`. Unknown/declined are not false. Never infer actual residence, payment eligibility, subscription status, bans, or authorization.

- **G1 interview coverage:** every applicable branch handled; unknowns visible. Complete, partial, paused, blocked, or emergency-deferred are distinct outcomes
- **G2 personalized plan:** enough current target, task, route, network/resource/payment/protection facts to plan; otherwise issue a conditional plan
- **G3 action:** exact proposed change or purchase, current prerequisites, scope/price, specific authorization, supported capability, and necessary recovery. Preview operations cannot satisfy execution capability simply by receiving approval

These gates do not replace PC-G1/PC-G2. When a purchase is later completed, update the current state and stop treating the user as still awaiting purchase. Old Q-C08 answers must not silently become new target-plan answers.

## Interruption and resume

真正中断后继续同一任务时，Agent 必须先调用 `resume_interview(state, resume_id=...)`，CLI 使用 `--input <已批准保存的状态> --resume <本次事件别名>`。普通 `loads_state` / `--input` 只是读档或连续轮次，不代表发生中断；不得每轮重启审查。已有 `paused=true` 不能直接改为 false 绕过续接。

保留当前任务的 VM/VPS 选择、原事实来源/时间、保护要求和已发生接触阶段，不能恢复成本机默认值或“从未接触”。尚未接受的本机仍只是候选。事件别名只用于本次重试去重，不是秘密、用户授权或设备身份凭据；宿主为每次真正的新中断使用新别名。

向用户展示一次 `resume_review_prompt` 的相关分组摘要：还是同一目标设备/账号吗，已记录的系统/版本、网络与测试、当前路线资源/访问/共享/恢复、登录和使用地区是否变化；订阅阶段只在本次购买/账单任务相关时纳入；已保留的 Q-C13 当前套餐单独作为功能依赖复核，不开启支付问卷。范围包含本路线已记录但尚未展开的条件项，不能因稍后激活某个分支而把旧事实当成新事实；不询问详细地址、凭据或全部问卷。没有可复用的相关环境事实时不加空审查门槛。

当前回答通过 `record_resume_review` / `--resume-review-file` 归一化记录。回答没变保留旧观测时间，另存本次 reported 复核的来源和时间，不能升级成设备实测。回答变化时仅使所报、属于本次范围的稳定字段 ID 失效，再补相应原题；不得失效路线选择、已选套餐、保护选择或动作权限。未知、拒答、稍后再说都停止自动重复此提示，保留条件建议；后续由用户主动补充或更正。已知换目标需 `begin_task` 显式重新绑定；只有用户明确更正“刚才说错，仍是原设备/账号”才能用新的当前回复解除该状态。

未回答或未解决的审查阻止 G2 个性化就绪；通用/条件指导与紧急事故分流仍可进行，紧急事故优先。已完成购买的同会话状态转换不制造新中断；尚未解决的相关环境或目标变化仍保留。复核、路线选择和保存的记录都不能打开 G3、PC-G1/PC-G2 或任何实际操作许可。

宿主须区分当前回复与历史导入：`record_facts` 的整批输入、以及未提供 `observed_at` 的 `record_fact` 表示明确的当前回复；提供 `observed_at` 的 `record_fact` 默认是保留证据日期的历史导入，不能因记录更新就当作本次回复。只有宿主确实正在归一化一条新的当前答复时，才能显式用 `current_reply=True` 保留其真实观测时间；此严格布尔参数只是可信宿主对输入来源的区分，不验证用户、证明新鲜性或授权任何行为，不能将旧快照重标为当前答复。早于最新订阅阶段观测的 Q-C13 仍不得恢复当前性。不能把历史日志放进当前回复接口来伪造新鲜性。读档、输出或续接事件/复核回复的幂等重试不得刷新事实时间、重获保存同意或将旧记录自动标成已观察；不存在任意 TTL。CLI 先开始真正续接，再处理上下文和本次复核，再吸收本次字段答案，整轮验证失败不保存部分状态。

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
| Q-C11 | Current subscriber's renewal, upgrade, environment, or incident task; explicit expired legacy-bill task uses host context |
| Q-C12 | Data, projects, clients, or settings that must be preserved |
| Q-C13 | Derived implementation ID: account-bound current plan only for an explicit actual plan-dependent technical/cleanup question; never the desired plan |
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


## Selected-device history and explicit cleanup task

| ID | Meaning and trigger | Binding and effect |
| --- | --- | --- |
| Q-D01 | Selected device's explicitly restricted-account use: current_restriction_on_target / past_restriction_on_target / ordinary_error_only / other_device_only / none_reported; unknown/declined are null-valued fact states. Automatically ask when Q-C03 past_suspension is reported and this device fact is absent; explicit reset does not depend on it. | Selected target alias, never inferred from account history or first subscription. A current device event requires bounded incident clarification; it does not mark the selected account suspended. |
| Q-D02 | audit_only / full_claude_data_reset / other_scope / no_cleanup. Record an already explicit request without asking again. | Selected target and current task only. Fresh task/route/target checks and resume review apply. Goal selection grants no filesystem or operation permission. |

A cleanup-only task asks only relevant target/client/OS, goal, preservation and check/change/recovery scope. It does not require payment or general subscription answers. The sole current-plan exception is the separately scoped Q-C13 dependency above, only for an explicitly existing subscriber and an actually plan-dependent client question; it is never a prerequisite to unrelated cleanup planning. `no_cleanup` ends cleanup questions. Unknown/refusal/defer remains bounded; urgent incidents retain priority. Current selected-account status stays separate from the identity of an account previously used on the device.


### Device-only triage resolution

When D01 truthfully says this device used another account that is currently restricted, retain that category and the selected account's independent C04 status. After bounded clarification, the host may explicitly report `set_context(state, device_incident_resolved=True)`. This closes only device-episode triage; it is bound to the current D01 fact's target/provenance/time/category, and grants no action permission. New device/route/namespace or actual episode evidence invalidates it. A task-only change retains informational resolution for the unchanged bound episode, clears obsolete cleanup intent and suppresses re-offering that same episode; fresh history or an explicit cleanup request can reactivate planning. Account suspension, credential exposure and data-risk incidents remain governed by their separate existing resolution state. Exact old-evidence replay cannot reopen the episode; a fresh report can. Do not tell the user to falsify D01 as past merely to proceed.
