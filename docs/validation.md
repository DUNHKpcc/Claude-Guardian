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


## Thirteenth rebuild batch: explicit inventory/export input boundaries

The four independently reviewed owned files were integrated onto the frozen
twelfth source without changing their hashes. Complete supported inventory and
compact interview envelopes now reject unknown fields before projection. Nested
static request fields reject before callbacks/reads, and malformed typed inputs
return fixed errors. CLI invalid arguments no longer echo through argparse;
standalone module import is covered separately from discovery-order effects.
Supported synthetic inventory retains its provenance and dashboard label. Imported
device formats do not acquire native authenticity or an open gate.

The original abbreviated provenance reproducer is now rejected by the complete
current-producer schema; a complete supported synthetic envelope independently
proves the before/after repair. No historical attachment replay is claimed.
T11/ENV-T34/ENV-T121/ENV-T124 remain pending because this is a focused subset of
public import/CLI/export surfaces, not universal secret detection or full-case
closure. The original 15 accepted cases and all 218 conditions remain unchanged.

Failing-first and independent review found projection, diagnostics, alias and
isolated-import defects; exact counterexamples and fixes are retained. The final
integrated aggregate ran 1,482 tests in 29.216 seconds: 1,474 passed, eight skipped.
Both Node synthetic suites, compilation and diff checks passed. Two packages are
byte-identical, SHA-256
`87f981156ad78d90b737029d89cd79fac37310c8d08b9ac5b9c833ea5606d596`.

The preceding twelfth batch was published as
`f57bfc825566ffe6a94874ebd662cc3fe6dac240`, parent
`ffc786c8e735f93d82900ff528029acfc8cb884b`. Both push workflows succeeded:
[tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39104444341)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39104444260).
Of 1,461 tests: Linux 1,453 passed/8 skipped; macOS 1,450/11; Windows 1,208/253;
Python 3.10 Linux 1,453/8. Preview 27/27 and detached runtime 9/9 passed.
The exact 15-file remote delta, parent, hashes and modes were verified. Skip counts
and native-context boundaries were unchanged; CI is not user-device acceptance.

## Fourteenth rebuild batch: bounded ordered policy conversion

The pinned Mihomo 1.19.32 main-rules and sing-box 1.12.0 route-rules fragment
converter preserves ordered exact/suffix predicates, duplicates and explicit
bijective ordinary terminal-outbound mappings. Unsupported semantics reject
atomically. Mapping/finality are caller declarations, not independently verified
engine behavior. No engine, network, host configuration or native repair ran.
Full ENV-T40 and controlled recovery composition remain pending. Original
acceptance remains 15 of 218 cases; all original conditions/layers are retained.

Independent review passed 118 committed checks and 183 adversarial cases.
Packaging/guidance preservation passed 66 focused checks, including the example
from the extracted release and unchanged ENV-T79/90 boundary replay. T09 and
ENV-T79/90 evidence pins were refreshed only after explicit independent review.
The integrated aggregate ran 1,508 tests in 30.195 seconds: 1,500 passed and eight
skipped. Both Node synthetic suites, compilation and diff checks passed. Two
release archives are byte-identical, SHA-256
`4bb4aad11cdc5986454af3a4f5055372c32b3d2695d089bbbaab1ba76851e4f6`.
The initial missing-module failing-first result was not separately logged; later
focused, importer, compilation and independent probes have retained logs.

The preceding thirteenth batch was published as
`8b0b2a8a877e6403d6c5ef163f52215c3d1a707f`, parent
`f57bfc825566ffe6a94874ebd662cc3fe6dac240`. Both push workflows succeeded:
[tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39104718029)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39104718047).
Linux and Python 3.10 Linux: 1,474 passed/8 skipped; macOS: 1,471/11;
Windows: 1,229/253. Preview 27/27 and detached runtime 9/9 passed.
Remote seven-file scope, parent, hashes and modes were verified. CI does not
substitute for user-device acceptance.

## Fifteenth rebuild batch: sanitized network case reference

A derived macOS DNS/IPv6/Tailscale experience reference was integrated byte for
byte from the independently reviewed public artifact. Only the derived prose is
distributed; the private original, provenance records and environment identifiers
are not included. Source IDs, historical manifests and original design rows are
unchanged. The active guide now distinguishes existing guarded host libraries
from a general active-network CLI and uncompleted native end-to-end acceptance.
This batch changes no runtime capability or IPv4/IPv6 policy default.

Six new documentation/package checks and three source-bundle checks passed.
Independent preservation review ran 182 relevant offline checks and 145 interview
checks, with zero skips, and compared five complete original-case replays.
Affected pins in all six accepted-evidence pages were refreshed after explicit
review; original acceptance remains 15/218. The aggregate ran 1,514 tests in
29.763 seconds: 1,506 passed, eight skipped. Both Node synthetic suites,
compilation and diff checks passed. Two packages are byte-identical, SHA-256
`2f3cecf66d60a48c468c29c9c67cd847596914cb2f189681280e68e8e0dd9649`.
The derived reference preserves unverified WebRTC/UDP and application-exit
lifecycle limits, configuration drift and the distinction between an empty AAAA
answer and system-wide IPv6 blocking. No original-case native result is added.

The preceding fourteenth batch was published as
`230101be81d28149b9c27c99a7047c274bb5cec4`, with verified parent
`8b0b2a8a877e6403d6c5ef163f52215c3d1a707f` and exact ten-file scope.
Its terminal push CI result is recorded separately when available.


## Fifteenth publication verification

Published `5f027d0dd033159bff95e3814c10d2732943ba3e`, parent
`230101be81d28149b9c27c99a7047c274bb5cec4`; exact 15-file scope verified.
[Push tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39106155494)
completed successfully: Linux/Python 3.10 1,506 passed and eight skipped;
macOS 1,503/11; Windows 1,261/253. Detached runtime checks passed nine tests.
The preview workflow did not trigger for this path scope; no preview CI run is
claimed. Local Node synthetic checks passed as recorded above. These hosted
results do not establish user-device acceptance.

## Sixteenth rebuild batch: scoped IPv4-only product policy

The separately dated policy defaults selected Claude application/target traffic
to IPv4-only without IPv6 fallback. Proxy outer transport, control/recovery and
other applications remain distinct. Typed private planning, Agent candidates,
interview/report consumers and the fixed dashboard projection agree on that
scope. No result reports actual enforcement, device-wide blocking or account
safety from this pure policy. Native evidence and execution remain absent.

Independent review found and reproduced three integration defects: inconsistent
private-plan constructor status, unsupported static dashboard tags, and current
report migration rejecting the additive fixed policy. Narrow fixes retain prior
privacy, active-HTML and cancellation guards. The original failing logs remain.
The fixed review passed 539 adversarial and 72 consumer checks, 27 policy tests,
17 migration tests and 27 static-preview/interaction tests. Guidance and original
case preservation were independently reviewed by a different reviewer.

After refreshing only reviewed pins, the full aggregate ran 1,543 tests in
31.288 seconds: 1,535 passed and eight skipped. Both Node synthetic suites,
compilation and diff checks passed. Two release packages are byte-identical:
`c587b28cea400a7fa063da053b32856d3e4dfd2838c859dc09ec754f8d555909`.
The 15 accepted cases retain original conditions/layers; 19 affected dependency
pins were refreshed and five shared-policy pins added (80 total). Old replay
members remain unchanged; the complete relevant objects have an additive fixed
policy, so whole-object byte identity with the prior batch is not claimed.
No native case or additional original case is accepted by this product change.

## Seventeenth rebuild batch: ENV-T40 full original L + R review

This test/evidence increment composes existing predicate and ordered-policy
conversion with actual controlled temporary-file apply, byte readback, separate
rollback and prepared-record reconciliation/restoration. The original ENV-T40
condition and literal L + R layers remain unchanged. Unsupported ASN, matching
and action semantics fail before planning/writing rather than silently dropping
content. No runtime module changed in this increment.

Independent review reran 200 supporting tests and exercised 32 additional real
temporary-artifact apply/restore paths in both directions, eight prepared-journal
gaps, 320 semantic/preservation checks and 30 atomic unsupported refusals. All
17 underlying evidence pins match. The independently repeated synthetic replay
matches `c1647c67598035d373dc6f9b92d89d34fc2338f3c89075f4a0c1a080931c0041`.
These checks support bounded format/loss refusal and controlled POSIX artifact
recovery; they do not establish live engine behavior, enclosing-config merge,
GUI persistence, subscription refresh, user-device deployment or Windows R.

