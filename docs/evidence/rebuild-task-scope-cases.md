# T34 / T78 / T43 / T48：任务范围、未知答案与事故优先级

2026-10-18，twelfth，基线为冻结 eleventh。本页提供四个原案例的完整 L+C 候选证据，最终状态见 `docs/acceptance-rebuild-ledger.json`；本页不自行改变状态。测试范围是归一化宿主接口、离线 CLI 和当前 Agent 指导审阅，不是任意模型的自然语言分类、原生设备或真实凭据处置验收，也不是全项目完成声明。

## 1. 原条件完整保留

来自 D-SPEC-v0.1.10 原行1093、1137、1102、1107，tracker 对四者均规定 **L+C**。L 为逻辑/对话轨迹/夹具，C 为内容逐句审阅，不能用数量或关键词匹配替代。218条原条件和证据层未改。

| ID | 原场景 | 原通过条件 |
|---|---|---|
| T34 | 方案题未回答或用户跳过 | 默认候选不升为已确认；只允许受限比较/初步建议 |
| T78 | 只说“我是老手/用过” | 当前订阅保持 unknown，精简澄清 Q-J02；不把熟练程度当作付费状态 |
| T43 | 开场明确已有订阅，只查本机环境 | 不问新目标套餐或支付渠道；记录本次未处理购买，不将其当成订阅准备默认场景 |
| T48 | 访谈中出现凭据泄露/紧急停用 | 最小必要分流优先，其余主题标延期，不以付款问卷拖延保护 |

同时完整审阅 D-SPEC §5.0、§6.3—6.6、§6.8、§6.11—6.13 与 D-ENV §18.4—18.6：已有事实复用、有限澄清、任务与订阅/熟练程度独立、事故抢占及动作/接触权限分离。排期审计文件是线索，不替代原条件。

## 2. 固定输入与完整断言方法

`tests/test_acceptance_task_scope_rebuild.py` 使用人工写出的 `FOUR`、完整中文 `PROMPTS` / `EXPOSURE_REMAINING`、固定问题序列、`expected_urgent` 和完整阶段对象；共用普通问题全文来自已冻结的 `test_acceptance_intake_rebuild.py`，不是从运行时表取预期。每一轮比较完整问题对象，包括分支、阶段、postcontact、clarification、允许结果及 requires_action_authorization。状态回执保存所有字段，包括曾被忽略的 purchase_intent，不通过删去矛盾字段造绿。

合成目标/账号/任务分别是 scope-device、scope-account、scope-task，时间固定 `2026-10-18T06:15:00Z`，来源 `synthetic:task-scope`。纯测试对文件/socket/子进程/shell设置失败哨兵；两个 CLI 测试只在专用临时目录读写合成状态并启动仓库 Python CLI。没有真实配置、秘密、网络、Claude接触或付款。`--replay`导出完整实际对象，不生成测试预期。宿主把原句归一化的规则在C层明确，不能声称脚本自己理解了自由文本。

## 3. T34：未答与跳过都没有选择本机

固定前段：首次订阅、Mac、网页用途、明确的合成目标套餐、无停用自述、已注册。下一题完整输出：

> 用本机、虚拟机、VPS，还是先比较？本机默认建议。

原状态未送达/未答时重复render仍是该题，facts无Q-C05。送达但未答（仅mark_asked）、unknown、declined、deferred，以及主动compare五种轨迹分别测试。后四者保留各自完整fact envelope，不把null解释成false或接受。送达之后只继续真实缺口，不再次逼问Q-C05。

五条轨迹都完整走完固定余下序列：

`Q-C06 → Q-C09 → Q-N01 → Q-N02 → Q-N03 → Q-N04 → Q-N06 → Q-P03 → Q-P04 → Q-P06 → Q-P07 → Q-W01 → Q-W02 → Q-W03 → Q-C12 → Q-Z01 → Q-C10 → None`

最终预期与实际：route_selection_basis=`default_proposal`，route_confirmation=`unconfirmed`；route通常为local候选，compare变体为compare候选。没有local/VM/VPS资源题，不暗中进入部署。G1 partial，Q-C05分别保留unasked/unknown/declined/deferred/route_unconfirmed；另有Q-W04 requires_contact_gate。G2 blocked/conditional_plan_only=true，G3 blocked，PC0，保存/导出同意false。读档后结果与事实原样不变，不自动补答或重获许可。

