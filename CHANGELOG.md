# 版本记录

## 养号规则只写在 A0（2026-10-27）

- 所有者确认：SKILL.md 不再逐条罗列养号规则，那一句只留入口，指向 `account-onboarding.md`；规则只在 A0 写一份，以后加规则不改 SKILL.md。上一条为压字节改短的新手组合一句恢复原措辞（“直接放弃重来”等）。原先检查 SKILL.md 含接码、老 Gmail、并发字样的断言改为由 A0 的守门测试覆盖，新增测试确认 SKILL.md 不再重复这些规则。回滚：回退本提交

## 新号并发 1 到 3、不用 workflow 模式（2026-10-27）

- 所有者提供：A0 第 4 条“不要把额度顶满”限定为新号；新增第 10 条：新号并发尽量控制在 1 到 3 之间，不多用也不少用；并发不按 session 算，子代理也算并发；新号不要使用 workflow 模式；Agent 要把并发讲清楚。SKILL.md、VPS 养号步骤、README 同步；SKILL.md 有 32000 字节上限，同段和新手组合一句压短了措辞（意思不变）。新增守门测试。回滚：回退本提交

## README 合作伙伴位（2026-10-26）

- 所有者要求：README 中英文版在“它能干什么”/“What it does”上方新增英文 Partners 栏，首个是 DPCC API（`docs/partners/dpcc-api.svg`，文字已转路径，点击跳转 https://api.dpccgaming.xyz）。回滚：回退本提交

## WebRTC：Chrome 插件与系统 TUN 严格路由（2026-10-26）

- 所有者要求：浏览器这边可以在 Chrome 装 WebRTC 禁用插件；系统这边写明只开系统代理时，非浏览器应用的 WebRTC/UDP 不受保护，必须开 TUN 严格路由。`agent-remediation.md` 新增“WebRTC：浏览器和系统分开堵”一节：Google 出品的 WebRTC Network Limiter（要在选项里勾上默认不勾的“Disable non-proxied UDP”）或 `WebRtcIPHandling` 策略二选一；系统层开 TUN 严格路由，用 `network_check.py run` 的 UDP、路由两项复测。修复表、`network-and-remedies.md`、浏览器环境验收、本机防火墙验证步骤指向这一节；装插件、写浏览器策略列入 B 档。新增守门测试
- 已知限制：插件选项名按商店页描述写，没有在真机 Chrome 上装过验证；插件只管装了它的那个配置文件。回滚：回退本提交

## 非法工具清理（2026-10-26）

- 所有者要求：清理时查出用户给 Claude 装的破限、反代分发等非法 MCP、插件、skills、hooks、环境变量和后台服务，也清理掉。新增 `references/illegal-tools-cleanup.md`（审计只列名字和键名、不打印令牌；C 档逐项确认；备份后只删那一项，目录移到隔离区；涉及令牌的按凭据泄露处理），随包发布、上 Wiki“清理”分组
- 冲突处理：Windows、Linux、macOS 清理和 SKILL.md 里 `~/.claude` 设置、skills、插件“始终保护”保留，各加一句指向非法工具这个例外；SKILL.md 清理库一段压短以留出篇幅。新增守门测试（含审计脚本不输出密钥值）；Windows CI 抓到审计脚本在默认控制台编码下输出中文报错，脚本开头改为 UTF-8 输出。回滚：回退本提交

## 封号申诉模块（2026-10-26）

- 所有者提供：申诉回复在 2 到 7 天左右，超过基本凉了；解封号权重高，但盲目跳脸还是死；英文申诉模板。新增 `references/ban-appeal.md`（随包发布、上 Wiki“入门”分组），文末写“祝大家都能顺利解封”
- 冲突处理：M12 的 K4 原写“不编造回复时限”“不写异常请求不是我”，改为封号申诉以 `ban-appeal.md` 为准；SKILL.md 封号那一行、README 同步。新增守门测试。回滚：回退本提交

## CI：只改文档时只跑 Linux（2026-10-26）

- **ADR-051：**新增 `tools/ci_scope.py` 和 `tests.yml` 的 `scope` job：只改 `.md`、`.pdf`、`.png` 的推送只跑 Linux，其他改动或读不到改动范围时照旧三平台加 Python 3.10；AGENTS.md、CLAUDE.md 同步。新增 `tests/test_ci_scope.py`。回滚：回退本提交

## 接码只用实体卡（2026-10-26）

- 所有者提供：接码不找共享号码、虚拟号码；遇到接码有条件用实体卡，没条件直接弃号。写入 `account-onboarding.md` A0 第 9 条；第 6 条原先“注册时要手机号验证的号可以直接放弃”与此冲突，改为按第 9 条处理（KYC 部分不变）；SKILL.md 同步；`mobile-guidance.md` 按所有者要求保持原样（曾加的一句已撤回）。新增守门测试。回滚：回退本提交

## 账号注册时间与老 Gmail（2026-10-26）

- 所有者提供：Claude 账号注册越早权重越高，新号容易风控；老 Gmail 是否更稳目前没有定论。写入 `account-onboarding.md` A0 第 8 条；S03 原文“gmail老号最好”不当作结论（原文与哈希不变）；A0 第 6 条和 A3 的弃号重注册补上新号严格养号；SKILL.md 同步。新增守门测试。回滚：回退本提交

## 浏览器环境验收网址；买来的教育邮箱是例外（2026-10-26）

- 所有者指定 https://ip.net.coffee/claude/ 为环境修复后的浏览器环境验收网址，除时区和语言外必须全绿：`whole-machine-ipv4.md` 新增 5a 节，SKILL.md、VM、VPS、本机防火墙、手机端的验证步骤都指向它；页面会测 claude.ai 可用性，由用户本人打开；痕迹清理的查 IP 匹配规则加入该站
- `account-onboarding.md`：买来的教育邮箱不算成品邮箱；教育邮箱可以免费注册
- 新增守门测试。回滚：回退本提交

## 不碰代充、低质量 KYC 代过、成品号与成品邮箱（2026-10-25）

- 所有者要求：支付模块 `accounts-and-payments.md` B1 写明不碰代充；KYC 所在的 A3 写明不碰低质量的 KYC 代过；邮箱注册模块 `account-onboarding.md` A0 第 2 条写明不碰成品号、成品邮箱；新增守门测试。回滚：回退本提交

## KYC 与 IP 一致性（2026-10-25）

- 所有者提供：KYC 会检查 IP，IP 与支付、使用环境不一致会增大风险；Pro 后期遇到 KYC 直接弃号。写入 `accounts-and-payments.md` A3 和 `account-onboarding.md` A0 第 6 条（做 KYC 前先用 `network_check.py` 确认出口和平时一致）；新增守门测试。回滚：回退本提交

## 第二批清理：旧策略、门禁空壳、探测入口版本（2026-10-25）

- **ADR-050：**报告里的 `traffic_policy` 改为现行整机只走 IPv4 策略（0.2），删除没人调的旧条件规划器；删除 `workflow_guard.py`、`windows_transactions.py` 和 `inventory_cli` 的 `workflow-status`、`controller-audit` 子命令；环境入口删除 0.2 版本、`probe_context` 和两个没人用的门
- 选择器的 `ipv4-only-policy` 改为整机关 IPv6 的调查动作
- 测试 1459 项全部通过。回滚：回退本提交

## 删除最初的设计规格、验收台账和不用的开发文档（2026-10-25）

- **ADR-049：**删除两份最初设计规格（约 400KB，原先随包发给用户）、验收与进度台账、历史输入清单、7 份没人引用的开发说明和 1 份重复文档
- manifest、references、SKILL.md、README、AGENTS.md、CLAUDE.md 去掉对它们的引用；面板卡片不再显示规格章节号
- 发行包少了两份大文件；测试 1620 项全部通过。回滚：回退本提交

## IPv6 统一为只走 IPv4；所有者资料全部上 Wiki（2026-10-25）

- **IPv6：**全项目统一为“只走 IPv4，IPv6 关闭”：Windows 本机路线默认关闭物理网卡 IPv6（B 档，远程机器仍是 C 档），Mac 可选；`authorization-tiers.md`、`whole-machine-ipv4.md`、`local-firewall-prompts.md`、SKILL.md 同步；手机端改为在小火箭、FlClash 里关闭 IPv6
- **Wiki：**新增“所有者提供的资料”分组，S01、S02（AI 所有支付方式汇总）、S03（原文，附 PDF 链接）、S04、S05、S07、VPS 推荐报告（17 份 PDF 链接）全部上 Wiki，和原有 S06、S08、R02 一起共 23 页；S02 里的 Q 群号在 Wiki 上改为指向首页交流渠道（ADR-032），S02 一处加粗笔误和 S04 指向上游仓库的徽章链接只在 Wiki 副本里修正，仓库原文和哈希不变
- 新增测试：所有者资料全部在 Wiki 页面清单里、Q 群号不出现在 Wiki
- 回滚：回退本提交

## 删除不干活的部分（2026-10-25）

- **ADR-048：**删除没有入口调用的 17 个脚本和 2 个工具（HTTPS、DNS 探测库，终端元数据会话与原生上下文，监听端口核对，ENV-06 规则转换链，旧访谈迁移，macOS 元数据观察），连同测试、开发文档和 CI 步骤，约 2 万行
- 面板 `--network` 直接读 `network_check.py` 报告，网络卡片显示实测结果；选择器的检测类动作改指 `network_check.py`；`stun_probe.py` 只留编解码
- `agent-remediation.md` 67KB → 11KB，开发契约移到 `host-libraries.md`；`network-and-remedies.md`、README 开发者表同步
- Windows 本机路线默认关闭网卡 IPv6（B 档）；面板策略行改为“整机只走 IPv4，IPv6 关闭”
- 发行包 102 个成员；测试 1623 项
- **已知限制：**`traffic_policy.py`、`workflow_guard.py`、`windows_transactions.py` 等和报告格式有牵连的部分留到第二批。回滚：回退本提交

