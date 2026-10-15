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
