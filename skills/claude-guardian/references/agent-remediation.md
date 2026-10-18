# Agent 编排检测与修复

依据 D-SPEC v0.1.10 §1、§7 与 D-ENV v0.3 §3、§5.6、§20；历史“只写 Spec”不阻止实现。实际权限与逐项验收继续有效。

## 一次任务的闭环

1. 复用访谈事实并确认目标主机。获准后调用 diagnostic_session.py 采集有限元数据；已有合法报告可直接进入解释，不强制重复全套访谈
2. 解释每个发现的证据、时间、程序/地址族/作用域。未知或采集失败不是错误配置。静态配置不等于实际流量
3. 调用固定选择器：`python scripts/agent_remediation.py select --input <本地报告.json> --target-ref <目标别名>`。接受 guardian-report/0.1、env-inventory/0.2 或下述 Agent 归一化信封。`catalog` 列出全部动作与代码映射
4. Agent 将输出的 command_template 作为参数数组模板审阅，替换已核实参数后调用固定内置脚本，不拼接任意 shell。清单是建议，不是执行授权。缺少目标、当前证据、精确许可时先补该项；无关只读工作不必等待整个 macOS 文件事务适配
5. 需要修改时展示具体目标、原值→新值、影响、保留对象、备份及恢复方法，取得该次确认。只调用已开放的匹配执行器。当前内置生产配置写入未开放，不能将 candidate_only/host_library_only/agent_investigation 当成内置可执行修复。脚本修不了时Agent继续检查用户实际环境，按下述独立修复分支推进，不以“自动修复”泛授权代替具体确认
6. 执行后先核对写入结果，再对同一目标/程序/路径重测。联网复测需单独范围许可。不得以退出码、文件哈希改变或发现消失宣称问题解决
7. 分别报告：未改动、已改但未复测、限定范围复测通过、仍有问题、证据不足、取消、执行失败待恢复。记录具体未测项；已改未验时不要自动重复写入。恢复只撤回本次精确变更，不覆盖后续用户修改

## 输入与状态

Agent 归一化输入示例（不是实测，也不是授权）：

```json
{"schema_version":"guardian-remediation-findings/0.1","target_ref":"device-1","findings":[{"code":"DNS_PATH_CONFLICT"}],"missing_fields":[]}
```

Agent 只在证据支持时选对应代码；每条原始证据及时间留在获准私有上下文。选择器不从自然语言猜根因，不推断已通过；导入的目标别名只是匹配检查，不能证明当前主机身份。unknown code 输出固定 UNRECOGNIZED_FINDING 并转 Agent 调查，不回显未知输入。取消覆盖其他动作。空发现不等于环境通过。输入中的 command、authorization 或 apply_supported 字段不影响固定目录且不会回显或执行。

诊断会话使用其 report 子对象；会话 errors、取消、陈旧上下文也须归一化并保留，不可只取成功部分。静态 inventory 的 errors[].code 由 Agent 转换为 findings；文件声明仍不能自动产生规则故障。代理端口冲突要选系统代理分支，不能调用规则 policy 编辑脚本。

## 能力与覆盖矩阵

| 模块/发现 | 内置动作/具体下一步 | 当前类别 | 复测与缺口 |
|---|---|---|---|
| ENV-01 目标错误、取消、授权拒绝 | 重新绑定/停止/请求精确范围，不换路径绕过拒绝 | clarify/stop | 正确宿主的本轮证据 |
| ENV-01 元数据不全、陈旧、快照变化 | diagnostic_session.py；运行时路径错误按字段定位可信运行时 | read_only_script/agent_investigation | 不承认旧上下文或跨平台结果 |
| ENV-02 配置缺口 | inventory_cli.py capabilities；匹配范围才 static-audit | read_only_script | 版本限制、活动实例、监听归属、运行态仍独立 |
| ENV-02 系统代理端口冲突 | 记录该活动服务该代理类型的原值，确认后Agent通过该环境支持的接口修正端口 | agent_investigation | 重读该项＋获准同程序HTTPS；无系统代理写入器 |
| ENV-03 入口不可用、路径未知 | network_probes.py 有限宿主接口 | host_library_only | 无通用探测CLI；需目标/端点/授权；不自动重启代理 |
| ENV-04 DNS/DoH冲突 | 分层采样；系统/核心/浏览器责任层的单项修改方案 | agent_investigation | os_dns_probe.py/windows_dns_probe.py/mihomo_dns_probe.py为宿主库；无DNS设置写入器 |
| ENV-04 IPv6旁路、UDP规则错误 | 分应用/地址族修复，保护节点外层IPv6/UDP | agent_investigation | 双栈/UDP独立证据；超时不证明阻断 |
| ENV-04 Fake-IP正常、IPv6超时、时区仅与出口不同 | 保留当前配置，解释局限 | no_change | 不制造修改目标 |
| ENV-05 WebRTC旁路、策略未生效 | 精确版本/Profile/origin与有效策略核对、环境适配的单项调整 | agent_investigation | 无浏览器策略写入器；实际候选与媒体复测 |
| ENV-06 已有规则policy错误/需prepend | repair_cli.py preflight，之后获准私有diff/plan | candidate_only | merge-policy与rules-prepend范围不同；生产execute仍阻塞 |
| ENV-07 程序忽略代理 | 精确启动入口/支持方式，Agent最小配置 | agent_investigation | 无启动器写入器；PC0不运行Claude |
| ENV-08 时钟/时区/语言目标 | 记录原值、确认单项目标、Agent通过系统支持的接口修改 | agent_investigation | 无设置写入器；不按出口地区改时区 |
| ENV-09 清理请求 | 精确对象/保护/备份/恢复清单，独立删除确认 | agent_investigation | 无清理执行器；事故优先不等于清理 |
| ENV-10 故障阻断未验证 | 列保护范围、独立恢复与平台演练方案 | agent_investigation | 无系统故障注入/防火墙写入器 |
| 通用缺依赖、无权限、错误输入/版本 | 定位该项依赖/许可/格式/适配，修正后重跑原检查 | agent_investigation/clarify | 不安装依赖或放松门禁来制造通过 |