## 网络基础检测（2026-10-25）

- **ADR-047：**新增 `scripts/network_check.py run`（macOS、Windows、Linux）：默认路由是否走 TUN、IPv4 出口（只显示国家和 ASN）、经本地代理端口的出口、IPv6 是否堵住、DNS 泄露（fake-ip 下也测得到，解析服务器在本国判泄露）、UDP（STUN）、`--failure-drill` 交互式故障演练；`--evidence-output` 交给 `egress_verifier.py`，判定器支持 Linux
- `whole-machine-ipv4.md` 第 4 节改为先跑这条命令；scripts-index、SKILL.md 登记；发行包 118 个成员
- **测试：**新增 12 个单测（路由解析、DNS 判定、IPv6 返回 IPv4、出口在本国、报告不含 IP、证据被判定器接受、故障演练四种结果、STUN 比对、只写新文件、只接受本机代理端口）；所有者 Omarchy 上实跑全部通过
- **已知限制：**WebRTC 仍在浏览器里测；面板尚未接入。回滚：回退本提交

## 自建梯客户端版本兼容提醒（2026-10-25）

- 所有者提供：自建梯时重点注意版本兼容性，不要出现桌面端 Clash Verge 能连上、移动端小火箭和 FlClash 连不上的情况。`egress-ip-options.md` 自建梯提示第 4 条：3x-ui 的 Xray core、协议和传输选项选所有客户端都支持的组合，建好后用用户实际要用的每个客户端各连一次、各测一次出口，只测桌面端不算建好；新增守门测试。仅文档改动。回滚：回退本提交

## 封号后的环境痕迹清理与 Linux 清理（2026-10-25）

- **ADR-046：**新增 `trace-cleanup.md`：代理客户端日志（Clash Verge Rev 三平台路径、FlClash 等定位方法，整体隔离 `logs`、配置不动、日志等级调到 warning）、VPN 客户端日志、Shell 历史只删查 IP 的命令（zsh/bash/fish/PowerShell，删前备份）、命令输出可能留存的几处、系统日志不清
- 新增 `linux-cleanup.md`：Claude Code 在 Linux（VM 客机、VPS）上的路径、分档、审计、备份、隔离与还原
- **对话记录可选移走：**`native_cleanup_mac.py` 新增 `conversation` 档（`~/.claude/projects`、`history.jsonl`），用户同意后才处理，终端确认页写明后果；Windows、Linux 指引同步；Agent 清理时单独询问并建议移走
- `~/.claude/debug` 从受保护改为可再生（Mac 模块与 Windows、Linux 指引）
- SKILL.md 资料表、README、Wiki 同步；新增守门测试和 Mac 模块的对话记录往返测试；发行包 117 个成员
- **已知限制：**手机端（Shadowrocket 等）这次不做；新增的 Linux、痕迹清理命令为常规用法，首次使用先跑只读审计核对路径。回滚：回退本提交

## Agent 说话方式：少说“不保证、不成立”（2026-10-25）

- **ADR-045：**SKILL.md 开头新增“和用户说话的方式”，说明门禁和证据口径是给 Agent 执行的规则、不念给用户；列出不要说的句式，免封只在被问到时说一次，所有者经验按事实直接说，汇报用“已确认 / 还没查 / 下一步”
- SKILL.md 其余部分去掉“不代表、不等于、不承诺、背书、不推定、不断言”等句式，改为正面说法；`account-onboarding.md` 的 A0b 开头与用法同步改写
- 面板（`status_dashboard.py`）、动作清单（`agent_remediation.py`）、探测样本（`probe_evidence.py`）的用户可见文字改为“另测”“还要另查”；判定条件与状态值不变
- **测试：**三条锁定旧措辞的断言改为新措辞（意思不变），新增两条守门测试
- **已知限制：**references 里的同类句式尚未改写，下一批处理。回滚：回退本提交

## 新手试错推荐组合（2026-10-25）

- 所有者提供：目前最适合小白试错的是苹果内购 + Gmail／Outlook 邮箱 + VPS 纯净个人 IP + 在 VM 或本机上使用 + Pro 订阅，退款成功率高、稳定率高。`account-onboarding.md` 新增 A0a 推荐组合表（每项链到对应指引），开头加新手入口；`accounts-and-payments.md` 支付推荐规则第 5 条：新手首选苹果内购；SKILL.md 首问处直接路由到 A0a
- A0 第 6 条补充：注册时弹手机号验证、之后 24 小时内又要 KYC 的号基本宣判死刑，直接放弃重来
- 新增守门测试；仅文档改动。回滚：回退本提交

## SKILL.md 瘦身：宿主库契约移到按需读取的 reference（2026-10-25）

- **ADR-044：**SKILL.md 里的宿主库与内置入口契约说明原文移到新的 `references/host-libraries.md`，SKILL.md 改为“内置脚本与宿主库”短节并登记到按需加载列表，从约 42KB 降到约 29KB；更正“尚无开放的内置写入适配器”的过时说法
- **测试与打包：**新增守门测试（契约章节只在新文件、SKILL.md 体积上限、关键契约词仍在）；发行包 115 个成员，打包成员数测试同步
- **已知限制：**规则文字未改，只换位置；Agent 实际耗时是否改善待使用者反馈。回滚：回退本提交

## README 去防御化与 Windows 防火墙分层诊断（2026-10-25）

- **README（ADR-043）：**中英文 README 把散在各处的限制收成一节“几条底线”，删去“它不是什么”“核心场景”“工作流与门禁机制”“开始前要知道”及示例、Star History 的免责句，路线表改写成“适合谁、主要内容”；门禁与授权规则不变，细节仍在 Skill 和 references
- **Issue #13：**`local-firewall-prompts.md` Windows 一节补回环接口替代 `::1`、`InterfaceAlias` 读回、核心路径核对，新增分层诊断、WFP 丢包记录查询、宿主拒绝时的收尾交接和最小反馈清单；重新生成章节索引
- **测试：**新增 Issue #13 指引守门测试（含分层顺序）和 README 不回退到防御性写法的测试
- **过度防御检查：**`whole-machine-ipv4.md` 不再写“没在真实设备上跑过”，改写 ADR-039 的 Mac 真机结果和尚缺项；防火墙页按 Issue #13 写明第 1 到 4 步在 Windows 上跑过，删去重复的免责句；SKILL.md 的 description 和版本说明改为直接说能做什么；新增对应回归测试
- **已知限制：**仅文档改动，新增的 Windows 命令未在真机重跑；Issue #13 的根因仍未知。回滚：回退本提交

## 进阶路线：远端 Linux 机器的出口钉死与反向隧道（2026-10-24）

来源：所有者在 Omarchy 里的“FlClash + nftables killswitch + VPS 反向隧道”部署经验（本机管理端 + 本地 VM + 远端他人网络里的 Omarchy + 兼任出口和中转的 VPS）。经验原文和含真实地址、私钥的脚本留在所有者的 Omarchy，不进仓库，仓库只收脱敏后的做法。

- **进阶路线（指引层，ADR-042）：**新增 `references/advanced-route.md`（架构、搭建顺序与档位、隧道专属的坑、崩溃自愈、验收与覆盖矩阵、盲区、运维手册、通用教训）和 `routes-and-platforms.md` 的 R-ADV 卡 A1 到 A4。它叠加在 VM／VPS 路线之上，不新增路线值，目标机仍按 vm_guest／vps 绑定，不动环境入口门禁。访谈新增 Q-V09（目标机能直连还是需要反向隧道），选 `remote_unreachable` 且为 Linux 客机时 `required_references` 附进阶路线文档和两个脚本，排在 killswitch 之前
- **新增脱敏脚本（`assets/remote-hardening/`）：**`install-reverse-tunnel.sh`（systemd 常驻反向 SSH 隧道；所有者原脚本把私钥内嵌，这里改为用户传入 `KEY_PATH`，脚本不生成、不内嵌、不输出密钥，并 `chown`、`chmod 600`）、`flclash-crash-heal.sh`（FlClash 崩溃后清策略路由残留 + core 看门狗，`install` 生成 timer 和隧道 drop-in，`KillMode=process`、服务级桌面环境变量）
- **共用的修复与完善（VM、VPS 路线同样受益）：**`install-flclash-killswitch.sh` 新增可选 `TUNNEL_UNIT`，从隧道 unit 解析 `user@IP`、`-p` 端口加入独立白名单，管理通道不再被自己的 killswitch 锁死（解析失败打印 WARN）；`install-flclash-tun.sh` 在非 0.9.1 版本自动加 helper 的 systemd drop-in（`FLCLASH_HELPER_OWNER_UID/GID`、`RuntimeDirectory=flclash`）；`vm-guidance.md` 补 GLOBAL 组含 DIRECT 的出口验证、priority 10 与 fake-ip 的坑、崩溃后路由黑洞、IPv6 实测（`inet` 家族 policy drop 已覆盖，换环境后用 `curl -6` 复测）、时区对齐出口地理位置与 NTP 被拦；`vps-guidance.md` 补作隧道中转时 sshd 保活和 `authorized_keys` 无引号写法（带字面引号会让 OpenSSH 8.9 静默拒绝转发）
- **测试与打包：**新增守门测试（进阶路线卡、脚本无个人信息和私钥、共用修复落在 VM／VPS 指引）和 Q-V09 引用顺序测试；`acceptance-routes-rebuild.json` 的 VM 答案补 Q-V09；发行包 114 个成员（含 1 份文档和 2 个脚本）
- **已知限制：**脚本的参数化与脱敏部分只做了 `bash -n` 和 killswitch 规则生成的离线检查（含与不含隧道 unit 两种），没有在真机整体重跑；`nft -c` 语法检查需要 root，本次未做。逻辑来自所有者在真机跑通的脚本。回滚：回退本提交即可，Q-V09 为新增问题，旧状态在该问题未答前评估为未完成

