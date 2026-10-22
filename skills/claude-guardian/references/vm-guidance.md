# VM 路线：客机系统、网卡、出口与防火墙

适用：用户已经选择 **VM 路线**（见 [R-VM](routes-and-platforms.md)）。选本机或 VPS 路线时不触发。只给方案和指引，不代装系统、不代配置、不代付款；实际操作前逐项展示改动、先打快照，取得具体批准。

## 1. 客机系统怎么选

- **默认首选：Omarchy。**
- **宿主是 Mac：首选 macOS 客机。**
- 创建前用 hypervisor 官方资料核实免费许可、架构兼容性和镜像来源，展示资源上限和磁盘增长；不捆绑付费许可，不克隆带登录状态的模板。

## 2. 创建前先选网卡

虚拟机创建前，网卡选 **LAN 独立网卡**（桥接到局域网，客机有自己的地址），**不选与宿主机一致的 shared NAT**。这样客机在局域网里有独立身份，出口和防火墙可以在客机里单独设置，不和宿主机的网络混在一起。

- 各 hypervisor 的叫法不同（常见是 Bridged 或桥接），按所用软件的官方说明选。
- 创建后记录客机网卡名、局域网网段和客机地址族，后面的防火墙要用。
- 已有 VM 用 NAT 的，不要覆盖现有磁盘，改网卡模式前先打快照并记录原值。

## 3. 出口 IP

直接复用[固定出口 IP 的来源](egress-ip-options.md)：纯净机场、自建梯（可搭配家宽出口）、家宽拼车三种来源，推荐 Max 优先自建，Pro 推荐机场；选 VPS 看 [VPS 推荐报告索引](../sources/vps-recommendations/INDEX.md)。客机里的客户端：Linux 客机（Omarchy）用 FlClash，macOS 客机用 Clash Verge 或 FlClash。出口由客机统一走同一个 IP，不要让客机进程再绕开它。

## 4. 客机防火墙（fail-closed）

参考脚本：[install-flclash-killswitch.sh](../assets/vm-killswitch/install-flclash-killswitch.sh)（脱敏版，适用 Linux 客机 + FlClash TUN，基于 nftables）。

**它做什么：**客机的一切出站流量只能 1）走 FlClash 的 TUN 出去，或 2）发往 profile 里各节点真实服务端的 IP 和端口；DHCP 和局域网内的 SSH、ping 放行，其余一律丢弃。节点 IP 解析时过滤 fake-ip（198.18.0.0/15），解析失败就经隧道 DoH 取真实 IP。TUN 掉线或进程被杀时，外网全断，不会直连出去。IPv6 除 DHCPv6 外不放行，与本项目的 IPv4_ONLY 一致。

**前置条件：**
- 客机里 FlClash 已运行并有 TUN，profile 在 `~/.local/share/com.follow.clash/profiles`。
- 用 `ip link` 确认网卡名，脚本默认 `enp0s1`，不同则设 `NIC=`；TUN 名默认 `FlClash`，不同设 `TUN=`。
- 必须设置 `LAN_NET`（客机局域网网段，如 `192.168.1.0/24`）；可选 `SSH_PORT`、`EXPECTED_EXIT_IP`（固定出口 IP，用于 test 比对）。
- 已安装 nftables；刷新服务由普通用户调用 sudo，需要该用户有免密 sudo，否则定时刷新会失败。

**用法（由用户在客机里自己运行，在虚拟机控制台操作，不要只靠 SSH）：**

```
sudo LAN_NET=<局域网网段> bash install-flclash-killswitch.sh install
bash install-flclash-killswitch.sh confirm      # 180 秒内确认，否则自动回滚
EXPECTED_EXIT_IP=<固定出口IP> bash install-flclash-killswitch.sh test
bash install-flclash-killswitch.sh status
bash install-flclash-killswitch.sh refresh      # 节点 IP 变了手动刷新（每小时也会自动刷新）
bash install-flclash-killswitch.sh uninstall    # 卸载并删除规则
```

**保险丝与验收：**应用规则后有 180 秒保险丝，没有执行 `confirm` 就自动回滚，避免锁死。装好后手动验收：出口 IP 是固定出口；浏览器打开 browserleaks.com/webrtc 和 dnsleaktest.com（WebRTC 也可用包内的[本地探测页](../assets/webrtc-probe.html)），确认没有真实 IP 和真实 DNS；`pkill FlClashCore` 后确认 curl 和 DNS 全部失败，重启 FlClash 后恢复。

**macOS 客机：**没有对应脚本。按[本机路线 L2](routes-and-platforms.md) 的做法评估 LuLu 或系统防火墙，同样要求 TUN 掉线时不直连。

Agent 的角色：解释脚本做什么、检查前置条件、核对参数，帮用户读 test 和 status 的输出；运行和卸载都由用户或经逐动作授权后进行。

## 5. 后续流程：与本机路线一致

客机环境就绪后，按本机路线的顺序继续：

1. **接触前门禁**：PC0，不接触 Claude；登录、支付逐项批准（见 [V3](routes-and-platforms.md)）。
2. **注册与养号**：邮箱注册、Gmail 或 Outlook、Proton，Free 至少 3 天再升 Pro，Pro 至少 15 天再升 Max，见[账号注册与使用节奏](account-onboarding.md)。
3. **订阅与支付**：按[支付说明](accounts-and-payments.md)，第一项参考 S02；选 Apple 或 Google 内购时，手机端先过[手机端防封要点](mobile-guidance.md)。
4. **日常**：宿主网络 → 启动 VM → 客机时钟与网络状态 → 选定客户端；宿主换网、VM 暂停恢复、更新后重测出口和防火墙。

## 边界

不承诺免封。快照不能恢复解封。脚本是 Linux 客机的参考实现，运行前先打快照；共享目录、剪贴板、凭据按 [V1](routes-and-platforms.md) 的边界处理，不默认共享整个用户目录。
