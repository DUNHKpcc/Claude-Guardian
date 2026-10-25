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

## ADR-015：VM 路线补全：系统、网卡、出口、防火墙（2026-10-21 已确认）

所有者要求完善 VM 路线：客机系统默认首选 Omarchy，宿主是 Mac 时首选 macOS；创建前网卡选 LAN 独立网卡，不选与宿主机一致的 shared NAT；出口 IP 直接复用 egress-ip-options.md；防火墙参考所有者的 install-flclash-killswitch.sh；之后的注册、订阅、养号与本机路线一致。新增 references/vm-guidance.md 和 routes-and-platforms.md 的 V2a 卡，SKILL.md 资料表加一行。

脚本以脱敏版收入 assets/vm-killswitch/：原脚本含所有者的固定出口 IP、局域网网段和用户名，按仓库规则不入库；改为 LAN_NET 必填、EXPECTED_EXIT_IP 可选、服务用户取当前 sudo 用户，其余逻辑不变。只适用 Linux 客机 + FlClash TUN；macOS 客机无对应脚本，按本机路线 L2 评估 LuLu 或系统防火墙。脚本由用户在客机里自己运行，Agent 只解释和核对，运行前先打快照，应用后 180 秒保险丝内必须 confirm。

已知限制：刷新定时服务由普通用户调用 sudo，需免密 sudo；只解析最新 profile 的 server 和 port 字段；不承诺免封。

## ADR-016：VPS 路线定位为开发机，补入 S08 与相关资料（2026-10-21 已确认）

所有者明确：VPS 路线主要用作**开发机**；VPS 当中转机（自建梯）是选择本机路线的用户选 IP 出口时的选项，两者不能混为一谈。VPS 路线的核心是**环境一致**：注册、登录、养号、订阅、OAuth 都在 VPS 的远程桌面浏览器里完成，不和本机浏览器混用，参考 S08。服务器系统首选 Ubuntu。防火墙参考 VM 的脚本。

补入所有者放在 Omarchy/粉丝群资源 的资料：S08（VPS Claude 教程，11 页 PDF，原“S08 仍未提供”改为已收录）及其文字版、S03 的 Markdown 源文本、R02《VPS 线路优化与家宽中转教程》。新增 references/vps-guidance.md 和 routes-and-platforms.md 的 P1a 卡；Q-S01 的问法改为“开发机，还是只想当代理出口节点（属于本机路线的出口选择）”；SKILL.md 资料表加一行，必附 S08。

防火墙：新增 assets/vps-firewall/vps-guard.sh，参考 VM 脚本的结构（nftables、原子替换、180 秒保险丝、开机自启），用于 VPS 自己的 IP 就是出口的情况，入站默认丢弃，只放行管理来源的 SSH 和 ping；套家宽出口并在 VPS 上跑 TUN 时直接用 VM 的 killswitch 脚本。规则语法经 nft -c 在隔离命名空间检查，应用与保险丝流程没有在真实服务器上实测。

未收录：《完整教程焚诀.docx》（含作者邀请码、联系方式和注册交易所的步骤）、二群.jpg（QQ 群二维码），待所有者决定。

ADR-016 补充（同日）：所有者指出 S03 Markdown 源文本末尾“尽量不要在机房环境，模拟海外环境使用”一段是原资料错误，已从仓库副本删除，manifest 哈希和说明同步更新；S03 的 PDF 本就不含该段，未改动。此前提到的该段与 S08 VPS 路线的冲突因此消除。《完整教程焚诀.docx》与二群.jpg 仍未收录。

ADR-016 再补充（同日）：所有者决定《完整教程焚诀.docx》和二群.jpg 不收录；VM 路线的出口也复用推荐（R01 报告索引、S07 IP 质量清单），VM 与 VPS 路线在 SKILL.md 资料表中直接列出各自的防火墙脚本。引用检查：新入库资料均可从 SKILL.md 沿链接触达，17 份 R01 PDF 都在索引中；原先没有任何引导文档引用的 assets/webrtc-probe.html 现接入 VM、VPS 的 WebRTC 验收和 SKILL.md 本地防护一行。

## ADR-017：线路优化：Agent 辅助的逐项流程（2026-10-21 已确认）

所有者要求线路优化写得详细，重点是“如何用 Agent 帮用户的机器优化线路”，而不是选配，以 R02《VPS 线路优化与家宽中转教程》为主线。新增 references/line-optimization.md：Agent 的固定工作方式（绑定目标、只读诊断、出变更卡、批准后执行并验证、可回滚）；按现象定位表；两机搭配（A 优化线路机、B 家宽出口机）的方案 A、方案 B；逐项应用（SSH 动态转发建 SOCKS5、noVNC 本地入口与画质、Realm 端口中转、BBR 临时切换到持久化与回滚）；验证与记录；Agent 不做的事。

入口：SKILL.md 资料表新增“线路优化”一行（必附 line-optimization 和 R02），vps-guidance.md、egress-ip-options.md 各加一节指向它。routes-and-platforms.md P1 第 2 条由“不运行 BBR/优化全家桶”改为“不默认运行，经用户逐项批准、先记原值、可回滚”。

边界：每项改动都是用户批准的一张变更卡，一次只改一个因素；没有云控制台救援入口和快照时不改 SSH、防火墙、转发；不承诺更快或更稳；端口转发不等于加密；自启和断线重连是单独一项改动。命令来自 R02，规则与语法未在真实服务器上实测。

## ADR-018：把路线、出口来源和手机端判断固化成访谈问题（2026-10-21 已确认）

此前 VM、VPS、线路优化、手机端、出口来源几块只是指引文档，“问什么、走哪条路”完全靠 Agent 读文档判断。所有者确认加入访谈状态机兜底。新增六个分类问题（取值见 interview_flow.ROUTE_EXIT_VALUES，未知或拒答用事实状态，不进取值）：Q-X01 出口 IP 来源，Q-X02 自建梯是否搭家宽出口，Q-M01 手机端（iOS、Android、两者、没有），Q-V07 VM 客机系统，Q-V08 VM 网卡模式，Q-S08 VPS 出口（自己的 IP 或套家宽）。

调度：只在路线被明确选择后才问（不由默认建议触发）。本机路线问 Q-X01，选自建梯再问 Q-X02；VM 路线问 Q-V07、Q-V08、Q-X01；VPS 路线问 Q-S08；选 Apple 或 Google 内购、或系统是仅手机时问 Q-M01。路线切换时与路线绑定的事实（含 Q-X01、Q-X02）按原规则变为 stale。值经记录时和读档时两处校验，并写入状态 schema。

对现有测试的影响：问题总数 98 增至 104；依赖“答完所有相关问题”的测试夹具补上新问题的合法取值，断言未放松；新增 tests/test_interview_route_exit.py 覆盖调度、取值校验、读写往返、schema 和路线切换。评估输出的结构未改。未做的事：没有让这些答案自动改变评估结论或授权任何动作，仍由 Agent 据此选择并附带对应资料。

## ADR-019：评估结果输出应附资料清单（2026-10-21 已确认）