After integrating only this reviewed original case, the ledger records 16/218
accepted and 202 pending, with original scenarios, requirements, layers and
75/113/30 scheduling unchanged. The full aggregate ran 1,561 tests in 33.338
seconds: 1,553 passed and eight skipped. This is not a count of complete cases.
Both Node suites, compilation, diff checks and repeated release packaging passed;
the unchanged release package remains
`c587b28cea400a7fa063da053b32856d3e4dfd2838c859dc09ec754f8d555909`.

The preceding sixteenth batch was published as
`fe30684801b39d49a7e7789e5437f7a68f574b04`, parent
`5f027d0dd033159bff95e3814c10d2732943ba3e`. Exact 29-file delta and all 198
source blobs were verified. Both push workflows passed:
[tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39107153859)
and [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39107153909).
Linux/Python 3.10: 1,535 passed/eight skipped; macOS: 1,532/11;
Windows: 1,290/253. The release hash was identical across all four jobs.
No skipped or hosted test is promoted to actual user-device acceptance.


## Seventeenth publication verification

Published `9c5e8c9cdf906395d71942d2ff4a3740377c3ac9`, parent
`fe30684801b39d49a7e7789e5437f7a68f574b04`; exact seven-file delta and all 200
source blobs/modes verified. [Push tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39107494531)
completed successfully: Linux/Python 3.10 1,553 passed/eight skipped;
macOS 1,550/11; Windows 1,290/271. The 18 new POSIX controlled-file tests skip
on Windows rather than claiming Windows restoration. The release package is
unchanged across jobs. No preview workflow was triggered by this test/docs scope.

## Eighteenth C5 callable cleanup and device-history integration

This product extension adds selected-device restriction history and an explicit
full application-data cleanup goal, plus real bounded POSIX quarantine,
restart reconciliation and separately approved restore. It removes selected
verified roots from active locations while retaining private quarantine and
journals; required independent backups are established separately by the host. It does not establish native root discovery, process
inactivity, credential/browser deletion, uninstall or permanent purge.

Independent review exercised malformed manifests, protected-path aliases,
interruption before/after renames, large recovery envelopes, cancellation and
isolated installation. The installed package actually moves and restores its own
synthetic history/configuration/extension files. No user-device data was touched.
The flow review covers 4,456 adversarial assertions and 2,000 timestamp/category
cases. It found a generated-hex reference that occasionally resembled sensitive
numeric data; exact dot-separated digest chunks fix that representation without
loosening the general sensitive-data filter. Deterministic regressions retain
both original failures.

The final aggregate ran 1,680 tests in 33.250 seconds: 1,672 passed and eight
skipped. Both Node suites, compilation and diff checks passed. Two independently
built release archives were byte-identical, SHA-256
`c563a758390910f407e7f896a7a379cc1b287c17f2409b9661a34b0c43c6307e`.
Reviewed affected evidence pins were refreshed after original-case replay;
acceptance remains 16/218 with 202 pending. The explanatory ledger note now
matches those existing rows. No original scenario, condition, layer or
acceptance status was changed by this batch. Future CLI/native integration
requires separate evidence; these callable APIs are not a claim of complete
end-to-end user-device cleanup.

## Eighteenth publication and macOS fixture correction

Published `ddd57b24ccdfe52e1ba969c2654f7e40fff7f645`, parent
`9c5e8c9cdf906395d71942d2ff4a3740377c3ac9`. Exact 22-file delta and all 205
source blobs/modes were verified through the complete Git tree identity.
[Push tests](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39110279671)
finished with a macOS failure; [preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39110279718)
passed. Linux/Python 3.10 passed 1,672 with eight skipped; Windows passed 1,316
with 364 skipped. macOS ran 1,680 with one error and 12 skips: the new Unicode
budget fixture exceeded the OS pathname limit during directory creation, before
reaching its intended recovery-envelope budget assertion. This failed run is
retained and is not reported as successful native acceptance.

The narrow fixture correction uses two UTF-8 directory components and 2,000
sibling files. Independent pathname-limit emulation reproduces the old fixture
failure at 1,169 bytes and passes the new fixture at 695 bytes including NUL.
In the initial independent emulated run, the observed plan was 2,444,957 bytes,
below 4 MiB; its reserved recovery receipt was 4,888,515 bytes, above 4 MiB.
Serialized metadata sizes can vary; the asserted budget inequalities are stable. All 2,007 entries remain below the 4,096-entry
limit. The exact budget rejection, zero writes and original/protected bytes are
asserted; no test is skipped or weakened. The core runtime is unchanged.
The 92-test independent focused run passed; the complete cloud aggregate passed
1,672 with eight skipped (1,680 total, 33.147 seconds). Both Node suites,
compilation, diff checks and reproducible packaging passed with the unchanged
release SHA `c563a758390910f407e7f896a7a379cc1b287c17f2409b9661a34b0c43c6307e`.
Path-limit emulation is not macOS execution; the corrected push CI is tracked
separately. Original-case acceptance remains 16/218.

## Nineteenth original-case intake and appeal evidence

Original T01/T02 L+C clauses were reviewed sentence by sentence against active
guidance and complete executable interview traces, including first/returning/
upgrade paths, complete expert input reuse, subsequent gaps and unchanged
independent authorization. Thirteen new focused tests and 151 combined checks
passed; independent replay matched the retained output exactly. A further 100
input-order permutations and generic-approval negative probes passed.

Original T18 L+C is supported by a retained actual two-turn synthetic guided
response and independent sentence-level factual review. The second response adds
only the stated webpage personal-writing event; location/payment/restriction
time remain unconfirmed. Eight integrity tests bind the exact responses,
original condition, guides and review. They do not regenerate model output or
establish performance on unseen inputs, real-account facts or external sending.

The initial integrated aggregate ran 1,701 tests in 34.621 seconds: 1,693 passed
and eight skipped; independent rerun 34.291 seconds matched. After carrying
forward the exact reviewed macOS fixture correction, the aggregate again passed
1,693 with eight skipped in 34.609 seconds; independent rerun 34.300 seconds matched. Both Node suites, compilation,
diff checks and two byte-identical release builds passed. Runtime and package
remain unchanged, SHA-256
`c563a758390910f407e7f896a7a379cc1b287c17f2409b9661a34b0c43c6307e`.
Only T01/T02/T18 become accepted under their unchanged L+C layers: 19/218
accepted, 199 pending. Original scenario/condition/layer bytes and scheduling
remain unchanged. These counts are original-case decisions, not the number of
unit tests or native-platform completion claims.


The preceding test-only macOS fixture correction was published as
`486aaf1c01dcaac394d3c40bf3b2a65581aadc47`. Its
[push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39110979717)
completed successfully: Linux/Python 3.10 1,672 passed/eight skipped; macOS
1,668/12; Windows 1,316/364. All four jobs built the same release hash shown
above. The exact four-file delta and complete 205-source Git tree were verified.
These hosted tests do not establish native user-device cleanup acceptance.

## Twentieth callable C5 CLI and installed host-bound recovery

A bounded standard-library dispatcher now exposes capabilities, strict scope
validation, plan, quarantine, reconciliation and separately authorized restore.
The ordinary entry point has no host and refuses selected-root operations.
An in-process Agent host must independently establish scope ownership, inactive
state, writer exclusion, verified backup and current operation consent; saved
JSON and command flags do not establish those facts. The shipped usage guide
states that native application adapters and permanent purge remain unavailable.

Independent review of the core-composed CLI found and corrected fixture scope/
backup verification, host exception sanitization, truthful post-move recovery
metadata, cancellation and deadline checks around private output persistence.
The 118-check runtime subset and independent schema/recovery probes passed.
Installed-package integration then exercised two genuinely separate interpreters:
the second rechecks parent-created inode/content/backup bindings and obtains
fresh restore consent after the first exits. Negative probes reject changed
backup, replaced inode, additional unbacked data, occupied destination, denied
consent, serialized authority and changed parent digest. This is controlled
fixture restart evidence, not native Claude ownership or production exclusion.

