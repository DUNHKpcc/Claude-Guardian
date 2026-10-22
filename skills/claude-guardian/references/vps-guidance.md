# VPS 路线：开发机（环境一致）

适用：用户已经选择 **VPS 路线**（见 [R-VPS](routes-and-platforms.md)）。VPS 路线是**开发机**：Claude Code 跑在 VPS 上，本机只用 VS Code Remote-SSH 连过去。VPS 当代理中转（自建梯）不属于本路线，那是**本机路线选 IP 出口**时的选项，见[固定出口 IP 的来源](egress-ip-options.md)，不要混为一谈。

只给方案和指引，不代买、不代装、不代配置、不代付款；每一步由用户在自己的服务器上运行，需要 Agent 协助的动作逐项取得具体批准。详细命令见 [S08：VPS Claude 教程（11 页）](../sources/S08-vps-claude-tutorial.pdf)，回答 VPS 路线问题时必附。

## 核心：环境一致

VPS 路线的目的是让**注册、登录、养号、订阅、OAuth、日常使用全部发生在同一个环境**：同一个 IP、同一套系统、语言、时区、地区。所以：

- Claude 的注册、登录、订阅和 OAuth 都在 **VPS 上的远程桌面浏览器**里完成，那个浏览器的互联网出口就是 VPS。
- **不要把本机浏览器和 VPS 混用。**本机只是 SSH、VS Code 和远程桌面的显示端，不在本机浏览器里登录 Claude。
- 好处（S08）：使用环境稳定，不用担心 IP 乱跳，也不用管系统、语言、时区、地区的差异，KYC 跳出的概率低。

## 服务器怎么选

| 项目 | 建议 |
| --- | --- |
| 系统 | **首选 Ubuntu 24.04**（系统完整度高，新手友好，有图形化界面，生态友好） |
| 架构 | 首选 x86_64（VS Code 兼容性最好） |
| 规格 | 2C 到 4C；内存 2G 是 VS Code 最低，4G 用着舒服，大型项目 8G 到 16G；公网 IPv4 |
| 线路 | DMIT（美西 premium）、搬瓦工、AWS、Vultr 等；CN2 GIA 带三网优化的线路（后期走图形化界面更稳定） |
| 区域 | 选你正常使用、且 Anthropic 支持的地区 |

选型参考所有者的 [VPS 推荐报告索引](../sources/vps-recommendations/INDEX.md)（业务、性价比、高端家宽三类），回答时点名具体报告并附链接。创建后用 `bash <(curl -sL IP.Check.Place)` 检查 IP（见 [S07 清单](../sources/S07-vps-script-catalog.md)）；如果随机到的 IP 不好，能找客服换就换。好的机房 IP 不用担心，最后都可以套静态 ISP 出口。

## 出口：两种情况

1. **VPS 自己的 IP 就是出口。**最简单，浏览器、Claude Code 都从 VPS 出去。
2. **套一层家宽出口。**两台机器分工：A 是优化线路 VPS（连接稳定、跑浏览器和开发），B 是家宽出口 VPS（网站看到的 IP）。**浏览器运行在哪台机器，就在哪台机器上给浏览器配出站代理**（例如在 A 上用 SSH 动态转发建 SOCKS5 入口指向 B，再在 A 的浏览器里设置）；只转发桌面入口不等于改了浏览器的出口。详细做法见 [VPS 线路优化与家宽中转教程（R02）](../sources/R02-vps-line-optimization.md)，家宽 VPS 选型见推荐报告里的“高端家宽”类。

不管哪种，登录后都要在远程桌面浏览器里确认出口 IP 是预期的那个（WebRTC 不泄漏真实 IP 可用包内的[本地探测页](../assets/webrtc-probe.html)），再继续注册和订阅。

## 创建与连接

1. **SSH 密钥：**创建服务器时添加自己的 SSH 公钥，或下载服务商生成的密钥；本机私钥不离开本机。
2. **SSH 安全（S08 的几种方案）：**公网加 SSH key（最简单）；Tailscale 加 SSH key（适合个人用户，注意备用出口）；改掉 22 端口；跳板机（门槛最高，适合商业化）。选哪种由用户决定，改动前先确认有云控制台的独立救援入口。
3. **日常开发用户：**不用 root，新建 `dev` 用户并加入 sudo，把授权密钥复制过去，再用 `dev` 重新连接；有条件写 `~/.ssh/config`。

## 开发环境与 Claude Code

