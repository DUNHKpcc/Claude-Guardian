换成宽 DOMAIN-SUFFIX 仍会跨业务，不能作为绕过范围问题的办法。比如 sentry.invalid 后缀同时覆盖根域、guardian、other 和 corp；前置后会影响 SharedTelemetry 和组织 Corp 策略。datadoghq.com、sift.invalid 的宽后缀也会覆盖已有 Work、Payments 的根域及子域。它们只排除了部分关键词误命中，并没有解决业务隔离。

边界也要分清：unrelated-sentry.example.invalid 不在 sentry.invalid 后缀内；browser-intake-us5-datadoghq.com 不在 datadoghq.com 的标签边界子域内。不能为了“一张网全收”忽略这些差别。

本次保留你当前开启的遥测，不把关遥测混入这项规则修复。若你要另改某个应用的可选遥测，需要先明确具体开关、版本和影响；目前附件没有这个开关的可核实配置。

你明确选择的窄需求已继续完成离线候选：完整导入 env-t41-exact-source.txt 的唯一主机，再从原始扩展快照编译。完整候选为：
```yaml
# synthetic owned rules extension; retain all bytes outside the selected insertion
prepend: ['DOMAIN,guardian.ingest.sentry.invalid,approved-group'] # preserve comment
append: ['DOMAIN,append.example.invalid,Other']
delete: []
unknown-field: {nested: [true, 12, keep-extension]}
```

导入参数使用 exact-domain-lines/0.1、rule-guardian-ingest、明确的 user_selected_egress / approved-group。来源实际哈希为 117c6b6c3af5232ea592db25e305cdbe1b1cb5cd76cff7a9e463e457692eb0ae；来源发布日期未提供，保持 unknown。shared_service=true 仅记录本合成案例的跨业务分类，不能证明真实供应商归属。编译使用 keep-existing、prepend、protected_rule_indexes=[0,1]，实际返回 added_rules=1、known_base_overlap_count=2、candidate_only_blocked。

按附件顺序做的前后第一命中对照：
- guardian.ingest.sentry.invalid：DOMAIN-SUFFIX,sentry.invalid 的 SharedTelemetry → 新精确 DOMAIN 的 approved-group
- other.ingest.sentry.invalid、sentry.invalid：仍由原 sentry.invalid 后缀命中 SharedTelemetry
- corp.sentry.invalid：仍由原精确 DOMAIN 命中 Corp
- unrelated-sentry.example.invalid：仍由 example.invalid 后缀命中 General
- datadoghq.com、sub.datadoghq.com：仍由 datadoghq.com 后缀命中 Work
- browser-intake-us5-datadoghq.com：仍由 MATCH 命中 DIRECT
- sift.invalid、shop.sift.invalid：仍由 sift.invalid 后缀命中 Payments
- rescue.example.invalid：仍由原精确 DOMAIN 命中 DIRECT
- work.example.invalid：仍由 example.invalid 后缀命中 General

因此这份附件上的改变仅为选定精确主机；组织和救援项的命中规则／动作均未改变，其他已有宽规则也没有被删改。编译器记录的两处已知重叠是所选主机对应的 SharedTelemetry 后缀和末尾 MATCH，不是保护项冲突。

这份对照只证明给定合成字符串与已声明合并顺序，不代表运行时路由。保护索引覆盖仍是调用方声明，真实完整覆盖、后续合并、版本与原生验收保持未核实，apply_supported=false；IPv4_ONLY_INTENT_CONFLICT 也原样保留，未借此修改网络策略。

[完整 12 主机前后对照](../ENV-T41-turn-2-host-matrix.json)、[完整候选](../traces/ENV-T41-turn-2-compile/candidate.yaml)、[完整差异](../traces/ENV-T41-turn-2-compile/complete.diff)、[精确编译输入](../traces/ENV-T41-turn-2-compile/input.json)、[完整返回](../traces/ENV-T41-turn-2-compile/output.json)、[实际导入输入](../traces/ENV-T41-turn-2-import-exact/input.json)。候选未应用。
