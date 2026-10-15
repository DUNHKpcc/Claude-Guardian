# 安装包离线验收

需求关联：ENG-01（运行时与入口）、VAL-08（审阅代码与发行包一致、来源、隐私与回归）。本项检查发行 ZIP 解压后的可用性，不安装到用户 Skill 目录，也不关闭真实设备验收项。

## 可重复运行

在仓库根目录运行：

```sh
python -m unittest discover -s tests -p test_installed_skill.py -v
```

测试调用真实 `tools/package_skill.py`，先在专用临时目录复制公开 Skill 和打包工具，加入合成私有文件哨兵，再构建 ZIP。解压目录和工作目录都在仓库之外，路径包含空格。构建用临时 checkout 随即删除，确保脚本不能依赖它。测试结束仅清理自己创建的临时目录。

子进程使用当前 Python，禁用继承的 Python 环境配置、用户 site 和 site-packages，并禁止产生字节码缓存。这样，仓库脚本路径或机器上已经安装的 PyYAML 不能掩盖发行包缺依赖的问题。没有 pip、运行时下载、用户目录安装或浏览器操作。

## 覆盖范围

| 检查 | 具体证据 | 不代表什么 |
| --- | --- | --- |
| CLI 可启动 | `guardian`、`interview_cli`、`inventory_cli`、`status_dashboard`、`diagnostic_session`、`recovery_cli`、`serve_webrtc` 的 `--help` | 未启动元数据采集、恢复事务或 WebRTC 服务 |
| 能力与默认门禁 | 解压后执行 `capabilities`、`workflow-status`，断言修改不可用且门禁关闭 | 不验证真实目标身份、权限或网络 |
| 离线访谈 | 合成首问、答案文件、明确保存、续接；确认没有执行动作 | 不代替真实 Codex UI 验收 |
| 离线报告与面板 | 合成空事实输入经 `analyze`、`plan`、HTML 输出；断言未知、无变更且计划不可执行 | 不运行本机查询、DNS、HTTP、STUN 或浏览器探测 |
| 完整依赖 | 已声明入口/独立库存在，AST 检查同目录模块依赖；逐一从解压目录导入 | 不认证可选宿主集成或第三方产品版本 |
| 导入边界 | 禁止导入时 socket、子进程、动态原生库加载、文件写入和非代码文件读取；拦截部分身份查询函数 | Python 导入机制自身的代码读取、路径解析仍允许；这不是全系统沙箱证明 |
| 可选 YAML 缺失 | 禁用 site-packages 后 `yaml is None`，解析以 `RUNTIME_OR_PARSER_UNAVAILABLE` 停止，禁止自动启动安装进程 | 不验证安装了 PyYAML 后的所有语义，相关单元测试另行负责 |
| 离线资料与资产 | `SKILL.md` 与来源索引中的本地 Markdown 链接存在且不越出安装根；WebRTC 资产路径有效；来源 manifest 哈希一致 | 不验证历史来源中的外部网页、事实时效或第三方许可完整性 |
| 分发隐私边界 | 合成 `.env`、报告、脚本旁文件、reference 私有笔记、raw 来源哨兵均未进入 ZIP；无缓存且带 LICENSE | 只证明显式清单排除未列入文件，不是对所有来源内容的自动隐私审计 |
| Python 基线 | 发行脚本以 Python 3.10 语法版本解析 | 语法通过不证明 Python 3.10 标准库行为或实际运行通过 |

测试不要求把未来尚未交付的任意脚本都装进 ZIP。已声明的 CLI/库及其同目录依赖必须包含；新交付入口或独立库应同步更新验收列表和打包清单。

## 本次证据与限制

2026-10-15：Linux、Python 3.12.14，9 项通过。执行环境未提供 Python 3.10，未安装补齐；Python 3.10 运行验证为 `not_run`。此记录不冒充 macOS 或 Windows 原生结果；其他平台须在对应 CI/目标环境运行并独立记录。

README 声明 Python 3.10+。检查未发现本次发行脚本明显依赖 Python 3.11+ 专用语法或 API；`str.removesuffix` 与打包器的 `Path.is_relative_to` 均在该下限之前已提供。静态检查不能穷举运行时分支，最低版本仍需独立执行证据。PyYAML 是可选运行时依赖，`requirements-dev.txt` 的固定版本用于已有测试覆盖，不代表默认安装或发行包内置依赖。

## 交付与回滚

本增量只有 `tests/test_installed_skill.py` 和本说明，不改变运行时、用户配置或发行包清单。可独立撤回这两个文件；不要因此撤掉原有源码哈希、重现打包或平台测试。完整推送验收仍按 AGENTS.md 执行，单独通过本套件不能替代全套测试和三平台 CI。
