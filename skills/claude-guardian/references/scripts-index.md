# 脚本索引

`scripts/` 下每个脚本一行：它是什么、Agent 什么时候用、对应说明在哪。**入口**可以直接运行（多数只读、离线）；**库**由入口或宿主导入，不直接运行。任何脚本都不授予权限：执行改动按[分级授权](authorization-tiers.md)，原生写入类脚本的真机验收只做了一部分（逐项见仓库的 CHANGELOG 和 ADR-035），没验的不要说成已验。

## 访谈与评估

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `interview_cli.py` | 入口 | 离线访谈：保存、续接、评估，不联网 | [intake.md](intake.md) |
| `interview_flow.py` | 库 | 访谈状态机、问题集、`assessment` 和 `required_references`（本次必附资料）、`authorization` 分级授权记录函数 | [intake.md](intake.md)、[authorization-tiers.md](authorization-tiers.md) |
| `interview_migration.py` | 库 | 旧版访谈格式迁移 | [intake.md](intake.md) |
| `environment_entry.py` | 库 | 环境入口资格（路线选定、PC0） | [agent-remediation.md](agent-remediation.md#environment-entry) |
| `workflow_guard.py` | 库 | 流程门禁（PC0/PC1/PC2 资格） | [contact-and-safety.md](contact-and-safety.md) |

## 检查与报告（只读）

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `guardian.py` | 入口 | 本机 macOS / Windows 基础诊断预览 | [SKILL.md](../SKILL.md)、[network-and-remedies.md](network-and-remedies.md) |
| `inventory_cli.py` | 入口 | Clash 配置与控制器的只读盘点（`capabilities`、`static-audit`） | [network-and-remedies.md](network-and-remedies.md) |
| `clash_inventory.py`、`controller_inventory.py` | 库 | 静态盘点与控制器审计 | [network-and-remedies.md](network-and-remedies.md) |
| `status_dashboard.py` | 库 | 把诊断快照做成离线 HTML 面板 | [agent-remediation.md](agent-remediation.md) |
| `diagnostic_session.py` | 库 | PC0 诊断会话 | [contact-and-safety.md](contact-and-safety.md) |
| `native_context.py`、`windows_native_context.py`、`windows_listener_binding.py` | 库 | 进程上下文与监听端口观察 | [agent-remediation.md](agent-remediation.md) |
| `macos_metadata_observer.py`、`macos_private_read.py` | 库 | macOS 文件元数据观察与私有读取守卫 | [agent-remediation.md](agent-remediation.md) |
| `source_evidence.py` | 库 | 公共来源资料的字节身份 | [source-library.md](source-library.md) |
| `egress_verifier.py` | 入口 | 整机只走 IPv4 出口的判定（`check --input`） | [whole-machine-ipv4.md](whole-machine-ipv4.md) |

## 网络探测（需要单独授权）

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `network_probes.py`、`stun_probe.py`、`dns_probe.py`、`mihomo_dns_probe.py`、`os_dns_probe.py`、`windows_dns_probe.py` | 库 | HTTPS、STUN、DNS 采样与编解码 | [network-and-remedies.md](network-and-remedies.md) |
| `probe_evidence.py` | 库 | 探测输出的离线投影 | [network-and-remedies.md](network-and-remedies.md) |
| `serve_webrtc.py` | 入口 | 在本机回环临时提供 WebRTC 探测页（`assets/webrtc-probe.html`） | [SKILL.md](../SKILL.md) |

## 修复计划与规则（离线，不写入）

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `agent_remediation.py` | 入口 | 根据报告选择修复动作（`select`），不授予执行权 | [agent-remediation.md](agent-remediation.md) |
| `remedy_plans.py`、`traffic_policy.py` | 库 | 语义修复计划、IPv4_ONLY 条件计划（旧目标范围契约） | [agent-remediation.md](agent-remediation.md#ipv4-only-policy) |
| `config_edit_plan.py`、`rules_extension_plan.py`、`agent_rules_task.py` | 库 | 规则候选与单条 rules 扩展任务 | [agent-rules-task.md](agent-rules-task.md) |
| `rule_format_conversion.py`、`rule_policy_conversion.py`、`rule_source_import.py` | 库 | 规则格式与来源导入转换 | [agent-remediation.md](agent-remediation.md) |
| `clash_verge_258.py` | 库 | Clash Verge Rev 2.5.8 归属与链接校验 | [agent-rules-task.md](agent-rules-task.md) |

## 写入与恢复（有事务和备份）

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `repair_cli.py` | 入口 | 修复预检与计划（`plan`、`execute`）；不要加 `-I` | [agent-remediation.md](agent-remediation.md#mac-修复链clash-verge-rev-258-的-rules-扩展) |
| `repair_execution.py` | 库 | 修复写入传输，原生门禁只放行 macOS Clash Verge Rev 2.5.8 的 rules 扩展 | 同上 |
| `native_clash_verge_mac.py` | 库 | 上述门禁的固定 macOS 适配器（应用须已退出，前后复查） | 同上 |
| `transactions.py`、`windows_transactions.py` | 库 | 精确文件事务（POSIX 写入；Windows 只读） | [agent-remediation.md](agent-remediation.md) |
| `recovery_cli.py` | 入口 | 独立的回执检查与恢复（`inspect`、`preview`、`rollback`、`reconcile`） | [agent-remediation.md](agent-remediation.md) |

## 清理（C 档）

| 脚本 | 类型 | 用途 | 说明 |
| --- | --- | --- | --- |
| `cleanup_cli.py`、`cleanup_transactions.py` | 入口、库 | C5 清理的分发器与隔离、对账、恢复核心；单独运行没有宿主 | [cleanup-cli-usage.md](cleanup-cli-usage.md) |
| `native_cleanup_mac.py` | 入口 | macOS 内置宿主：备份、计划、隔离、对账、还原，终端输入确认短语 | [cleanup-cli-usage.md](cleanup-cli-usage.md)、[S06](../sources/S06-macos-cleanup-sanitized.md) |
| `native_claude_state_mac.py` | 入口 | macOS 钥匙串退出登录、`CLAUDE_CODE_SIMPLE`、用户指定时区 | [cleanup-cli-usage.md](cleanup-cli-usage.md) |

Windows 没有清理脚本，按 [windows-cleanup.md](windows-cleanup.md) 用 PowerShell 分步做。

## 随包脚本资产（`assets/`）

| 文件 | 用途 | 说明 |
| --- | --- | --- |
| `assets/vm-killswitch/install-flclash-killswitch.sh` | VM 客机 fail-closed 防火墙 | [vm-guidance.md](vm-guidance.md) |
| `assets/vm-killswitch/install-flclash-tun.sh` | VM 客机安装 FlClash TUN | [vm-guidance.md](vm-guidance.md) |
| `assets/vm-killswitch/enable-guest-ssh.sh` | 开客机 SSH（限管理来源） | [vm-guidance.md](vm-guidance.md) |
| `assets/vps-firewall/vps-guard.sh` | VPS 入站防火墙（带 180 秒保险丝） | [vps-guidance.md](vps-guidance.md) |
| `assets/webrtc-probe.html` | 本地 WebRTC 探测页 | [SKILL.md](../SKILL.md) |
