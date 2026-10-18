# 验证记录 · 0.1.0 诊断预览

日期：2026-10-15。执行环境：Friday 云端 Linux，Python 3。

## 已执行

- `python3 -m unittest discover -s tests -v`：42 项行为测试通过
- Skill frontmatter/命名校验通过，全部按需引用文件存在
- 独立复核保存访谈再续接、模拟 check → analyze → plan 的流程
- 回归修复空值代理事实、过期/变化快照错误就绪、隐私字段与原生证据限定信息丢失
- 发行包重复构建字节一致；只包含显式文件清单和 GPL LICENSE

## 尚未执行

- 原生 macOS / Windows 真实采集与 Codex 桌面交互
- 实际 Clash / Mihomo / 浏览器配置、代理路径、DNS、IPv6、STUN/WebRTC
- 系统配置写入、清理、故障注入与回滚

当前原生采集只实现系统家族、内核/构建版本、当前 UTC 偏移的最小子集，不能冒充完整 ENV-01/02。所有公网探测、自动修改和增强阻断未开放。离线输入的真实性不能靠 CLI 自行证明，输入标记与授权参数仍依赖宿主和操作者核实。报告分享前仍需复查脱敏结果。

## 工作流基础增量（待 PR 验收）

2026-10-15，Linux 云端复核：163 项 Python 单元/回归通过，另 8 个 Node 模拟浏览器生命周期场景通过。模拟浏览器不发 STUN、不代表真实浏览器政策验收。新访谈、输入绑定、凭据拒绝、事务文档校验、超时/取消清理和固定页面服务均有回归。POSIX 文件事务仅测试临时文件；Windows 不支持该事务后端，相关测试应明确跳过，不能算 Windows 写能力交付。

上一版本固定提交 57cbbe0 已经在授权 Mac 上运行60项测试并真实采集7项元数据、完成回读；该结果不自动覆盖新增基础模块。新版三平台 CI 与本机结果以 PR 固定提交记录为准。

## PR #2 固定提交验证

2026-10-15，提交 `3139d9cf4978094a64ce24a80d0e8192b0f79d40`：[CI 38708994819](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38708994819)。Ubuntu/macOS 各171项Python测试通过；Windows发现171项，实际136项通过、35项不适用POSIX/原生用例跳过。各平台另8项Node合成生命周期测试通过，编译及重复构建通过。三端ZIP SHA-256一致：`59db8411ebf0248775462b30dff579c0f9c46dca2715681d3317eceadd44276f`。这是该固定提交的包，不是后续增量的哈希。

用户Mac只运行了旧提交 `9ebb3b626893128fe5cdb2ac1db719770b7bb277`：补做获准回环测试后共130个不同Python用例通过，33个事务用例在setup阶段因缺少`os.listxattr`出错，事务测试主体未运行；8项Node合成用例通过。后续Darwin描述符xattr修复有云端macOS CI证据，但尚未在用户Mac重测。用户本机可离线，原生验证暂停不妨碍云端开发。

实际公网探测、真实代理/防火墙/浏览器修改、账号登录、真实清理和故障恢复仍未执行。上述通过不关闭全部218项设计验收。PR #2待所有者明确确认后合并。

## PR #3 固定提交验证

提交 `be2e626a3626bfb853babf2b407fd67be146ec82`，[CI 38711511300](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38711511300)：Linux/macOS发现343项、339通过、4项Windows原生夹具跳过；Windows发现343项、258通过、85项POSIX用例跳过（35事务、17静态读取、33请求读取）。Windows真实CI环境的4项临时文件测试通过：普通只读计划、ADS/硬链接拒绝、junction祖先拒绝、注入元数据权限失败后的句柄清理。最后一项不是真实ACL拒绝验收。各平台另8项Node合成测试及打包通过；ZIP SHA-256统一为 `b4c0b29bc6f78c9c06de61b1fae30e1573cde5d9ed5a807cd827e0a742f8ad4e`。未测试用户真实文件，未实现Windows写入或回滚。

## PR #3—5 后续固定提交

- PR #3 `9441d3385a0f82f1bc45a7da41e81766d84bf7a0`，[CI 38712347446](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38712347446)：Linux/macOS 349通过/4跳过，Windows268通过/85跳过，共353；三端包 `6fadbcd067070894f0838fc95e539e36f6be6736452a2c6ea28c38607fbcabcd`
- PR #4 `89029537d3545b62a955610210abd236775deb08`，[CI 38713285829](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38713285829)：Linux/macOS372通过/4跳过，Windows290通过/86跳过，共376；三端包 `d6b6e917cfe9761c366d197dce496f54c548cf48f87c8a3b17a0c1ed72b1367c`
- PR #5 `75ff97182dfbaeabd2e763881893982ba6cfb4de`，[CI 38714405280](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38714405280)：Linux/macOS402通过/5跳过，Windows321通过/86跳过，共407；三端包 `6cf6fd487d1481149e2c919b9a4a545a9a09b9ac6271b9d15bfd43160a8fdd18`

各轮另8项Node合成生命周期测试、编译和重复打包通过。Windows跳过均为POSIX限定项；Linux/macOS跳过为Windows原生夹具。PR #5的Windows自有临时IPv4/IPv6监听器身份测试实际通过，关闭监听器后拒绝旧状态；不读取用户进程，不证明完整应用实例或命名空间身份。命名空间仍依赖宿主断言，未使用Microsoft标记保留的compartment API。以上均是固定版本证据，不继承到未运行的新提交。

## Windows 元数据离线预检增量（历史独立分支证据）

2026-10-15，精确隔离发布树的云端 Linux 检查：Python 发现486项，481通过、5项Windows原生用例跳过；Windows事务定向35项中31通过、4项原生用例跳过。另8项Node合成生命周期测试、运行时代码编译、重复构建检查通过。发行包SHA-256：`15451fc929a70fe6cd76b56b1def2065b625e823c8229d5b6668f76aea170f35`。

新增12项均为合成/离线测试，包括所有截断、尾随/重复流、不支持流类型与属性、命名流、边界长度、损坏数据、取消/预算、伪造完整性和目标/过期拒绝；另扩展现有预算回归覆盖超大整数。尚未运行本增量的三平台CI时不得继承旧CI结论，最终固定提交及各平台结果以PR检查记录为准。

BackupRead原生收集、完整安全描述符验证与保留（含SACL）、短文件名检查、Windows apply/rollback及故障恢复仍未实现；帧被接受仅证明调用方字节结构和数据摘要，不证明原生来源、元数据完整性或用户设备验收。没有提权、启用特权、真实配置修改或公网探测。


## 离线环境面板独立分支验证（2026-10-15）

以 main `78072c2a84652e304f681d8c16b1dc591c515b27` 的相同树为基线，
仅加入面板、打包清单与相关文档，不包含并行的 Windows preflight 增量。
本地 Linux：`python -m unittest discover -s tests -v` 发现492项，487通过、5项Windows原生用例跳过。
其中 `test_status_dashboard.py` 18项合成测试通过，覆盖秘密/HTML哨兵、白名单、逐字段时效、
未知来源、重复/非法ID拒绝、未知ID不计证据、无网络/进程调用与拒绝覆盖。
`node tests/webrtc-lifecycle.cjs` 的8项合成场景、compileall及重复构建一致性通过。
包SHA-256：`fa96fe015aa665c99051892ca913411bdc916639fcc75b0294d968d86a257948`。
三平台CI结果以PR最终提交检查为准，不继承之前提交结果。

静态示例仅使用合成数据，未收录到仓库。实际浏览器渲染因执行环境阻止而为 `not_run`；
响应式CSS代码检查不代替桌面/窄屏截图。网络组件结果未集成，仍为 `not_run`；
不将11类展示范围或测试数量当作ENV-01—05/ENV-10完整验收。无用户设备/配置操作。


### 面板精简重设计增量

按用户要求减少默认可见信息：白底紧凑三列表格保留11类检查、状态与关键事实，
原生details默认折叠证据；报告失败/取消/未知状态仍在时间行可见，不因精简隐藏。
面板23项合成回归通过；独立面板分支Linux全套497项，492通过、5项Windows原生用例跳过。
8项Node场景、compileall和重复打包通过。新包SHA-256：
`619c638e6d2f2cb0307a8a87f30086d31153bd032f07813b026242326e5914fa`。
先前面板的测试/包证据不代替此版本；三平台CI以PR当前提交记录为准。
真实浏览器视觉验收仍not_run，未增加网络或设备操作。


## 集成交付说明（2026-10-15）

以上 PR 分支记录保留其原始测试范围与时点。按所有者最新要求，本次将 Windows 预检、精简状态面板和离线探测附件整合为直接 main 交付，不再新建 PR。独立分支的网络尚未接入描述为当时状态；本次新增可选 HTTPS/STUN 本地附件导入，但不进行新探测、不验证宿主来源、不授予实际操作权限。实际设备、浏览器、网络与恢复验收仍未执行。

最终隔离集成树的本地 Linux 验证：`python -m unittest discover -s tests -v` 发现522项，517通过、5项Windows原生用例跳过；`node tests/webrtc-lifecycle.cjs` 8项合成场景、compileall、git diff --check 和两次重复打包一致性通过。发行包 SHA-256：`8280b4951007f1098b38290a454ed7a2062f7b0b97ea864c3d81e8c166520aa1`。此处不是三平台 CI 或用户设备实测结论；实际发布提交及各平台 push CI 以对应固定提交检查记录为准。


## DNS / Mihomo / 离线投影集成批次（2026-10-15，尚未发布）

基于 main `06735926b14c15259272735d495af9707008e29c` 的隔离树，包含纯 DNS 编解码、独立 Mihomo DNS 适配器、面板 DNS 样本投影、包清单和相应文档。Linux 完整套件发现584项，579通过、5项Windows原生用例跳过；其中纯协议31项、Mihomo适配器20项、新投影11项，均通过。另8项Node合成生命周期场景、compileall、diff检查、两次重复打包一致性通过。包 SHA-256：`795eb659562a004cfc3786ad9d76498ebe9e060a42c5da3afa19975c9ec93acc`。