## 注册即要手机号或 KYC 的号（2026-10-24）

- `account-onboarding.md` A0 第 6 条补充：注册时就提示手机号或 KYC 的号直接放弃，存活率不高，修好环境和邮箱后重新注册；已使用中才弹出的 KYC 仍按 A3 本人完成。仅文档改动

## Apple 内购续费入口提醒（2026-10-23）

- `accounts-and-payments.md` B2 第 10 条补充：Apple 渠道续费必须先打开 Claude App，在 App 内订阅页付费，不要从 App Store 订阅管理页续费（所有者提供的实例：扣款后会员未到账，Apple 与 Claude 互相推诿）；仅文档改动

## 减少停顿与重复读取（2026-10-23）

- 有用户反馈 Skill 执行很久、要反复输入“继续”。`SKILL.md` 的“少打扰用户”新增两条：A 档工作在一轮里连续做完，只在缺必需信息、C 档确认点、需用户本人动手时停下；按需读取 reference 章节，不整篇重读。仅规则文字调整，门禁与授权不变；实际耗时改善待使用者反馈确认

## 注册方式补充（2026-10-23）

- `account-onboarding.md` A0 第 1 条补充：Google 授权登录与 Gmail 邮箱登录在 Claude 这边是两个不同的账号，订阅和历史不互通；注册时选定一种并记下，登录后若是空账号先核对登录方式，不重复注册。仅文档改动，无代码变化

## 路线补全、访谈兜底与资料引用（2026-10-21）

- **验证口径更正（2026-10-22，ADR-041）：**README、SKILL.md、Issue 表单和 wiki 首页的说法改为所有者的口径：作者在 Mac、Windows、VM、VPS 上都验证过，但每个人的环境不一样，需要按实际调整；不再写“作者没有验证”。仓库内的具体验收结论仍只有 Mac（ADR-039）
- **真机验收交给使用者（2026-10-22，ADR-040）：**作者不再逐项做真机验收，只保留一台 Mac 上的样本结果（ADR-039）；新增 Issue 表单“真机使用反馈”（`.github/ISSUE_TEMPLATE/device-report.yml`），收集使用者在自己环境里的结果；README 写明这一点。门禁、诚实标注和 Agent 按环境调整的规则不变
- **Wiki 已发布（2026-10-22）：**12 篇教程加首页和侧边栏已推送到 GitHub Wiki（https://github.com/DUNHKpcc/Claude-Guardian/wiki），导出时把 `**加粗**` 转成 `<strong>`，避免 GitHub 在中文标点后不识别加粗而显示星号；README 文档导航加了入口
- **Mac 真机验收收官与修正（2026-10-22，ADR-039）：**所有者完成 Mac 线验收：4.2b 真实写入、重启后规则在场、`recovery_cli` 回滚回基线哈希全闭环；4.4 判定 `established`（8 层全 pass）；时区真实切换与恢复通过。据此修正：写入者排除只认 Clash Verge 应用本身（后台的核心和 root 服务不算，原先逼用户 `sudo launchctl bootout` 还会断 TUN）；时区验证对 `/etc/localtime` 的异步更新做有限轮询（原先误报 `TIMEZONE_VERIFY_FAILED`）；`ACTIVE_HOST` 提示补上残留后台进程的排查办法；整机出口文档补三点真机发现（IPv6 探测返回 IPv4 字符串的记法、界面设置何时覆盖合并文件、严格路由默认可能关着）
- **GitHub Wiki 教程导出（2026-10-22，ADR-038）：**新增 `tools/export_wiki.py`，把 12 篇面向用户的教程（账号注册与养号、手机端、出口 IP、整机出口、本机 Clash 与防火墙、VM、VPS、线路优化、macOS 与 Windows 清理、所有者提供的 S08 和 R02）从仓库渲染成 wiki 页面，附首页、侧边栏、频道信息和“自动生成，请到仓库修改”的横幅；链接改写为 wiki 页面或仓库链接，发现个人信息或凭据样式的内容就拒绝导出。仓库仍是唯一来源，Agent 读取的 `references/` 没有移动
- **少打扰用户（2026-10-22，ADR-037）：**`SKILL.md` 新增“少打扰用户”八条（能读到的不问、访谈只问当前任务要的并合并提问、同一范围只确认一次、不重复检查、不循环重试、被拦时说人话、小事不升级、汇报要短）；macOS C5 宿主一整轮的终端确认从 7 次减到 4 次（备份、计划、隔离、还原；读取与保存计划合并为一次，对账只读不再问）；被拒绝时输出一句话 `hint`（如请先退出 Claude、请在普通终端运行）。安全门禁不变
- **验收定位调整（2026-10-22，ADR-036）：**真机验证只是样本，不再把“全机型真机验收”当完成标准。`SKILL.md` 新增“每台机器环境不同”：Agent 先核对实际环境，差异在已批准计划内就调整参数，超出就重新出变更卡，失败停下回滚并如实报告，不放松门禁，不把一台机器的结果说成通用；README 和 AGENTS.md 同步
- **Mac 真机验收（2026-10-22，ADR-035）：**F2 修复后在一台 Mac（MacBookPro18,1，macOS 15.7.4，Clash Verge Rev 2.5.8）实测：4.2b 的版本、归属、进程名、`plan` 计划（两次独立运行摘要一致）、应用运行时 `execute` 拒绝且目标文件哈希不变；4.4 判定器五条路径；4.5 的 Claude 运行时、由 Claude 启动、无终端短语、非终端管道全部正确拒绝；4.6 钥匙串服务名与 `ACTIVE_HOST`、非法时区。**未验：**真实写入与回滚、C5 放行全流程、真实钥匙串删除、`simple`、真实时区变更、TUN/LuLu、整机出口的 GUI 联网取证。详见 ADR-035
- **章节级可发现性（2026-10-22，ADR-034）：**新增 `references/section-index.md`，由 `tools/gen_section_index.py` 生成，列出每份 reference 的每个二、三级小节和锚点；守门测试检查它与生成结果一致、每个小节都有链接、访谈能发出的每个 `#锚点` 定位符都能解析（顺手发现并修复 `#a0b` 锚点不存在）。访谈 `required_references` 新增 `routes-and-platforms.md`（按路线定位到对应操作卡）和 `network-and-remedies.md`（任务为 network 或 environment 时）。发行包 111 个成员
- **资料可发现性复查（2026-10-22，ADR-033）：**起因是 A0b 短期封号时间线和 KYC 指引只躺在 `account-onboarding.md` 里，Agent 不一定翻得到。修复：`SKILL.md` 资料表新增“账号被封或被限、KYC 触发或身份核验”必附行（A0b、S03 第 5 页、A3、S04 §2.3、M12）；访谈 `required_references` 新增封号与身份核验、整机出口、macOS 与 Windows 清理的必附资料，且同一文件的多个页码会合并；新增 `references/scripts-index.md`（每个脚本和资产的用途与入口）；`SKILL.md` 补直接指向 S03/S08 文字版、manifest、设计规格、cleanup-cli-usage。新增 `tests/test_skill_discoverability.py`：任何 references、sources、assets、scripts 文件从 `SKILL.md` 出发翻不到、脚本索引与 `scripts/` 不一致、相对链接或锚点失效，测试都失败。发行包 110 个成员
- **Issue #12（2026-10-22，ADR-032）：**补充资料来源新增 IDC Flare 和 VPSHub，按 S03 第 5 页写明家宽、家宽拼车、VPS 的查找渠道和所有者列的帖子；skill 可直接当帖子与论坛搜索工具；短期封号时间线（S03 第 5 页图片表）写进 `account-onboarding.md` A0b
- **Mac 真机验收修复（2026-10-22，ADR-031）：**macOS 15 内核自动给文件加不可移除的 `com.apple.provenance`，使修复链和 C5 清理链在真机上必然被元数据门禁拒绝；`transactions._has_xattrs` 现在只容忍这一个属性（其他仍拒绝，不读取属性值，固定 21 字节缓冲），所有门禁共用该函数。清理 CLI 用法补上验收中发现的勘误
- **参考 claude-cleanup 收紧 C5、补 Windows（2026-10-22，ADR-030）：**`~/.claude` 整个目录不能当根，对话记录、历史、设置、skills、插件、凭据始终受保护；根分“可再生缓存/日志”和“桌面端持久数据”两档；补桌面端路径；由 Claude Code 或 Claude 应用启动时拒绝；新增 `native_claude_state_mac.py`（钥匙串退出登录、`CLAUDE_CODE_SIMPLE`、用户指定时区，均终端确认）；新增 `references/windows-cleanup.md`（官方路径，PowerShell 分步，无内置宿主）。**不采用**第三方的 userID/machineID 轮换。发行包 109 个成员，未真机验收
- **C5 清理宿主（2026-10-22，ADR-029）：**新增 macOS 内置宿主 `native_cleanup_mac.py`，实现 `verify`（固定清单、Claude 已退出、内容校验的备份）、`approve`（用户在真实终端输入 `CONFIRM <操作> <摘要前8位>`）、`exclusive`（进入和退出时检测 Claude 进程）、`cancelled`；命令 `context`、`allowed`、`backup`、`plan`、`quarantine`、`reconcile`、`restore`。拒绝 `~/.claude.json` 和含 `.credentials.json` 的目录，永久删除、钥匙串、浏览器数据不在范围内。只有合成与 CI 测试，未真机验收；发行包 107 个成员
- **整机统一出口（2026-10-22，ADR-028）：**新增 `references/whole-machine-ipv4.md`（Clash Verge 的 TUN、DNS、`ipv6: false`、规则兜底配置，按分级授权的步骤，Mac 与 Windows 取证命令）和只读判定 `scripts/egress_verifier.py`：根据 Agent 提供的观察判定 8 个必要层，输出 `established / violated / incomplete`，不回显 IP；持续保护须重启、睡眠唤醒、换网都复验才算有证据。Windows 不做写入引擎，由 Agent 按提示词操作并备份读回。未真机验收
- **Mac 配置写入适配器（2026-10-22，ADR-027）：**新增 `native_clash_verge_mac.py`，`repair_execution` 的原生门禁对 macOS 上 Clash Verge Rev 2.5.8 的 `rules-prepend` 放行；要求应用及其核心已退出，提交前后复查进程与元数据文件，检测到变化失败并保留恢复批次。其他系统、产品、版本和 `merge-policy` 仍不可用。只有合成与 CI 测试，未真机验收；发行包 104 个成员
- **部署口径更正（2026-10-22）：**VM 和 VPS 文档原写“不代部署／不代装／不代配置”，与所有者意图不符。改为：用户买好服务器并给出访问方式后，Agent 可通过宿主 shell／SSH 按分级授权执行文档里的命令和脚本来部署；买服务器、付款、注册、登录仍由用户本人完成。Skill 没有内置自动部署程序，脚本未真机实测
- **VM 路线：**客机系统首选 Omarchy（Mac 宿主首选 macOS），创建前网卡选 LAN 独立网卡而不是 shared NAT；新增搭建顺序和三个脱敏脚本（开客机 SSH、安装 FlClash TUN、fail-closed 防火墙，Agent 可通过宿主 shell 或客机控制台按分级授权运行，启用 fail-closed 防火墙属 C 档），出口复用出口来源和 VPS 推荐报告
- **VPS 路线：**定位为开发机，核心是环境一致，注册、登录、养号、订阅和 OAuth 都在 VPS 的远程桌面浏览器里完成；服务器首选 Ubuntu；新增 VPS 入站防火墙脚本（规则语法经 `nft -c` 检查，未在真实服务器上实测）；自建梯中转归本机路线的出口选择
- **本机路线：**新增固定出口 IP 的来源（纯净机场、自建梯、家宽拼车）及推荐；新增手机端防封要点和账号注册与使用节奏
- **分级授权：**用户不需要每一步在场。授权按风险分三档：A 范围内自行做（只读诊断、查资料、出方案、预演），B 整个计划批准一次（可自行撤销、不切断访问、不涉及账号钱和凭据），C 必须当场确认（可能锁死、账号和钱、凭据、删除和不可逆、组织设备、接触 Claude）；到 C 档 Agent 暂停写确认单，用户可稍后回复；硬规则不变。各路线文档标注了每一步的档位；范围确认、计划批准和确认单可写进访谈状态的 `authorization` 段（来源必须是用户的明确回复，换路线或会话恢复后永久失效，存档被篡改时拒绝读取），评估结果带摘要，G3 仍为 blocked
- **本机路线防火墙：**不提供脚本，用提示词引导；Windows 用系统自带防火墙（导出备份、保险丝计划任务、先加允许规则再切默认出站、故障演练、回滚），Mac 依赖第三方 LuLu，并补 Mac 上 Clash Verge 的 TUN 和 DNS 引导；命令未在真实机器上实测
- **线路优化：**新增 Agent 辅助的逐项流程（只读诊断、变更卡、批准后执行并验证、可回滚），依据 R02
- **访谈状态机：**新增 7 个分类问题（Q-X01、Q-X02、Q-M01、Q-V07、Q-V08、Q-S08、Q-T01），只在路线被明确选择后才问；评估结果新增条件字段 `required_references`，按已答事实列出必附资料，不是授权
- **资料：**新增 S08（VPS Claude 教程）、R01（17 份 VPS 推荐报告，压缩后约 15MB）、R02（线路优化与家宽中转教程）、S03 的 Markdown 源文本；S07 精简为 IP 质量测试清单；资料随答附带规则和 Agent 补充资料来源（Linux.do、NodeSeek、V2EX、Reddit、X）
- **移除：**`docs/validation.md`（1600 多行的按日期验证记录，内容仍在 git 历史）；验收台账与证据体系（台账 JSON、`docs/evidence`、30 个验收测试及相关文档），内容仍在 git 历史；常设推送授权写入 `AGENTS.md`
- **README：**重写开头，新增“它能干什么 / 它不是什么 / 怎么工作 / 分级授权”，并用技术栈徽章标注平台、运行时、网络与代理、开发环境
- **限制：**所有新脚本和命令均未在真实机器上验收；决策记录见 `docs/decisions.md` ADR-009 至 ADR-021

