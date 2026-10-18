# T53 / T74 / T81：完整问诊轨迹与内容复核

日期：2026-10-18。基线：冻结 tenth；本页对象：eleventh 的归一化宿主接口、离线 CLI 和当前 Agent 指导。这里提供三个原案例的 L+C 候选证据，最终状态见 `docs/acceptance-rebuild-ledger.json`；本页不自行改变案例状态。不是模型自由文本端到端测试、原生设备验收、当前套餐/价格核验或全项目完成声明。

## 1. 原条件与证据层不变

原文来自 `D-SPEC-v0.1.10.md` §11（原行 1112、1133、1140）；`implementation-tracker.md` 对三者均规定 **L+C**。L 是纯逻辑/对话轨迹/夹具；C 是逐句内容与来源审阅，不是依赖标签、关键词命中或测试计数。

| 原 ID | 完整场景 | 完整通过条件 | 本页证据 |
|---|---|---|---|
| T53 | 用户愿意按本机默认建议进行 | 记录 `accepted_default`，不再增加一次无意义确认；执行授权仍单独处理 | 当前本机候选 → 接受 → 完整余下 PC0 路径；G3/接触/保存边界；路线与权限指导逐句复核 |
| T74 | 明确第一次准备订阅 | 问 Q-C08 目标套餐；不问 Q-C07、Q-P02、Q-A06 或旧套餐/旧购买渠道 | Apple（含礼品卡）、Google、网页三个完整适用分支；PC0 延期及后续调度；题目全文与间接旧账单措辞审阅 |
| T81 | 一句话说“第一次开通，Mac，本机，套餐已选好” | 同时吸收订阅阶段/系统/方案/目标套餐；只问真正缺口，不顺序重问 | 原句自身四事实、全部 24 排列、完整缺口顺序、一次身份澄清和退出；另有明确命名套餐的 24 排列对照；宿主提取指导审阅 |

依据同时包括 D-SPEC §5.0、§6.3—6.4、§6.8—6.9、§7 的方案字段语义，以及 D-ENV §18.4—18.6。没有把原句改成“Pro 已选好”，没有增加问题 ID，没有修改原表 218 行或证据层。

## 2. 输入、预期、实际与复现方式

`tests/test_acceptance_intake_rebuild.py` 中的 `FOUR`、`PROMPTS`、`PLAN_PROMPT`、`expected_question`、`expected_literal_assessment` 和固定问题序列是独立写出的预期，不从运行时问题表生成。每一轮比较完整问题对象（ID、分支、阶段、postcontact、中文全文、clarification、允许退出及 requires_action_authorization），再提交固定答案；意外多问、少问、换序或换词都会失败。四事实比较完整 envelope 与完整初始 assessment，逐项检查上下文、来源、时间、账号/设备角色及不修改输入。`--replay` 只导出实际轨迹，不用于生成测试预期。

全部数据都是合成别名。纯逻辑测试固定时间 `2026-10-18T05:00:00Z`，并令文件打开、socket、子进程和 shell 调用抛错；CLI 测试只在专用 TemporaryDirectory 保存合成状态和答案，并真实启动本仓库 Python CLI。没有用户设备、网络请求、Claude 接触、支付或配置动作。`contact_phase='PC2'` 仅用于检查后置题调度，G3 仍 blocked，不能据此宣称通过真实 PC-G1/PC-G2 或获得登录/付款许可。

### T53：接受默认候选，只选择一次

固定输入：首次订阅，Mac、网页用途、明确的合成目标套餐 Pro、无停用自述及已注册自述；此时下一题全文为“用本机、虚拟机、VPS，还是先比较？本机默认建议。”随后输入 Q-C05=`accepted_default`，来源 `synthetic:T53-accept`。

预期和实际一致：保存原值 `accepted_default`，route=`local`，route_selection_basis=`accepted_default`，route_confirmation=`confirmed`，不变成 explicit_choice 或默认推断；原输入对象不变。直接进入 Q-C06，不再要求一次“确定本机吗”。固定余下序列如下，全部中文全文在测试和实际 replay 中逐项比对：

