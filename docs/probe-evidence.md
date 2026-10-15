# 离线探测证据投影：Mihomo DNS 增量

对应 ENV-04A / D-ENV-v0.3 §20.4.2，延续
[环境状态面板](environment-dashboard.md) 的 `--probes` 离线附件。
这一步只将已有 `guardian-mihomo-dns-probe/0.1` 结果接入 DNS 配置 / 查询行。
不调用控制器、不解析域名、不读取系统、不产生运行授权。

## 附件中的单条样本

```json
{
  "schema_version": "guardian-probe-evidence/0.1",
  "target_ref": "local-target-alias",
  "samples": [
    {
      "expected_path_kind": "mihomo_dns_query",
      "context": {
        "target_ref": "local-target-alias",
        "path_kind": "mihomo_dns_query"
      },
      "captured_at": "2026-10-15T12:00:00+00:00",
      "result": {"schema_version": "...replace with complete Mihomo result..."}
    }
  ]
}
```

`result` 是结构占位，须换成现有探测器的完整返回字典，不是可执行查询请求。
整个附件最多 64 条；沿用输入文件大小限制和重复 JSON 键拒绝。

Mihomo 的公开结果有意不包含设备、用户、命名空间或控制器绑定标识。
`context` 是宿主保存附件时可附加的声明，不是可从结果中恢复的真实身份。
目标别名只与附件的 `target_ref` 作一致性比较，路径只与固定类别和
`expected_path_kind` 比较；未与主盘点报告、当前设备或控制器做独立绑定。
缺少上下文显示未知；不匹配单独显示。JSON 布尔、来源字段、question_matches
或 gate_state 均不能建立可信宿主来源、操作授权或就绪通过。

成功返回读取 fact 的 `observed_at`，失败无 fact 时可读取附件的 `captured_at`。
两者都是未核验的时间声明；渲染时间从不填补缺失的采集时间。
缺失、未来、非法、超过 24 小时的时间保持相应缺口；取消/失败可同时显示时间无效或过期。

## 展示与严格边界

- 只显示 A/AAAA、地址族、rcode（0—4095）、截断标志、答案/地址/CNAME 数量、全局单播/非全局地址分类计数
- 计数必须是 0—256 的整数，布尔不算整数；分类数量与地址数量、答案分项必须一致
- completed 仅称“已记录响应声明”；rcode 非零和截断回复仍完整保留，不称 DNS 成功
- 失败报告不得夹带响应 facts；取消、超时、授权/权限缺口、绑定/响应上下文不匹配、其他失败均单独显示，不用普通未知吞掉
- 缺少/非法格式或自相矛盾的报告拒绝生成；不回显任意错误文本
- 多个样本保持原顺序，包括成功、负响应、取消和过期记录，不用最后一条覆盖旧记录
- 既有报告错误或授权缺口及其说明继续保留；样本响应不能掩盖它们
- 缓存/hosts 来源、Fake-IP、上游链路与真实请求均未核验，地址分类不能推断可达性、污染或泄露
- DNS 泄露、浏览器、IPv4/IPv6 HTTPS、STUN、一般 UDP、TUN 和失效保护均不取得新的检测证据
- 不显示域名、IP、端口、设备/用户/实例别名、响应自由文本、凭据或调用指令

主表仍为原来的三列。响应细节在 DNS 行折叠证据内；行验证状态不因样本而通过。
本接口不构造 workflow_guard.Evidence、不打开接触门禁，也不触发后续操作。

## 回归与限制

```sh
python -m unittest discover -s tests -p test_mihomo_dashboard.py -v
python -m unittest discover -s tests -p test_probe_evidence.py -v
python -m unittest discover -s tests -p test_status_dashboard.py -v
```

Mihomo 兼容性测试调用实际探测函数并注入字节响应；禁止 socket、系统 DNS、
subprocess 与渲染期间的 probe 调用。覆盖两族、负响应/截断、失败无事实、上下文、
非法计数、时间、混合样本和秘密哨兵。没有实际控制器、公网 DNS、真实设备或浏览器渲染验收。
回滚本次投影分支、状态标签和新增测试/文档即可；没有持久配置或运行状态变更。