The final aggregate ran 1,729 tests in 35.204 seconds: 1,721 passed and eight
skipped. Both Node suites, compilation and diff checks passed. Two release builds
were byte-identical, SHA-256
`9ce77248c44c36e1d6f79bfc80ac59cec70ae126f43813c377e0d5f3138256b7`.
Only the CLI and its usage guide are newly packaged; the synthetic host/helper
and private test artifacts are excluded. An independent 23-test source and
nine-test installed-library replay preserves original T09 source deduplication,
authorizing its single packager dependency-pin refresh. Original-case acceptance
stays 19/218; no new native or complete-device cleanup acceptance is inferred.

## Nineteenth publication verification

Published `cfdd270cc495299fd8bfb035b2e8c555148a093d`, parent
`486aaf1c01dcaac394d3c40bf3b2a65581aadc47`; exact 17-file delta and complete
217-source Git tree verified. [Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39111478733)
passed: Linux/Python 3.10 1,693 passed/eight skipped; macOS 1,689/12;
Windows 1,337/364. All four release hashes matched. No preview workflow was
triggered by that test/evidence-only scope, and no hosted result is promoted to
actual user-device acceptance.

## Twenty-first reconstruction: T16 resume and T23 local runtime with VPS exit

Original T16 and T23 retain their full original conditions and L+C layers.
T16 combines actual save/load/resume with selective environment invalidation,
cleared permissions, no repeated completed purchase intent, and an actual
synthetic two-root cleanup interrupted after one move. Reload/reconcile does not
repeat the move; original retry and stale restore are rejected, and a fresh
approved restore touches only the moved fixture root. This does not prove
provider-side payment idempotency or native device cleanup.

T23 records local execution separately from a user-reported VPS network exit.
It stays on the local route, asks for unknown local-install facts, and never
creates a remote installation action from an exit alias. Exit changes invalidate
only relevant network answers. The host must normalize actual execution location
and clarify uncertainty; no natural-language inference or actual exit probe is
claimed. Both complete clauses have independent reviews and repeatable traces.

The aggregate ran 1,737 tests in 35.771 seconds: 1,729 passed and eight skipped.
An independent review found a locale-dependent T16 fixture import; the narrow
explicit UTF-8 fix preserves assertions and is covered by a retained cp1252
failure/repair reproduction. Its final aggregate rerun
ran 1,737 tests: 1,729 passed and eight skipped, in 35.351 seconds.
Both Node synthetic suites, compilation, diff checks and two identical release
builds passed. Release SHA-256 remains
`9ce77248c44c36e1d6f79bfc80ac59cec70ae126f43813c377e0d5f3138256b7`.
Original acceptance is 21/218, with 197 pending. User-device acceptance remains
unperformed; conditional scheduling does not add an unrequested native layer.

## Twentieth publication verification

Published `76e799f94ce08db1470fdc8b9749b7f1acd6d6f5`, parent
`cfdd270cc495299fd8bfb035b2e8c555148a093d`; exact 13-file delta and complete
224-source Git tree verified. [Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39111983373)
passed: Linux/Python 3.10 1,721 passed/eight skipped; macOS 1,717/12;
Windows 1,338/391. All four release hashes matched; the
[synthetic browser preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39111983458)
also passed. Hosted fixtures do not establish native Claude ownership, exclusive
writer exclusion or actual user-device cleanup authorization.

## Twenty-second reconstruction: T03/T05 actual guided response evidence

T03 and T05 retain original L+C clauses. Exact synthetic inputs, actual two-turn
responses, execution timestamps and independent sentence-level reviews are
retained. T03 asks response origin, authentication outcome and resource permission
before diagnosing a 403; unknown cause stays unknown. T05 records the supplied
intermittent observation dates and missing scope without inventing a ban rate or
future safety guarantee. This is observed guided behavior, not an actual VPS test
or a guarantee about future model outputs.

Six retained-record integrity tests verify artifacts, guidance and review bytes;
they do not generate responses. The aggregate ran 1,743 tests in 35.765 seconds:
1,735 passed and eight skipped. Only T03/T05 change acceptance, now 23/218 with
195 pending. Original IDs, conditions, layers and scheduling remain unchanged.
No runtime, shipped guidance, private user records or native results are added.

Independent twenty-second integration rerun: 1,743 total, 1,735 passed and eight
skipped in 35.322 seconds. Both Node suites and compilation passed. Two release
archives are identical at
`9ce77248c44c36e1d6f79bfc80ac59cec70ae126f43813c377e0d5f3138256b7`;
no tests or retained response records are shipped in the Skill package.

## Twenty-first publication and minimum-Python test hotfix

Published `51193c3d610c35686596dc896d48615103420263` with exact source tree
`7e0910aa72a39e08bbf295518dc1354daa108030`. Its
[push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39112833044)
failed on Python 3.10: two new setup methods affecting seven tests used TestCase.enterContext,
which is unavailable there. Ubuntu passed 1,729/eight skips, macOS 1,725/12,
Windows 1,345/392. This run is not an all-green result.

The narrow test-only repair uses ExitStack plus addCleanup(close), registering
cleanup before patch installation. Assertion bodies, runtime and package are
unchanged. Updated test hashes invalidate and renew only their evidence pins.
The cloud rerun ran 1,737 tests in 35.002 seconds: 1,729 passed, eight skipped.
Actual minimum-Python compatibility remains subject to the new push CI; an
API-absence emulation is retained as a separate local regression reproduction.

Independent hotfix rerun: 1,737 tests in 35.970 seconds, 1,729 passed and eight
skipped. API-absence reproduction retains the original seven failures and the
fixed eight-test success. Explicit cleanup-lifetime checks cover patch removal
and partial setup failure; these are local compatibility probes, not a substitute
for the actual Python 3.10 push result.

After the exact minimum-Python test hotfix transplant, the local aggregate ran
1,743 tests in 35.421 seconds and the independent aggregate in 35.178 seconds:
1,735 passed and eight skipped in each run. The fixed setup API and relevant
evidence pins match the separately reviewed hotfix; actual CI is recorded below.

## Minimum-Python hotfix publication verification

Published `d44f4c95710dde953e932fb89b9878727a27c2aa`, parent
`51193c3d610c35686596dc896d48615103420263`; exact seven-file delta and complete
228-source tree `3666c6ff59de19714bcaa1b388a082caa422bd78` verified.
[Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39113242566)
passed on all four jobs: Python 3.10 and Ubuntu 1,729 passed/eight skipped;
macOS 1,725/12; Windows 1,345/392. All release hashes matched. This closes the
specific enterContext test compatibility defect; the earlier failed run remains
recorded, and hosted results do not replace actual user-device acceptance.

## Twenty-third reconstruction: history, pause and retired fields

Original T31/T47/T82 retain full L+C clauses. Deterministic replays and active
content review distinguish current reported usability from prior restrictions;
pause stops questions and blocks planning/execution gates without erasing contact
history; supported compact/report migration discards retired ownership fields
without replacing the question or making omission block readiness. Old arbitrary
wire formats remain unsupported. Fresh target binding, stale-fact review and
actual operation approval remain necessary.

Fifteen new tests and repeated traces accompany 26 exact dependency pins.
Proposed model dialogue exercises are explicitly unrun; these records establish
state transitions and reviewed guidance, not generated model response behavior.
The narrow migration-doc correction lists the already-supported optional fixed
traffic_policy member; runtime is unchanged. The aggregate ran 1,758 tests in
37.897 seconds: 1,750 passed, eight skipped. Acceptance is 26/218 with 192 pending;
original IDs, conditions, layers and scheduling are preserved.

## Twenty-second publication and explicit-encoding regression

Published `3430901cf84f0034b4151170235cbb8030b21c67`, exact 240-source tree
`6dd659e5351c2f635bb16893dad201a0187a2e24`. Its
[push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39113513208)
failed on Windows: four retained-evidence tests read Chinese text with default
cp1252. Python 3.10/Ubuntu passed 1,735/eight skipped and macOS 1,731/12.
The failed run remains recorded, without relabeling it as success.

The repair adds explicit UTF-8 at seven read_text call sites. Responses, review
artifacts, source pins, assertions and runtime remain unchanged. Two small
regressions parse acceptance helpers using Python 3.10 grammar, reject known
unsupported enterContext and implicit text encoding, and run the fourteen
relevant tests in a separate process with cp1252 default text decoding.
The emulation handles both None and the literal locale encoding sentinel. An
earlier wrapper that handled None alone did not reproduce the fault and was
corrected before release. Independent old-source replay now reproduces all four
errors; fixed replay passes. These bounded checks do not establish arbitrary
API compatibility or substitute for actual Windows/minimum-Python push CI.