“只允许受限比较/初步建议”由这项G2状态和下文当前指令共同支持：未确认不得给完整可执行方案或按本机部署，可解释比较、缺口和最小查证方法。这里没有执行部署来检验拒绝路径，也不把一个未调用的执行器说成已测试。

## 4. T78：经验不是当前订阅

分别保留原句“我是老手”和“用过”。宿主明确归一化为 `ambiguous_experience=true`，没有创建付费事实。两者初始facts为空，journey=unknown，current_subscription精确为 `{status: unknown, source: null, observed_at: null}`，payment_intent=unresolved。

完整Q-J02预期与实际：

```json
{"id":"Q-J02","branch":"core","stage":"I1","postcontact":false,
 "prompt":"你说用过/是老手：现在还有有效订阅，还是准备开通/重新开通？",
 "clarification":false,"allowed_outcomes":["reported","unknown","declined","deferred"],
 "requires_action_authorization":false}
```

这是针对含糊原句的一次业务澄清；`clarification=false`是既有冲突/过期重试位，不代表再问一轮。送达后若明确unknown/declined/deferred，保存对应空值fact及source/time，current_subscription继续unknown；下一题Q-C02，重复调度/读档不重开Q-J02，G2仍blocked。它没有要求旧套餐、旧渠道、账号归属或用登录证明经验。

只有后续明确答案改变分支：first_subscription→none_reported/new_subscription/Q-C02；returning_subscription→none_reported/resubscribe/Q-C02；existing_subscriber→active_reported/unresolved/Q-C11。以上current_subscription均带真实合成答复来源/时间，不声称已查账单。尝试把existing_subscriber作为inferred写入会原子拒绝 `Inference cannot establish protected facts`，原状态仍unknown并等待Q-J02。熟练度只控制解释深度的C规则与此一致。

## 5. T43：完整记录里明确没有购买任务

自足场景：“我已有订阅，这次只检查 Mac 本机环境。”本轮四事实为 Q-J01=existing_subscriber、Q-C11=environment、Q-C02=macos、Q-C05=local。全部24种输入顺序都保存相同完整envelope、原source/time与设备/账号角色：Q-J01绑定scope-account，其余绑定scope-device。context.task=environment，current_subscription=active_reported，**purchase_intent=none、payment_intent=none**，明确是本次不处理购买，而不是说没有订阅。

完整后续问题序列，全文逐轮匹配：

`Q-C01 → Q-OS03 → Q-C03 → Q-C04 → Q-C06 → Q-C09 → Q-N01 → Q-N02 → Q-N03 → Q-N04 → Q-N06 → Q-L01 → Q-L04 → Q-C12 → Q-Z01 → Q-C10 → None`

没有新目标Q-C08或支付分支，完整最终assessment为I6/G1 complete/G2 pass，active_branches=`[core, os, network, local, protection]`，G3仍blocked，PC0和保存/导出许可仍关闭。这里G2仅说明合成访谈覆盖足以规划，不等于目标Mac通过原生检查。

### 真实缺陷与兼容性修复

冻结eleventh的同一输入已经正确跳过支付问卷，却仍暴露purchase_intent=`subscription_preparation`；不能把这个字段从投影删掉来假装完整条件已满足。规范测试先失败，现以当前明确task归一化派生意图标签：纯环境/network/incident的payment_intent=none，purchase_intent由购买任务集合/已完成状态确定。`record_fact`、`record_facts`、`set_context`、load/save和begin_task路径均覆盖。

旧保存记录被加载或明确保存时只修正派生标签，不改facts、current_subscription、来源、时间、目标、方案或许可；输入原字节和原Python对象不变。已有purchase_completed=true且purchase_intent=completed的同任务历史保持completed/payment none。明确begin_task进入新环境任务才变为none；进入renew/upgrade/change_channel/新订阅任务重新设置相应意图，旧套餐不自动成为新目标。直接set_context/record_fact往返也测试；曾暴露“回到renew仍payment none”的次级回归有独立failing-first记录，已修复。

没有新保存schema、字段或问题ID；不是重新查询旧订阅，也不从经验推导权益。非法批次或非法task拒绝且输入不变；unknown/refused/deferred/inferred Q-C11不能自行把默认任务改成environment。CLI普通--input/--output实际验证旧标签修正、事实时间不动、公开下一题Q-C01；没有引入新CLI参数或改写CLI生产代码。