所有 guardian.py 已实现 finding/error 与静态 inventory 公开错误码由测试覆盖。网络等归一化代码仅用于 Agent 解释现有获准证据，不代表检测器自动输出或该模块全部实现。

## ENV-06：把已读取规则来源转换为受限候选输入

`rule_source_import.py` 是纯内存宿主库，不是新命令或写入执行器。Agent先明确用户选中的客户端/功能、来源范围及目标策略；只传入已经获准读取的完整字节。不能因为官方文档列出可达域名，就自行选择代理动作或扩大业务范围。仅做离线解释/转换不需要原生执行器准入或修改设备许可；后续文件读取、变更和探测仍各自满足权限与范围。

支持的显式格式只有：

- `exact-domain-lines/0.1`：每行一个ASCII精确域名，只匹配该主机；支持LF/CRLF、一个可选结尾换行和开头BOM。不接受空白/注释行、首尾空格、根点、通配符、Unicode/IDNA或IP字面量，不自动猜后缀。所有标签均为数字的主机（如`127.1`、`192.000.2.1`）也作为歧义输入拒绝，`123.example.invalid`仍可用；这是保守子集，不是任意地址写法检测
- `mihomo-domain-rules-fragment/0.1`：仅含`rules`的YAML映射，使用block sequence和plain单行三字段`DOMAIN`/`DOMAIN-SUFFIX`。后缀选择保留原有语义，包括后缀本身和标签边界下的子域；不改成仅子域。引号/转义、多行、flow list、别名/标签、provider payload、其他引擎JSON、ASN/CIDR/keyword、修饰符均不在本片段语法内

格式ID只声明该输入语法，不证明安装版本支持。Agent须先核实原列表确实声明精确主机语义，不能把语义未知的provider或其他列表标成精确格式来通过。两种格式使用相同主机子集。源域名大小写和原记录顺序完整保留；仅在检查同类型重复选择器时按ASCII主机名大小写比较。重复、冲突或任意不支持记录导致整批拒绝，不排序、去重、过滤或返回部分候选。精确与后缀记录不会互相合并；它们若重叠，后续编译器仍可拒绝优先级不明的组合。

宿主示例（虚构数据，不能据此执行修改）：

```python
import hashlib
from rule_source_import import import_rule_bindings

raw = b"Api.example.invalid\n"
source = {
    "schema_version": "guardian-rule-source-binding/0.1",
    "source_ref": "source-a", "expected_sha256": hashlib.sha256(raw).hexdigest(),
    "evidence_kind": "user_supplied", "verified_at": "2026-10-18",
    "version_scope": "declared-source-v1", "purpose": "workflow-repair",
    "client_scope": ["client-a"], "feature_gate": "selected-feature",
    "shared_service": False, "activation_state": "candidate",
}
imported = import_rule_bindings(
    raw, "exact-domain-lines/0.1", ["rule-a"], source,
    {"kind": "user_selected_egress", "group_name": "approved-group"},
)
public_summary = imported.preview()
components = imported.binding_components()  # private, fresh copies
provenance = imported.private_material()      # private; do not log/export
```

