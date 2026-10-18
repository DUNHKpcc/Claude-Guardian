已按这一个变化重建：connector 现在开启、同一版本确实使用它，而且你明确选择其完整独立来源走 approved-group。因此更新后的候选有 core、download、connector 三条；旧 bridge 仍不适用。

我重新导入了三份完整来源，再调用 compile_rules_extension。编译输入仍是同一个原始扩展，SHA-256 为 4e3ab056951981e7eba67945ad1a598888f3b68e2fe81aa68a2441e9b4f3ed99；没有把上版未应用候选当作现状，也没有在它上面重复追加。

完整新候选：
```yaml
# synthetic owned rules extension; retain all bytes outside the selected insertion
prepend: ['DOMAIN,api.workflow.invalid,approved-group', 'DOMAIN,downloads.workflow.invalid,approved-group', 'DOMAIN,connector.workflow.invalid,approved-group'] # preserve comment
append: ['DOMAIN,append.example.invalid,Other']
delete: []
unknown-field: {nested: [true, 12, keep-extension]}
```

变化集中在：
- 新纳入 source-connector → rule-connector → DOMAIN,connector.workflow.invalid,approved-group
- connector 的来源日期仍为 2026-10-15、版本范围 fixture-client-v1；原字节哈希为 eeb6e8cdff457bbde759586911dcc3363ae9049e2afcc02774dffc4934460590。功能启用事实更新不意味着来源发布日期也更新
- 对这条新增依赖补做本次离线完整性、规则选择、组名与保护优先级检查；已知与 base 的 MATCH,DIRECT 重叠从 2 处变成 3 处。今后获准的同范围功能／路由验证应包括 connector 的实际路径与参与进程，原先未选择的 connector 检查现在才进入所选范围
- core、download 的来源、选择和规则内容未变；不重问这些已确认事实。bridge、遥测、TLS、设备设置没有跟着改变

三次导入均返回 imported_candidate_only；编译返回 added_rules=3、candidate_only_blocked、apply_supported=false，保护索引仍为 [0,1]。没有应用候选或联系任何端点。已有原生／有效优先级阻塞仍保留；语义输出仍有 IPV4_ONLY_INTENT_CONFLICT，不能用规则候选生成成功推导目标腿 IPv4_ONLY 已生效。

[相对原始快照的完整差异](../traces/ENV-T42-turn-3-compile/complete.diff)、[相对上版候选的变化](../ENV-T42-turn-3-versus-turn-1.diff)、[完整候选](../traces/ENV-T42-turn-3-compile/candidate.yaml)、[精确编译输入](../traces/ENV-T42-turn-3-compile/input.json)、[完整返回](../traces/ENV-T42-turn-3-compile/output.json)、[更新的选择记录](../ENV-T42-turn-3-selection.json)。
