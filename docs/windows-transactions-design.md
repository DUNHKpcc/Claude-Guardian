# Windows 精确文件事务：受控写入与离线恢复设计评审

日期：2026-10-15。状态：**所有者已接受默认不提权、完整元数据不能保证即停止的方向；尚未实现 Windows apply / rollback**。这是设计方向接受，不批准任何真实文件变更、提权、安装或权限修改，也不改变现有操作门禁。需要提权时须另行说明精确范围并请求单次授权；当前未实现或执行该路径。

依据：[ENV §3、§17](../skills/claude-guardian/sources/design/D-ENV-v0.3.md)、[主规范 §4.2](../skills/claude-guardian/sources/design/D-SPEC-v0.1.10.md)、[实现跟踪](implementation-tracker.md)，以及现有 `transactions.py` / `windows_transactions.py` 的实际边界。对应 ENG-08、VAL-02/06/07，重点覆盖 ENV-T25—28、67—68、102。

## 1. 结论与当前证据

建议先研究并实现**不提权、同卷本地 NTFS、单个既有普通文件**的窄适配器：私有备份、完整元数据适用性检查、暂存文件校验、一次句柄重命名替换、冲突安全恢复。不能完整检查或保存安全信息时，明确不支持；不把“普通文件”当成“没有隐藏安全元数据”。

这不是要求先解决所有 Windows 文件类型。ADS、EFS、压缩/稀疏文件、云占位符、链接、未知扩展属性等可先拒绝。相反，源文件已有 ACL/SACL 不能因难处理而静默丢弃。

现有基线 `be2e626a3626bfb853babf2b407fd67be146ec82` 的 [CI 38711511300](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38711511300) 和 [验证记录](validation.md) 已记录四项 Windows 原生临时夹具通过：只读计划、ADS/硬链接拒绝、junction 祖先拒绝、注入元数据失败后的句柄清理。最后一项**不是实际 ACL 拒绝测试**。这些证据不覆盖写入、私有备份、崩溃恢复或用户配置。

下述原生事务机制仍属于待实现设计；本次只新增 §12 的离线预检和流格式解析。既有 `windows-read-only-file-plan/1` 仍不能用于提交；不能通过修改 `apply_status` 或增加一个布尔开关升级为可执行计划。

## 2. 与 POSIX 底座共用和不同的契约

共用：精确目标、动作 ID、完整计划摘要、过期时间、应用前重读、两次实时授权、先验证备份再提交、保留恢复记录、后续用户修改阻止整文件回滚。授权回调的 `True` 是可信宿主的断言，不是人类同意的密码学证明；计划摘要也不是凭据。

Windows 必须独立实现以下部分：

- 权限隐私依赖安全描述符，不能用 `chmod(0700/0600)` 代替 DACL
- 句柄共享模式与删除/重命名访问相互影响；现有只读句柄不能直接留到所有替换 API 内继续使用
- 文件安全信息不仅是 owner/group/DACL；SACL、完整性标签和资源属性需单独识别
- 原子命名切换、进程崩溃可恢复、断电持久性是三项不同承诺
- 平台与卷类型按实际观测绑定；不能用 WSL/POSIX 运行结果替代 Windows 原生证据

POSIX 也依赖宿主排除并发写入，不能把 Windows 适配器要求提升成抵御同权限恶意进程/管理员的隔离系统。但宿主必须有真实停写安排；“exclusive_access=True”本身不能证明 GUI、同步程序和后台服务已停止写入。

## 3. 首个候选支持范围与失败出口

候选条件全部满足后才可生成新的执行计划：