`expected_sha256`必须匹配函数从完整字节实际计算的SHA-256；不是调用者给什么哈希就信什么。`source_ref`、版本范围、用途、客户端和功能使用非识别性别名；已知凭据形状会拒绝，但不是通用秘密检测。每条私有记录保留源索引/行号/字节位置/原记录、类型、大小写及源动作。带动作来源的每一项必须与明确选定组一致，混合REJECT/DIRECT/其他组不会被静默改写。无动作来源也必须有明确选择。来源日期/版本/类别只作为调用者声明保存，不证明真实性、新鲜度、独立性、活动配置或授权。

Agent将`components`用于既有`rules-prepend` binding的`rules`、`rule_order`、`group_name`字段，不把来源元数据塞进编译器不接受的字段。与当前请求的规则引用、顺序或组不一致时停止并核对选择，不能为通过校验改请求含义。其余target/scope、扩展/base快照、保护索引、所有权/版本/策略组检查仍由原流程处理。继续调用既有`compile_rules_extension`或`repair_cli`预检，不能绕过保护/重复/陈旧/有效优先级门禁；成功导入也不改变`apply_supported=false`或原生未验状态。

私有来源证据应随本次候选审阅保留，但本库不读取来源路径，也不替当前CLI增加来源文件的持久化/执行期复验。来源变化或需再次规划时，重新读取获准字节、重新导入并重新预检，不能把旧源哈希或旧日期当作现在仍有效的证明。公开输出只有固定状态和有界计数；不要将`private_material()`的源正文或元数据放进普通报告。

默认上限：1 MiB完整来源、256条记录、16个客户端别名、5秒（最多60秒）的原始调用预算；保持取消回调。超限、不可读、格式未知或解析器缺失时说明准确缺口，不跳过坏记录、不扩大读取范围、不静默安装依赖。精确域名格式不依赖PyYAML；YAML片段缺解析器时返回固定`PARSER_UNAVAILABLE`。

这个导入接口只补原ENV-T40的一小段来源到现有绑定的能力。下面的独立转换器补充有限provider/JSON谓词转换；ASN、动作转换、完整版本适配和原ENV-T40的L+R验收仍未完成。继续扩展须先核对有日期/版本的官方语法，不依赖遗失代码或猜测字段。

## ENV-06：固定兼容版本的纯谓词格式转换

Agent可调用纯内存`rule_format_conversion.convert_rule_format`，把已经获准读取的完整来源转换为另一种**无动作谓词集合**。它不写文件、不安装或调用引擎、不获取provider，也不是修复执行入口。用途是把明确格式的依赖集合整理成可供下一步私有审阅的完整字节；普通离线转换无需等待原生执行门禁。

支持profile固定如下，必须显式传入，不能按文件扩展名猜测：

| 常量 | profile | 受限语义 |
|---|---|---|
| `EXACT` | `exact-domain-lines/0.1` | 每行一个精确主机，无动作 |
| `MIHOMO_DOMAIN` | `mihomo/1.19.32/provider-domain-yaml` | sole `payload` block sequence；裸域名=精确，`+.域名`=包含本身及标签边界子域 |
| `MIHOMO_CLASSICAL` | `mihomo/1.19.32/provider-classical-yaml` | sole `payload` block sequence；仅二字段`DOMAIN,域名`、`DOMAIN-SUFFIX,域名`，无第三动作字段 |
| `SING_BOX` | `sing-box/1.12.0/source-rule-set-json-v1` | 严格`version: 1`＋`rules`；每项只允许非空`domain`/`domain_suffix`字符串数组，无动作/其他条件 |

这些是选定的兼容性审阅目标，不代表最新版本或当前设备已装版本。只接受实际整数schema 1；2/3/5、布尔/字符串/浮点形式均不当作1。原始域名必须是小写ASCII DNS标签；不自动改大小写、去根点、转Unicode/IDNA或修复空标签。已有小写`xn--`字符串仅按不透明ASCII处理，不宣称与Unicode名称等价。所有数字标签的歧义主机也拒绝。此接口的主机契约比前面的大小写保留导入器更窄，不能为了通过而静默预处理来源。

`DOMAIN-SUFFIX`、domain provider的`+.`及无前导点的sing-box `domain_suffix`都保留apex及子域。provider的`.域名`、`*.域名`与sing-box前导点后缀不同，当前不支持，不可剥掉前缀。后缀不能导出成精确列表。匹配等价范围只覆盖同样满足小写ASCII契约的候选主机；外部流量的大小写、根点和Unicode如何进入各引擎仍未验证，不能报告普遍运行时等价。

