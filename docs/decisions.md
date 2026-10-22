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

