# T19 / T20 / T21 / T24：路线验收重建证据

日期：2026-10-18（UTC），本页已按第七工作树的 T24 修复重新回放和逐句复核。仓库基线：`584064fc9c210e684ba4a0e11b79db74f1946155`；本次评审对象是基线上已有重建修改的工作树，不能把 HEAD 当成全部受审字节。文末逐文件 SHA-256 固定实际评审对象。

## 结论及证据边界

| 原 ID | L：纯逻辑／对话夹具 | C：内容／来源逐句审阅 | 本轮建议 |
|---|---|---|---|
| T19 | 未选／只展示未回答／明确不知道都不确认本机；只有明确接受才进入本机 | 默认建议、主动选择、只展开所选路线一致 | 可作为原 L+C 行的验收候选 |
| T20 | L0 的明确 VM 选择进入独立 VM 提问序列，保留逐步说明偏好 | VM 入门解释及 V1→V2→V3 的准备、接入、配置、日常、故障与恢复逐步卡片均经下述语义审阅 | 可作为原 L+C 行的验收候选 |
| T21 | 已有／新建两种 VPS 输入都保持 VPS，保存不同服务器事实，进入同一有条件的独立路线 | P1 明确分开已有服务器接入与新服务器比较；P2—P5 提供后续完整路线 | 可作为原 L+C 行的验收候选 |
| T24 | 显式中断续接保留选择，先输出完整相关变化核实；未答阻止 G2，没变保留原时点，变化只失效指定字段 | SKILL 入口、intake 续接契约、接触指导与 API/兼容说明已逐句对照原条件 | **本页提供 L+C 候选证据，最终状态见 ledger** |

L、C 是原 `verification_layer=L+C` 的含义，不是交付依赖字母。原行和原规格未编辑；本批只增加有界续接契约及其 CLI/指导/测试。既有 T19/T20/T21 的 evidence hash 在本次完整复核后更新，不提前改变 T24 状态。T19/T20/T21 的候选结论同时依赖行为回放和内容审阅，不能只运行测试就自动更新它们的状态。

本次 L 证据为 `interview_flow` 的内存状态及调度器回放；C 是随包、当前实际生效指导的人工语义审阅。没有调用模型、没有验证自由文本提取、没有测 Codex UI 的显示与点击、没有创建或运行 VM/VPS、没有访问网络、修改系统或验证真实设备权限。`dialogue_inputs` 是虚构场景说明，输入代码的是明确列出的归一化事实，不宣称已经测过这些中文句子的自然语言解析。

`G1=complete`／`G2=pass` 只表示此模块把已提供的 reported 答案视为访谈覆盖／规划输入；本夹具的 `not_tested`、`pending_verification` 不能成为兼容性、实际配置、PC-G1 或部署成功证明。本页固定路线回放全程 G3 blocked、PC0、保存同意均关闭；补充状态测试也验证已发生的 PC2 历史不会因续接重置。内容中要求以后核验的价格、许可证、客户端兼容性仍未实测；教程存在不代表生产适配器开放。**这不是全项目完成声明。**

## 原文、设计依据和可复现材料

以下四行完整复制原验收要求，不以本页摘要替换：

| ID | 原场景 | 原完整要求 | 原层级 |
|---|---|---|---|
| T19 | 未指定部署方案，也无明确远端任务 | 本机仅为默认候选，先询问选择/接受建议；未答时为 `unconfirmed`，不是已选本机 | L+C |
| T20 | L0 明确选择虚拟机 | 进入 `R-VM`，提供新手步骤，不强制先走本机或 VPS 教程 | L+C |
| T21 | 用户明确选择 VPS 完整部署 | 进入 `R-VPS`，不被本机默认值覆盖；区分已有与新建服务器 | L+C |
| T24 | 已选 VM/VPS 后中断再继续 | 按当前任务保留选择，核实环境变化，不重置本机默认值 | L+C |

出处：`docs/implementation-tracker.md` §8 对应原行；`sources/design/D-SPEC-v0.1.10.md` T19/T20/T21/T24。进一步阅读了 D-SPEC §3.1（能力和方案正交）、§3.3（宿主／目标／出口）、§5.0—5.7（独立完整路线）、§6.14 与 §7.4（续接），以及 D-ENV §18 的阶段和变化失效约束、§18.10 的 VM/VPS 目标边界。原规格中的历史“未实现”不是当前代码测试结果；本页按实际受审工作树列证据。

材料：

- `tests/fixtures/acceptance-routes-rebuild.json`：固定虚构场景、共用 reported 事实、VM/VPS 逐题答案、已有／新建服务器差异
- `tests/test_acceptance_routes_rebuild.py`：独立手写的完整中文预期题目及结构化预期；没有从运行时问题常量生成预期，没有通过“包含若干词”或测试数量判断内容正确
- `project()`：明确列出被断言的完整边界，包括 task/target/account、route/basis、全部路线题 ID、完整下一题、完整 assessment、PC0 和保存权限；服务器答案还检查完整事实信封
- `replay()`：输出本次实际回放的完整投影，供逐字段复核；不会反过来自动生成预期断言
- `tests/test_interview_resume.py`：额外的宿主 API、条件分支、重试/购买组合、CLI 和错误路径矩阵
- `docs/interview-resume.md`：明确 API、可选保存状态扩展、当前回复/历史导入界限、迁移与回滚

复现命令：

```sh
python -m unittest discover -s tests -p test_acceptance_routes_rebuild.py -v
python tests/test_acceptance_routes_rebuild.py --replay > /tmp/guardian-route-rebuild-actual.json
```

