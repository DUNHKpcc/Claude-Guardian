# Agent 编排检测与修复

依据 D-SPEC v0.1.10 §1、§7 与 D-ENV v0.3 §3、§5.6、§20；历史“只写 Spec”不阻止实现。实际权限与逐项验收继续有效。

具体支持2.5.8独占rules扩展的单个DOMAIN变更时，见 [应用编辑任务与内容核验](agent-rules-task.md)。它复用原候选与归属校验，供Agent执行实际获准的应用动作；不调用内置生产写入器。

## 一次任务的闭环

1. 复用访谈事实，先确认本轮 local／VM／VPS 路线，再按下述完整环境入口声明绑定目标。获准后调用 diagnostic_session.py 采集有限元数据；已有合法报告可直接进入解释，不强制重复全套访谈
2. 解释每个发现的证据、时间、程序/地址族/作用域。未知或采集失败不是错误配置。静态配置不等于实际流量
3. 调用固定选择器：`python scripts/agent_remediation.py select --input <本地报告.json> --target-ref <目标别名>`。接受 guardian-report/0.1、env-inventory/0.2 或下述 Agent 归一化信封。`catalog` 列出全部动作与代码映射
4. Agent 将输出的 command_template 作为参数数组模板审阅，替换已核实参数后调用固定内置脚本，不拼接任意 shell。清单是建议，不是执行授权。缺少目标、当前证据、精确许可时先补该项；无关只读工作不必等待整个 macOS 文件事务适配
5. 需要修改时展示具体目标、原值→新值、影响、保留对象、备份及恢复方法，取得该次确认。只调用已开放的匹配执行器。当前内置生产配置写入未开放，不能将 candidate_only/host_library_only/agent_investigation 当成内置可执行修复。脚本修不了时Agent继续检查用户实际环境，按下述独立修复分支推进，不以“自动修复”泛授权代替具体确认
6. 执行后先核对写入结果，再对同一目标/程序/路径重测。联网复测需单独范围许可。不得以退出码、文件哈希改变或发现消失宣称问题解决
7. 分别报告：未改动、已改但未复测、限定范围复测通过、仍有问题、证据不足、取消、执行失败待恢复。记录具体未测项；已改未验时不要自动重复写入。恢复只撤回本次精确变更，不覆盖后续用户修改

<a id="environment-entry"></a>
## 当前环境入口：完整声明与实际调用

先确定当前任务，再显式选择执行路线，最后补所选网络资源和配置状态。已有 VPS、推荐默认值或旧访谈答案都不自动构成本轮选择；订阅解释、路线比较和不接触设备的纯内存计划无需先填环境问卷。当前没有把旧访谈自动转成入口声明的接口，宿主应依据本轮明确选择构造完整 `guardian-environment-entry-input/0.1` 对象，不能为通过校验把 unknown 改成 selected。

以下是完整、虚构的合法输入示例：已选择本地 `device-1`，资源和配置仍未知。只有 `offline_precheck` 具备进入原门禁的资格，配置／主动探测仍阻塞；不要求先购买代理。`client` 是本轮已明确的用途，不代表启动或访问 Claude Code。

```json
{
  "schema_version": "guardian-environment-entry-input/0.1",
  "route": {"choice": "local", "state": "selected"},
  "targets": [{"role": "local", "target_ref": "device-1"}],
  "network": {
    "possession": "unknown", "selection": "unknown",
    "configuration": "unknown", "path": "unknown"
  },
  "local_entry": {"kind": "unknown"},
  "final_egress": {"kind": "unknown", "protocol": "unknown"},
  "client": "claude_code"
}
```

声明只接收规定的枚举和非识别性别名。不得加入真实主机名、IP、订阅 URL、UUID、密码、token、原配置或授权布尔值；别名语法校验也不保证隐私，宿主仍须脱敏。`effective` 仅是报告的配置状态，不是原生观察。`eligible_for_existing_gate` 不证明设备／用户／命名空间，不授予读取、写入、联网或 PC0 接触权限。

### 文件与宿主入口

下面所有路径都是占位示例。先在获准的私有本地已水合目录准备 UTF-8 JSON，再替换成经过核实的规范绝对路径；不能从真实用户目录猜位置。入口文件安全读取复用 `inventory_cli.read_request`：最多 65,536 字节、拒绝重复 JSON 键及非有限数值、非普通文件、硬链接和包括祖先在内的符号链接；文件读取期间的身份／大小／时间变化会拒绝。文件的本地性、已水合状态及读取许可仍由宿主建立。

