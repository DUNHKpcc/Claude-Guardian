# 整机统一出口：只走 IPv4，不走 IPv6（Clash Verge，Mac 与 Windows）

适用：用户已选**本机路线**，出口 IP 已经定了来源（见[固定出口 IP 的来源](egress-ip-options.md)），要让这台电脑**所有普通应用的公网流量都走同一个 IPv4 出口，不出现 IPv6**。口径与[现行整机统一路径](agent-remediation.md#ipv4-only-policy)一致。

分工：**配置**由 Agent 按分级授权做；**判定**由 `scripts/egress_verifier.py` 根据 Agent 实际观察到的证据给出，它只读、不采集、不改任何东西。判定通过只说明这些观察成立，不代表平台认可、不代表 IP 纯净、不承诺免封。

## 1. 要达到什么

1. TUN 开启，严格路由，默认路由经 TUN。
2. 核心 `ipv6: false`，DNS 不返回也不使用 IPv6。
3. 规则最后兜底走代理，没有写进规则的直连例外。
4. 浏览器、终端、其他应用、后台服务取样的出口 IPv4 都一致（等于预期出口）。
5. IPv6 探测不可达，WebRTC 没有真实地址，DNS 没有泄漏。
6. 停掉代理核心后**没有任何直连**（故障演练）。
7. 重启、睡眠唤醒、换网之后再验一次，才算持续保护有证据。

## 2. 配置（Clash Verge）

**Clash Verge 的 TUN 和 DNS 开关由客户端设置生成运行时配置，会覆盖同名字段，所以 TUN、DNS 优先在客户端设置界面里改；** 改完用运行时配置读回确认，以当前版本的实际行为为准。合并文件（Merge）里放下面两处：

```yaml
ipv6: false
# 规则末尾：先拒绝 IPv6 目标，再兜底走代理组（组名换成自己的）
rules:
  - IP-CIDR6,::/0,REJECT,no-resolve
  - MATCH,<代理组名>
```

客户端设置里对应：TUN 模式开启，严格路由（strict-route）开启；DNS 开启、IPv6 关闭、增强模式 fake-ip；`dns-hijack` 接管 53 端口。Fake-IP 的边界和回滚后清 DNS 缓存见 [macOS DNS 经验](macos-dns-case-lessons.md) 和 [agent-remediation 第 10 条](agent-remediation.md#post-repair-stability)。

规则里**不要保留** `GEOIP,CN,DIRECT` 之类的直连规则，除非用户明确要这个例外；例外要逐条列出（目的范围、协议、原因），判定里 `direct_exceptions` 填 `listed`，没列清楚的填 `unlisted`，会判失败。

## 3. 怎么做（按档位）

| 步骤 | 档位 | 说明 |
| --- | --- | --- |
| 只读盘点：TUN、路由、核心配置、规则末尾、系统 IPv6 状态 | A | `inventory_cli.py` 或下面的只读命令 |
| 出变更卡：原值→新值、影响（局域网、VPN、DNS）、备份、恢复 | A | |
| 改 Clash Verge 合并文件和客户端 TUN／DNS 设置 | B | 计划批准一次；先备份，改后读回；失败自动恢复原值 |
| 退出和重启 Clash Verge | B | 写文件前先退出，改完再启动 |
| 关闭网卡 IPv6 | **C** | 先确认节点外层不依赖 IPv6；当场确认；见下 |
| 默认出站阻止／killswitch | **C** | 见[本机防火墙提示词](local-firewall-prompts.md) |
| 故障演练（停代理核心） | B（本机且用户在场）／**C**（远程或唯一入口） | |

**Mac：** 写合并文件时，Agent 先 `cp` 备份到用户目录下的私有备份文件夹，写后读回对比哈希；规则扩展（rules-prepend）有内置写入适配器，见 [Mac 修复链](agent-remediation.md#mac-修复链clash-verge-rev-258-的-rules-扩展)，合并文件和客户端设置没有，按上面方式处理。

**Windows：** 没有内置写入引擎，由 Agent 按提示词操作：配置在 `%APPDATA%\io.github.clash-verge-rev.clash-verge-rev\` 下，改前 `Copy-Item` 到私有备份目录，改后 `Get-FileHash` 读回，出问题用备份恢复；TUN 要管理员权限，系统弹窗由用户确认。Windows 防火墙见[本机防火墙提示词](local-firewall-prompts.md)，网卡 IPv6 见 [Windows 网卡 IPv6 提示词](agent-remediation.md#windows-adapter-ipv6-hint)。

**关闭网卡 IPv6（C 档）：** Mac 先 `networksetup -listallnetworkservices` 列出服务名，再 `networksetup -setv6off "<服务名>"`，恢复用 `networksetup -setv6automatic "<服务名>"`。核心 `ipv6: false` 已经挡住代理里的 IPv6，关网卡是更强的一层，不是必须；不关会在判定里留一条建议 `OS_IPV6_NOT_DISABLED`。

## 4. 取证（Agent 实际执行，不替用户编造）

| 要证明的 | Mac | Windows |
| --- | --- | --- |
| TUN 开启、默认路由经 TUN | `route -n get default` 看接口是 `utun*`；`ifconfig | grep utun` | `Get-NetRoute -DestinationPrefix 0.0.0.0/0 | Sort-Object RouteMetric`；`Get-NetAdapter` 找 TUN 网卡 |
| IPv4 出口（浏览器、终端、其他应用、后台各取一次） | 终端 `curl -4 -sS --max-time 10 https://ifconfig.me`；浏览器打开检测页 | `curl.exe -4 -sS --max-time 10 https://ifconfig.me`；浏览器同上 |
| IPv6 不可达 | `curl -6 -sS --max-time 10 https://ifconfig.me`，应失败 | `curl.exe -6 -sS --max-time 10 https://ifconfig.me`，应失败 |
| WebRTC | 包内[本地探测页](../assets/webrtc-probe.html) | 同左 |
| DNS 泄漏 | 检测页（dnsleaktest.com）；看有没有本地运营商解析 | 同左 |
| 系统 IPv6 状态 | `networksetup -getinfo "<服务名>"` | `Get-NetIPInterface -AddressFamily IPv6` |
| 故障演练 | 退出 Clash Verge 或停核心，`curl` 和浏览器应全部失败；再启动应恢复 | 同左 |

AAAA 为空、`curl -4` 成功、一次 HTTPS 成功都不能单独证明整机通过；故障演练里不能让本来就断网的状态冒充"没有直连"。

## 5. 判定

把观察写成证据文件（**放在私有临时目录，含出口 IP，不提交、不上传，用完删除**），再运行：

```
python scripts/egress_verifier.py check --input <证据文件.json>
```

证据文件格式（`guardian-egress-evidence/0.1`，示例用文档保留地址）：

```json
{
  "schema_version": "guardian-egress-evidence/0.1",
  "platform": "macos",
  "target_ref": "mac-a",
  "tun": {"enabled": "yes", "strict_route": "yes", "default_route_via_tun": "yes"},
  "core": {"ipv6": "off"},
  "dns": {"ipv6": "off", "hijack": "yes", "leak_test": "pass"},
  "rules": {"final_match": "proxy", "direct_exceptions": "listed"},
  "firewall": "fail_closed",
  "os_ipv6": "disabled",
  "ipv6_probe": "unreachable",
  "webrtc": "no_leak",
  "failure_drill": "no_direct",
  "samples": [
    {"family": "ipv4", "exit": "203.0.113.9", "process": "browser"},
    {"family": "ipv4", "exit": "203.0.113.9", "process": "terminal"}
  ],
  "expected_exit": "203.0.113.9",
  "lifecycle_checked": ["restart", "sleep_wake", "network_change"]
}
```

取值只能是文档里列的枚举，没观察到就写 `unknown` 或 `not_run`，不能猜。输出的 `status`：

- `established`：8 个必要层都通过（`tun`、`core_ipv6`、`dns`、`rules`、`exit_ipv4`、`ipv6_probe`、`webrtc`、`failure_drill`）。
- `violated`：任一层明确失败，`blockers` 里给出原因；先修再复验。
- `incomplete`：有层没做或不确定，不能说整机已统一。

`persistence` 只有在 `established` 且重启、睡眠唤醒、换网都复验过时才是 `checked`，否则是 `not_established`，要如实告诉用户。`firewall` 和 `os_ipv6` 是建议项，不影响 `status`，会出现在 `advisories`。报告不回显任何 IP。

## 6. 回滚

恢复备份的合并文件和客户端设置，重启 Clash Verge；关过网卡 IPv6 的恢复 `networksetup -setv6automatic`（Windows 用对应的恢复命令）；回滚后清系统 DNS 缓存。默认出站阻止和 killswitch 的回滚见各自文档。

## 7. 限制

- 这套流程**没有在真实设备上跑过**；判定只相信 Agent 提供的观察。
- Windows 没有带事务的写入引擎，靠备份和读回哈希，不是原子替换。
- IPv4 不可用时报告不可用，不回退到 IPv6，也不自动换节点。
- 同一代理链不保证同一公网 IP，样本一致只支持实际测量的范围；IP 漂移要告知用户并复验。
