# 进阶路线：远端 Linux 机器的出口钉死与反向隧道管理

适用：目标机器是 Linux（本路线的实测对象是 Omarchy / Arch），**管理者不能直接连到它**（在别人的网络里、NAT 之后、没有公网地址），但要求这台机器的整机出口钉死在一个固定 IP，并且长期可管理。典型是：管理端（Mac 或其他）+ 本地 VM + 远端机器 + 一台兼任出口节点和隧道中转的 VPS。

本路线是 [VM 路线](vm-guidance.md) 和 [VPS 路线](vps-guidance.md) 之上的**进阶层**，不是第四种环境：目标机的客机系统、网卡、FlClash TUN 和 killswitch 仍按 VM 指引做；VPS 的购买、IP 检测和 `vps-guard` 仍按 VPS 指引做。本文只写这两者没有的东西：反向隧道、崩溃自愈、钉死覆盖矩阵和运维。**本地 VM 能直接连的，不需要本路线**（用 VM 路线即可）。

授权档位见[分级授权](authorization-tiers.md)：装隧道、装看门狗是 B 档；**启用 killswitch 是 C 档**（默认出站丢弃，在远端等于可能永久失联），当场确认，且必须有独立于代理链路的救援入口。买服务器、付款、注册、登录由用户本人完成。脚本的参数化与脱敏部分没有在真机上整体重跑；它们由所有者在真机上跑通的脚本整理而来，逻辑不变。

## 1. 最终架构

```
[远端 Linux 目标机]
  ├─ FlClash(TUN + fake-ip) ──→ 出口钉死：节点 IP:端口（VPS 兼任节点）
  ├─ nftables killswitch：OUTPUT/INPUT policy drop（fail-closed）
  │    白名单：节点 IP:端口 / 隧道 VPS:sshd 端口 / lo / LAN_NET
  ├─ guardian-reverse-tunnel.service：ssh -R 127.0.0.1:2222:127.0.0.1:22 → VPS
  └─ 崩溃自愈：路由清理 drop-in + core 看门狗 timer
[中转 VPS]
  └─ sshd 回环 127.0.0.1:2222 ← 反向隧道落点
[管理端]
  └─ ssh -L 2222:127.0.0.1:2222 → VPS，再 ssh -p 2222 <用户>@127.0.0.1
```

设计原则：**整机所有流量只能走 FlClash 出口；FlClash 死 = 全断（零泄漏），不回退直连；管理通道的出站独立于代理链路单独放行。**

## 2. 搭建顺序