该文件读取器目前仅支持具备相应安全文件能力的 POSIX 环境，Windows 返回能力缺口，不能以改平台标记或不安全读取绕过。已审阅宿主可直接传当前 dict；`guardian.native_check(args, entry_request=entry_request)` 与 `diagnostic_session.execute(target_ref, consent=live_consent, entry_request=entry_request)` 保留各自原有的平台、目标及许可校验，dict 不补齐原生能力。

已确认本地 macOS、真实读取许可及当前宿主绑定后，命令形式如下。`--confirm-target`、`--authorize-audit` 不是替用户做确认；只有真实前提成立才使用。

```sh
python /trusted/claude-guardian/scripts/guardian.py check --target-ref device-1 --target-os macos --target-kind local --namespace desktop --execution-location native_local --user-context same --confirm-target --authorize-audit --entry-file /private/guardian-task/entry.json
python /trusted/claude-guardian/scripts/diagnostic_session.py --target-ref device-1 --entry-file /private/guardian-task/entry.json
python /trusted/claude-guardian/scripts/repair_cli.py preflight --request /private/guardian-task/repair-request.json --target-path /private/guardian-task/selected-extension.yaml --target-ref device-1 --candidate-kind merge-policy --entry-file /private/guardian-task/entry.json
```

`guardian check` 和诊断入口缺 entry 默认禁止，不再隐含选择本机；`--target-kind local` 本身也不能替代 entry。诊断终端仍要求新鲜随机挑战的实时范围同意，没有自动同意或 DNS CLI 开关。宿主 DNS 查询还须 `active_probe` 资格和逐查询的目标／运行时／中性端点核验；HTTPS 宿主 `network_probes.probe_https_ip(..., entry_request=entry_request)` 仍要求独立的精确端点与路径许可。上述 unknown 示例不能进行这些主动探测。

`repair_cli.py` 的 `plan`、`preflight`、`diff`、`execute` 都必需 `--entry-file`；前三者使用 `offline_precheck`，execute 使用 `configuration`。预检还要符合原请求格式、候选类型、精确路径、版本和所有权条件；合法 entry 不使生产写入可用，原生执行适配仍未准入。宿主 merge-policy 预检使用 `repair_cli.preflight(request_path, target_path, target_ref, entry_request=entry_request)`；不可把入口 JSON 当作 repair request。

### 静态 inventory 的 /2 信封

`inventory_cli.py static-audit` 不使用 `--entry-file`，而在完整 `guardian-static-cli-request/2` 请求的顶层嵌入 `entry_request`；旧 /1 不再接受。下面是完整虚构格式，文件路径也只是占位值：

```json
{
  "schema_version": "guardian-static-cli-request/2",
  "target_ref": "device-1",
  "entry_request": {
    "schema_version": "guardian-environment-entry-input/0.1",
    "route": {"choice": "local", "state": "selected"},
    "targets": [{"role": "local", "target_ref": "device-1"}],
    "network": {
      "possession": "unknown", "selection": "unknown",
      "configuration": "unknown", "path": "unknown"
    },
    "local_entry": {"kind": "unknown"},
    "final_egress": {"kind": "unknown", "protocol": "unknown"},
    "client": "claude_code"
  },
  "target_binding": {
    "target_ref": "device-1", "binding_state": "bound", "declared_os": "macos",
    "execution_location": "native_local", "desktop_user_relation": "same",
    "filesystem_namespace": "host_desktop"
  },
  "application": {
    "product": "clash-verge-rev", "gui_version": "2.5.5", "core_version": "1.19.0"
  },
  "files": [
    {"source_ref": "profile-1", "kind": "profile", "path": "/private/guardian-task/selected-profile.yaml"}
  ]
}
```

```sh
python /trusted/claude-guardian/scripts/inventory_cli.py static-audit --request /private/guardian-task/inventory-request.json --target-ref device-1
```