本次实际结果：6 个规范路线测试方法全部通过，0 skipped；两次完整 replay 输出逐字相同。另运行 `python -m unittest discover -s tests -p 'test_interview*.py' -v`，145 项全部通过，其中 33 项为新增续接 API/CLI 定向方法；`python -m py_compile skills/claude-guardian/scripts/interview_cli.py tests/test_interview_resume.py tests/test_acceptance_routes_rebuild.py` 通过。原 T24 缺口断言已替换为更强的规范预期，没有删除条件或放松断言；T19/T20/T21 的手写完整预期未改。测试数量不等于原案例验收数量，最终判定还依赖下述完整 C 审阅。

完整 `--replay` 标准输出 SHA-256：`8e2a95d358a8fb9ca27a95f72f9788598e2337ed0498a5e22936142767727a84`。原事实时间固定为 `2026-10-18T04:00:00Z`、来源 `synthetic:route-case`；本次变化复核时间为 `2026-10-18T04:30:00Z`、来源 `synthetic:current-review`。回放不随机、不会联网；单元回放期间文件打开、socket、Popen、os.system 均由拒绝式哨兵阻断。

## T19：未指定路线

### 固定输入、预期、实际

输入 `T19`：目前已有订阅，只准备 Code 的运行环境；未指定部署路线或远端任务，要求计划。共用事实明确 task=`environment`、使用 Mac、逐步指导、保护项目和设置；没有 Q-C05。这里没有从“Code”“Mac”“现有代理”推定已选本机。

预期：本机只能作为候选，问一次本机／VM／VPS／比较；未答不确认、不展开任何独立部署题；明确接受以后才切换为已确认本机。

实际（完整对象由测试逐字段比较）：

| 检查点 | route / basis | route_confirmation | 下一题 | 路线题 | G1 / G2 |
|---|---|---|---|---|---|
| 初始 | local / default_proposal | unconfirmed | Q-C05 | `[]` | partial / blocked |
| 只标记 Q-C05 已展示，尚未回答 | local / default_proposal | unconfirmed | null | `[]` | partial / blocked，Q-C05=unasked |
| 用户回答 unknown | local / default_proposal | unconfirmed | null | `[]` | partial / blocked，Q-C05=unknown |
| 明确 accepted_default | local / accepted_default | confirmed | Q-L01 | `[Q-L01,Q-L04]` | partial / blocked，仍缺本机事实 |

实际 Q-C05 完整提示为：“用本机、虚拟机、VPS，还是先比较？本机默认建议。”题目 `requires_action_authorization=false` 只表示提问不需要动作授权，不表示答案授予执行权限。四个检查点都保持 G3 blocked、PC0 和全部保存许可 false。

### C 逐句／逐分句核对

1. 原句“本机仅为默认候选”：SKILL 开始方式第 3 项第一句说本机是默认建议但要询问接受／选择；`intake.md` Scheduling 末段第一句把 local 限定为接受前的 proposal；routes 第 11 行标题明确 never silently selected。三个入口没有把候选写成既定事实，与初始 actual 一致。
2. 原句“先询问选择/接受建议”：SKILL 同项提供本机、VM/VPS、比较三个去向；routes 第 67 行的完整选择句明确展示三种方案且可“先解释”。紧随的“接受本机建议即可，不考察技术水平”避免再要求服务器比较。实际 Q-C05 也提供同一组实质选项，没有预先展开 VM/VPS 资源调查。
3. 原句“未答时为 unconfirmed”：`intake.md` 紧接句要求未接受保留 default_proposal；`contact-and-safety.md` Permissions 第一段明确 silence/cancellation/default option 不能授权。actual 的初始、已展示未答和 unknown 三态均不确认；已展示未答不再发同题是“不重复问”的调度约定，并非补出了用户答案。
4. 原句“不是已选本机”：routes 第 44 行“每次只展开选中的路线”，配合本机标题及 intake 选择依据约定，禁止把 local 候选当成执行入口。actual 的 route_question_ids 在未答时为空，接受后才出现 L01/L04。

结论：原句的四个条件都有 L+C 对应证据。无需新网络／原生执行层来证明这个特定行；也不据此接受其他部署能力行。

## T20：L0 明确选择 VM

### 固定输入、预期、实际

输入 `T20`：“我是零基础，明确选虚拟机，请按新手步骤指导。准备新建，虚拟化软件还没选。”宿主归一化输入 Q-C05=`vm`、Q-C10=`step_by_step_beginner`，V01=`{lifecycle:new, hypervisor:not_selected}`；详细后续字段全部列在 fixture，均为 reported。

预期：立即保持 R-VM，不需要先选择／完成本机或 VPS；用小步问题了解既有／新建、主客机、资源、网络、共享、恢复，再按 VM 操作卡给入门说明。

实际 route=`vm`，basis=`explicit_choice`，route_confirmation=`confirmed`；route_question_ids 精确为 `[Q-V01,Q-V02,Q-V03,Q-V04,Q-V05,Q-V06]`，没有 local 或 vps 题。完整下一题轨迹是：

1. Q-V01：“已有虚拟机还是准备新建？使用什么虚拟化软件？”
2. Q-V02：“宿主与客机各是什么系统/架构？”
3. Q-V03：“可供 VM 使用的内存/磁盘大约多少？已有项目需要保留吗？”
4. Q-V04：“虚拟机怎样联网，代理在宿主还是客机？”
5. Q-V05：“需要共享哪些目录、剪贴板或工具？是否已有账号凭据挂载？”
6. Q-V06：“有没有快照/备份和可用的恢复方式？”