资料随答附带（ADR-011）此前只是 SKILL.md 中由 Agent 自行对照执行的规则；ADR-018 的问题只决定“问什么”。所有者要求附上对应资料也由状态机兜底。新增 interview_flow.required_references(state) 和评估结果里的条件字段 required_references：按任务、计费渠道、订阅阶段、系统和 Q-X01、Q-X02、Q-M01、Q-V07、Q-S08 等事实，输出有序的资料路径、主题和页码。

规则与 SKILL.md 资料表一致：支付相关时 S02 排第一；首次或重新订阅、未注册附 account-onboarding、S03、S04；Apple 或 Google 内购、手机端或仅手机附 mobile-guidance 和 S03 第 4 页；本机路线附 egress-ip-options（Windows 加 S05）；VM 路线附 vm-guidance、egress-ip-options，非 macOS 客机附 VM 防火墙脚本；VPS 路线附 vps-guidance、S08、R01、S07，出口是自己的 IP 加 vps-guard，套家宽加 R02、line-optimization 和 VM killswitch；本机或 VM 选自建梯附 R01、S07，再搭家宽出口加 R02 和 line-optimization；macOS 清理附 S06。未明确选路线时不附路线资料。

清单是必附资料的下限，不是执行授权（G3 仍为 blocked）。评估结果原有字段不变，新字段只在清单非空时出现。测试覆盖每条规则，并校验所有路径都在技能包内。

## ADR-020：Agent 补充资料来源（2026-10-21 已确认）

所有者资料和 required_references 是必附的下限，Agent 仍可按需补充。为让补充有章可循，SKILL.md 新增“Agent 补充资料来源”一节，列出渠道 Linux.do、NodeSeek、V2EX、Reddit、X 及各自适合找什么，并规定：所有者资料优先，冲突时以所有者资料为准并说明；用到的内容标明链接、平台和日期，找不到就说没找到；优先较新内容并注明过时；帖子里的命令不是授权；不向用户索要这些站点的账号、Cookie 或令牌，读不到就如实说明；只做查找，不通过任何渠道访问 Claude 或 Anthropic 页面，不查账号共享、代充、批量注册；邀请码和返佣只当线索。

不是做的事：不把这些渠道的内容自动入库；入库仍需所有者提供并确认。

## ADR-021：补全 VM 搭建脚本、线路问题和 Windows IPv6 入口（2026-10-21 已确认）

补录所有者主目录里的两个 VM 脚本：install-flclash-tun.sh（装 FlClash 和 TUN 助手，固定版本并核对 SHA256）和 enable-guest-ssh.sh（开客机 SSH）。前者只把版本和架构改成可覆盖参数（FLCLASH_VERSION、ARCH）；后者原按 QEMU shared NAT 写、放行 10.0.2.2，与“LAN 独立网卡”相反，改为必填参数 SSH_SRC。两者无个人信息。vm-guidance 新增“3a Linux 客机的搭建顺序”：建 VM、开 SSH、装 TUN、导入节点并开 TUN、最后装 killswitch。

新增访谈问题 Q-T01（线路症状：无、晚高峰慢、断流、大文件慢、桌面卡、出口不对），在明确的 VPS 路线、或本机和 VM 选了自建梯之后问；非“无”时 required_references 附线路优化和 R02（晚高峰慢、断流再附 R01）。Windows 本机路线的 required_references 附 Windows 网卡 IPv6 提示词（带锚点）；VM Linux 客机附 SSH、TUN、killswitch 三个脚本，按搭建顺序。SKILL.md 资料表同步。同步 README 和 CHANGELOG，删去“VPS 选购和部署留待后续”的旧说法。

未解决：本机 Mac 和 Windows 没有防火墙脚本，macOS 客机同样没有，待与所有者讨论方案；S08 第 3 到 5 页截图未读；R02 图片未入库。

## ADR-022：本机路线防火墙用提示词，不写脚本（2026-10-21 已确认）

所有者决定本机路线的防火墙仍以提示词解决：Windows 利用系统自带防火墙，Mac 依赖第三方软件（LuLu）。新增 references/local-firewall-prompts.md：通用工作方式（先问清楚、先看后改、一次一张变更卡、先让 TUN 跑通再加防火墙、必须故障演练、保留回滚）；Mac 一节包含 Clash Verge 的安装、导入节点、TUN（服务模式）、DNS 核对、验证，以及 LuLu 的来源、系统扩展批准、规则思路、覆盖范围实测和回滚，不自己写 PF 规则（见 ADR-006）；Windows 一节包含 Clash、TUN、网卡 IPv6，以及系统防火墙的备份、保险丝计划任务、先加 guardian- 开头的允许规则、最后切换默认出站为阻止、故障演练、回滚、更新后复查。

接入：routes-and-platforms.md 的 L2 第 4、5 条指向它；SKILL.md 资料表新增一行；Windows 本机路线的 required_references 附它（锚点 #windows）和 S05，Mac 附它（锚点 #mac）和 macOS DNS 经验；VM 和 VPS 路线不附。

边界：命令基于 PowerShell 和 netsh 的通用用法，没有在真实机器上实测，文档要求首次使用前先用只读命令或 -WhatIf 核对参数和别名；组织管理的设备不改防火墙；不自动安装 LuLu、不替用户点系统授权；LuLu 的覆盖范围不假定，必须故障演练；不承诺免封。

## ADR-023：补全 S08 截图、macOS 客机与过时文档收紧（2026-10-21 已确认）

S08 第 3 到 5 页的截图已读：第 3 页是 IP.Check.Place 检测报告示例，第 4、5 页是 LazyVim 和 VS Code Remote-SSH 的界面截图。转述写进 S08 文字版文末（manifest 哈希同步），并在 vps-guidance 新增“怎么读 IP 检测报告”，按六部分说明看什么，结论只描述当时该 IP，不推导免封概率。R02 缺少两张图（图源/VPS-线路优化-单端中转.png、图源/VPS-线路优化-双端隧道.png），由所有者补。

macOS 客机不加脚本，全部用提示词：开“远程登录”（图形界面，用户自己点）、Clash Verge 按本机路线 Mac 提示词、防火墙用 LuLu，不自己写 PF 规则。收紧过时文档：README、implementation-tracker、agent-remediation、docs/source-manifest.json、incidents-and-integrations 里指向已移出的台账和证据目录、或仍写“七份阅读来源、S01–S07”的地方；validation.md 是按日期记录的历史，不改写。真机验收统一放到最后解决。

## ADR-024：R02 图片入库，移出 docs/validation.md（2026-10-21 已确认）

R02 缺的两张链路图在所有者的粉丝群资源目录里找到，入库为 sources/R02-images/single-relay.png 和 dual-tunnel.png（manifest 里作为 R02 的伴随文件登记，保留原文件名和哈希）。R02 文档里的 Obsidian 图片链接和 [[…]] 内部链接改为相对路径，链接指向 R01 报告 PDF；realm 配置里的 [[endpoints]] 是 TOML 表头，保持不变。line-optimization 引用这两张图。

移出 docs/validation.md：它是 1600 多行按日期记录的验证日志，大部分属于已移出的验收体系，ADR-010 曾保留它。所有者决定清理掉；README 的“当前进展”改为以 CHANGELOG 和决策记录为准，其余文档里指向它的地方改为“git 历史中的 docs/validation.md（已移出）”。可从 git 历史找回。真机验收结果以后记在 CHANGELOG 和决策记录里。

## ADR-025：分级授权，用户不需要每一步在场（2026-10-21 已确认）