这个静态 CLI 当前仍限定上述 macOS／产品版本和原终端确认，字段中的 bound 只是调用者声明，不能伪造来补能力。全部请求先校验、范围确认后再复核；转入原 inventory 库时移除 entry 字段，不保存为授权。Windows 静态文件读取、自动发现和控制器访问不会因 /2 而开放。

### 路线与失败边界

- 本地执行配 VPS 出口仍是 `route.choice=local`；资源持有、选择、导入和生效分开记录。明确 direct 时无需购买代理：`selection=direct`、`path=direct`、`local_entry.kind=none`、`final_egress.kind=direct`、`protocol=unknown`，但不得凭格式修改来改变用户实际选路
- 本地和 VM 的入口评估建议适用的详细检查；VM 必须同时声明不同别名的 `vm_host` 与 `vm_guest`，分别绑定实际宿主和来宾，不能用宿主结果代表来宾。VPS 使用 `vps` 目标角色，仅基础、非侵入检查；不扩展到部署、配置变更或 quarantine。纯入口评估支持这些声明，不等于已有对应执行适配；当前 guardian native、diagnostic session 和 static inventory 只接纳 local 角色，不能自动 SSH、套用本机结果或把 VM 改称 local 来通过
- 缺失／畸形 entry、路线未选、撤销、冲突、陈旧或目标不属于当前路线都阻塞相关新动作；保留固定错误并重新核对当前范围，不能退回隐含路线或自动复用旧确认。调用期间变化停止后续依赖步骤；已有材料只保留其真实历史状态，不能当作当前权限
- repair 与 cleanup 的保留计划跨调用绑定生成时的完整入口声明。路线、目标、所选资源或配置声明变化后，必须重新生成并审阅计划；新的合法 entry 不能继续执行旧计划，也不能手改计划中的绑定摘要来通过。未保留该入口绑定的历史清理计划仅可用于已有工作的精确 reconcile／恢复，不允许启动新 quarantine；保存的摘要始终不是许可
- 已有回执的精确恢复不要求重新建立这项新动作 entry；`recovery_cli.py` 的既有恢复及 cleanup 的 reconcile／restore 保留原回执、摘要、当前目标、单独恢复许可、冲突和备份核验。撤销路线不能让既有恢复义务消失，也不能把恢复例外用于新配置、扩大清理或主动探测

## 输入与状态

Agent 归一化输入示例（不是实测，也不是授权）：

```json
{"schema_version":"guardian-remediation-findings/0.1","target_ref":"device-1","findings":[{"code":"DNS_PATH_CONFLICT"}],"missing_fields":[]}
```

Agent 只在证据支持时选对应代码；每条原始证据及时间留在获准私有上下文。选择器不从自然语言猜根因，不推断已通过；导入的目标别名只是匹配检查，不能证明当前主机身份。unknown code 输出固定 UNRECOGNIZED_FINDING 并转 Agent 调查，不回显未知输入。取消覆盖其他动作。空发现不等于环境通过。输入中的 command、authorization 或 apply_supported 字段不影响固定目录且不会回显或执行。

诊断会话使用其 report 子对象；会话 errors、取消、陈旧上下文也须归一化并保留，不可只取成功部分。静态 inventory 的 errors[].code 由 Agent 转换为 findings；文件声明仍不能自动产生规则故障。代理端口冲突要选系统代理分支，不能调用规则 policy 编辑脚本。

<a id="ipv4-only-policy"></a>
## PRODUCT-IPV4-20261018：限定 Claude 范围的 IPv4-only 规划

当前产品默认已确定为 `IPv4_ONLY`，禁止所选 Claude 目标／应用流量回退 IPv6。网络／Claude 准备任务必须检查这个要求，不以“没有 IPv6 旁路发现”为由略过，也不再次要求用户选择协议偏好。该产品选择不授权任何具体网络修改或探测；未知能力仍是 unknown／unsupported，合规尚未建立。

固定接口 `traffic_policy.policy_projection()` 提供当前要求；报告、访谈评估、选择器、语义计划和面板中的 `traffic_policy` 是策略说明，不接纳调用者宣称的 verified／native_pass。`traffic_policy.plan_ipv4_only(scope=None, *, max_seconds=5, cancelled=...)` 返回私有条件计划；`remedy_plans.compile_ipv4_policy_plan` 是同一规划的独立入口，不是旧规则编辑入口。只公开 `preview()` 的固定状态／原因；`private_material()` 中的范围声明仅在获准私有审阅中使用，别名和声明不证明实际设备或覆盖。