## WebRTC 样本的本地 IPv4 比对

- 现有页面可选输入已知 HTTPS IPv4 样本，仅在本次采样内比较 srflx IPv4，结果只输出 same／different／unknown 与计数，不输出原始地址
- 参考值在开始时冻结，结束／取消／离开时清理输入与临时引用；不新增请求、保存、下载或 IP 哈希，不承诺安全擦除
- 保留 701、截断、IPv6 与未观察媒体路径等限制；一致仅支持已观察的 IP 样本，不证明同一路由、整机防泄漏或 IPv4-only 达标

## 固定检测页的受限顶层导航

- 仅允许精确本地固定页的单一 GET 顶层文档导航：匹配 Host、缺省或同源 Origin、明确用户激活及无请求体；拒绝重复或矛盾的导航元数据
- 跨站子资源、iframe、无用户激活及 HEAD 继续拒绝；页面安全头和页内手动同意保持不变，载入页面不自动发起 STUN

## WebRTC 首次拒绝的可选分类诊断

- 原有本地服务新增显式 `--diagnose-rejection`：每次服务最多输出首个拒绝请求的固定分类，不记录原始请求头、地址或私有值
- 保持原 Host、Origin、跨站、路径及请求体准入规则；诊断不放行请求，不启动浏览器或 STUN，不构成 WebRTC 路径验收

## 中性样本入口与受控诊断增量

- 显式 environment-entry /0.2 将受控中性 shell 样本的实际路径／当前宿主绑定与配置规划要求分开；未知最终协议不再要求伪填，配置与 Claude 接触仍保留原门槛，旧 /0.1 和保留计划不自动升级
- 可信适配器的当前上下文、路径、端点及授权在发送前有界复核；发送后变化保留真实请求次数并将证据降为 unknown，不重试，也不认证整机持续保护
- WebRTC 本地服务输出白名单阶段／错误码，保留主错误、逐资源收尾和未确认清理的 unknown；URL已输出后不能称探测未开始，页面仍须关闭
- macOS console身份为空增加受控诊断，不推断原因、不伪造会话、不降级门禁；此为诊断能力改善，原生根因仍待获准复验
- 无新增浏览器／DNS主动探测或显式代理执行器，不改变本机配置；真实身份及精确操作许可仍由可信宿主提供

## 2026-10-19 — 整机统一路径默认与明确分流例外

- 按用户新要求将网络准备／修复默认扩展到同一电脑所有普通应用、子进程和后台服务；普通应用目标腿 IPv4-only，故障不直连，用户明确指定的独立路径分别验收
- 配置前说明 TUN 等接管方式、影响、精确例外及恢复并取得具体批准；区分接管与路由模式、上游引导／本地例外、整机强制证据及IP观察范围
- 原 target-only API、报告和面板契约保持原义，不冒充整机能力；仅更新现有 Skill 指导与离线文档回归，不新增脚本、守护、真实设备操作或持续保护能力

## 2026-10-19 — 修复后出口稳定性指导

- 在现有 Agent 修复闭环增加唯一稳定性核查章节，覆盖自启、配置持久化、故障出口边界、IPv4-only、生命周期复验及 IP 漂移说明
- 区分规则声明、应用载入、目标进程采用和端到端观察；复用现有检查与回执，保留 DNS／UDP／WebRTC 证据、具体授权、独立恢复及未知能力边界
- 仅补充既有 Skill 文档及五项离线文档回归；不新增 Skill、脚本、守护进程或运行能力，不扩张真实设置／重载权限、历史验收或持续守护承诺

## 2026-10-19 — Preserve comments in the bounded Agent rules task

- Accept legal comments within the existing three-sequence extension shape while preserving original bytes and the single insertion
- Require exact original/candidate bytes when comments are present; comment removal or formatting changes require new review rather than semantic-equivalence acceptance
- Keep complete repair-plan prerequisites, native gates, permissions and actual-device evidence requirements unchanged

## 2026-10-19 — Agent-supported single-rule task

