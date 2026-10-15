# 需求与实现边界 · 0.1.0 诊断预览版

## 基线与覆盖

依据主设计 v0.1.10、ENV 设计 v0.3 的派生实现。用户已确认首版提供“访谈、检查和修复计划，系统修改与回滚在实机验证后分期开放”。本版本取代设计阶段的“暂不编码”交付限制，但不把接受设计理解为用户电脑操作授权。

- Codex 优先；中文交互；真实 UI 能力不足时短问句回退
- 订阅阶段先于 OS；熟练程度、是否注册、是否付费独立记录
- 本机默认建议须接受；VM/VPS 是可独立进入的完整规划路线
- 本机教程限 macOS/Windows；VM 客机和远端 Linux 保留
- Q-C07 永久停用；Q-C08 为目标套餐；Q-P02/Q-A06 有条件触发
- PC0 不接触 Claude/Anthropic；盘点不等于 PC-G1；明确交接与 PC-G2/登录/付款分开
- 不承诺防封；不输出平台私有风控因果、概率或伪造身份方案
- 私有原始来源不发布；GPL-3.0 仅覆盖本仓库依法可发布的作品

## 功能分层

| 层级 | 首版含义 | 不代表 |
|---|---|---|
| 访谈 | 稳定字段、条件问题、已知去重、缺口与路线摘要 | 问完即有执行授权 |
| 只读检查 | 已实现且获准的目标原生元数据；其余明确 unknown | 全部 ENV-01/02 字段或所有平台已验收 |
| 离线分析 | 对输入事实作范围明确的解释 | 输入来自真实用户设备且已验证 |
| 修复计划 | 具体问题、最小建议、保留项、验证要求与阻塞项 | 已应用、已修复、已实现回滚 |
| 路线教程 | 本机/VM/VPS 的完整生命周期规划 | 自动购买、创建、部署或迁移 |
| 证据索引 | 历史公开来源指针及适用限制 | 本轮实时核验或端点授权 |

主动 IP/DNS/STUN/WebRTC 请求、本地控制器 API 集成、代理/浏览器配置写入、系统设置、账号操作、支付、清理、故障注入与 rollback 不在预览执行范围。命令行参数不能用来绕过这一限制。

## 模块追踪

| 稳定模块 | Skill 参考入口 |
|---|---|
| M00 | references/intake.md；contact-and-safety.md |
| M01 | references/routes-and-platforms.md |
| M02/M03 | references/accounts-and-payments.md |
| M04/M05 | references/network-and-remedies.md |
| M06 | references/routes-and-platforms.md；network-and-remedies.md |
| M07 | references/incidents-and-integrations.md；routes-and-platforms.md |
| M08/M09 | references/routes-and-platforms.md |
| M10 | references/network-and-remedies.md；incidents-and-integrations.md |
| M11/M12/M13 | references/incidents-and-integrations.md |
| M14 | references/evidence-policy.md |
| ENV-01—ENV-10 | references/network-and-remedies.md；各专项入口 |

这里的 references 相对 skills/claude-guardian/。M/ENV 编号只表示覆盖与追踪，不能据此宣传全部脚本已实现。

## 验收与发布门槛

1. 离线访谈测试覆盖：首次订阅、技术老手首次付费、到期重订、已有订阅纯排障、当前停用、已选 VPS、VM 及未接受本机建议
2. 不恢复 Q-C07，不把旧权益作为目标套餐，不让首次用户答旧订阅题；未知/拒答不会伪装为通过
3. 检查目标与执行宿主绑定；云端/WSL/容器不得冒充桌面；权限失败不自动提权
4. 无默认联网、写系统、清理、支付；输出不含秘密，不默认持久化访谈
5. 网络修复建议保留路径/程序/地址族/时间范围；超时不能认定故障阻断已通过
6. 实际 macOS/Windows 验收、浏览器真实路径、事务恢复和主动网络测试保留为未完成门槛；合成测试不关闭这些门槛
7. 公布实际测试结果及限制，不虚构测试数量、平台能力或“全机隔离”

后续开放顺序以证据驱动：完善平台只读采集 → 获准的最小中性端点 → 有版本适配的配置计划/差异 → 实机验证后逐项开放修改与恢复。每项有独立能力声明、保护范围、失败出口和测试证据，保持既有稳定 ID。