每次回答后只剩后续未答字段；完整下一题及 assessment 都与手写预期相同。回答完后 question=null，G1 complete/G2 pass，仅为访谈状态；Q-C05=vm、Q-C10 的新手偏好和 V01 的“准备新建、hypervisor 未选”原值均保留。代码没有声称提供商已选择或已创建虚拟机。新手操作内容是下列实际 guidance 的 C 证据，**不是**伪造一次模型生成回答。

### C：入口、新手说明、独立步骤逐句审阅

`routes-and-platforms.md` 的位置固定于文末 hash。下列为逐句／分句的语义核对，不是关键词存在测试。

| 实际指导位置 | 句子／分句的具体含义 | 与 T20 的关系及审阅结果 |
|---|---|---|
| SKILL 开始方式 3 | 本机／VM／VPS 是独立方案，不是升级顺序；明确目标优先 | 允许 L0 直接 VM；没有本机或 VPS 先修条件 |
| SKILL 按需加载第一条及末尾双语呈现说明 | 入口实际链接 `references/routes-and-platforms.md`，明确 M01/M06–M09、VM/VPS 与生命周期计划；英文技术细则供执行者，不直接把整份参考文件当中文答复 | V1—V3 不是孤立未链接文件；所选 VM 可从生效 SKILL 按需到达，并以中文分步解释 |
| intake Scheduling 第 2 段末句 | 技术水平只改变解释深度 | 新手偏好不能把已选 VM 改成本机 |
| routes 61 | VPS 是远端租用服务器；本地 VM 是宿主上的客机；标签不代表账号稳定性 | 提供本机与客机的第一层入门概念，不用风险排名劝退所选路线 |
| routes 67 第 2、4 句 | 不考察技术水平；新手用逐步卡片，熟悉用户用简表，安全门槛不变 | 实际指导规定 L0 的呈现方法，不能把全部卡片一次塞给用户 |
| routes 44 的三句 | 操作卡是人的分阶段手册；适配器能力另查；每次只展开所选路线 | VM 完整卡片可独立读取，不能先要求读完 L1—L3 或 P1—P5 |
| V1.1 两分句 | 明确选 VM 后确认客户端／项目／hypervisor／主机资源；Mac 宿主不能证明客机二进制兼容 | 第一步是收集此 VM 的具体条件；fixture 的 hypervisor 未选不会被猜测成已安装 |
| V1.2 两句 | 已有 VM 记录标识／OS／网络／共享且不覆盖磁盘；新 VM 先核实许可／架构／资源／镜像和回收 | 有新手可顺序跟进的新建路径，也保护已有 VM；不强制重建 |
| V1.3 两句 | 新建／安装要批准，不捆绑付费、不克隆登录状态；零预算不满足则停 | 选择 VM 不是购买或安装许可；不把费用／许可问题留成隐含动作 |
| V1.4 两句 | 只准备获准任务依赖，Claude 留到 PC1；不默认共享整个 home 或双向剪贴板 | 给准备与实际客户端接触清楚顺序；默认共享不是“新手便利” |
| V1.5 两句 | 用户选精确共享范围与权限并了解后果；改变前记录原值 | 有明确、可暂停的共享决策及恢复前提 |
| V1 验收／恢复三句 | 记录客机与共享边界；无权限／不兼容阻塞；失败保护旧盘，删除也需批准；宿主成功不能代替客机 | 没有把问卷完成或教程读完当部署完成 |
| V2.1 两句 | 记录 NAT/桥接及地址族；画客机→代理→上游→出口，解释 guest loopback 不等于 host | 对 fixture 的“宿主代理+NAT”给出具体下一步，避免照抄 127.0.0.1 |
| V2.2 两句 | 核实最窄可达接口及控制；监听／防火墙改动需单独批准并保护宿主业务 | 网络步骤有作用域和失败边界，不以整网开放简化新手操作 |
| V2.3 两句 | 测客机路径，宿主只对照；DNS/IPv6/UDP/WebRTC 及浏览器独立复验 | 不混合主客机结果 |
| V2.4 两句 | 快照可能含秘密，共享／云数据不属于恢复保证；关机／静默和快照另批，名称不写秘密 | 快照不是无限恢复承诺 |
| V2.5 及验收／恢复 | 独立备份并在隔离副本读回；失联走宿主控制台；回退列出丢失的新改动；不能解除封禁 | VM 路线自身有恢复步骤，无需先走其他教程 |
| V3.1—2 | 客机为 PC1/PC2 目标，兼容性和安装／登录／支付分开；OAuth 核对回调，不搬令牌 | 正确承接 V1/V2，既不在 PC0 安装也不声称主机登录代验客机 |
| V3.3 | 按宿主网络→启动 VM→客机时间／网络→客户端启动；暂停／NAT／换网后重测 | 有具体日常顺序和变化后的复验安排 |
| V3.4 两句 | 主客机和应用更新分别记录；前置检查备份／空间，后置检查共享权限、路径和子进程 | 更新有前后检查，不等同重建 |
| V3.5 两句 | 故障先资源／磁盘／时间／网络，再客户端／认证；迁出只迁获准数据，旧环境保留至确认 | 提供排障／迁出出口，不先删除 VM |
| V3 交付 | 主客机摘要、启动步骤、路径测试、共享清单、恢复步骤，未执行记 not_run | 清楚定义交付和未执行范围，不虚报实机成功 |