- Reuse the pinned 2.5.8 compiler and linkage checks for one dedicated rules extension and one DOMAIN change; provide private candidate material and fixed Agent steps
- Compare supplied content without claiming Save, application activation, routing, authorization or native execution; retain independent scoped recovery review
- Add the helper and focused usage reference to the explicit 67-member package; keep production transaction and cleanup admission unchanged

## 2026-10-19 — Internal Darwin private-read subset

- Add one shared descriptor-only metadata guard for private control documents and parents; distinguish absent, empty and nonempty ACLs without exposing principals or values
- Add opt-in owned temporary fixture experiments and a macOS-only CI step; synthetic results remain separate from native and user-device evidence
- Keep existing CLI, transaction/cleanup gates and the 65-member installed package unchanged; selected-receipt integration awaits applicable native validation


## 2026-10-19 — Explicit execution-route and resource entry

- Require a current local / VM / VPS choice and bounded resource declarations before target inspection or remediation; resource ownership alone never selects a route
- Recheck entry state around host callbacks and invalidate withdrawn contact grants; retain narrowly scoped recovery protections and routes
- Separate local/VM detailed eligibility from VPS basic non-intrusive scope, and distinguish local HTTP/mixed proxy entry from a SOCKS upstream
- Add the entry module to the 65-member package; preserve historical 51-case evidence with explicit current revalidation status rather than rewriting original clauses or old results
- Native metadata write support, application activation and actual device acceptance remain pending

## 2026-10-19 — Bounded read-only Darwin metadata observation

- Add inherited-fd observation with fixed categories/counts, bounded native name listing, ownership/state checks and privacy-safe errors
- Read no attribute values, file contents or ACLs; preserve caller descriptor ownership and all existing production write-admission gates
- Include one standalone script in the 64-member release; new native module validation remains pending, and original acceptance counts do not change

## 2026-10-19 — Preserve platform-specific replay coverage

- Correct the compatibility receipt for the original resume suite’s existing Windows skip: compare the complete Windows trace against its own fixed digest, while retaining the complete POSIX digest
- Verify the exact test/skip inventory, reject missing or changed trace fields, and keep historical/current full-output equality mandatory
- No runtime, installed package, original test, historical evidence or acceptance-count changes; the initial Windows CI failure remains recorded

## 2026-10-19 — Asset-route evidence and fact-value isolation

- Revalidate original T26/T33 with separately observed synthetic dialogue and normalized logic, retaining initial partial coverage and adaptive later observations
- Copy incoming fact values to prevent caller-owned mutable dictionaries/lists from silently changing recorded evidence; five regressions fail on the previous runtime and pass after the one-line correction
- Preserve all historical evidence packets; an exact-source compatibility supplement reconstructs the old runtime and independently reruns current semantic traces instead of relabeling historical records
- No native operations, deployment or real account/network actions; no change to original 218 requirements or layers


## 2026-10-19 重建第三十四批

- 按原 L+C 验收 T22 本机专家 Code 范围和 T25 原方案专项诊断；累计49/218，169项待验收
- 保留三段对话七条实际回复、完整独立审阅与九项独立的规范化逻辑回归；实际对话未调用辅助器
- 公开证据只含合成材料，明确来源读取为答复者报告及329-token清理材料遗漏；不冒充完整工具记录或物理隔离
- 运行时、原218条款/层级和安装包不变；未新增真机、当前账号/服务、修复、恢复或实际操作权限

## 2026-10-18 重建第三十三批

- 已有订阅升级只核对相关订单与目标缺口；实际订阅冲突绑定当前 episode，未解决不能重复购买
- 单项拒答保留已知互补字段及原来源；中断后旧套餐仍须单独复核
- 保留真实失败与独立修复后对话，按原 L+C 验收 T77/T80；累计47/218，171项待验收
- 既有证据按精确当前来源复核，审核材料不进入63成员安装包；没有新增真机或实际付款权限
- 2026-10-19 发布前隐私修订：公开审阅材料改为明确标注的最小合成证据投影，移除内部身份、机器路径与协调元数据；原始记录私下保留，运行时不变

## 2026-10-18 重建第三十二批

- 明确已回答的否定前提、访谈覆盖度与具体购买/操作权限的区别，运行时不变
- 保留 T38 首轮失败及独立新一轮回复，按原 L+C 核验 T36/T38/T46/T54
- 重新审阅 12 份既有证据覆盖的 26 项原条件；累计45/218，173项待验收

## 2026-10-18 重建第三十一批

- 补充规则字段、方向、共享服务、功能选择及待确认建议的指导与真实离线对话证据
- 按原 L + C 核验 ENV-T38/39/41/42/58；累计41/218，未增加真机能力

## 2026-10-18 访谈入口计数文案修正（第三十批已发布）

- 删除易过期的问题总数，保留按条件调度与 Q-C07 永久停用
- [单次文案兼容性记录](docs/evidence/skill-registry-wording-compatibility.json)保留历史生成回复、来源哈希与证据原文；不新增运行时能力或验收项

## 2026-10-18 重建第二十九批

- 修复到期重订用户相关旧订单处理，避免无关购买问卷
- 新增独立的当前套餐兼容性事实及中断、任务切换、重复回执保护
- 重新核验27项既有完整条件，并按原 L+C 验收 T76/T84
- 累计36/218，182项待验收；实际账号、付款及真机操作仍未执行

## 2026-10-18 重建第二十八批

- 保留并独立核验 T11/T12 的四段实际生成回复及逐条审阅证据
- 补充受限输入重放和非 ASCII 路径编码回归；运行时不变
- 累计34/218，184项待验收；不外推通用脱敏或未观察的模型行为

## 2026-10-18 重建第二十七批

- 按原 L+C 条件核验 T75 技术老手首次付费和 T79 新手已有订阅
- 技术熟练度、讲解偏好与订阅状态独立；保留未提供实际任务时的未知
- 累计32/218，186项待验收；运行时不变

## 2026-10-18 重建第二十六批

- 按原 L+C 条件核验 T29 订阅阶段优先和 T57 简短系统分支
- 保留已提供信息、未知与拒绝出口；不扩展已有权益问卷或安装付款教程
- 累计30/218，188项待验收；运行时不变

## 2026-10-18 重建第二十五批

- 按原 L+C 条件核验 T49 VPS 与手机付款设备分离、T83 首次内购必要检查
- 保留未知与已知负面前提，明确覆盖度不是付款资格；T36/T38 继续待验收
- 累计28/218，190项待验收；运行时不变

## 2026-10-18 重建第二十四批

- 修正Agent清理分流仍声称没有执行器的过期描述，提供固定C5内部宿主交接信息
- 保留独立选择、真实宿主核实和逐动作许可；通用清理请求不执行任何修改
- 修复安装后文档定位，增加实际打包链接回归；四处既有证据依赖经过独立复核


## 2026-10-18 重建第二十三批

- 按原 L+C 条件核验 T31 当前状态与既往受限分离、T47 暂停阻断后续提问与门禁、T82 退役字段迁移
- 补充精确证据依赖，修正迁移文档允许的固定 traffic_policy 字段说明；不增加任意历史格式兼容承诺
- 累计26/218，192项待验收；运行时不变

## 2026-10-18 编码模拟器最低版本调用约定修复

- 直接包装Path.open，保留io.open，避免Python3.10旧pathlib accessor把替换函数绑定为方法
- 保留原证据、断言和运行时；如实记录前一CI的模拟器失败


## 2026-10-18 验收测试编码与可移植性回归

- 修复七处证据文本读取默认编码，保留原文与断言
- 增加验收辅助测试静态编码/已知最低版本API检查和独立cp1252默认编码子进程回归
- 如实记录第二十二批Windows CI失败，运行时与23项验收结论不变

## Twenty-second reconstruction, 2026-10-18 (3430901)

- Revalidate original T03/T05 using retained actual two-turn guided responses and independent sentence-level review
- Preserve uncertainty for 403 origin/authentication/permission and prohibit inferred ban rates from a reported VPS observation period
- Add six evidence integrity checks; no runtime changes or native/service claims

## 2026-10-18 最低 Python 测试兼容修复

- 修复新增 T16/T23 测试使用 Python 3.11 专属 enterContext，改用等价 ExitStack 与 addCleanup，保留原断言
- 记录第二十一批 Python 3.10 CI 失败，不修改运行时或原验收条件

## 2026-10-18 重建第二十一批（51193c3）

- 按原 L+C 条件验收 T16：非秘密进度恢复、环境变更复核、已完成购买状态和真实临时清理中断／重试控制
- 按原 L+C 条件验收 T23：本机 Code 与 VPS 出口分开记录，不擅自转换远端工作区或安装
- 不修改运行时，保留宿主事实归一化和实际动作授权契约；累计 21/218，197 项待验收

## 2026-10-18 重建第二十批（76e799f）

- 新增可打包的 C5 命令分发与私有操作清单、计划／回执保存和重新核对接口
- 已审查的 Agent 宿主可调用真实隔离／恢复；普通脚本没有宿主时拒绝读取目标树和执行清理，不用参数伪造设备归属或授权
- 两个独立解释器完成临时夹具隔离后重新建立目标、备份和同意范围，再核对与恢复；包内包含使用指南，测试宿主不入包
- 修复独立审查发现的宿主异常、操作后恢复元数据、取消、超时和输出保存边界；不声称用户真机全清已验收

## 2026-10-18 重建第十九批（cfdd270）

- 按原完整 L+C 条件补 T01/T02 首次、重订、升级及完整环境复用验收；必要授权不由普通布尔值替代
- 保留 T18 两轮实际生成的合成申诉草稿与独立逐句事实审查；完整性测试不会再次生成回复，不外推未观察输入
- 不修改运行时；累计 19/218 原案例验收，199 项待验收，原条件及层级不变