协议测试仅用合成字节；Mihomo测试仅使用注入响应与测试自有回环监听器；投影只读本地样本。独立投影复核运行67项相关回归并检查429个畸形字段组合，无意外异常。没有运行真实控制器、公网DNS、原生用户设备、浏览器或完整DNS泄露验收。测试套件通过不等于运行许可；该批尚无三平台push CI证据，不继承上批CI结果。发布须取得本批具体授权。

回滚范围为本批新增模块/投影分支、清单与文档；无持久配置、数据迁移、缓存清理或实际设备状态需要恢复。ENV-04/VAL-04仍保留未完成项。

## 系统 DNS 与命令清理隔离批次（2026-10-15，发布前本地证据）

基于 main `974ee563d22451aba0008f9fe2822995d94c1bd3`，仅含 macOS/Windows 系统 DNS 库、离线投影、固定命令生命周期修复及清单/文档；不含并行原生上下文或会话集成工作。
本地 Linux 全套654项，648通过、6跳过（Windows原生/专用mock用例）；新增macOS21项、Windows21项（Linux20通过/1跳过）、OS投影11项、命令生命周期17项，相关盘点13项通过。独立复核另检查1001个畸形投影字段组合，无意外异常。8项Node合成生命周期场景、compileall、diff检查及两次重复打包一致性通过。包SHA-256：`0d3164434bde8c0c86ea81c6149eb3f2eb1876a49b6188cbf673437cec472891`。

固定命令白名单未扩大。新回归覆盖启动/读取/超时/超额/中断/终止回收失败，清理失败不当作成功或安全取消；不使用删除测试、放松断言或吞异常取得通过。Windows管道分支本地mock验证不等于实际Windows原生执行；后续精确提交的三平台push CI须分别记录，不继承历史结果。Linux/macOS进程夹具、Windows受控mock模块均不查询真实DNS，不证明真实设备、受管策略、实际用户/命名空间或运行时信任。

这些库没有新的CLI、安装、配置写入或探测执行授权；宿主回调、进程创建/内核异常不提供硬实时保证。真实设备DNS、浏览器/应用路径、权威关联及完整ENV-04/VAL-04仍待验收。回滚本批代码/清单恢复此前行为，无用户配置、缓存、凭据或持久状态迁移需要撤销。


## 系统 DNS 与命令清理固定提交 CI 回执

提交 `fcc46b9a5a269f0aa3423edb898f49c6f4212413` 的 [push CI 38760023126](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38760023126) 三平台全部成功。Linux/macOS各654项、648通过/6跳过；Windows654项、542通过/112跳过。三端Node8项、编译与重复打包通过，包SHA-256均为 `0d3164434bde8c0c86ea81c6149eb3f2eb1876a49b6188cbf673437cec472891`。Windows owned mock-cmdlet与适用生命周期测试通过，不是实际DNS或用户设备验收；跳过不等于通过。这是上批固定提交证据，不自动覆盖后续上下文/会话代码。

## 上下文与诊断会话批次（2026-10-15，发布前隔离证据）

基于 main `fcc46b9a5a269f0aa3423edb898f49c6f4212413`，包含Mac/Windows窄范围原生上下文观察、按实际平台选择的元数据会话、共享Windows输出路径语法防护、打包与文档。Linux隔离全套749项，743通过/6项Windows专用跳过；独立复核覆盖Mac上下文19、Windows上下文28、会话44、共享保存路径4项。Node8项、compileall、diff检查及两次重复打包通过；包SHA-256 `396bb95a2a4ab558aa7c3fbb63c901b93d9ac6b26278111a5c25bdd604fb3b50`。并行数值边界与配置候选工作不在此树内。

原生上下文测试使用合成ABI/系统函数与文件元数据，所有平台均不执行真实上下文API；会话测试注入上下文与DNS响应，禁用真实解析/进程创建。CLI的fresh nonce属于真实交互流程实现，不是宿主身份/OS权限证明。Windows控制台账户相等关系保持unknown/binding blocked；路径语法筛选不证明本地存储或ACL，Windows保存文件继承父目录权限。实际Mac/Windows控制台、运行时依赖、namespace、真实DNS、浏览器视觉与Codex UI验收仍未运行。生产DNS核验回调尚需可信宿主实现，CLI无DNS选项。后续精确提交三平台CI须另行核实。

回滚本批上下文/会话/保存语法增量及清单即可，不涉及系统配置、凭据、安装或持久授权撤销；用户明确创建的报告应保留，不自动删除。


## 数值边界与私有配置候选批次（2026-10-15，发布前隔离证据）

基于 main `a016769badfbfa1fd25aa9376dc2465c7455f16d`，七个既有数值边界脚本、两份新数值回归、配置候选模块/测试/文档、包清单与能力/证据文档。完整Linux隔离套件795项，789通过/6项Windows专用跳过；新增数值31项、候选15项，既有remedy22项通过。Node8项、compileall、diff检查、两次可复现打包通过，包SHA-256：`f84ced5385196ed0e955b316d5a076de8034f737b9e02abf46c80b0d4b387f60`。

独立数值复核覆盖31项新增与144项既有相关测试（其中5项平台限定跳过）；配置候选复核覆盖15+22项。测试仅使用注入数值/时钟与合成配置，未访问真实DNS/用户配置或设备。数值防护针对所改公共边界，内部transport/子进程cleanup原始时钟读取未重构，不宣称OS故障下硬实时期限或全部时钟来源可信。候选只在内存中生成、不调用事务，apply_supported=false及原生适配/版本/归属/动作授权阻塞保持。

上下文批次 `044a891` 的Linux/macOS CI成功，但Windows发现三个测试可移植性问题（UTF-8默认解码与POSIX路径夹具）。`a016769` 仅更正这两份测试，保留全部断言与跳过数，运行时和包哈希未变；后续三端结果须看精确提交记录。修复后Windows原失败项通过，首次运行另遇既有PowerShell mock超时，仅重试失败job后通过，未放宽断言或生产时间界限。最终[三平台CI 38765033394](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38765033394)均成功，准确平台计数见日志；包哈希仍为 `396bb95a2a4ab558aa7c3fbb63c901b93d9ac6b26278111a5c25bdd604fb3b50`。未通过的历史轮次不记作成功。

当前批次固定提交三平台CI另行核验，跳过不算通过。回滚代码/清单即可，无用户状态迁移或系统改动。

## 包/上下文验收与进程诊断批次（2026-10-15，发布前本地证据）

基于 main `f7baad5d7b01ab48e4300a7f93ca2d722b85d298`。本地完整821项，813通过/8跳过（原Windows专用、关闭的native smoke、关闭的Windows诊断）；Node8项、compileall、diff检查、重复打包通过，包SHA-256 `0519b9d1644d53125ecdd78d0d50e89d02db989da4af16a0af538f46d9ab78e2`。包含解压发行包9项、原生上下文smoke合成边界与显式CI-only实际阶段、Windows PowerShell单独stage观察，以及Mac helper提前退出BrokenPipe修复回归。

本地首轮发现helper立即退出时stdin buffered close可泄露BrokenPipeError，修复后用确定性write/close×退出20/21/0六子案例覆盖：保留退出20为RESOLUTION_FAILED、其他失败及请求未交付的退出0为PROCESS_FAILED，始终回收进程并关闭管道；真实cleanup失败不吞掉。没有放宽探测预算或增加操作权限。

Windows既有15秒mock-cmdlet测试重复超时，原因尚未确定。新增诊断只在普通单元套件之后、Windows且显式flag下执行，最长45秒用于固定阶段观察，不改变原语义测试的15秒、生产预算或通过条件；诊断first/repeat不能认作冷/热缓存证据。只有固定阶段/耗时/状态输出，无原始query/path/env/stderr。原单元失败仍使CI失败，不被诊断成功掩盖。

原生上下文smoke首次实际执行将仅在CI自有Mac/Windows进程，Linux为n/a；已知headless/权限/路径阻塞记skip，未知ABI/超时/清理失败仍失败。CI绿色不是完整原生桌面验收，必须分别读取smoke结论。未访问用户设备或运行真实DNS。

## 合成截图与原生错误诊断增量（2026-10-15，发布前本地证据）

基于 `87364bdc51a808557c71a08d184a2cc98d874488`，新增合成浏览器截图workflow/工具/12测试/文档，以及native smoke安全失败诊断3回归。完整本地836项，828通过/8跳过；Node8项、运行时与工具compileall、diff与重复打包通过。运行时包未改变，SHA-256仍 `0519b9d1644d53125ecdd78d0d50e89d02db989da4af16a0af538f46d9ab78e2`。浏览器工具的本地测试无Chrome/网络，真实截图与像素检查尚待精确CI产物；PNG头夹具不作为图片交付。原生失败的固定代码/阶段诊断仍是失败，不放宽BLOCKED集合或输出任意私密文本。

前一轮[CI 38767766447](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38767766447)三端完整821项单元测试通过：Linux/macOS813通过8跳过，Windows701通过120跳过。Windows随后实际上下文smoke非零子进程失败，后续Node/编译/打包未运行，整个CI失败；Mac实际上下文capture/RUNTIME_PATH_INVALID明确跳过，其他流水线步骤成功，不能宣称完整原生ABI验证。Windows原15秒mock语义测试此轮通过，after-suite诊断first/repeat为0.343/0.297秒且所有固定阶段完成，仅记录这次观察，不证明早先间歇超时原因或稳定修复。

## 部分元数据、字体与原生失败定位（2026-10-15，发布前隔离证据）

基于 `3a5d98a4e6622831c40fa577da9d54956289fcc8`，15份经复核实现/测试/专用文档及5份共享能力/证据文档。完整Linux隔离862项：854通过/8跳过；Node8、脚本与工具compileall、diff及重复打包通过。最终包SHA-256 `aba457e0ef47344eb4c47007b84306653d2b0739ad5efda1f5424f314e423487`。Mac元数据API与session fallback仅合成回归；Windows诊断32项、会话54项、字体预览16项；smoke21项中20通过/1Linux跳过，另532种枚举/退出组合复核未改变失败语义。

