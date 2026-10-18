---
name: claude-guardian
description: 为 Claude 订阅准备、账号与客户端异常、代理和运行环境问题提供分阶段访谈、有限只读检查和离线修复计划。覆盖 macOS/Windows 本机及可选 VM/VPS 路线、清理规划；不承诺免封；默认CLI不自动联网或修改系统，可选宿主库须逐项授权并满足可信目标/运行时前提。
---

# Claude Guardian

**0.2.0 工作流增量版**：访谈、获准的本地元数据检查、离线分析、面板和修复计划。默认CLI不自动联网、付款、清理或配置修改；可选探测库及限定POSIX事务/恢复接口须符合各自可信宿主、精确范围和即时授权契约，不是默认执行权限。原生设备与完整场景仍有未验收项；计划或样本不等于修复完成。

## 开始方式

1. 优先由 **Codex** 编排。分别确认执行宿主与实际目标；云端 shell 的信息不能冒充用户 Mac 的结果。仅使用当前可用且获准的工具；没有结构化提问界面时使用短问句，不伪造按钮。
2. **默认用中文交流、提问、解释报告**，保留技术 ID/命令原文；用户明确选择其他语言时跟随。先复用已有事实，再补缺口。首个缺失的业务问题是 **Q-J01：首次准备订阅、到期后重新订阅，还是当前已有订阅？** 随后询问 Mac/Windows 与用途。技术熟练度不代表付费状态；紧急事故优先。
3. 本机是默认建议，但要问用户接受本机、选择 VM/VPS，还是先比较。三者是独立方案，不是升级顺序。已明确的目标优先；拥有 VPS 不等于选择远程工作区。
4. 按需读取 [intake.md](references/intake.md)，使用稳定问题 ID 和 G1/G2/G3。**Q-C07 永久停用**，不得换名称恢复账号归属/控制权问题。首次订阅无实际冲突时跳过旧套餐/旧渠道题。
5. 每次工具操作前遵守 [contact-and-safety.md](references/contact-and-safety.md)。从 **PC0** 开始：不接触 Claude/Anthropic、不安装或运行客户端、不登录、不查看订阅页。公开文档、DNS、HEAD、`claude --version` 及委派 Claude 工具也不是例外。使用随包历史依据，待核验的现行事实明确标出。
6. 只在获准目标范围内使用已实现 CLI 检查（先查看 `scripts/guardian.py --help`）。缺依赖不静默安装；未支持的检查记为未知。内置功能未开放时，Agent继续调查实际环境；不得用临时命令绕过权限拒绝、PC0或既有执行门禁。独立Agent修复须按 [agent-remediation.md](references/agent-remediation.md) 取得具体动作许可并提供最小差异、备份与复测。
7. 交付具体问题、目标范围、证据、未知项、最小修复建议、保留项及下一步。`pass/fail/unknown/not_applicable/blocked/skipped` 只描述指定检查。盘点完成不等于 PC-G1 通过；离线测试不证明平台支持或网络隔离。

## 完整访谈入口