`Q-C06 → Q-C09 → Q-N01 → Q-N02 → Q-N03 → Q-N04 → Q-N06 → Q-P03 → Q-P04 → Q-P06 → Q-P07 → Q-W01 → Q-W02 → Q-W03 → Q-L01 → Q-L04 → Q-C12 → Q-Z01 → Q-C10 → None（PC0）`

PC0 后只留下 Q-W04=`requires_contact_gate`。整个过程 G3 都是 `{status: blocked, reason: Interview answers are not specific action authorization; action and contact gates must be checked separately}`；contact_phase 仍 PC0，private_save/export/public_export 都 false。重复同一带原时间的接受记录不改状态。反向对照：已明确 local/vm/vps/compare 不是待接受的默认建议，再提交 accepted_default 原子拒绝；inferred 的 accepted_default 不确认路线。这里没有测试实际动作执行器，执行授权隔离由返回状态及 C 层具体规则共同证明。

### T81：原句中“已选”不等于已提供名称

原句：**第一次开通，Mac，本机，套餐已选好**。宿主归一化输入精确为：

```json
[
  {"question_id":"Q-J01","value":"first_subscription"},
  {"question_id":"Q-C02","value":"macos"},
  {"question_id":"Q-C05","value":"local"},
  {"question_id":"Q-C08","value":"selected_unspecified"}
]
```

四个 envelope 的共同字段为 state=`reported`、source=`synthetic:literal-T81`、observed_at=`2026-10-18T05:00:00Z`、applies_when=`current task and target`、required_for=`[intake, plan]`、sensitivity=`low`、clarification_count=0、blocker_reason=null。Q-J01/Q-C08 的 subject_ref=`intake-account`，Q-C02/Q-C05 的 subject_ref=`intake-device`；value 如上。全部 24 种输入顺序产生相同四事实、相同完整 assessment 和下一题 Q-C01；订阅状态为 `none_reported`（原来源/时间），payment_intent=`new_subscription`，本机选择为 explicit_choice。已知的订阅阶段、Mac、local 都不重问。

Q-C08 保留“已经选择”的事实，但名称仍缺失，G1 精确列 `target_plan_identity_missing`，G2 blocked/conditional_plan_only=true。固定缺口路径如下：

`Q-C01 → Q-OS03 → Q-C08（身份澄清）→ Q-C03 → Q-C04 → Q-C06 → Q-C09 → Q-N01 → Q-N02 → Q-N03 → Q-N04 → Q-N06 → Q-P03 → Q-P04 → Q-P06 → Q-P07 → Q-W01 → Q-W02 → Q-W03 → Q-L01 → Q-L04 → Q-C12 → Q-Z01 → Q-C10 → None（PC0）`

身份澄清的完整预期与实际都是：

```json
{"id":"Q-C08","branch":"core","stage":"I2","postcontact":false,
 "prompt":"你已经选好套餐；具体是哪一个套餐？","clarification":true,
 "allowed_outcomes":["reported","unknown","declined","deferred"],
 "requires_action_authorization":false}
```

这是补真正缺失的身份，不是重新问是否选好、让用户重走比较或猜套餐。本固定后续回复明确回答 `Pro`，来源改为 `synthetic:followup`；这个 Pro 只来自后续答案，不归因于原句，也不是当前可售/适合购买的结论。回答后 Q-C08 count=1，其余原句事实和来源不动；PC0 最终只剩 Q-W04 接触门禁。完整 before/after 反例另在下一节。

边界轨迹：