所有者明确：不要每一步都在现场，只有非常重要的才在；Skill 的目标是让 Agent 在加持下按用户的需求和环境做得更好，而不是固定程序或一键修复。因此把“逐动作授权”改成按风险分档（references/authorization-tiers.md）。A：范围确认后自行做（只读诊断、查资料、出方案、预演）。B：整个计划批准一次，Agent 连续执行，计划范围内可按环境调整参数，任一步失败自动撤销并汇报。C：必须当场确认。判定看五个问题：能否自行撤销、会不会切断自己的访问、是否涉及账号钱或凭据、是否删除或不可逆、是否影响他人或组织设备；拿不准按更高一档。

C 档清单（所有者确认）：可能锁死自己的改动（默认出站切成阻止、启用 killswitch 或 vps-guard、改 SSH、关网卡 IPv6、远程机器上会切断唯一入口的故障演练）；账号和钱；凭据；删除和不可逆（含持久化 BBR）；组织管理设备的策略；接触 Claude 或 Anthropic。到 C 档 Agent 暂停并写确认单，用户不需要全程在场，可稍后回复，超时不等于确认。

不变的硬规则：PC0、PC1、PC2；付款、注册、登录、KYC、OAuth 由用户本人；不收集凭据；用户授权不能覆盖宿主和组织策略；范围确认单和计划批准单必须是用户在对话里明确给出，不能由 Agent 自己生成并默认通过，不能用代码布尔值或回调伪造。

落实：AGENTS.md 的权限条改为分档；contact-and-safety 和 agent-remediation 加说明，“具体授权／逐项批准”按档位理解；SKILL.md 新增“授权档位”一节和资料表一行；本机防火墙、线路优化、VM、VPS 文档标注各步档位；路线明确选择后 required_references 附 authorization-tiers。未做：状态机里的 G3 仍恒为 blocked，没有“计划级批准”记录，是否增加留作后续决定。

## ADR-026：状态机里留下分级授权的可追溯记录（2026-10-21 已确认）

所有者要求 B 档批准在状态机里留下可追溯记录。访谈状态新增可选的 authorization 段：scopes（范围确认单）、plans（B 档计划批准）、confirmations（C 档确认单）。对应函数：record_scope_confirmation、record_plan_approval、record_plan_result、request_critical_confirmation、resolve_critical_confirmation、use_critical_confirmation，以及只读的 authorization_check 和 authorization_summary。动作档位目录 ACTION_TIERS 与 authorization-tiers.md 一致，未知动作按 C 档；注册、登录、付款、凭据、接触 Claude 四类永远不允许 Agent 执行，即使用户确认过。

约束：授权类记录的来源必须是 user: 开头的用户明确回复，agent:、host: 或空来源拒绝，防止 Agent 自批准；范围只能含 A、B 档动作，C 档或未知动作拒绝；计划步骤必须全是 B 档且在范围内；范围绑定目标、账号、任务和路线，换路线、撤回路线选择、会话恢复都使范围、计划和确认单永久失效（stale），改回原路线也不复活；一次只有一个有效范围；已确认的 C 档确认只能用一次；存档读取时重新校验，来源被改、范围里被塞入 C 档动作、重复编号、未知字段都拒绝。

不变：记录只是追溯，不执行任何动作；访谈回答不会产生记录；评估结果的 G3 仍恒为 blocked，只多一个 authorization 摘要字段，旧字段不变；authorization_check 是辅助自查，不是执行授权。未做：命令行入口暂不提供写入这些记录的参数，由宿主通过函数调用。

## ADR-027：开放 Mac 上 Clash Verge 的配置写入适配器（2026-10-22 已确认）

所有者要求补上“没有生产环境配置写入适配器、Mac 修复链不完整”。`repair_execution._native_session` 原先始终抛 `NATIVE_REPAIR_ADAPTER_UNAVAILABLE`，现在转到固定的 `native_clash_verge_mac.session`，只放行 macOS 上 Clash Verge Rev 2.5.8 的 `rules-prepend` 扩展，路径必须是固定位置（应用 `Info.plist`、当前用户 Application Support 下的 `profiles.yaml` 和 `profiles/`），其余范围、其他平台和 `merge-policy` 照旧返回不可用，且不碰任何文件。

写入者排除：macOS 没有强制文件锁，所有者确认采用“要求应用及其核心已退出，提交前后复查”。适配器用固定命令 `/bin/ps -axo comm=`（不经 shell，最小环境，5 秒超时）列进程，应用包路径下的进程或 `clash-verge`、`verge-mihomo`、`verge-mihomo-alpha`、`clash-verge-service` 任一在运行就返回 `CLASH_VERGE_RUNNING`；进程列表取不到则 `PROCESS_LIST_UNAVAILABLE`，一律失败关闭。同时复查基础 profile、`profiles.yaml` 和 `Info.plist` 的快照与目录身份（`SOURCE_SNAPSHOT_CHANGED`），应用元数据必须属于 root 或当前用户且无组/其他可写（`APP_METADATA_NOT_TRUSTED`）。这只能发现并失败，不能阻止两次复查之间的写入，文档里写明。

Mac 修复链补全为：预检计划（A）→ 批准计划（B）→ 退出应用（B）→ 写入读回 → 重启应用（B）→ 验证出口与规则命中，失败回滚。应用的退出与重启由 Agent 通过宿主执行，不在适配器里。写入成功仍只报告 `written_but_not_verified`，应用重载和实际路由是单独步骤。

未做：FlClash、Windows、`merge-policy`、代码签名校验（Clash Verge 的签名状态未核实，避免误拦）、真机验收。进程名是按 2.5.8 常见安装整理的，需要真机核对。测试：`tests/test_native_clash_verge_mac.py` 用合成进程列表和临时文件，覆盖拒绝路径、写入者启动于提交各阶段、真实端到端写入读回和恢复批次。

## ADR-028：整机统一出口（只走 IPv4）的配置与判定（2026-10-22 已确认）

所有者要求整机出口只走 IPv4、不要 IPv6，Windows 的写入引擎先不做，改由 Agent 按提示词操作。落实为两件事。其一是 `references/whole-machine-ipv4.md`：Clash Verge 的 TUN（严格路由）、DNS、核心 `ipv6: false`、规则末尾 `IP-CIDR6,::/0,REJECT` 加兜底代理组；TUN 和 DNS 优先在客户端设置界面改，合并文件放 `ipv6: false` 与规则；按分级授权列步骤（关网卡 IPv6、默认出站阻止、远程故障演练为 C 档）；Mac 与 Windows 的取证命令；Windows 没有带事务的写入引擎，靠备份和读回哈希。其二是只读判定 `egress_verifier.py`：不采集不修改，只读 Agent 写下的证据文件（枚举取值，未观察到写 unknown 或 not_run），判 8 个必要层（tun、core_ipv6、dns、rules、exit_ipv4、ipv6_probe、webrtc、failure_drill），全通过才是 established，任一明确失败是 violated，其余 incomplete；出口地址只比较不回显，取样须来自至少两类进程；防火墙与系统 IPv6 是建议项；持续保护须重启、睡眠唤醒、换网都复验才是 checked。

