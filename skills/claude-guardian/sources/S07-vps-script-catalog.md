---
title: NodeSeek 常用 VPS 脚本｜可直接执行版
source: https://www.nodeseek.com/post-183694-1
updated: 2026-10-07
tags:
  - VPS
  - Linux
  - Script
  - NodeSeek
---

# 常用 VPS 脚本｜可直接执行版

> 这版只保留**可以直接复制到终端运行的命令**，不再只给项目地址。
>
> `✅` = 2026-10-07 已确认脚本入口仍可访问  
> `⚠️` = 原帖仍提供该命令，但当前未能确认脚本入口状态  
> `🔥` = 会重装系统 / 改网络 / 改防火墙等，执行前务必确认

## 0. 先装常用依赖

Debian / Ubuntu：

```bash
apt update && apt install -y curl wget sudo ca-certificates
```

---

# 1. DD 重装系统

> [!danger]
> 以下命令会**清空系统盘并重装系统**。重要数据先备份。

## ✅ InstallNET：Debian 12

```bash
wget --no-check-certificate -qO InstallNET.sh 'https://raw.githubusercontent.com/leitbogioro/Tools/master/Linux_reinstall/InstallNET.sh' && chmod a+x InstallNET.sh && bash InstallNET.sh -debian 12 -pwd '你的密码'
```

## ✅ 萌咖 InstallNET：Debian 11

把 `你的密码` 和 `你的SSH端口` 改掉：

```bash
bash <(wget --no-check-certificate -qO- 'https://raw.githubusercontent.com/MoeClub/Note/master/InstallNET.sh') -d 11 -v 64 -p '你的密码' -port '你的SSH端口' -a -firmware
```

## ✅ NewReinstall

```bash
wget --no-check-certificate -O NewReinstall.sh https://raw.githubusercontent.com/fcurrk/reinstall/master/NewReinstall.sh && chmod a+x NewReinstall.sh && bash NewReinstall.sh
```

## ✅ Windows 10 DD

```bash
bash <(curl -sSL https://raw.githubusercontent.com/leitbogioro/Tools/master/Linux_reinstall/InstallNET.sh) -windows 10 -lang "cn"
```

原帖给出的默认 Windows 信息：

```text
账户：Administrator
密码：Teddysun.com
```

> [!warning]
> Windows 安装完成后第一时间修改默认密码。本文不收录第三方 Windows 非授权激活命令。

---

# 2. 综合测试

## ✅ bench.sh

```bash
wget -qO- bench.sh | bash
```

## ✅ LemonBench

```bash
wget -qO- https://raw.githubusercontent.com/LemonBench/LemonBench/main/LemonBench.sh | bash -s -- --fast
```

## ⚠️ 融合怪

```bash
bash <(wget -qO- --no-check-certificate https://gitlab.com/spiritysdx/za/-/raw/main/ecs.sh)
```

## ✅ NodeBench

```bash
bash <(curl -sL https://raw.githubusercontent.com/LloydAsp/NodeBench/main/NodeBench.sh)
```

---

# 3. YABS 性能测试

## ✅ 完整测试

```bash
curl -sL yabs.sh | bash
```

## ✅ 跳过网络，测 Geekbench 5

```bash
curl -sL yabs.sh | bash -s -- -i5
```

## ✅ 跳过网络和磁盘，测 Geekbench 5

```bash
curl -sL yabs.sh | bash -s -- -if5
```

## ✅ Geekbench 5，不测 Geekbench 6

```bash
curl -sL yabs.sh | bash -s -- -5
```

---

# 4. 流媒体 / IP 质量

## ⚠️ 常用流媒体解锁检测

```bash
bash <(curl -L -s check.unlock.media)
```

## ⚠️ Media.Check.Place

```bash
bash <(curl -sL Media.Check.Place)
```

