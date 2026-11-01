# 出口与本机环境一致：TCP 延迟、TCP 指纹、UA

所有者 2026-11-01 提供。选出口、选本机系统、做浏览器验收、用户问到改 UA 时都按本文。出口 IP 从哪来见[固定出口 IP 的来源](egress-ip-options.md)，浏览器验收见[整机统一出口 5a](whole-machine-ipv4.md#browser-acceptance)。

**为什么要一致：**经代理访问网站时，网站看到的 TCP 连接是从出口服务器发起的，TCP 层的特征（延迟、TTL、TCP 指纹）属于出口那台机器；浏览器的 UA、`navigator.platform`、Client Hints、TLS 指纹属于你本机的浏览器。两边各说各的系统，或者延迟和出口所在地对不上，就是环境矛盾。

## 1. TCP 延迟

解决办法有两个：

1. **选线路优秀的美国 VPS 做出口。**线路差的美国 VPS 延迟高、晚高峰抖动大；按 [VPS 推荐报告索引 R01](../sources/vps-recommendations/INDEX.md) 和[自建梯怎么选 VPS](egress-ip-options.md#自建梯怎么选-vps) 选优化线路的机器，已有的机器按[线路优化](line-optimization.md)诊断。
2. **选物理距离近的出口，例如日本。**物理距离近，延迟天然低。

## 2. TCP 指纹

**代理端（自建出口、机场等）用的是 Linux，你的本机也要用同系统，至少是接近的系统。**

- **Android：**内核就是 Linux，天生不用担心。
- **Mac 和 iOS：**和 Linux 的 TTL 差异不大。
- **Windows：**默认 TTL 是 128，Linux、macOS、iOS、Android 是 64，和 Linux 出口差得最远。Windows 用户在 Linux 客机里使用，按 [VM 路线](vm-guidance.md)装 Omarchy 客机；或者走 [VPS 路线](vps-guidance.md)，直接在 Linux 开发机上用。

自建出口的系统在服务器上用 `cat /etc/os-release` 查。

## 3. UA 与环境一致性

**不要随意修改 UA，保持浏览器原生 UA 最安全。**

UA 插件只改了请求头里的 User-Agent，`navigator.platform`、Client Hints（`Sec-CH-UA-*`）、TLS 指纹和 TCP 指纹都没变，反而制造了矛盾：请求头说是一个系统，其余几层说是另一个系统。

- 已经装了改 UA 的插件或开了 UA 覆盖的，停用或卸载，恢复浏览器原生 UA。浏览器插件由用户自己在浏览器的扩展管理页里操作，Agent 告诉用户看哪里、关哪个。
- 想让 UA 显示成和出口一致的系统，做法是换本机系统（第 2 节），不是改 UA。
- 同理，不用开发者工具的设备模拟、不改 `navigator` 的脚本去伪装平台。

## 4. Agent 什么时候用本文

1. **选路线和出口时：**用户在 Windows 上、出口是 Linux，把第 2 节告诉用户，作为选 VM 或 VPS 路线的理由之一；延迟要求高的，按第 1 节选出口。
2. **浏览器验收时：**[ip.net.coffee/claude](https://ip.net.coffee/claude/) 的设备信息一项不绿，先查有没有改 UA 的插件和 UA 覆盖。
3. **用户问“要不要改 UA”“装个 UA 插件行不行”时：**直接按第 3 节回答。