不变：判定只支持提供的观察，不代表服务资格、IP 纯净或免封；旧的目标范围策略契约和 `traffic_policy` 输出没有改；不新增后台监视。未做：Windows 写入引擎；真机验收；验证器没有接入访谈评估的 `required_references`。

## ADR-029：macOS 上 C5 清理的内置宿主（2026-10-22 已确认）

所有者要求补上 C5 清理。核心（计划、隔离、对账、恢复）早已实现，缺的是 `cleanup_cli` 要求的宿主。新增 `native_cleanup_mac.py`，只支持 macOS，其他平台返回 `UNSUPPORTED_PLATFORM`；Windows 的清理按所有者前面的决定走 Agent 提示词。同意方式与备份方式均经所有者确认：同意必须由用户在真实终端（stdin 和 stdout 都是 TTY）输入 `CONFIRM <操作> <审阅摘要前 8 位>`，没有标志、文件、回调或非交互模式，同一进程内同一操作和摘要只需输入一次；备份由模块自己复制到 `~/.claude-guardian/backups/<backup_ref>`（0700，文件 0600）并写每个文件的 sha256 清单，该目录必须在受保护路径里。

范围来自所有者的 S06 清理教程：`~/.claude`、桌面端的 Application Support（Claude、Claude-3p、claude-code-desktop）、HTTPStorages、Preferences（含 ByHost）、Caches 中 `com.anthropic.claudefordesktop*`、Logs/Claude。不在清单里的路径一律 `unknown_ownership`；`~/.claude.json` 和含 `.credentials.json` 的目录返回 `credential_scope`，独立 CLI 程序、`/Applications/Claude.app`、钥匙串、浏览器站点数据、永久删除不在范围内。`verify` 同时处理隔离前后的位置：根不在原处时去隔离批次里找，并和备份清单比对（文件大小、修改时间、权限、链接目标；内容哈希在每个宿主实例里校验一次备份）。`exclusive` 在进入和退出时检测 Claude 进程，进程按可执行文件名匹配（桌面端应用包路径、`claude`、`Claude Helper*`），Node 启动的 Claude Code 会话看不到，所以确认页要求用户先退出所有会话；macOS 没有强制锁，只能发现并失败。

`cleanup_cli.py` 本身不变：普通运行仍无宿主；包装命令收下 `--host-scope` 和 `--entry-file`（私有 0600 的路线声明，不授予任何权限）。拒绝原因（`host_refusal`）打印到 stderr，因为分发器会把所有非通过结果折叠成 `HOST_SCOPE_UNVERIFIED`。未做：Windows、凭据和浏览器数据清理、卸载、永久清除、真机验收（备份会含登录状态等敏感文件，文档提示用户自己保管和删除）。测试：`tests/test_native_cleanup_mac.py` 用一次性主目录、合成进程列表和脚本化终端，覆盖清单、拒绝路径、备份校验、同意短语、排除区间，以及真实核心的备份、计划、隔离、对账、恢复往返。

## ADR-030：参考第三方 claude-cleanup 收紧 C5，补 Windows 官方路径（2026-10-22 已确认）

所有者让参考 suyuan2022/suyuan-skill 的 claude-cleanup（MIT，仅 macOS），并要求冲突部分也参考，Windows 参考官方文档。采用：其一，`~/.claude` 不再能整个当根，对话记录、历史、设置、skills、插件、命令、agents、hooks、凭据等一律保护（第三方的绝对保护清单并上官方“需要保留的状态文件”），根只能是可再生缓存/日志（官方“删除没有用户可见损失”的行加第三方缓存清单）或桌面端持久数据；其二，桌面端路径补 `com.anthropic.claudefordesktop` 的 Application Support、Saved Application State、WebKit 和 DiagnosticReports、CrashReporter；其三，由 Claude Code 或 Claude 应用启动时拒绝运行（沿父进程链，只看可执行文件名，不读参数，无法确定时按拒绝）；其四，钥匙串退出登录、`CLAUDE_CODE_SIMPLE`（官方环境变量，等同 `--bare`，不读取 OAuth 和钥匙串凭据，故订阅登录不可用，确认页明说）、用户指定的系统时区做成独立命令，各自终端确认，均为 C 档。时区由用户指定，不写死任何地区，原时区打印出来便于还原。

**不采用：**轮换 `userID`/`machineID` 并清账号缓存字段。它的作用是更换平台用来关联设备的标识，属于规避设备关联，与本项目“不轮换设备身份、不伪造地区或身份”的规则冲突，所有者要求参考时我如实说明不做。S06 里关于这两个字段的说明（不能据此宣称防封，普通退出登录不必伪造）保持不变。第三方的“继承遥测状态”采用为约束：修改 `settings.json` 后核对遥测键与修改前一致。移入废纸篓也不采用，保持私有隔离目录加对账回执。

**Windows：**新增 `references/windows-cleanup.md`，路径只用官方文档写明的：`%USERPROFILE%\.claude`、`.claude.json`、`.credentials.json`、`.local\bin\claude.exe`、`.local\share\claude`、VS Code 扩展 `globalStorage`、`%APPDATA%\Anthropic`、桌面端 `%APPDATA%\Claude\claude_desktop_config.json` 与 `logs`（MCP 文档）。桌面端其余数据路径官方没写，文档要求先只读列出再给用户看，不凭记忆。流程：只读审计（A）、哈希校验备份（B）、隔离与还原（C，对话中明确确认，没有终端短语）、凭据与退出登录单独确认；`claude purge` 要运行 Claude，由用户自己决定并先过 PC1。没有内置宿主，命令未在真实 Windows 上跑过。

测试：`tests/test_native_cleanup_mac.py` 更新为分档与受保护路径，`tests/test_native_claude_state_mac.py` 用桩命令覆盖钥匙串、简单模式和时区，`tests/test_windows_cleanup_guide.py` 检查官方路径、保护清单和不含设备标识轮换。

## ADR-031：元数据门禁容忍内核自动添加的 `com.apple.provenance`（2026-10-22 真机验收后）

Mac 真机验收（macOS 15.7.4，记录在 `acceptance-mac-2026-10-22.md`）发现：macOS 15 起内核给任何本地进程新建或写入的文件自动加扩展属性 `com.apple.provenance`，且无法移除（`xattr -d` 返回 0 但立即复原）。Clash Verge 自己维护的 `profiles.yaml`、profile 文件和应用的 `Info.plist` 都带它，Terminal.app 新建的文件也带它。而 `transactions._has_xattrs` 要求零扩展属性，所以修复链的请求文件加载（`UNSAFE_RECEIPT_FILE`）、目标文件读取（`UNSUPPORTED_FILE_METADATA`）和 C5 清理链的 scope 与 entry 加载（`UNSUPPORTED_METADATA`、`INVALID_ENTRY_FILE`）在该系统上必然 fail-closed，真机验收无法越过。所有这些门禁都经过 `tx._has_xattrs`，只改这一处。

取舍与所有者确认：该属性由内核添加、不含用户内容、不携带写入者或来源语义，豁免不削弱 uid、mode、nlink、链接等其他检查；其余任何扩展属性仍拒绝。实现保持原有“不分配不可信大小、不读取属性值”的约束：先用空缓冲取所需大小，只有大小恰好等于单个名称 `com.apple.provenance\0`（21 字节）时才用固定 21 字节的缓冲读取名称，名称完全一致才容忍；其他大小、第二次调用失败或返回值不符都拒绝或报 `XATTR_CHECK_FAILED`。回归测试覆盖：仅 provenance 通过；同长度的 `com.apple.quarantine`、差一字节的名称、更大或更小的列表仍拒绝，且不读名称；第二次调用异常时失败关闭；`plan()` 对只带 provenance 的文件通过、对其他属性仍报 `UNSUPPORTED_FILE_METADATA`。