没有 scope 时返回未绑定缺口；完整声明最多形成 conditional_plan，仍为 `compliance=not_established`、`environment_pass=false`、`apply_supported=false`、`authorization=none`，原生验证为 not_run。范围支持未知／不支持、IPv6 回退未排除、保留范围冲突、旧意图冲突、陈旧配置分别报告固定 `IPV4_ONLY_*` 原因，不能靠改声明消除真实缺口。默认 5 秒、最多 60 秒合作式预算并保留取消；错误不产生执行权限。

选择器的固定 `ipv4-only-policy` 动作为 candidate_only，显式策略缺口才选择它；不输出网络修改命令。它提示下面的宿主调查／方案闭环，不能替代具体平台的受支持实现和当次授权。

Agent 应给出可审阅的具体下一步，而不只说“脚本不支持”：

1. 绑定实际设备、应用／版本、档案、目标／功能和参与的子进程；分别列出应用到代理、代理到目标及代理节点外层传输。不能用父进程环境变量、IPv4 回环监听或一次 HTTPS 结果代替全链路覆盖
2. 在获准范围检查支持的限定机制、继承／绕过入口与失败回退。明确保护外层必要 IPv6／UDP、Codex／独立恢复通道、组织规则、内网／VPN、其他应用、回环及系统接口 IPv6。范围重叠或分离不明先阻塞该变更，不能换全局禁用模板；IPv4 失败时报告不可用，不回退双栈
3. 给出该版本的精确目标、原值→新值、影响、未覆盖项、保留对象及备份／独立恢复步骤。机制未知时先提出一项具体、有限的检查，不猜命令；只有更广作用域机制时另行说明影响和替代方案，取得新的确切范围批准。不得擅自缩小应用／子进程清单来宣称通过
4. 取得当次具体修改许可，并核实实际宿主／平台和可用执行路径。没有内置原生适配器时，仍可调查和提出独立、受支持的最小方案；不得绕过取消、权限拒绝、PC0、陈旧目标或原生执行门禁。普通策略投影、计划和回调声明都不是许可
5. 未来获准变更后先读回，再按同应用／档案／目标腿复测 IPv4 和禁止 IPv6 fallback 的覆盖，包含相关子进程、字面 IPv6／独立解析、浏览器路径及故障／重启／更新场景。联网和故障测试各自需批准；保护恢复通道。AAAA 为空、`curl -4`、IPv6 超时或单次 HTTPS/STUN 成功均不足以报告强制生效。出现未知中间状态先保留证据并调查，不能盲目重复写入

这个策略规划与既有四种语义修复计划分开，不自动往规则编辑候选加入 IPv4 修改或放宽旧兼容路线对外层 IPv6 依赖的保护。旧意图若要求保留目标腿 IPv6，应明确报告与当前策略冲突，不静默改含义。规则候选、G2 或独立修复成功都不能充当本策略通过。

取消、拒绝、目标失配和 no-change 终止结果保持原有优先级；没有具体策略缺口时，不因默认策略投影给无关账号任务自动加入网络动作。已观察到的 IPv6 旁路仍需真实分层证据；IPv6 超时单独保持无结论，不能据此改系统。事故优先分诊与其他安全的独立工作照常进行。

## 能力与覆盖矩阵

