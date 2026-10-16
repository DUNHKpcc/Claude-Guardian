# 本地环境状态面板（离线快照）

对应 ENV-01—05 / UI-I06 的可视化报告投影。新增 Python 标准库脚本
`skills/claude-guardian/scripts/status_dashboard.py`，无安装依赖、常驻服务、CDN
或遥测。不会执行采集、探测、修改设置或自动打开浏览器。

## 使用

先使用已有诊断命令在经过授权的目标环境中获得 `guardian-report/0.1`
分析报告或 `env-inventory/0.2` 原生检查 JSON 报告。不要为生成页面而重新运行真实设备检查；已有本地报告即可。

```sh
python skills/claude-guardian/scripts/status_dashboard.py \
  --input /approved-local-directory/report.json \
  --output /approved-local-directory/environment-status.html
```

显式输出路径必须是新文件。生成后由用户自行在浏览器打开 HTML，无需服务器。
退出码 0 仅表示页面生成成功；2 为输入/格式错误，3 为取消或保存拒绝，4 为内部错误。
不会覆盖已有文件；POSIX 新文件权限为 0600。Windows 文件访问权限继承父目录，
应使用用户自己的私有本地目录。输入必须已本地保存、hydrated，不能是网络挂载或云端占位文件。
路径检查不能证明挂载本地性或防御恶意并发路径替换；宿主应独立核实并限制文件访问。

## 显示内容与边界

- 紧凑三列表格：项目、状态、关键事实；优先显示 IPv4、IPv6、DNS 泄露、UDP、STUN、WebRTC、TUN，保留全部 11 个检查项
- 单项证据、来源章节和限制置于原生 `<details>`，默认折叠；报告说明单独折叠
- 白底、细分隔线、小字号、窄屏换行，无营销标题、卡片网格或重复图例；授权边界仅一行
- 严格区分 `verified`、`error`、`unknown`、`not_run`、`authorization_needed`
- 当前报告格式没有完整验收证据，面板不会生成 `verified`；折叠说明保留其含义
- 完成采集、关闭系统代理、TUN 开启都不等于环境通过或失败
- 白名单显示 OS family、S04 架构枚举及进程视图标签、P06 布尔 enabled 或固定格式的Mac默认开关摘要、P11 模式、P12 布尔 TUN；不展示原始版本字符串、地址、端口、路径、用户名、设备标识、凭据或配置
- 仅展示状态为 observed、单字段时间和快照时间均在过去 24 小时内的白名单事实；未来、缺失、过期时间不会被当作当前证据
- Mac文本摘要仅接受采集器已有的完整固定格式；HTTP/HTTPS/SOCKS/PAC/WPAD缺失保留未知，不将scoped值混入默认开关。作用域仅显示存在/未报告，详情未采集，不证明真实路径或代理可用；其他文本不投影
- 报告时间、页面生成时间与合成演示标签独立展示；时钟未经外部核验
- 文件是静态快照，重新打开不会刷新，也不会按浏览时间重新计算时效；需要新证据时重新生成
- 报告内容是未经独立认证的输入声明；页面不是实际授权、身份绑定或完整诊断报告
- 可用 `--probes` 导入现有 HTTPS/STUN 输出；没有样本的检查保持 not_run，不从不同来源拼凑验证结论

输入仅投影有限枚举、布尔、计数和解析后的日期。任意自由文本、发现代码、
原始证据、计划差异、下一步指令均不回显；简短授权边界提醒先确认操作权限。
HTML 输出使用转义；没有 JavaScript、外部资源、表单或链接，CSP 默认禁止所有资源。
分享前仍请复核，因为少量系统和代理摘要也是本地环境信息。

## 验证

```sh
python -m unittest discover -s tests -p test_status_dashboard.py -v
```

覆盖状态分离、秘密/HTML 哨兵、字段白名单、非法类型、逐字段时效、未知来源、
无网络/进程调用、CLI 错误及拒绝覆盖。全部是合成离线测试，不代表 Mac/Windows
原生检测验收。响应式布局适配桌面与窄屏，颜色之外保留中文状态；机器状态保留于 title 和折叠证据中。

## 与设计文档的检查范围对应

页面逐项标注 `sources/design/D-ENV-v0.3.md` 的来源章节：

| 检查项 | 设计章节 | 必须保留的区别 |
| --- | --- | --- |
| 系统与目标 | §19 | 设备、用户、命名空间与系统信息 |
| 代理配置/入口 | §19、§20.1–3 | 系统继承、显式 HTTP/mixed、浏览器路径 |
| TUN 声明与接管 | §20.4.4、§20.6 | 开关和 IPv4/6、DNS、UDP 实际覆盖 |
| IPv4 出口 | §20.3、§20.5 | 各请求路径独立样本；不显示出口 IP |
| IPv6 分层覆盖 | §20.5 | 本机接口、节点外层、目标侧、浏览器 ICE |
| DNS 配置与解析路径 | §20.4 | 系统、DoH、Mihomo、引导解析、Fake-IP |
| DNS 泄露证据 | §20.4.1–4 | 配置声明与实际查询/连接关联；不同解析器不自动判泄露 |
| UDP 可达与业务范围 | §20.6 | 应用 UDP 与隧道外层 UDP；不同目的地/端口/协议 |
| 独立 STUN 映射 | §20.6.1–2 | 原生 Binding 与浏览器样本独立；不显示映射 IP |
| 浏览器/WebRTC | §20.7 | 所选浏览器/Profile、政策、host/srflx/relay 和 IPv6 |
| 代理失效/防直连 | §18、§20.5、ENV-10 | 故障后行为、程序与子进程范围、恢复 |

