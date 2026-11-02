# Mac PF killswitch 真机测试单

对应 ADR-054 和脚本 [`guardian-pf-killswitch.sh`](../skills/claude-guardian/assets/mac-killswitch/guardian-pf-killswitch.sh)。目的：在真 Mac 上证明两件事——**TUN 正常时一切照常能用**，**核心或 TUN 停掉后什么都直连不出去**——以及保险丝、回滚、开机加载都按设计工作。2026-11-02 已有[单台 Mac 最终验收报告](../reports/mac-pf-isolated-acceptance-2026-11-02.md)：关键保护和回滚取得通过样本，换网与 UDP 仍未全通过，不能宣布整条路线验收通过。本轮按所有者要求排除时间/时区，不改变以下通用测试项。

## 先读：安全和救援

- 这台 Mac 就在你面前，规则只拦网络，不拦本机终端，所以不会把自己锁在机器外面。任何时候断网了，在本机终端运行：
  ```bash
  sudo bash <仓库路径>/skills/claude-guardian/assets/mac-killswitch/guardian-pf-killswitch.sh rollback
  ```
  脚本不在了就直接：`sudo pfctl -a com.apple/claude-guardian -F rules`。最后手段：`sudo pfctl -d`（整个关掉 PF）。
- `apply` 之后默认 180 秒内不 `confirm` 就自动撤销。前几项测试正是靠它兜底。
- 测试时不要在这台 Mac 上跑会被断网打断的 Agent 会话（见 `agent-on-target.md`）：命令都由你自己在终端里敲。
- `render` 和 `status` 的输出里有**节点真实 IP**，反馈时只写结论和退出码，不要贴 IP。

## T0 记录环境，准备基线

| 项 | 怎么看 | 记录 |
| --- | --- | --- |
| macOS 版本、芯片 | `sw_vers`，`uname -m` | |
| Clash Verge Rev 版本、核心版本 | 客户端“关于”页 | |
| TUN 栈 | 客户端 TUN 设置（gVisor／system／mixed） | |
| 节点类型、节点写的是 IP 还是域名 | 客户端代理页 | |
| 节点是否在 proxy-providers 里 | 订阅配置 | |
| PF 原始状态 | `sudo pfctl -s info \| head -1`（Enabled 或 Disabled） | |
| 系统 DNS | `bash guardian-pf-killswitch.sh dns`（每个网络服务是手动还是自动、走哪张网卡；只记类别） | |
| 物理网卡 | `networksetup -listallhardwareports` | |

准备：

1. **关掉 LuLu 的默认拒绝**（切回放行，或退出 LuLu）。LuLu 按进程拦，会把正常 TUN 流量一起拦掉（Issue #17），和本方案冲突。记下你原来的 LuLu 设置，测完按需要恢复。
2. Clash Verge：TUN 开、严格路由开、IPv6 关、fake-ip、DNS 劫持开（按 `whole-machine-ipv4.md`）。
3. 确认流量走 TUN：`route -n get 1.1.1.1 | grep interface` 应该是 `utunN`。
4. 基线三条，都应该成功（记退出码和 HTTP 码）：
   ```bash
   curl -sS -m 10 -o /dev/null -w "%{http_code}\n" --noproxy '*' https://1.1.1.1/cdn-cgi/trace; echo "exit $?"
   curl -sS -m 10 -o /dev/null -w "%{http_code}\n" --noproxy '*' https://www.cloudflare.com/cdn-cgi/trace; echo "exit $?"
   curl -sS -m 10 -o /dev/null -w "%{http_code}\n" -x http://127.0.0.1:<mixed 端口> https://www.cloudflare.com/cdn-cgi/trace; echo "exit $?"
   ```

> `dns` 有 WARN（网络服务是“自动”，或当前 DNS 走物理网卡）时，按它给的命令把**每个网络服务**的 DNS 设成手动公网地址，再往下测。2026-11-02 第一轮 R3 的域名解析失败，最可能就是这个原因：换网后用了 DHCP 下发的路由器 DNS。不要用 `LAN_NET` 放行系统 DNS，那样查询会绕过代理。