前轮CI38769891354 Linux/macOS整体成功；Windows836项单元715通过/121跳过，但实际smoke为`exit=1; code=CONTEXT_UNKNOWN; phase=capture`，全轮失败，原生根因未定。Windows原15秒mock再次通过，after-suite诊断first/repeat为0.344/0.328秒，仍不证明历史间歇超时已修复。截图首次因缺CJK字体在Chrome前失败、没有PNG。本批通过显式CI标志获取固定上游字体及许可、验证哈希，仅临时页面内嵌，未实际执行下载/截图前不宣称视觉通过。所有新实际CI结论待固定提交运行后补记；没有用户设备读取或真实DNS。

## TokenHasRestrictions兼容修复（2026-10-15，发布前隔离证据）

基于d9582ce，专用class21零初始化DWORD读取器接受长度1/4，长度1仅在高字节全零时有效；所有非零值继续被限制检查拒绝。官方DWORD契约与报告过的返回长度差异分别说明，不从固定错误枚举推断本次实际长度。通用读取器、native调用次数和跳过集合未变。独立35项合成复核通过；完整Linux865项857通过/8跳过，Node8、compileall、diff、可复现包通过，包SHA-256 `46ef4ca7348147797a64960bd75868431afb31543fba982c93489bb19366c8ad`。真实Windows结果须检查本次精确push CI，不能提前标绿。

d9582ce的合成截图run38771591023成功，artifact11991666940归属该提交，ZIP SHA-256 `a88189d838d85218d8cedde34f8a2d35d2ee66393374fd156e38200f2e3e0dbd`。实际下载且逐图查看：desktop1440×1000 SHA-256 `55f0c6d7fa05d43b90150683ec50159b55bb02bfd01c4dbf38be1f8e901da479`；mobile390×1100 `2677a889fc735a715fd595f59fb20b8d456488fbf6b59158f8860b8b781d72ca`。中文可读、极简表格/合成标签/未知状态可见、无明显裁切。此为静态布局证据，不证明折叠交互、真实设备、DNS或网络隔离。

## 最终代码基线CI回执（2026-10-15）

`78535f69b523287a0304c1be017dd60e491554f0`：[三平台CI 38772721879](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38772721879)全部成功。865项单元测试：Linux857通过/8跳过，macOS856通过/9跳过，Windows744通过/121跳过；三端Node合成生命周期、编译、可复现打包全部成功。包SHA-256：`46ef4ca7348147797a64960bd75868431afb31543fba982c93489bb19366c8ad`。

实际CI上下文smoke：Windows在capture/CONTEXT_FOREIGN明确阻塞跳过，Mac在capture/RUNTIME_PATH_INVALID阻塞跳过。修复后的Windows不再出现此前token_restrictions返回大小错误，但后续未到达的ABI路径和真实桌面验收仍未通过，Mac新部分元数据API尚无原生执行证据。无真实用户设备或DNS探测。

[同提交合成截图CI 38772721875](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38772721875)成功；下文记录已取回并查看像素的d9582ce截图，不能将静态截图当作交互验收。此前失败轮次保留为历史记录。

## 单轮访谈事实批处理（2026-10-15，发布前隔离证据）

基于已验证代码基线（完整SHA `bebea617012b958a8835045c8621433083b7d509`），4份代码/测试加共享能力/证据文档。新增16项回归，独立复核发现并修复旅程/任务顺序导致payment_intent不同，以及非字符串state泄露TypeError；两类均保留回归。独立重测两种旅程ID的顺序组合与24种畸形state，原状态不变、G3关闭。完整Linux881项873通过/8跳过，Node8、compileall、diff及重复打包通过，包SHA-256 `02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`。

批处理只接收规范化事实，不理解自由文本；source/设备账号角色/同轮时间保留，保存仍须显式output。旧单项CLI格式与record_fact顺序接口保留，冲突需宿主澄清，未知套餐不推断。T53/T81仅相应子证据，不代表完整真实Codex交互或动作许可。精确提交CI须后续核验。

## 合成真实浏览器交互入口（2026-10-15，发布前隔离证据）

基于fb8ceede新增4份独立CI工具/测试与workflow及证据文档。完整Linux889项881通过/8跳过，Node8生命周期与独立Node合成协议检查、compileall、diff及重复打包通过，发行运行时代码未变，包SHA-256仍 `02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`。24项dashboard工具边界（其中8项新交互工具测试）独立复核通过；没有在本地执行Chrome。真实键盘事件、焦点与折叠/布局结果只能由精确CI产物建立，不能以模拟协议结果充当验收。

前一代码提交fb8ceede的CI38775571648三端成功：881项，Linux873/8、macOS872/9、Windows760/121通过/跳过；Node/compile/可复现包成功。真实上下文smoke仍明确Mac RUNTIME_PATH_INVALID与Windows CONTEXT_FOREIGN阻塞，不改变原生设备、DNS或运行时信任限制。

## 浏览器交互实际回执与稳定代码基线（2026-10-15）

代码基线 `af3be41ba287c3b9c2f44775c25d97bb04b8c1be`：[三平台CI38778429996](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38778429996)成功。892项测试：Linux884通过/8跳过，macOS883通过/9跳过，Windows771通过/121跳过；Node、编译与可复现包通过。包SHA-256 `02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`。

[真实Chrome交互CI38778430369](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38778430369)成功。artifact `11994278104`已取回校验，Chrome155在1440×1000和390×1100下实际验证12处summary的Tab焦点/可见焦点轮廓、Enter/Space展开折叠、全展开无横向溢出；页面范围观测只有一个本地文档、零子资源。此为CI合成页面交互证据，不能证明全浏览器网络隔离、真实诊断结果或用户设备。原生上下文仍为Mac RUNTIME_PATH_INVALID、Windows CONTEXT_FOREIGN阻塞跳过，后续ABI/运行时/namespace/设备授权缺口保持。

失败历史保留：43d63f6首次交互未输出可用诊断；29ab8bd定位Enter未展开。af3be41修正CDP文本键事件和错误的native keycode映射，原DOM/焦点/布局断言及安全策略未放宽；不靠重试或skip掩盖失败。

取回ZIP SHA-256 `f1720114914c02d0d09ac90ed7e445298d212c668848edc4ba0cf10ebb115973`，interaction.json SHA-256 `1d8b20287c57882011cefd2d3d805a3977d9f5bc5adf9efa7923ba539490897b`；schema/两viewport/固定结果/原HTML hash均核验，network_isolation_verified=false。PNG哈希同时与manifest核对；此前逐图视觉复核仍有独立固定提交记录。

## Python 3.10 最低运行时任务（2026-10-15，推送前证据）

