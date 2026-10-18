# Claude-Guardian 离线合成对话记录

本包是实际响应代理按冻结场景逐轮生成的中文答复与实际 helper 调用记录，不是期望答案、评分表或原生验收报告。

## 对话入口

按生成顺序：
1. [ENV-T42 完整三轮](conversations/ENV-T42-through-turn-3.md)
2. [ENV-T41 完整两轮](conversations/ENV-T41-through-turn-2.md)
3. [ENV-T39 完整两轮](conversations/ENV-T39-through-turn-2.md)
4. [ENV-T38 完整两轮](conversations/ENV-T38-through-turn-2.md)
5. [ENV-T58 完整两轮](conversations/ENV-T58-through-turn-2.md)

每轮独立回复位于 responses/；conversations/ 下每个 through-turn 文件都保留该场景之前的用户及代理原文。后续轮次没有改写前面的答复。

## 实际材料

- inputs/：唯一任务输入 scenarios.json 及其明确引用的完整夹具字节
- traces/<call-id>/input.json：真实调用的精确位置参数、关键字参数与实际 API 签名
- traces/<call-id>/output.json：真实返回对象的类型、公开 preview 和实际读取的 binding_components/private_material；bytes 使用原始 UTF-8、Base64、长度与 SHA-256 三者关联保存，tuple 保留类型标签
- traces/<call-id>/error.json：实际异常类型、原始错误内容与 Python traceback；两次混合 CIDR 导入均在此，无部分候选
- 每次成功候选编译目录的 original.yaml、candidate.yaml、complete.diff：完整原始／未应用候选字节与全上下文差异
- ENV-T41-turn-1-keyword-analysis.json、ENV-T41-turn-2-host-matrix.json：给定 12 个主机的离线字符串匹配；计算代码 calculate_host_matches.py 是透明的本地分析，不冒充已有 Guardian API 或真实路由器
- ENV-T42-turn-3-versus-turn-1.diff：两版未应用候选之间的完整变化；两次编译均从原始扩展开始
- events.jsonl：真实保存／调用事件顺序
- provenance-manifest.json：输入、源文件、输出哈希，实际调用与响应顺序及边界

source_binding.verified_at 统一记为此次离线字节核对日 2026-10-18，并不证明官方来源真实性、新鲜度或版本适用性。场景已提供的来源日期和版本单独保留；没有提供的来源发布日期保持 unknown。用作别名的 synthetic-fixture-v1 不是已观察到的客户端版本。

夹具 ipv6_goal=preserve 保持不变，所有实际语义输出的 IPV4_ONLY_INTENT_CONFLICT 均保留。配置／版本／归属等投影事实仅是合成声明。所有候选未应用，原生验收未运行；没有网络、浏览器、Claude 接触、设备设置、安装、凭据读取或真实清理。

证据记录工具 evidence_tools.py 只负责记录真实调用与将手写逐轮答复装入对话文件，不生成答复模板，也没有期望结果或评分逻辑。仓库源代码和测试未由本响应代理修改。