因此 T20 的“提供新手步骤”有实际分阶段内容支持，而非只检测 R-VM 字样或 V1/V2/V3 标题。此输入尚未选 hypervisor，当前合适交付是逐步选型／准备卡；不能凭这行验收声称任何具体 hypervisor/guest 组合的点击教程或原生安装已经验证。

## T21：明确 VPS 完整部署，已有／新建分开

### 固定输入、预期、实际

两个独立回放都从 Q-C05=`vps` 开始，再答 Q-S01=`workspace_not_exit_only`。一个 Q-S02.lifecycle=`existing`、server_alias=`server-a`；另一个 lifecycle=`new`、server_alias=`none`，资源仍待比较。固定 OS、资源、地区状态详见 fixture，没有提供实际服务器或真实账号。

预期：保持 R-VPS；先区分工作区／出口，再询问已有或新建；保留两种不同事实，使指导分别走已有接入或新建比较，不以本机默认值覆盖。

实际：两种轨迹均为 route=vps/basis=explicit_choice/confirmed，路线题精确为 S01—S07。Q-S01 完整提示：“VPS 是 Claude 工作区，还是仅提供代理出口？”Q-S02 完整提示：“已有 VPS 还是新建？地区、系统和大致资源是什么？”两种不同的完整 Q-S02 事实信封均保存原输入值、reported、同一固定来源和时点、正确目标；不是把它们合并成“服务器就绪”。

答 S02 后的实际下一题均为 Q-S03：“是否能正常 SSH？有没有独立的控制台/救援入口？”未答精确为 S03—S07。后续完整提示依次是生产服务／未备份项目、远端数据与本机依赖、成本、终端／Remote-SSH／远程浏览器与维护。两种答案走同一后续问题集合是合理的共同需求，不等于购买步骤相同。代码负责保存生命周期，C 指导负责有条件的接入／创建步骤。完整轨迹终点仍为 vps。对已选 VPS 再提交 `accepted_default` 的实际结果为 `InterviewError: No current local default proposal to accept`，原状态不变。

### C：已有／新建和完整独立路线逐句审阅

| 实际指导位置 | 句子／分句的具体含义 | 与原条件的对应／判断 |
|---|---|---|
| SKILL 开始方式 3；routes 44 | 明确目标优先，独立路线且只展开选中者 | VPS 选择不能被本机建议覆盖，也不要求先读本机完整教程 |
| routes 36 首句；P1.1 第一句 | 先确认工作区／仅出口，出口-only 不装远端 Claude | 与实际 S01 对应；本案例明确工作区，故正确进入后续部署路线 |
| P1.1 第二句 | 确认语言／工具／资源／GUI／硬件／驻留 | 在创建前检查远端是否适合任务，没有拿“买服务器”代替可行性 |
| P1.2 两句 | 已有服务器优先只读接入，登记身份／用途／不可中断服务；不假定空机、不开破坏性工具 | 对 existing 输入给接入路线，避免无条件购买、重装 |
| P1.3 两句 | 新服务器先比较真实合规地区和所有相关费用，不能硬编码旧商家价格；免费工具不等于同意 VPS 费用 | 对 new 输入给选型／成本路线，未把“未有服务器”当购买授权 |
| P1.4 | 本机依赖或数据不能迁时说明阻碍并保留本机方案；只有用户改选才迁移 | 这是已发现不可行条件的说明，不能作为覆盖 VPS 明确选择的无条件默认 |
| P1.5 两句 | 开通／条款／支付各需确认，手册不创建服务器；不得虚假身份／地址绕过准入 | 新建分支的合法性与动作边界明确 |
| P2.1 | 本机核对服务器身份／SSH 指纹；未知时停止，不跳过校验 | 首次连接给出具体核对入口及失败出口 |
| P2.2 两句 | 本机保留既有私钥，新增持续授权单独确认；不复制到服务器或报告 | 既有认证复用不扩成秘密迁移 |
| P2.3 | 控制台先核实独立救援身份与恢复步骤，现有会话不算验证 | 提供断连恢复先决条件 |
| P2.4 两句 | 服务器核实用户／目录／sudo；日常最小权限；用户及安全配置变更另批 | 本机／服务器执行位置清楚 |
| P2.5 两句 | 保留原会话，第二会话验证后才收窄；云和主机防火墙分开 | 防止“完整部署”步骤断开唯一管理通道 |
| P2.6 及恢复 | 原配置和撤销方法先存私有批准位置；无证据阻塞安全写入，失联只恢复相关规则 | 有可执行的恢复方向，不以 SSH 能连当成全部准备通过 |
| P3.1 两句 | 确认项目和依赖；Claude 留 PC1；迁移明确文件／目的地／权限且保护未提交工作 | 完整部署中的开发准备与客户端接触分段 |
| P3.2 | 服务器测实际网络／DNS／地址族／代理层，不能用本机结果代替 | 独立服务器证据边界 |
| P3.3 两句 | 额外出口只有明确需求才比较；不同方案的覆盖／恢复／日志／费用影响分开 | 没有沿旧 S08 缺口让用户自行搜索，也没把额外代理变成必买 |
| P3.4 两句 | 指定精确应用／目的地／DNS／认证／失败行为，核验协议；按版本出配置，不执行可变脚本 | 提供有条件配置流程，当前缺事实仍保留未知 |
| P3.5—6 | 有救援和批准才应用，前后复验及检查现有服务；失败恢复和复验，未演练不能称 kill switch | 路线包含验收与恢复，不是仅部署清单 |
| P4.1—2 | 远端交接后才按当前兼容性安装；本机编辑器与远端扩展分开，需要访问／上传则授权 | 明确客户端运行位置和 PC1 范围 |
| P4.3 两句 | 按官方支持的设备码／回调流程，不改 URI／公开端口／搬令牌 | OAuth 指导有安全失败出口，无真实登录声明 |
| P4.4 三分句 | GUI 只在需要时规划，先核验认证／传输／访问限制和关闭，禁无密码公网 VNC | 临时远程浏览器是条件步骤，不强制长期桌面 |
| P4.5—6 | 无登录与登录后验证分开；异常回诊断，临时组件需正常关闭并检查端口／会话 | 完整路径包括退出，关闭窗口不等于服务已结束 |
| P5.1—2 | 本机核对主机／用户再接入；服务器核对目录；tmux 可选，断线先列现有会话 | 具体日常和续接服务器任务步骤，不重复启动任务 |
| P5.3—4 | 使用现有资源／日志视图；持续监控另授权；备份范围、费用、读回和一致性分别核对 | 有日常维护和备份验证，预算提醒不承诺硬上限 |
| P5.5—6 | 更新复验访问／路径／进程，恢复保护新工作；退役逐项确认迁出、端口和计费 | 包含更新、恢复、退役；停止实例不等于停止账单 |
| routes 196 两句 | 列完整生命周期所需证据并逐项标状态；不能仅凭 SSH 宣称远端产品可用 | 供将来部署验收的出口条件，当前没有冒认这些证据存在 |