## T1 生成规则（不改系统）

```bash
cd <仓库路径>/skills/claude-guardian/assets/mac-killswitch
bash guardian-pf-killswitch.sh render
```

| 检查 | 期望 |
| --- | --- |
| 退出码 | 0 |
| `cg_nics` | 包含 Wi-Fi（通常 en0）和你实际在用的有线网卡 |
| `cg_nodes` | 你的节点真实 IP，没有 198.18.x.x |
| `cg_node_ports` | 包含你节点的端口 |

节点是域名的，脚本会先查系统解析，结果是 fake-ip 就用 DoH 取真实地址。节点在 proxy-providers 里、或解析不出来时，改用 `NODE_IPS=... NODE_PORTS=...` 手动指定。用了 Hysteria2 端口跳跃（`ports:` 范围）的，这一版不支持，记下来。

## T2 保险丝自动撤销

```bash
sudo bash guardian-pf-killswitch.sh apply
```

1. 立刻跑一遍 T0 的三条基线：应该都成功。
2. **不要 confirm**，等 3 分半钟。
3. `sudo bash guardian-pf-killswitch.sh status`：

| 检查 | 期望 |
| --- | --- |
| 本 anchor 规则 | 空 |
| 最近事件 | `APPLIED` 之后是 `ROLLED_BACK_BY_FUSE` |
| PF 状态 | 和 T0 记录的原始状态一致 |
| 基线三条 | 仍然成功 |

## T3 正常使用（规则生效、TUN 正常）

```bash
sudo bash guardian-pf-killswitch.sh apply
```

在 180 秒内做完：

| 检查 | 命令或做法 | 期望 |
| --- | --- | --- |
| 透明 TUN、IP 字面地址 | 基线第 1 条 | 200，exit 0 |
| 透明 TUN、域名 | 基线第 2 条 | 200，exit 0 |
| 显式代理 | 基线第 3 条 | 200，exit 0 |
| 浏览器 | 随便开两个网站 | 正常 |
| 规则命中 | `sudo bash guardian-pf-killswitch.sh blocked 60`，这 60 秒里正常上网 | 只有组播/广播、链路本地、IPv6 这类；没有公网 TCP/443、公网 UDP/STUN。出现公网 UDP/53 的，记下来（可能是核心自己的上游 DNS） |

全部通过才执行：

```bash
sudo bash guardian-pf-killswitch.sh confirm
```

期望输出“已确认，保险丝已取消”。不通过就让保险丝撤销（或手动 `rollback`），记下哪一项失败、退出码多少。

## T4 停核心演练（最关键）

1. 退出 Clash Verge，并确认核心真的停了：`pgrep -fl mihomo` 没有输出。服务模式下核心可能还在跑，要在客户端里关掉 TUN 或停服务，直到 `pgrep` 为空。
2. 确认路由已经回到物理网卡：`route -n get 1.1.1.1 | grep interface` 应该是 `en0` 之类，**不是** utun。这一步证明下面的失败是规则在起作用，不是因为没有路由。
3. 下面每一条都应该**失败**：

| 检查 | 命令 | 期望 |
| --- | --- | --- |
| IP 字面地址 | 基线第 1 条 | 失败（exit 7 或 28） |
| 域名 | 基线第 2 条 | 失败（exit 6、7 或 28） |
| 显式代理 | 基线第 3 条 | 失败（exit 7，连接被拒） |
| ping | `ping -c 2 -t 5 1.1.1.1` | 100% 丢包 |
| 直接查 DNS | `dig +time=3 +tries=1 @8.8.8.8 example.com` | 超时（如果你把 8.8.8.8 填进了 BOOTSTRAP_DNS，就换一个没填的） |
| UDP | `nc -u -z -w 3 1.1.1.1 443; echo $?` | 记录结果（UDP 的 nc 不一定能区分，主要看上面几项） |
| 浏览器 | 刷新任意网站 | 打不开 |
| 命中计数 | `sudo bash guardian-pf-killswitch.sh status` | `block drop out` 的 Packets 明显增加 |