先做完 [VM 指引 3a 的第 1 到 4 步](vm-guidance.md#3a-linux-客机的搭建顺序omarchy)（目标机有 FlClash、TUN 通、出口是预期 IP）。然后：

1. **VPS 侧准备（B 档）：**sshd 保活和 `authorized_keys` 写法见 [VPS 指引](vps-guidance.md#作为隧道中转的-vps进阶路线)。隧道专用密钥由用户在管理端自己生成，只授权给隧道用途，不复用登录密钥。
2. **装反向隧道（B 档）：**[install-reverse-tunnel.sh](../assets/remote-hardening/install-reverse-tunnel.sh)。必填 `VPS_HOST`（IPv4，killswitch 按 IP 放行，不接受域名）、`VPS_SSH_PORT`、`KEY_PATH`；密钥由脚本复制到目标用户的 `~/.ssh` 并 `chown`、`chmod 600`（sudo 写入的文件属主是 root，sshd 客户端会拒读，表现是服务反复 activating、对端每几秒一次 preauth 断开）。装完在管理端走一遍 `ssh -L` 再 `ssh -p 2222` 确认能进。
3. **装崩溃自愈（B 档）：**[flclash-crash-heal.sh](../assets/remote-hardening/flclash-crash-heal.sh) `install`，生成看门狗 service + timer，并给隧道 unit 加 `ExecStartPre` 清路由的 drop-in。
4. **最后装 killswitch（C 档）：**[install-flclash-killswitch.sh](../assets/vm-killswitch/install-flclash-killswitch.sh)，它会自动读取隧道 unit 的 `user@IP` 和 `-p`，把隧道放进白名单。**在管理端保持一个已登录的会话、目标机本地或宿主机控制台另有一个入口**，`install` 后 180 秒保险丝内 `confirm`；t+15 秒先探活（出口 IP、DNS、隧道仍在），再 `confirm` 固化。顺序反了（先 killswitch 后隧道）或者白名单没覆盖隧道，一启用就失联。
5. **验收：**见第 5 节。

## 3. 隧道专属的坑

- **`authorized_keys` 选项转义是静默失败：**`restrict,permitlisten=\"127.0.0.1:2222\"`（字面反斜杠加引号）会让 OpenSSH 8.9 静默拒绝 `tcpip-forward`。服务端日志干净，客户端只报 `remote port forwarding failed`。选项值一律无引号：`restrict,permitlisten=127.0.0.1:2222`。**服务端日志干净不等于服务端放行**。
- **排查顺序：**VPS `journalctl -u ssh` 看连接记录 → 客户端加 `-vvv` → 检查 `authorized_keys` 格式 → 检查私钥属主和权限。
- **回环端口被占：**VPS 上旧的僵尸连接占着 2222，新隧道 `ExitOnForwardFailure` 退出重连。VPS 侧设 `ClientAliveInterval 15`、`ClientAliveCountMax 2`。
- **`known_hosts` 撞指纹：**管理端的 `[127.0.0.1]:2222` 可能和本机其他服务（如本地 VM 的转发）的旧指纹冲突，清掉旧条目再连。
- **首次启用锁死：**白名单只有节点端口时，隧道断线重连要出站到 VPS 被拦。killswitch 的 `TUNNEL_UNIT` 解析就是为了这个；解析不出来脚本会打印 WARN，这时不要继续。

## 4. 崩溃自愈

`FlClashCore` 死后，FlClash 写的 `ip rule` 和策略路由表（2022）会残留，公网被黑洞，隧道重连包到不了网卡（白名单计数器为 0 可佐证），管理通道丢失。自愈分两层：

- **`routes`：**TUN 不存在时清残留策略路由，挂在隧道 unit 的 `ExecStartPre=+…`，每次重连前先清场。TUN 在或 core 活着时绝不碰路由。
- **`watchdog`：**timer 每 30 秒检查，core 和 TUN 都没了持续 90 秒就以桌面用户拉起 FlClash GUI（GUI 会重建 TUN 和路由）。

实测时序（全程零人工）：`pkill FlClashCore` → t+20 到 80 秒 core 死、TUN 消失、全断（零泄漏）→ t+100 秒看门狗重启 GUI → t+140 秒 TUN 恢复、出口钉死恢复。

systemd 的两个坑已写进脚本：oneshot 默认 `KillMode=control-group` 会杀掉脚本后台拉起的 GUI，所以用 `KillMode=process`；看门狗服务要在服务级写全 `DISPLAY`、`WAYLAND_DISPLAY`、`XDG_RUNTIME_DIR`、`DBUS_SESSION_BUS_ADDRESS`。通过 SSH 手动拉 GUI 时这四个变量同样缺一不可：

```
sudo -E env DISPLAY=:0 WAYLAND_DISPLAY=wayland-1 XDG_RUNTIME_DIR=/run/user/<uid> \
  DBUS_SESSION_BUS_ADDRESS=unix:path=/run/user/<uid>/bus runuser -u <桌面用户> -- flclash &
```

## 5. 验收与覆盖矩阵

钉死思路是**双层加时间轴**：第一层 TUN 在路由层截获一切流量，第二层 nftables fail-closed 在内核层兜底，启动、运行、崩溃、恢复各阶段都有组件接手。

| 场景 | 拦截层 / 机制 | 验证方式 |
| --- | --- | --- |
| 应用绕过代理直连 | TUN 策略路由截获，与进程无关 | 出口 IP 实测 |
| FlClashCore 崩溃或被 kill | TUN 消失 → policy drop 全断，看门狗约 t+140 秒恢复 | `pkill -x FlClashCore` 后 curl 和 DNS 全失败，再恢复 |
| 节点或订阅失效 | TUN 还在但上游不通，等于断网而不是直连 | 断开节点后 curl 失败 |
| DNS 泄漏 | fake-ip 接管 DNS；mihomo 死则 DNS 被 OUTPUT drop | dnsleaktest.com |
| 未知进程发起新连接 | OUTPUT 默认 drop，仅白名单可出 | `nft list ruleset` 看 counter |
| 机器重启冷启动 | nft 先于 FlClash 桌面自启加载，隧道走白名单 | 重启后管理端能重连 |
| 订阅换节点、节点换 IP | refresh.timer 周期重解析 profile 更新白名单 | `killswitch.sh refresh` |
| SSH 管理通道 | 隧道目标出站白名单 + 入站 lo 放行，独立于代理链 | 断开重连 |

**盲区（按可修复性排序）：**

1. **IPv6 出口：**规则表是 `inet` 家族，IPv6 已随 policy drop 一起拦截；盲区在于换桥接或换宿主后环境变了。接入新环境时先 `ip -6 addr show scope global`，有全局 v6 就 `curl -6` 实测应当失败，再武装。
2. **root 改规则：**root 能删 nft、杀看门狗。威胁模型是防泄漏，不防本机 root 沦陷。
3. **`LAN_NET` 直连：**有意保留的宿主侧救援入口，对局域网内设备是裸的。
4. **VPS 单点：**出口节点和管理中转是同一台 VPS，挂了就是断网加失联。这是本架构的固有属性。

## 6. 日常运维

**重连（管理端两步）：**常驻用 launchd / systemd 保持 `ssh -p <VPS端口> -N -L 2222:127.0.0.1:2222 <用户>@<VPS>`，再 `ssh -p 2222 <目标机用户>@127.0.0.1`。目标机的反向隧道是 systemd enabled，VPS 上的入口常开，管理端只补最后一跳。

**体检（目标机上）：**

```
timedatectl && date                          # 时区和时钟
curl -s ipinfo.io | grep -E 'ip|city'        # 出口钉死验证
nft list ruleset | grep -A3 'set proxy'      # 白名单内容
systemctl is-active flclash-killswitch flclash-helper guardian-reverse-tunnel
systemctl list-timers | grep -E 'refresh|watchdog'
ip rule show                                 # core 死后不应有 table 2022 残留
```

**故障恢复：**

| 场景 | 恢复方式 |
| --- | --- |
| core 崩溃（会话内） | 看门狗约 t+140 秒自动恢复；等不到就重启（启动时无路由残留，killswitch 先应用，隧道走白名单直连网卡） |
| killswitch 启用失败导致 SSH 全断 | 180 秒保险丝自动回滚；远端则需要本地终端或宿主机控制台 |
| 反向隧道断 | `Restart=always` 加 `ExecStartPre` 清路由，约 5 秒内重连 |
| 机器重启 | FlClash 自启 + killswitch enabled + 隧道 enabled，整条链自愈 |

## 7. 通用教训

1. fail-closed 白名单必须覆盖**管理通道自身的出站**，不只是代理节点，否则一开就自杀。
2. 任何“先断后验”的操作都带自动回滚保险丝。
3. 代理软件死亡不等于系统恢复直连：TUN 消失后检查策略路由残留，残留本身就是黑洞。
4. 远端改配置不要用 sed 拼引号（引号会丢），用 `base64 | bash` 最稳。
5. 到别人机器上执行长命令，分步粘贴比一把梭稳；终端的 bracketed paste 残留（`^[[200~`）会让命令出错。
6. `pkill -f` 会匹配到自己的命令行，用 `pkill -x` 加精确进程名。

## 边界

不承诺免封。出口钉死是网络层的一致性，不是平台许可。快照不能恢复解封。远端机器在他人网络里时，先确认网络所有者和机器所有者同意此项加固，隧道和 killswitch 的任何改动都要有回滚和独立救援入口。密钥、真实 VPS 地址和订阅链接不写进仓库、日志或报告。