基于43ec2a228ca0c7092d5585f1b1aca531389530c0，新增独立Linux最低版本CI及四项workflow结构回归。官方[action v6引用](https://api.github.com/repos/actions/setup-python/git/ref/tags/v6)与[固定提交定义](https://github.com/actions/setup-python/blob/ece7cb06caefa5fff74198d8649806c4678c61a1/action.yml)已核对；使用完整SHA，不新增生产依赖或用户设备安装。CI可使用runner缓存或官方actions/python-versions发行运行时，版本范围固定3.10并打印实际补丁版本，不宣称跨补丁二进制可复现。

本地Python3.12.14完整896项：888通过/8跳过；四项workflow回归、Node8生命周期与合成协议、compileall、diff检查及重复打包通过。发行包SHA-256仍为`02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`，生产包内容未改变。前一workflow缺少minimum-python任务会被新结构回归拒绝。

推送前Python3.10实际执行为not_run，后续实跑回执见下节；语法检查和本地3.12运行不替代最低版本执行。新任务完整套件保留原平台跳过，不显式启用原生smoke；再单列脱离源码发行包运行、编译和重复打包。结果仅覆盖Linux CI解释器，不关闭Mac/Windows最低版本、真实桌面、原生运行时信任、网络或218原案例。三平台默认运行时任务保持原样。风险限CI解释器下载/runner兼容与额外任务耗时；回滚为撤销本批workflow、测试和文档，无用户设备恢复动作。

## 最低运行时与三平台最新代码回执（2026-10-15）

代码/CI基线 `8c4adae369e14c0fc486059c0f010cd21f60a954`：[push CI38788444583](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38788444583)四个任务首次执行全部成功。默认三平台均896项：Linux888通过/8跳过，macOS887通过/9跳过，Windows775通过/121跳过；三端Node合成生命周期、编译及可复现打包成功。

新增[最低运行时job116606434623](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38788444583/job/116606434623)实际为Ubuntu24.04上的CPython3.10.22，版本断言成功；完整896项888通过/8跳过，另列脱离源码且关闭site包的发行运行测试9/9通过，编译和重复打包成功。日志已取回核对实际解释器、精确提交与计数；发行包SHA-256仍为`02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`。最低版本运行由not_run提升为Linux CI已有实跑证据，不推广至其他补丁版本或Mac/Windows最低版本。

既有原生上下文smoke分别21项20通过/1跳过：macOS仍在capture/RUNTIME_PATH_INVALID阻塞，Windows仍在capture/CONTEXT_FOREIGN阻塞；跳过不等于原生验收。真实桌面、后续ABI、运行时信任、namespace、用户设备权限、真实网络以及218原案例缺口不变。Chrome交互仍引用历史固定提交af3be41的独立产物；本次没有重跑浏览器或新增设备/公网探测。

## 配置候选与诊断连续性（2026-10-16，推送前本地证据）

基于 `fc81b67cc5ea3008bd0a7e02ed7107aa51cc455e`，两份运行时模块、两份测试及能力/证据文档。独立Linux Python3.12.14完整919项：911通过/8跳过；配置候选23项、既有remedy22项、诊断会话69项（54既有＋15新边界）独立通过。Node8项生命周期与合成交互协议检查、运行时/工具compileall、diff检查和两次打包字节比较通过。包SHA-256 `84fb7347938638567ac0aab5b02e2d86823742badb3531631e5fb7a57d059f3a`；来源manifest哈希由打包和完整套件核对，未改动来源快照或依赖。

修复前证据：配置新样例在原模块上出现8个失败断言和1个缺少差异字段错误；诊断15项新测试对内存加载的基线模块产生15个失败断言（覆盖11个方法及子案例），无错误，四个兼容控制通过。最终保留失败回归，不放宽既有断言。独立复核另指出取消仍创建输出违反ENV-T123，现已修复并保留拒绝不保存/明确阻塞报告可保存的双向测试。

配置差异只含私有内存原始字节位置和前后policy token，公开预览不变；域名标签、已知前置MATCH/DOMAIN-SUFFIX覆盖和多修改失败原子拒绝有合成证据。其他规则/provider/修改器仍未知，不证明完整规则图、GUI合并或实际路由，无apply。诊断保持最初60秒预算，锁定暂态上下文/取消适配异常，阻止DNS清洗错误后继续采纳结果；旧事实/样本保持历史状态。回调和同步原生API仍须自行有界，本次不是硬实时抢占保证。

新测试仅用合成配置与注入上下文/解析响应，禁止真实socket解析和进程启动；完整套件原有自有临时文件/回环夹具不等于用户设备或公网探测。无真实配置访问、用户设备操作、生产可信宿主实现或新增权限。当前批次macOS/Windows、Linux Python3.10与实际CI均待精确提交执行；历史绿色不继承，8项跳过不算通过。原218项完整验收仍未关闭。

回滚：撤回本批模块/测试/文档变更即可；没有用户状态迁移、配置写入或运行服务。取消无保存为本批行为收紧，其他显式新文件输出契约保留。


## Agent修复接线（2026-10-16，本地独立复核）

基线`553450cae2f48fcdb1cd1335ad9e11b43a131c51`。新增`repair_cli.py`、`repair_execution.py`及两份测试；本节只描述该接线快照，不包括后续实际Clash版本适配增量。Linux完整946项：938通过、8跳过，独立运行16.829秒；限定repair测试27项通过。Node8项生命周期、合成交互协议、运行时/工具compileall、diff检查和两次发行包字节比较通过。此快照包SHA-256为`1d7ceb48a68fe083ab3ec7fdda8a76fad14e5958e5f2ceb6993d2d9b21db44ae`；后续代码或SKILL变化须重建，不能沿用此摘要。

独立审阅推动修正参数错误泄露、私有差异无法供非交互Agent审阅、差异与保留计划摘要未绑定、初始取消仍读计划、原生资源退出错误丢失恢复批次，以及提交/清理双重失败时的批次丢失。对应回归保留；未删除或放宽既有断言。测试覆盖过期/变更请求和计划、目标/备份范围、同字节inode替换、取消、写失败、读回后上下文变化、独立恢复、恢复后旧计划重放及后续编辑冲突。

真实宿主核对对话授权，脚本检查确切计划与文件状态；无JSON授权开关、终端确认码或可指定的动态执行器。生产`_native_session`始终拒绝，测试中替换该函数只用于专用临时文件的事务接线验证。不能把合成通过解释为Clash原生适配、真实写入者排除、GUI合并/重载、实际路由或用户设备验收。真实Mac、Windows及本批精确提交CI均not_run；PC0保持关闭，无真实配置或凭据读取、设备修改或公网探测。

保留计划是明确请求的新私有文件输出；其有效期、精确原快照、候选、请求摘要、目标和备份路径绑定不构成授权。失败不承诺未修改，已有恢复批次须私下检查，prepared不自动重放。回滚本代码增量为撤回新模块/测试/文档及打包条目；本次仅临时夹具，不存在用户设备配置需要恢复。后续真实操作恢复依独立`recovery_cli.py`契约，不覆盖后来更改。

### 同批追加：固定2.5.8声明链校验（2026-10-16）

追加只读`clash_verge_258.py`、14项合成测试及明确打包条目后，独立Linux完整960项：952通过/8跳过，19.220秒；repair27项与声明链14项分别通过。Node8项生命周期与合成交互协议、compileall、diff及两次打包比较通过。最终SKILL说明更新后的包SHA-256为`eabe2a91298306e3301d52e377b2d7f0da87185359e3c5578710219a776e3ebb`。开发者稍早独立包`e87e8b3bc96d66082954146bf75f2485a0cfd87ddf59b0bf633d9d43547473c9`与此包逐条比较只有SKILL.md不同，运行时代码相同；本节最终摘要以说明已更新的`eabe2a91298306e3301d52e377b2d7f0da87185359e3c5578710219a776e3ebb`为准。

2.5.8声明链只消费显式提供的三份字节快照，匹配应用元数据和current→profile→option.merge→唯一merge条目/文件名，绑定私有摘要。独立审阅实证plist默认解析会接受相互冲突的重复bundle键；现XML和binary重复键均拒绝并有回归。UID/文件归属重复、非merge目标、断链、路径穿越、格式混淆、缺依赖、取消及预算均有合成证据。保守basename和显式option.merge子集不宣称覆盖全部原生产品格式；脚本/序列链仍阻塞。

此增量不连接生产执行门禁，supplied_metadata_only不是实际安装、活动配置、内核版本或原生归属证明。真实Mac读取/写入、GUI与服务互斥、合并后规则、应用接受/重载和网络效果未由本地测试建立。用户已确认Agent对话授权设计不替代具体文件读取、依赖安装或实际配置变更授权。当前补丁尚未提交/推送，后续原生补丁合入须重新独立评审和测试。

## Mac 限定只读检测与明确阻塞（2026-10-16，未推送）

基于 `553450cae2f48fcdb1cd1335ad9e11b43a131c51` 的独立干净克隆，未覆盖用户改动。
授权本机执行器与命令沙箱分别记录；下列不是全范围原生验收或网络/配置操作许可。
未读取订阅正文、秘密、私人浏览器数据或个人配置哈希；来源快照及manifest未变。

| 检查 | 结果与范围 |
| --- | --- |
| 基线完整单元/回归，命令沙箱内 | 919项：767通过、39失败、64错误、49跳过；回环受沙箱限制，不当成产品网络失败 |
| 基线完整单元/回归，本机执行 | 919项：799通过、39失败、45错误、36跳过 |
| 修改后完整单元/回归，本机执行 | 930项：810通过、39失败、45错误、36跳过；84个失败/错误测试名称与基线完全一致，无新增失败 |
| 失败分组 | config_edit_plan 28、recovery_cli 20、transactions 36；前者缺可选PyYAML，后两者自有临时文件携带系统provenance，事务按既定拒绝xattr契约阻塞 |
| 相关定向检查 | native_context 29/29、inventory 15/15、status_dashboard 26/26、diagnostic_session及boundaries 69/69；native_context_smoke 21通过/1未启用的CI原生测试跳过 |
| 旧代码回归反证 | 将新测试置于基线临时副本运行三个代表案例：路径原因、进程架构、代理摘要投影；1失败/2错误；修复后对应全部通过 |
| Node / compile / package | 两组Node合成、compileall、重复打包字节一致；脱离源码包的9项测试亦包含于完整套件，均通过；包哈希见独立本地交付回执 |
| Mac只读事实链 | check取得8字段，无采集错误；S04仅进程架构，check→analyze/plan及面板投影完成；gate closed、无changes、空plan diff、面板unknown |
| 严格上下文 | 本机capture为RUNTIME_PATH_INVALID，首个固定诊断executable/symlink；原筛查保持。命令沙箱为CONTEXT_INACTIVE，不能混用结论 |
| 部分上下文 | 本机metadata API观察到same-user active console；无句柄、continuity not_established、runtime integrity not_verified、namespace unknown |

运行命令：`python3 -m unittest discover -s tests -v`；
`node tests/webrtc-lifecycle.cjs`；`node tests/dashboard-interaction-protocol.cjs`；
`python3 -m compileall -q skills/claude-guardian/scripts`；
`python3 tools/package_skill.py --output <新的临时ZIP>` 连续两次并比较字节。
本机完整套件中的回环及文件写入只涉及测试自有临时对象，未执行真实配置写入或恢复。

临时文件最小复现：对专用临时目录先规范化，再创建普通文件并调用`transactions.plan`，
原生`_has_xattrs`为true，plan返回`UNSUPPORTED_FILE_METADATA`。对两个自有临时文件
使用Darwin `fgetxattr/fsetxattr`复制provenance返回0并回读字节相等；复制前两者属性已相等，
因此这只证明本次幂等setter可调用，不证明从不同原值恢复、完整元数据/ACL保留、
GUI写入、真实配置或应用恢复。没有删除/忽略属性，也没有开放生产事务支持。

待授权/补证：如需全套解析器测试，须批准独立临时venv中的固定PyYAML安装及PyPI请求；
未安装。GUI profile引用、持久扩展目标及写入者暂停方式需要另获精确读取/交互范围。
没有为DNS/HTTPS/STUN、控制API、浏览器、系统代理/DNS/TUN/防火墙变更或权限调整授权。
PC0保持关闭，未启动、解析或联系Claude/Anthropic。未创建PR、提交或推送。

回滚：撤回本批代码/测试/说明补丁；无用户系统设置需恢复。全套未通过，禁止据此发布
“Mac修复已验证”或关闭原ENV/VAL验收。Linux/Windows和最低Python版本本轮未执行。

## 同日后续：隔离解析器与原生临时元数据实验

前节的两项待授权随后获明确批准：任务临时venv中的固定解析器安装，以及仅本地读取
profile索引和当前关联扩展。未获得实际配置写入、核心启动/重载或系统网络变更许可。
使用已有受管CPython3.12.14创建临时venv；系统Python3.13.3未改。安装PyYAML6.0.3，
索引为官方PyPI、wheel来源files.pythonhosted.org，SHA-256
`fc09d0aa354569bc501d4e787133afc08552722d3ab34836a80547331bb5d4a0`。
没有安装额外运行时或改变全局证书/代理设置。

同一代码的930项本机全套使用该venv重跑：865通过、20失败、36错误、9跳过。
config_edit_plan不再失败，原56项事务/恢复失败均为UNSUPPORTED_FILE_METADATA；
不能将缺解析器已解决等同于全套通过。前节3.13.3证据与本节3.12.14分别保留。

只读适配取证发现需覆盖的真实结构：当前关联merge为仅注释/空白的空文档，
不能被既有严格mapping编译器当成完整配置；rules扩展为prepend/append/delete三个空列表。
索引关系唯一，关联普通文件在读取期间稳定、当前用户/组拥有、无硬链接；
不据此证明GUI持久性、合并优先级、写入者暂停方式、核心版本或适配器可应用。
原文、UID、实际扩展文件名、节点、订阅、凭据和个人配置哈希均未导出。

自有临时文件通过Darwin fcopyfile(COPYFILE_ALL)复制可访问属性、数据和mode/owner/group。
第一次连续复用descriptor未复位offset，API返回0但restore内容不等；保留该失败。
本机Apple copyfile(3)明确说明fcopyfile不重置源/目的seek位置。
第二次复位两端offset后，备份/恢复内容、两个可见xattr（含provenance和自有测试marker）、
mode/owner/group逐项相等，原文件不变、未删除属性。marker起初不同，确实恢复其值；
provenance原值已相等，未证明不同来源provenance恢复；显式ACL/完整应用恢复未验证。
该实验不改变生产事务拒绝xattr的契约，不开放修复编排或真实应用能力。


## Mac v2补丁云端合并独立复核（2026-10-16）

收到的14文件补丁SHA-256为`827bfd077e5081f6ed276aba9a2f77df4c579c15badf3c2d919ee199e374b92d`，脱敏证据JSON为`712f6b27d4a4bc7ba67d3642610a2ef81d9a7804be777489631160ebae3509e9`；ZIP完整摘要为`e177364741285409abfff26ffe47a365a4ebb7d934b86b41cfc06d40c778b3c3`。云端逐项核验后合并，CHANGELOG和validation仅作追加合并，保留先前Agent修复接线与2.5.8声明链工作。原始交付JSON和两个临时复现脚本未加入发行清单，未在云端冒充Mac运行。

本组合快照Linux完整971项：963通过/8跳过，16.541秒；native_context29、inventory15、dashboard26通过，native_context_smoke22项21通过/1跳过。三个代表新增案例在独立553450ca基线副本上重现1失败/2错误（缺路径诊断接口、缺S04进程事实、缺Mac代理摘要显示），合并后通过。首次反证命令在错误工作目录因模块导入失败，修正工作目录后得到上述功能反证，不将导入错误算作旧行为证据。

Node8项生命周期、合成交互协议、compileall、diff检查及两次打包逐字节比较通过，此组合快照包SHA-256为`21c84da2516ac666f84374871f029257ba08b79c8020697890ed6a623f6450ed`。Linux合成绿色不覆盖本机930项套件的56个元数据失败；Mac strict capture仍阻塞，事务xattr门禁未放宽。真实Mac观察取自已核验交付证据，云端没有新设备访问、依赖安装、网络探测或真实配置变更。后续规则扩展候选编译器不包含在本节971项快照；合入后须另行评审和完整重测。未提交或推送。

## 统一rules候选接线组合复核（2026-10-16）

在上述Mac v2与Agent修复入口上增加空rules扩展编译器及同一CLI的显式rules-prepend路线；所需应用plist、profile索引、基础配置与扩展UID均显式传入，安全读取后只验证所提供声明链。保留计划0.2绑定这些文件的精确路径、父目录及快照；旧0.1必须重新生成、展示并确认。候选只插入既有空prepend，delete限定为空，保持append及其他字节；已知保护规则冲突拒绝，未知链和声明事实继续阻塞。未接入真实原生写入适配。

独立Linux复核完整1003项：995通过/8跳过，16.816秒。相关73项覆盖原修复接线27、编译器17、rules CLI12及2.5.8声明链17：含共享profile引用/全局UID拒绝、源文件同内容换inode、错误基础profile文件、私有差异前源/请求刷新、最终适配复核回调修改基础源后在提交前停止且保留备份、生产门禁不写目标。合成适配器替换仅用于临时夹具，不构成宿主授权或原生验收。

Node合成交互协议、8项WebRTC生命周期、compileall和git diff --check通过；两次新文件名打包逐字节相同，SHA-256为`96c47e39828bd48f93e75411ebcad4de2d1520fc25e6dd227143baf5300ddef3`。打包显式包含rules_extension_plan、repair_cli、repair_execution和clash_verge_258，未加入私有配置/交付证据文件。本节不覆盖此前Mac930套件仍有的56项元数据失败；无新Mac执行、真实设置写入、应用重载或公网探测。原生上下文、元数据完整恢复、GUI写入者排除、有效合并链/核心/路由及真实恢复验收保持开放。当前仅本地组合复核，未提交/推送，远端四任务CI及受影响浏览器CI尚未执行。

回滚范围：撤回本批新增候选/接线与只读诊断代码、测试和说明，或仅撤回rules路由与对应发行清单项；不需恢复任何用户设置。已保留旧计划不得自动迁移或重建授权。实际修复任务仍未完成。

## 2921e4f 后的 Mac 原生适配调查（未推送）

本次使用独立干净克隆，精确基线2921e4f72ba0c0bcd2d37bdfb6d5410248f045e6；旧工作区及14处修改保留。使用已批准的CPython3.12.14任务临时venv、PyYAML6.0.3，无新依赖安装或系统Python变更。

| 检查 | 结果及限制 |
| --- | --- |
| 新发布基线完整单元/回归 | 1003项：903通过、25失败、66错误、9跳过 |
| 新工具后完整单元/回归 | 1015项：915通过、25失败、66错误、9跳过；91个失败/错误测试集合与本机基线完全相同 |
| 失败分组 | repair_cli12、repair_execution12、rules_repair_cli11、transactions36、recovery_cli20；已有严格临时文件元数据/回执边界阻塞，未改断言、删属性或放宽实现 |
| 新合成边界 | macos_metadata_probe12/12：双端offset复位、失败反例、ACL资源释放、xattr读取预算/短读、缺失provenance及setter/回读不符不能作为恢复成功；不调用原生API |
| 真机临时文件 | Darwin ACL API为当前用户创建不同显式ACL；不同内容/mode/group/普通xattr/ACL先成立，fcopyfile(COPYFILE_ALL)备份逐项相等，原对象不变；复位offset恢复之前反例已恢复元数据，仅内容恢复成立，不证明不同元数据恢复 |
| 真机失败保留 | 初次numeric-name chmod设置ACL失败；改用已核对SDK的当前用户UUID ACL API。未复位offset时API0但内容不等。两份批准运行时有真实不同provenance，但fixture setter后的即时回读为false/true/true，未形成不同值，不能关闭该验收 |
| 未完成元数据 | 不同owner需跨用户/提权授权，未尝试；压缩/资源fork/flags/timestamps及完整应用恢复未覆盖。生产事务仍拒绝xattr |
| 严格运行路径 | 正常拼写的symlink仍阻塞；真实规范路径的新隔离子进程完成capture/recheck，但mode screen仍拒绝非root/可写，integrity未知、namespace未知、gate closed；Apple CLT Python3.9.6低于最低版本 |
| Verge只读取证 | 产品/build仍2.5.8；current及merge/rules关联唯一且读取稳定，merge仅注释/空白，rules三列表空；现有supplied validator保留链/core/上下文/写入者阻塞，不是native admission |

命令：`python -m unittest discover -s tests -v`；`python -m unittest discover -s tests -p test_macos_metadata_probe.py -v`；`python -B tools/macos_metadata_probe.py`（可按已批准范围提供两个runtime metadata source）；Node两组合成、compileall及重复打包字节比较完成。发行包SHA-256仍`96c47e39828bd48f93e75411ebcad4de2d1520fc25e6dd227143baf5300ddef3`，新工具只属开发证据，不进入发行清单，来源快照/manifest未改。

官方Verge tag源精确为4337bd85758d54d7b9044b2da3c9ac1176eae1f3，仅下载/阅读，未构建或运行。具体保存、内存编辑器、定时刷新、重载失败重启/服务替换和GUI退出路径及最小后续授权方案见macos-native-adaptation。未读取订阅payload、脚本正文、控制器凭据或个人配置哈希；未发控制API/网络探测，未暂停/重载GUI或core，未改真实配置/系统网络。原始失败日志保留本地，移交仅项目补丁与脱敏固定结果。回滚仅撤回开发工具、测试与说明，无用户设置需恢复；未推送/PR，未关闭原生修复准入。


### 云端整合复核及恢复实验修正（未推送）

导入ZIP的SHA-256核对为`788a7015f2e5d113f74c645c25068f6ab869e53615ecf0c9a72e9931be9a6f99`，7文件补丁可干净应用至2921e4f。云端初始完整套件1015项通过（1007通过、8跳过），Node两组、compileall、diff与复现打包通过，发行包哈希不变。

发现原生实验的负例已先恢复ACL/group/mode/xattrs，使随后正例只比较已相等元数据。工具现于正例前重新建立差异并立即采集`different_before_reset_restore`，独立验证provenance重置回读，另补2项合成回归。历史Mac结果不替代修正后的原生重跑；不同元数据恢复仍待验证。未修改生产事务/准入，没有Mac操作或真实配置变更。

修正后云端完整套件1017项（1009通过、8跳过），14项probe回归通过；新编排测试仅自有临时文件、不调用Darwin元数据API。两组Node合成、compileall、diff检查和两次打包再次通过，发行包SHA-256仍为`96c47e39828bd48f93e75411ebcad4de2d1520fc25e6dd227143baf5300ddef3`。该云端修正时点无提交/推送、Mac修正版尚未运行；后续回调状态见下节。


## Agent环境驱动修复与Mac调查组合交付复核（2026-10-16，未提交/推送）

精确基线为2921e4f72ba0c0bcd2d37bdfb6d5410248f045e6。组合13文件：Mac工具/测试/说明7文件，加主Skill、强制安全参考、Agent修复参考、只读选择器、选择器测试与发行清单6文件。Agent继续承担环境限定修复；内置能力缺口不要求等待通用自动写入器。每次实际操作的权限、PC0、目标绑定、影响、备份恢复和真实复测保持独立；选择器没有写入执行或成功修复能力。

- 最终完整云端命令：`python -m unittest discover -s tests -v`，1033项，1025通过、8跳过，18.170秒
- 选择器16项与Mac probe14项定向回归通过；涵盖实际会话/修复权限与上下文错误、陈旧证据阻塞、两种规则模板、错误输入脱敏、未识别项继续调查、取消优先及恢复fixture重建
- `node tests/webrtc-lifecycle.cjs`：8项合成场景通过；`node tests/dashboard-interaction-protocol.cjs`通过。没有真实浏览器执行
- `python -m compileall -q skills/claude-guardian/scripts tools/macos_metadata_probe.py`及`git diff --check`通过
- 两次`python tools/package_skill.py --output <独立新路径>`逐字节相同，SHA-256为`5857e5cf5e77072704f2d9ab77aff61bf120e7c86e015484612e1f00b8362127`。解包后catalog/select可运行、prepend模式与4个来源参数完整、未知命令/参数不泄露传入值、两份修复/安全参考均存在
- 发行包包括Agent选择器及参考，不包括Mac开发probe、私有配置或移交证据；来源快照及manifest未变

独立复核修复了：prepend误用默认merge-policy模板、非字符串schema的未处理异常、实际PC0/上下文/权限/快照/恢复错误误归缺适配、CLI错误回显输入以及强制安全参考的旧手工交接措辞冲突。最终未发现阻断性审查问题。这是代码/文档批次复核，不是任何用户环境已修复的证明。

### 修正版Mac回调与证据限制

已读取Mac任务回调：14项定向测试通过；两次临时文件实验的`different_before_reset_restore`在contents/mode/group/普通xattr/ACL上为真，正例复制后对应比较为真，`original_unchanged`为真。provenance即时差异为假，仍不能证明不同值恢复；不同owner、压缩、resource fork、flags、timestamps及完整应用恢复亦未覆盖。

该次上传因握手失败，云端尚未收到/下载/校验修正版结果JSON或完整证据包；上述内容仅标记为任务回调报告。旧ZIP已校验不等于新结果已校验。先前Mac完整基线1003项为903通过/25失败/66错误/9跳过，原工具1015项为915通过/25失败/66错误/9跳过，91个失败/错误集合不变；本次没有组合1033项的完整Mac或Windows实测，不用Linux通过覆盖这些缺口。

风险与回滚：本批改变Agent动作指引及只读选择器，新增开发实验；不改内置生产事务/准入、不执行真实网络或配置动作。撤回本批13文件对应差异即可回退代码，不需恢复用户系统设置。原Mac元数据/运行时/写入者/有效链及应用恢复缺口继续开放。此快照未提交/推送，远端push CI尚未运行；后续直接main交付须取得本批明确授权，核对远端基线，普通非强制提交并逐平台跟踪CI。


## 9caa42f推送CI与Windows窄修正（2026-10-16）

用户明确批准上述13文件后，以expected-SHA=2921e4f、非强制更新发布9caa42f7366f1d319265dc771449dcf7feeaa088；远端tree e5375a33d89f5f759274daa0e43b19a5bd3aab4d与冻结本地tree完全相同。本地仅同步index/ref，没有覆盖或删除工作文件。

[单元工作流38894445411](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38894445411)已终止为failure：

- Ubuntu：1033项，1025通过、8跳过；native context smoke22项/1跳过通过
- macOS：1033项，1024通过、9跳过；native context smoke22项/1跳过通过
- Python3.10 Linux：1033项，1025通过、8跳过；独立发行包运行时9项通过
- Windows：1033项，869通过、1失败、3错误、160跳过。四个问题均定位到新批次：选择器JSON中文stdout的cp1252编码错误、测试源码默认编码读取错误、两项Mac合成测试mock不存在的geteuid/pwrite。后续always PowerShell诊断1项通过，不替代失败的主套件
- [合成浏览器工作流38894445231](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38894445231)成功，包括Chrome截图、键盘/布局检查与合成产物上传；不代表用户真实浏览器环境验收

窄修正仅将选择器JSON改为ASCII转义（json解析值保持不变）、测试源码显式UTF-8、两项probe测试使用模块局部OS替身，不改产品平台支持、不删除测试或新增Windows跳过。新强制PYTHONIOENCODING=cp1252/PYTHONUTF8=0的回归在原9caa42f脚本上重现UnicodeEncodeError/exit1，修正后通过；原有重置、复制顺序和结果断言保留，增加descriptor关闭检查。

修正本地验证：17项选择器测试与14项probe测试通过；完整1034项，1026通过、8跳过，17.603秒；两组Node合成、compileall、diff检查通过。两份新包逐字节相同，SHA-256为`6c589234b1293fb3ab6263fb8b3700b760ce75a5751a7b9f9cb8c1aae307d3ab`。独立审查未发现阻断性问题。仅此本地验证不能称修正后的WindowsCI通过；该窄修正未提交/推送。

### 修正版Mac证据文件补齐（无新增实验）

上传重试后收到仅证据ZIP，SHA-256为`6511463d741d4fdb5463917462b4080f1670cafa59e3cc5110a11a760e0f102d`。已下载并校验manifest所列两份JSON的大小/哈希，取代上节的callback-only限制；不冒认重传过程执行了新的原生实验。

两份结果均记录正例前contents/mode/group/xattrs/ACL差异为真，reset-offset恢复全部7维比较相等，original_unchanged为真；nonreset反例仅contents比较失败。owner/provenance正例前差异为假，provenance回读问题未消失，不证明不同值恢复。14项Mac定向测试通过来源仍为任务报告，JSON不是完整测试日志。用户Mac原91个失败/错误保留；本次hosted Mac1033通过不能替代用户设备重测。生产原生准入、运行时信任、写入者排除、不同owner/其他元数据与完整应用恢复仍未验收。

本修正回滚仅撤回对应代码/测试/记录差异，不需恢复用户设置；没有新增真实设备操作或权限。

## 2026-10-18 重建批次 1：验收范围与回滚

起点为已发布 `584064fc9c210e684ba4a0e11b79db74f1946155`。缺失的旧工作树不是
新的验收依据；本批从该起点重新复现问题并执行回归。基线完整发现1034项：1026通过、
8跳过，13.356秒。原218行完整条件和验证层哈希保持
`84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`。

涉及 M00/ENG-01 的事故状态与取消、ENV-06/ENG-08/VAL-02/07 的计划新鲜度、
Agent 修复选择器中的权限/取消/来源诊断。全部使用离线输入、自有临时文件与注入故障；
无Mac/Windows新增真机结果，无平台接触，无生产修复准入变化。

已知限制：保留计划在创建后才发现取消/变化时可能留下私有产物，但不返回有效当前摘要；
不盲删可能已被替换的路径。因此不据此关闭 ENV-T123。完整原条件以台账 requirement 为准，
不能用后续步骤摘要放宽。旧schema-1事故缓存需要明确归属/澄清，不能冒充当前事故证据。

回滚为还原本批列出的源码/测试/文档改动至起点，保留既有原始来源、旧平台证据和其他人的
独立提交。没有系统配置回滚需求；本批未变更系统设置。提交及推送需依AGENTS的精确批次授权；
推送后各平台CI须记录精确提交结果，跳过不得算通过。

本批冻结后的新验证：`python3 -m unittest discover -s tests -v` 共1073项，
1065通过、8跳过，13.229秒；两组Node合成测试（WebRTC生命周期8场景、面板交互协议）、
`compileall` 与 `git diff --check` 通过。两次独立打包逐字节相同，发行包SHA-256为
`25df240a43df4d47640a8564bf0a73a4f4cfde7df38e89c0c476dcb33dae5216`。
独立审查重新执行166项定向测试并重现修复前的问题，冻结版本未发现剩余阻断项。
这些测试属于离线/合成证据；218项完整设计验收状态仍为待重新核验，没有据此宣布真机通过。

## 2026-10-18 重建批次 2：限定的导出取消与接口一致性

本批在第一批冻结副本之后另行修改。ENV-T123 中已经识别取消、尚未开始导出的分支
不再调用新文件写入器；取消输入、分析/计划、采集中断与取消错误均使用离线夹具复现。
正常导出及现有退出语义保留。写入器开始后的中断、目录准入和原生续接重采仍未验收，
故不能将此子条件修复写作整个 ENV-T123 通过。回滚为撤回第二批对应差异，不修改系统设置。

访谈CLI新增固定错误输出，避免未知参数和底层输出异常中的私人值回显；令牌形态筛查
在既有 sk- 规则上补 ghp_/github_pat_，不会声称识别任意秘密。普通别名仍可私有保存/续接。
来源清单区分最初八份输入与当前七份阅读材料、两份设计快照及PDF派生文字层，
原资料字节、分发哈希及原署名不变；不据资料提供者许可推断所有第三方素材许可。

第二批冻结代码完整回归1100项：1092通过、8跳过，13.568秒。两组Node合成、
Python编译和diff检查通过。两次发行包逐字节相同，SHA-256为
`88c99d94aef25b86739a8627f35947fff0c44f22eef6e29420786c225dc83e59`。
真实离线闭管道回归检查独立CLI退出码2及固定错误信息；嵌入调用不关闭调用者流。
已获准私有保存成功但后续输出失败时保留文件并在可用错误通道标明saved=true，
避免把输出失败误报为保存未发生。不声称任意秘密都能自动识别。

第二批独立只读审查重新执行163项定向测试全部通过，另以正常/无效参数/help三条路径
关闭stdout进行验证，未发现剩余阻断项。没有新增网络/真机操作或推送。

## 2026-10-18 重建批次 3：报告字段与事故证据新鲜度

D-ENV §19.5 明确禁止P17存储密码、UUID和真实节点主机。旧输入校验却接受任意标量，
使合成UUID进入直接API、stdout及请求的导出文件。本批仅为当前已实现字段定义类型和
取值边界，未实现字段只接受明确缺口；reason/coverage限定为现有生产者值。保留Mac语言
列表等已有生产者格式。已支持格式并不证明事实真实性，也不代表识别任意秘密。

事故来源/时间相同的明确重放不再重新开启已解决事故或复活失效证据。较旧或同时间
矛盾的替换需明确correction=True；该标志不是任何外部动作许可。未指定观察时间的新
用户回复保持新回复语义，不能仅凭相同来源/值当作重放。没有新设TTL或验证外部时间真实性。

第一批已获本批明确授权并直接发布为de80b76de3fdfb3bb02c392ef1c5a260a01b2041，
父提交584064fc，远端精确15文件及blob身份/模式已复核，无额外删除或修改；推送CI结果另记。
第二/第三批不包含在第一批发布中。本批回滚只撤回自身差异，不改变第一批提交或系统设置。

第一批push CI已终止成功：[单元与跨平台工作流39095340191](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095340191)、[合成预览39095340314](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095340314)。
Linux为1065通过/8跳过，macOS为1064通过/9跳过，Windows为902通过/171跳过，
Python3.10 Linux为1065通过/8跳过；合成预览27项通过。原生context capture中，
Mac因RUNTIME_PATH_INVALID（可执行文件符号链接）、Windows因CONTEXT_FOREIGN跳过。
这些限制保留，不把hosted绿色CI或跳过项冒认为用户真机验收。

第二批按当前项目交付授权直接发布为d8f4e2bb01ea16f847b101bc9048183f85622736，
父提交de80b76；精确12个增量路径及远端blob/模式已复核，无额外删除或修改。
该次发布未包含第三批修改；第二批push CI仍需单独记录终态。

第二批push CI已终止成功：[跨平台39095520668](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095520668)、[合成预览39095520551](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095520551)。
Linux1092通过/8跳过，macOS1091通过/9跳过，Windows929通过/171跳过，
Python3.10 Linux1092通过/8跳过；合成预览27通过，独立发行包运行时9通过。
Mac可执行文件符号链接及Windows外部上下文导致的原生capture跳过继续保留；不替代用户真机。

第三批冻结后完整回归1133项：1125通过、8跳过，14.011秒；两组Node合成、编译及diff检查通过。
两次发行包逐字节相同，SHA-256为
`4daca3ec5db27c73a3c0195ed910ef958577a94817a847cf75364a0f630a6c37`。
独立审查重新执行213项定向测试，所有已发现反例均已修复，未发现剩余阻断项。
保留普通短别名、长task别名、Slovak语言标签、长语言列表和既有原生生产者格式；
不将任意字符串、来源名或格式通过当成真实性证明。原218例与原始来源字节未改。

第三批已普通非强制发布f87fdbf426097eae22cefa9fea7a2febe3e611d7，父提交d8f4e2b，
精确7文件路径/SHA/blob/模式已核对，无额外删除或修改。推送工作流
[39095809216](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095809216)及
[39095809124](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39095809124)均终止成功。
Linux1125通过/8跳过、Mac1124/9、Windows962/171、Python3.10 Linux1125/8；
预览27通过、独立运行时9通过。原生capture仍分别因Mac可执行文件符号链接和Windows外部上下文跳过。

## 2026-10-18 重建批次 4：逐例云端证据

本批来源去重助手只处理调用者已获准读取的有限公开字节与非识别性别名，内部计算SHA-256并比较字节，
不接受调用者伪造摘要，不读文件、不联网、不执行原文。输出不含原文；不同内容组不意味着独立来源。
过大、空、无法读取或不合格输入不当作已经完成去重核验。原资料字节与各自许可归属保留。

路线重放是规范化合成输入到当前访谈API的确定性测试，加上活动Skill/路线卡逐句内容审阅，
不宣称对任意模型自然语言理解、完整部署或用户真机作了测试。T24的保存续接虽然保留VM/VPS路线，
但环境变化复核还未接入必经续接流程，明确保留待办，不把局部成功当整例通过。
本批回滚撤回对应帮助器、打包条目、测试及证据差异，不触及系统配置。

Fourth-batch aggregate checks (2026-10-18 UTC): 1,153 tests ran in 14.636
seconds, 1,145 passed and eight skipped. Both Node synthetic suites, compilation
and whitespace validation passed. Two package builds were byte-identical:
`afcd86b25476300a2465c51a354cff22fc8feadcfe62bde64d46d792a77c4b7f`.
Independent review supports only T09/T19/T20/T21 at original L+C layers using
the pinned evidence pages; 214 original cases, including T24, remain pending.
These counts do not imply native or arbitrary model acceptance.

Fourth publication `6e0688f` CI was not fully green: Windows reported one test
error decoding the UTF-8 source manifest with locale-default cp1252 (981 passed,
171 skipped); its later capture/compile/package stages were skipped. Linux
1,145/8, macOS 1,144/9, minimum Python 3.10 Linux 1,145/8 and preview 27/27 passed.
The closed-pipe regression also emitted a Windows reader-thread exception while
marked passing; this is recorded rather than treated as clean output.

The follow-up changes only test portability: explicit UTF-8 manifest decoding and
removing the already-closed stdout handle before communicate starts reader
threads. Original assertions remain. T09 test-file/evidence pins were refreshed
following review; production source bytes and package are unchanged. Fresh local
aggregate: 1,153 tests in 14.455 seconds, 1,145 passed and eight skipped; both Node
suites, compilation, diff checks and identical package builds passed. Windows
confirmation depends on the follow-up remote CI; no local Windows result is claimed.


Fifth batch closes only the synthetic post-incident stale-contact subgap. See
[evidence and host contract](evidence/rebuild-contact-freshness.md). Full aggregate
1,178 tests: 1,170 passed, eight skipped, 14.406 seconds. Both Node suites,
compilation, whitespace and repeatable packaging passed; package SHA-256
`1be01bb2ebe08fa589cf43adec74d1f52673a254316708a45879aaba9e368ba3`.
ENV-T81/89 remain pending; no native/contact action occurred.


Published follow-up results: `386da6c` fixed the Windows test portability issue;
all four triggered CI jobs passed, and Windows logs contain neither encoding
errors nor the prior reader-thread traceback. Preview was not triggered for that
test/docs-only change. The next runtime batch `7f30247` passed both workflows and
all five jobs: Linux 1,170/8 skipped, macOS 1,169/9, Windows 1,007/171, Python 3.10
Linux 1,170/8; preview 27/27 and detached runtime 9/9. Native-context skips persist
and are not user-device acceptance. Remote main and exact file deltas were verified.

Sixth batch: supported exact-repeat prepend and already-correct merge selections
can report no change in supplied snapshots without creating a transaction or
retained artifact. Mixed selections change only needed tokens. Freshness checks
and incident/prerequisite precedence remain. See
[evidence and limits](evidence/rebuild-idempotent-replanning.md); full ENV-T60 L+R
remains incomplete. Second aggregate rerun: 1,207 tests in 14.762 seconds, 1,199
passed and eight skipped. Both Node synthetic suites, compilation, diff checks
and two identical packages passed; SHA-256
`ac389186fc8a45b99e5d35da090441bbb15c04f52d49e6329543ea1360813f57`.
Independent review reran 151 focused/integrity tests with no remaining blockers.

Sixth publication `94983007` passed both workflows and all five jobs: Linux
1,199/8 skipped, macOS 1,198/9, Windows 1,021/186, Python 3.10 Linux 1,199/8;
preview 27/27 and detached runtime 9/9. The 15 additional Windows skips are new
POSIX-only CLI/file-transport regressions, not Windows acceptance. Native-context
capture remains skipped on Mac/Windows. Exact remote delta and parent verified.

Seventh batch: explicit interruption review retains the selected route and
same-task facts, distinguishes current replies from historical imports, and
preserves uncovered old-route obligations through purchase completion. Ordinary
loads remain ordinary loads. See [resume API](interview-resume.md) and the
[full original-case evidence](evidence/rebuild-route-cases.md). T24 joins the
four prior original L+C acceptances: five accepted, 213 pending; all original
218 rows/conditions/layers remain unchanged. These are normalized offline logic
and active-guidance results, not arbitrary-model/UI/native or permission proof.

Second full aggregate: 1,240 tests in 17.823 seconds, 1,232 passed and eight skipped.
Both Node synthetic suites, compilation and whitespace checks passed. Two package
builds matched SHA-256
`b36a139cf6d2bb0bfe2ad5b83f8cfcf2819aa3fe846ff0e107396de9a25a1e90`.
Independent full-condition review supports T24; prior T19/T20/T21 replay objects
remain byte-equivalent at their unchanged projections. Rollback code, CLI,
guidance, saved-state compatibility and evidence/ledger together; do not discard
an unresolved resume record merely to load it with an older reader.

Seventh publication `b64c159f` passed both workflows and all five CI jobs:
Linux 1,232/8 skipped, macOS 1,231/9, Windows 1,054/186, Python 3.10 Linux
1,232/8; preview 27/27 and detached runtime 9/9. No traceback appeared. Mac
executable-symlink and Windows foreign-context capture skips remain; they do not
establish user-device acceptance. Exact remote delta and parent were verified.

Eighth batch adds a pure bounded source-to-binding importer for explicit exact
lists and the existing three-field domain-rule subset. It preserves source bytes,
indexes, case, type, order, actions and supplied provenance; unsupported/conflicting
batches fail without output. No source is fetched or executed. Existing downstream
protection/version/group/staleness/native gates remain. See
[API and evidence](evidence/rebuild-rule-source-import.md). Full ENV-T40 L+R remains
pending. T09's packager pin was freshly reviewed; the five original accepted
cases and other 213 pending rows are unchanged.

Second full aggregate: 1,285 tests in 18.385 seconds, 1,277 passed and eight skipped.
Both Node synthetic suites, compilation and whitespace checks passed. Two packages
matched SHA-256 `8ccd1e7ec763445ffdbace66f9b73f5618fe8408d2b1d707e4e879de8ac18692`.
Independent review reran 144 focused checks and the exact before/after reproducer.


Eighth batch was published as `1390be90bf45f58b65eebeee8ef245b6a1aea5b7`,
parent `b64c159f6448cf3995fb62c4075d970ed5f1beeb`. Both push workflows reached
success: [tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39099770079)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39099770047).
Linux 1,277 passed/8 skipped, macOS 1,276/9, Windows 1,099/186, Python 3.10 Linux
1,277/8; preview 27/27 and detached runtime 9/9. Native-context skips remain and
do not establish user-device acceptance. All nine remote changed paths and their
exact bytes/modes were verified.