1. Windows 原生进程，明确的目标设备/执行用户/命名空间，已授权的文件和备份位置
2. 显式卷 GUID 路径、本地固定 NTFS 卷、祖先与文件均无 reparse/recall/offline 状态；继续拒绝 UNC、设备路径、驱动器相对路径和未核验驱动器别名
3. 既有单链接普通文件；数据上限沿用 4 MiB；只允许明示的属性和可完整处理的安全描述符
4. 原文件 owner 与实际 TokenUser 匹配；不代其他用户变更文件，不接收调用者提供的 SID/令牌作为身份依据
5. 无活动数据库、无应用内锁定状态；宿主已经确认目标应用的停写/重启边界
6. 拟写内容、原始备份、暂存文件、日志均有大小上限；每阶段有取消/预算检查
7. 本地恢复解释器/工具和操作说明在离线状态可用，不需要 Claude、网络、管理员服务或新安装依赖

失败分类须可区分：`PLATFORM_UNSUPPORTED`、`TARGET_MISMATCH`、`SECURITY_METADATA_UNAVAILABLE`、`UNSUPPORTED_METADATA`、`EXCLUSIVE_ACCESS_REQUIRED`、`BACKUP_NOT_PRIVATE`、`STALE_FILE`、`CANCELLED`、`TIMEOUT`、`RECOVERY_REQUIRES_RECONCILIATION`、`ROLLBACK_CONFLICT`。这些是拟议稳定类别，不宣称当前代码已实现所有错误码。

## 4. 元数据：先证明可保存，再允许提交

### 4.1 完整快照与拒绝策略

候选快照包含：卷 ID、文件 ID、所有祖先 ID、大小、链接数、数据哈希、基础属性、创建/访问/修改/变更时间、完整安全描述符及控制位、额外流类别清单。原始安全描述符和私有路径只进入受保护恢复目录，不进入 stdout、普通报告或 PR。