## 2026-10-18 第十八批 macOS 测试夹具修正

- 将 Unicode 恢复记录预算测试改为浅目录与更多同级文件，避免 macOS 路径总长度限制提前打断测试
- 保留真实 4MiB 溢出拒绝，并增强准确错误码、零写入、条目数和原数据保留断言；不跳过测试，不修改运行时

## 2026-10-18 重建第十八批（ddd57b2）

- 新增选定设备限制经历 Q-D01 与独立清理意图 Q-D02；区分账号、设备、当前事故和历史事实，明确全清请求不依赖购买问卷
- 新增可调用 C5 POSIX 私有清单、目录/文件隔离、当前状态核对、独立授权恢复和严格重载接口；真实临时目录覆盖中断和冲突，不只展示计划
- 明确逐项选中的 Claude 本地历史、配置、扩展范围；源码、Codex、共享/未知数据保留，凭据/浏览器/卸载/永久清除另行适配
- Agent 可使用随包脚本，默认 CLI 与访谈保持无副作用；隔离不是独立备份，不把回调声明或临时目录测试当作真机证据
- 新增发行包内独立解释器的完整意图到隔离/恢复回归，原 218 条及 16 项既有验收保持原条件

## 2026-10-18 重建第十七批（9c5e8c9）

- 将已有有序主规则转换与真实临时文件写入、读回、独立回滚及 prepared 恢复串联，补完整 L+R 证据
- 不可表达的 ASN、匹配和动作在计划/写入前原子拒绝；保留顺序、重复项和来源，不隐含实际引擎部署效果
- 独立按原条件验收 ENV-T40；原 218 条不变，累计 16 项验收、202 项待验收
- 本批新增测试与证据、更新台账，不修改运行时实现

## 2026-10-18 重建第十六批（fe30684）

- 新增用户确认的 Claude 应用/目标流量 IPv4-only 策略，不回落到 IPv6；代理外层传输、控制恢复通道和其他应用保持独立
- 共享类型化策略接入访谈、Agent 修复候选、计划、报告和面板；策略声明不代表实际强制生效
- 缺少原生范围、实施能力或验证证据时保持 unknown/unsupported/not_established，不把空 AAAA、curl -4 或单次 HTTPS 成功当作全部 IPv6 阻断证明
- 保留旧报告兼容、严格隐私投影、取消和目标保护；修复固定策略字段与迁移消费者、静态面板的集成回归
- 原 218 条和原层级不变；本批不宣称真机网络修复或防封保证

## 2026-10-18 重建第十五批（5f027d0）

- 将单机 DNS/IPv6/Tailscale 排查经验重新整理为脱敏参考，仅分发派生文本
- 按需加载与网络指导加入链接；原来源编号、原稿和历史来源清单保持不变
- 分清受控宿主探测库与通用 CLI、实际设备验收；修正文档旧的全部探测不可用措辞
- 保留 AAAA、Fake-IP、UDP/TCP、WebRTC、退出回归与配置漂移的证据限制；不新增运行能力或改变 IPv4/IPv6 默认策略

## 2026-10-18 重建第十四批（230101b）

- 新增固定兼容版本的纯主规则片段转换，保留顺序、重复项、域名族 OR 与显式普通出站映射
- 仅在声明的规范域名与 TCP/UDP 终结前提下比较标签选择；不支持动作/条件/外层默认行为整批拒绝
- 不改变原无动作转换器，不写配置或调用引擎；新增打包入口与 Agent 私有调用示例
- 原已验收案例的受影响打包/指导证据重新复核；15/218 不变，ENV-T40 完整 L+R 仍待审阅

## 2026-10-18 重建第十三批（8b0b2a8）

- 完整库存与访谈信封先按受支持结构校验再投影，未知字段和畸形类型返回固定拒绝
- 静态库存嵌套请求在读取前拒绝未知字段，已知凭据形式别名不进入直接 API 报告
- CLI 参数错误保留帮助/用法与固定错误码，不回显不可信输入；独立导入回归避免测试顺序掩盖依赖
- 受支持合成报告保留来源与合成标签，原生通过状态不升级；此批为局部边界修复，原验收 15/218 不变

## 2026-10-18 重建第十二批（f57bfc8）

- 已有订阅的技术任务同步派生购买意图；技术与购买任务往返保留真实事实和既有完成记录
- 凭据泄露使用最小必要的专属分流措辞，紧急延期单独展示，不覆盖用户延期或要求回答完七题才给保护指导
- 当前已授予门禁所依据的必需证据失效时撤销范围并更新复核身份；取消/拒绝保留主结果，过期证据不能在重绑后重放
- 独立本地计划与尚待采集的后续阶段检查不受误伤；原 218 条与层级不变，累计 15 项验收、203 项待验收

## 2026-10-18 重建第十一批（ffc786c）

- 修复已选套餐但未给名称时提前通过门禁的问题：保留事实，只补问真实缺口，CLI 有效回答才消耗提问机会
- 重放首次订阅、接受本机默认与精确四事实输入，复核完整活动指导；T53/T74/T81 按原 L+C 验收
- 纯离线规则检查与工作流保护边界分别完成 ENV-T79、ENV-T90 原层验收，不推导真实流量或操作系统隔离
- 原 218 项条件与层级不变，累计 10 项重新验收、208 项待验收；75/113/30 为调度分类而非完成数

## 2026-10-18 重建第十批（84f8f73）

- 新事务在替换前保留 v2 暂存身份见证，新增只读核对及独立授权、当前快照绑定的 prepared 恢复
- 回滚自身也先保留恢复见证；回执失败、取消与清理失败保留主错误和恢复定位，不伪造历史成功
- 新增 reconcile/restore-prepared CLI 与 Agent 调用指导；旧 prepared 仍不写入，Windows/生产原生门禁不变
- 补备份/回执/目录/暂存身份及生成路径预算复核，异常先解决恢复前提，不能转入替代修改
- 临时文件故障注入、子进程中断与真实终端确认回归；原验收 5/218 不变

## 2026-10-18 重建第九批（293d856）

- 新增固定版本纯谓词格式转换：精确域名列表、Mihomo domain/classical 提供方、sing-box schema-v1 源规则集
- 保留顺序和来源，后缀含根域；明确规范小写 ASCII 匹配边界，动作、额外条件和不支持版本整批拒绝
- 组合现有 POSIX 事务完成专用临时文件写入、精确回读及独立授权回滚测试；真实环境生效不外推
- 复现写入后回执失败的 prepared 状态恢复缺口，保留证据并明确待核对；ENV-T40 全项仍待验收
- T09 包清单新增项重新复核，原 218 行及已验收 5 项不变

## 2026-10-18 重建第八批（1390be9）

- 新增纯离线规则来源导入器，仅支持明确精确域名列表和既有三字段DOMAIN/DOMAIN-SUFFIX片段
- 保留原始字节、记录位置、大小写、类型、顺序、动作及声明来源信息；不支持或动作冲突整批拒绝
- 私有结果接既有绑定与保护检查，公开预览只有固定状态/数量；不读写文件、不获取来源、不授予执行权限
- T09打包文件新增项已重新复核；原5项验收不变，ENV-T40仍待完整L+R验收

## 2026-10-18 重建第七批（b64c159）

- 显式中断续接先核实相关环境变化，保留VM/VPS选择、当前任务与接触历史；普通加载不重复提问
- 对当前回复、历史导入、旧异路线事实和购买完成组合保留明确边界；变化仅失效指定事实
- 接入CLI、活动Skill指导及兼容说明；T24按原L+C重新验收，现为5/218，其他213行待验收

## 2026-10-18 重建第六批（9498300）

- 同一受支持规则重复规划返回所供快照无需改动；合并策略中已正确条目不再阻止其余精确改动
- 无变更结果不创建事务、保留计划或写入回执，展示前仍重查目标、请求、来源、取消及期限
- no-change阻止替代修复回退，保留独立事故处置与真实前置问题；不升级原生或生效状态
- ENV-T60仍为部分离线子项，原验收条件/层级不变

## 2026-10-18 重建第五批（7f30247）

- 已观察接触后使用新的进程内审阅标记使旧接触证据/行动事实失效；重新授权不能复用旧事实
- 同绑定重绑与带接触历史续接更新标记，保持本地规划与获准中立诊断可用；不猜事故时间，不添加任意期限
- 增加原已验收证据底层文件哈希失效检查；ENV-T81/89仍待完整验收

## 2026-10-18 第四批 Windows 测试兼容性修正（386da6c）

- S03 来源清单读取明确 UTF-8，修复 Windows 默认编码异常；原断言不变
- 关闭管道回归断开已关闭 stdout 引用，避免 Windows communicate 读取线程对关闭句柄报错，保留非零退出与脱敏断言
- 更新 T09 同内容证据的测试文件固定哈希；生产代码与验收范围不变

## 2026-10-18 重建第四批（6e0688f）

- 新增来源实际字节去重助手与M14使用步骤，完全相同资料按一个内容组处理；不同哈希不推导独立交叉证据
- 重建T19/T20/T21路线的确定性输入/预期/实际及内容审阅，T24保留环境变更复核尚未接入的明确缺口
- 原规范条件与真机延期不变；正式验收状态以本批逐例证据及独立复核为准

## 2026-10-18 重建第三批（f87fdbf4）