## 6. T48：先保护、再补事故细节，常规主题暂缓

固定起点是尚未回答付款设备Q-P03的订阅准备；已有目标套餐、Mac、local、账号与网络自述。分别中途报告credential_exposure（明确宿主上下文）和当前账号current_suspension（Q-C03当前报告），不是历史停用或仅凭错误码判断。

### 零题/一题的立即路径

事故一出现，真实API及CLI即输出I0、G1 emergency_deferred、active_branches=`[incident]`、G2 blocked/conditional_plan_only=true和G3 blocked。无需先填写H01—H07，`emergency_deferred_branches=[payment, local, protection]`已显示原未完成主题因事故暂缓；原facts及用户显式deferred_branches完全不变。这是新增的**assessment-only**投影，不写入保存schema、不伪装成用户拒答。答完H01后这些状态仍在，下一题只是H02，付款问卷没有抢占。

立即可给的是最小保护指导：不发送秘密；助手不再发起自己尚未发送的请求/重试；识别受影响服务/凭据类别，说明官方保护入口及影响。当前intake直接链接已生效的M12卡，该卡要求上述立即处理，不要求七题全答完才给指导。CLI是问答/阶段接口，不生成完整Agent讲话，也没有凭据撤销执行器。G3从始至终关闭，任何实际撤销、停止用户任务、会话退出或服务接触仍走独立权限和具体条件；本页没有通过紧急标志绕过门禁，也不宣称已执行隔离或撤销。尚缺事实只阻断依赖该事实的具体步骤，不阻断这些一般保护说明。

### 完整事故问题全文

两类事故均使用既有H01—H07，保留ID/顺序。credential exposure的专用措辞修复了原先H01“被限制对象”、H05默认计费渠道及H06默认申诉/退款的错配；停用分支字节不变。

| ID | 凭据泄露实际问句 | 当前停用实际问句 |
|---|---|---|
| Q-H01 | 可能泄露的是哪类凭据、涉及哪个服务或客户端？只说类别和对象，不要发送密码、令牌或密钥内容。 | 被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？ |
| Q-H02 | 最近一次与本次任务有关的事件，大约何时发生？目前恢复了吗？ | 同左 |
| Q-H03 | 有什么迹象提示凭据可能泄露？只提供脱敏后的提示或现象，不要贴原始秘密或完整日志。 | 当时显示什么错误/通知？有可脱敏的原文或局部截图吗？ |
| Q-H04 | 发现泄露前做过什么相关操作，或把信息发到了哪类位置？不要贴具体秘密或含密链接。 | 出现问题前正在注册、登录、订阅、更新客户端还是执行任务？ |
| Q-H05 | 哪些设备、客户端或自动任务可能使用这类凭据？只列受影响对象，不读取凭据内容。 | 当时在什么设备/环境、通过什么客户端和计费渠道使用？ |
| Q-H06 | 是否已经通过官方渠道处理这次泄露，或收到需要完成的保护指示？不知道可以说明。 | 是否正在申诉、身份核验或处理退款？有没有官方回复要求你完成的事项？ |
| Q-H07 | 之后做过哪些退出、重装、清理或配置修改？有需要保留/导出的数据吗？ | 同左 |

每轮完整question对象都相同元数据：incident/I0、postcontact=false、clarification=false、允许reported/unknown/declined/deferred、requires_action_authorization=false。原例并非声明七问都是每次必须回答：已知事实批量吸收，不相关项可not_applicable，拒绝提供细节可停止自动追问；C指导要求保护先行，不能把表显示成长问卷。

全部七题给出合成脱敏报告后，next_question=None，但**不会自动判定事故解决**，G1仍emergency_deferred、G2仍blocked。仅显式报告incident_resolved=true后恢复之前任务：先补相关历史变化Q-H08“本次是否沿用当时的设备/网络/付款工具？哪些变了？”，再回原Q-P03。无需重做已知套餐/系统/网络事实。H08不是继续调查泄露的必答前置，也没有在紧急阶段阻止保护。

另一整组轨迹分别把H01—H07全部设为unknown/declined/deferred/not_applicable：不循环，读档不重开，incident_resolved仍false。not_applicable清除相应字段缺口但不解决事故；unknown/refused/deferred明确保留其缺口。停用与凭据泄露都保留G3、PC0及保存边界。