The final local suite ran 1,745 tests in 36.394 seconds: 1,737 passed and eight
skipped. No case count changes: 23 accepted,195 pending. Guards apply to the
acceptance-helper family; other newly changed helpers require explicit read-only
encoding/API review before freezing rather than inheriting a blanket certification.

The final independent rerun ran 1,745 tests in 35.889 seconds: 1,737 passed and
eight skipped. Thirteen isolated AST mutation cases check both rejected implicit
text/API usage and accepted binary/explicit-encoding forms. Both Node suites,
compilation and reproducible package remain successful at the unchanged release
hash `9ce77248c44c36e1d6f79bfc80ac59cec70ae126f43813c377e0d5f3138256b7`.

After the frozen explicit-encoding hotfix transplant, the twenty-third aggregate
ran 1,760 tests in 38.700 seconds locally and 38.787 seconds independently:
1,752 passed, eight skipped in each. New portability guards and all 163 table
pins passed; package bytes are unchanged. These runs do not replace the new
actual Windows/minimum-Python CI result recorded below.

## Encoding-guard publication and Python 3.10 accessor correction

Published `090b2344b546007c2d6f2b91b935d056b1303ab8`. The
[push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39114025321)
confirms Windows evidence decoding now passes, but the new subprocess emulator
fails on Python 3.10: replacing io.open before pathlib's lazy import allows its
legacy accessor class to bind a Python function as a method. The extra accessor
argument shifts the expected file/mode arguments. This is a guard implementation
failure, not a passing minimum-version result.

The minimal repair imports pathlib before patching and wraps Path.open directly,
leaving io.open intact. It preserves the documented Path.open method signature
and builtin open behavior, forcing cp1252 only for implicit/default-locale text
reads. Binary and explicit-encoding reads retain their original behavior. Exact
retained responses, assertions and shipped runtime/package remain unchanged.
Only Python 3.12/3.13 are already installed locally; no additional interpreter
was installed. Local API-contract and legacy-accessor-model checks remain
separate from the upcoming actual Python 3.10 push result.

The local corrected-emulator aggregate ran 1,745 tests in 35.854 seconds:
1,737 passed and eight skipped. The new guard does not modify the test bodies
or any shipped runtime code.

Independent verification ran the same 1,745 tests in 36.786 seconds: 1,737
passed and eight skipped. The original unencoded source still produces four
UnicodeDecodeErrors under the corrected emulator; all 14 relevant tests pass
with the explicit-UTF-8 source. Fifteen API checks cover the pinned Python
3.10.22 Path.open signature, legacy accessor binding, explicit encoding,
binary operations and patch restoration. Both Node suites, compilation,
ledger integrity and repeated release builds pass; the package SHA-256 remains
9ce77248c44c36e1d6f79bfc80ac59cec70ae126f43813c377e0d5f3138256b7.

With the corrected Path.open guard transplanted, the independent twenty-third
aggregate ran 1,760 tests in 38.080 seconds: 1,752 passed and eight skipped.
Both Node suites, compilation, portability checks, all 163 table dependency pins
and repeated unchanged release builds passed. The original case count remains
26 accepted and 192 pending.

The corrected emulator was published as
`8e0010a5d68db0800535e82f90a5aabfe6899674`, exact tree
`8970831f62d40c4622d1f6a9f192ffb4197e0c5d`.
[Actual push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39114631211)
completed successfully: Python 3.10 and Ubuntu each passed 1,737 with eight
skipped; macOS passed 1,733 with 12 skipped; Windows passed 1,353 with 392 skipped.
All jobs ran the same 1,745-test inventory. The skipped native-dependent cases
remain unverified on user devices. The unchanged package hash was reproduced.
This closes the preceding test-helper compatibility failures without rewriting
their recorded outcomes. Twenty-third publication remains a separate commit.

## Twenty-fourth reconstruction: callable cleanup host handoff

The generic cleanup finding previously claimed that no executor existed, despite
the shipped C5 core and CLI. Its informational host_handoff now names the existing
plan/quarantine/reconcile/restore path and packaged cleanup guide. This does not
execute a cleanup or grant authority: the separate Q-D02 choice selects scope_inventory planning; actual inventory
still requires its scoped permission. The real host must verify ownership,
inactivity, exclusions, backup choice
and fresh per-action approval before invoking the existing executor.

The installed reference resolves to references/cleanup-cli-usage.md. Seven new
regressions cover the fixed handoff and actual package-link existence. The other
268/269 catalog projections remain byte-for-byte equivalent. Credential stores,
browser data, projects and shared state remain outside the automatic adapter;
no native Mac/Windows integration, irreversible purge or host deletion ran here.

The integrated local suite ran 1,767 tests in 38.334 seconds: 1,759 passed and
eight skipped. After the corrected portability guard transplant, independent
verification ran the same 1,767 tests in 37.955 seconds with identical outcomes.
Both Node suites, compilation, ledger checks and repeated package builds pass.
The changed package SHA-256 is
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a.

Four existing evidence scopes were re-reviewed against the bridge change;
only the enforcement page's current dependency pin needed refreshing. The
prepared-recovery record intentionally retains its historical guide hash, while
rule-import and idempotent-replanning reviews use their existing narrative
dependencies. This is not a claim that four current hash pins changed. No
original case is promoted: 26/218 accepted and 192 pending remain unchanged.

The preceding twenty-third batch published as
`04b7b476b7a76d66891b601872d34054743b5780`, tree
`4733f05517e65b94460f58b6a02cfe071a06bbd2`.
[Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39114982417)
succeeded across all four jobs: Python 3.10/Ubuntu each 1,752 passed/eight skipped,
macOS 1,748/12, and Windows 1,368/392, from 1,760 total tests per job.
The unchanged prior package was reproduced. These results concern the preceding
case batch; the C5 handoff change above has its separate publication and CI.

## Twenty-fifth reconstruction: mobile billing versus execution route

Original T49/T83 were independently reviewed under their complete L+C clauses.
Six regression tests and complete four-path normalized-host replays retain the
chosen execution route while
checking Apple/Google device, store, intended account, target plan and actual App
entry at the applicable stage. Historical billing questions appear only for an
explicit relevant conflict. No web-card path is forced by selecting VPS.
Supplied synthetic setup is not extracted from an arbitrary short utterance;
proposed model dialogue exercises remain unrun. T36/T38 remain pending actual
host-response evidence, and coverage G2 is not an account-eligibility evaluator.

The first parent aggregate command used the workspace root and failed test
discovery; no tests ran in that invocation. The corrected repository-root command
ran 1,773 tests in 42.884 seconds: 1,765 passed and eight skipped. Independent
verification ran the same inventory in 42.536 seconds with identical outcomes.
Detached release tests passed 9/9, both Node suites and compilation passed,
forced cp1252 passed all six new tests, and full UTF-8 replays match. Repeated
packages remain byte-identical at
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a.
Only T49/T83 are promoted: 28/218 accepted and 190 pending. Original conditions,
layers and scheduling are unchanged; runtime and installed guidance are unchanged.

The preceding C5 handoff batch published as
`95368b3332db4b22060e3bed49df0c22589c9c4a`, tree
`57fa626200f67052acf7acc4c05c459d91f10f8d`.
[Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39115315171)
and [synthetic preview](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39115315151)
both succeeded. All four test jobs ran 1,767 tests: Python 3.10/Ubuntu each
1,759 passed/eight skipped, macOS 1,755/12, Windows 1,375/392. The new package hash
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a was reproduced.
These results establish the preceding bridge CI, not user-device cleanup or the
forthcoming twenty-fifth publication result.

## Twenty-sixth reconstruction: entry order and bounded OS question

Original T29/T57 complete L+C clauses are exercised with seven new deterministic
regressions and substantive review of the current intake guidance. Fresh intake
asks subscription stage before the bounded Mac/Windows question; supplied facts
are reused and unknown/refused/mobile-only exits remain limited. No new purchase
or installation tutorial is inferred from missing information, and prior paid
entitlements are not presumed. Model dialogue exercises remain explicitly unrun.