- 离线报告按已支持字段的类型/值域过滤，拒绝P17 UUID等未实现字段原始标量；保留现有原生生产者格式和显式缺口
- 事故证据按明确来源/时间处理重放和陈旧替换，保留解决状态与失效标记；当前新回复仍按新观察处理
- 所有结果仍是离线/合成证据，不替代完整ENV-T121、原生验收或真实行动授权

## 2026-10-18 重建第二批（d8f4e2b）

- 已识别取消的盘点/诊断不再创建请求的导出文件；保留正常导出与既有退出码，不声称覆盖写入开始后的取消
- 访谈CLI参数错误不回显私人输入；输出失败返回非成功状态；既有凭据筛查补GitHub令牌形态，普通别名及旧状态兼容保持
- 来源索引对齐七份阅读材料与两份设计快照；最初八个输入清单明确为历史记录，原文、哈希及第三方归属不变

## 2026-10-18 重建第一批（de80b76）

- 从已发布584064fc重新验证，不沿用丢失23批源码的通过声明；新增218原条件保真台账、Mac/Windows延期步骤及依赖
- 补取消/拒绝/上下文诊断的优先阻断，未知能力仍可交由Agent调查，未知错误不能冒充能力缺失
- 修正访谈当前事故、历史事故、解决后新事故和旧事实失效的状态分流；CLI取消优先于输入解读
- 保留修复计划前后重查原请求、目标和来源快照、期限与取消状态，陈旧计划不返回成功摘要
- 所有回归仅用离线输入及私有临时文件；没有新真机验收、平台接触或生产修复准入

## 未发布 — Windows输出/测试可移植性修正与Mac证据补齐

- 修复选择器在Windows cp1252输出中文JSON失败：JSON使用ASCII转义，解析后语义不变；增加强制旧编码回归，源码检查显式UTF-8
- 两项Mac开发probe合成测试使用模块局部OS替身，保留重置、顺序与清理断言，不跳过Windows测试，不放宽生产平台门禁
- 记录9caa42f三组运行时CI和浏览器通过、Windows1失败/3错误的实际结果；本修正云端1034项1026通过/8跳过，Windows修正后CI尚待执行
- 已下载并核验修正版Mac证据包和两份JSON；不同内容/mode/group/普通xattr/ACL恢复获得限定证据，不同provenance仍未成立，完整应用恢复未验收

## 未发布 — Agent环境驱动修复编排（与Mac调查组合复核）

- Agent负责检测、解释、具体确认、环境限定修复、恢复与同范围复测；内置脚本缺适配时继续调查，不默认交给用户手工处理
- 新增只读动作选择器与完整merge-policy/rules-prepend模板；导入报告不恢复权限、不执行修改、不宣称修复成功
- 权限、PC0、目标/上下文、陈旧快照、备份与写后失败保留前置阻塞；同步主Skill及强制安全说明，补16项回归和发行清单
- 组合云端1033项：1025通过、8跳过；两组Node、编译、可复现打包及解包CLI检查通过。该轮Mac修正版先仅收到限定回调，后续证据传回核验见最新记录；生产内置修复准入未开放

## 未发布 — Mac 元数据与运行路径原生适配调查

- 新增仅写自有临时文件的开发验收工具，比较内容、mode、owner/group、可见xattr及显式ACL，保留descriptor未复位反例与provenance setter成功但回读不符的阻塞
- 补12项合成边界回归；云端复核另补2项，修复正例复用反例已恢复元数据的fixture缺陷，修正后的限定原生恢复已补齐两份证据JSON核验，不同provenance仍阻塞；工具不进入发行运行时，不修改事务或生产修复准入
- 记录真实规范路径启动的上下文连续性与仍未受信任的运行时状态，以及Verge2.5.8写入/重载的固定版本来源和待授权最小计划；未操作真实配置

## 未发布 — 空rules扩展候选与统一CLI

- 显式rules-prepend路线绑定2.5.8应用元数据、profile索引、当前基础配置和扩展UID，仅在既有空prepend列表插入选定DOMAIN/DOMAIN-SUFFIX规则
- 保持append及其他字节，限定delete为空；报告已知优先级影响，拒绝重复/受保护冲突、共享扩展及全局默认作用域，不证明完整规则图或实际路由
- 保留计划升级0.2，绑定全部源快照并在私有复核、提交及读回边界重查；旧计划要求重新生成及确认
- 原生执行、Mac元数据安全事务、写入者排除与真实应用验收仍阻塞；无实际配置写入或重载，详见docs/rules-extension-plan.md

## 未发布 — Mac 检测缺口与路径阻塞定位

- Mac盘点补S04采集进程架构，保留硬件/Rosetta未知，不以x86_64判定Intel
- 严格路径失败附固定字段/原因枚举；元数据和CI阻塞诊断可定位symlink等条件，不暴露真实路径、不跟随链接、不放宽门禁
- 面板显示采集器已有的Mac默认代理开关白名单摘要，scoped详情和真实路径继续未知
- 新增11项回归；初次Mac全套因缺解析器及临时文件元数据阻塞；获准安装解析器后仍有56项事务/恢复失败，不宣称全套通过或修复验收，详见validation


## 未发布 — Agent修复入口与受限事务接线

- 确认对话授权后由Agent调用内部脚本的交互设计，不新增终端确认码要求；真实操作授权仍由可信宿主逐次核对
- 增加精确文件preflight、选定规则私有差异、显式私有计划保留和摘要/有效期/原快照绑定；不接受JSON批准字段或运行时任意执行器
- 事务接线保留备份、提交前复核、读回及恢复记录；生产Clash版本/归属适配门禁仍关闭，不能把合成临时文件测试当作已完成用户设备修复
- 增加固定Clash Verge Rev2.5.8来源的只读声明链校验，区分merge数组替换与rules序列扩展；拒绝重复plist键/配置UID/文件归属和路径歧义，仍不证明原生所有权或开放执行
- 无新增依赖、设备操作、应用启动/重载或公网探测；实际范围、证据和限制见`docs/agent-repair-flow.md`

## 未发布 — 配置候选与诊断会话边界

- 私有候选增加原始字节偏移/前后policy token差异；拒绝无效域名标签和可证明的前置MATCH/DOMAIN-SUFFIX覆盖，仍非完整规则图或原生适配器
- 严格上下文复核遵守原60秒会话期限，锁定上下文/取消回调异常，避免DNS错误清洗后继续接纳结果
- 取消/拒绝会话不创建请求的面板文件；阻塞报告仍可按显式输出请求保存
- 仅离线/合成边界增量，无真实配置读写、DNS请求、用户设备操作或权限扩张；原生验收与可信宿主集成仍待完成

## 未发布 — Python 3.10 最低运行时 CI

- 增加独立Linux Python3.10全套回归、脱离源码发行包运行、编译及可复现打包；官方setup-python使用已核对的完整提交固定
- 三平台默认运行时任务保持原样；8c4adae的CI38788444583首次全部成功，Linux CPython3.10.22完整896项888通过/8跳过、脱离源码发行包9/9；不以此代表Mac/Windows最低版本或真实设备验收
- 仅在一次性CI runner准备解释器，无用户设备安装、原生smoke启用或公网诊断探测

## 未发布 — 合成面板真实浏览器交互检查

- CI自有Chrome通过本地调试管道检查键盘焦点、Enter/Space展开折叠和双尺寸无横向溢出；不注入页面脚本、不放宽sandbox/CSP
- 只导出有界合成交互摘要；页面请求观测不冒充全浏览器网络隔离，实际执行证据待精确CI

## 未发布 — 单轮多事实与本机默认建议

- 离线访谈增加原子化规范事实批处理及CLI answers列表；订阅阶段先于派生任务更新，顺序不改变意图，重复/冲突/错误整批拒绝
- 明确接受当前本机默认建议记录accepted_default，不再重复路线问题；不会覆盖已选路线，不提升G3/PC0或保存许可
- 自然语言提取仍由宿主完成，未给出的套餐不猜测；T53/T81仅新增相应子证据

## 未发布 — Windows token restriction 返回长度兼容

- 对TokenHasRestrictions专用读取器使用零初始化DWORD缓冲，仅接受返回长度1或4；长度1须无脏高字节，所有非零限制值仍阻塞，通用读取器/权限/跳过集合不变
- 根据CI固定错误阶段定位增加回归；实际返回长度未从日志推断，原生结果须由后续CI验证

## 未发布 — 部分元数据与CI故障定位

- Mac新增无上下文句柄的部分元数据API；终端会话只对路径筛查失败在原剩余期限内使用，不能继续DNS或提升信任
- Windows原生失败增加双重白名单阶段/原因诊断，保持原失败结果和跳过集合
- 合成截图可显式下载固定上游提交、SHA-256与OFL许可核验的Noto中文字体到临时目录，通过仅内嵌字体渲染；不安装字体或扩大宿主权限
- 修复Windows下模拟POSIX清理测试缺少SIGKILL常量；运行时清理与原断言不变

## 未发布 — 合成浏览器截图与原生失败诊断

- 新增独立CI合成面板截图流程，使用runner已有sandboxed Chrome和中文字体，上传精确提交的桌面/窄窗口截图与范围清单；未运行前不声明视觉通过
- 原生上下文smoke的非零子进程可输出严格白名单错误代码/阶段及有界退出码，仍判失败；不回显原始输出、不扩大可跳过错误集合

## 未发布 — 发行包与 CI 原生上下文边界验收

