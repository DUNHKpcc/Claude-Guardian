不把 /21 加入客户端默认规则：包含关系不改变它在这份历史资料里属于 service_to_external 的用途。选择更大网段会扩大命中范围，却没有补上当前 client_to_service 来源证据或第三方依赖覆盖。

独立的单域名事项已经继续做了。你这轮明确选择的是完整独立来源 env-t39-supported-source.txt，我将它整份导入；它不是从上轮任一失败混合片段中截取的部分结果。

实际调用参数为：
- import_rule_bindings：完整原字节 api.workflow.invalid 加结尾换行，format_id=exact-domain-lines/0.1，ordered_rule_refs=[rule-core]，action_intent={kind: user_selected_egress, group_name: approved-group}
- source_ref=source-api-exact，expected_sha256=d59f172c6e22bdf3b4f088db7c9f0db7a8c3f7d58b4e8a3def1d2b8392b44a84。该文件发布日期未给出；2026-10-18 仅为离线字节核对日期，不冒充官方来源核验日期
- compile_rules_extension：keep-existing 请求，原始 owned-rules-extension.yaml 与 effective-base.yaml，placement=prepend，rule_order=[rule-core]，group_name=approved-group，protected_rule_indexes=[0,1]

完整未应用候选：
```yaml
# synthetic owned rules extension; retain all bytes outside the selected insertion
prepend: ['DOMAIN,api.workflow.invalid,approved-group'] # preserve comment
append: ['DOMAIN,append.example.invalid,Other']
delete: []
unknown-field: {nested: [true, 12, keep-extension]}
```

导入返回 imported_candidate_only；编译返回 added_rules=1、candidate_only_blocked、apply_supported=false。仅在原始空 prepend 内插入一条精确规则，原 base、append、delete 和所有无关字节保留。唯一已知 base 重叠是末尾 MATCH,DIRECT，所选主机在声明顺序下优先走新规则；组织和救援索引未冲突。

没有生成任何 CIDR 规则，也没有应用配置或做网络查询。真实版本能力、归属／完整保护覆盖、有效优先级及原生验收依然未核实；原始语义夹具的 ipv6_goal=preserve 未被改写，输出中的 IPV4_ONLY_INTENT_CONFLICT 与合规 not_established 原样保留。

[完整候选字节](../traces/ENV-T39-turn-2-compile/candidate.yaml)、[完整差异](../traces/ENV-T39-turn-2-compile/complete.diff)、[导入精确输入](../traces/ENV-T39-turn-2-import-exact/input.json)及[导入返回](../traces/ENV-T39-turn-2-import-exact/output.json)、[编译精确输入](../traces/ENV-T39-turn-2-compile/input.json)及[编译返回](../traces/ENV-T39-turn-2-compile/output.json)。