- 普通 Q-C08 已送达后才收到“已选好”，仍允许一次身份澄清；普通询问不预先消耗这一次
- direct host 实际送达后调用 mark_asked；重复 render/load 保留原 envelope 和时间，不能消耗或重新获得次数
- 已消耗后再报 selected_unspecified，不再次追问；身份仍 unresolved，不能把“停止追问”伪装成 G2 通过
- 明确 unknown/declined/deferred 以现有空值字段替换契约保存，count=1，进入 Q-C03，缺口分别保持对应状态；本页不声称替换后仍保留先前完整 selection 值
- 后续明确命名正常解决身份。另一个明确说出 Pro 的四事实回复在全部 24 排列都跳过 Q-C08；它只是对照，不取代原句
- 已有订阅且只做 environment 时 Q-C08 不适用；紧急 credential_exposure 优先 Q-H01 / emergency_deferred

### T74：全部相关渠道，不偷换为“是否已有权益”

固定初始输入 Q-J01=`first_subscription`，来源 `synthetic:T74`。预期和实际均记录 current_subscription=`none_reported`，不声称查过账单。第一缺口是系统和用途，随后目标 Q-C08；原文的“问 Q-C08”不等于绕过既定 OS/用途顺序。共同前段：

`Q-C02 → Q-C01 → Q-OS03 → Q-C08 → Q-C03 → Q-C04 → Q-C05 → Q-C06 → Q-C09 → Q-N01 → Q-N02 → Q-N03 → Q-N04 → Q-N06 → Q-P03 → Q-P04 → Q-P06 → Q-P07`

每条路径都有固定“合成用户自述”答案，只在 Q-P06 选择渠道；苹果路径还显式设置 gift_card/buying_gift_card=true 以实际展开适用礼品卡分支。每条继续渠道 PC0 题，再继续同一保护尾段：

| 渠道 | PC0 渠道题（按实际顺序） | PC0 后仅延期这些题 | 合成 PC2 后顺序 |
|---|---|---|---|
| Apple | Q-A01、Q-A02、Q-A03、Q-A07、Q-A09、Q-A10 | Q-A04、Q-A05、Q-A08 | Q-A04 → Q-A05 → Q-A08 → None |
| Google | Q-G01、Q-G02 | Q-G03、Q-G04 | Q-G03 → Q-G04 → None |
| 网页 | Q-W01、Q-W02、Q-W03 | Q-W04 | Q-W04 → None |

共同保护尾段为 `Q-L01 → Q-L04 → Q-C12 → Q-Z01 → Q-C10 → None`。在 PC0，延期原因都是 requires_contact_gate；人为设定调度阶段并提供后置合成报告后，完整 assessment 才是 I6/G1 complete/G2 pass。G3 仍 blocked，保存/导出同意仍 false。完整轨迹没有 Q-C07/Q-P02/Q-A06，适用问题集合也没有这三者；更重要的是，全文和下述 C 审阅确认没有换措辞问旧套餐/旧渠道。

额外负对照：只有显式 subscription_conflict=true 才加入 Q-P02/Q-A06，Q-C07 仍不存在。这是原规范允许的实际冲突分支，不能反向当作无冲突首次用户的默认问卷。API/组织/企业在本场景没有明确需求，故不加载；指导明确仅按真实需求加载，不是漏掉一套人人必答的支付表。

## 3. 缺陷复现、最小修复与兼容性

冻结 tenth 的 flow SHA-256 为 `9a19073d243adc2f252c4fbfb8383bb95fa605d829400798189571ad59e6109a`，CLI 为 `62cd96d848f896889ed3142e51f86412d771907b012955c051aa768e101bf8d3`。

**缺陷一，原句失去真正缺口：** 原实现把 reported Q-C08 的任何字符串当作解决。用同一四事实输入及同一系统/用途补充后，旧实现直接问 Q-C03；把其余适用问题答完后，Q-C08 仍是 selected_unspecified/count=0，却得到 G2 pass。先写的规范测试真实失败（日志 `T81-failing-first.log`）；新实现新增一个保留字符串谓词、一个缺口 reason，并复用既有一次 clarification_count，实际输出上列身份问题。`T81-before-after.json` 保存两个版本完整状态和问题序列，旧/新最终 G2 pass 的差别可直接看到：新版本必须先接收明确的后续名称才能通过。

