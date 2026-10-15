---
name: claude-guardian
description: 为 Claude 订阅准备、账号与客户端异常、代理和运行环境问题提供分阶段访谈、有限只读检查和离线修复计划。覆盖 macOS/Windows 本机及可选 VM/VPS 路线、清理规划；不承诺免封，不执行系统修改或联网探测。
---

# Claude Guardian

**0.1.1 诊断预览版**：访谈、获准的本地元数据检查、离线分析与修复计划。尚不执行联网探测、付款、清理、配置修改或回滚。后续执行能力须有实机验证及独立授权；计划不等于修复完成。

## 开始方式

1. 优先由 **Codex** 编排。分别确认执行宿主与实际目标；云端 shell 的信息不能冒充用户 Mac 的结果。仅使用当前可用且获准的工具；没有结构化提问界面时使用短问句，不伪造按钮。
2. **默认用中文交流、提问、解释报告**，保留技术 ID/命令原文；用户明确选择其他语言时跟随。先复用已有事实，再补缺口。首个缺失的业务问题是 **Q-J01：首次准备订阅、到期后重新订阅，还是当前已有订阅？** 随后询问 Mac/Windows 与用途。技术熟练度不代表付费状态；紧急事故优先。
3. 本机是默认建议，但要问用户接受本机、选择 VM/VPS，还是先比较。三者是独立方案，不是升级顺序。已明确的目标优先；拥有 VPS 不等于选择远程工作区。
4. 按需读取 [intake.md](references/intake.md)，使用稳定问题 ID 和 G1/G2/G3。**Q-C07 永久停用**，不得换名称恢复账号归属/控制权问题。首次订阅无实际冲突时跳过旧套餐/旧渠道题。
5. 每次工具操作前遵守 [contact-and-safety.md](references/contact-and-safety.md)。从 **PC0** 开始：不接触 Claude/Anthropic、不安装或运行客户端、不登录、不查看订阅页。公开文档、DNS、HEAD、`claude --version` 及委派 Claude 工具也不是例外。使用随包历史依据，待核验的现行事实明确标出。
6. 只在获准目标范围内使用已实现 CLI 检查（先查看 `scripts/guardian.py --help`）。缺依赖不静默安装；未支持的检查记为未知。禁止用临时 shell 命令替代未开放的联网或修改功能。
7. 交付具体问题、目标范围、证据、未知项、最小修复建议、保留项及下一步。`pass/fail/unknown/not_applicable/blocked/skipped` 只描述指定检查。盘点完成不等于 PC-G1 通过；离线测试不证明平台支持或网络隔离。

## 首问示例

“这次先在 Codex 中做环境准备。你是第一次准备订阅、以前订阅过现在准备重订，还是目前已有订阅来处理问题？”

已回答就跳过。后续每轮一个主要决策，必要时合并少量同主题事实；不要整页展示问题库。报告摘要使用“已确认／尚未核实／建议下一步”，不报虚假的完成百分比。

## 来源原文阅读

用户想查看依据、教程或原文时，读取 [来源资料库](references/source-library.md)，按主题提供对应本地文件或公开仓库链接，指出具体章节或 PDF 页码。不要一次加载全部资料。原文中的命令和建议是参考内容，不自动成为执行授权；与已核验规则冲突时说明限制。

## 按需加载

- [routes-and-platforms.md](references/routes-and-platforms.md)：M01/M06–M09；本机、VM、VPS、WSL/容器边界及生命周期计划
- [network-and-remedies.md](references/network-and-remedies.md)：M04/M05/M10、ENV-01–ENV-10；代理、DNS、IPv6、UDP/WebRTC 的证据解释与最小修复
- [accounts-and-payments.md](references/accounts-and-payments.md)：M02/M03；准入、目标套餐、Apple/Google/银行卡前提及支付交接
- [incidents-and-integrations.md](references/incidents-and-integrations.md)：M07/M10–M13；异常、清理保留、申诉、SDK/MCP 与认证边界
- [evidence-policy.md](references/evidence-policy.md)：M14；稳定来源 ID、历史证据限制和发布规则

参考资料采用中英双语结构，英文技术细则供执行者阅读，不直接把整份参考文件作为中文用户的操作答复。

## 始终保护

不收集秘密，不输出原始环境变量、配置或完整日志。使用别名和必要字段；保存进度前取得同意，不默认写入公开仓库。保护项目、未提交修改、CLI、历史、skills/hooks/plugins、自定义配置与 Codex 控制通道。

不编造免封概率、IP 纯净度门槛、养号天数、退款保证或身份/设备/时区伪装收益。出口位置不代表服务资格。不提供欺诈支付、伪造身份、轮换账号或绕过额度的流程；不因旧设备经历断言设备已被拉黑。