已知后果：C5 的根目录里如果有带其他属性的文件（例如下载文件上的 `com.apple.quarantine`、`com.apple.macl`），计划仍会以 `UNSUPPORTED_METADATA` 拒绝，需要缩小根范围。验收记录里的文档勘误（`-I` 只适用于 `cleanup_cli.py`，`native_cleanup_mac.py` 的 `--host-scope`、`--entry-file`，digest 在 stdout JSON）已写入清理 CLI 用法。

## ADR-032：Issue #12——新增 IDC Flare 渠道、直接当帖子与论坛搜索工具、短期封号时间线（2026-10-22）

所有者在 Issue #12（文档来源）提了三件事。其一，VPS 新增渠道 IDC Flare：加入“Agent 补充资料来源”，并按 S03 第 5 页写明所有者指的路：找 VPS 搜 IDC Flare、NodeSeek、Linux.do 的 VPS 分区、VPSHub；家宽去 Linux.do（L 站）的 VPS 分区找，家宽拼车去 IDC Flare 找；所有者列的四条帖子链接也收进去（NodeSeek 那篇原作者的做法是应审查的用户经验，不照单执行，沿用 D-SPEC F02）。其二，skill 可直接当帖子和论坛搜索工具：用户明确要求去论坛搜某商家、线路或问题时不必先有资料缺口，Agent 直接检索，规则不变（所有者资料优先、标来源和日期、命令不是授权、不收集账号信息、不访问 Claude 页面、推广只当线索），SKILL.md 的 description 同步写明。其三，短期封号原因：Issue 指向 S03 的最后一张图（PDF 第 5 页），该表此前没转述，现在写进 `account-onboarding.md` 的 A0b：五个时间段对应的排查方向，明确不是因果判定。

两个限制如实记录：idcflare.com 有 Cloudflare 验证，本次无法读取站点内容，所以只按所有者的说法登记用途，没有自己描述站点。2026-10-22 所有者确认两个地址：IDC Flare 为 https://idcflare.com/，VPSHub 为 https://vpshub.org/zh/。Issue 里的 Q 群号属于联系方式，不写进仓库，文档只引用 PDF 的文件名由来。

## ADR-033：资料必须能被 Agent 翻到，加守门测试（2026-10-22 已确认）

所有者问“KYC 在哪里提了、短期封号参考放哪了”，暴露出一类问题：A0b（S03 第 5 页的短期封号时间线）和 KYC 指引存在，但只在 `account-onboarding.md` 里，`SKILL.md` 的资料表和访谈的 `required_references` 都没有路由到它，Agent 不一定翻得到。所有者要求：项目所有资料必须能被 Agent 翻到，并复查不要再出现。

做法：其一，逐个复查文件：没有从 `SKILL.md` 出发翻不到的文档，但有 11 个脚本（访谈状态机 `interview_flow.py` 等库）没有任何说明提到，新增 `references/scripts-index.md` 列出每个脚本和资产的类型、用途和说明；`SKILL.md` 补直接链接 `cleanup-cli-usage.md`、S03/S08 文字版、`manifest.json`、设计规格。其二，主题路由：资料表新增“账号被封或被限、问多久被封的、KYC 触发或身份核验”必附行；访谈 `required_references` 新增三类：事故为 suspension 或 identity_review、或 Q-D01 有当前或过去限制时附 A0b、S03 第 5 页、S04、M12，身份核验再附 A3；本机路线附整机 IPv4 出口；清理任务按系统附 S06 与 cleanup-cli-usage（macOS）和 windows-cleanup（Windows），系统未知时两类都附。同一文件需要多个页码时合并（`p.4, p.5`）而不是丢掉。其三，守门测试 `tests/test_skill_discoverability.py`：每个随包文件沿着提及链从 `SKILL.md` 能到达（只有说明文字算路由，代码互相导入不算）；每个 references 和 sources 顶层文件在 `SKILL.md` 里直接点名；脚本索引与 `scripts/`、`assets/` 一一对应；`SKILL.md` 和 references 里的相对链接及锚点都能解析；资料表里的承诺主题（封号与 KYC、清理、整机出口、线路、VPS、VM、手机、出口来源、IDC Flare、VPSHub）都有行。

不变：必附资料是下限，不是执行授权；A0b 仍然只是排查方向，不断言原因，不承诺免封或免 KYC。限制：测试检查的是“能到达”，不能判断路由得是否恰当；仓库里不随包的 `docs/` 不在 Agent 的加载范围内，不检查。

## ADR-034：章节级可发现性与自动附资料补全（2026-10-22 已确认）

ADR-033 之后实测：文件层可达 100%，但章节层很低（232 个 H2/H3 小节里只有 10 个被锚点指到），访谈能自动附上的文档 23/35，核心参考 `routes-and-platforms.md` 和 `network-and-remedies.md` 不在其中。所有者要求继续收紧。

做法：其一，新增 `references/section-index.md`，由 `tools/gen_section_index.py` 生成（围栏代码块里的 `#` 不算标题，重复标题加 `-N` 后缀，规则同 GitHub），列出每份 reference 的每个二、三级小节和锚点链接；`SKILL.md` 的“按需加载”指向它，说明定位到文件后到这里找小节。其二，访谈 `required_references` 新增 `routes-and-platforms.md`（路线选定后附，定位符指向对应路线的操作卡：本机、VM、VPS）和 `network-and-remedies.md`（任务为 network 或 environment 时附）。其三，守门测试补三条：提交的索引必须与生成结果一致；每份 reference 的每个小节都有索引链接；访谈能发出的每个 `#锚点` 定位符都能在目标文件里解析。第三条立刻查出一个真实缺陷：ADR-033 给 A0b 用的定位符 `#a0b` 在文件里并不存在（真实锚点是长标题），已在标题前加显式 `<a id="a0b"></a>`。

仍不是自动附的文档（刻意）：`intake.md`、`contact-and-safety.md`、`evidence-policy.md`、`source-library.md`、`scripts-index.md`、`agent-rules-task.md`、`S01` 术语表，以及 S03/S08 的文字版副本。它们是通用参考或来源副本，不对应某个访谈事实；Agent 仍从 `SKILL.md` 一跳可达。限制：索引保证小节“能被找到”，不保证 Agent 在合适的时候去找；主题到小节的判断仍靠资料表和必附资料。

## ADR-035：Mac 真机验收结果（F2 修复后，2026-10-22）

验收记录在所有者的 `Omarchy/Claude-Guardian-验收-20261022/验收结果记录.md`，设备 MacBookPro18,1（M1 Pro），macOS 15.7.4，Clash Verge Rev 2.5.8（默认路径，未开 TUN）。验收期间由 Agent 宿主（WorkBuddy）做只读和自动化部分，所有需要真人输入确认短语的步骤留给所有者在 Terminal.app 做。