## 7. C逐句审阅与可达入口

| 生效段落 | 本次逐句/逐步骤判断 |
|---|---|
| SKILL 开始方式2—5、完整访谈入口及按需链接 | 先复用已知事实；熟练度不代表付费，紧急优先；本机只是建议而非默认同意；读取intake的稳定ID与三门禁；PC0不接触服务。完整CLI入口明确区别旧八字段兼容入口，按需链接routes/accounts/incidents使相关指导可实际到达。T34/T78/T43/T48均适用，不用脚本测试冒充模型提取。 |
| intake Scheduling首三段 | 一轮吸收全部事实、跳过已知和不适用、只澄清一次后允许未知/拒答/暂停。正常顺序服从紧急优先。首次/已有订阅与本次任务分开，纯技术任务不加载支付调查。没有让“老手”跳过订阅澄清或权限。 |
| intake新增Q-C05/Q-J02段 | 第一句明确未答/跳过/未知/拒答/延期保留候选，限制为比较或带缺口初步建议，禁止按本机部署和把停止追问当接受。第二句把老手/用过归一化为经验含糊标记而非付费，Q-J02一次短澄清。末句允许退出、不猜当前付费。对应T34/T78每个原条件。 |
| intake新增已有订阅环境段 | 第一句同时吸收旅程、实际任务、系统和路线，不问新套餐/支付渠道。第二句两种none标签仅说明本次不处理购买。第三句旧记录仅派生标签修正，订阅来源/时间不变；已完成历史和新任务分开，旧目标不复用为新购目标。对应T43记录完整性及兼容性边界。 |
| intake新增事故段（逐句） | 首句最小分流优先并用单独投影标其他未完成主题，未改为用户拒答；第二句凭据语境只问安全的类别/迹象/组件/保护状态，允许未知拒答不适用。第三句立即停助手自身未发送请求、说明保护，不等七题。第四句实际撤销/停止他人运行任务/退出/接触仍分别授权，紧急不开放G3。最后两句链接M12，只有相关具体步骤补缺口，明确解决才恢复旧任务，未知不是解决。 |
| intake Fact states/G1—G3与原索引 | inferred不得建立订阅等敏感事实，unknown/declined不是false；G2不具备就给条件计划，G3独立。Q-J02用于经验含糊；Q-C11用于已有订阅的本次任务；Q-C08只购买适用。H系列是字段索引，不是强制七题表。没有新增隐性套餐/归属问题。 |
| routes-and-platforms R-LOCAL、M01及执行卡 | local never silently selected；接受建议才进入路线；术语比较可先解释，不考技术水平。没有批准只交付操作卡，不执行、不购买VM/VPS。C05未选时的条件式输出不诱导先部署。已有明确本机任务直接复用，不重走选购教程。 |
| accounts-and-payments 开头、A1、B1、A3与Handoff | 任务由真实目标收窄，已有用户只处理实际续费/升级/环境/故障；不把纯环境检查变成购买。A1有账号不等于有订阅、当前事故先处理；A3仅记凭据类别/服务/时间，不收秘密，立即停止自身未发送请求；停止用户任务、撤销/更新凭据另行审批。不能以购买或重新登录测试事故。 |
| incidents-and-integrations Incident triage、K1、K2 | 首先暴露凭据/数据危险，其次明确停用；最少脱敏事实即可开始，用户自述可作为初步分流。立即停自身未发送请求与重试，用户运行任务另需批准；不声称撤销可逆。K1明确不让事故用户重走套餐/服务器购买教程，已知事实复用，保全项目不自动清理。K2按观察分层，凭错误码不认定封禁；当前停用走真实官方路径，不循环换号/清理“解封”。 |
| incidents K3/K4、contact-and-safety权限与阶段 | 证据包保存/发送单独批准，不收原始秘密/全部日志；官方联系、申诉/导出/退款需实际许可。PC0不为了复现访问服务。问题答案、计划接受、宿主/OS/接触/付款权限互相不替代；紧急分流不会例外授予实际操作许可。缺权限只停依赖动作，可继续独立安全指导。 |