The local aggregate ran 1,780 tests in 43.172 seconds: 1,772 passed and eight
skipped. Only T29/T57 are promoted, yielding 30/218 accepted and 188 pending.
Original clauses/layers/scheduling and runtime bytes remain unchanged. Final
independent checks and preceding publication results are recorded below.

Independent integrated verification ran the same 1,780 tests in 43.611 seconds:
1,772 passed and eight skipped. Detached release tests passed 9/9, portability
checks 2/2, forced cp1252 candidate checks 7/7; both Node suites, compilation,
diff checks and exact UTF-8 replay passed. Two packages remain byte-identical at
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a.

The preceding mobile-route batch published as
`d9d83a135d747795d9d7d5e56c1e4b686a6c8bec`, tree
`54fa35c540b0d4b5b1b0ffdd7cb93f8467be653d`.
[Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39115784630)
succeeded on all four jobs: Python 3.10/Ubuntu each 1,765 passed/eight skipped,
macOS 1,761/12, Windows 1,381/392, from 1,773 tests per job. The unchanged package
hash was reproduced. These prior-commit results do not substitute for the
forthcoming twenty-sixth CI or user-device acceptance.

## Twenty-seventh reconstruction: experience and subscription status

Original T75/T79 complete L+C clauses are covered by six deterministic regressions
plus substantive novice/expert content review. Technical expertise/free-only use
keeps first_subscription and concise explanation preferences. Existing paid status
with novice preference asks the actual task when missing, then follows that task
without starting first-purchase preparation. Before the missing task is supplied,
the generic subscription_preparation metadata remains unresolved while Q-C11 is
asked and no payment branch is activated; this limitation is retained truthfully.
Explanation preference/state traces do not establish actual generated prose.

The local aggregate ran 1,786 tests in 45.221 seconds: 1,778 passed and eight
skipped. Only T75/T79 are promoted to32/218 accepted and186 pending; original
conditions/layers/scheduling and runtime bytes remain unchanged.

The preceding entry-order batch published as
`ff859040ff488f4827021cfbd01225e6ff34666b`, tree
`f6e397f1f163666c8c561d74d69d4e1667f2e908`.
[Push CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/39116150916)
succeeded across all four jobs, each running 1,780 tests: Python 3.10/Ubuntu
1,772 passed/eight skipped, macOS 1,768/12, Windows 1,388/392. The unchanged
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a package
was reproduced. These prior-commit results do not establish the forthcoming
experience/status batch CI or native user-device acceptance.

Independent integrated checks ran 1,786 tests in 47.771 seconds: 1,778 passed
and eight skipped. Detached release passed9/9, portability2/2, ledger3/3 and
forced cp1252 candidate checks6/6. Both Node suites, compilation, diff checks,
exact UTF-8 replay and duplicate package builds passed. Package remains
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a.

## 2026-10-18 twenty-eighth: observed T11/T12 safe-input evidence

The complete local suite ran 1,793 tests in 47.126 seconds: 1,785 passed and
8 skipped. Seven focused safe-input checks and three ledger integrity checks
passed. The four actual generated responses and original provenance/execution
records are retained unchanged. Independent candidate review found the initial
wrapper failed on non-ASCII output paths under legacy encoding; both JSON
serialization points now escape non-ASCII characters. The new regression fails
against the former wrapper and passes under ordinary and forced cp1252/C-locale
execution. These supporting tests do not regenerate model responses.

The prior twenty-seventh commit 99c1820872f0fa56e3e8a940456108da6377624c passed
CI run 39116710419 on all four platforms: Ubuntu 1,778 passed / 8 skipped,
Python 3.10 Linux 1,778 / 8, macOS 1,774 / 12, and Windows 1,394 / 392.
The hosted matrix is not user-device acceptance. The prior package remains
3345ff8dab7b0edbfbb7c89154a7fced535ed295d69b36c5ad4205788ef5a21a.
Independent integrated checks ran 1,793 tests in 47.194 seconds: 1,785 passed
and eight skipped. Detached release9/9, portability2/2, ledger3/3, forced cp1252
7/7, both Node synthetic suites, compilation and duplicate package builds passed.
Current-batch CI is pending.

## 2026-10-18 twenty-ninth: expired bills and conditional current-plan facts

The final local suite exited 0: 1,842 tests in 51.913 seconds, with 1,834 passed
and eight skipped. Its log SHA-256 is
51809da8cf567ac5f36520c37af0d660b261106c69e21b2965cebfae43dd7e2f.
The independent terminal run exited 0: 1,842 tests in 52.389 seconds, also
1,834 passed and eight skipped; log SHA-256 is
b09807e65184085497b38e974fc908a531358b9eddae42d51f69312b56da1a85.
A premature independent progress count/duration was withdrawn before acceptance;
only the terminal logs above support these results. An earlier local aggregate
overlapped the final evidence-table pin conversion from 12 to 13 and failed that
single integrity assertion. The consistent final tree was rerun in full; no
behavioral assertion was relaxed and no new skip introduced.

Before pin updates, the integrated 1,828-test run had exactly 41 stale source-pin
failures and no functional failures. Three independent clause/replay reviews then
preserved all 27 affected accepted cases. Thirteen pages received dated appendices
and exactly 41 reviewed pin replacements. T16's full replay adds five optional
completion receipts; all pre-existing members are unchanged. Historical generated
response packets remain byte-identical. The two new original T76/T84 cases have
14 independent tests, 385 repeatable full snapshots, and 13 offline CLI commands
with 12 saved-state inspections. These are normalized-host L+C evidence, not
actual entitlement, commercial compatibility, generated dialogue or native action.

The 35 repair tests pass forced cp1252/C-locale execution. Independent detached
release 9/9, portability 2/2, both Node synthetic suites, compilation and diff checks
pass. Duplicate package builds match
2aeec7ac5d051dadefaf88ad0ae6f85a0192e9239e424ca94135268795cb4640.
Actual Python 3.10 is unavailable locally; grammar/API checks do not replace its
hosted runtime job. The historical SKILL question count is a separately tracked
documentation correction; the current derived registry has 98 entries.

Prior commit 12603a4ecade3d5ee54d24436ba6821d5415acb5 passed CI 39117151076 on all
four hosted platforms. Current-batch CI is pending. Hosted macOS/Windows jobs
are not native acceptance on the user's devices. All original 218 conditions and
layers are preserved; current candidate acceptance is 36, with 182 pending.


## 2026-10-18 thirtieth: exact registry-count wording correction

The local complete suite exited 0: 1,847 tests in 51.910 seconds, 1,839 passed
and eight skipped. Log SHA-256:
00cf9083d63fa0c5431c03ef7f2f34997195010a10d61888c1a71e52feae4da9.
The only installed-package change is deletion of the six UTF-8 bytes for the
hardcoded question count. Runtime scripts and 69 historical evidence files are
byte-identical. The exact 14 current-page / 29 existing-ledger-hash map was
independently approved after all 14 complete before/after replay streams matched.
The original 218 clauses/layers and 36 accepted cases remain unchanged.

Before the map was applied, the unchanged ledger integrity suite failed exactly
14 stale dependency pins. The exact approved fixture then passed all three checks.
Independent compatibility probes reject unrelated guide changes, malformed or
changed supplements, symlinks and other source drift. Historical response-source
hashes remain historical; fresh replay provenance reports actual current bytes.

Detached package tests passed 9/9 and portability 2/2. Both Node synthetic suites,
compilation, diff checks and repeat package builds passed. A mistaken invocation
of the production browser helper returned INTERACTION_REQUIRES_CI before opening
a browser; the correct synthetic protocol suite then passed. No CI-mode override
or real browser result is claimed. Package SHA-256:
077f7bca611e3990ed4927c69402e109cdcbbea9051bb178977737d7450b7fa1.

Prior commit cec0505808d9110e65e4a2ccdae2cee6a3301120 passed CI 39120359380:
Ubuntu 1,834 passed / 8 skipped, Python 3.10 Linux 1,834 / 8, macOS 1,830 / 12,
and Windows 1,450 / 392. All four packages matched the recorded prior digest.
Independent final integrated verification exited 0: 1,847 tests in 55.975 seconds,
1,839 passed and eight skipped. Its log SHA-256 is
e39c1ba52e9bc0615b8f465f2ace6e2c6109a60c5cf23dfe108366d5cc3b95f0.
The independent forced-cp1252 regression set passed all 197 tests; detached9/9,
portability2/2, both synthetic Node suites, compilation and duplicate package
builds passed. Current-batch hosted CI is pending.
Hosted OS jobs do not replace user-device acceptance.