T21 的完整路线指“选择后有独立、从准备至恢复的指导”，不是此测试已替用户实际部署。已有／新建原句所需的具体差异有 S02 输入和 P1 内容同时支持。

## T24：同任务选择保留，并在真正续接时先核实相关变化

### 修复前的精确反例

旧 `interview_flow.py` SHA-256 为 `b4f031b735073e07352fc4849bbf343a50a6a57239f08513e965eb0c889c35ac`，旧完整 replay SHA-256 为 `8732f875db1bb0bf29ff47503bddd9e752cd0c825501c825ed2fd09b3f16c05b`。对本页不变 fixture 的完整 VM/VPS，执行 `set_context(paused=True)` → `dumps_state(host_opt_in=True)` → `loads_state` → `set_context(paused=False)`。两条路线都输出 route 原值、basis=explicit_choice、question=null、G1 complete、G2 `{status:pass, conditional_plan_only:false}`，没有相关变化核实；事实仍来自原时点。旧辅助 `invalidate_facts` 只有宿主另行调用才生效，不能补足入口缺口。本次已再次用相同旧源码 hash 的冻结第五工作树只读回放核对该反例，没有修改旧树。

### 固定输入、完整预期、实际

任务仍为 `route-task`，目标/账号仍为 `route-device` / `route-account`，同一原 fixture。新的规范路径为：暂停 → 明确保存/加载 → `resume_interview(resume_id='route-resume')` → 当前用户变化报告。普通读档不产生中断事件，直接 true→false 清除暂停的旧绕过路径现在精确报 `InterviewError: Use resume_interview for an interrupted session`。

| 检查点 | 路线 / 选择依据 | 原题 / 复核提示 | G1 | G2 | 原事实 |
|---|---|---|---|---|---|
| 暂停并加载后 | 原 vm/vps / explicit_choice | 都 null | paused | blocked，条件建议 | 全部保留 |
| 显式续接，尚未回答 | 原 vm/vps / explicit_choice | 原题 null；独立 resume_review 提示如下 | complete | blocked / conditional_plan_only=true / reason=resume_review_required | 全部保留 |
| 当前回答 unchanged | 原 vm/vps / explicit_choice | 原题及复核提示均 null | complete | pass / conditional_plan_only=false | 值、来源及原 observation time 全部逐字相同；另记当前 reported 复核 |
| 当前回答 changed，VM V04 | vm / explicit_choice | Q-V04，clarification=true | partial，唯一 gap 为 Q-V04/stale | blocked，条件建议 | 仅 V04 stale，其他事实逐字相同 |
| 当前回答 changed，VPS S03 | vps / explicit_choice | Q-S03，clarification=true | partial，唯一 gap 为 Q-S03/stale | blocked，条件建议 | 仅 S03 stale，其他事实逐字相同 |

共同精确 scope 为 `[Q-C02,Q-C04,Q-C06,Q-C09,Q-N01,Q-N02,Q-N03,Q-N04,Q-N06,Q-OS03]`；VM 再加 V01–V06，VPS 再加 S01–S07。全部按此顺序固定。输出还精确包含 `kind=resume_review`、`event_id=route-resume`、六个 outcome `[unchanged,changed,unknown,declined,deferred,target_changed]`、`requires_action_authorization=false`，不是注册新问题 ID。

VM 完整实际提示，与手写预期逐字相同：

> 继续上次的虚拟机任务：还是原来的目标设备和账号吗；上次记录的系统/版本、语言和时间设置、网络/代理及此前测试、虚拟机资源、网络、共享和恢复条件、账号登录情况、使用地区/跨地区安排（无需详细地址）（含本路线已记录但尚未展开的条件项）有没有变化？可以说没变、具体变化、不确定、暂不回答或稍后再说；换了目标请先说明。

VPS 完整实际提示，与手写预期逐字相同：

