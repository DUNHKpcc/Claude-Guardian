# 本机路线高级扩展：异机远程协助

OpenSSH、Tailscale、内网穿透和远程管理是协助别人部署时的扩展，不是本 Skill 的核心流程，也不是本机路线的前置条件。**目标机已有 Agent 时，默认直接在目标机按[本机指引](local-firewall-prompts.md)操作，不需要建立远程接入。**

本文只在**用户明确选择远程协助**时使用；典型情况是目标机没有可用 Agent，Agent 在管理机，通过获准的通道协助另一台 Mac/Windows 目标机。仍属于 R-LOCAL，本机路线不新增路线值；目标机、日常使用者和管理机分别记录，不能用管理机的网络结果代替目标机验收。

完整原始经验保留在 [S10](../sources/S10-windows-deployment-sanitized.md)，本文负责划清入口与操作范围。VM／VPS 的远端 Linux 反向隧道、自愈和出口钉死继续见[原进阶路线](advanced-route.md)，不把其中的 Linux 脚本套到 Windows。

## 1. 先确定是否需要远程

1. 目标机已有 Agent：回到本机主流程；Agent 链路与待改网络在同机时按 [agent-on-target.md](agent-on-target.md)准备本地恢复。
2. 确需异机协助：先使用用户已有的远程通道；没有通道时才提出 OpenSSH、Tailscale 或内网穿透方案，说明要新增的组件、目标、访问范围、维护成本、备份和回滚。
3. 不为配置 Clash 默认安装远程软件、开 SSH 服务、加 VPS 中转或开放公网端口。组织设备、凭据和可能失联的动作按[分级授权](authorization-tiers.md)处理；本次开发或阅读资料不替代实际操作授权。

## 2. 远程接入与传文件

- **OpenSSH / Tailscale：**S10 [第一节](../sources/S10-windows-deployment-sanitized.md#windows-ssh)记录了管理机 Tailscale 状态、同一 tailnet、Windows 管理员账户公钥位置与权限。先核对两端实际环境；管理员账户的路径取决于当前 `sshd_config`，不推广为所有 Windows 账户的固定路径。
- **内网穿透：**仅在现有通道无法到达目标且用户选定该方案时规划；先说明是否新增中转、监听端口或长期服务，再按范围批准。S10 的 Tailscale 案例不是默认必须做的步骤，也不自动授权其他穿透方式。
- **传脚本：**S10 [第五节](../sources/S10-windows-deployment-sanitized.md#powershell-tools)保留了先写脚本再 scp、PowerShell 5.1 编码及 SYSTEM 用户目录差异。纯本机执行只需采用编码和路径经验，不需要为了传文件启用 SSH。
- **管理通道例外：**只有实际使用该通道时才考虑对应放行规则，列清程序、方向和作用域；无远程管理需求不添加 Tailscale/SSH 例外，不把管理流量另行放行说成所有流量同一出口。

## 3. 远程故障演练

先按[本机主流程](local-firewall-prompts.md)让 TUN、出口和正常联网通过，再处理远程演练。远程停核心、改默认出站、重启后可能连不回来，属于 **C 档**，须当场确认，并先准备备份、保险丝和目标机本地或独立救援入口。

S10 [第三节](../sources/S10-windows-deployment-sanitized.md#windows-firewall)记录了停核心同时断 SSH、远端脚本随会话退出的问题。确需远程演练时，获准后用独立计划任务完成“停核心 → 探测 → 恢复 → 写私有结果”，重连后取回结果；不能拿 SSH 已断代替没有直连的证据。结果路径用目标机的明确私有位置，不把 SYSTEM 的 `USERPROFILE` 当作交互用户目录。

后台演练任务与桌面 GUI 分开：S10 [第八节](../sources/S10-windows-deployment-sanitized.md#verge-runtime)记录了 SYSTEM 会话启动 GUI 的失败；桌面应用应在正确的交互用户会话里运行。桌面开关仍按[晚间复盘](../sources/S10-windows-deployment-sanitized.md#desktop-launcher)验证真实双击入口和 UAC，不能用远程管理员命令或 SYSTEM 测通代替。

## 4. 交付与回滚

网络验收仍在目标机按[整机出口指引](whole-machine-ipv4.md)做；远程扩展额外记录管理通道是否恢复、保险丝与临时任务状态、目标机本地恢复方法。重启、睡眠唤醒和换网没测的继续标未测。

结束时列明本次实际创建的 SSH/Tailscale 配置、授权公钥、计划任务、端口转发和防火墙例外，由用户决定哪些长期保留；不删除原有远程通道。回滚只恢复本次记录的改动，账号、密钥与删除动作仍按对应授权处理。

本文是对 S10 远程经验的分类与引导，不新增远程执行器，也不表示在读者设备上完成了部署或验收。