来源是谓词OR集合，记录顺序保留用于溯源，不证明最终策略优先级。JSON规则中的字段和数组按原始出现顺序展开；输出一条谓词对应一项，保留源引用、索引、路径、原值及完整源字节，不排序、合并或去重。不同类型的重叠选择器保留；相同类型的重复选择器整批拒绝。相同JSON键、未知字段、port/network/invert/logical条件、ASN/CIDR/keyword/regex/no-resolve/嵌套rule-set、不支持语法或任意混合坏项均整批报错。

带动作的主`rules`或route配置不能变成无动作来源；REJECT/DIRECT/其他组、第三字段或action/outbound都不会被丢弃。provider的获取代理与引用处的出站策略是不同概念；转换结果不创建RULE-SET引用，不设置provider下载路径或业务出站。后续选择策略、所在配置、组织保护、版本/归属、精确差异、操作许可与读回仍由独立流程处理。

宿主调用示例（全部虚构，不写入配置）：

```python
import hashlib
from rule_format_conversion import convert_rule_format, MIHOMO_CLASSICAL, SING_BOX

raw = b"payload:\n  - 'DOMAIN,api.example.invalid'\n  - 'DOMAIN-SUFFIX,example.invalid'\n"
source = {
    "schema_version": "guardian-rule-source-binding/0.1",
    "source_ref": "source-a", "expected_sha256": hashlib.sha256(raw).hexdigest(),
    "evidence_kind": "user_supplied", "verified_at": "2026-10-18",
    "version_scope": "reviewed-source-v1", "purpose": "selected-dependencies",
    "client_scope": ["client-a"], "feature_gate": "selected-feature",
    "shared_service": False, "activation_state": "candidate",
}
converted = convert_rule_format(raw, MIHOMO_CLASSICAL, SING_BOX,
                                ["rule-exact", "rule-suffix"], source)
public_summary = converted.preview()
private_output = converted.private_material()["output_bytes"]
```

公开摘要仅含固定状态及有界计数，保持`apply_supported=false`、`native_acceptance=not_run`；无域名、源hash或调用者元数据。私有结果不可变，`repr`固定脱敏，默认JSON/pickle序列化拒绝；仅在获准私有审阅中访问输出与来源证据。沿用前述来源声明及实际SHA校验，不据日期/类别/版本别名确认真实性、新鲜度、独立性或权限。

默认完整输入及输出各≤1 MiB、≤256条谓词、≤16个客户端别名、5秒原始预算（最多60秒），保留取消回调；JSON另限48层/20,000结构token，YAML复用既有安全有界解析器。超限、取消、超时、缺解析器或任何错误都不返回部分输出。时间/取消是合作式检查，不保证中断正在运行的解析器。精确文本与JSON不依赖PyYAML；provider YAML缺失时固定`PARSER_UNAVAILABLE`，不自动安装。

这提供原ENV-T40的有限L逻辑证据。独立临时文件写回/恢复测试即使通过，也不代表用户设备、引擎加载、GUI持久化、实际路由或完整R通过。完整L+R仍待逐条件审阅。详细API、版本来源和反例见仓库`docs/evidence/rebuild-rule-format-conversion.md`。

<a id="prepared-recovery"></a>
## 已替换但回执未完成：精确文件恢复

仅针对`transactions.py`既有POSIX精确文件范围，不处理系统设置、凭据撤销、删除、Windows或应用有效状态。实际变更前须把可信`recovery_cli.py`及`transactions.py`、原始备份和步骤保留在获准私有位置，并核实目标上的独立终端能运行；不能等Agent失联后再要求在线取得步骤。完整命令见仓库`docs/offline-recovery.md`。

1. 写入失败或中间状态不明，先停止自动重试。保留当前文件和私有批次，独立核对目标别名、精确目标路径、批次及选定回执来源；不扫描其他位置，不把备份、base64、完整文件或敏感摘要发到公开报告
2. `inspect --receipt`只读指定回执，摘要仅为未验证候选。经确认精确读取范围后，`reconcile`加`--receipt-digest / --target-ref / --target-path / --backup-batch`读取该范围；宿主库入口是`reconcile(recovery, receipt_path=..., target_ref=..., target_path=..., backup_batch=...)`。分类是当前观察，不是历史apply成功或恢复许可
3. 只有v2 prepared的`prepared_candidate_observed`能进入单独恢复。展示原字节/模式将覆盖的确切当前候选、经审阅语义影响、保留项和恢复风险；保留该完整观察的操作摘要。旧v1 prepared、原文件仍在、已恢复候选和冲突均不走此写入口；不能改schema、伪造applied回执或重建快照消除冲突
4. 可信宿主取得本次具体恢复许可并实际排除所有写入者后，调用`restore_prepared(recovery, observation, target_ref=..., authorize=..., exclusive_access=True)`。两次授权核对必须绑定`restore_prepared`、`digest({'recovery_digest': digest(recovery), 'observation': observation})`及目标；脚本复核回执、原备份、批次和完整当前快照。不能自行返回True、使用保存的JSON权限或模拟终端确认。独立普通终端用`restore-prepared`及`--reconciliation-digest`，要求真实用户分别完成排他条件和两次新的随机挑战确认
5. 观察摘要或任一快照变化就停止，重新调查并展示受影响差异；不自动换摘要重试。成功仅表示本次原字节/模式恢复，保留prepared及恢复结果，不补造历史applied。错误可能发生在已恢复后、结果日志落盘前；用返回的有界批次/尝试别名定位确切`restore-<attempt_id>.prepared.json`，存在时先inspect再按独立范围reconcile。没有日志不等于没有修改；`restored_candidate_observed`只读报告，不重复写入，别名也不证明日志必然存在