每项折叠证据给出最早当前观察时间、路径未知/未独立绑定提示及证据限制。
HTTPS 与独立 STUN 的细粒度离线结果可单独导入；DNS、浏览器、一般 UDP 与故障阻断没有因此取得检测证据，继续显示 `not_run`。
不能把上述“展示范围覆盖”当作对应探测器集成或全范围验收完成。

本轮全套 Linux 合成测试：509 项，5 项跳过。
本轮简化设计：面板 23 项离线测试通过（新增表格语义、默认折叠、可见信息预算、状态文字、键盘焦点及过期提示回归）。
静态 HTML 示例已生成，但浏览器进程被执行环境阻止，桌面/移动实际渲染验收为 `not_run`。
响应式 CSS 与无脚本边界已做代码/单元测试检查，不代替截图或真实浏览器验证。

输入出现重复 fact ID（即便值相同）或非字符串 ID 时拒绝生成。只统计 S01—S16、P01—P24 已定义字段；未知 ID 不计入观察证据。

## HTTPS / STUN 离线证据接入（ENV-03/04）

`--probes /approved-local-directory/probe-evidence.json` 可与原有 `--input` 同用。
该附件只投影已经保存的结果，不调用 `network_probes.py` 或 `stun_probe.py`，不添加端点或自动重试。

附件结构：

```json
{
  "schema_version": "guardian-probe-evidence/0.1",
  "target_ref": "local-target-alias",
  "samples": [
    {
      "expected_path_kind": "direct_socket_os_route_tun_unknown",
      "captured_at": "2026-10-15T12:00:00+00:00",
      "result": {"sample_type": "...existing complete probe result..."}
    }
  ]
}
```

上面 `result` 是结构占位，使用时必须换成现有模块返回的完整字典；不是可执行探测请求。
最多 64 个样本；使用现有输入文件大小限制与重复 JSON 键拒绝机制。
HTTPS 读取结果中的 `started_at` / `finished_at`；独立 STUN 当前没有墙钟时间，
因此要求封装宿主在取得结果时单独记录 `captured_at`，缺失时显示时间未知。
渲染时绝不把现在写成采集时间。24 小时窗口只筛选输入时间声明，不能认证时钟或来源。

`target_ref` 与逐条结果的目标别名作精确比较，逐条路径与 `expected_path_kind` 比较。
这只是附件内部声明的一致性，不证明它属于主盘点报告或当前设备；没有跨报告自动身份绑定。
输入的 `approved` / `authorized` / `verified` / provenance 等标志均不授予权限，也不认证来源。
真正的宿主需要另行核实设备、用户、命名空间、版本、配置与实时授权；
这个离线接口不生成 `workflow_guard.Evidence`，也不打开 PC0 接触门禁。

紧凑摘要显示成功声明、取消、过期、时间无效、目标/路径不匹配、超时与授权缺口的数量；
展开保留每条样本的原顺序、固定端点标签、地址族、路径类别、目标声明一致性和解析后的时间。
新旧、成功与失败样本均保留，不用“最后一条成功”覆盖冲突。不同样本的原始目标别名、IP、
端口、异常自由文本、凭据与附带指令不显示。有样本但无更强发现的行状态为 unknown；已有报告错误/授权缺口及其说明继续保留，不能被成功样本覆盖。成功只表示导入的样本声明。

IPv4/IPv6-only HTTPS 样本分开；自然双栈样本标明 ipify_dual，不冒充 IPv6-only 检查。
双栈失败且地址族未知时两行都保留该条不确定样本。独立 STUN 只进入 STUN 行，
不填充一般 UDP、浏览器/WebRTC、DNS 泄露、TUN 或故障阻断的验证状态。
超时不证明阻断，出口地址不证明目标策略或平台许可，测试夹具始终标注为本地夹具。

回归命令：

```sh
python -m unittest discover -s tests -p test_probe_evidence.py -v
python -m unittest discover -s tests -p test_status_dashboard.py -v
```

新测试使用合成记录、注入的 HTTPS transport 和不打开 socket 的 STUN 取消结果；
不运行公网探测、不采集设备，不关闭任何原生平台验收门槛。

本次离线接入回归：13 项适配器测试与 23 项原面板测试通过；完整 Linux 合成测试 522 项，其中 5 项跳过。未进行浏览器渲染或原生设备验收。