- 直接对临时解压发行包运行入口/离线链路、依赖/来源哈希、可选解析器缺失和隐私哨兵回归，避免源码环境掩盖打包缺项
- 新增显式启用的CI自有进程上下文smoke：Mac/Windows只读当前runner身份/会话，受控子进程、有界输出；已知headless/权限阻塞记跳过，未知ABI/清理错误记失败
- Windows mock-cmdlet保留原15秒语义测试，另在其后加入有界固定阶段诊断以定位重复超时，不掩盖原失败
- 修复Mac helper提前退出导致stdin关闭泄露BrokenPipe的竞态，保留固定退出错误分类并始终回收
- 用户设备和真实DNS未验收，包检查或CI整体绿色不自动代表原生上下文完整通过

## 未发布 — 私有规则修改候选

- 将限定keep-existing语义计划与绑定的UTF-8配置快照编译为内存候选，仅替换选定既有DOMAIN/DOMAIN-SUFFIX规则policy token并保留其他字节
- 重解析验证完整语义不变范围，拒绝重复/歧义选择，私有材料与可分享摘要分离；无文件IO、CLI、apply或事务执行
- 原生适配、版本/归属、真实路由与即时授权阻塞全部保留；不声称已修复配置

## 未发布 — 时间与预算数值边界

- 对公开资格判定、监听绑定、Windows离线预检、控制器与系统DNS边界拒绝超大整数、非有限时间、倒退时钟及截止溢出，返回固定失败而非泄露异常或接受无效时效
- 补31项合成回归；不扩展权限、网络目标或原生能力，不将回调边界防护描述成底层硬实时保证

## 未发布 — 原生上下文观察与窄范围诊断会话

- 新增独立 macOS/Windows 当前身份/控制台上下文观察，私有短时句柄不持久化、不形成授权或完整命名空间/运行时证明
- 新增 Mac/Windows 终端元数据会话：每次显示精确读取范围并要求新随机 nonce，默认不保存、不探测 DNS
- 可调用会话串联逐项授权与系统 DNS 样本，但生产宿主绑定/运行时/中性端点核验仍须独立提供，不能用 JSON 或永真回调代替
- 共享新文件输出拒绝Windows备用数据流、设备路径/名称与尾随点空格别名；不把语法检查当作ACL或本地存储证明
- 宿主核验失败在会话内锁定，保留失败与历史样本，不将面板输出当作就绪通过
- 所有证据为合成/注入测试，真实桌面/API兼容性、设备命名空间和 DNS 验收仍未完成

## 未发布 — 系统 DNS 样本与命令进程清理

- 新增 macOS getaddrinfo 与 Windows Resolve-DnsName 独立受控子进程库适配器，均要求精确查询授权、当前绑定和可信运行时核验
- 系统解析样本接入既有离线 DNS 行，区分平台与来源，不编造 RCODE、服务器、路径或无泄露结论
- 修复固定命令执行器的进程生命周期与清理边界，并补回归测试；不扩大命令白名单或设备操作权限
- 实际设备 DNS、运行时信任与授权 UI 集成仍待验收；合成进程/PowerShell mock 不等于真实 DNS 验证

## 未发布 — DNS 协议基础与 Mihomo DNS 样本

- 新增纯 A/AAAA DNS 编解码与有界响应关联，无传输、CLI 或自动探测
- 新增独立 Mihomo DNS 库适配器，可信宿主逐次核实绑定与精确查询授权后才允许单次数值回环请求；不扩展配置审计白名单
- DNS 样本按白名单接入紧凑离线面板，保留失败、取消、过期与证据不可信提示；不会将样本变成授权或环境通过
- 无真实控制器、公网 DNS、用户设备或浏览器验收；ENV-04、VAL-04 仍未完成

## 未发布 — 离线探测结果接入面板

- 可选本地 HTTPS/STUN 证据附件，保留逐样本路径、地址族、时间和取消/过期/未知状态
- 仅展示白名单摘要，不输出 IP/设备别名；输入成功声明不等于可信来源、授权或环境验证
- 保留紧凑三列表格；未检测的 DNS/WebRTC/一般 UDP/故障阻断仍独立标记
- 合成/注入 transport 回归，不执行新联网探测或真实设备验收

## 未发布 — 离线环境状态面板

- 新增标准库静态 HTML 投影，按设计章节呈现十一类环境状态与授权缺口
- 仅展示白名单枚举、布尔与逐字段时效；拒绝重复字段及非法 ID，不回显原始秘密
- 不采集、不联网、不启动浏览器；网络细粒度结果尚未接入，保持 not_run
- 精简为白底三列表格、11行检查项与默认折叠证据；保留可见失败/取消、时效、演示与授权提示
- 面板23项合成回归通过；实际桌面/移动浏览器渲染仍未执行

## 未发布 — 历史访谈迁移

- 识别实际旧紧凑状态/报告，按字段语义迁移，不信任历史错位问题ID
- 复用事实保留为过期证据，丢弃停用归属题及旧Q-C08，不继承许可/保存同意/绑定
- 历史账号停用仅形成待重新确认提示，不与设备历史混同
- 当前为纯宿主接口，无自动CLI迁移、保存或操作授权

## 未发布 — 独立终端恢复

- 新增POSIX普通终端恢复入口，精确回执与目标/备份绑定，不依赖Agent或联网
- 写入前逐阶段新的随机挑战确认，拒绝排队粘贴、管道授权和保存许可
- 跨进程临时文件恢复、崩溃待处理、备份损坏与并发修改保护回归
- Windows/原生应用和网络恢复仍未开放；不把普通文件恢复当成全部VAL07

## 未发布 — 有界STUN协议底座

- 新增独立STUN Binding编解码与精确范围、固定数值端点、最多三次发送的事务
- 合成及自有IPv4/IPv6回环夹具验证协议拒绝、取消和清理；未运行公网探测
- 返回映射仅为未认证样本，浏览器/Claude路径和TUN关联保持未知

## 未发布 — Windows监听者与限流提示

- 增加限定Windows监听PID/创建时间/同用户的只读核对；命名空间仍由宿主断言，不宣称原生核实
- 限流响应提供有界Retry-After建议；日期格式需要可信接收时钟，始终不自动重试或等待
- CI仅用自身临时监听器测试，无真实控制器调用或用户进程盘点

## 未发布 — 语义修复计划

- 增加四模板离线语义计划、DNS依赖环检查、带类型的代理组图、控制路径保护
- 私有快照哈希和公开别名分离；不生成执行补丁、不自动授权或开放原生改写
- Windows受控写入设计提案独立记录权限/元数据和崩溃恢复限制，尚未实现

## 未发布 — 安全盘点增量

- 新增限定静态配置盘点、无凭据回环控制器快照及保守CLI；运行时有效性保持未知
- 新增阶段/范围资格校验，审批期间目标变更、撤回与新失败证据使旧许可失效
- 新增Windows本地卷只读计划底座及临时文件测试；写入/回滚仍不支持
- 可选YAML解析器在测试依赖中固定版本，运行时缺依赖不自动安装
- 原生完整验收及218项设计追溯仍未完成；需单独审阅确认后合并

## 0.2.0 — 工作流基础（开发中）

- 完整95-ID中文访谈状态机与独立CLI、明确保存/续接
- 新增S07 VPS脚本参考，按阅读材料收录，危险命令不自动执行
- 新增带明确端点/路径授权的HTTPS探测契约及本地WebRTC页
- 新增限定POSIX普通文件的事务/备份/回滚基础
- 更正兼容访谈入口的问题ID，补全主规范映射
- 更新原生Mac与三平台CI证据，仍未完成全设计与实机配置验收


## 0.1.1 — 2026-10-15（来源阅读与只读采集增量）

- 收录获准公开的六份来源资料、两份设计规格及 PDF 搜索辅助文本
- 添加会话内按主题提供原文的阅读入口，保留署名与分发哈希；清理个人机器记录
- 扩展 Mac/Windows 固定命令只读采集，限制输出、时间和执行路径
- CI 扩展 Linux/macOS/Windows 单测、回归、打包与只读元数据 smoke
- 仍未完成全部设计要求；真实代理/浏览器/修改恢复需继续实现与验收


## 0.1.0 — 2026-10-15（诊断预览）

- 根据主规范 v0.1.10 / ENV v0.3 实现 Codex 优先 Skill
- 建立订阅阶段优先访谈、PC0 接触前限制和目标设备边界
- 新增 Python 标准库的只读检查、离线分析与修复计划接口
- 按需加载本机、VM、VPS、支付、事故与网络证据说明
- 新建行为回归、合成样例与确定性发行包
- 采用 GPL-3.0-only；不包含未经确认再分发权的第三方全文或清理代码

### 本版限制

原生 Mac/Windows 实测未完成；没有自动配置、清理、联网探测、付款或自动回滚能力。首版检查只覆盖明确声明的字段子集，未覆盖项保持未知。后续新增能力须分别记录实现、夹具与原生验证状态。

## 未发布 — Windows 元数据离线预检

- 新增始终阻止写入的离线预检，明确部分安全信息、未验证目标/新鲜度和未实现元数据保留
- 新增有界 BackupRead 序列帧检查，仅接受默认数据与安全流；调用方输入不构成原生捕获或完整安全描述符证据
- 增加12项合成回归及极大整数预算回归；不提权、不启用特权、不开放 Windows 写入或恢复


## 2026-10-18 rule-scope guidance and observed original-case evidence

- Clarify TLS field semantics, traffic direction, shared-service preservation,
  feature/version source selection and pending recommendation boundaries
- Preserve atomic import and current scoped IPv4-only policy; add no runtime
  feature-gating engine or device operations
- Retain independently reviewed ENV-T38/39/41/42/58 observed L+C examples,
  actual helper traces and separately identified reviewer negative controls