固定`cleanup_code`为`STAGING_RETAINED / STAGING_CLEANUP_FAILED / DESCRIPTOR_CLOSE_FAILED`时，主错误之外还存在保留材料或清理失败；按精确范围调查，不宣称没有残留或自动删除可能含秘密的暂存文件。

这使限定恢复路径可由可信宿主调用，并保留Agent不可用时的独立入口；不是内置生产配置写入适配器，`NATIVE_REPAIR_ADAPTER_UNAVAILABLE`不改变。独立读取/恢复也不能绕过目标权限、PC0或操作系统拒绝。Linux合成临时文件/终端测试不代表Mac/Windows设备、实际断网、应用重载或规则命中通过。

## 下一项真正可执行修复：窄范围系统代理端口适配（尚未实现）

建议优先 macOS 的“已启用手动代理、同一活动网络服务、同一代理类型，仅端口修正”。它直接对应当前已实现 PROXY_PORT_ASSOCIATION_CONFLICT 检测，不需要 Clash 文件候选的完整合并/扩展归属证明，但必须有它自身的保护：

- 精确服务ID/代理类型、原主机/端口/开关/绕过列表与新的已绑定监听端口；PAC、服务切换或未知写入者冲突时停步
- 私有原值与动作回执；本次确切修改授权，可能断开Agent控制通道的风险和独立恢复步骤；任何OS提权单独处理
- 只改该端口，前后读回；失败仅对仍等于本次写入值的项做恢复，后续用户修改则提示冲突
- 重读设置与获准路径探测分开；原生Mac正常/取消/权限拒绝/并发/失败恢复测试后仅开放该具体能力

这是待实现/待原生验收的下一批工作，不是本选择器已具备的能力。Windows需自己的设置/权限/恢复适配，不能继承Mac通过。

## 内置脚本修不了：Agent继续负责

`agent_fallback=investigate_scoped_repair` 表示继续调查，不是执行许可，也不是“请用户自己修”。内置候选/宿主库缺适配、未识别发现和没有脚本的系统设置均可进入这一分支。

1. 在实际目标读取必要的OS/客户端版本、当前设置、安装方式、管理权限和对应受支持接口；原有证据够用则不重复采集。未知发现先定位根因，不套用最近的修复模板
2. 根据该环境构建最小动作：可以用宿主工具、精确配置编辑或临时脚本。先审阅脚本和参数；不执行下载内容、配置内脚本或任意报告提供的命令；不扩大读取/写入范围
3. 展示具体差异、风险、受影响对象和备份恢复路径。网络/代理、浏览器政策、清理、凭据或其他需确认操作按实际范围取得许可。需要用户自己处理的身份/提权/安全动作才交接该步骤，其余继续由Agent完成
4. 备份原值、复查目标未变化、执行一次最小动作并读回；后续变化或未知中间状态先检查，不盲目重试。控制通道可能中断时先准备独立恢复，不静默冒险
5. 以同范围真实复测报告结果。Agent修复的成功只属于该设备/版本/动作，不改变内置适配器的 native_acceptance，也不让以后用户免确认

权限拒绝、取消、PC0接触限制、目标不匹配、路径安全失败不是“缺适配器”。先解决真正的授权/目标/安全前提；不得借Agent分支换路径绕过。无法安全执行时说明具体缺失条件、已完成调查与下一步，不以“脚本不支持”笼统结束。

上面的系统代理端口适配建议是下一项内置实现；本次任务不要求Agent等待它发布。Agent可在用户实际环境和具体授权下用已核实的OS接口完成同一窄范围修复，并如实标明该路径和未覆盖限制。