| 模块/发现 | 内置动作/具体下一步 | 当前类别 | 复测与缺口 |
|---|---|---|---|
| ENV-01 目标错误、取消、授权拒绝 | 重新绑定/停止/请求精确范围，不换路径绕过拒绝 | clarify/stop | 正确宿主的本轮证据 |
| ENV-01 元数据不全、陈旧、快照变化 | diagnostic_session.py；运行时路径错误按字段定位可信运行时 | read_only_script/agent_investigation | 不承认旧上下文或跨平台结果 |
| ENV-02 配置缺口 | inventory_cli.py capabilities；匹配范围才 static-audit | read_only_script | 版本限制、活动实例、监听归属、运行态仍独立 |
| ENV-02 系统代理端口冲突 | 记录该活动服务该代理类型的原值，确认后Agent通过该环境支持的接口修正端口 | agent_investigation | 重读该项＋获准同程序HTTPS；无系统代理写入器 |
| ENV-03 入口不可用、路径未知 | network_probes.py 有限宿主接口 | host_library_only | 无通用探测CLI；需目标/端点/授权；不自动重启代理 |
| ENV-04 DNS/DoH冲突 | 分层采样；系统/核心/浏览器责任层的单项修改方案 | agent_investigation | os_dns_probe.py/windows_dns_probe.py/mihomo_dns_probe.py为宿主库；无DNS设置写入器 |
| PRODUCT-IPV4-20261018 范围／强制生效缺口 | ipv4-only-policy；绑定 Claude 目标腿并规划限定 IPv4-only、备份／恢复与具体批准 | candidate_only | 无原生强制执行适配；合规尚未建立，保护外层 IPv6／UDP 和控制通道 |
| ENV-04 IPv6旁路、UDP规则错误 | 分应用/地址族修复，保护节点外层IPv6/UDP | agent_investigation | 双栈/UDP独立证据；超时不证明阻断 |
| ENV-04 Fake-IP正常、IPv6超时、时区仅与出口不同 | 保留当前配置，解释局限 | no_change | 不制造修改目标 |
| ENV-05 WebRTC旁路、策略未生效 | 精确版本/Profile/origin与有效策略核对、环境适配的单项调整 | agent_investigation | 无浏览器策略写入器；实际候选与媒体复测 |
| ENV-06 已有规则policy错误/需prepend | repair_cli.py preflight，之后获准私有diff/plan | candidate_only | merge-policy与rules-prepend范围不同；生产execute仍阻塞 |
| ENV-07 程序忽略代理 | 精确启动入口/支持方式，Agent最小配置 | agent_investigation | 无启动器写入器；PC0不运行Claude |
| ENV-08 时钟/时区/语言目标 | 记录原值、确认单项目标、Agent通过系统支持的接口修改 | agent_investigation | 无设置写入器；不按出口地区改时区 |
| ENV-09 清理请求 | 通用请求先确认目标与保护范围；独立选择 C5 后转限定宿主接口 | agent_investigation | 选择器不执行；cleanup_cli/cleanup_transactions 支持限定 POSIX 隔离与恢复，原生归属适配未提供；事故不等于清理授权 |
| ENV-10 故障阻断未验证 | 列保护范围、独立恢复与平台演练方案 | agent_investigation | 无系统故障注入/防火墙写入器 |
| 通用缺依赖、无权限、错误输入/版本 | 定位该项依赖/许可/格式/适配，修正后重跑原检查 | agent_investigation/clarify | 不安装依赖或放松门禁来制造通过 |

所有 guardian.py 已实现 finding/error 与静态 inventory 公开错误码由测试覆盖。网络等归一化代码仅用于 Agent 解释现有获准证据，不代表检测器自动输出或该模块全部实现。

<a id="selected-rule-scope"></a>
## ENV-06：先选择适用来源，再转换整批字节

依据 D-ENV v0.3（2026-10-15）§5.4、§5.7—5.9、D08 与 §0.3／§16.1／§17。Agent先在私有任务上下文登记每项依赖的客户端、版本、启用事实、用途、方向、来源日期及明确出站选择，再决定哪些完整来源进入本次计划。下述是 Agent 的选择责任，不是新增运行时能力或执行许可。

- 已明确关闭的功能保持“关闭”；给定版本明确不使用的依赖标为“不适用”。说明各自排除原因，不把它们改成 unknown、要求启用以通过、列为必测／必改项或默认准备阻塞。事实确实未知时才补该项缺口。已启用且适用的独立功能仍可继续；只改变一个功能时，仅重审依赖它的选择、候选和验证证据，不扩大到其他设置
- `feature_gate` 只是别名，`shared_service` 只是声明；导入器不会核实功能是否开启或共享服务是否属于本业务，`binding_components()` 也不携带这些元数据。选择必须发生在导入前，并保留选入／排除理由和每份来源的完整字节、哈希、日期及版本。可选择已独立界定范围的完整来源；不能从混合来源静默删项后仍声称导入原完整来源，不能改格式／来源标签来掩盖不能表达的记录。选定来源无法完整表示时报告限制；导入器仍对所选整批全有或全无，不过滤坏项
- 官方“需要可达”不替用户选择出站动作。共享服务既不能默认用 `datadog/sentry/sift` 关键词全收，也不能换成同样跨业务的宽后缀来绕过限制。只有核实适用范围并明确选定动作的条目才进候选；保留已有其他业务规则、原策略和遥测开关。禁止新增宽泛默认规则不等于删除用户已有宽规则。对所选主机及同服务其他业务、后缀根域／子域和标签边界反例比较第一命中，组织强制与救援规则冲突仍阻止候选
- D01—D12 的已确认条件方向继续用于规划，不重复询问同样产品原则。但新增 `recommendation_pending` 端点、额外依赖和扩大发布范围分别留待评审，不进入默认探测、安装、apply 或其他默认动作；先放入默认计划再问执行许可也不合格。设计采用、实现能力、原生验证和本次操作授权分别记录，`apply_supported=false` 不能补救错误的默认选择