> 继续上次的VPS任务：还是原来的目标设备和账号吗；上次记录的系统/版本、语言和时间设置、网络/代理及此前测试、服务器、SSH/救援、数据、费用和使用方式、账号登录情况、使用地区/跨地区安排（无需详细地址）（含本路线已记录但尚未展开的条件项）有没有变化？可以说没变、具体变化、不确定、暂不回答或稍后再说；换了目标请先说明。

变化后的完整原题分别为“虚拟机怎样联网，代理在宿主还是客机？”与“是否能正常 SSH？有没有独立的控制台/救援入口？”。完整题信封为原 ID/branch、stage=I5、postcontact=false、clarification=true、四个原 outcome 和 requires_action_authorization=false；完整 assessment 由 `expected_resumed` 手写断言。受影响事实仍保留旧值、source 和 `04:00:00Z`，只改 state=stale、blocker_reason=`Reported change since interview interruption`、clarification_count=0。原问卷 ID、route、basis、目标和未受影响事实不变。

### 组合、边界和错误路径的具体证据

`test_interview_resume.py` 的定向轨迹实际验证：

1. 普通 loads/连续 CLI `--input` 不产生 review 或改变下一题；真正 resume 在当前回复之前执行。未答时 G2 阻塞，G3 始终阻塞。既有 PC2 和独立 blocker 保留，不恢复保存许可。
2. pending/current unchanged/current changed/unknown/declined/deferred/target_changed 分开；后三类不自动重复复核，仍允许有限指导；目标变化须重新绑定或用户当前明确更正。重复相同 event/复核结果不使已刷新的字段再次 stale；新暂停不能重用已完成 event。
3. 已存的 N05、L02、L03、OS09、Z04 在后来激活条件时仍属于已展示的分组范围；C09 地区变化可选失效，无需详细地址。保护、权限、方案和目标套餐不在 changed_keys 白名单。
4. 空相关 scope 不增加门槛；空事件后新回答 common/route facts 可正常规划。旧 off-route V04 后来被选择时必须核实；真正当前回复与仅导入历史观测不同。Oct-1 旧观察被 Oct-2 历史观察替换，仍不能绕过 Oct-18 的续接核实；没有相对日期或 TTL 放行。
5. 完成购买不制造当前路线的新中断。原任务 reviewed 后若仍有从未纳入复核的旧 off-route S03，保存原复核来源/时间及该义务；两次 purchase completion 后改选 VPS，S03 仍触发 review。pending/unresolved 只剩过时 billing scope 时也保留 off-route 义务，target_changed 不被抹除；没有 off-route 义务的正常购买路径仍可继续。
6. 紧急停用报告先问 H01，暂不输出 resume prompt，处置后恢复；不得让复核阻止保护性分流。换 task/target/account 不继承他者的已复核状态，路线切换只核实仍待复用的相关旧事实。
7. CLI 输入缺 event、目标不匹配、无 input、坏 key/日期/来源/权限字段均清洁失败且不保存部分状态；changed review 后同轮当前答案可刷新该字段。拒答/延期重试没有循环；取消在保存前停止；source 不出现在 stdout；普通输出及保存语义保持。

这些是固定输入与结果断言，不是执行权限、真实用户当前身份或任意模型遵守契约的证明。宿主仍负责识别真正中断、取得当前用户报告、把历史证据送到正确接口。事件标签只去重，不是安全令牌。

### C：当前有效入口及每句契约的语义复核

| 实际指导句子 / 分句 | 与原 T24 的对应和本次判断 |
|---|---|
| D-SPEC §7.4 的同任务保留选择及相关变化句 | 原完整条件未改；本次 API 保留 vm/vps，不重问套餐或重置本机，只复核相关环境/版本和本次相关订阅 |
| SKILL 完整访谈入口新增句 | 清楚区分普通 `--input` 与真正中断 `--resume`，直接链接活动 intake 规则；不再把反序列化错误说成已完成续接核实 |
| intake 第 1 段三句 | 明确 Agent 必须调用入口、普通轮次不重复事件、禁止直接解除已暂停状态；与 CLI 实际顺序一致 |
| intake 第 2 段三句 | 保留事实时间、保护与接触历史，未接受本机仍未确认；事件标签不是授权/身份，新的中断有新标签 |
| intake 第 3 段四个分句 | 一次相关分组提示含已存条件项，不逐条审问 dormant 字段；只有相关订阅入 scope；不问地址/凭据；空 scope 无额外门槛 |
| intake 第 4 段的 unchanged/changed 句 | 当前报告与原观测分开，没变不改旧时点；变化只失效指定范围稳定 ID；路线、套餐、保护及权限不因环境变化被擦除 |
| intake 第 4 段未知/拒答/延期及目标句 | 不重复催问；有限建议仍可给；新目标需重绑，目标更正必须来自新鲜明确用户报告，不能静默当成恢复成功 |
| intake 第 5 段四句 | G2 与 G3/PC 分开；紧急分流优先；完成购买是同会话转换，仍保留未解决环境/目标义务；选择与复核不给操作许可 |
| intake 第 6 段各句 | 明确当前批次/无 observed_at 与历史导入接口边界；日期较新不是当前报告；渲染/读档/事件与复核重试不更新时间，无 TTL；CLI 先复核后当前答案且失败不部分保存 |
| contact-and-safety 新段逐句 | 真正中断先检查再规划，普通反序列化不重开；保留路线/PC2，保存不是授权；用户报告不升级原生证据；未知可有限指导且紧急优先；目标变化不能被购买清除；标签仅去重 |
| docs/interview-resume.md Boundary/API/Scope/Record/CLI/Rollback | 每个可选字段有必要性说明；旧 schema-1 无 marker 可读，旧 reader 拒新字段的兼容限制明确；历史导入不伪装当前回复；购买保留 off-route 义务与重复语义写明；回滚不能删除未解决 marker 来绕过规划边界 |
| routes 共用交接单 6、V3.3、P5.2 | 原变化失效、VM 暂停后复验、远端任务接入指导仍成立；它们继续作为后续操作指导，不被冒称通用访谈入口本身的核实证据 |

