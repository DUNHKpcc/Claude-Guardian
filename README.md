# Claude-Guardian

面向 Codex 的 Claude 使用准备与环境诊断 Skill。许可证：**GPL-3.0-only**。

## 当前版本：0.2.0 工作流基础（尚非全设计完成）

首版提供分阶段访谈、明确授权后的限定范围本机元数据采集、离线事实分析与修复计划。它不承诺免封；检查通过也不代表平台认可网络环境。

- 首问订阅阶段，再按需了解系统、用途、目标套餐、账号经历和路线
- 本机默认建议；VM 与 VPS 是独立可选方案
- 本机主线 macOS / Windows；云端 Linux 不能替用户电脑出具检查结论
- 接触前 PC0 门禁关闭，不启动 Claude、登录或访问其服务
- 预览版没有联网探测、配置写入、清理、付款或自动回滚执行器
- 原生平台实测尚未完成；Python 核心测试与合成夹具不能替代真实设备验证

## 安装与使用

将仓库的 `skills/claude-guardian` 文件夹复制到你使用的 Codex Skill 目录，保留文件结构；根目录 LICENSE 应随发行包分发。Skill 文本可独立阅读，调用脚本需要 **Python 3.10+**。项目不会自行安装 Python、代理工具或后台服务。

在支持 Skills 的 Codex 会话中调用 `$claude-guardian`，例如：“帮我准备第一次订阅 Claude，先检查我的 Mac 环境”。代理应先复用你已经说明的信息，再分轮提问，并只执行你授权范围内的检查。

底层接口：

```sh
python3 skills/claude-guardian/scripts/guardian.py --help
python3 skills/claude-guardian/scripts/guardian.py interview
```

`check` 的目标绑定参数必须来自实际宿主能力与用户确认，不能为了通过检查而填写不存在的授权。`analyze` / `plan` 处理本地结构化事实；具体契约及示例见脚本帮助、`tests/fixtures/`。默认输出到标准输出，只有明确指定 `--output` 才保存报告。

## 开发与迭代

```sh
python3 -m unittest discover -s tests -v
python3 tools/package_skill.py --output /tmp/claude-guardian-0.2.0.zip
```

目录：

- `skills/claude-guardian/SKILL.md`：Skill 入口
- `skills/claude-guardian/references/`：按需加载的访谈、路线与证据说明
- `skills/claude-guardian/scripts/`：离线核心与只读采集入口
- `tests/`：行为回归与合成样例
- `docs/requirements.md`：设计覆盖及未实现项
- `docs/decisions.md`：关键取舍、确认状态和后续条件
- `docs/source-manifest.json`：输入设计版本及哈希

设计基线是主规范 v0.2.00 和环境脚本规范 v0.3。新版本分别记录设计、代码实现、夹具验证与原生实测状态，避免把“有文档”写成“已可用”。历史规格引用的机器契约 ZIP 没有随本次提供，当前契约按正文重新实现，不继承历史测试结论。

## 发布与隐私

测试与发行包只使用合成数据。用户画像、原始代理配置、订阅地址、账号、凭据、真实 IP 和个人报告不得提交仓库。用户已确认所提供资料由其制作并允许公开分发。来源资料随包提供，保留署名和原有许可声明；清理教程中的个人机器记录已去除。参阅 [来源资料库](skills/claude-guardian/references/source-library.md)。来源原文与经过核验的执行建议分别使用，不把阅读命令当作执行授权。

后续迭代：补充真实 Mac/Windows 只读采集覆盖；确认中性探测端点与隐私边界；按操作完成平台实测后，再开放可审查差异、备份、受控修改和冲突安全恢复。

## 自动检查覆盖

每个 push / PR 在 Linux、macOS、Windows CI 上运行单测、回归和确定性打包检查。Mac/Windows CI 另外运行只读 OS 元数据 smoke；该 smoke 不证明真实用户桌面、Clash、浏览器或故障恢复验收通过。原生采集扩展到产品/构建版本、语言偏好、时区和代理/PAC 启用状态，不读取代理凭据或订阅内容。

## 新增工作流基础

- `scripts/interview_cli.py`：完整95-ID访谈调度、条件分支、单题输出与明确保存/续接；推荐作为完整访谈入口
- `scripts/network_probes.py`：带端点与路径授权契约的有限 HTTPS 出口探测；当前不由主CLI自动调用
- `scripts/serve_webrtc.py`：限时、仅127.0.0.1的固定页面服务，不暴露目录或自动联网；打印本地URL后由用户自行打开
- `assets/webrtc-probe.html`：本地浏览器页，仅在用户确认和点击后尝试单次STUN；无媒体权限请求
- `scripts/transactions.py`：POSIX临时/测试文件事务基础，精确计划哈希、私有备份、核验和冲突拒绝回滚；不是已验收的系统/Clash适配器，Windows尚未实现

访谈示例：

```sh
python skills/claude-guardian/scripts/interview_cli.py --target-ref laptop-a --account-ref account-a
```

输出下一题和阶段评估，不默认保存。用户明确要求保存时提供 `--output`，后续通过 `--input` 续接。问题回答使用本地JSON文件（question_id、value、state、source），不要通过命令行传入凭据。

源码里的可调用底层API不代表Agent可以绕过授权。尚未开放的完整Clash配置、浏览器策略、系统设置、深度清理、真实路径与故障注入能力继续在验收台账保留，不声称完成。