## 2026-10-18 ninth reconstruction batch

A pure fixed-profile converter now translates exact and apex-inclusive suffix
predicates between explicit domain lines, Mihomo v1.19.32 domain/classical YAML
providers and sing-box v1.12.0 source-rule-set JSON schema v1. These are selected
compatibility targets, not latest-version claims. Actions, extra conditions and
unsupported versions fail atomically. The explicit canonical lowercase ASCII
host model is a conditional matching boundary, not runtime equivalence.
See [conversion evidence](evidence/rebuild-rule-format-conversion.md).

[Controlled transaction evidence](evidence/rebuild-rule-conversion-transaction.md)
composes the unchanged POSIX API with synthetic whole-artifact temp files. Ten
integration tests include exact readback, independently approved rollback, stale
target/source rejection and conflict preservation. Post-replace receipt failure
retains prepared evidence but still requires reconciliation; it is not reported
as unchanged or successfully rolled back. This does not establish production
configuration, GUI, native-device or full ENV-T40 acceptance.

The first full suite ran 1,342 tests in 19.469 seconds: 1,334 passed and eight
skipped. The implementation worker independently repeated the same aggregate in
19.411 seconds. Both synthetic Node suites, compilation and reproducible package
checks passed; the package SHA-256 is
`574e4334b003794752103cdb4121c36a237a48b60a7e9306f0f04cea1940eb4b`.
The original 218 rows are unchanged; five exact original L+C cases remain accepted.