本页作者已重新阅读全文与上述分句，并且 T19/T20/T21 的原 C 表逐项仍与当前有效 SKILL/on-demand 链接、V1–V3、P1–P5 内容一致。该结论是完整语义复核，不以标题、关键词或方法数量替代。独立审阅已经检查 core/CLI/指导并纠正条件范围、旧时间导入及购买组合反例；最终原行验收由集成后的独立裁定完成，**本页不自行改变 T24 状态**。

## C 来源审阅：不让旧教程覆盖现行路线

1. D-SPEC §3.1 原句把 L0—L4 与路线正交，§5.4 明确新手 VM 不需先完成其他教程。这是 T20 内容采纳依据。routes 的“新手逐步卡片”和独立 V1—V3 没有加入技术门槛或购买前提。
2. D-SPEC §5.3 原句明确已有 VPS 跳过购买／创建、不假定空机；新建路线仍有预算和数据前提。这是 T21 的已有／新建语义依据。P1.2/P1.3 不把两种生命周期混为一次通用购买。
3. S01 的“小鸡＝VPS”“母鸡＝宿主”及“独服”等是术语来源。routes 61 只保留对初学者有帮助的概念；没有把历史商家／价格绰号当成选择依据。
4. S04 §4 把海外 VPS 写成“极低”“长期最稳”，§5.1 声称架构排除风控，§5.2 把购买特定实例／旧版本安装／美国身份与支付串成固定步骤。逐句对照后，这些**未被本次采纳为验收依据**：SKILL 末尾禁止免封收益／身份伪装；routes 40/51、P1.3/P1.5 要求实际资格、当前成本、真实身份及独立批准；T19/T20 没有被该旧推荐推成 VPS。
5. S04 §5.2 中 SSH、远端开发、tmux 的流程类别可以作为背景，具体实现、版本、购买、认证及执行仍服从 D-SPEC/D-ENV 的较新阶段边界。P2—P5 逐项说明位置、授权、救援及关闭，不直接运行原教程命令。
6. routes 200 明确 S08 未提供，不能声称复现其第 2—11 页具体命令。本次未制造该来源，也未以缺失附件假装精确命令已核验；采用的是仓库实际 D-SPEC 已确定的独立路线约束。
7. D-ENV §18.10 要求主客机／远端证据分别绑定；routes V2、P3 实际遵守。没有借 Linux 单元测试建立 Mac/Windows/VM/VPS 原生支持证明。

这些结论来自逐句阅读和语义对照，未把来源哈希正确、文件存在、关键词命中或标题数量当成 C 通过。没有实时核验政策／厂商版本／费用；本轮无 X 层声明。源材料原文没有编辑。

## 评审对象哈希、维护与回滚

以下 hash 只固定已阅读内容，不能代替以上 L/C 证据。任何相关来源／指导／实现变化，都需重新执行相应轨迹并重新评审，不自动沿用候选结论。

| 文件 | SHA-256 |
|---|---|
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/scripts/interview_flow.py` | `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e` |
| `skills/claude-guardian/scripts/interview_cli.py` | `003b9a31c01395be446e658d0ddac6a898172a9008981a302d7f8d8d5e324a91` |
| `skills/claude-guardian/references/intake.md` | `1d3d6f75788abafefe4a8ce8e9ca1c740b1f4b57656b350a4688c6629ac52dba` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/sources/S01-server-glossary.md` | `e2660c1b049d73e7a927594743f079cb0a5f10be9f72bad7928f10a5838bb68b` |
| `skills/claude-guardian/sources/S04-claude-guide.md` | `281b2881c5a016b5188aa71c1e7162e1742c98170d9685f2a4e24503ee7a5992` |
| `tests/fixtures/acceptance-routes-rebuild.json` | `073ad74ba195fd1c72bcab61887f24f1ce5cbeaef6ff6036d9ff76a713154a80` |
| `tests/test_acceptance_routes_rebuild.py` | `893329472b97152d69d41d3b352c90e9bddc8dd93d812d334edc1efbebc5428b` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `docs/interview-resume.md` | `0c8325daad9e5d56093819068001617024c226cd934aca8fd195f2c280210691` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |

本批修改 interview_flow/CLI、SKILL 一句、intake/contact 指导、原 route 回放测试、本页及三个既有验收行的 evidence hash；新增 focused resume 测试和 API/兼容说明。原 fixture、来源原文、原验收条件均未改。代码与指导须一起回滚，并同步恢复准确证据 pins/hash；旧 reader 不认识可选 resume_review，不能通过删掉未解决状态绕过核实，详见 docs/interview-resume.md。完整套件、Node、编译与打包另附集成记录，本页不以定向结果代替它们。


## Tenth-batch active recovery guidance re-review

The SKILL entry changes only its independent POSIX recovery paragraph: v2
witnessed prepared reconciliation/restoration is separately authorized, legacy
prepared and conflicts remain non-mutating, and production native admission
stays closed. Independent content review compared this exact delta against
T19/T20/T21/T24 and found no change to route selection, staged presentation,
retained facts or resume review. All six exact route replays and 33 resume tests
passed again. The route implementation and fixtures are byte-identical to ninth.
Only the reviewed SKILL pin is refreshed; the original L+C acceptance limits and
five accepted original cases are unchanged.


