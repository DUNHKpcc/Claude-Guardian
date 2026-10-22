# 本机路线：Clash 与防火墙（Agent 提示词）

适用：用户已选**本机路线**（Mac 或 Windows），出口 IP 已经定了来源（见[固定出口 IP 的来源](egress-ip-options.md)），现在要在自己的电脑上让**所有公网流量只走同一个代理出口**，代理掉线时不直连（fail-closed）。本机路线不提供脚本，**全部用提示词引导**：Agent 一步一步问、说明、出变更卡，用户在自己的电脑上操作，或经逐项批准后由 Agent 在获准的会话里执行。

- **Windows：**用系统自带的 Windows 防火墙（Windows Defender 防火墙）。
- **Mac：**依赖第三方软件 LuLu（Objective-See 的免费开源出站防火墙）。
- 整机统一路径、明确例外、IPv4_ONLY 的要求见[现行整机统一路径](agent-remediation.md#ipv4-only-policy)；DNS、IPv6、WebRTC 的证据解释见[网络与修复建议](network-and-remedies.md)。

## 通用工作方式（两个系统相同）

1. **先问清楚，再动手：**系统版本、用的 Clash 客户端（Clash Verge 或 FlClash）、是否已导入节点配置、是否开了 TUN、电脑是不是公司或学校管理、有没有别的 VPN 或局域网必须保留（NAS、打印机、内网）。组织管理的设备先停下，防火墙策略可能不归用户管。
2. **先看后改：**只读收集现状（当前防火墙状态、现有规则、代理进程路径、TUN 网卡名、节点真实 IP 和端口），不改任何东西。
3. **按授权档位做（[authorization-tiers.md](authorization-tiers.md)）：**把能自行撤销、不切断访问的步骤合成一张**计划**，用户批准一次，Agent 连续执行；到可能锁死自己的步骤（默认出站切成阻止等）暂停，写确认单，用户确认后才继续。每步都写清目标、原值→新值、影响、回滚方法、验证方法。
4. **顺序固定：**先让 Clash 的 TUN 跑通并确认出口，再加防火墙。顺序反了会把自己锁在外网之外。
5. **必须做故障演练：**防火墙装好后，停掉代理核心，确认外网全部失败（没有直连），再启动代理确认恢复。没演练就不能说 kill switch 成功，只能说"规则已配置，未验证"。
6. **保留回滚路径：**动手前导出现有规则，备好撤销命令；有第二个会话或另一台设备可以操作，不要只有一个入口。
7. **不承诺：**不承诺免封，不把防火墙当解封办法，不把一次 curl 成功当整机不泄漏。

## Mac

### Mac 上的 Clash（Clash Verge）怎么配

下面是 Agent 引导用户的顺序，界面名称以当前版本为准，先核实实际安装版本再给步骤。

1. **安装与版本：**从官方发布页安装 Clash Verge（Rev），记录版本（本项目对 2.5.8 的 rules 扩展有专门的单条规则任务，见 [agent-rules-task.md](agent-rules-task.md)；其他版本需要对应适配）。不创建扩展、不改订阅原文、不切换 profile，除非用户明确要求。
2. **导入节点配置：**由用户在客户端里导入自己的订阅或节点，Agent 不索取订阅链接、密码或 UUID。
3. **TUN 模式：**在客户端设置里开启 TUN。macOS 上通常需要先安装“服务模式”来获得创建虚拟网卡的权限，会弹系统授权，由用户自己确认。说明影响：TUN 会接管整机流量，局域网、VPN、DNS 可能受影响。
4. **DNS：**TUN 下的 DNS 解析和 Fake-IP 的边界按 [macOS DNS 经验](macos-dns-case-lessons.md) 逐层核对：系统实际解析器、核心配置、浏览器自带 DoH 分开看；Fake-IP 本身不泄漏，但 `fake-ip-filter` 里的域名会真实解析，要核对由谁应答。
5. **验证出口：**浏览器和终端分别确认出口 IP 是预期的那个；WebRTC 用包内的[本地探测页](../assets/webrtc-probe.html)检查；DNS 用检测页确认没有明显的本地运营商解析。
6. **只读盘点：**需要看现有 Clash 配置和控制器时，用只读盘点（`inventory_cli.py`），不读订阅正文、控制器密钥或个人配置哈希。

### Mac 的防火墙：LuLu（第三方）

LuLu 是按进程和目的地过滤出站连接的应用防火墙，**不是系统自带**。Agent 要先把这一点和影响讲清楚，用户同意才继续。

1. **来源与权限：**只从 Objective-See 官方渠道获取；安装需要在“系统设置 → 隐私与安全性”里批准系统扩展，由用户自己点。核实当前版本的许可和兼容性、卸载方法。
2. **想要的效果：**除代理核心之外，其他进程不能直接出站；代理核心只能连节点的真实 IP 和端口；本地回环和必要的局域网例外逐项确认。
3. **配置思路（界面名称以当前版本为准）：**
   - 把 LuLu 设成阻止未匹配规则的连接的模式（Block Mode），或在首次弹窗时对不认识的进程选择阻止。
   - 给**代理核心进程**建一条允许规则，目的地限定为节点的真实 IP 和端口；进程名和路径在活动监视器和 LuLu 弹窗里核对，不凭名字猜。
   - TUN 虚拟网卡上的流量由系统路由到核心，核心再经物理网卡出站，所以允许规则要加在**核心**身上，不是每个应用。
   - Apple 系统进程是否默认放行取决于 LuLu 的设置，要查看当前选项并告知用户影响。
4. **覆盖范围必须实测：**LuLu 对部分系统进程和某些连接类型的过滤有限，**不能假设全覆盖**。用故障演练验证：退出 Clash Verge 并停掉服务模式的核心，确认浏览器、终端、其他常用应用都连不出去；再启动恢复。
5. **回滚：**在 LuLu 里删除自己加的规则或切回放行模式；必要时按官方方法卸载。

Mac 上不建议自己写 PF 规则：Apple 的技术说明不建议把 PF 当稳定接口使用，规则和系统的交互难以预测（见 ADR-006）。

## Windows

### Windows 上的 Clash

1. 客户端（Clash Verge 或 FlClash）从官方发布页安装，记录版本；用户自己导入节点配置，Agent 不索取订阅链接和密码。
2. **TUN：**开启 TUN 需要管理员权限，由用户确认系统弹窗。说明影响：整机流量被接管，局域网、VPN、DNS 可能受影响。
3. **网卡 IPv6：**如果有 IPv6 旁路风险，按 [Windows 网卡 IPv6 提示词](agent-remediation.md#windows-adapter-ipv6-hint)（只提示，用户同意后才由用户执行，先确认节点外层不依赖 IPv6）。
4. 验证出口、WebRTC、DNS 的方法同 Mac。

### Windows 的防火墙：系统自带

**先决条件：**用管理员 PowerShell；电脑不是组织管理（组策略或 MDM 管理的防火墙，停下，不由用户决定）；TUN 已跑通并确认出口；**节点真实 IP 和端口**已知（从 profile 里读，域名解析成真实 IP 时要排除 Fake-IP 的 198.18.0.0/15）。

按下面顺序。**第 1 到 3 步是 B 档**（可自行撤销、默认仍放行、不会断网），合成一张计划批准一次；**第 4 步是 C 档**（切默认出站为阻止，可能锁死），到这一步暂停，写确认单，用户当场确认；第 5 步在用户本机且用户在场时按 B 档，目标是远程机器时按 C 档；第 6、7 步是回滚和维护：

1. **导出现有规则并记录原值（只读加备份）：**
   - `netsh advfirewall export "<备份路径>\fw-backup.wfw"`
   - `Get-NetFirewallProfile | Format-Table Name,Enabled,DefaultInboundAction,DefaultOutboundAction`
   把输出里的默认出站动作记下来，这是回滚依据。
2. **布置保险丝（先于任何阻止动作）：**创建一个几分钟后自动把默认出站改回允许的计划任务，用户确认规则有效后再删除它。命令形式（时间换成当前时间加 3 分钟，先在用户机器上核实可用）：
   `schtasks /Create /TN guardian-fw-rollback /SC ONCE /ST HH:MM /RU SYSTEM /TR "powershell -NoProfile -Command Set-NetFirewallProfile -Profile Domain,Private,Public -DefaultOutboundAction Allow" /F`
   确认后删除：`schtasks /Delete /TN guardian-fw-rollback /F`。
3. **先加允许规则（此时默认动作仍是允许，不会断网）：**规则名统一以 `guardian-` 开头，方便整体回滚。
   - 代理核心到节点：`New-NetFirewallRule -DisplayName "guardian-allow-proxy-core" -Direction Outbound -Program "<核心程序完整路径>" -RemoteAddress <节点IP> -RemotePort <端口> -Protocol TCP -Action Allow`，UDP 节点（如 Hysteria2、TUIC）再加一条 UDP。
   - TUN 网卡：`New-NetFirewallRule -DisplayName "guardian-allow-tun" -Direction Outbound -InterfaceAlias "<TUN 网卡别名>" -Action Allow`（别名用 `Get-NetAdapter` 核实）。
   - DHCP：`New-NetFirewallRule -DisplayName "guardian-allow-dhcp" -Direction Outbound -Protocol UDP -LocalPort 68 -RemotePort 67 -Action Allow`。
   - 回环和必要的局域网例外**逐项核对**，不要假定默认放行；有则加规则。
4. **最后切换默认出站为阻止（保险丝已就位）：**`Set-NetFirewallProfile -Profile Domain,Private,Public -DefaultOutboundAction Block`。切换后立刻验证出口仍通、浏览器可用。
5. **故障演练：**停掉代理核心，确认外网全部失败（没有直连）；再启动，确认恢复。通过后删除保险丝任务。未演练就不删。
6. **回滚：**`Set-NetFirewallProfile -Profile Domain,Private,Public -DefaultOutboundAction Allow`，再 `Get-NetFirewallRule -DisplayName "guardian-*" | Remove-NetFirewallRule`；必要时 `netsh advfirewall import "<备份路径>\fw-backup.wfw"` 还原整体。
7. **更新后复查：**换节点、改端口、更新客户端后，节点 IP 和核心路径可能变，规则要同步更新，否则会断网。

以上命令基于 PowerShell 和 netsh 的通用用法，**没有在真实机器上实测**；Agent 首次使用前先在 `-WhatIf` 或只读命令里确认参数和别名。

## Agent 不做的事

- 不在没有备份、没有保险丝、没有第二个入口时切换默认出站为阻止。
- 不在组织管理的设备上改防火墙；不绕过策略。
- 不假定回环、局域网、系统进程默认放行；不把“规则配置完成”说成“kill switch 成功”。
- 不自动安装 LuLu、不自动批准系统扩展、不替用户点系统授权弹窗。
- 不索取订阅链接、节点密码、UUID，不把它们写进规则说明或报告。
- 不承诺免封；防火墙和代理都不是账号状态的保证。