`GetFileInformationByHandleEx` 用于已打开对象的基础信息、ID、标签和流检查。[Microsoft API 文档](https://learn.microsoft.com/en-us/windows/desktop/api/winbase/nf-winbase-getfileinformationbyhandleex)

拟用有界 `BackupRead` 补足普通数据流列表看不到的备份元数据。按 `WIN32_STREAM_ID` 严格解析；只接受已实现的默认数据和完整安全描述符，其他流先拒绝，不调用 `BackupSeek` 跳过错误后宣称完整。EA、对象 ID、链接、reparse、稀疏或未知记录均需要明确分支。[流类别文档](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-win32_stream_id)

`BackupRead` 的安全信息读取仍受句柄权限约束；缺少 `ACCESS_SYSTEM_SECURITY` 时不会读取 SACL。必须正确释放备份上下文，失败和取消也调用 abort 清理；EFS 不走此路径。[BackupRead 文档](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-backupread)

短文件名不能遗漏。候选办法是在获准的直接父目录内，使用有界 `FileIdBothDirectoryInfo` 找到与目标 ID 一致的条目；只保留该条目，不导出其他文件名，不递归扫描。存在短名先拒绝；无法取得完整、有界结果也拒绝。父目录枚举范围须由宿主的精确读取授权覆盖。此结构提供短名字段。[结构文档](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_id_both_dir_info)

### 4.2 安全信息不是可忽略的未知项

完整安全描述符需要 owner/group/DACL/SACL 及相应保护、继承、完整性和资源属性。`BACKUP_SECURITY_INFORMATION` 表示完整安全信息，查询需要 `READ_CONTROL` 与 `ACCESS_SYSTEM_SECURITY`；只读取 owner/group/DACL 不能证明 SACL 为空。[权限矩阵](https://learn.microsoft.com/en-us/windows/win32/secauthz/security-information)

**默认不提权、不启用新令牌权限。** 若现有执行权限不能完成完整检查或复原，返回不支持。对常见标准用户，这可能使首批写支持范围很小甚至不可用；必须如实报告，不能为了扩大覆盖退化为仅比较 DACL。

`GetSecurityInfo` 可按句柄读安全描述符，但不解决并发安全描述符变更；读取 SACL 的权限取得本身也是需要单独评审的权限路径。[GetSecurityInfo 文档](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-getsecurityinfo)

新暂存对象必须在不可被其他用户访问的区域内完成所需安全描述符设置，并读回比对。`SetSecurityInfo` 使用对象句柄；设置 NULL DACL 会授予所有人访问，必须拒绝误用。它可能传播可继承 ACE，因此禁止拿用户现有目录做“修复权限”的操作对象。[SetSecurityInfo 文档](https://learn.microsoft.com/en-us/windows/win32/api/aclapi/nf-aclapi-setsecurityinfo)

不使用“BackupWrite 返回成功”推导完全恢复：其 SACL 和完整性 ACE 恢复另有权限要求。若以后采用该 API，只对白名单化、已验证的私有备份数据使用；绝不向现有目标盲目重放任意备份流。[BackupWrite 文档](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-backupwrite)

### 4.3 明确预期变化

源文件全部快照永久随本次备份保存。候选策略保留创建、访问、修改时间和允许属性；NTFS 文件 ID 与系统生成的变更记录可能因替换改变，必须在计划中列为预期变化，不能承诺原物理身份可恢复。暂存后与提交后的比较规范需分别定义，避免把合法的新 ID 当失败，或忽略真正的 ACL/字节变化。若某时间/属性无法按已批准策略保持，则阻止提交，不能提交后才扩大允许差异。

这只是文件层契约。保留修改时间不证明应用重新载入；应用验收另外执行，不能提前启动 Claude 或连接网络。

## 5. 私有备份与暂存区

建议每次动作在**已授权且验证私有的备份根目录**下建立随机批次目录。首版要求与目标同卷，以减少不同卷丢失/恢复和替换语义；没有合适位置时不自动改用云盘、公共 TEMP 或用户桌面。

- 使用实际执行 TokenUser 生成明确、非 NULL 的 DACL；批次目录只允许该用户所需访问，不自动增加 Everyone、Users、Authenticated Users 或任意调用者 SID。SYSTEM/管理员仍具有操作系统级能力，不能宣称备份抵御管理员
- 通过 `SECURITY_ATTRIBUTES` 在 `CreateDirectoryW` / `CreateFileW(CREATE_NEW)` 时设置安全描述符；目录/文件名碰撞立即停止，绝不复用不明对象
- DACL 设置为受保护，防止继承宽权限；目录和文件显式分别设置，不依赖“以后再 chmod”。创建后从句柄复核 owner、DACL、控制位、卷和 reparse 状态，核验通过前不写原始秘密
- 备份根及其祖先也必须检查；安全子目录不足以抵御不可信父目录的删除/替换权限。不能静默收紧已有父目录权限，不能自动清除原来的 ACL
- `original.bin`、原始元数据、执行计划、阶段日志分开保存并分别哈希。原文件 ACL 作为**备份内容**存储，不能把它直接应用到承载秘密的备份文件上
- 暂存文件可在同卷私有批次内准备；只有完成元数据检查且宿主维持排他边界后，才能按目标最终权限设置。设置目标安全描述符后，暂存句柄必须持续禁止其他读取/写入/删除打开，直到命名切换；不能仅靠父目录“不允许遍历”保证秘密，因为执行身份可能具有绕过遍历检查的权限。若所选 API 要求提前关闭该句柄而会暴露数据，则此路径不支持

创建时传入安全描述符与事后继承的差异，见 [CreateDirectoryW](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-createdirectoryw)；保护 DACL 的控制位示例见 [SetSecurityDescriptorControl](https://learn.microsoft.com/en-us/windows/win32/api/securitybaseapi/nf-securitybaseapi-setsecuritydescriptorcontrol)。

保留所有恢复数据；自动清理/保留期限不属于这次设计。后续释放空间需另行明确授权。

## 6. 并发、句柄与原子提交

### 6.1 首选研究路线

使用固定系统 DLL、明确 ABI 的 `SetFileInformationByHandle(FileRenameInfo)`，对已校验暂存句柄进行一次同卷 replacement rename。候选输入：`ReplaceIfExists=TRUE`、已持有的目标父目录句柄作为 `RootDirectory`、单个目标 basename；不接收额外路径段。该结构支持相对目录句柄，文件名长度以字节计算；ABI 要按目标架构验证，不能把网页格式直接照抄成 ctypes 布局。[FILE_RENAME_INFO](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-file_rename_info)、[SetFileInformationByHandle](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-setfileinformationbyhandle)

这是**候选单文件命名切换原语**，尚无本项目写入证据。必须用原生观察者/故障注入证明声明范围内无半写内容与意外空窗；不能从函数名推出任意文件系统的崩溃原子性。不同卷、需要额外 POSIX rename flags 或绕过 readonly 的情况先拒绝。

### 6.2 真实排他边界

1. 校验阶段保持所有祖先句柄，禁止 delete sharing；目标初始拒绝 write/delete sharing，防止通常的数据写入与重命名
2. Windows share flags 不阻止所有属性/ACL 更新。宿主须维持应用停写、ACL/映射不变的边界；用前后安全摘要检测可见变化，不声称能检测任意“修改再改回”的恶意对手
3. 提交前重新检查目标/父目录/备份根身份、完整安全信息、数据哈希和计划过期，再调用精确摘要授权回调
4. 替换可能要求关闭目标旧句柄或使用兼容的 delete sharing。**允许在可信宿主排他保证下关闭旧目标句柄**；祖先和暂存句柄仍保持。此窗口由同一宿主保证覆盖，不能用“检查完再 close”冒充系统级 CAS
5. 若目标进程、端点防护、索引器等持有冲突句柄，报告 sharing/access failure；不结束安全软件、不改排除项、不增加共享权限来绕过保护。允许在新一次状态检查和仍有效授权下有限重试，不能无限循环或盲重放提交
6. 提交后先使用仍持有的暂存对象句柄核验字节、安全信息及允许属性，并核验它的新名称/父目录归属。若排他共享模式阻止另行重开，先完成该句柄验证，再在同一宿主排他边界内关闭并从受控目标入口重开，确认目标仍对应提交 ID。不得为验证自行增加未批准的其他读取者。宿主在最终验证和状态落盘前不能释放停写保证

若宿主不能提供关闭旧句柄期间的排他保证，这一设备/文件不支持 apply。不是要求新建常驻锁服务，也不是要求完美防御管理员。

### 6.3 不默认选择的替代方案

`ReplaceFileW` 可以合并 DACL、创建时间、短名、对象 ID、部分其他属性和未冲突命名流；结果使用替换文件的 ID。它没有文档化的完整 SACL/owner/group 保留承诺，`REPLACEFILE_WRITE_THROUGH` 不受支持，ignore-ACL/merge flags 会放弃保障。错误 1175/1176/1177 还存在不同名称/位置结果。因此不能作为免元数据检查的捷径；若以后选用，要单独实现错误状态协调，且不使用忽略错误标志。[ReplaceFileW](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-replacefilew)

不做原地 truncate/write：那会破坏单文件提交的原子性。不做手写“旧文件改名、新文件改名”双步替换。不采用 TxF 作为新依赖；Microsoft 建议优先研究其他方案。[TxF 替代方案](https://learn.microsoft.com/en-us/windows/win32/fileio/deprecation-of-txf)

## 7. 计划、授权和日志顺序

新的执行 schema 独立于只读计划，至少绑定：

- action_id、适配器版本、目标设备/用户/namespace、卷与祖先/文件身份
- 原字节/完整元数据哈希、私有拟写字节或受保护内容引用及哈希、受影响键、语义差异摘要
- 精确备份根身份/路径、同卷限制、允许元数据差异、到期时间、预算、停止条件
- 实际采用的恢复能力层级；原生支持矩阵版本

宿主在任何新备份/暂存写入之前取得此次具体操作许可。第一次回调绑定整个计划和备份目的地；第二次在提交前以同一摘要再次确认。回调异常、非 True、超时或取消均停止，不记录回调异常中的秘密。日志记录“宿主断言已批准”及关联 ID，不伪装为人类签名，不接受任意令牌/凭据字段。

拟议执行顺序：

1. 输入/身份/权限预检 → 获取排他边界 → 重读完整源快照
2. 第一次授权 → 创建并核验私有批次 → 写 `original.bin`、元数据和计划；分别 flush、重读、哈希核验
3. 写独立的 `prepared` 记录，含备份/目标绑定；flush 成功前不得提交
4. 创建暂存 → 写拟写数据 → 设置全部允许元数据 → flush → 全部读回核验
5. 写 `commit_intent`，含暂存 ID/哈希和预期目标状态；flush → 最后一次取消/预算/过期/快照检查 → 第二次精确授权
6. 单次替换 → 目标完整核验 → 写并 flush `applied`，包含**实际提交后快照**
7. 返回文件层结果；应用生效、配置 reload 和网络路径仍分别标未测试

日志采用新建、不覆盖的有界记录：序号、前记录摘要、动作 ID、状态、关联哈希。摘要链用于检测破损/不一致，不抗同权限伪造。读取器不信任最新文件名或部分 JSON；未知字段、重复记录、缺口和截断需进入协调分支。备份所在私有信任边界与可信宿主来源仍是前提。

## 8. 崩溃恢复与持久性必须分层

### A. 拟先支持：应用进程崩溃后的协调恢复

操作系统和磁盘仍正常时，在每个阶段强制终止工作进程，重新启动离线恢复程序。恢复程序只读验证记录和当前对象，分类为：源状态未变、已应用且匹配、已恢复且匹配、冲突/不确定。仅 `prepared` 不代表已应用；仅缺 `applied` 也不代表未提交。根据 `commit_intent`、实际 ID/哈希/安全信息和备份完整性判断；无法唯一判断则保留数据并报告人工协调。

文件数据与日志使用 `FlushFileBuffers`，处理失败；这要求相应写句柄。该 API 文档另列了全卷 flush 的管理员要求，不能把它当作无权限的通用目录 fsync。[FlushFileBuffers](https://learn.microsoft.com/en-us/windows/win32/api/fileapi/nf-fileapi-flushfilebuffers)

### B. 不先宣称：断电/内核崩溃后的持久提交

单文件 flush、原子 rename、日志 flush 不能在本项目没有证据时合并成断电一致性承诺。命名空间落盘顺序、存储写缓存、设备行为和日志是否存在需要独立验证；不能默认借用 POSIX directory-fsync 语义，也不能默默执行需要管理员权限的全卷 flush。

首版若 A 通过，只发布 A，明确 B=`not_validated`。若用户实际任务把断电持久性作为必需条件，该任务仍不能放行；不能由一个“接受风险”选项暗降原要求。可继续做私有备份、日志解析和合成故障研究，不必为此先新增服务或提权。

同步 Windows API 可能阻塞。协作式取消和单调时钟预算只在调用之间检查；宿主需要独立工作进程实施硬超时。提交开始后被终止时只能返回/记录“需协调”，不能宣称取消即未变更。恢复记录和离线工具必须在关键动作前准备好。

## 9. 回滚协议

- 从可信私有批次加载 receipt；验证 schema、链、原始备份和完整元数据；原 apply 过期不应阻止合法恢复
- 重新绑定实际目标/用户/卷/祖先和当前对象。当前字节、文件 ID、允许属性及安全描述符必须匹配 `applied` 快照；即使用户后来写入了相同内容，身份/元数据不同仍属于冲突
- 获取新 rollback 授权，绑定 receipt 摘要和恢复目的地；不重用 apply 的回调结论
- 使用同一私有暂存、元数据完整性和单步替换过程恢复原字节及允许元数据；提交前再确认授权和冲突条件
- 保存 `rollback_intent`、新恢复对象 ID、`restored` 与验证结果；不删除原备份，不伪造原来的物理文件 ID
- 崩溃后 receipt 不明确时先协调；不根据用户提供的任意路径恢复，不整文件覆盖后来的无关修改，不自动合并秘密内容
- apply 失败后不未经新授权自动 rollback；如以后需要失败补偿，必须在最初具体授权中明确其范围，并仍进行冲突检查

## 10. 最小测试与发布门槛

所有变更测试仅在明确启用的合成临时目录中运行；不能把测试授权扩大到用户真实配置。平台、Windows build、架构、卷类型、token 权限和文件状态分别记录。

| 测试组 | 必须证明 | 当前状态 |
| --- | --- | --- |
| 既有只读原生边界 | 普通计划、junction、ADS、硬链接、注入失败清理 | 四项 CI 夹具通过；范围见 §1 |
| 私有备份 ACL | 创建时即私有；宽父继承不能进入批次；NULL DACL/额外 ACE/不明 owner 拒绝；另一普通用户读取失败 | 未实现/未测 |
| 实际拒绝与端点防护 | 真正 READ_CONTROL/WRITE_DAC/DELETE 拒绝；共享冲突；安全软件占用时无绕过；句柄完整释放 | 未测；注入失败不能替代 |
| 元数据 | owner/group/DACL/SACL/标签/继承位；EA/对象 ID/短名/未知流准确拒绝；缺 SACL 权限不冒充空 | 未实现/未测 |
| 原子提交 | 观察者只见完整旧/新字节；原始只读/共享冲突不被绕过；相对目录/ABI 在声明架构验证 | 未实现/未测 |
| 宿主并发 | GUI 回写、祖先替换、ACL 更新、同内容换 ID、备份根替换；失去排他边界必须停止 | 未实现/未测 |
| 授权 | 任意计划字段变化使摘要失效；目标不符、过期、两次取消、回调异常/超时不提交 | 写路径未实现/未测 |
| 备份故障 | 同大小损坏、短写、磁盘满、flush 失败、元数据设置失败；提交前失败不改变原目标 | 未实现/未测 |
| 崩溃层 A | 每条日志及替换前后 kill；尤其替换成功但 applied 未写；恢复不猜测、不盲重放 | 未实现/未测 |
| 断电层 B | 独立虚拟机/存储故障测试与明确缓存假设；不能用进程 kill 代替 | 不在首批声明内 |
| 回滚 | 正常、重复请求、备份损坏、目标后来更改、ACL-only 更改、目录换位、prepared-only、离线运行 | 未实现/未测 |
| 隐私/资源 | 哨兵秘密不出日志；上下文/句柄/内存界限；硬超时后恢复路径仍可用 | 写路径未实现/未测 |

交付顺序：元数据与私有备份原型 → 原生权限/并发测试 → 单文件提交与进程崩溃协调 → 冲突安全离线回滚 → 发布窄支持矩阵。每一步可独立提交评审，不因尚不支持所有 NTFS 特性而停做安全工程。

## 11. 真正需要所有者决定的事项

**目前无需为库研究重新询问产品方向。** 默认不提权、不装组件、不降低保证；编写纯逻辑和明确授权的临时夹具属于工程实现。API 选择、日志格式、错误分类和测试细节由工程评审解决。

以下变化才需要先提出明确选择：

1. 若非提权路径因完整安全元数据权限不足而覆盖有限，是否开展一个**可选、单次、精确目标的提权方案**。届时说明所需权限、影响和恢复，不引入默认常驻服务；当前方案不执行它
2. 若未来要宣传断电持久提交，须先决定并验证更高的持久性方案、依赖和成本。当前仅考虑可测试的进程崩溃协调；遇到用户必需断电保证时不自动降低目标
3. 扩大到共享/组织文件、更多备份访问者、云同步目录、加密/复杂元数据，或变更备份保留策略，都是新增范围，不能借“Windows 支持”总括批准

每次真实 apply/rollback 的精确计划授权，以及 PR 的所有者合并确认，始终独立存在。本设计及 CI 通过均不替代它们。


## 12. 已实现的首个有界增量：离线预检与流格式解析

2026-10-15：`windows_transactions.py` 新增两个纯内存接口，不打开文件、不调用原生 API、不启用令牌权限，也不创建备份或执行恢复。

- `preflight(plan, target_ref=...)`：验证现有只读计划、目标引用和有效期，返回 `write_readiness=blocked` 与 `SECURITY_METADATA_UNAVAILABLE`。执行状态 `completed` 仅指解释完成；真实目标绑定、文件新鲜度仍为 `not_checked`。缺少完整安全信息、流采集、短名检查、元数据保存/回读和事务后端分别列出，不把失败归因为未经实际检测的用户权限不足
- `inspect_backup_streams(blob, expected_size=..., expected_sha256=...)`：只解析调用者提供的有界字节。按 20 字节 `<IIqI` 前缀（不含 C 结构尾部填充）、名称字节数和负载长度处理 `WIN32_STREAM_ID`。要求恰好一份默认数据和一份安全描述符记录，顺序不限；数据必须匹配指定大小和哈希
- 仅允许未命名的 `BACKUP_DATA`（属性为 0）以及 `BACKUP_SECURITY_DATA`（属性为 0 或 `STREAM_CONTAINS_SECURITY`）。拒绝其他 ID、未知或修改时读取/稀疏等属性、名称、重复、负长度、超限、截断和尾随垃圾。零字节数据允许；安全负载限制为 20—65536 字节，但**长度不是安全描述符有效性校验**
- 安全负载是未解析的不透明字节。即使格式被接受，仍明确输出 `security_descriptor_validation=not_run`、`security_completeness=unknown`、`native_capture_provenance=not_verified`、`metadata_completeness=unknown`、`apply_status=unsupported`。不接受“完整”开关，不将此结果升级成执行计划
- 两个接口支持协作式取消/预算检查，异常只含稳定代码；不输出原始字节、流名称、路径或安全描述符及其哈希。调用者输入本身仍应私密保存，报告不是授权凭证
- `capabilities()` 分开描述离线接口、现有原生只读计划和未实现能力，明确 `no_elevation_or_privilege_enablement`。旧计划 schema 与 apply/verify/rollback 的无 I/O 拒绝行为保持不变

格式依据：[WIN32_STREAM_ID](https://learn.microsoft.com/en-us/windows/win32/api/winbase/ns-winbase-win32_stream_id)、[Microsoft WinBase.h 常量与结构](https://github.com/microsoft/win32metadata/blob/main/generation/WinSDK/RecompiledIdlHeaders/um/WinBase.h)。[BackupRead](https://learn.microsoft.com/en-us/windows/win32/api/winbase/nf-winbase-backupread) 明确限制 SACL 读取权限；有安全流不能证明该权限或完整 SACL。未来原生采集须独立证明成功到达 EOF、权限、上下文 abort 清理与句柄身份；当前解析器不能证明这些事情，也未调用 BackupRead/BackupWrite。

新增 12 个合成测试覆盖：两种流顺序、空/最大负载、每一截断位置、同大小损坏、重复/未知记录、危险属性、名称、无效参数、取消/超时、秘密不回显、目标不匹配、过期和伪造完整性。云端 Linux 的该模块共发现35项，31通过、4项原生 Windows 测试跳过。此结果仅为离线契约证据，未新增原生 Windows 写入、安全描述符有效性或权限拒绝验收；§10 的原生待实现/未测矩阵保持不变。
