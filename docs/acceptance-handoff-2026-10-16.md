# 2026-10-16 验收交接

## 冻结代码基线与真实交互回执

代码基线 `af3be41ba287c3b9c2f44775c25d97bb04b8c1be`：[三平台CI38778429996](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38778429996)成功。892项测试：Linux884通过/8跳过，macOS883通过/9跳过，Windows771通过/121跳过；Node、编译与可复现包通过。包SHA-256 `02f822e26833172f00816625a0e924c940639f598f164c948cdbd97a44bc4a87`。

[真实Chrome交互CI38778430369](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38778430369)成功。artifact `11994278104`已取回校验，Chrome155在1440×1000和390×1100下实际验证12处summary的Tab焦点/可见焦点轮廓、Enter/Space展开折叠、全展开无横向溢出；页面范围观测只有一个本地文档、零子资源。此为CI合成页面交互证据，不能证明全浏览器网络隔离、真实诊断结果或用户设备。原生上下文仍为Mac RUNTIME_PATH_INVALID、Windows CONTEXT_FOREIGN阻塞跳过，后续ABI/运行时/namespace/设备授权缺口保持。

失败历史保留：43d63f6首次交互未输出可用诊断；29ab8bd定位Enter未展开。af3be41修正CDP文本键事件和错误的native keycode映射，原DOM/焦点/布局断言及安全策略未放宽；不靠重试或skip掩盖失败。

## 先前代码基线

`78535f69b523287a0304c1be017dd60e491554f0`：[三平台CI 38772721879](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38772721879)全部成功。865项单元测试：Linux857通过/8跳过，macOS856通过/9跳过，Windows744通过/121跳过；三端Node合成生命周期、编译、可复现打包全部成功。包SHA-256：`46ef4ca7348147797a64960bd75868431afb31543fba982c93489bb19366c8ad`。

实际CI上下文smoke：Windows在capture/CONTEXT_FOREIGN明确阻塞跳过，Mac在capture/RUNTIME_PATH_INVALID阻塞跳过。修复后的Windows不再出现此前token_restrictions返回大小错误，但后续未到达的ABI路径和真实桌面验收仍未通过，Mac新部分元数据API尚无原生执行证据。无真实用户设备或DNS探测。

[同提交合成截图CI 38772721875](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38772721875)成功；下文记录已取回并查看像素的d9582ce截图，不能将静态截图当作交互验收。此前失败轮次保留为历史记录。

## 已发布与已验证

- `06735926b14c15259272735d495af9707008e29c`：Windows离线预检、极简面板和HTTPS/STUN附件；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38752978424)成功。Linux/macOS 517通过/5跳过，Windows416通过/106跳过，均522项
- `974ee563d22451aba0008f9fe2822995d94c1bd3`：DNS编解码、Mihomo查询库和面板DNS样本；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38756716054)成功。Linux/macOS579通过/5跳过，Windows478通过/106跳过，均584项
- `fcc46b9a5a269f0aa3423edb898f49c6f4212413`：Mac/Windows系统DNS库、样本投影和命令清理修复；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38760023126)成功。Linux/macOS648通过/6跳过，Windows542通过/112跳过，均654项
- `044a891401aa0220ed3cac123eabee3c9a34eb98`：上下文/诊断会话增量已发布；首次Windows CI有三个测试可移植性错误，`a016769badfbfa1fd25aa9376dc2465c7455f16d`已修复。修复后[三平台CI 38765033394](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38765033394)成功；Windows首次PowerShell mock超时，仅重试失败job后通过，未放宽断言或生产预算
- `db102e9e07181929c6a68699fbc21eeef813405e`：数值边界与私有配置候选已发布。Windows合成审批过期测试依赖短sleep导致一次失败，`f7baad5d7b01ab48e4300a7f93ca2d722b85d298`改为注入时钟，原断言/生产预算不变。当轮Linux/macOS通过，Windows重复PowerShell mock超时导致当轮未能三端通过；后续代码基线三端成功见上文，间歇超时根因未被确定
- `87364bdc51a808557c71a08d184a2cc98d874488`：[CI 38767766447](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38767766447)三端单元套件通过；Windows实际上下文smoke非零子进程失败，该历史轮CI失败，后续构建步骤跳过。Mac上下文在capture/RUNTIME_PATH_INVALID阻塞并明确跳过，不能当完整ABI或桌面通过
- 同轮Windows原15秒PowerShell mock通过，额外first/repeat诊断为0.343/0.297秒；此前间歇超时原因仍未知，不据本轮成功宣称修复
- `56509f49c0e0c704f982a0779d10db54ec5ef727` 首轮新截图测试在Windows缺少模拟SIGKILL常量，`3a5d98a4e6622831c40fa577da9d54956289fcc8`已修复。[CI 38769891354](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38769891354) Linux/macOS成功，Windows836项单测715通过/121跳过，随后实际原生smoke失败：CONTEXT_UNKNOWN/capture；整个CI未通过，仍需固定阶段诊断定位
- 合成浏览器[首次截图流程](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38768934000)因runner缺少中文字体在启动Chrome前失败，无PNG。当时没有视觉产物；后续临时内嵌字体修复已产生并核验双尺寸PNG，见下文静态布局证据