Ninth batch was published as `293d85644d3b26c8319247f1724ece17915e129d`,
parent `1390be90bf45f58b65eebeee8ef245b6a1aea5b7`. Both push workflows reached
success: [tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39100587276)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39100587322).
Linux 1,334 passed/8 skipped, macOS 1,333/9, Windows 1,146/196, Python 3.10 Linux
1,334/8; preview 27/27 and detached runtime 9/9. Windows gained ten explicitly
POSIX-only temporary transaction skips; these are not Windows write coverage.
Native-context capture skips remain. All eleven remote changed paths and exact
bytes/modes were verified; five accepted original cases remain unchanged.


## 2026-10-18 tenth reconstruction batch

New v2 pre-replace identity witnesses support read-only reconciliation and a
separately authorized restoration of an observed prepared candidate. New rollback
operations also persist a restore witness before replacement. Legacy prepared
records remain non-mutating; current observations never manufacture a historical
applied receipt. See [core evidence](evidence/rebuild-prepared-recovery.md) and
[CLI evidence](evidence/rebuild-prepared-recovery-cli.md).

The CLI binds independent target/batch/receipt and complete reconciliation digests,
then requires fresh terminal confirmations. Agent host calls require their own
trusted approval callbacks. Stage/backup/receipt/parent identity and generated-path
budgets are rechecked; primary errors and fixed cleanup context remain visible.
The scope is synthetic POSIX regular files under exclusion, not power-loss
certification, native configuration/application effectiveness, or Windows writes.