## ⚠️ TcpQuality

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/ibsgss/TcpQuality/main/runTcpQuality.sh)
```

## ⚠️ RegionRestrictionCheck

```bash
bash <(curl -L -s https://github.com/1-stream/RegionRestrictionCheck/raw/main/check.sh)
```

## ✅ IP 质量体检

```bash
bash <(curl -sL IP.Check.Place)
```

## ✅ DNS Alice Unlock

> [!warning]
> 会修改 DNS 配置。

```bash
wget https://raw.githubusercontent.com/Jimmyzxk/DNS-Alice-Unlock/refs/heads/main/dns-unlock.sh && bash dns-unlock.sh
```

---

# 5. 测速

## ⚠️ Speedtest

```bash
bash <(curl -sL bash.icu/speedtest)
```

## ⚠️ Taier

```bash
bash <(curl -sL res.yserver.ink/taier.sh)
```

## ⚠️ HyperSpeed

```bash
bash <(curl -Lso- https://bench.im/hyperspeed)
```

## ✅ nws.sh 全球测速

```bash
wget -qO- nws.sh | bash
```

或者：

```bash
curl -sL nws.sh | bash
```

## ✅ nws.sh 区域测速

可选区域：

```text
na
sa
eu
asia
africa
au
middle-east
india
china
iran
indonesia
russia
10gplus
```

例如测亚洲：

```bash
wget -qO- nws.sh | bash -s -- -r asia
```

测中国：

```bash
wget -qO- nws.sh | bash -s -- -r china
```

## ✅ nws.sh iperf3

```bash
wget -qO- nws.sh | bash -s -- -iperf
```

## ✅ Ping + 路由

全球：

```bash
wget -qO- nws.sh | bash -s -- -rt global
```

中国：

```bash
wget -qO- nws.sh | bash -s -- -rt china
```

亚洲：

```bash
wget -qO- nws.sh | bash -s -- -rt asia
```

欧洲：

```bash
wget -qO- nws.sh | bash -s -- -rt eu
```

---

# 6. 回程路由

## ✅ Backtrace：直接看回程

```bash
curl https://raw.githubusercontent.com/ludashi2020/backtrace/main/install.sh -sSf | sh
```

## ✅ AutoTrace：详细回程

```bash
wget -N --no-check-certificate https://raw.githubusercontent.com/Chennhaoo/Shell_Bash/master/AutoTrace.sh && chmod +x AutoTrace.sh && bash AutoTrace.sh
```

## ✅ testrace

原帖用了 `ghproxy`，这里直接使用 GitHub Raw：

```bash
wget https://raw.githubusercontent.com/vpsxb/testrace/main/testrace.sh -O testrace.sh && chmod +x testrace.sh && bash testrace.sh
```

---

# 7. 常用系统功能

## ⚠️ 添加 SWAP

```bash
wget https://www.moerats.com/usr/shell/swap.sh && bash swap.sh
```

## ✅ Fail2ban

> [!warning]
> 会修改 SSH 防爆破 / 防火墙相关配置，运行前确保 SSH 端口设置正确。

```bash
wget --no-check-certificate https://raw.githubusercontent.com/FunctionClub/Fail2ban/master/fail2ban.sh && bash fail2ban.sh 2>&1 | tee fail2ban.log
```

## ✅ 开启内核自带 BBR

适合较新的 Debian / Ubuntu：

```bash
echo "net.core.default_qdisc=fq" >> /etc/sysctl.conf
echo "net.ipv4.tcp_congestion_control=bbr" >> /etc/sysctl.conf
sysctl -p
sysctl net.ipv4.tcp_available_congestion_control
lsmod | grep bbr
```

## ⚠️ 多功能 BBR 脚本

```bash
wget -N --no-check-certificate "https://gist.github.com/zeruns/a0ec603f20d1b86de6a774a8ba27588f/raw/4f9957ae23f5efb2bb7c57a198ae2cffebfb1c56/tcp.sh" && chmod +x tcp.sh && ./tcp.sh
```

## ⚠️ 锐速 / BBR Plus / BBR2 / BBR3

```bash
wget -O tcpx.sh "https://github.com/ylx2016/Linux-NetSpeed/raw/master/tcpx.sh" && chmod +x tcpx.sh && ./tcpx.sh
```

## ⚠️ TCP 窗口调优

```bash
wget http://sh.nekoneko.cloud/tools.sh -O tools.sh && bash tools.sh
```

## ⚠️ WARP

```bash
wget -N https://gitlab.com/fscarmen/warp/-/raw/main/menu.sh && bash menu.sh
```

## TCP 25 端口测试

先安装 telnet：

```bash
apt update && apt install -y telnet
```

测试：

```bash
telnet smtp.aol.com 25
```

---

# 8. 常用环境 / 软件安装

## ✅ Docker

```bash
bash <(curl -sL 'https://get.docker.com')
```

安装完成检查：

```bash
docker --version
docker compose version
```

## ✅ Python 多版本安装

```bash
curl -O https://raw.githubusercontent.com/lx969788249/lxspacepy/master/pyinstall.sh && chmod +x pyinstall.sh && sudo ./pyinstall.sh
```

## iperf3

Debian / Ubuntu：

```bash
apt update && apt install -y iperf3
```

## ✅ Realm

```bash
bash <(curl -L https://raw.githubusercontent.com/zhouh047/realm-oneclick-install/main/realm.sh) -i
```

## ✅ GOST

```bash
wget --no-check-certificate -O gost.sh https://raw.githubusercontent.com/qqrrooty/EZgost/main/gost.sh && chmod +x gost.sh && ./gost.sh
```

## ✅ Aurora Admin Panel

```bash
bash <(curl -fsSL https://raw.githubusercontent.com/Aurora-Admin-Panel/deploy/main/install.sh)
```

## ✅ 哪吒监控

```bash
curl -L https://raw.githubusercontent.com/naiba/nezha/master/script/install.sh -o nezha.sh && chmod +x nezha.sh && sudo ./nezha.sh
```

## ⚠️ Aria2

```bash
wget -N git.io/aria2.sh && chmod +x aria2.sh && ./aria2.sh
```

## ⚠️ 宝塔 Ubuntu

> [!warning]
> 建议执行前确认宝塔官方当前安装地址，原帖中的脚本可能随版本变化。

```bash
wget -O install.sh http://v7.hostcli.com/install/install-ubuntu_6.0.sh && sudo bash install.sh
```

## ✅ PVE 虚拟化

> [!danger]
> 会进行较大规模系统配置修改，只在明确需要 Proxmox VE 时使用。

```bash
bash <(wget -qO- --no-check-certificate https://raw.githubusercontent.com/oneclickvirt/pve/main/scripts/build_backend.sh)
```

## ✅ Argox

```bash
bash <(wget -qO- https://raw.githubusercontent.com/fscarmen/argox/main/argox.sh)
```

---

# 9. 综合工具箱

## ✅ 科技 Lion

```bash
apt update -y && apt install -y curl
bash <(curl -sL kejilion.sh)
```

## ✅ SKY-BOX

```bash
wget -O box.sh https://raw.githubusercontent.com/BlueSkyXN/SKY-BOX/main/box.sh && chmod +x box.sh && clear && ./box.sh
```

---

# 10. 杜甫 / 独立服务器测试

## ⚠️ SICK

```bash
curl -sL https://sick.onl | bash
```

## ⚠️ Aniverse A

```bash
wget https://github.com/Aniverse/A/raw/i/a && bash a
```

## ✅ SICK Hardware Info

```bash
curl -sL https://raw.githubusercontent.com/Yuri-NagaSaki/SICK/refs/heads/main/hardware_info.sh | bash -s -- -cn
```

## ✅ nws.sh

```bash
wget -qO- nws.sh | bash
```

---

# 11. 杜甫 DD 常用参数

先下载 InstallNET：

```bash
wget --no-check-certificate -qO InstallNET.sh 'https://raw.githubusercontent.com/leitbogioro/Tools/master/Linux_reinstall/InstallNET.sh' && chmod a+x InstallNET.sh
```

## Debian 12

```bash
bash InstallNET.sh -debian 12
```

## RAID 0

> [!danger]
> 会重建磁盘 / RAID，请确认数据已经备份。

```bash
bash InstallNET.sh -debian 12 -raid "0"
```

## 指定网络

以下 IP **只是示例，必须改成你自己服务器的参数**：

```bash
bash InstallNET.sh -debian 12 \
  --ip-addr 139.162.52.1 \
  --ip-mask 24 \
  --ip-gate 139.162.52.1 \
  --ip6-addr 2a07:e040:2:1d3::1 \
  --ip6-gate 2a07:e040::1 \
  --ip6-mask 32
```

## 指定 root 密码

```bash
bash InstallNET.sh -debian 12 -pwd '你的强密码'
```

---

# 12. 禁用 IPv6

> [!warning]
> 使用 Docker、Kubernetes、部分代理、双栈网络之前不要随便禁用 IPv6。

```bash
echo "net.ipv6.conf.all.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "net.ipv6.conf.default.disable_ipv6 = 1" >> /etc/sysctl.conf
echo "net.ipv6.conf.lo.disable_ipv6 = 1" >> /etc/sysctl.conf
sysctl -p
```

确认：

```bash
ip -6 addr
```

---

# 13. 我最常用的一套

新 VPS 到手快速检查：

```bash
apt update && apt install -y curl wget sudo ca-certificates
```

IP 质量：

```bash
bash <(curl -sL IP.Check.Place)
```

综合性能：

```bash
curl -sL yabs.sh | bash
```

全球测速：

```bash
wget -qO- nws.sh | bash
```

中国路由：

```bash
wget -qO- nws.sh | bash -s -- -rt china
```

回程：

```bash
curl https://raw.githubusercontent.com/ludashi2020/backtrace/main/install.sh -sSf | sh
```

硬件信息：

```bash
curl -sL https://raw.githubusercontent.com/Yuri-NagaSaki/SICK/refs/heads/main/hardware_info.sh | bash -s -- -cn
```

Docker：

```bash
bash <(curl -sL 'https://get.docker.com')
```

---

> [!important]
> `curl ... | bash` / `wget ... | bash` 会直接执行远程代码。重要生产服务器上建议先下载查看：
>
> ```bash
> curl -fsSL '脚本地址' -o script.sh
> less script.sh
> bash script.sh
> ```
>
> 尤其是 **DD、WARP、BBR、Fail2ban、PVE、DNS 修改** 类脚本。
