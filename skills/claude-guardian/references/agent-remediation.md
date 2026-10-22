# Agent 编排检测与修复

> 授权粒度按 [authorization-tiers.md](authorization-tiers.md)：本文里的“具体授权／逐项批准”，在 B 档指批准整个计划一次，在 C 档指当场确认；硬规则不变。

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
8. 本轮范围包含网络修复或用户已明确要求稳定性检查时，在继续获准工作的条件下按[修复后的出口稳定性与生命周期复验](#post-repair-stability)完成交付。取消、拒绝、目标失配及 no-change 的原有终止结果不变，不把无关任务改成网络检查

<a id="post-repair-stability"></a>
## 修复后的出口稳定性与生命周期复验

这是同一修复闭环中的 Agent 指导，不是新 Skill 或额外执行入口，不新增脚本、守护进程、定时任务或持续监控服务。目标是把当前修复的适用条件、持久化与复验缺口交代清楚；“目前可用”不是长期稳定或故障防直连的认证。以下各项先复用已有事实，只补与本次范围有关的缺口。

1. **绑定实际目标和使用入口。** 核对设备、使用者、命名空间、OS、代理／核心／客户端版本、浏览器档案、所选功能及参与的子进程。区分 GUI、终端、IDE、后台任务和独立解析入口；继承变量不证明采用。本机与 VM 宿主、客机分别绑定，VPS 仍受既有基础非侵入范围限制；不以本机、云端或宿主结果代替其他目标。沿用[路线与平台](routes-and-platforms.md)，不顺带部署或切换路线。

2. **核对自启和配置持久化。** 按实际环境检查现有代理的自启方式、启动顺序和失败表现：macOS 核对应用、登录项或已有服务的实际支持入口；Windows 核对应用、登录启动或已有服务入口；VM 宿主和客机分别核对。先核实版本支持与所有权，不照搬其他平台的命令。记录持久化源、订阅／扩展合并顺序、生成配置、应用载入和运行时配置的关系，区分持久环境变量与已运行进程实际继承的值。只修改生成配置可能被应用回写、重启或订阅更新覆盖；已勾选自启不证明下一次成功启动。缺少受支持入口就明确缺口，不自行安装服务或新建自启脚本。

3. **保持现行整机默认及明确例外。** 按[整机路径要求](#ipv4-only-policy)核对所有普通应用及子进程；其他应用不再默认置于保护范围之外，用户明确指定的独立路径分别记录。区分应用到代理、代理到目标和上游外层，普通应用目标腿保持 `IPv4_ONLY`。代理失效时非例外范围禁止直连、未经批准的备用出口及 IPv6 fallback；IPv4 不可用就报告不可用。外层地址族、Codex／独立恢复通道、回环、组织规则、内网／VPN与系统 IPv6的影响及例外按该节逐项核实和批准，不直接继承旧保留清单。整机强制覆盖未建立仍是 blocker，不以全局开关掩盖缺口，也不自动换节点。

4. **分开四层证据。** 逐项报告“规则声明”“应用已载入”“目标进程实际采用”“端到端观察”，分别绑定来源、目标／档案／功能、路径、地址族、时间和配置修订。前一层不能代替后一层：文件写入／哈希变化不证明载入，载入不证明每个进程采用，一次 curl／HTTPS 成功不代表整个客户端、DNS、UDP、WebRTC 或故障状态通过。代理回环入口为 IPv4 也不证明代理到目标仅用 IPv4；网络观察不证明服务资格、账号状态或免封。

5. **复用检查与回执，不复活权限。** 在原能力和授权范围内复用已有 check、inventory、探测摘要、精确修复计划和回执，不为新章节增加执行器。核对它们的目标、时间、配置修订、实际观察范围及取消／失败记录；陈旧、矛盾或缺失的部分重新列为缺口，不只挑成功结果。回执不证明应用载入或网络生效，内容核验不证明真实保存／重载。没有保存许可时只在当前对话给出必要脱敏摘要，不另写持久报告；续接不自动恢复旧许可。

6. **按变化复验生命周期。** 列明正常基线、节点失效、GUI 退出但核心仍在、内核停止、代理／应用／子进程重启、系统重启、睡眠唤醒、换网，以及配置／订阅更新和客户端更新后的相关路径。真实演练必须另有具体授权、独立恢复步骤与可用控制通道，不能切断唯一控制通道；不能用本来全网断线证明故障阻断。每个结论需要实际状态切换、新连接尝试和对应观察，恢复后还要核对 Codex、代理、内网与必要应用。未实际执行写 `not_run`，观察不足写 `unknown`；`not_applicable` 须解释真实不适用依据，不能用来隐藏缺能力。变化后旧结论只适用于旧条件，按受影响范围复验，不重做无关访谈。

7. **DNS、UDP 与 WebRTC 独立解释。** 依据[网络证据边界](network-and-remedies.md)分别记录系统解析、代理核心、浏览器解析以及已覆盖的 UDP/TCP DNS、DoH、DoT；不以端口 53 配置或单个查询宣称全部解析被接管。STUN 样本、一般 UDP、WebRTC 候选与媒体路径只能支持其实际采样范围，不能互相代证；中性页面不代表 Claude origin。AAAA 为空、IPv6 超时、没有 ICE 候选或无响应不是阻断证明，仍需区分未发送、端点／网络故障与真实阻断证据。保留代理自身必要 UDP，不为检测页好看先改变候选或放行测试例外。

8. **说明 IP 漂移及提供方局限。** 仅在获准、可比较的同路径观察下描述 IP 漂移，注明时间、条件、地址族与受影响的结论；路径不同或证据不足时先说明不可比。发现非预期变化应告知用户并暂停依赖旧路径结论的步骤，先查当前选择、自动切换和配置更新，不靠反复重试或轮换节点制造稳定结果。“住宅”“固定 IP”是需核验的资源属性／提供方声明，不构成长期可用、出口永不变化、服务资格或免封保证；不据此自动购买、更换供应商或归因账号异常。

9. **具体许可、恢复与诚实交付。** 自启、网络／代理、路由／防火墙、浏览器策略、安装及保存／重载等实际变更，先逐项展示精确目标、原值→新值、影响、保留项、备份和独立恢复方法，再取得对应具体授权。联网、停止进程和故障演练各自核对范围；PC0 不启动 Claude、不访问其目标域名来补证据，后续接触仍过原门禁。若只获准不影响现有配置的测试，这个限制不授权真实设置、保存／重载、重启或故障注入；只做获准的只读或隔离夹具检查。能力未知／不支持分别报告 `unknown`／`unsupported`，必须满足的要求未验证就暂停依赖步骤，不认证全栈安全。交付已确认、已改但未测、尚未覆盖、下一次复验触发条件及恢复说明；不声称已执行未做的动作、持续监视或永久守护。

10. **Fake-IP 回滚后清理系统 DNS 缓存。** 使用 Fake-IP（常见假地址段如 198.18.0.0/15）时，假地址会进入系统 DNS 缓存；代理或 TUN 关闭、回滚后，缓存里的假地址不可达，可能表现为上不了网（失败而非直连泄漏）。独立恢复方案须包含：回滚后核对并清理系统 DNS 缓存，并说明影响。Windows 为 `ipconfig /flushdns`；macOS 为 `sudo dscacheutil -flushcache` 加 `sudo killall -HUP mDNSResponder`。这些是提示词，需用户同意后才执行；`fake-ip-filter` 条目与程序自带 DoH/DoT 的泄漏判断见[网络证据边界](network-and-remedies.md)，Fake-IP 本身不算泄漏。

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

### 受控中性 HTTPS 样本的 /0.2 入口

前文 `guardian-environment-entry-input/0.1` 保持原契约；unknown 示例仍不能主动探测，旧保存计划不会自动升级。为调查未知路径，可信宿主可显式使用 `guardian-environment-entry-input/0.2`，并提供严格的 `guardian-probe-context/0.1`。它区分样本执行者、实际传输方式、当前目标／用户／命名空间、资源声明及来源；整机是验收目标，shell／browser 是不同的取样主体，不能改标签互相代证。

已实现的中性 HTTPS 库仅接收 shell 适配。`direct_socket_os_route_tun_unknown` 表示按操作系统实际路由发送的样本，不宣称绕开 TUN 或确为直连；最终代理协议、未选资源与配置可以如实 unknown，不能为了过门伪填 direct 或 SOCKS。撤回、冲突、陈旧路线／资源及目标错位仍阻塞；configuration 和 PC1／PC2 接触继续要求原严格条件。只有既有中性端点白名单、获准路径和预算范围内的请求可进入此接口，不由 JSON 声明生成许可。

宿主先独立取得实际当前绑定与逐项许可，再构造 `SystemRouteTransport(context_reader=...)`。reader 必须从可信执行环境刷新当前事实；返回调用方复制的 JSON、`source=current_host_observation` 字符串或任意布尔回调都不是独立身份验证。默认没有可信 reader 时拒绝。发送前有界复核实际适配器路径、当前上下文、入口投影和授权；可观察的回调变更会拒绝，不声称这是恶意 Python 调用者的隔离沙箱。

`explicit_proxy` 未新增内置执行器。已有、另经审核的适配器仍须绑定实际端点，并通过 `approved_proxy_endpoints` 取得该具体端点的当前许可；`entry_ref` 别名不能代替地址许可。端点须无凭据，拒绝 userinfo、路径、query／fragment、控制字符和无明确端口等输入；识别某协议语法不代表实现了该协议。不得把认证信息写进对话、报告或错误。browser、未适配的 DNS／诊断入口不因 /0.2 获得能力，仍应报告不支持／阻塞，不改标签转用 shell 或绕过原生上下文门。

结果保留声明与未知来源，范围仅 `single_context_sample_not_whole_machine`；真实路径关联仍可能 unknown，浏览器路径未观察。发送后上下文、路径或许可变化必须保留已经发送的 `request_count=1`，将当前证据降为 unknown，不声称零请求、不自动重试。样本成功不认证整机统一出口、防泄漏、故障持续保护或原生身份。只有具体支持的目标与宿主集成完成后，才恢复原已批准且未失效的检测范围。

### 探测准备失败的受控诊断

WebRTC 本地服务仅报告白名单阶段和错误码，不输出原始异常、路径、请求头或用户名。URL 未发布时可以报告未开始；URL 已开始输出（包括部分输出）后，浏览器采样状态为 unknown，需关闭已加载页面；服务退出或超时不会撤销页面已发出的 STUN。清理失败不能称监听器或全部连接已经关闭，也不能掩盖先发生的错误；只能按实际关闭结果报告。

macOS console 身份 API 返回空值时抛出 `CONTEXT_UNKNOWN`；可信调用方可用 `native_context.api_diagnostic(error)` 读取固定的 `console_user/null_result` 诊断，不能假定所有现有 CLI 已输出该附加字段。这只说明本次未获得可信身份，原因仍未知，不能断言用户未登录或系统权限故障，也不签发会话、不填假身份、不降级门禁。诊断改进不等于已修好原生根因；需在获准的真实执行上下文再次做有界只读核验。

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
## 现行整机统一路径与明确例外（2026-10-19）

2026-10-19 用户确认：同一目标电脑默认统一指定代理路径／出口，优先于 2026-10-18 的仅 Claude 目标范围默认；用户明确要求的软件／进程可独立分流。这里统一当前 Agent 的规划与报告口径，不等于已经启用整机接管，不改写旧设计、来源、验收或工具契约，也不新增脚本、守护进程、后台监视或设置写入器。

1. **默认整机，不能悄悄缩小。** 所有普通应用、子进程、后台服务的公网 TCP／UDP／DNS 都在默认范围，包括自带 DoH、QUIC、WebRTC 的软件；不能因它使用 UDP 或忽略系统代理就自动排除。按获准的目标检查范围识别实际 OS、使用者、进程入口和命名空间；同机 VM／WSL／容器、桥接或其他虚拟网卡的覆盖需明确，未知就列缺口，不自动视为例外，也不借整机目标授权全机扫描。远端电脑仍须独立绑定，不能用本机结果替代。

2. **配置前说明接管方式，再取得具体批准。** 展示拟用的 TUN 或其他该版本实际支持的方式、精确原值→新值、受影响应用、LAN／VPN、DNS、系统服务、控制连接、例外、备份及独立恢复。TUN 不等于 Clash 的 global 模式，不天然提供 kill switch；系统代理、接管机制和规则路由模式是不同层，不能为满足口号盲目打开全局开关。用户接受整机默认只是目标选择，具体配置／权限仍须批准。只获准不影响现有配置的测试时，不授权真实设置、保存／重载、重启或断网；PC0 与停止进程、联网探测的既有门禁不变，故障演练另行批准，不能切断唯一控制通道。

3. **用户明确要求的独立路径。** 核实精确程序／应用身份、相关子进程、共享运行时、目的范围、协议、地址族、指定出口或直连选择、规则优先级及失败行为；不能从软件名称推断用户要直连或放行整个共享运行时。告知它与整机默认的差异和其他程序可能受影响的范围，取得具体配置批准后才实现；默认范围与例外的正常与故障路径分别验收。用户也可明确选择仅 Claude 的窄范围模式，但这不是旧默认的自动恢复。存在例外不能仍称全软件同一路径；请求撤回或改变后重新评估相关配置、证据和许可，不静默恢复旧计划。

4. **检查真正的强制边界和必要例外。** 核对有效路由、TUN 排除、过滤器、代理规则中的 DIRECT／fallback、系统与应用自带解析、UDP和IPv6 字面地址等旁路入口，不能只看代理界面。普通应用目标腿采用 `IPv4_ONLY`，禁止 IPv6 fallback；代理故障时非例外范围禁止直连或切换未经批准的备用出口，不支持的协议报告不可用。代理上游外层、节点 bootstrap／解析、控制、回环、DHCP及必要局域网通信须逐层明确目的地址范围、协议／端口、作用域和必要性，防止代理递归与DNS引导循环；例外清单不是自动放行许可，不得无限放行整个代理进程。普通业务域名解析不自动归入 bootstrap 例外，更新／订阅下载等其他请求也不因进程相同就放行。代理上游外层是否也须 IPv4 依实际依赖明确决定：不自动沿用旧目标模式的外层 IPv6 例外；确有 IPv6／UDP 依赖时先说明影响和替代方案，只有具体批准的外层例外才能保留，也不直接全局关闭 IPv6。Codex／救援获准独立直连也必须列为例外，不能声称全软件零旁路；没有安全恢复或组织策略冲突未解决就暂停相关变更。

5. **证据支持多大范围，就报告多大范围。** 规则声明、应用载入、进程采用、端到端观察分开，按目标／路径／协议／地址族／时间／配置修订记录。相同节点名、系统代理、curl、单个浏览器HTTPS、DNS或STUN样本都不能代替其他程序和故障场景；DNS／UDP／WebRTC沿用各自证据边界。同一代理链不保证同一公网 IP，样本一致只支持实际测量范围；IP漂移仍需告知并复核受影响结论。按[生命周期复验](#post-repair-stability)检查获准的启动、重启、睡眠、换网、更新与失败恢复，并分别验证明确例外。整机强制覆盖未建立不能 pass；能力未知／不支持分别写 `unknown`／`unsupported`，持续保护未建立必须明示，不因有配置或局部通过声称长期守护。

### PRODUCT-IPV4-20261018：旧兼容规划契约

下面保留既有 target-only API 与明确选择窄范围时的规划办法，不定义现行整机默认。`traffic_policy` 在现有CLI、报告、访谈评估、选择器、语义计划及面板仍为 `applies_to=claude_target_application_traffic`、`other_applications=unchanged`；这些输出不代表整机合规，不能改写返回字段、伪造新schema或忽略冲突来声称已支持整机。Agent须另行说明现行默认／明确例外和覆盖缺口，不将旧保护清单自动继承为整机豁免。

固定接口 `traffic_policy.policy_projection()` 提供旧目标范围策略说明，不接纳调用者宣称的 verified／native_pass。`traffic_policy.plan_ipv4_only(scope=None, *, max_seconds=5, cancelled=...)` 返回私有条件计划；`remedy_plans.compile_ipv4_policy_plan` 是同一规划的独立入口，不是旧规则编辑入口。只公开 `preview()` 的固定状态／原因；`private_material()` 中的范围声明仅在获准私有审阅中使用，别名和声明不证明实际设备或覆盖。

没有 scope 时返回未绑定缺口；完整声明最多形成 conditional_plan，仍为 `compliance=not_established`、`environment_pass=false`、`apply_supported=false`、`authorization=none`，原生验证为 not_run。范围支持未知／不支持、IPv6 回退未排除、保留范围冲突、旧意图冲突、陈旧配置分别报告固定 `IPV4_ONLY_*` 原因，不能靠改声明消除真实缺口。默认 5 秒、最多 60 秒合作式预算并保留取消；错误不产生执行权限。

选择器的固定 `ipv4-only-policy` 动作为 candidate_only，显式策略缺口才选择它；不输出网络修改命令。它提示下面的宿主调查／方案闭环，不能替代具体平台的受支持实现和当次授权。

只有用户明确选择相应窄范围方案时才采用以下步骤；其中保留其他应用或外层传输的旧范围声明，不是整机默认下的自动例外。Agent 应给出可审阅的具体下一步，而不只说“脚本不支持”：

1. 绑定实际设备、应用／版本、档案、目标／功能和参与的子进程；分别列出应用到代理、代理到目标及代理节点外层传输。不能用父进程环境变量、IPv4 回环监听或一次 HTTPS 结果代替全链路覆盖
2. 在获准范围检查支持的限定机制、继承／绕过入口与失败回退。明确保护外层必要 IPv6／UDP、Codex／独立恢复通道、组织规则、内网／VPN、其他应用、回环及系统接口 IPv6。范围重叠或分离不明先阻塞该变更，不能换全局禁用模板；IPv4 失败时报告不可用，不回退双栈
3. 给出该版本的精确目标、原值→新值、影响、未覆盖项、保留对象及备份／独立恢复步骤。机制未知时先提出一项具体、有限的检查，不猜命令；只有更广作用域机制时另行说明影响和替代方案，取得新的确切范围批准。不得擅自缩小应用／子进程清单来宣称通过
4. 取得当次具体修改许可，并核实实际宿主／平台和可用执行路径。没有内置原生适配器时，仍可调查和提出独立、受支持的最小方案；不得绕过取消、权限拒绝、PC0、陈旧目标或原生执行门禁。普通策略投影、计划和回调声明都不是许可
5. 未来获准变更后先读回，再按同应用／档案／目标腿复测 IPv4 和禁止 IPv6 fallback 的覆盖，包含相关子进程、字面 IPv6／独立解析、浏览器路径及故障／重启／更新场景。联网和故障测试各自需批准；保护恢复通道。AAAA 为空、`curl -4`、IPv6 超时或单次 HTTPS/STUN 成功均不足以报告强制生效。出现未知中间状态先保留证据并调查，不能盲目重复写入

这个旧目标范围策略规划与既有四种语义修复计划分开，不自动往规则编辑候选加入 IPv4 修改或放宽旧兼容路线对外层 IPv6 依赖的保护。旧意图若要求保留目标腿 IPv6，应明确报告与其 IPv4-only 契约冲突，不静默改含义；整机需求另按上节核对。规则候选、G2 或独立修复成功都不能充当策略通过。

取消、拒绝、目标失配和 no-change 终止结果保持原有优先级；没有具体策略缺口时，不因默认策略投影给无关账号任务自动加入网络动作。已观察到的 IPv6 旁路仍需真实分层证据；IPv6 超时单独保持无结论，不能据此改系统。事故优先分诊与其他安全的独立工作照常进行。

## 能力与覆盖矩阵

下表列既有动作能力，不是现行整机要求已经实现的声明；旧目标范围候选、其他应用保留和外层传输保护均须按上节核对适用性，不能据此默认豁免整机流量。

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
| ENV-08 时钟/时区/语言目标 | 记录原值、确认单项目标、Agent通过系统支持的接口修改 | agent_investigation | 无通用设置写入器；Agent 不替用户按出口地区决定时区；用户明确指定目标时区时，macOS 可用 `native_claude_state_mac.py timezone <IANA名>`（C 档，终端确认，sudo 密码只在原生隐藏提示输入） |
| ENV-09 清理请求 | 通用请求先确认目标与保护范围；独立选择 C5 后转限定宿主接口 | agent_investigation | 选择器不执行；cleanup_cli/cleanup_transactions 支持限定 POSIX 隔离与恢复，原生归属适配未提供；事故不等于清理授权 |
| ENV-10 故障阻断未验证 | 列保护范围、独立恢复与平台演练方案 | agent_investigation | 无系统故障注入/防火墙写入器 |
| 通用缺依赖、无权限、错误输入/版本 | 定位该项依赖/许可/格式/适配，修正后重跑原检查 | agent_investigation/clarify | 不安装依赖或放松门禁来制造通过 |

所有 guardian.py 已实现 finding/error 与静态 inventory 公开错误码由测试覆盖。网络等归一化代码仅用于 Agent 解释现有获准证据，不代表检测器自动输出或该模块全部实现。

<a id="windows-adapter-ipv6-hint"></a>
## ENV-04：Windows 网卡 IPv6 的提示词（仅提示，无自动执行）

仅当 Windows 目标已有真实证据显示 IPv6 旁路风险，且已核实代理节点外层传输不依赖 IPv6 时，Agent 才向用户提出下面的可选步骤。这是提示词，不是写入器：本 Skill 不提供、也不新增自动修改网卡的脚本，不执行该命令，不把用户同意之外的改动当作授权。

提示须包含：

1. **指明具体网卡**：列出用户实际使用的网卡名称，不对全部网卡或虚拟网卡一刀切；VPN、虚拟机、WSL 网卡须单独说明，未知就不建议。
2. **原值→新值**：先读取并记录该网卡当前 IPv6 绑定状态，再说明拟改为关闭。
3. **操作位置**：图形界面是 `ncpa.cpl` → 该网卡属性 → 取消勾选“Internet 协议版本 6 (TCP/IPv6)”（设备管理器没有此开关）；命令行是管理员 PowerShell 的 `Disable-NetAdapterBinding -Name "<网卡名>" -ComponentID ms_tcpip6`。
4. **恢复方式**：勾回同一选项，或 `Enable-NetAdapterBinding -Name "<网卡名>" -ComponentID ms_tcpip6`；恢复步骤必须在用户操作前给出。
5. **影响说明**：可能影响局域网、VPN、依赖 IPv6 的服务及组织策略；代理节点外层依赖 IPv6 或不确定时不提出此步骤，改为说明替代方案。
6. **复测**：用户同意并自行或授权 Agent 执行后，读回绑定状态，再按同应用／目标腿复测。关闭网卡 IPv6 本身不是合规通过证据，也不等于已阻断所有旁路。

用户拒绝、不确定或策略冲突时保持现状，记为 unknown／未执行；不整机关闭 IPv6 的现行规则不变。

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

这提供原ENV-T40的有限L逻辑证据。独立临时文件写回/恢复测试即使通过，也不代表用户设备、引擎加载、GUI持久化、实际路由或完整R通过。完整L+R仍待逐条件审阅。详细API、版本来源和反例见 git 历史中的 `docs/evidence/rebuild-rule-format-conversion.md`（该目录已移出仓库，见 ADR-010）。

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

公开摘要不带来源字节、域名、策略标签或元数据；私有结果保持来源、输出、顺序与映射证据。上限与取消遵循接口常量/参数；解析缺依赖不自行安装。此接口没有读写、探测、引擎调用或执行授权。把输出写入哪份配置仍须独立校验完整上下文、精确差异、许可、恢复、读回与实际效果；原 ENV-T40 的完整 L+R 验收仍待逐条件核对。详见 git 历史中的 `docs/evidence/rebuild-policy-conversion.md`（该目录已移出仓库，见 ADR-010）。

<a id="prepared-recovery"></a>
## 已替换但回执未完成：精确文件恢复

仅针对`transactions.py`既有POSIX精确文件范围，不处理系统设置、凭据撤销、删除、Windows或应用有效状态。实际变更前须把可信`recovery_cli.py`及`transactions.py`、原始备份和步骤保留在获准私有位置，并核实目标上的独立终端能运行；不能等Agent失联后再要求在线取得步骤。完整命令见仓库`docs/offline-recovery.md`。

1. 写入失败或中间状态不明，先停止自动重试。保留当前文件和私有批次，独立核对目标别名、精确目标路径、批次及选定回执来源；不扫描其他位置，不把备份、base64、完整文件或敏感摘要发到公开报告
2. `inspect --receipt`只读指定回执，摘要仅为未验证候选。经确认精确读取范围后，`reconcile`加`--receipt-digest / --target-ref / --target-path / --backup-batch`读取该范围；宿主库入口是`reconcile(recovery, receipt_path=..., target_ref=..., target_path=..., backup_batch=...)`。分类是当前观察，不是历史apply成功或恢复许可
3. 只有v2 prepared的`prepared_candidate_observed`能进入单独恢复。展示原字节/模式将覆盖的确切当前候选、经审阅语义影响、保留项和恢复风险；保留该完整观察的操作摘要。旧v1 prepared、原文件仍在、已恢复候选和冲突均不走此写入口；不能改schema、伪造applied回执或重建快照消除冲突
4. 可信宿主取得本次具体恢复许可并实际排除所有写入者后，调用`restore_prepared(recovery, observation, target_ref=..., authorize=..., exclusive_access=True)`。两次授权核对必须绑定`restore_prepared`、`digest({'recovery_digest': digest(recovery), 'observation': observation})`及目标；脚本复核回执、原备份、批次和完整当前快照。不能自行返回True、使用保存的JSON权限或模拟终端确认。独立普通终端用`restore-prepared`及`--reconciliation-digest`，要求真实用户分别完成排他条件和两次新的随机挑战确认
5. 观察摘要或任一快照变化就停止，重新调查并展示受影响差异；不自动换摘要重试。成功仅表示本次原字节/模式恢复，保留prepared及恢复结果，不补造历史applied。错误可能发生在已恢复后、结果日志落盘前；用返回的有界批次/尝试别名定位确切`restore-<attempt_id>.prepared.json`，存在时先inspect再按独立范围reconcile。没有日志不等于没有修改；`restored_candidate_observed`只读报告，不重复写入，别名也不证明日志必然存在

固定`cleanup_code`为`STAGING_RETAINED / STAGING_CLEANUP_FAILED / DESCRIPTOR_CLOSE_FAILED`时，主错误之外还存在保留材料或清理失败；按精确范围调查，不宣称没有残留或自动删除可能含秘密的暂存文件。

这使限定恢复路径可由可信宿主调用，并保留Agent不可用时的独立入口；这些恢复入口本身不是写入适配器；写入适配器仅放行 macOS Clash Verge Rev 2.5.8 的 `rules-prepend`（见下文“Mac 修复链”），其余范围 `NATIVE_REPAIR_ADAPTER_UNAVAILABLE` 不变。独立读取/恢复也不能绕过目标权限、PC0或操作系统拒绝。Linux合成临时文件/终端测试不代表Mac/Windows设备、实际断网、应用重载或规则命中通过。

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

普通 `cleanup_cli.py` 运行没有宿主，返回 `HOST_ADAPTER_UNAVAILABLE`；不存在注入宿主模块或“已授权/已核实”的命令行开关。macOS 上用内置宿主 `native_cleanup_mac.py`（固定清单、Claude 已退出、内容校验的备份、用户在真实终端输入确认短语），详见随包清理CLI用法；其他平台没有宿主。包装命令使用返回的 `document_digest`，不是核心 action digest；它只绑定材料，不授予权限。完整格式与回执恢复见随包[清理CLI用法](cleanup-cli-usage.md)，核心范围见[事故与清理指南](incidents-and-integrations.md#cleanup-migration-and-recovery-m13--env-09)。

宿主必须新鲜核实设备/用户/命名空间、独占 Claude 数据归属、应用与数据库停用、受保护/共享路径、独立内容备份，并在写入和校验期间保持真实写入者排除。`verify` 是获准的宿主核实；`approve` 逐次复核同一次仍有效的精确操作同意；`exclusive` 提供真实排除；`cancelled` 反映撤销或取消。不得用模型自行返回 True 的回调、保存的 JSON 或任意脚本绕过缺失前提。scope读/hash、保存计划、quarantine、reconcile、保存回执和restore各自按当前范围授权；隔离同意不包含恢复同意。

默认保护 CLI、配置、历史和扩展；独立选择且核实归属的 Claude 专属 C5 数据可另行纳入。源码、Codex、其他应用、共享对象和恢复通道继续保护。成功 quarantine 移除所有已选择并验证的活动根，隔离副本、日志及独立备份仍保留；这不是永久安全擦除，也不证明发现所有 Claude 对象。报告确切所选/排除范围和部分完成情况，不声称卸载、清除远程限制或免封。

失败可能发生在真实移动之后，按 recovery_id、moved_count 和 stage 报告，不能因错误码断言未修改。保留计划与隔离批次；重新核实宿主、获准 reconcile 并保存新回执后，另行展示并批准 restore，不覆盖后续改动。永久 purge 未实现，未来需要独立实现和逐动作批准。

## Mac 修复链：Clash Verge Rev 2.5.8 的 rules 扩展

范围固定：macOS、Clash Verge Rev 2.5.8、`rules-prepend` 扩展。`merge-policy`、其他版本和其他系统仍返回 `NATIVE_REPAIR_ADAPTER_UNAVAILABLE`。路径固定在 `/Applications/Clash Verge.app/Contents/Info.plist` 和当前用户的 `~/Library/Application Support/io.github.clash-verge-rev.clash-verge-rev/` 下，其他位置一律不放行。

顺序（授权档位见[分级授权](authorization-tiers.md)）：

1. **预检与计划（A 档）：** `repair_cli.py plan` 读取请求、目标和元数据，给出差异、备份位置和恢复办法。
2. **你批准计划（B 档，批准一次）：** 计划里写明会退出和重启 Clash Verge。
3. **退出 Clash Verge（B 档）：** 用 ⌘Q 退出应用，确认 `clash-verge` 不在进程列表里。适配器自己也会检查，应用还在运行就返回 `CLASH_VERGE_RUNNING`，不写入。**后台的核心 `verge-mihomo` 和 root 服务 `clash-verge-service` 不用停**：只有应用会写 profile 文件，服务还是 KeepAlive 会立刻被拉起，停它还会断 TUN。
4. **执行写入：** `repair_cli.py execute` 在适配器会话内备份、原子替换、读回；会话在提交前、授权时、替换前和读回后各复查一次进程和元数据文件（`profiles.yaml`、应用 `Info.plist`、基础 profile）。任何变化返回错误并带恢复批次编号，目标文件要么没动要么可按回执回滚。
5. **重启 Clash Verge（B 档）：** 重新打开应用，让它载入新规则。写入成功只表示文件读回一致，不表示应用已载入。
6. **验证出口与规则命中：** 用现有探测验证出口 IP、DNS 和 WebRTC；失败就用回执回滚，再重启应用。

限制：macOS 没有强制文件锁，适配器只能发现并失败，不能阻止别的进程在两次复查之间写入。只有应用 `clash-verge`（及应用包路径下的进程）算写入者，已在一台真实 Mac 上核对；核心和服务不算（真机上退出应用后它们仍在运行，旧版本把它们也算进去，逼用户 `sudo launchctl bootout`，已取消）。适配器的拒绝路径已真机验证，真实写入与回滚尚未实测。