**缺陷二，CLI 只输出而不消耗：** 修复核心后，将待澄清状态保存，CLI 读入同一 selected_unspecified 当前答案又输出 Q-C08，count 仍 0，导致重复循环。规范子进程测试先失败（`T81-cli-failing-first.log`）。现 CLI 仅当此前下一题正是 reported/observed marker 的 Q-C08 身份澄清，而且完整有效批次中确实有 Q-C08 回答，才对原状态 mark_asked 后应用该批次。先验证整个批次，故错误后半项不能留下部分事实或已消耗次数。它不扩展其他题目的送达语义。

六个 CLI 测试包括单项/批量重复 marker、明确命名、unknown/declined/deferred、无关答案、错误批次、普通已显示题、stale-marker、render/load/retry。完整错误输出固定为 `{status: blocked, code: INVALID_OR_UNAUTHORIZED_INTERVIEW_IO, action_executed: false}`，exit=2，无输出状态文件，输入原字节不变；错误私有文本不回显。单项/批量匹配回复进入 Q-C03/count=1；render 与无关答案仍 Q-C08/count=0。CLI 的 `--output` 是测试中独立明确的私有保存 opt-in，并非路线接受附带的许可。

**保存状态兼容性：** 沿用原 schema、字段、稳定问题 ID 与 0/1 clarification_count，旧状态仍能加载。保留字符串 selected_unspecified 现在有明确语义；如果过去保存过这个字面值，它将重新显示为身份缺口而不是已知名称，这是有意的安全纠正。其他明确名称不改变；不把该 marker 当套餐枚举或当前产品目录。已有有效命名事实要由宿主复用原来源/时间，不因后一句“已选好”而覆盖成 marker。历史导入/普通读档不刷新时间；真正 resume 的现有契约不变。回退需同时回退本批 flow、CLI、intake 指导和测试，并撤销依赖新契约的候选证据，不能单独撤回指导而保留新语义。

## 4. C：逐句含义、可用入口及反例审阅

这里审阅的是当前生效文字，不是仅检索 required phrases。表中逐句/逐步骤解释为什么满足原条件及不扩张权限；原文文件由下方哈希固定。

