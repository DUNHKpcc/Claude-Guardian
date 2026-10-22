# 实施决策记录

## ADR-001：首版范围（2026-10-15 已确认）

首版交付诊断预览：访谈、只读检查、离线分析与修复计划。网络配置写入、深度清理与自动回滚须逐项通过原生平台测试后开放。选择理由是先建立可试用、可回归的基础，避免未验证修改影响设备；代价是首版不会替用户完成全部环境配置。

本次实施请求取代原规格中“本轮只写 Spec”的历史阶段限制，不等于授权实际修改最终用户电脑。

## ADR-002：宿主与接触门禁（继承已确认设计）

按主规范后续章节和 ENV §18 采用 Codex 优先。旧 §3.3 的 Claude Code 首个执行宿主表述被新规定覆盖。PC0 不安装、启动或访问 Claude。脚本限制自身动作，不能声称已实现整个操作系统的隔离。

## ADR-003：GPL 与参考资料（按本次请求落实）

原创项目代码采用 GPL-3.0-only，随发行包提供 LICENSE。用户指定 GPL 3.0，没有擅自扩大为“或任意后续版本”。后续用户明确确认资料由其制作并允许公开，现将来源资料和设计基线按清单随包收录，保留署名及原有许可声明，不把引用内容自动重新许可为 GPL。已去除清理教程中的个人机器记录。来源内脚本为阅读材料，不捆绑为可自动执行的清理工具。

## ADR-004：主动检测端点与增强阻断（待后续决定）

PD-03：用户已确认采用可替换的 ipify 与 Cloudflare STUN 作为首批候选服务；每次实际探测仍独立确认目标、路径和数据披露。PD-04：用户明确只考虑免费方案；基础版不强制安装，严格模式优先评估免费 LuLu，不引入付费依赖。此产品选择不授权实际安装、系统扩展审批或故障注入，亦不关闭严格隔离验收。首版不运行公网探测，不购买检测服务或新增常驻进程。未来选择端点时需列出运营方、传输数据、频率/流量预算、维护成本和失败含义。严格 kill-switch 目标未完成时不能标为已准备就绪。

## ADR-005：运行时与验证边界（可替换工程选择）

离线逻辑采用 Python 标准库，降低依赖与维护成本；代价是目标机器需要 Python 3.10+。缺少运行时必须明示，不能静默安装。Skill 文本不依赖 Python 也可阅读。

原生只读采集与纯逻辑测试分别报告；Linux 上通过夹具不能证明 Mac/Windows 实机可用。历史 ENV01_ENV02_Contracts_v0.2.zip 未随本次提供，当前紧凑契约按正文重建，不能继承历史“56 个案例通过”。

## 迭代纪律

每次变更区分设计状态、实现状态、夹具结果、原生实测和当次授权。默认不常驻、不自动更新、不收集凭据。新增平台写操作应有独立差异、恢复方案与失败测试，再决定开放范围。

## ADR-006：免费出站工具路线（2026-10-15 已确认）

仅评估免费方案。Mac 基础路线不强制新增常驻工具；严格模式以 LuLu 为候选，安装/系统扩展/故障测试另行确认。Windows优先评估自带Windows Firewall出站规则。不得因免费候选无法满足要求而降低验收标准或误报隔离完成。