## Eleventh-batch route and resume preservation review

Four relevant source pins changed for the bounded unnamed-plan identity repair
and the scoped recovery capability correction. Independent review re-ran 166
intake/interview/CLI/resume/migration/route tests, including all 33 resume cases.
The complete prior route replay is byte-identical. T19/T20/T21/T24 retain their
full original L+C conclusions: default-route acceptance, VM/VPS independence,
novice lifecycle guidance and the resume contract are unchanged. The new CLI
consumption rule is restricted to a genuinely pending identity clarification.
The contact paragraph preserves phase/permission boundaries while distinguishing
read-only reconciliation from separately authorized POSIX recovery writes.
These reviewed pin updates do not accept the new intake cases by themselves.


### Twelfth-batch preservation review

The task-intent and exposure-triage changes in interview_flow.py and active intake
guidance were independently re-reviewed against all original conditions on this
page. The unchanged route replay remains `8e2a95d3` (prefix), and the eleventh
intake replay remains `67406ca1` (prefix); complete hashes remain in their original
evidence sections. The 181 focused checks passed. New emergency postponement is
a derived projection, not user deferral or action authorization. Only these two
reviewed file pins are refreshed here; no native or model-integration proof is added.


### Fifteenth derived-reference preservation review

On 2026-10-18 the sanitized case reference and its two active links were
independently reviewed against this page's full original conditions. Existing
case replays remain unchanged. The host-library/CLI clarification grants no new
capability or authorization; historical single-device observations do not become
current native evidence. Only reviewed affected file pins above were refreshed.
The review reran 182 relevant offline tests and 145 interview tests with no skips,
and compared five complete case replay outputs and both release archives.

Sixteenth-batch preservation review (2026-10-18): the original case conditions
and layers remain unchanged. Fresh replays preserve all prior members; relevant
reports add only the exact fixed, non-authorizing traffic-policy projection.
Complete objects are therefore not claimed byte-identical to the fifteenth
batch. Shared policy, migration-consumer compatibility, static rendering and
package dependencies were independently reviewed before these pins were updated.
No native enforcement or new original-case acceptance is inferred.

### Eighteenth scoped cleanup preservation review

Independent review reran the original case's affected logic/guidance and package
paths before refreshing these dependency pins. Existing route, intake and
task-scope replay objects remain byte-identical to the seventeenth batch. New
selected-device history and explicit C5 intent do not infer the current account's
status or grant action permission. Callable quarantine/recovery is separately
scoped and reviewed; default interview/CLI and existing contact/authorization
safeguards remain. No new original cleanup/native case is accepted here.


### Twenty-ninth subscription-repair preservation review (2026-10-18 UTC)

The published twenty-eighth tree and frozen six-file repair integrated into the twenty-ninth tree were compared by file bytes, not local Git HEAD. T19/T20/T21/T24 retain their unchanged original L+C requirements. All six existing route tests pass on both trees; each full --replay projection ran twice per tree and all four stdout byte streams and parsed complete objects are equal, SHA-256 dd128334df685184abf60fa6c27f24bfed166aca2917ccaea3885768f4bc552f. This compares the fresh published baseline with the repair; the earlier 8e2a95d3 digest remains a dated pre-traffic-policy observation and is not relabeled as the current output.

The changed intake/resume instructions were read against D-SPEC §3.1/3.3, §5.0–5.7, §6.13–6.14 and §7.4, and D-ENV §18.4–18.10. Ordinary absent/shown/unknown route answers remain default_proposal/unconfirmed with G2 blocked. The narrow billing_issue explanation can omit an unrelated deployment questionnaire without confirming a route; returning to an environment/network/purchase task restores that route requirement. Explicit VM/VPS choices, novice depth, existing/new server facts and independent V1–V3/P1–P5 guidance are preserved.

The current resume contract has two additions to the historical C table: retained Q-C13 is an account-bound current-plan fact, separately reviewed even while its explicit plan-dependency condition is dormant; supplied observed_at is a historical import by default, with strict current_reply=True reserved for a genuinely current host-normalized answer at its real time. That declaration is neither verified freshness nor authority. Changed/unknown/declined/deferred/target-change review still blocks the dependent plan; no route/default reset occurs. Unresolved Q-C13 cannot become fresh through a new task/device, historical import or account change. Optional purchase_completion metadata deduplicates a reported completion, is not a payment or entitlement grant, and an exact retry preserves subsequent task/route/plan/contact history. Old strict readers may reject these optional schema-1 additions and must be upgraded rather than stripping obligations.

The integrated 207 interview tests, 43 workflow tests, 24 contact-epoch tests and two portability tests pass with no skips. Six additional independently authored interaction methods, including VM/VPS/default-route and local-egress compositions, pass twice under fail-fast I/O sentinels; their full-state replay is deterministic, SHA-256 b999541701067f90029b3a00ca72acd761b013f27d7915e24697b53d0d56d3cc. G3 remains blocked, save/export permission is not restored, and reviewed same-task PC2 history is retained. Only the three reviewed changed source pins in this page are refreshed.

This is preservation of the unchanged original requirements/layers, not acceptance of any additional case. Normalized synthetic host facts and current active guidance were reviewed; no model dialogue, native device, live service contact, payment, deployment, OS isolation or actual cleanup is established. The trusted host remains responsible for truthful task/target/applicability, current replies and genuine separate authorization.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.
