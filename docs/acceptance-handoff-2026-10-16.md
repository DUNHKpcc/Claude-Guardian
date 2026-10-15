# 2026-10-16 验收交接

## 已发布与已验证

- `06735926b14c15259272735d495af9707008e29c`：Windows离线预检、极简面板和HTTPS/STUN附件；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38752978424)成功。Linux/macOS 517通过/5跳过，Windows416通过/106跳过，均522项
- `974ee563d22451aba0008f9fe2822995d94c1bd3`：DNS编解码、Mihomo查询库和面板DNS样本；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38756716054)成功。Linux/macOS579通过/5跳过，Windows478通过/106跳过，均584项
- `fcc46b9a5a269f0aa3423edb898f49c6f4212413`：Mac/Windows系统DNS库、样本投影和命令清理修复；[三平台CI](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38760023126)成功。Linux/macOS648通过/6跳过，Windows542通过/112跳过，均654项
- `044a891401aa0220ed3cac123eabee3c9a34eb98`：上下文/诊断会话增量已发布；首次Windows CI有三个测试可移植性错误，`a016769badfbfa1fd25aa9376dc2465c7455f16d`已修复。修复后[三平台CI 38765033394](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38765033394)成功；Windows首次PowerShell mock超时，仅重试失败job后通过，未放宽断言或生产预算
- `db102e9e07181929c6a68699fbc21eeef813405e`：数值边界与私有配置候选已发布。Windows合成审批过期测试依赖短sleep导致一次失败，`f7baad5d7b01ab48e4300a7f93ca2d722b85d298`改为注入时钟，原断言/生产预算不变。新轮Linux/macOS通过，Windows重复PowerShell mock超时仍在定位，尚不能称三端通过
- `87364bdc51a808557c71a08d184a2cc98d874488`：[CI 38767766447](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38767766447)三端单元套件通过；Windows实际上下文smoke非零子进程失败，整个CI仍失败，后续构建步骤跳过。Mac上下文在capture/RUNTIME_PATH_INVALID阻塞并明确跳过，不能当完整ABI或桌面通过
- 同轮Windows原15秒PowerShell mock通过，额外first/repeat诊断为0.343/0.297秒；此前间歇超时原因仍未知，不据本轮成功宣称修复
- `56509f49c0e0c704f982a0779d10db54ec5ef727` 首轮新截图测试在Windows缺少模拟SIGKILL常量，`3a5d98a4e6622831c40fa577da9d54956289fcc8`已修复。[CI 38769891354](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38769891354) Linux/macOS成功，Windows836项单测715通过/121跳过，随后实际原生smoke失败：CONTEXT_UNKNOWN/capture；整个CI未通过，仍需固定阶段诊断定位
- 合成浏览器[首次截图流程](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38768934000)因runner缺少中文字体在启动Chrome前失败，无PNG。本批加入临时内嵌字体修复；实际执行和下载查看像素前，视觉验收保持待验证

- `d9582ce75e1f4d5094a9932b98d52f30dc6604dc`：[CI 38771591206](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38771591206) Linux/macOS成功，Windows862项单元741通过/121跳过，原生失败进一步定位token_restrictions/return_size_mismatch，整体仍失败；本批专用兼容修复等待新CI
- 同提交[合成截图CI 38771591023](https://github.com/DUNHKpcc/Claude-Guardian/actions/runs/38771591023)成功，artifact `11991666940` 已下载核对ZIP/PNG哈希并查看真实像素：1440×1000与390×1100中文清晰、无可见裁切。仅布局证据，不代表交互/网络/真实设备通过

以上标明三平台成功的各轮Node合成生命周期、编译及可复现打包通过。跳过不等于通过，CI临时环境与模拟API不代表用户电脑或真实网络验收。

## 能用的入口与仍需集成的库

- 离线面板：`status_dashboard.py --input <本地报告> --probes <可选本地附件> --output <新HTML文件>`；只投影已有证据，不运行探测、不打开浏览器。省略附件参数也可用
- 诊断会话：先查看 `diagnostic_session.py --help`，再按其平台范围和精确读取提示决定是否运行。终端新nonce确认不替代可信设备/宿主权限。CLI仅做有限元数据读取；DNS保持关闭
- HTTPS、STUN、Mihomo与系统DNS是宿主库接口，尚不能把永真回调、旧报告或JSON布尔当成生产集成。每个目标、名称、地址族与可能上游披露均需要对应授权
- 配置候选库只在内存中改选定规则policy token、重解析核对并产生私有差异；没有apply，原生版本/归属/即时授权阻塞仍保留
- Windows离线预检始终阻止写入；完整元数据保留、写入/回读/恢复仍未完成。已有POSIX恢复也仅限已授权的精确事务与备份范围

## 建议人工验收顺序（不会自动执行）

1. 核对目标机器、当前用户、宿主可信来源及仓库固定提交；先读相关模块契约和限制
2. 只看帮助与离线合成报告，检查极简表格、展开证据、取消/过期/错误是否可见；浏览器视觉与键盘操作仍需真正验收
3. 若准备核验本机元数据，先确认显示的读取范围；Windows观察即使成功也可能保持控制台账户关系未知、绑定阻塞，不应强行放行
4. 真正DNS/HTTPS/STUN测试另行批准精确目标、名称/端点、类型、预算和信息披露，先补齐宿主身份、命名空间与运行时信任实现；不在缺前提时使用测试回调
5. 系统/浏览器路径、DoH、DNS权威关联、故障防直连、Windows事务恢复等逐项保留未验收状态；测试数量不转换为完成百分比

## 边界

本轮没有访问用户设备、运行公网探测、启动Claude、改变网络/代理/权限、安装依赖、处理凭据或删除个人数据。PC0接触门禁保持关闭。后续验收发现失败应保留原始本地证据并脱敏汇报，不上传秘密、真实地址或个人机器完整日志。
