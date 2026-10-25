# 内置脚本与宿主库的契约说明

从 SKILL.md 移出（ADR-044）。这里是各内置入口和宿主库的精确边界：能做什么、要什么输入、哪里会阻塞。用户任务用到某个脚本或库时再读对应小节；只是做访谈、出方案、按分级授权在用户机器上操作时不需要读。脚本清单见 [scripts-index.md](scripts-index.md)。

## Agent内部修复入口（按动作能力分流）

已核实目标使用2.5.8且选定独占rules扩展时，可用 [Agent 应用编辑任务](agent-rules-task.md) 生成单个DOMAIN变更的私有候选和供给内容核验。实际保存／重载由Agent通过受支持应用界面执行，须具体许可；该辅助接口不执行写入或证明实际网络效果。

`scripts/repair_cli.py`提供精确文件的`preflight / plan / diff / execute`接口。`plan`显式指定`--plan-file`和`--backup-directory`才写入新的私有计划文件，不修改目标；`--private-review`可在获准的私有Agent会话中非交互展示选定规则及policy前后差异，不输出无关配置。私有差异不得混入公开报告。

已确认交互是Agent展示具体改动、目标、影响、备份及恢复路径，用户在对话确认后，由可信宿主核对该次授权并调用固定内部脚本；不要求第二次终端确认码。宿主将确切`retained_plan_digest`、目标与备份范围绑定到本次操作；摘要只是完整性检查，不是授权。不能用JSON布尔值、任意回调、临时shell改写或终端模拟绕过权限。

`scripts/repair_execution.py`保留计划有效期、请求摘要、原文件身份和内容、候选一致性复核、事务备份及读回链路；生产原生适配门禁只开放一个固定范围：macOS 上 Clash Verge Rev 2.5.8 的 `rules-prepend` 扩展（`native_clash_verge_mac.py`，要求 Clash Verge 应用已退出（后台的核心和服务可继续运行），写入前后复查，检测到变化即失败；macOS 无强制文件锁，这是发现并失败，不是阻止）。其他系统、产品、版本和 `merge-policy` 仍返回`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`，不得宣称实际修复完成。该适配器在一台真实 Mac（macOS 15.7.4）上已验证：版本与归属、计划可复现、应用运行时拒绝写入、真实写入、重启后规则在场、`recovery_cli` 回滚回到基线哈希；那台 Mac 的 profile 有 script 与 merge 链，规则是否被后面的链改写要重启后探测，写入成功不等于生效；别的环境以实际核对为准。Linux临时夹具中替换适配器的测试不开放用户Mac/Windows能力。恢复仍遵循独立`recovery_cli.py`契约，不自动覆盖后续改动。

`scripts/clash_verge_258.py`只校验调用方提供的2.5.8应用plist、配置索引和扩展字节之间的声明一致性：current→活动profile→显式option.merge或option.rules→唯一同类型扩展及basename。拒绝跨profile共享扩展、全局默认UID及路径/文件别名歧义。该库不读取真实文件，不证明实际安装/运行归属；输出始终为supplied_metadata_only。merge的rules数组替换基础数组，不能将rules扩展的prepend/append/delete混当此格式；脚本/后续链、内核版本、真实写入者排除和验收仍阻塞，不能以该结果开启execute。

`--candidate-kind rules-prepend`提供独立的rules扩展候选：必须显式给出`--base-path`、`--app-info`、`--profile-index`及`--extension-uid`，经安全读取核对所提供的2.5.8声明链和当前基础profile路径。只向现有空`prepend: []`插入用户明确排序的DOMAIN/DOMAIN-SUFFIX规则；`delete`必须为空，`append`与其他字节保持不变。拒绝已知受保护规则冲突，不把调用方声明的控制路径或优先级当作验证。私有差异包含已知优先级影响；未知链和原生执行继续阻塞。

保留计划格式为`guardian-retained-repair/0.3`，绑定当前环境入口摘要、候选类型、UID和基础配置/plist/索引的精确路径、父目录及文件快照。执行参数必须一致，提交前与读回后复核；旧0.1/0.2计划必须重建并重新展示确认。完整输入格式及命令见仓库`docs/rules-extension-plan.md`。不得用此入口初始化空merge、替换完整rules数组或绕过xattr限制。

## 限定静态盘点入口

`scripts/inventory_cli.py capabilities` 查看实际开放范围；`workflow-status` 仅显示新建且关闭的门禁。`static-audit` 只读取用户明确列出的本地配置，要求新的精确范围终端确认，拒绝保存的授权字段；目标身份/本地文件性质仍需可信宿主核实，终端输入不能代替宿主或操作系统权限。缺少可选PyYAML时停止，不自动安装。静态声明不代表运行时路由。Windows安全静态读取、控制器原生绑定、系统改写与自动恢复未开放。