## 2026-10-18 thirty-first: observed Agent rule-scope selection

The final local suite exited 0: 1,863 tests in 52.639 seconds, 1,855 passed
and eight skipped. Log SHA-256:
c34a59ee4ca24a1c55abbce8fa50ab7040a730e8f55fb5167e1d46cdac680912.
The initial unrefreshed 1,847-test run had only three stale reference-pin failures.
Independent baseline/candidate preservation checks passed 222/222, with complete
ENV-T79/90 and ENV-T81 replay bytes unchanged. Four reference pins on three pages
and three existing ledger hashes were then refreshed under exact review.

The first integrated aggregate had one explicit acceptance-registration mismatch:
the ledger already contained the five approved rows while the test's exact
ACCEPTED map still held the previous list. That failed log is retained. Only the
five exact case/layer entries and new page's 21-pin count were registered; every
assertion remains intact, and the final full run above passed.

Eleven actual model-authored turns, 22 original helper calls and six complete
candidates/diffs are retained unchanged. Independent review added ten clearly
separate reviewer controls, not fabricated original calls. All 22 calls replay
exactly with API-level no-I/O sentinels unused; these observations do not establish
historical host-wide isolation. Sixteen retained-evidence tests pass normally and
under forced cp1252/C-locale; a combined preservation/evidence set passed 241/241.
Only ENV-T38/39/41/42/58 receive new complete original L+C acceptance, making 41/218.
Original source dates, clauses/layers, current IPv4 policy and native deferrals
are preserved. No new runtime feature-selection engine or actual device repair
is introduced. Selection happens explicitly before the atomic source importer.

Both Node synthetic suites, compilation, diff checks and duplicate package builds
passed. Package SHA-256:
d5d848e61e6ce37b70a9e3e2ac0219454b6d301fe52897ea273dbe5c0c122981.
Prior commit a25e71975fecf579d34e577a335ca21e236faa30 passed CI 39121431849:
Ubuntu/Python 3.10 each 1,839 passed / 8 skipped, macOS 1,835 / 12, Windows 1,455 / 392.
Independent integrated aggregate exited 0: 1,863 tests in 56.686 seconds,
1,855 passed and eight skipped; independent log SHA-256 is
c3d97bf3e9f8f903a38ac66ca2362f8ba9d1a84a2ea4ae08a9b8bf4278c5e988.
Ledger 3/3, forced cp1252/C 16/16,
Node synthetic suites, compilation and repeat packages passed. All 63 installed
members match the tested source, with only the two active references changed
from the previous package. Current-batch hosted CI is pending. Hosted OS
jobs do not replace user-device acceptance or prove unseen Agent conversations.

## 重建第三十二批：否定前提与覆盖度解释、四项原对话验收

2026-10-18，基于第三十一批 `ce94ca82c4b31b73203c68601ba23e1aecc49aaa`。仅安装包内的 `references/intake.md` 增加一段解释：已回答的否定事实可以与 G1 complete/G2 pass 并存；保留原值，分别解释具体路线前提、G3、接触状态及动作权限。运行时不变。

原 T36/T46/T54 使用逐句独立审阅的原始多轮输出并经过当前指导语义保全；T38 原始第三轮把上述共存误称为矛盾，失败记录原样保留。新一轮使用相同冻结输入、更新的正常指导，逐轮交付并固定前序回复后生成，再由独立审阅者核验完整原条件与报告解释。当前四项按原 L+C 验收；累计45/218，173项待验收。实际回复不是测试生成的模板，独立辅助器重放与回复生成记录分开；记录不冒充独立操作遥测或未观察输出保证。

另对受 intake 影响的12份既有证据、26个已验收原条件独立保全：每树105项原测试与207项访谈回归通过，12组完整重放各两次且字节一致；仅审阅通过的当前依赖与对应页哈希更新，历史包/回复哈希不变。所有218原条款、层级和75/113/30调度分类保持不变。

父执行器最终完整套件1883项，1875通过、8跳过，51.485秒，退出0；原始日志 SHA-256 `d832eb1f9e19b04b544fecff1676b8e2ec6de40d703cb9c867742a82b73e66ef`。新增安装布局20项与台账3项均通过。两项仓库 Node 合成测试、编译、tracked diff检查与重复打包通过。一次调用了不存在的 Node 测试文件名而失败，记录已保留；随后按仓库实际两个测试路径执行成功，没有改变测试。

重复包 SHA-256 `7a1ab5561a58880136a0715698e0bbf50cc436c9af61515db80718461462e74c`，63项清单不变，仅 intake 内容改变；证据与测试不进入安装包。新证据测试已在 UTF-8、C-locale/cp1252、Python3.13运行；本地无3.10，最低版本执行以该提交后CI为准。Mac/Windows用户设备、真实账户/购买资格、网络隔离、凭据及实际操作均未验收。

独立最终执行同为1883项，1875通过、8跳过，51.929秒，退出0；日志 SHA-256 `906c2d0845aed0819e587d196085d5a39031a66e42c27ef250497af225c16046`。强制缺省文件编码 cp1252/C-locale 并禁止较新 unittest 上下文API的337项兼容性检查全部通过；Python3.13安装布局20项通过。静态审计首次把明确受 no-I/O 阻断的故障注入 open 哨兵误作普通文本读取，另一次把未纳入172项正文manifest的自身哈希旁文件误作漏文件；原失败审计保留，只修正审阅工具的精确分类与manifest定义，没有改候选测试或历史证据。

## 重建第三十三批：限定升级访谈、订阅冲突与终止答复保留

2026-10-18，基于第三十二批 `ef8602d5bfcde6aa9ee06aae8d84e31dab340af5`。安装包中的 interview_flow.py、interview_cli.py、intake.md 补齐升级任务相关字段、实际冲突 episode、明确更正、较早证据与重复回执限制。单缺口拒答保留互补项原来源/时间；实际中断后保留的套餐仍须复核。最终实现没有新增实际购买、接触、保存、设备或网络权限。

原 T77/T80 按完整 L+C 核验：[案例页](evidence/rebuild-upgrade-conflict-cases.md)与[精简保留证据](evidence/subscription-upgrade-conflict/)固定原条件、输入、真实回复、逐轮调用链和独立语义结论。revision3 的12条轨迹42轮中，两条拒答实际暴露字段丢失；失败记录保持不变。revision4 对这两条重新独立生成6轮并通过逐句审阅；其余10条保持原生成身份，通过精确当前来源兼容性复核。全部163项相应记录调用与当前运行时比较，不冒充重新生成。保留7次恢复的 API 参数错误及1次临时上下文读取错误。访谈覆盖度不代替实际账户状态；完整字段下仍以未解决冲突阻断 G2/G3。累计47/218，171项待验收，原条款/层级/调度分类不变。

既有45项采用受影响证据差异复核：105项测试、12组完整回放与15次历史辅助调用通过；所有原始173文件订阅证据与历史模型输出保持原字节。当前严格兼容桥只允许精确 tuple，未审阅源、证据或审批内容漂移应失败。原中间失败、typed schema 修复与真实拒答前后证据均有持久归档；不继承丢失旧版本的通过结论。

首次最终集成全量1984项运行60.157秒，出现1项失败、1项错误、8跳过，日志 SHA-256 `ca47670bb63e5776b6fd9e2a8b09f3a78f47e75d5fd30922d3e79921e911c076`。原因分别为台账完整性测试的固定集合尚未加入已独立验收的T77/T80，以及负向证据夹具复制了源文件0444属性，不能写入预期篡改。补充两项原ID映射；仅改新建临时夹具的复制方式并新增只读源回归，原证据/权限和语义校验函数不变。没有跳过或删除失败测试。