**真机通过：**4.2b：版本 2.5.8、默认路径、uid 归属；进程名与代码一致（`clash-verge`、`verge-mihomo` 在 `/Library/Application Support/clash-verge-service/cores/`、`clash-verge-service`，`verge-mihomo-alpha` 本机没有）；`plan` 返回 `planned_but_blocked`，差异是在偏移 64 处插入一条规则，保留计划摘要在两次独立运行中一致，与 `MATCH,PROXY` 的优先级重叠如实记录，归属报告如实标出 script、merge 链不受支持；应用运行时 `execute` 返回 `CLASH_VERGE_RUNNING`，目标文件哈希不变，没有生成备份。4.4：`egress_verifier.py` 五条判定路径（established、两种 violated、incomplete、INVALID_EVIDENCE）符合预期，报告不含出口 IP。4.5：`context`、`allowed`；Agent 会话里 `RUNNING_UNDER_CLAUDE`；Claude 运行时 `ACTIVE_HOST`；没有输入短语或非终端一律 `AUTHORIZATION_REQUIRED`；scope 结构门禁（`QUARANTINE_OVERLAP`、`ENVIRONMENT_ENTRY_REQUIRED`、`UNSAFE_DOCUMENT`）正确拦截（期间修正的三处是验收脚本自己配错）。4.6：钥匙串服务名核对一致（Safe Storage 存在，Code-credentials 未找到）；Claude 运行时 `keychain` 返回 `ACTIVE_HOST`；非法时区含 `..` 返回 `INVALID_TIMEZONE`。F2 的修复（ADR-031）已覆盖修复链和 C5 链，两条链的文件元数据门禁都走同一函数。

**没验（需要真人或 C 档批准）：**4.2b 的真实写入、读回、重启后规则命中、回执回滚、plan 与 execute 之间启动应用的演练；4.5 放行全流程（backup、plan、quarantine、reconcile、restore，以及 `shared_scope`、`credential_scope` 的拒绝页，这些都要先输入确认短语）；4.6 的真实钥匙串删除、`simple on/off`、真实时区变更；4.2 的 TUN、LuLu、fail-closed 演练；4.4 的 GUI 联网取证和重启、睡眠、换网复验。

**需要注意的两点：**其一，真实 profile 的计划里带 18 个 blockers，包括 `PROFILE_SCRIPT_CHAIN_UNSUPPORTED`、`PROFILE_MERGE_CHAIN_UNSUPPORTED`、`GLOBAL_SCRIPT_CHAIN_UNSUPPORTED` 和 `LATER_MERGE_SCRIPT_EFFECTS_UNVERIFIED`：这个 profile 有 script 和 merge 链，写进扩展的规则可能被后面的链改写。`apply_supported` 仍为 false，写入只证明文件字节，`effective_routing` 是 `not_run`，所以真实写入之后必须重启并探测，不能把写成功说成生效。其二，计划里仍报 `NATIVE_SCHEMA_ADAPTER_NOT_IMPLEMENTED`，而此范围已经有写入适配器：这个名字指的是另一件事（原生配置模式适配），措辞容易误读，已记下，没有改动，改动会牵动一处严格集合比较。

**环境记录，不是仓库缺陷：**Agent 宿主沙箱里 `ps`、`pgrep` 被拦，宿主创建的文件带 `com.apple.provenance`；CPython 导入期的 `os.supports_dir_fd` 探测在该沙箱内间歇失败，导致在该会话里直接跑仓库测试出现大量假失败，仓库测试应在 Terminal 或 CI 跑。

## ADR-036：真机验证是样本，环境差异由 Agent 按实际环境处理（2026-10-22 已确认）

所有者认为把真机验收当作完成标准不合理：一个人测通一台机器，不代表别人的系统版本、应用版本、安装位置和宿主环境都一样；用户本来就有 Agent，环境不一致时让 Agent 按实际环境修更现实。采纳。

变化：其一，`SKILL.md` 新增“每台机器环境不同”一节，把 Agent 的做法写成规则：先只读核对实际环境（A 档）；差异在已批准的计划范围内就调整参数并沿用备份与回滚，超出范围重新出变更卡按档位批准；失败就停下并回滚，如实报告哪一步、实际看到什么、和文档哪里不同；不为让命令通过而放松进程检查、元数据和属性检查、保护路径、终端确认，也不改写返回值；不把一台机器上的结果说成通用；差异值得记时由用户决定是否合入仓库。其二，README 的“不是什么”把“没有在真实机器上验收”改为“没有对每台机器的保证”，AGENTS.md 的验证条增加同样的定位。其三，真机验收清单继续保留，但性质是样本验证，不再阻塞任何交付；稳定版本发布仍须所有者确认。

不变：诚实标注——写明在什么环境验证过，没验的写 unknown，不跨平台冒认验收；所有门禁照旧 fail-closed（这一次真机上出现的 `com.apple.provenance` 就是例子：门禁拦住了，原因被查清后才有针对性地放宽，而不是绕过）；PC0、分级授权和“Agent 不能自己批准 C 档”不变。

## ADR-037：不要让用户烦——少确认、不循环、被拦时说人话（2026-10-22 已确认）

所有者要求没有多余操作、循环操作、过度严格的检查把用户烦死。先审计，再收紧该收紧的，不降低安全要求。审计结果：访谈默认订阅流程约 20 个问题、VPS 路线约 28 个，偏长；macOS C5 一整轮要在终端输入 7 次确认短语（备份、读取范围、保存计划、隔离、读取对账、保存回执、还原），其中 4 次是同一件事的拆分；门禁被拦时输出只有错误码，用户不知道该做什么。

处理：其一，`SKILL.md` 新增“少打扰用户”八条，约束 Agent 的行为：能读到的不问；访谈只问当前任务要用的，相关的合并问（一次不超过 3 个），用户说不知道就记 unknown 继续；同一范围只确认一次，C 档确认单一次写清；环境没变不重复检查；同一失败最多换一个有明确理由的办法重试一次再停；被拦时说人话；只读和可自行撤销的事不升级为 C 档；汇报要短。访谈状态机本身没有改，问题数量由 Agent 按这些规则控制，不再把全部问题走一遍。其二，C5 宿主把确认分组：备份、计划（读取范围和保存计划合并成一次，提示里显示宿主自己核实过的范围）、隔离、还原各一次，共 4 次；对账和保存回执只读已批准的内容并写私有记录，不再询问。移动或复制敏感数据的步骤一律仍要输入短语，且各组互不共用。其三，`native_cleanup_mac.py` 和 `native_claude_state_mac.py` 被拒绝时在错误码之外输出一句中文 `hint`，例如“请先退出所有 Claude 桌面端和 Claude Code 会话”“请在普通终端运行”。

不变：所有 fail-closed 门禁、受保护路径、终端确认短语、Agent 不能自己批准 C 档。没有放松检查，只是不重复问、不拆开问、不只给错误码。未做：压缩访谈问题集本身（保留，由 Agent 按规则取用）；对其他 CLI 的错误输出统一加 hint（先做 macOS 清理相关）。

## ADR-038：把教程发布到 GitHub Wiki，仓库仍是唯一来源（2026-10-22 已确认）