装 Node、npm、git；习惯终端的可以装 nvim、mosh、tmux。用官方安装方式装 Claude Code（`curl -fsSL https://claude.ai/install.sh | bash`），`claude --version` 验证。本机装 VS Code 和 Remote-SSH 扩展，在 `~/.ssh/config` 里配 Host，之后项目直接放在服务器的 `~/workspace`。

## 临时远程浏览器（远程桌面）

浏览器**只在这些时候启动**：Claude 注册或登录、养号、购买订阅、OAuth、重新授权。不需要装完整 Ubuntu Desktop。

- S08 的做法：Xvfb 虚拟显示 + Openbox + x11vnc + noVNC，浏览器直接打开，无需安装客户端；也可以用 TigerVNC / Xvnc 或 Xpra，按自己的需求选。
- 浏览器用 Google Chrome，独立的用户数据目录。内存不够先建 swap，实在不行再升级配置；正常只有 Claude 单个标签页，约 500MB 上下。
- **5900 和 6080 绝不直接开放到公网。**x11vnc 只监听本地，从本机用 SSH 本地转发（`ssh -L 6080:127.0.0.1:6080 …`）后，在本机浏览器打开 `http://127.0.0.1:6080/vnc.html`。看到的 Chrome 实际运行在 VPS 上，所以出口是 VPS。不用公网无密码 VNC。
- **用完就关**：OAuth 完成后停掉 Chrome、noVNC、x11vnc、Xvfb，日常不占约 0.6 到 1.2GB 内存；需要重新登录时再启动。关闭命令精确匹配进程，不用宽泛的结束进程命令。

## 注册、养号、订阅、OAuth（与本机路线一致，但全在 VPS 浏览器里）

1. **注册与养号：**按[账号注册与使用节奏](account-onboarding.md)：邮箱注册，Gmail 或 Outlook，Proton 防拦截；**OAuth 之前必须先从 Free 号养号**，Free 至少 3 天再升 Pro，Pro 至少 15 天再升 Max，额度不顶满。
2. **订阅：**在 VPS 的 Chrome 里打开 claude.ai，用自己的真实账号和支付资料，Settings → Billing 选套餐。支付方式按[支付说明](accounts-and-payments.md)，第一项参考 S02。选 Apple 或 Google 内购要在手机上完成，手机端先过[手机端防封要点](mobile-guidance.md)，并注意手机的出口也要和 VPS 一致。
3. **OAuth：**VPS 终端里运行 `claude`，需要登录时执行 `/login`，把给出的授权 URL 复制到 **VPS Chrome**，登录并授权，回到终端。

## 防火墙

- **VPS 自己的 IP 是出口：**用 [vps-guard.sh](../assets/vps-firewall/vps-guard.sh)，参考 VM 的脚本结构：nftables，入站默认丢弃，只放行回环、已建立连接、来自管理来源（`ADMIN_NET`）的 SSH 和 ping、云 DHCP、IPv6 邻居发现；出站不限制。应用后有 **180 秒保险丝**，没有 `confirm` 就自动回滚。
- **套家宽、VPS 上也跑 FlClash TUN：**直接用 [VM 的 install-flclash-killswitch.sh](../assets/vm-killswitch/install-flclash-killswitch.sh)，把 `LAN_NET` 设成你的管理来源网段，`NIC` 设成 VPS 的网卡，出站只走 TUN 或节点真实 IP 和端口，fail-closed。
- 用法与前置：`ADMIN_NET` 必填（固定公网 IP 加 /32，或 Tailscale 网段 100.64.0.0/10）；先 `render` 看规则；**运行前在云控制台确认有独立救援入口，先打快照，在另一个 SSH 会话里确认**，不要只靠一个会话。云厂商安全组和系统防火墙是两层，分别核对。
- 脚本的规则语法经 `nft -c` 在隔离环境检查过，应用和保险丝流程没有在真实服务器上实测，首次使用按上面的顺序小心进行。

## 日常

打开 VS Code → Remote-SSH 到工作区 → 打开 `~/workspace/项目` → 终端里 `tmux new -A -s claude` → `claude`。SSH 断开后任务继续，重连后 `tmux attach -t claude`。只有 Claude 登录失效、订阅管理或重新 OAuth 时才启动远程浏览器。定期看 `free -h`、`df -h`；4C8G 建议留 4G swap。

## 边界

不承诺免封。命令都由用户在自己的服务器上运行，Agent 不自动执行；快照不能恢复解封。