结论限定：四个原案例均有完整固定轨迹及对应当前指导；不把经验归一化标记、合成停用报告或宿主incident标签称作已测试的NLP识别或真实安全事件发现。没有当前价格/规则推荐，所以没有新增外部查价或服务访问。

## 8. 执行结果、回执与冻结文件

命令均从twelfth根目录执行：

```sh
python -B tests/test_acceptance_task_scope_rebuild.py -v
python -B -m unittest discover -s tests -p 'test_interview*.py' -v
python -B tests/test_acceptance_routes_rebuild.py -v
python -B tests/test_acceptance_intake_rebuild.py -v
python -B tests/test_acceptance_task_scope_rebuild.py --replay > /tmp/guardian-task-scope-twelfth/task-scope-replay.json
```

当前实测：新15项通过1.541s；既有interview145项通过4.464s；route6项通过0.350s；intake15项通过1.471s，共181项。数目不代替原条件逐条证明。聚合、包与最终ledger另见父级集成回执。

完整回执目录 `/tmp/guardian-task-scope-twelfth` 随项目归档保存：

| 文件 | SHA-256 / 内容 |
|---|---|
| task-scope-replay.json | `71fe994782fdd58d77470b54c315f9291b41e4033a1ce4bc5dd5e27f9f795ac1`；1252347 bytes，四原ID、全部状态/问句/退出、T43全部24排列；连续两次字节相同 |
| before-after.json | `7b6ff484d9e7bd681905299fbb71d943d945cd57d51c33cca4387c0d585088da`；eleventh/twelfth完整任务标签和全部事故问题对照 |
| route-replay.json | `8e2a95d358a8fb9ca27a95f72f9788598e2337ed0498a5e22936142767727a84`；已接受路线轨迹字节不变 |
| intake-replay.json | `67406ca122eea39f62e4fbb881cc1040a488a4796e487fa5235a5591b972bc87`；已接受T53/T74/T81轨迹字节不变 |
| failing-first.log | 原T43标签、泄露H01和缺少明确事故暂缓投影的修复前失败 |
| task-roundtrip-failing-first.log | 兼容性回归：直接从environment返回renew仍payment none的真实失败 |
| task-scope-tests.log / interview-regressions.log / route-regressions.log / intake-regressions.log | 当前完整测试日志 |
| make_counterexamples.py | 独立baseline/current完整回执复现器，参数为twelfth根目录 |

新增assessment字段仅在urgent时出现，既有deferred_branches不变；严格消费固定键集合的外部调用者须允许此可选字段。保存schema不变，普通load不是resume，不消耗问句或重新授予保存权限。旧任务标签会按当前context被纠正，事实证据不会重新定时。回退必须同时撤回flow、intake、本测试及依赖新语义的证据，不能保留候选acceptance却回退行为。

下表固定本页实际阅读、执行和依赖的文件字节。改动需先回放与重审，不仅更新哈希。ledger/tracker由父级集成，因此不作为不变输入固定。

| 文件 | SHA-256 |
|---|---|
| `skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md` | `6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562` |
| `skills/claude-guardian/sources/design/D-ENV-v0.3.md` | `ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4` |
| `skills/claude-guardian/scripts/interview_flow.py` | `304144309c2e918223777df5d0f2f9801ff1e862fad195d18f0f318b5b321f4e` |
| `skills/claude-guardian/scripts/interview_cli.py` | `003b9a31c01395be446e658d0ddac6a898172a9008981a302d7f8d8d5e324a91` |
| `tests/test_acceptance_task_scope_rebuild.py` | `e5585ba5cd68dc3bf35ca217453f6e2be7835558588fb47006c8d8be7b4f964e` |
| `tests/test_acceptance_intake_rebuild.py` | `e26a26ee3b3d0ba93270787f8dbd8022ed11adb2fbbb0f1229df8f1aef57245a` |
| `tests/test_interview_flow.py` | `7140e70b88e4cd3099d2fa725b3b20269de511be90d4dd020154d2db3e5e0965` |
| `tests/test_interview_cli.py` | `a3cbd2c8332d50e6c49fee61ced2bb9c10295b7a3393b39b6de2e89a9a37be4d` |
| `tests/test_interview_resume.py` | `081036b33c3b9a97a476d1e7894b2876ffe0b07d3bdf148b36fe1f370b47d442` |
| `tests/test_interview_migration.py` | `6c4e6bf32875b83ea179ffc836f140141f161240b478b359b62b304767063618` |
| `skills/claude-guardian/SKILL.md` | `f6cd5e5fc2e9ddda329d70fc0643ff323588858a6ad45d5f36fafb01fb7de1d3` |
| `skills/claude-guardian/references/intake.md` | `1d3d6f75788abafefe4a8ce8e9ca1c740b1f4b57656b350a4688c6629ac52dba` |
| `skills/claude-guardian/references/routes-and-platforms.md` | `dd671d72e8b16963f6a1708fc953ecb41a5191f42934d68f0404824c17354984` |
| `skills/claude-guardian/references/contact-and-safety.md` | `095caff949dbd3feffb13f19279a2fdce16e528775898d0b0298d5928f69f53c` |
| `skills/claude-guardian/references/accounts-and-payments.md` | `ec855e1ffe5daaffa8001fa39056d03c8b3e0441d6c6b38fcfddb376c742ede8` |
| `skills/claude-guardian/references/incidents-and-integrations.md` | `37d1f06a3e46a61fd841455ad40ca4081468c0e6b2b4248d23b345c05d93e9d2` |
| `skills/claude-guardian/scripts/traffic_policy.py` | `8abb87e212b96f2dc80f59d065b13256257211b4743340438090aca8bd53d9fd` |


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