The final aggregate ran 1,400 tests in 27.996 seconds: 1,392 passed and eight skipped.
Earlier aggregates exposed new guard classification and a stale accepted-guidance
pin; both were explicitly corrected and re-reviewed, without weakening assertions.
Independent composed checks passed 162 tests, with 39 route/resume replays for the
recovery-only SKILL paragraph. The five original accepted cases are unchanged.
Both Node synthetic suites, compilation and diff checks passed. Two final packages
are byte-identical, SHA-256
`56876940c43f8229846df06902de98bd447b972696e2b46e035088524053dd44`.

This supersedes ninth's missing prepared recovery path only for supported new v2
witnesses. It does not retroactively make old prepared receipts recoverable or
close full ENV-T40/native acceptance. Historical ninth pins describe that fixed
published version; current core and CLI pins are in their tenth evidence pages.


Final independent review also found and closed three pre-publication defects:
backup/receipt tampering during approval, generated journal-path overflow, and
legal Unicode paths plus near-limit content yielding an unreadable applied record.
Each has an executed failing/fixed reproduction. Recovery envelopes are now
reserved before mutation and journal encoding uses the bounded canonical form;
the document ceiling is unchanged. The last boundary case rejects before any
approval or target write, while normal 4-MiB proposals still restore. These
reproductions do not establish protection against malicious local callers.