完整状态化访谈使用 `scripts/interview_cli.py`：默认仅输出下一题和阶段评估；已确认答案通过本地 answer JSON 传入；用户明确要求保存时才指定 `--output`。普通读档或连续轮次用 `--input`；真正中断后继续须加 `--resume <本次事件别名>`，按 [intake.md 的续接规则](references/intake.md#interruption-and-resume) 先核实相关变化，再规划。95 个问题 ID 按条件调度，Q-C07 始终停用。`guardian.py interview` 保留为兼容的简化入口，不把它的八字段流程当作完整访谈。

由 Agent 编排检测、解释、选择内置动作、具体确认、执行和复测，详见 [agent-remediation.md](references/agent-remediation.md)。`scripts/agent_remediation.py select --input <本地报告.json> --target-ref <目标别名>` 生成结构化动作清单；只读脚本、候选、宿主库和 Agent 环境修复分开，不执行清单或从JSON恢复权限。当前尚无开放的内置生产配置写入适配器；内置脚本修不了时，由 Agent 继续检查实际环境，使用具体获准的宿主工具或经审阅的限定临时脚本完成独立最小修复、备份恢复和复测。内置门禁仍不能绕过；选择器本身不是已完成修复。不能自行提供一个返回 True 的授权回调代替用户确认。

## Agent内部修复入口（按动作能力分流）

`scripts/repair_cli.py`提供精确文件的`preflight / plan / diff / execute`接口。`plan`显式指定`--plan-file`和`--backup-directory`才写入新的私有计划文件，不修改目标；`--private-review`可在获准的私有Agent会话中非交互展示选定规则及policy前后差异，不输出无关配置。私有差异不得混入公开报告。

已确认交互是Agent展示具体改动、目标、影响、备份及恢复路径，用户在对话确认后，由可信宿主核对该次授权并调用固定内部脚本；不要求第二次终端确认码。宿主将确切`retained_plan_digest`、目标与备份范围绑定到本次操作；摘要只是完整性检查，不是授权。不能用JSON布尔值、任意回调、临时shell改写或终端模拟绕过权限。

`scripts/repair_execution.py`保留计划有效期、请求摘要、原文件身份和内容、候选一致性复核、事务备份及读回链路；生产原生适配门禁目前始终返回`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`，不得宣称实际修复完成。必须先完成实际产品/版本、活动配置/自有扩展归属、合并语义及写入者排除适配与验证。Linux临时夹具中替换适配器的测试不开放用户Mac/Windows能力。恢复仍遵循独立`recovery_cli.py`契约，不自动覆盖后续改动。

`scripts/clash_verge_258.py`只校验调用方提供的2.5.8应用plist、配置索引和扩展字节之间的声明一致性：current→活动profile→显式option.merge或option.rules→唯一同类型扩展及basename。拒绝跨profile共享扩展、全局默认UID及路径/文件别名歧义。该库不读取真实文件，不证明实际安装/运行归属；输出始终为supplied_metadata_only。merge的rules数组替换基础数组，不能将rules扩展的prepend/append/delete混当此格式；脚本/后续链、内核版本、真实写入者排除和验收仍阻塞，不能以该结果开启execute。

`--candidate-kind rules-prepend`提供独立的rules扩展候选：必须显式给出`--base-path`、`--app-info`、`--profile-index`及`--extension-uid`，经安全读取核对所提供的2.5.8声明链和当前基础profile路径。只向现有空`prepend: []`插入用户明确排序的DOMAIN/DOMAIN-SUFFIX规则；`delete`必须为空，`append`与其他字节保持不变。拒绝已知受保护规则冲突，不把调用方声明的控制路径或优先级当作验证。私有差异包含已知优先级影响；未知链和原生执行继续阻塞。

保留计划格式为`guardian-retained-repair/0.2`，绑定候选类型、UID和基础配置/plist/索引的精确路径、父目录及文件快照。执行参数必须一致，提交前与读回后复核；旧0.1计划必须重建并重新展示确认。完整输入格式及命令见仓库`docs/rules-extension-plan.md`。不得用此入口初始化空merge、替换完整rules数组或绕过xattr限制。

## 限定静态盘点入口

`scripts/inventory_cli.py capabilities` 查看实际开放范围；`workflow-status` 仅显示新建且关闭的门禁。`static-audit` 只读取用户明确列出的本地配置，要求新的精确范围终端确认，拒绝保存的授权字段；目标身份/本地文件性质仍需可信宿主核实，终端输入不能代替宿主或操作系统权限。缺少可选PyYAML时停止，不自动安装。静态声明不代表运行时路由。Windows安全静态读取、控制器原生绑定、系统改写与自动恢复未开放。

控制器盘点与Windows只读计划是供可信宿主集成的库，不能绕过尚缺的原生身份/权限适配。workflow_guard提供即时资格判定，不是进程隔离或可持久化执行授权。

`scripts/remedy_plans.py` 提供四种方向的离线语义计划：保留现状、显式代理规则、TUN规则、限定兼容处理。它不生成可执行配置补丁，不开放apply；需要可信宿主提供私有快照绑定和公开别名。现有inventory CLI不能直接提供全部输入。结果中的DNS图、协议、控制路径和规则范围只依据投影事实；缺失或冲突保持阻塞，不推导已修复。

Windows监听者核对库 `scripts/windows_listener_binding.py` 仅供可信宿主显式集成：核对限定回环端口的PID、创建时间和同用户关系，不发控制器请求；为此会在私有内存读取有界监听表再筛选，必须向用户披露并获准。命名空间仍为宿主断言，不能据此声称独立原生核实或完整应用实例绑定。

网络库收到429时只报告有界Retry-After提示，不自动等待或重试。日期提示需要可信的响应接收时钟；未知、无效或过长值保持未知。

独立STUN库 `scripts/stun_probe.py` 仅在可信宿主提供当前精确范围授权、目标和取消检查后使用。没有CLI或自动触发，名称到固定数值地址的绑定由宿主另行核验；本模块不解析DNS。Cloudflare候选选择不等于任何一次公网执行授权，映射响应不认证提供方，也不证明浏览器或Claude路径。

POSIX独立恢复入口为 `scripts/recovery_cli.py`，须与 `transactions.py` 预先保留在可信本地位置。inspect只读用户选定回执；preview/rollback仍只接纳已应用回执。reconcile须绑定独立确认的目标、备份批次与回执摘要，只读观察选定记录；仅v2 prepared的候选匹配状态可用restore-prepared另行恢复，并要求上次私有观察的完整摘要、实际排除其他写入者及真实终端逐阶段新确认。旧prepared或冲突状态不写入，不重放apply；摘要和回执不是授权，Windows不支持。Agent宿主的对应调用及失败处理见 [agent-remediation.md](references/agent-remediation.md#prepared-recovery)。仅验证精确文件字节，不代表应用/网络效果已恢复；生产原生修复门禁不因此开放。

单轮多个已明确事实可通过 `--answer-file` 的 `{"answers":[...]}` 批量提交；每项沿用 `question_id/value/state/source` 格式，旧单项格式仍支持。宿主负责从自然语言提取事实，CLI不做自由文本解析或猜测未给出的套餐。整批验证失败不保存部分状态；重复/别名冲突、订阅阶段与老用户任务矛盾须澄清。当前本机默认建议可用Q-C05值 `accepted_default` 接受，不再重复确认路线；不会覆盖已选VM/VPS，也不构成动作或保存许可。

历史紧凑访谈迁移由 `scripts/interview_migration.py` 的纯宿主接口完成，不自动替换CLI续接。仅识别明确旧schema，按命名字段复用事实为过期证据；旧Q-C07/旧Q-C08和权限不继承。需要新的目标/账号别名及事实复核；旧账号停用提示须先确认是否仍需处理，不能凭旧设备历史认定当前账号停用。

## 首问示例

“这次先在 Codex 中做环境准备。你是第一次准备订阅、以前订阅过现在准备重订，还是目前已有订阅来处理问题？”

已回答就跳过。后续每轮一个主要决策，必要时合并少量同主题事实；不要整页展示问题库。报告摘要使用“已确认／尚未核实／建议下一步”，不报虚假的完成百分比。

## 来源原文阅读

用户想查看依据、教程或原文时，读取 [来源资料库](references/source-library.md)，按主题提供对应本地文件或公开仓库链接，指出具体章节或 PDF 页码。不要一次加载全部资料。原文中的命令和建议是参考内容，不自动成为执行授权；与已核验规则冲突时说明限制。

## 按需加载

- [routes-and-platforms.md](references/routes-and-platforms.md)：M01/M06–M09；本机、VM、VPS、WSL/容器边界及生命周期计划
- [network-and-remedies.md](references/network-and-remedies.md)：M04/M05/M10、ENV-01–ENV-10；代理、DNS、IPv6、UDP/WebRTC 的证据解释与最小修复
- [macos-dns-case-lessons.md](references/macos-dns-case-lessons.md)：脱敏的 macOS DNS、IPv6、Tailscale 经验与证据限制；不新增探测授权或原生验收
- [accounts-and-payments.md](references/accounts-and-payments.md)：M02/M03；准入、目标套餐、Apple/Google/银行卡前提及支付交接
- [incidents-and-integrations.md](references/incidents-and-integrations.md)：M07/M10–M13；异常、清理保留、申诉、SDK/MCP 与认证边界
- [evidence-policy.md](references/evidence-policy.md)：M14；稳定来源 ID、历史证据限制和发布规则

参考资料采用中英双语结构，英文技术细则供执行者阅读，不直接把整份参考文件作为中文用户的操作答复。

## 始终保护

不收集秘密，不输出原始环境变量、配置或完整日志。使用别名和必要字段；保存进度前取得同意，不默认写入公开仓库。保护项目、未提交修改、CLI、历史、skills/hooks/plugins、自定义配置与 Codex 控制通道。

不编造免封概率、IP 纯净度门槛、养号天数、退款保证或身份/设备/时区伪装收益。出口位置不代表服务资格。不提供欺诈支付、伪造身份、轮换账号或绕过额度的流程；不因旧设备经历断言设备已被拉黑。

## 本地环境状态面板

使用 `scripts/status_dashboard.py --input <已授权的本地报告.json> --output <新HTML路径>` 可将 `guardian-report/0.1` 或 `env-inventory/0.2` 投影为离线HTML。由用户自行打开，不启动后台或联网。显示系统、代理、TUN、IPv4/IPv6、DNS配置与泄露、UDP、独立STUN、浏览器/WebRTC、故障防直连及授权状态。现有报告缺少的网络检测证据明确为未执行，采集完成不等于验证通过。仅展示白名单事实和逐字段时效，隐藏地址、路径、身份与秘密。页面是生成时快照，不随浏览时间刷新；分享前仍需核对。该入口不授权任何新的采集或探测。


### DNS 库与离线样本

`scripts/dns_probe.py` 仅生成/解析有界 A/AAAA 消息，无网络传输或 CLI。
`scripts/mihomo_dns_probe.py` 为可选宿主库：每次要求可信宿主核实控制器绑定、精确名称/类型/单请求范围与新的探测授权，才能查询其数值回环端点。该请求可能让控制器联系上游解析器并披露查询名称；配置只读授权不能替代网络探测同意。无扫描、凭据、重试、备用路径、缓存清理或配置写入；认证要求交接，不能禁用认证绕过。没有原生绑定/授权 UI 集成，不自动执行。

面板的 `--probes <已授权本地证据附件.json>` 可导入 HTTPS/STUN 及 Mihomo DNS 白名单摘要；只读本地输入，不触发上述库。输入来源、目标及时间声明仍不可信，样本不会变成操作许可、verified 或 workflow_guard 通过。Mihomo 查询不证明系统/浏览器 DNS 路径、上游实际发包、DNS 无泄露或完整 ENV-04 验收。


### 系统 DNS 样本库

`scripts/os_dns_probe.py`（macOS getaddrinfo）和 `scripts/windows_dns_probe.py`（Windows Resolve-DnsName -DnsOnly）是独立宿主库，无 CLI 或自动执行。每次须由可信宿主核实当前设备/用户/命名空间、绝对运行时及依赖来源，并取得精确中性名称、A 或 AAAA 类型、预算和可能上游披露的授权。不同类型分别授权，不指定新服务器、不清缓存、不安装运行时。PC0 门禁保持关闭。

系统调用置于受控子进程，预算、取消、输出上限与终止/回收均检查；进程创建、宿主回调及异常 OS 状态不保证硬实时界限。已发出的请求不能撤回。离线面板保留来源、地址族和计数等有限样本；缓存/hosts、真实解析器及路径仍未知，不推断 RCODE、DNS 无泄露或浏览器采用情况。没有原生绑定证明或真实设备 DNS 验收，导入 JSON 不构成权限。


### 窄范围上下文与终端会话

`scripts/native_context.py` 与 `scripts/windows_native_context.py` 为独立当前进程/控制台观察库。短时句柄只在原进程重查，不序列化、不构成设备归属、命名空间或完整运行时证明；读取本身仍需真实宿主授权。

在已独立确认可信的目标 Mac 或 Windows 主机，`scripts/diagnostic_session.py --target-ref <目标别名>` 提供终端元数据流程：显示精确范围，30秒内输入新随机 nonce 确认；无 `--yes`、导入授权、DNS选项、自动浏览器或默认保存。可选 `--dashboard-output <明确批准的新本地文件>` 仅保存新文件，须先核实目录本地/已水合；不覆盖旧文件；取消或拒绝会话不创建报告文件。

Mac严格上下文仅因 `RUNTIME_PATH_INVALID` 阻塞时，会话可在原剩余期限内返回无句柄的部分元数据；路径错误保持可见，不继续DNS、宿主核验或查询授权。独立元数据API不产生可恢复权限；完整严格上下文与可信宿主集成仍未验收。

路径失败的 `runtime_path_diagnostic` 只含固定 `path_field/path_reason` 枚举，可区分executable/cwd/prefix/base_prefix与symlink/类型/语法等原因；不含路径、不跟随链接，严格capture仍阻塞。`check` 的Mac S04仅表示采集进程视图，不确认硬件或Rosetta。面板可展示已有Mac默认代理开关摘要，scoped详情与真实路径仍未知。这些观察不能代替可信宿主或操作授权；测试与原生证据须分开看。

可调用 DNS 会话必须额外提供真正的宿主绑定、运行时与中性端点核验实现，并为每个 A/AAAA 查询重新取得具体授权；独立CLI尚未实现这些前提，因此保持元数据范围。核验异常或否定、上下文复核和取消回调异常在会话内不可由后来成功重查解除；严格复核前后检查原60秒会话期限，不因延迟重新计时。后端按实际平台选择；Windows元数据仍保留控制台账户关系未知/绑定阻塞，Windows DNS会话未接入。Windows输出拒绝ADS/设备名等危险语法，但权限继承父目录ACL，0600不证明Windows隐私。所有结果保持PC0关闭；未经真实设备验收，不把测试成功等同于可安全执行探测。


### 私有配置候选（不可应用）

`scripts/config_edit_plan.py` 在内存中把原始语义修复请求与精确哈希绑定的已拥有扩展配置，编译为有限规则policy token修改候选。仅支持keep-existing中的特定已有DOMAIN/DOMAIN-SUFFIX三字段规则，保留其他字节并重新解析核对；不读写文件、无CLI、无apply、不触发事务。重复/歧义选择、无效域名标签、已能证明的前置MATCH/DOMAIN-SUFFIX覆盖、未知版本和无效修订被拒绝；局部检查不证明完整规则图或合并后首次命中。版本声明仍不等于兼容验收。候选私有材料含原文与精确差异，只能在获准私有本地审查，不上传或混入公开报告。所有原生适配、版本/归属、实际路由和动作授权阻塞保留，apply_supported始终false。