### Twentyninth subscription-repair preservation review (2026-10-18)

The earlier twelfth-batch statement “没有新保存schema、字段或问题ID” describes that earlier correction, not this later subscription repair. Twentyninth adds optional `plan_compatibility_needed`, derived current-plan Q-C13, optional `purchase_completion` and its explicit lifecycle handling while retaining old schema-1 inputs. Strict older readers may reject records containing these additions; they must be upgraded rather than dropping unresolved facts to manufacture readiness. Q-C13 is an implementation ID, not an alteration of the original specification IDs or Q-C08 target-plan semantics.

An independent reviewer read unchanged original T34/T43/T48/T78 and D-SPEC §5.5, §6.4–6.6, §6.11–6.14 and §7.3, all changed runtime sections, and the complete changed intake/accounts/resume guidance. All 15 original tests pass on fresh published baseline and candidate, zero skips. The complete current replay, including all 24 T43 opening permutations and full question/state/assessment trajectories, is byte-identical across both trees and both runs: SHA-256 `99c11ee14d12e3f07e67b7e35c9b98338594dabd81b7cac71f5db5f261c35360` (1314975 bytes). The earlier twelfth hash `71fe994782fdd58d77470b54c315f9291b41e4033a1ce4bc5dd5e27f9f795ac1` remains historical, reflecting the prior evidence stage; it is not the current replay digest.

T34 retains an unconfirmed route for unanswered/shown/skipped/unknown/declined/deferred/comparison inputs. A complete billing explanation can omit an unrelated route prerequisite without confirming that route; returning to environment/network/cleanup/subscription preparation exposes the original missing route and conditional plan again. T43 remains purchase_intent=none/payment_intent=none with no target-plan/payment questions in ordinary environment work; explicit relevant Q-C13 adds current-plan information only, separately account-bound and never copied from Q-C08 or claimed as established feature compatibility. T48 still preempts old-billing/current-plan branches with immediate minimal incident triage, explicit ordinary-theme postponement, bounded unknown/refusal/defer and explicit resolution; neither seven-question completion nor an emergency flag grants authority. T78 still records unknown subscription and asks the short Q-J02 when only experience is supplied; plan/compatibility flags, target choice and expertise cannot establish paid status or inferred entitlement.

Independent preservation checks cover these new branch intersections and closed G3/contact/save boundaries. All four original L+C conclusions remain within the existing normalized-host/guidance contract. No arbitrary-language parser, native incident detection, actual credential action, real feature compatibility or new original-case acceptance is claimed. Current source table pins reflect only the reviewed exact bytes; original historical narrative and artifacts are preserved.


## Registry-count wording preservation review (2026-10-18)

The current SKILL dependency pin incorporates only removal of the hardcoded registry total, as independently reviewed in [the exact documentation compatibility record](skill-registry-wording-compatibility.json). Conditional scheduling and permanent Q-C07 retirement are unchanged. Earlier observations and generated-response source bytes remain historical; this correction adds no acceptance case, runtime behavior, native evidence, contact or action authorization.