所有者要求把教程都搬进 wiki。wiki 是 `<仓库>.wiki.git` 这个独立的 git 仓库，不随 skill 打包，Agent 读不到，也不在可达性和守门测试里。如果真的把 `references/` 搬走，Agent 就读不到规则和指引，所以采用“渲染一份副本”：仓库的 `skills/claude-guardian/` 仍是唯一来源，wiki 是面向用户的展示页。

范围：面向用户的步骤类教程 12 篇——账号注册与养号节奏（含 A0b）、手机端防封、固定出口 IP 的来源、整机统一出口、本机 Clash 与防火墙、VM、VPS、线路优化、macOS 清理（S06）、Windows 清理、VPS Claude 教程文字版（S08）、线路优化与家宽中转教程（R02，含两张图）。不导出的：规则与依据类文档（授权档位、修复流程、接触与安全、证据政策、来源库、各索引）、设计规格、脚本、PDF 与 17 份 VPS 报告（页面里链接到仓库文件，图片用仓库的 raw 地址）。`tools/export_wiki.py` 生成每页加“自动生成，请到仓库修改，不要直接改 wiki”的横幅、首页（分组目录、频道、不承诺免封和环境差异提醒）和侧边栏；相对链接改写为 wiki 页面或仓库 blob 链接，代码块里的链接不改；每次导出前扫描，出现所有者出口 IP、局域网段、用户名、本机路径、手机号、QQ 群号（频道 QQ 除外）、凭据样式内容、订阅链接协议头就拒绝导出；重新导出时只删除自己生成过的旧页，不碰手写页。

发布方式：GitHub 在网页上创建第一页之前，wiki 仓库不存在（`git ls-remote` 返回 not found），所以第一次需要所有者在 Wiki 标签点一次“Create the first page”并保存；之后把导出结果推到 wiki 仓库。未做：用 GitHub Action 在每次 main 更新后自动同步（要给 workflow 写 wiki 的权限，先不加，由所有者决定）；17 份 VPS 报告和 S04、S05、S07 等阅读材料不放 wiki，页面里指向仓库。

## ADR-039：Mac 真机验收收官，按真机发现修正（2026-10-22）

证据与日志按所有者要求留在 Omarchy（`Claude-Guardian-验收-20261022/`，含最终版验收记录、截图、日志、一键脚本、判定报告），不进仓库，因为含用户名、本机路径、真实 profile 文件名和摘要；仓库只记结论。设备 MacBookPro18,1，macOS 15.7.4，Clash Verge Rev 2.5.8，一台机器。

**真机通过：**4.2b 全项：版本、归属、进程名；`plan` 三次独立运行摘要一致；应用运行时 `execute` 返回 `CLASH_VERGE_RUNNING` 且哈希不变；真实写入返回 `written_but_not_verified` 和 `byte_readback: pass`，重启后规则在场，`recovery_cli rollback` 返回 `restored`，哈希回到基线。4.4：判定器五条路径，TUN 开启下的 GUI 取证（出口一致、DNS 与 WebRTC 无泄漏），自动取证判定 `established`（8 层全 pass，`persistence: checked`）。4.6：系统时区真实切换并恢复，钥匙串服务名一致，`simple` 确认页完整。4.5：全部拒绝路径；放行全流程所有者暂缓。第 6 项：界面设置覆盖合并文件同名字段，与文档一致。**未验：**4.5 放行全流程、LuLu 与停核心的 fail-closed 演练、重启与睡眠唤醒与换网的复验、`simple` 真实开关、真实钥匙串删除、VM、VPS、Windows、手机。

**由真机发现而改的：**其一，写入者排除过严：旧实现把核心 `verge-mihomo` 和 root 服务 `clash-verge-service` 也当写入者，而退出应用（⌘Q）后服务因 KeepAlive 仍在运行，写入恒被拒，只能 `sudo launchctl bootout`（还会断 TUN 与代理）。实际只有应用写 `profiles.yaml` 和 profile 文件，核心和服务不写，所以只认应用（`clash-verge` 和应用包路径下的进程）。这是一次放宽，依据是真机行为和谁真正写这些文件；如果以后发现核心或服务也会写，回滚此改动即可。其二，F4：`systemsetup -settimezone` 返回后 `/etc/localtime` 异步更新，立即读会误报 `TIMEZONE_VERIFY_FAILED`；改为每 0.5 秒读一次、最多 10 次，仍不符才报失败，没有固定长等待。其三，`ACTIVE_HOST` 提示补残留后台进程（例如 Claude 的 `chrome-native-host`）的排查办法。其四，文档：整机出口一节补“IPv6 探测返回 IPv4 字符串（被代理接管）记 unreachable，不要当 IPv6 样本”（F5 的误判来自这里）、界面设置只有对应开关启用时才覆盖合并文件、严格路由默认可能关着（关着时 fail-closed 靠 LuLu 或系统防火墙，建议开启）。

**判断：**F5（TUN 下 IPv6 泄漏）已被所有者的验收撤回为误判，没有改判定器：判定器拒绝把 IPv4 字符串标成 IPv6 样本是正确行为。F3 与 F1 是宿主沙箱的环境限制，不改仓库。此验收只代表这一台 Mac，其他环境由 Agent 按实际核对（ADR-036）。

## ADR-040：真机验收交给使用者（2026-10-22 已确认）

所有者认为逐项做真机验收太累，且一个人测通一台机器不代表别人的环境（ADR-036 已采纳“真机验证是样本”）。决定：不再逐项做真机验收，交给使用者在自己的环境里验证。

落实：其一，README“开发与验证”里把“下一步仍包括真实环境验证和完整清理验收”改为“真机验证由使用者来做”，写明作者只验证过一台 Mac（结果见 ADR-039），VM、VPS、Windows、手机和其他系统与应用版本没有验证，也不再逐项验收，并给出反馈入口。其二，新增 Issue 表单 `.github/ISSUE_TEMPLATE/device-report.yml`（“真机使用反馈”）：选用的是哪一项、系统与应用版本与 Agent 宿主、结果（走通、需要调整、被门禁拦住、出错、文档不一致）、具体情况，并要求确认没有贴账号、凭据、订阅链接、真实 IP 或个人路径；使用者的反馈再由作者按需要改脚本或文档。其三，所有者本地的真机验收清单继续存在，但不再是任何交付的条件，也不再追踪。

不变：诚实标注——没验证的环境写未知，不写通过，`native_acceptance` 仍如实报 `not_run`；所有门禁 fail-closed；Agent 按实际环境核对、调整、失败回滚并如实报告（SKILL.md“每台机器环境不同”）；稳定版本发布仍须所有者确认。

## ADR-041：验证口径——作者都验证过，但每个人的环境不同需要调整（2026-10-22 已确认，更正 ADR-040 的措辞）

ADR-040 的 README 写成“作者只在一台 Mac 上验证过，VM、VPS、Windows 作者没有验证”，所有者指出不能这么写：作者在 Mac、Windows、VM、VPS 上都验证过，正确的表述是“都验证过，但每个人的环境不一样，所以需要按实际调整”。采纳。README“它不是什么”和“开发与验证”、SKILL.md“每台机器环境不同”、Issue 表单“真机使用反馈”、wiki 首页同步改为这个口径。