最终主执行完整套件1985项，1977通过、8原生平台跳过，58.985秒，退出0。日志 SHA-256 `eb3cfd1c16f6725062efa76d7e86d65bb6ef44399e7e661cf5fe76c61e985d0c`。最终新证据安装布局8项在强制cp1252/C-locale、禁用UTF8与locale coercion下通过；修正后的既有兼容桥28项及台账3项通过。Node两项合成套件、编译与重复打包通过。独立完整套件同为1985项、1977通过、8跳过，59.645秒，退出0；日志 SHA-256 `cfb16de6045d10dd5cb94d6b78af5827aa9246a6033b44b8910f074855da313a`。独立受影响检查240项通过，强制C-locale/cp1252的8项新证据、28项兼容桥和3项台账均通过。162个仓库Python文件与4个归档Python文件通过UTF-8及3.10语法审查，API审阅未发现最低版本不兼容。独立包重复字节一致，63项源/ZIP/解压字节及10项声明来源哈希相符；额外调用不支持的 cleanup_cli --help 发生预期 INVALID_ARGUMENTS 退出2，原记录保留，随后只按已声明能力完成smoke检查。

重复安装包 SHA-256 `d05fbc0aa35e2a8e12fd753c94ad9a5b410c803c8e1b60ee7bbf29f5184f26ca`，仍63成员，审核归档/对话/测试均不进入安装包。一次过宽的审计用“evidence”子串误判正常的 evidence-policy.md 指导文件；审计修正为明确的 docs/evidence、tests 和 evidence.zip 边界后通过，包字节未改变。最低Python3.10语法/API审查不代替原生3.10执行；实际最低版本与托管跨平台结果以本提交CI为准。用户Mac/Windows、真实账户/支付、网络隔离与完整模型工具访问均未作实际验收。

### 2026-10-19 公开证据最小化修订

发布前独立隐私审阅发现原精简归档仍包含不必要的执行器路径、内部身份及协调元数据，因此原归档未作为本批提交发布。私有原始记录保持不变；公开候选改用明确标记的合成证据投影，不能重建或独立认证被省略的原始执行记录。原记录哈希仅供持有原件者对照，不当作执行证明。没有修改运行时代码、原218条款、验收层级或63成员安装包。

公开对话投影保留48组实际输入/回复、186次语义调用及7次失败、208项答复单元审阅和163次当前源码重放选择。独立进行1713项语义对照，零差异；保留首轮失败、修复后6轮与其他10条历史轨迹的区别。首次投影审计又发现原条件元数据残留绝对来源路径；仅规范为仓库相对路径，原条件正文与来源哈希未变，并扩大隐私回归以扫描全部公开文件。独立注入旧泄漏字段会被拒绝，最终12文件公开包审阅通过。兼容性证据同时清除机器标识，173个历史文件、11项源码固定值与完整15次语义调用结果不变；新增实际双次重放和语义篡改控制。

最终主执行完整套件1989项，1981通过、8跳过，59.995秒，退出0；日志SHA-256为 `57120593597d59b73ca672978dccdfee38726e6466c1490447916ac8e918c7f2`。独立最终套件同为1989项，1981通过、8跳过，59.680秒，退出0；日志SHA-256为 `0a10625541bec333fc0ee0475aa02bcc745975c746b09337dde3aefa675cf054`。独立强制C-locale、UTF8 mode关闭、cp1252:strict的40项公开证据/兼容性检查全部通过，1.813秒，退出0。前一中间投影全量也通过，但未通过隐私终审，不作为最终发布证据。

Node两项合成检查和编译通过；两次打包字节一致，SHA-256仍为 `d05fbc0aa35e2a8e12fd753c94ad9a5b410c803c8e1b60ee7bbf29f5184f26ca`，63成员不含项目审核材料。两个公开包的独立隐私与来源语义复核通过；这不等于发布授权。本地Python3.10静态兼容检查不代替原生执行，托管CI以实际提交为准，用户Mac/Windows及真实账户/网络操作仍未验收。


## 重建第三十四批：本机专家 Code 与原方案专项诊断

2026-10-19，仅新增 T22/T25 合成证据、测试和验收登记，运行时与安装内容不变。[案例页](evidence/rebuild-local-incident-cases.md)与[最小公开证据包](evidence/local-incident-v1/evidence-manifest.json)保留三段对话七条实际回复及完整独立审阅；投影 SHA-256 `be04d06826c162ecb7e2fc68c71342bb849374bc20eb8555f60685a206f2157e`，审阅 SHA-256 `b104c249aaa56b6c9d5ff7a3931b77701aef968c59cb4a3c367ed878e6e6e90b`。所有场景事实均为虚构的用户报告，不是设备或账户实测。辅助器未参与实际对话；九项规范化逻辑回归与回复审阅分别提供证据，不把数量当作完整行为证明。

独立审阅按原完整 L+C 条件通过 T22/T25，本次台账仅这两行从待验收变为验收；累计49/218，169项待验收。所有原场景、条款、层级及75/113/30调度分类不变，218行身份 SHA-256 仍为 `84975325686c368a191b8232a0564518f1ba32ad7055ce4742d32cc4c26c77b9`。保留来源读取为答复者报告、非完整独立工具记录，以及329-token清理材料遗漏且未重读的限制；全文件哈希不证明逐节读取，指令范围限制不等于物理隔离。未新增未观察输入保证、T04或相邻案例、真机、当前官方流程、网络、修复或恢复验收。

定向 Linux 检查全部退出0、无跳过：`test_acceptance_local_incident*.py` 共22项（九项逻辑与13项证据完整性/隐私），3.924秒，日志 SHA-256 `3c0cf4a68b47a3636e414670b3f945d9c1380e0c8a86a46a7a784d54c0ffa83e`；台账3项，0.027秒，日志 `21329db5531fe9d3fb4bf2af6ad12e0782d89851d0a366da455012a34ade1e31`；可移植性2项，0.659秒，日志 `a103359e3f007e8556b86a8e81d03c94b18b43f4da61d80d7fbc85d562c6e44e`。强制C-locale、UTF8 mode与locale coercion关闭、缺省文件编码cp1252、标准输出cp1252:strict下，22项新证据/逻辑加3项台账共25项通过，3.959秒，日志 `87c3053f8422fccc2eddb2558f8c24e7168bbae9d361655c412ebf74c8ee3a62`。负向控制拒绝改写并重算内嵌哈希的回复、输入/顺序/来源/边界漂移、额外元数据及私有路径/标识注入；这些是固定证据的防漂移检查，不重新生成或重放模型回复。

单次打包验证63成员，SHA-256仍为 `d05fbc0aa35e2a8e12fd753c94ad9a5b410c803c8e1b60ee7bbf29f5184f26ca`；测试与公开审阅包未进入安装包。tracked diff与新增文件空白检查通过。本节只记录上述定向检查，最终全量、重复打包及托管CI以实际后续记录为准；本地3.10语法/API检查不冒充原生3.10或用户Mac/Windows验证。风险限定为证据登记/文档误标，源变动须重新语义审阅；回滚本批证据、测试、文档及两行登记即可，不涉及设备状态、凭据或用户数据恢复。


## Thirty-fourth rebuild aggregate, 2026-10-19

The original T22/T25 evidence-only candidate ran `python -m unittest discover -s tests -v`: **2,011 total, 2,003 passed, 8 skipped**, 63.800 seconds, exit 0. Aggregate log SHA-256: `a1fa41524fd8d14846f50679254573ece782e97ccb65c885d28fd5dc002aa38d`. The independent semantic review and scoped normalized tests remain separate evidence; test counts alone do not establish original-case acceptance.

Strict C locale with UTF-8 mode disabled and cp1252 output reran the 22 new logic/evidence tests: 22 passed, 0 skipped, 3.850 seconds, exit 0; log SHA-256 `b88ca0788e89015c9cf9094b87ac1e80d30830178a6df0c923cbd2d5e26d697e`. New Python files parse under Python 3.10 grammar and all new text reads/writes specify encoding. These checks are not a native Python 3.10 run.

Both existing Node synthetic suites and script compilation passed. An initial dashboard check used a nonexistent filename and returned MODULE_NOT_FOUND; no code was changed for that command error. The corrected existing `tests/dashboard-interaction-protocol.cjs` suite passed; the failed invocation and successful correction are retained in the verification receipt. WebRTC lifecycle log SHA-256: `68fb032c2716f26c3fa8c4082d024784629adce51ef79c603ffbb0a94eea343c`; corrected dashboard log: `7166f8ddcd27ec9cc9cff26b9cd751b5242c6868d6b9e5285bc2b6b4b9548365`.

Two package builds are byte-identical to the preceding published Skill: 63 members, SHA-256 `d05fbc0aa35e2a8e12fd753c94ad9a5b410c803c8e1b60ee7bbf29f5184f26ca`. No runtime or installed Skill member changed. This candidate has not been published or run in hosted CI; no Mac/Windows user-device result is inferred.