4. 重新打开 Clash Verge 并开 TUN：基线三条恢复成功。**节点是域名的**，看核心能不能重新连上节点。连不上通常是核心解析节点域名的 DNS 被拦了：查配置里的 `proxy-server-nameserver` 或 `default-nameserver`，把这些 IPv4 填进 `BOOTSTRAP_DNS` 重新 apply 和 confirm，再演练一次。

## T5 项目自带的一次取证

TUN 开着、规则已确认时，按 `whole-machine-ipv4.md` 跑一次：

```bash
python3 <仓库路径>/skills/claude-guardian/scripts/network_check.py run --target-ref mac-test \
  --proxy http://127.0.0.1:<mixed 端口> --failure-drill --evidence-output <私有目录>/evidence-T5.json
```

按提示停核心再打开，把 `evidence-T5.json` 交给 `egress_verifier.py` 判定（`--evidence-output` 每次要用新文件名，里面有出口 IP，不要外传）。记录判定结论，以及“故障演练”一项的结果。

## T6 浏览器验收

浏览器打开 https://ip.net.coffee/claude/，除语言外全绿；WebRTC 用包内的 `assets/webrtc-probe.html` 再查一次。记录结果。

## R 泄漏复查：WebRTC、DNS、IPv6（多次使用）

ADR-039 只证明了一台 Mac 在 TUN 正常时这三项不泄漏；重启、睡眠唤醒、换网之后还没复测过。这一节定义一次复查，下面 R1 到 R4 四个时间点各做一次。

前提：TUN 开着、规则已确认；平时用 Claude Desktop 的，让它**开着**再测（它自己发 STUN/UDP，要在它运行时证明 UDP 也走代理）。

1. **一次取证：**
   ```bash
   python3 <仓库路径>/skills/claude-guardian/scripts/network_check.py run --target-ref mac-test \
     --proxy http://127.0.0.1:<mixed 端口> --output <私有目录>/R<编号>.json
   ```
   `--output` 每次换新文件名。看报告里四项：

   | 项 | 通过的样子 |
   | --- | --- |
   | 路由 | 走 TUN（utun） |
   | IPv6 | 不可达（返回的是 IPv4 字符串也算不可达，见 `whole-machine-ipv4.md`） |
   | DNS | 没有解析服务器在中国（不是 fail） |
   | UDP | STUN 映射地址和 TCP 出口一致。显示 UDP 被拦或无法判定时记“无法判定”，不算通过 |

2. **浏览器 WebRTC：**
   ```bash
   python3 <仓库路径>/skills/claude-guardian/scripts/serve_webrtc.py
   ```
   在你平时用的那个浏览器（和那个配置文件）里打开它打印的本机地址，按页面提示点开始。通过：没有出口以外的公网 IP 候选（局域网、mDNS 候选不算）。
3. **浏览器 DNS 和 IPv6 复核：**打开 https://ip.net.coffee/claude/，除语言外全绿。

| 编号 | 时间点 | 做法 |
| --- | --- | --- |
| R1 | 加了 PF 之后的基线 | T3 confirm 之后、T4 之前 |
| R2 | 睡眠唤醒之后 | T7 合盖 5 分钟、打开、等 TUN 恢复后 |
| R3 | 换网络之后 | T7 换到另一个 Wi-Fi、等 TUN 恢复后 |
| R4 | 重启之后 | T8 重启、打开 Clash Verge 开 TUN 之后 |

## R3+ 换网定向复测（2026-11-02 第一轮 R3 和 UDP 没通过）

用新版脚本（规则带日志）重新 apply、confirm 之后做。

1. **换网前：**`bash guardian-pf-killswitch.sh dns`，确认没有 WARN（没改 DNS 就先按 T0 的提示改）。
2. 另开一个终端先跑 `sudo bash guardian-pf-killswitch.sh blocked 180`，然后在这 3 分钟里：换到另一个网络，等 TUN 恢复，再跑基线三条和 `network_check.py run`（R 那一节的命令）。
3. **换网后：**再跑一次 `dns`。
4. 记录：