边界要说清楚：这是所有者的第一手说法，Windows、VM、VPS 的验证记录在所有者那里，没有进仓库，仓库里只有 Mac 这一轮的逐项结论（ADR-039）。所以 README 只写所有者自己的整体说法和 Mac 的具体结果，不替 Windows、VM、VPS 逐项写“通过”；本项目新写的内容（例如 `vps-guard.sh`、Windows 清理提示词、整机出口指南）的具体通过项，以所有者提供的记录为准，没有记录的不在仓库里写成已通过。不变：Agent 按实际环境核对和调整、失败回滚并如实报告、门禁 fail-closed、`native_acceptance` 仍如实报 `not_run`、稳定版本发布须所有者确认。

## ADR-042：进阶路线做成叠加在 VM／VPS 之上的指引层，不新增路线值（2026-10-24 已确认）

所有者提供新一轮真实经验：本机管理端、本地 VM、他人网络里不可直连的远端 Omarchy、兼任出口节点和隧道中转的 VPS，要求把它做成进阶路线，并把其中可共用的修复和完善也补进现有指引。

取舍：路线值 local／vm／vps 写死在访谈状态机、环境入口门禁、迁移、清理和测试里，加第四个值要动门禁和迁移，风险大。所有者选择指引层：新增 `advanced-route.md` 与 R-ADV 卡，不改 route 枚举和 `environment_entry`；目标机按 vm_guest／vps 绑定，中转 VPS 按 vps 绑定，管理端按 local 绑定，证据仍分开记录。访谈只加一个路线内问题 Q-V09，按 ADR-018 的先例（Q-V07、Q-V08 同样是路线内必答），因此 VM 路线的“已答完”夹具要补 Q-V09。脚本选择合并：killswitch 加可选隧道白名单，不另放 remote 版，避免两份脚本漂移。

边界：隧道和 killswitch 在他人网络里属于 C 档，需要网络所有者同意和独立救援入口；密钥由用户生成传入，不内嵌；真实 VPS 地址、端口、用户名不进仓库。IPv6：所有者总结里的“盲区”在本仓库脚本里已被 `inet` 家族的 policy drop 覆盖，文档改为“换环境后实测”，不另写规则。

## ADR-043：README 去掉重复的防御性说明；Issue #13 的 Windows 防火墙反馈并入本机指引（2026-10-25）

所有者指出 README 防御性太强。README 原来在“它不是什么”“核心场景”“工作流与门禁机制”“开始前要知道”和路线说明里反复写同一组限制，读者先看到一堆“不能”“不代表”。改为：能力表之后只留一节“几条底线”（钱和账号本人来、不要凭据、准备阶段不碰 Claude、按环境调整、不保证免封），路线表写成“适合谁、主要内容”，删去示例、Star History 等处的免责句；门禁细节仍在 Skill、`contact-and-safety.md` 和 `authorization-tiers.md`，开发者折叠区保持原样。英文版同步。规则本身不变。

Issue #13（Windows 真机反馈，Agent 自行编排，已回滚）并入 `local-firewall-prompts.md` 的 Windows 一节：`::1` 规则在部分 Windows 上被拒，改用回环软件接口并说明单值 `InterfaceAlias` 读回是字符串；核心程序路径以运行中的进程为准（服务模式跑的是另一份核心）；新增“切换后不通：分层诊断”（显式本地代理 → IPv4 字面地址经 TUN → 系统 DNS → 域名 HTTPS，配 curl 退出码对照，四步通过后才做故障演练）、“查 WFP 丢包记录”（显式输出文件，查询失败不等于无事件，可撤销的失败审计）、“宿主拒绝执行时”（停下、确认安全状态、交接，不绕过）和“最小反馈清单”。Issue 的根因未知，文档不替它下结论。

随后按所有者要求检查全项目的过度防御，改了三类：一是与记录不符的“没跑过”：`whole-machine-ipv4.md` 写“没有在真实设备上跑过”，但 ADR-039 已记录 Mac 真机判定 `established`，改为写明验过什么、还缺什么；`local-firewall-prompts.md` 的“没有在真实机器上实测”按 Issue #13 改为第 1 到 4 步在一台 Windows 上跑过、第 5 步还没跑通。二是同页重复的免责句（防火墙页两处“不承诺免封”留一处）。三是 SKILL.md 的 description 和版本说明：原文只写“有限只读检查和离线修复计划”，并堆了一串“不是默认执行权限”“仍有未验收项”，既低估了实际能力（Agent 按分级授权配置、部署、复测）又让 Agent 一开始就带着防御心态，改为直接说做什么。没改的：PC0、授权档位、凭据、付款本人这些硬规则；`vps-guidance.md` 与 `windows-cleanup.md` 的“没有在真实机器上跑过”（按 ADR-041，所有者没给出对应记录前不改）；SKILL.md 中后段的宿主库契约说明（约一半篇幅，是否移到单独的 reference 待所有者决定）。

## ADR-044：宿主库契约说明移出 SKILL.md（2026-10-25 所有者确认）

SKILL.md 每次运行都整篇载入，原 42KB 里约一半是宿主库和内置入口的契约说明（repair/recovery/inventory、诊断会话、面板、DNS、STUN、配置候选、环境入口校验、旧目标范围契约），几乎全是“不代表、不证明、仍阻塞”，普通任务用不到，却让 Agent 一开工就背着这些限制。所有者同意优化：原文一字不删移到 `references/host-libraries.md`，SKILL.md 换成“内置脚本与宿主库”短节（常用入口各一行 + 链接）并在按需加载列表里登记；顺带更正 SKILL.md 中“当前尚无开放的内置生产配置写入适配器”（与 ADR-039 已开放的 rules-prepend 矛盾）。SKILL.md 降到约 29KB。规则不变：门禁、授权档位、证据口径都在，只是换了位置，用到对应脚本时再读。发行包 115 个成员。

## ADR-045：Agent 对用户说话的方式——规则给 Agent 执行，不念给用户（2026-10-25 所有者要求）

所有者反馈：Agent 读完 Skill 后满口“不保证、不成立、不改变、不背书”，用起来很烧心。原因是 Agent 会照抄它读到的语气：SKILL.md 和 references 里约 208 处这类说法，脚本输出到面板和动作清单的文字里还有约 24 处。

处理分三层。第一层，SKILL.md 开头新增“和用户说话的方式”：门禁和证据口径是给 Agent 执行的规则，对用户只说做了什么、看到了什么、下一步谁做；限制只在用户要越过时说一次并给出路；列出不要说的句式；免封只在用户问到时说一次；所有者经验按事实直接说；汇报用“已确认 / 还没查 / 下一步”。第二层，SKILL.md 其余部分去掉这类句式，同样的约束改成正面说法（例如“配置导入后要实测确认生效”代替“配置已导入不等于已经生效”）。第三层，面板、动作清单和探测样本的用户可见文字改为“另测”“还要另查”“以实测为准”，判定逻辑和状态值不变：unknown、not_run、verified 的条件一条没改。A0b 短期封号时间线的开头和用法同步改写。

测试：三条原本锁定旧措辞的断言改成新措辞（意思相同：DNS 路径要另查、时间线给方向再查证据）；新增守门测试，SKILL.md 除说话方式一节外不再出现这些句式，三个脚本的用户可见文字也不出现。下一步：references 按需读取的文件（agent-remediation.md 57 处最多，其次 accounts-and-payments、routes-and-platforms、incidents-and-integrations、intake）分批改写。