| 当前文字位置 | 逐句/逐步骤复核与案例对应 |
|---|---|
| SKILL 核心规则 2、3、4、5 | 规则2先复用已有事实，再补缺口；首个缺失业务问题为订阅阶段，不重复已知答案。规则3本机只是建议，VM/VPS独立，已有明确目标优先。规则4按需读取 intake，Q-C07永久停用，不换名恢复；首次无冲突跳过旧套餐/旧渠道。规则5保持PC0不接触/不启动/不登录，不因问诊完成就行动。对应T53/T74/T81全句。 |
| SKILL 完整 interview_cli 入口、批量答案段、示例后节奏句 | 明确使用完整95-ID状态化入口，旧八字段命令不能冒充本场景。answers列表表示一轮全部事实；宿主提取、脚本不猜未给出的套餐；整批失败不部分保存。accepted_default只接受当前本机候选，不重复确认，不覆盖VM/VPS，不授予动作/保存权限。“已回答就跳过”及一轮一个决策支持不顺序重问。intake链接使新 marker 规则是可被 Agent 实际读取的执行指导。 |
| intake Scheduling 第1—3段 | 先读既有事实；吸收一轮所有有效字段、跳过已知/不适用；含糊只澄清一次后允许未知/拒答/暂停。正常阶段顺序和紧急抢占有明确说明。首次自述只是none_reported，不冒充账单核验；Q-C08只表示目标，P02/A06只在相关账单任务或真实矛盾触发。对应完整T74及T81，而非四个字段计数。 |
| intake 新“套餐已选好”段（逐句） | 第1句只在名称缺失时保存reported selection并吸收其他事实，禁止猜Pro/Max或改为未决定。第2—3句只补一次“具体哪一个”，保留已选含义而不满足身份/G2。第4句分别规定直接宿主mark_asked及CLI完整有效匹配回复的消耗时机，普通/无关回复不消耗。第5句render/load和重复marker不重启。第6句后续名称可解决，明确未知/拒答/延期沿用空值替换而非伪保留。第7句名称早已有效则保留旧来源/时间。末句限定宿主归一化、无NLP/可售/购买授权宣称。 |
| intake local proposal 段、Fact states/G1—G3、Core/OS索引 | accepted_default与explicit_choice/task_context明确分离，未接受仍default_proposal。G1缺口和G2条件计划不能伪装成G3操作。Q-C05接受建议即可；Q-C08目标套餐，Q-OS03补版本而非重问Mac。C06仅已有注册相关，C07永久墓碑，不通过别名恢复。 |
| routes-and-platforms R-LOCAL 六步、M01选择题、执行卡约定 | 本机标题明确never silently selected；第1步先访谈/获准读取，第2步列缺口，第3步讲门禁，第4步必须具体交接和批准，第5—6步日常/恢复规划，均未把“选本机”当安装或网络变更。M01明确“接受本机建议即可，不考察技术水平”，不增加同义确认或必修VM/VPS。执行卡没有批准只交付卡片，路线不批准费用或部署。对应T53“不额外确认”和独立执行授权。 |
| contact-and-safety Phase、Permissions、Persistence | 问题答案、计划接受、宿主权限、OS权限、接触和付款分别记录；默认、沉默、取消及接受路线不授其他许可。PC0仅现有材料/离线规划；PC1和PC2都有独立范围和批准。保存先问，续接不恢复权限。T53/T81中状态值的技术事实与实际动作边界一致。 |
| accounts-and-payments 开头、PC0、A1、B1 | 先复用首次/重订/当前状态；有账号不等于有订阅。目标套餐优先，未决定才比较功能/预算；没有用“是否已有付费权益”替换C08。当前价格、资格和购买可行性另待官方核验；测试Pro不成为推荐。A1的登录可用性和异常分流不调查旧账单或账号归属。 |
| intake Payment索引 + accounts Apple 7条及B2十步骤 | A01—03只问可用设备、登录验证和商店地区；不是账号归属。A04/A05延期查官方入口及本次目标Claude匹配，不调查历史计划。A07卡种/地区状态、A08当前结账覆盖、A09本次卖家、A10未来续费均与本次准备相关。Apple第7条明确A06只相关旧账单或真实冲突。B2第10步只有实际改区才展开其他Apple余额/订阅，不能把它变成首次Claude旧订阅问卷。B2第9步的原渠道对账只在真实付款后缺权益出现，不是提前调查。原运行时Apple标题很短，本C层审阅了完整执行卡，不能用标题词命中代替。 |
| accounts Google段及B3五步骤 | G01/G02设备、Google验证/Play地区是渠道前提；G03实际目标入口延期；G04核对本次服务账号，不等于Q-C07归属问卷。G05未来续费与P07去重。B3第4步只在恢复购买/重复扣款等实际冲突查看旧账单；第5步是已发生付款异常的分流，未提前触发。 |
| accounts Web段及B4、B5—B7 | W01类别/发行地区、W02如实账单、W03线上/周期能力与真实拒付提示、W04本次总额/账期，均非旧套餐/购买渠道调查。B4拒付后的待处理核对是实际症状分支；B5为具体购买独立批准；B6在购买后或续费/升级/取消才核对相应旧渠道；B7只有已扣/重复扣款等真实观察才对账。API/组织/企业另以明确需求触发，不普遍追加长问卷。 |

结论：在已明确的归一化宿主 + 当前指导范围内，三个原条件都有完整 L 轨迹及相应 C 依据；不存在将 T81 字面“已选好”直接解释成 Pro/Max 的捷径。这里没有证明任意模型在所有自然语言表达下都能正确提取；Agent文字指导的合规性属于C，不标成已执行NLP集成。