Independent read-only integration verification passed: 13 evidence tests (0.008s), 9 normalized logic tests (4.041s), and 3 ledger tests (0.022s), each exit 0 and zero skips. Log SHA-256 values respectively: `8113cd31b0c939b605c4b9390f4da1eb0f89604ae69954c66f76c5475f3bc8aa`, `4c9ccc9e0fa6295029f915ab507a215b8bca4967053d1ab7770bf3a24e47951c`, `215c7ee5ca4a3af1518913120cb5bca257329f220eec1915e156e4fb167c1009`. Exact comparison found seven new evidence/test files and five modified documentation/ledger files, no deletions, and only T22/T25 acceptance/evidence/next-step fields changed. Original requirements, all scheduling/dependencies and every installed Skill source remain unchanged.

## Thirty-fifth rebuild: asset routing and immutable recorded inputs, 2026-10-19

T26/T33 are supported by nine retained synthetic replies and a separate whole-response review. The initial T26 replies and later continuations left route elicitation unobserved; the adaptively added fresh ninth input supplied a complete goal and explicitly distinguished assets from choice. This limitation remains visible. Normalized helper tests did not generate the replies. Original requirements/layers stay unchanged: 51 accepted, 167 pending. User-device and account behavior are not certified.

The sole runtime change records `deepcopy(value)` to isolate a fact from later mutation of its caller-owned JSON value. Five regressions genuinely fail on the preceding runtime; all 31 normalized tests pass on the candidate. Existing historical evidence remains byte-identical. The exact-source compatibility supplement reconstructs genuine prior bytes and separately compares 13 complete current/historical replays, 15 guarded subscription calls and 163 upgrade calls. It neither substitutes hashes nor regenerates historical dialogue. Independent review verified all 232 retained packet files and 50 prerequisites, including negative drift controls. Arbitrary non-JSON objects and malicious caller mutation of returned state are outside this fix.

The first aggregate was a real failure: 1,982 collected tests, 14 failures, one import error, eight skips, 63.176 seconds, exit 1. Strict source pins rejected the changed runtime; the subscription import error also prevented collection of its remaining tests. These failures were retained. The compatibility supplement and explicit dated source-pin updates were reviewed before the final run; original evidence was not rewritten.

Final full command `python -m unittest discover -s tests -v`: **2,069 total, 2,061 passed, eight skipped**, 93.909 seconds, exit 0. Log SHA-256: `44244c3faf78941f380efd26961f0fe9046291be96b647180fc9e7f3f810a0dc`. Independent integration ran 47 asset logic/integrity tests and three ledger tests, all passed without skips. Strict C locale, disabled UTF-8 mode and cp1252:strict output ran the 47 asset tests successfully. Independent compatibility verification passed 67 tests both with strict cp1252 output and with simulated cp1252 default file decoding. Python 3.10 grammar/API review is not actual Python 3.10 execution.

Both existing Node synthetic suites, compilation and two reproducible package builds passed. The package contains the same 63 members; only interview_flow.py changed. Package SHA-256: `e7077430e9b720bdc82a66547de64a7a18910186f229b94ee8777502fa7e39a8`. Test/evidence material is excluded from the installed Skill. The candidate has not been published or executed in hosted CI. No Mac/Windows user-machine acceptance is inferred. Rollback restores the previous fact-recording line and this batch's evidence/consumer changes; no user data or host configuration was changed.

Public-scope audit found two inherited concrete workspace locations in historical command examples. They are now displayed as `${PROJECT_ROOT}`; the historical records remain unchanged and the presentation-only redaction is stated on that page. After this adjustment, the full suite again ran 2,069 tests: 2,061 passed, eight skipped, 94.212 seconds, exit 0; log SHA-256 `e935005edef393c9f8a9626d56dcd1cde40b236dfe9b2bf2e83a85abb44ccdea`. No new runtime or package change resulted.

## Thirty-sixth rebuild: Windows replay receipt correction, 2026-10-19

Published commit 1ea6ddce02f4693d564b0a040e98ae75676ae84d passed Ubuntu, macOS, Python 3.10 and preview CI, but its Windows suite failed one compatibility check (2,069 collected, one failure, 397 skipped). Complete old/current Windows outputs matched; the subsequent fixed digest incorrectly required the POSIX trace. The unchanged original resume suite intentionally skips its POSIX temporary cleanup fixture on Windows.

The correction retains all 13 original POSIX hashes and whole old/current comparisons. The resume suite alone has explicit POSIX and Windows profiles, exact trace-key inventories and exact test/skip identities and reasons. The Windows profile was derived by running the unchanged suite with only its existing decorator outcome simulated in isolated subprocesses; this is not a native Windows rerun. Remaining states are compared in full, with negative tests rejecting missing/extra/modified semantic data and skip drift. No runtime, original suite, historical packet, package member or original-case count changed.

Final local full suite: 2,072 total, 2,064 passed, eight skipped, 95.572 seconds, exit 0; log SHA-256 `5f40473e04bd7033baf72fc0df9b82f1ed1b5f022c966c6e1532808cf7e2e226`. Focused compatibility12, subscription31, upgrade10 and local-incident14 tests passed. Three new platform regressions passed under strict cp1252 output and C locale. Both Node suites, compilation, Python 3.10 grammar/explicit text-encoding review and reproducible packaging passed. Package remains `e7077430e9b720bdc82a66547de64a7a18910186f229b94ee8777502fa7e39a8`, 63 members. Native Windows confirmation of this correction remains pending its new CI run; prior failure is preserved.

Independent review cleared the exact platform-profile correction: 12 focused checks and a 76-test combined run under strict cp1252 output plus simulated cp1252 default file decoding passed with no skips. The full verifier's simulated nt path used genuine old/current subprocess outputs and the original one-test skip. Log hashes: focused `c2bf673240f6c40bfb0abb61551facedf35c59b3e4fde4c61b1123340f47b8c9`; combined `faf54dca2016c8c37aa650cf87d446e5475219df04ae3491a39bdb311b9a7f26`; nt simulation `9f2b6ee0e3f717923908f0d02f425c79781c4031bf4659ef53b51a2f514f1ecc`. This retains the explicit native-confirmation limitation above.


## Thirty-seventh rebuild: bounded read-only Darwin metadata observation, 2026-10-19

The preceding Windows replay correction completed all four hosted CI jobs successfully at commit d7c159dfb9e739980454bd7dfd972111c928d8c2. Ubuntu passed 2,064 with eight skips; macOS passed 2,055 with 17 skips; Python 3.10 passed 2,059 with 13 skips; Windows passed 1,675 with 397 skips. Skips remain explicit limitations.

This batch adds an opt-in observer of an already-open caller-owned descriptor. It reads bounded attribute names and stat metadata only, returns fixed category counts, and never reads attribute values, file contents or ACLs. It does not mutate metadata or grant write admission. Two name reads and surrounding stat checks detect some changes without claiming an atomic snapshot. The production transaction, receipt and cleanup gates are unchanged. Native execution of the new observer remains not_run; earlier separate Mac experiments are supporting API evidence only.

The initial aggregate failed three checks: two exact historical packager pins and a guide-example assertion edited during that run. All failures were retained. The package now adds exactly one observer member (64 total). Historical evidence remains unchanged; the compatibility check pins both the current builder and historical proof, then removes exactly one known manifest item and verifies the entire historical builder hash. Negative controls reject additional changes, missing/duplicate entries and altered proof. The original T09 source tests and complete evidence were independently reviewed; no original acceptance count increased (51 accepted, 167 pending).

Final aggregate: 2,111 total, 2,103 passed, eight skipped, 96.310 seconds, exit 0. Log SHA-256: `02838d1f76093d0808e4a0a3a31fd9641b098c14e155dca7f056c3d083b0b1ed`. Both existing Node synthetic suites, script compilation and two byte-identical package builds passed. A mistaken direct invocation of the CI-only interaction driver returned INTERACTION_REQUIRES_CI; the correct existing synthetic protocol suite subsequently passed, without running a browser. Package SHA-256: `ac241ddd1a924f8081020a98e4b9779d9d92863e6e791250cc54c23f6111b916`. The new documentation and tests are excluded from installation. No user-machine write, recovery, cleanup or routing success is claimed.