参考：[Apple TN3165](https://developer.apple.com/documentation/technotes/tn3165-packet-filter-is-not-api) 不建议广泛发行的软件把PF当稳定API；[LuLu官方说明](https://objective-see.org/products/lulu.html) 的过滤覆盖及allow-list限制必须纳入测试；[Windows规则文档](https://learn.microsoft.com/en-za/windows/security/operating-system-security/network-security/windows-firewall/rules) 要求核对阻止/允许规则优先级、应用身份及策略合并，不能照抄“全阻止＋一条允许”而假设例外生效。

## ADR-007：Claude 目标流量仅允许 IPv4（2026-10-18 已确认）

新增产品要求 **PRODUCT-IPV4-20261018**。用户对“Claude相关流量默认仅走IPv4设为Skill推荐方案吗？”明确答复“改为仅允许ipv4”。当前产品策略为 `IPv4_ONLY`，所选 Claude 目标连接不得回退 IPv6；IPv4 不可用时报告该策略下不可用，不静默恢复双栈。

这是对当前产品推荐的更新：在此限定范围内，取代历史 D05／ENV §20.5 的“双栈已覆盖则保留、必要时才限定 IPv4-only”选择顺序。原设计来源、218 条历史验收条件及层级保持原样；新要求单独追踪，不把产品选择算成历史案例通过，也不改写脱敏历史 macOS 案例。

- **纳入范围**：明确选中的 Claude 应用、目标／功能流量及实际参与该工作流的关联子进程。逐项绑定程序、档案、路径和目标连接；父进程代理变量不能证明子进程覆盖。使用代理时，还必须区分并覆盖代理到目标的地址族选择，本地 IPv4 代理监听并不足够
- **保留范围**：代理节点外层传输可继续使用必要 IPv6／UDP；保留 Codex 与独立恢复通道、组织规则、VPN／内网解析、其他应用、未选流量、回环及系统接口 IPv6。所选目标腿与这些通道的可分离性未知时，先报告缺口，不扩大限制
- **能力不足**：无受支持的限定范围机制或没有当前证据时，策略仍为 `IPv4_ONLY`，执行能力为 unknown／unsupported，合规为 not_established，不能报通过。若只存在更广范围机制，说明实际影响、控制通道风险和替代方案，另行取得具体范围的批准；本要求不授权关闭整机 IPv6 或改动无关浏览器源
- **证据边界**：AAAA 为空、`dns.ipv6: false`、`curl -4`、一次 IPv4 HTTPS 成功、IPv6 超时、没有 ICE 候选或单次 STUN 结果均不能证明限定范围强制生效。须分别验证目标腿、子进程、字面 IPv6／独立解析与相关浏览器路径，以及故障／重启／配置变化后不回退的行为；未测项保持未知
- **操作边界**：本批只落实固定策略、纯规划与诚实报告，不提供原生强制执行适配。Agent 仍须给出具体最小差异、保留对象、备份／独立恢复和同范围复测方案，取得当次修改及探测许可；PC0 和原有接触门禁不变。G2 规划就绪、规则编辑成功或导入 JSON 声称 verified 都不构成 IPv4-only 合规或环境通过

代价是 IPv4 路径不可用时该 Claude 工作流可能无法连接，限定范围能力也依赖实际平台／客户端版本。不能用扩大到系统全局、删除原有规则或跳过验收来隐藏这个代价。已有安全的独立任务可继续；无需把 IPv4／IPv6 偏好重新作为访谈必答题。


## ADR-008: selected-device history and explicit C5 data cleanup (2026-10-18)

PRODUCT-DEVICE-CLEANUP-20261018

The owner requested asking whether the selected local device previously used a banned account and a real complete Claude application-data cleanup option, rather than assessment alone. Add selected-target typed Q-D01 and independent explicit Q-D02 C5 intent. C5 permits separately selected verified Claude-owned local history/configuration/extensions and Desktop data; unrelated source/Codex/shared or unknown objects remain protected. Recoverable quarantine is the default; irreversible purge, credential/browser/native uninstall operations remain separate. Original D-SPEC §9/M13 and D-ENV §10 safeguards, PC0, action consent, backups and recovery remain in force. This is a supplemental product decision, not a rewrite of original source text, acceptance layers, or a claim that any original native case passed. No unban/fingerprint-reset promise.


## ADR-009：注册与养号节奏写入 skill（2026-10-21 已确认）

所有者要求写入账号注册与使用节奏：邮箱注册优先、少用 Apple/Google 授权；Gmail/Outlook 优先，Proton 用于防拦截；Free 至少 3 天后升 Pro，Pro 至少 15 天后升 Max；额度不顶满、早期不用重置卡、不乱薅赠送优惠；美国/英国教育邮箱权重高、手机号 KYC 概率极低；新号 KYC 的原因是环境差加邮箱新。这些资料就是本项目的依据，写入 references/account-onboarding.md（A0），不再逐条加限定语。

保留：不承诺免封或免 KYC（AGENTS.md 既有原则）；教育邮箱可通过合法渠道购买，不伪造、不借他人身份；注册、登录、付款由本人完成，PC0 门禁与事故分诊不变；不提供轮换账号、绕过额度或伪造身份的流程。

## ADR-010：移出验收台账与证据体系（2026-10-21 已确认）

所有者认为项目臃肿，验收体系对日常改动成本过高：台账与历史夹具把普通指导文档、测试和打包脚本的字节也锁住，改一行文档就要重新登记审阅。决定移出：`docs/acceptance-rebuild-ledger.json`、`docs/evidence/`、30 个 `tests/test_acceptance_*.py`、验收回放脚本、`package_manifest_transition.py` 及其三条打包转换测试、历史夹具，以及 `acceptance-handoff`、`test-coverage-map`、`package-acceptance`、`entry-revalidation-status` 等文档。

保留：设计规格原文（含 218 条验收条件）、全部运行代码和功能测试、`docs/validation.md` 等验证记录。所有被删内容可从 git 历史恢复。

后果：218 项验收的逐项追踪与哈希防篡改不再存在，不能再声称某案例“已按台账验收”；“区分指导已写、代码已实现、夹具结果、原生实测”的原则仍然适用，AGENTS.md 对此不变。回滚：revert 本提交即可恢复全部文件。

## ADR-011：所有者资料随答附带，S02 为支付核心参考（2026-10-21 已确认）

所有者要求提供的资料不能静默：相关任务的 Agent 回答必须内嵌资料跳转，例如支付回答后附《AI 所有支付方式汇总（核验版）》；Agent 可据该文档向用户推荐支付方式；该资料是支付主题的核心参考，必须列在第一项。

采用：SKILL.md 增加“资料随答附带”规则和主题对应表；source-library.md 增加“相关回答必须附带资料”，S02 标为支付核心参考；accounts-and-payments.md 的 B1 增加基于 S02 的推荐规则（按用户条件挑 1 至 3 个候选、标证据等级与风险、不推荐 S02 自己标为不推荐的渠道、购买前核验当前官方页面、不承诺成功率或退款、不以返佣排序），并放宽此前“不得照抄 S02 排名”的限制。

仍保留：只附相关几份而非全部资料；价格、准入变化快，购买前核对当前官方页面；来源中的命令不是执行授权；付款由用户本人完成，PC0 和逐动作授权不变。代价：价格和准入会变，回答需提示用户核对当前官方页面。

## ADR-012：本机路线增加“固定出口 IP 来源”指引与 VPS 推荐报告（2026-10-21 已确认）

所有者指出本机路线已要求固定 IP 出口，却没有教用户怎么得到稳定纯净的出口。新增 references/egress-ip-options.md：纯净机场、自建梯（可搭配家宽出口）、家宽拼车三种来源的优缺点；推荐 Max 优先自建、Pro 推荐机场；家宽拼车只作了解风险。仅在用户选择本机路线之后触发（routes-and-platforms.md 的 L2a），VM 和 VPS 路线不触发。

资料：收集 V2EX 讨论作社区观点（IP 类型不是封号唯一因素，也有自建中转被封案例，所以“自建风险极低”标为所有者判断而非保证）；NodeSeek 帖子因站点 403 未能读取正文，linux.do 和 X 未检索到，未收录。所有者提供 17 份 VPS 推荐 PDF（业务、性价比、高端家宽），以 R01 收入 sources/vps-recommendations/，PDF 字节不变，文件名改 ASCII，哈希入 manifest。

代价与限制：增加约 32MB 包体积；报告为历史记录且两份含商家推广或邀请链接，不作排序理由；不承诺免封或 IP 稳定纯净；不新增访谈问题编号，仍以文档指引为主。

ADR-012 补充（同日）：机场与家宽拼车不提供教程和渠道，由用户自行搜索；自建梯只给简版提示词：3x-ui + CN2 GIA 等优化线路 VPS + 可选家宽出口；客户端 iOS 小火箭、Android FlClash、桌面 Clash Verge 或 FlClash。R01 登记在 manifest 的 collections，不计入七份阅读来源，打包脚本同时校验 sources 与 collections。

ADR-012 再补充（同日）：17 份 PDF 用 Ghostscript 压缩，32MB 降到约 15MB，页面与链接保留，文字层提取个别字符可能缺失，哈希与原始哈希均登记在 manifest；移除“社区观点并不一致”段落（不再写自建社区案例分歧）；VPS 推荐报告与其他资料同口径，相关回答必须附索引和被引用的具体报告链接。

## ADR-013：手机端防封要点（2026-10-21 已确认）

所有者要求加入手机端防封：内容取自 S03 第 4 页的手机端表格（原为图片，12 项），并补充 Android 手机要拔掉 SIM 卡。新增 references/mobile-guidance.md。入口：账号注册（account-onboarding.md 第 7 条）和选择 Apple、Google Play 内购时（accounts-and-payments.md 的 Apple、Google 卡），另有仅手机用户（Q-OS12）。SKILL.md 资料附带表加一行，必附 S03 第 4 页。

边界：不承诺免封；拔 SIM 会影响通话和验证码，需要收验证码时先插回；表格里“IPv6 统一出口或关闭”与本项目“不自动关闭 IPv6”并存，是否关闭由用户自行决定；只给指引，不代操作手机。出口 IP 获取复用 egress-ip-options.md，不重复。

## ADR-014：去掉资料来源的限定说明；教育邮箱可合法购买（2026-10-21 已确认）

所有者确认其提供的资料就是本项目的真实依据，要求不再写“社区经验、没有官方依据、未经验证”之类限定，并修改更早的通用说明。已改：source-library.md 开头与 S01、S03、S04 条目，evidence-policy.md 的论断类型、C 系列和 F 系列说明，accounts-and-payments.md 的来源边界，incidents-and-integrations.md 的封号时间线说明，routes-and-platforms.md 的出口标签说明。教育邮箱由“仅限本人合法获发”改为“可通过合法渠道购买，不伪造、不借他人身份”。

仍保留：不承诺免封或免 KYC；不提供伪造身份、轮换账号或绕过额度的流程；PC0、逐动作授权和付款本人完成；价格与准入变化快，购买前核对当前官方页面；来源中的命令不是执行授权。