- `d9582ce75e1f4d5094a9932b98d52f30dc6604dc`：[CI 38771591206](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38771591206) Linux/macOS成功，Windows862项单元741通过/121跳过，原生失败进一步定位token_restrictions/return_size_mismatch，该历史轮整体失败；专用兼容修复78535f69的三端成功及原生阻塞结果见上文
- 同提交[合成截图CI 38771591023](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38771591023)成功，artifact `11991666940` 已下载核对ZIP/PNG哈希并查看真实像素：1440×1000与390×1100中文清晰、无可见裁切。仅布局证据，不代表交互/网络/真实设备通过

以上标明三平台成功的各轮Node合成生命周期、编译及可复现打包通过。跳过不等于通过，CI临时环境与模拟API不代表用户电脑或真实网络验收。

## 追加的离线访谈增量

本机默认建议可明确接受且不重复问路线；单轮规范化answers列表原子吸收后只问缺口，顺序/冲突/异常回归已覆盖。宿主仍负责自然语言提取，未给出的套餐不猜测；动作门禁不变。该追加批次`fb8ceede005dd08496b5bea0d21e9e4284e5dafc`的[CI38775571648](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38775571648)三端成功：881项，Linux873通过/8跳过、Mac872通过/9跳过、Windows760通过/121跳过；原生smoke仍为上列明确阻塞。Node/编译/可复现包成功。后续真实键盘交互已通过，精确回执见顶部；其范围仍不等于用户设备验收。

## 能用的入口与仍需集成的库

- 离线面板：`status_dashboard.py --input <本地报告> --probes <可选本地附件> --output <新HTML文件>`；只投影已有证据，不运行探测、不打开浏览器。省略附件参数也可用
- 诊断会话：先查看 `diagnostic_session.py --help`，再按其平台范围和精确读取提示决定是否运行。终端新nonce确认不替代可信设备/宿主权限。CLI仅做有限元数据读取；DNS保持关闭
- HTTPS、STUN、Mihomo与系统DNS是宿主库接口，尚不能把永真回调、旧报告或JSON布尔当成生产集成。每个目标、名称、地址族与可能上游披露均需要对应授权
- 配置候选库只在内存中改选定规则policy token、重解析核对并产生私有差异；没有apply，原生版本/归属/即时授权阻塞仍保留
- Windows离线预检始终阻止写入；完整元数据保留、写入/回读/恢复仍未完成。已有POSIX恢复也仅限已授权的精确事务与备份范围

## 建议人工验收顺序（不会自动执行）

1. 核对目标机器、当前用户、宿主可信来源及仓库固定提交；先读相关模块契约和限制
2. 只看帮助与离线合成报告，检查极简表格、展开证据、取消/过期/错误是否可见；CI合成视觉与键盘已取得上述证据，用户设备/浏览器版本仍需对应验收
3. 若准备核验本机元数据，先确认显示的读取范围；Windows观察即使成功也可能保持控制台账户关系未知、绑定阻塞，不应强行放行
4. 真正DNS/HTTPS/STUN测试另行批准精确目标、名称/端点、类型、预算和信息披露，先补齐宿主身份、命名空间与运行时信任实现；不在缺前提时使用测试回调
5. 系统/浏览器路径、DoH、DNS权威关联、故障防直连、Windows事务恢复等逐项保留未验收状态；测试数量不转换为完成百分比

## 边界

本轮没有访问用户设备、运行公网探测、启动Claude、改变网络/代理/权限、安装依赖、处理凭据或删除个人数据。PC0接触门禁保持关闭。后续验收发现失败应保留原始本地证据并脱敏汇报，不上传秘密、真实地址或个人机器完整日志。