| 项 | 记录 |
| --- | --- |
| 换网前后 `dns` 有没有 WARN，各网络服务是手动还是自动 | |
| 基线三条（尤其域名那条是否 exit 6） | |
| `network_check.py` 的路由、DNS、UDP 三项 | |
| `blocked` 汇总（整段贴，里面没有 IP） | |

5. UDP：换网前后各跑 3 次 `network_check.py run`，记 UDP 一项每次的结果。不通过的那几次，`blocked` 里有没有公网 UDP 或公网 UDP/53。

## T7 换网络、睡眠唤醒

| 场景 | 做法 | 期望 |
| --- | --- | --- |
| 换 Wi-Fi | 连到另一个 Wi-Fi | TUN 恢复后正常；`status` 没有“不在规则里”的 WARN |
| 插有线或 USB 网卡 | 插上新网卡 | `status` 可能出现 WARN（新网卡不在规则里）；重新 apply 后 WARN 消失。记录插上后、apply 前，拔掉 Wi-Fi 时能不能直连（能直连就是没保护，正是 WARN 的意思） |
| 睡眠唤醒 | 合盖 5 分钟再打开 | 规则还在（`status` 有规则），上网正常 |

换 Wi-Fi 后做一次 **R3**，睡眠唤醒后做一次 **R2**。

## T8 开机自动加载

1. `sudo bash guardian-pf-killswitch.sh persist`，期望“已安装开机项”。
2. 暂时关掉 Clash Verge 的开机自启（这样开机后能看到“客户端起来之前”的状态）。
3. 重启 Mac，登录后**先不要开 Clash Verge**：

| 检查 | 期望 |
| --- | --- |
| `sudo bash guardian-pf-killswitch.sh status` | 有规则；最近事件有 `BOOT_LOADED`；主规则集挂载“是” |
| 基线第 1、2 条 | 失败（没有 TUN，被规则拦住） |
| `cat /var/log/claude-guardian-pf.log` | 没有报错 |

4. 打开 Clash Verge 开 TUN：基线恢复。然后做一次 **R4**。最后恢复 Clash Verge 的开机自启。

如果重启后规则不在（`status` 显示空），说明系统开机时加载 `/etc/pf.conf` 把我们的规则冲掉了，或者开机项比系统先跑。这是本方案最需要真机确认的一点，请务必记录。

## T9 回滚和卸载

1. `sudo bash guardian-pf-killswitch.sh rollback`：期望提示“开机项还在”；`status` 里规则为空。退出 Clash Verge 后直连能上网。
2. `sudo bash guardian-pf-killswitch.sh uninstall`：期望“已卸载”；`/Library/LaunchDaemons/com.claude-guardian.pf-killswitch.plist` 和 `/Library/Application Support/ClaudeGuardian/pf-killswitch` 都不存在。
3. `sudo pfctl -s info | head -1`：和 T0 的原始状态一致。
4. 按需要恢复 LuLu。

## 反馈表（贴这个，不要贴 IP）

| 项 | 结果（通过／不通过／没做） | 失败时的退出码或现象 |
| --- | --- | --- |
| T0 环境（版本、TUN 栈、节点类型、系统 DNS 类型） | | |
| T1 render | | |
| T2 保险丝自动撤销 | | |
| T3 正常使用 | | |
| T4 停核心演练 | | |
| T4 节点域名时核心能否重连（是否用了 BOOTSTRAP_DNS） | | |
| T5 一次取证判定 | | |
| T6 浏览器验收 | | |
| R1 基线复查（路由／IPv6／DNS／UDP／WebRTC 各一项） | | |
| R2 睡眠唤醒后复查（同上五项） | | |
| R3 换网后复查（同上五项） | | |
| R3+ 换网定向复测（dns 前后、域名是否 exit 6、blocked 汇总、UDP 6 次） | | |
| R4 重启后复查（同上五项） | | |
| R 时 Claude Desktop 是否开着 | | |
| T7 换网络、新网卡、睡眠 | | |
| T8 开机加载 | | |
| T9 回滚、卸载、PF 恢复原状 | | |

把这张表发回来，我按结果改脚本和文档，并把 Skill 里的“未在真机验证”改成实际验证过的环境。