Tenth batch was published as `84f8f732288a8f89ea8c528b85ca83974a02bc0f`,
parent `293d85644d3b26c8319247f1724ece17915e129d`. Both push workflows reached
success: [tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39101971520)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39101971525).
Of 1,400 tests, Linux passed 1,392/8 skipped; macOS 1,389/11; Windows 1,147/253;
Python 3.10 Linux 1,392/8. Windows added 57 explicitly POSIX-only recovery skips;
macOS added two Linux-only long-path/budget fixtures. Preview 27/27 and detached
runtime 9/9 passed. Native-context limits remain; CI is not user-device acceptance.
The exact 16-file remote delta, byte hashes, modes and expected parent were verified.


## Eleventh rebuild batch: exact intake and enforcement cases

T53/T74/T81 were revalidated against every unchanged original L+C clause,
including accepted defaults without redundant route confirmation, first-purchase
Apple/Google/web wording, and the literal unnamed selected-plan input. The runtime
retains that selection without inventing a plan identity; a genuine missing
identity is asked once. Only a valid current CLI answer consumes that clarification;
rendering, unrelated input and invalid batches do not. These are normalized-host
offline and content results, not model NLP or current purchase/catalog proof.

ENV-T79 (L) and ENV-T90 (L + C) were independently reviewed with literal-domain
offline sentinels and full workflow output/guide coverage. Workflow guards are not
OS isolation; observed native traffic, engine effects and unmediated tool calls
remain outside these results. Evidence pages pin 14 intake and 15 enforcement
files. Previous accepted route/resume cases were freshly re-reviewed after the
relevant four-file changes; source/package checks preserve T09.

All original 218 rows, conditions and literal layer spellings remain unchanged.
The ledger now accepts 10 with current evidence and leaves 208 pending. Scheduling
is still 75 cloud-only / 113 deferred-native / 30 conditional-native, not acceptance.
Before final ledger integration the aggregate passed 1,415 of 1,423 tests with
eight skips; final integrated validation and publication evidence follow below.

Final integrated aggregate: 1,423 tests in 28.187 seconds, 1,415 passed and eight
skipped. Both Node synthetic suites, compile and diff checks passed. Two final
packages are byte-identical, SHA-256
`457a1b48ccd35e370aae3f312e22d75d0b352c41019d91e2bcd4d5b7fcc1217b`.
All 47 accepted-evidence underlying pins and original ledger invariants passed
independent review. Cloud CI publication is recorded separately after it completes.

Eleventh batch was published as `ffc786c8e735f93d82900ff528029acfc8cb884b`,
parent `84f8f732288a8f89ea8c528b85ca83974a02bc0f`. Both push workflows succeeded:
[tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39103430733)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39103430722).
Of 1,423 tests: Linux 1,415 passed/8 skipped; macOS 1,412/11; Windows 1,170/253;
Python 3.10 Linux 1,415/8. Preview 27/27 and detached runtime 9/9 passed.
Skip counts and native-context boundaries were unchanged. The exact 14-file
remote delta, expected parent, blob hashes and modes were verified.


## Twelfth rebuild batch: task scope, incident priority and invalidated grants

T34/T78/T43/T48 and ENV-T81 have complete independent review under their original
L+C (ENV literal L + C) conditions. Unanswered routes stay unconfirmed; experience
does not imply an active subscription. Explicit technical tasks synchronize both
derived intent labels, including supported task round-trips, without rewriting
facts. Credential-exposure prompts avoid the unrelated restriction/billing survey;
automatic emergency postponement is distinct from user deferral. Immediate
protective guidance is not conditioned on completing seven questions, and no
credential-revocation executor or extra action authority is invented.

A genuine failure of a current grant's prerequisites revokes its public scope
while retaining phase/contact history. A fresh review identity prevents reuse of
old passing evidence after same-binding reset/resume. Approval-time expiry also
invalidates the grant on cancellation/denial while preserving the primary result.
Unrelated malformed requests, later-stage collection and independent local plans
remain distinct. This is trusted-host workflow enforcement, not native detection
or OS/network isolation. Failing-first counterexamples were retained.

The ten previously accepted cases were rechecked before their affected source
pins were refreshed. All 218 original rows and layers remain unchanged; the
ledger now records 15 accepted and 203 pending. Scheduling remains 75/113/30.
The parent aggregate ran 1,461 tests in 29.017 seconds: 1,453 passed, eight skipped.
The worker's earlier sole stale-evidence-pin failure was retained and resolved by
explicit re-review, not a weakened assertion. Both Node synthetic suites,
compilation and diff checks pass. Two packages are byte-identical, SHA-256
`b807550e8331899646947edff1e93b89d449551475b15aa26741b8cedd8ea825`.
Final integrated ledger/pin checks and publication evidence are recorded separately.

Final integrated rerun: 1,461 total in 29.649 seconds, 1,453 passed and eight skipped.
All 75 underlying accepted-evidence pins and ledger integrity checks passed.