TLS 字段与 Inbound／Outbound 的具体语义见[网络参考](network-and-remedies.md#tls-and-direction-semantics)。候选只改变独立选中的受支持规则；不顺带修 TLS、遥测或目标腿 IPv4 策略。现有编译器的完整快照、保护优先级及原生阻塞保持不变。

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

这个导入接口只补原ENV-T40的一小段来源到现有绑定的能力。下面的独立转换器补充有限provider/JSON谓词转换；ASN、任意动作转换、完整版本适配和原ENV-T40的L+R验收仍未完成。继续扩展须先核对有日期/版本的官方语法，不依赖遗失代码或猜测字段。

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

## ENV-06：受限主规则动作与顺序转换

`rule_policy_conversion.convert_policy_rules` 是另一套纯内存接口，不改变上面的无动作转换器。只支持显式 `mihomo/1.19.32/main-rules-yaml` 与 `sing-box/1.12.0/route-rules-json` 片段互转。前者只有 rules，后者是 route.rules 的 JSON 数组片段，不是完整配置；固定版本是兼容性目标，不是最新或已安装版本。

只接收规范小写 ASCII 精确域名/包含根域的后缀匹配，以及显式一一对应的普通出站标签。按原顺序保留重复项；同一个 JSON 规则内的域名族 OR 展开为连续、同动作条目，并保留每个出现位置的来源关联。不会排序去重，也不会把动作剥掉再导入无动作集合。

每对出站都必须声明两侧为 ordinary_outbound，且 TCP/UDP 均为 terminal_for_tcp_udp；这些声明不是程序已核实的事实。不能凭组名认定终结行为，必须先审阅组成员、特殊处理和协议。DIRECT、REJECT、REJECT-DROP、COMPATIBLE、PASS、PASS-RULE、GLOBAL 七个精确保留标签均拒绝；其他不受支持动作、ASN/额外条件/全局 MATCH/final、未知格式、歧义映射及混合坏项整批报错，不返回部分结果。

no-match 仅声明片段继续交给外层配置处理，两侧必须保留 defer_to_enclosing_configuration。转换不发现或验证实际外层 fallback、命中优先级、最终出口或引擎运行行为，不自动生成默认动作。不能把其有限标签选择结果说成完整配置等价。

宿主示例（全部虚构；只转换已获准读取的字节）：

```python
import hashlib
from rule_policy_conversion import convert_policy_rules, MIHOMO, SING_BOX

raw = b"rules:\n  - 'DOMAIN,api.example.invalid,egress-a'\n"
source = {
    "schema_version": "guardian-rule-source-binding/0.1",
    "source_ref": "source-a", "expected_sha256": hashlib.sha256(raw).hexdigest(),
    "evidence_kind": "user_supplied", "verified_at": "2026-10-18",
    "version_scope": "reviewed-source-v1", "purpose": "selected-dependencies",
    "client_scope": ["client-a"], "feature_gate": "selected-feature",
    "shared_service": False, "activation_state": "candidate",
}
bindings = [{"source_label": "egress-a", "target_label": "out-a",
             "source_kind": "ordinary_outbound", "target_kind": "ordinary_outbound",
             "source_finality": "terminal_for_tcp_udp",
             "target_finality": "terminal_for_tcp_udp"}]
result = convert_policy_rules(raw, MIHOMO, SING_BOX, ["rule-a"], source, bindings)
public_summary = result.preview()
private_output = result.private_material()["output_bytes"]
```

公开摘要不带来源字节、域名、策略标签或元数据；私有结果保持来源、输出、顺序与映射证据。上限与取消遵循接口常量/参数；解析缺依赖不自行安装。此接口没有读写、探测、引擎调用或执行授权。把输出写入哪份配置仍须独立校验完整上下文、精确差异、许可、恢复、读回与实际效果；原 ENV-T40 的完整 L+R 验收仍待逐条件核对。详见仓库 `docs/evidence/rebuild-policy-conversion.md`。

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


## C5：限定清理宿主交接

选择器的 `cleanup.host_handoff` 是固定能力说明，不是已选择操作或执行授权；`target_mutation_supported=false` 和 `builtin_execution=not_available_for_target_mutation` 描述选择器本身。单独的 `cleanup_cli` / `cleanup_transactions` 已提供限定 POSIX 文件操作，但没有原生 Claude 数据发现、归属、停用或写入者排除适配。普通 `CLEANUP_REQUESTED`、事故或历史记录不能替用户选择 C5，也不能从报告中的布尔值恢复许可。

Agent先核对当前目标和独立明确的 `Q-D02=full_claude_data_reset`（评估为 `C5-full-claude-data-reset`）。这仅进入 `scope_inventory`：暂停、事故优先、延期、未完成续接复核或前提失败仍停止依赖步骤。先取得限定盘点许可，核实精确 Claude 专属根、保留项、独立备份及恢复，再准备 `mode=C5-full-local-data` 的私有操作清单。清单声明和摘要本身不证明归属或同意。

实际入口为 `cleanup_cli.main(argument_list, host=reviewed_live_host, entry_request=current_entry)`，使用受信任安装路径导入；选择器不会调用它。plan／quarantine 必须传与清理目标一致的本轮 entry；它只检查 `offline_precheck`，不代替逐操作清理许可，VPS quarantine 明确阻塞。已有计划／回执的 reconcile／restore 不要求新 entry，仍须全套恢复核验。现有参数如下，只能通过独立审阅的进程内宿主桥执行目标操作：

```text
plan --scope <private-scope> --plan-output <new-private-plan>
quarantine --plan-file <retained-plan> --expected-plan-digest <document_digest>
reconcile --plan-file <retained-plan> --expected-plan-digest <document_digest> --receipt-output <new-private-receipt>
restore --receipt-file <receipt> --expected-receipt-digest <document_digest>
```

普通脚本运行没有宿主，返回 `HOST_ADAPTER_UNAVAILABLE`；不存在注入宿主模块或“已授权/已核实”的命令行开关。包装命令使用返回的 `document_digest`，不是核心 action digest；它只绑定材料，不授予权限。完整格式与回执恢复见随包[清理CLI用法](cleanup-cli-usage.md)，核心范围见[事故与清理指南](incidents-and-integrations.md#cleanup-migration-and-recovery-m13--env-09)。

宿主必须新鲜核实设备/用户/命名空间、独占 Claude 数据归属、应用与数据库停用、受保护/共享路径、独立内容备份，并在写入和校验期间保持真实写入者排除。`verify` 是获准的宿主核实；`approve` 逐次复核同一次仍有效的精确操作同意；`exclusive` 提供真实排除；`cancelled` 反映撤销或取消。不得用模型自行返回 True 的回调、保存的 JSON 或任意脚本绕过缺失前提。scope读/hash、保存计划、quarantine、reconcile、保存回执和restore各自按当前范围授权；隔离同意不包含恢复同意。

默认保护 CLI、配置、历史和扩展；独立选择且核实归属的 Claude 专属 C5 数据可另行纳入。源码、Codex、其他应用、共享对象和恢复通道继续保护。成功 quarantine 移除所有已选择并验证的活动根，隔离副本、日志及独立备份仍保留；这不是永久安全擦除，也不证明发现所有 Claude 对象。报告确切所选/排除范围和部分完成情况，不声称卸载、清除远程限制或免封。

失败可能发生在真实移动之后，按 recovery_id、moved_count 和 stage 报告，不能因错误码断言未修改。保留计划与隔离批次；重新核实宿主、获准 reconcile 并保存新回执后，另行展示并批准 restore，不覆盖后续改动。永久 purge 未实现，未来需要独立实现和逐动作批准。