控制器盘点与Windows只读计划是供可信宿主集成的库，不能绕过尚缺的原生身份/权限适配。workflow_guard提供即时资格判定，不是进程隔离或可持久化执行授权。

`scripts/remedy_plans.py` 提供四种方向的离线语义计划：保留现状、显式代理规则、TUN规则、限定兼容处理。它不生成可执行配置补丁，不开放apply；需要可信宿主提供私有快照绑定和公开别名。现有inventory CLI不能直接提供全部输入。结果中的DNS图、协议、控制路径和规则范围只依据投影事实；缺失或冲突保持阻塞，不推导已修复。

Windows监听者核对库 `scripts/windows_listener_binding.py` 仅供可信宿主显式集成：核对限定回环端口的PID、创建时间和同用户关系，不发控制器请求；为此会在私有内存读取有界监听表再筛选，必须向用户披露并获准。命名空间仍为宿主断言，不能据此声称独立原生核实或完整应用实例绑定。

网络库收到429时只报告有界Retry-After提示，不自动等待或重试。日期提示需要可信的响应接收时钟；未知、无效或过长值保持未知。

独立STUN库 `scripts/stun_probe.py` 仅在可信宿主提供当前精确范围授权、目标和取消检查后使用。没有CLI或自动触发，名称到固定数值地址的绑定由宿主另行核验；本模块不解析DNS。Cloudflare候选选择不等于任何一次公网执行授权，映射响应不认证提供方，也不证明浏览器或Claude路径。

POSIX独立恢复入口为 `scripts/recovery_cli.py`，须与 `transactions.py` 预先保留在可信本地位置。inspect只读用户选定回执；preview/rollback仍只接纳已应用回执。reconcile须绑定独立确认的目标、备份批次与回执摘要，只读观察选定记录；仅v2 prepared的候选匹配状态可用restore-prepared另行恢复，并要求上次私有观察的完整摘要、实际排除其他写入者及真实终端逐阶段新确认。旧prepared或冲突状态不写入，不重放apply；摘要和回执不是授权，Windows不支持。Agent宿主的对应调用及失败处理见 [agent-remediation.md](agent-remediation.md#prepared-recovery)。仅验证精确文件字节，不代表应用/网络效果已恢复；生产原生修复门禁不因此开放。

单轮多个已明确事实可通过 `--answer-file` 的 `{"answers":[...]}` 批量提交；每项沿用 `question_id/value/state/source` 格式，旧单项格式仍支持。宿主负责从自然语言提取事实，CLI不做自由文本解析或猜测未给出的套餐。整批验证失败不保存部分状态；重复/别名冲突、订阅阶段与老用户任务矛盾须澄清。当前本机默认建议可用Q-C05值 `accepted_default` 接受，不再重复确认路线；不会覆盖已选VM/VPS，也不构成动作或保存许可。

历史紧凑访谈迁移由 `scripts/interview_migration.py` 的纯宿主接口完成，不自动替换CLI续接。仅识别明确旧schema，按命名字段复用事实为过期证据；旧Q-C07/旧Q-C08和权限不继承。需要新的目标/账号别名及事实复核；旧账号停用提示须先确认是否仍需处理，不能凭旧设备历史认定当前账号停用。

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

## 环境入口校验

调用 `scripts/environment_entry.py` 的 `assess_entry` / `require_entry` 严格校验当前投影，再走原有目标、PC0、权限及逐动作授权门。入口资格不是许可或原生绑定证据，不把保存的报告恢复成许可。CLI 的 `--entry-file` 只读取明确提供的有界本地投影，Windows 此文件适配尚未开放；可信宿主可传已校验的字典。路线／资源改变必须使旧适用性和计划失效，不能复用旧检查结论。既有精确恢复义务仍按原回执、目标、保护和本次批准处理，不被新问卷阻断。

## 旧目标范围契约与整机结论

现有 `traffic_policy`、CLI、访谈评估和面板仍输出旧目标范围契约，不代表整机合规；不能改返回字段假装升级能力。规则声明、应用载入、进程采用和端到端观察分别报告；同一代理链不保证同一公网 IP，样本一致只支持测量范围。整机强制覆盖或持续保护未建立时如实标 unknown／unsupported／未建立，不能 pass，G2或单次curl成功也不能代证。PC0、具体动作许可、取消、拒绝及事故优先级保持不变。