## 5. 命令、完整回执与结果

在 eleventh 根目录：

```sh
python -B tests/test_acceptance_intake_rebuild.py -v
python -B -m unittest discover -s tests -p 'test_interview*.py' -v
python -B tests/test_acceptance_routes_rebuild.py -v
python -B tests/test_acceptance_intake_rebuild.py --replay > /tmp/guardian-intake-eleventh/intake-replay.json
```

实测：新案例/CLI **15/15**（1.583s），原 interview **145/145**（4.455s），原 route **6/6**（0.395s）。独立复核另运行同一166项通过（6.228s）；旧路线完整 replay 字节仍是 `8e2a95d3…`。这些数字只说明所列范围执行结果，不代替上文原条件论证。全项目聚合、打包、发布与 ledger 集成另由对应总回执记录。

完整项目交付回执位于 `/tmp/guardian-intake-eleventh`（父级交付归档复制）：

| 完整文件 | SHA-256 / 用途 |
|---|---|
| intake-replay.json | `67406ca122eea39f62e4fbb881cc1040a488a4796e487fa5235a5591b972bc87`；650648 bytes，三原ID、四事实完整envelope、24+24排列、全部问题全文及最终状态；连续两次导出字节一致 |
| T81-before-after.json | `ea529a7816dda0b9b81e3737d8b9680dcd5b5f96ed16192bea4b6fef7a64d20a`；同一输入在tenth与eleventh的完整状态/问句 |
| CLI-exact-trace.json | `a087b00658a808d79f22d1ececc9031e83650ffc383876c39283316413b6bdaf`；固定时间CLI公共输出及私有保存状态，含render/单项/批量/命名/三种退出/无关/错误批次 |
| T81-failing-first.log / T81-cli-failing-first.log | 两个真实修复前规范失败，不删除或当成当前失败隐藏 |
| intake-tests.log / interview-regressions.log / route-regressions.log | 完整当前运行日志 |
| make_counterexample.py / make_cli_trace.py | 独立回执重现脚本，参数为eleventh根目录；只用合成临时文件 |

## 6. 冻结阅读与执行文件

下表固定本次C审阅与L测试所用字节。修改任一相关文件后须重新审阅/回放；不能只刷新哈希。tracker/ledger属最终集成状态，故不把它们作为不变运行输入固定。

| 文件 | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/scripts/interview_flow.py` | `f1779626ef5fca0fae9a16ab0d7c64781ebe696f7b63d92aba260238584b9b42` |
| `skills/claude-guardian/scripts/interview_cli.py` | `003b9a31c01395be446e658d0ddac6a898172a9008981a302d7f8d8d5e324a91` |
| `tests/test_acceptance_intake_rebuild.py` | `e26a26ee3b3d0ba93270787f8dbd8022ed11adb2fbbb0f1229df8f1aef57245a` |
| `tests/test_interview_flow.py` | `2e9fa3e886262c62c1a11bbcb0ebda4f02356d03be595de6f9bac804d31b1d4a` |
| `tests/test_interview_cli.py` | `a3cbd2c8332d50e6c49fee61ced2bb9c10295b7a3393b39b6de2e89a9a37be4d` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `tests/test_interview_migration.py` | `6c4e6bf32875b83ea179ffc836f140141f161240b478b359b62b304767063618` |
| `skills/claude-guardian/SKILL.md` | `9fcf19d0b58f5f2d09c6c7251dea1601315763883c544a0c36ac82f99f86466e` |
| `skills/claude-guardian/references/intake.md` | `f736f42bf9f962ee1a945452ccf9c3497a849aaa08097ab261b8cdad4bc1e4a7` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `cf16e85bfbe2a9ea6a2cc51d88b9f82c85eab29248f289c3ae3990c15cda6cb9` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |


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
