# Mac PF killswitch 真机测试单

对应 ADR-054 和脚本 [`guardian-pf-killswitch.sh`](../skills/claude-guardian/assets/mac-killswitch/guardian-pf-killswitch.sh)。目的：在真 Mac 上证明两件事——**TUN 正常时一切照常能用**，**核心或 TUN 停掉后什么都直连不出去**——以及保险丝、回滚、开机加载都按设计工作。全部测完之前，Skill 里这条路线写的是“未在真机验证”。

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
| 系统 DNS | `scutil --dns \| grep nameserver \| sort -u` | |
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

> 系统 DNS 如果是路由器的局域网地址（比如 192.168.x.1），加规则后 DNS 查询会走物理网卡被拦，域名全部解析失败。遇到时有两种处理：把系统 DNS 改成一个公网地址（流量会进 TUN 被劫持），或者在 apply 时加 `LAN_NET`。T3 会暴露这个问题，记下你用了哪种。

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
| 规则命中 | `sudo bash guardian-pf-killswitch.sh status` 里 `block drop out` 那条的 Packets | 很小或 0 |

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
python3 <仓库路径>/skills/claude-guardian/scripts/network_check.py run --failure-drill
```

按提示停核心再打开，把结果交给 `egress_verifier.py` 判定。记录判定结论，以及“故障演练”一项的结果。

## T6 浏览器验收

浏览器打开 https://ip.net.coffee/claude/，除语言外全绿；WebRTC 用包内的 `assets/webrtc-probe.html` 再查一次。记录结果。

## T7 换网络、睡眠唤醒

| 场景 | 做法 | 期望 |
| --- | --- | --- |
| 换 Wi-Fi | 连到另一个 Wi-Fi | TUN 恢复后正常；`status` 没有“不在规则里”的 WARN |
| 插有线或 USB 网卡 | 插上新网卡 | `status` 可能出现 WARN（新网卡不在规则里）；重新 apply 后 WARN 消失。记录插上后、apply 前，拔掉 Wi-Fi 时能不能直连（能直连就是没保护，正是 WARN 的意思） |
| 睡眠唤醒 | 合盖 5 分钟再打开 | 规则还在（`status` 有规则），上网正常 |

## T8 开机自动加载

1. `sudo bash guardian-pf-killswitch.sh persist`，期望“已安装开机项”。
2. 暂时关掉 Clash Verge 的开机自启（这样开机后能看到“客户端起来之前”的状态）。
3. 重启 Mac，登录后**先不要开 Clash Verge**：

| 检查 | 期望 |
| --- | --- |
| `sudo bash guardian-pf-killswitch.sh status` | 有规则；最近事件有 `BOOT_LOADED`；主规则集挂载“是” |
| 基线第 1、2 条 | 失败（没有 TUN，被规则拦住） |
| `cat /var/log/claude-guardian-pf.log` | 没有报错 |

4. 打开 Clash Verge 开 TUN：基线恢复。恢复 Clash Verge 的开机自启。

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
| T7 换网络、新网卡、睡眠 | | |
| T8 开机加载 | | |
| T9 回滚、卸载、PF 恢复原状 | | |

把这张表发回来，我按结果改脚本和文档，并把 Skill 里的“未在真机验证”改成实际验证过的环境。
