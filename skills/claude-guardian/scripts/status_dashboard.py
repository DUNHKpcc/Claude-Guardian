#!/usr/bin/env python3
"""Offline, allowlisted HTML projection of diagnostic snapshots. No collectors."""
import argparse
from datetime import datetime, timezone
from html import escape
import json
import sys

from guardian import GuardianError, load_json, save_new

STATES = {
    "verified": ("已验证", "仅用于有对应范围验收证据的检查；本预览不生成此结论"),
    "error": ("发现问题", "报告存在错误、冲突或执行失败"),
    "unknown": ("未知", "证据不足、缺失或已过期"),
    "not_run": ("未执行", "当前报告格式没有此项实际检测证据"),
    "authorization_needed": ("待授权", "先核实目标与操作范围，再取得本次授权"),
}
GROUPS = (("system", "系统与目标", "ENV-01", "S"),
          ("proxy", "代理配置 / 入口", "ENV-02", "P"),
          ("tun", "TUN 声明与接管", "ENV-02", "P"),
          ("ipv4", "IPv4 请求出口", "ENV-03", None),
          ("ipv6", "IPv6 分层覆盖", "ENV-04", None),
          ("dns", "DNS 配置与解析路径", "ENV-04", None),
          ("dns_leak", "DNS 泄露证据", "ENV-04", None),
          ("udp", "UDP 可达与业务范围", "ENV-04", None),
          ("stun", "独立 STUN 映射", "ENV-04", None),
          ("browser", "浏览器 / WebRTC", "ENV-05", None),
          ("failure", "代理失效 / 防直连", "ENV-10", None))
COVERAGE = {
    "system": ("§19", "目标设备、用户、命名空间；系统信息不证明目标绑定"),
    "proxy": ("§19 / §20.1–3", "系统代理、显式 HTTP/mixed 入口、浏览器路径须分别核实；端口声明不证明可用"),
    "tun": ("§20.4.4 / §20.6", "TUN 开关、IPv4/IPv6 路由、DNS 与 UDP 接管分别核实；开启不等于覆盖"),
    "ipv4": ("§20.3 / §20.5", "需区分系统继承、显式代理、TUN 与浏览器的 HTTPS IPv4 样本；出口/地区标签不证明平台许可"),
    "ipv6": ("§20.5", "分别记录本机接口、节点外层通道、代理到目标、浏览器 ICE；AAAA 为空或超时不证明阻断"),
    "dns": ("§20.4", "系统、浏览器 DoH、Mihomo、引导解析与实际解析器连接分别核实；Fake-IP 差异不自动判错"),
    "dns_leak": ("§20.4.1–4", "解析器设置不等于泄露证据；需关联批准的查询、解析目标与实际连接。不同解析器或地区不自动判泄露"),
    "udp": ("§20.6", "区分应用 UDP 与代理隧道外层 UDP；单次 STUN 不证明所有目的地、端口或协议覆盖"),
    "stun": ("§20.6.1–2", "独立 Binding 事务的地址族、映射分类、路径与时间须有证据；不展示映射 IP，不代替浏览器样本"),
    "browser": ("§20.7", "所选浏览器/Profile 的政策、HTTPS 路径、ICE host/srflx/relay 与 IPv6 分别核实；无候选不证明无泄露"),
    "failure": ("§18 / §20.5 / ENV-10", "代理失效后的行为、程序/子进程范围与恢复需单独验收；超时或配置声明不证明防直连"),
}
FACT_IDS = {"S%02d" % n for n in range(1, 17)} | {"P%02d" % n for n in range(1, 25)}
ERROR_CODES = frozenset({"PROXY_PORT_ASSOCIATION_CONFLICT", "COLLECTOR_INTERNAL_FAILURE",
    "INPUT_OR_RESPONSE_INVALID", "TARGET_USER_CONTEXT_MISMATCH", "SNAPSHOT_CHANGED_DURING_AUDIT",
    "OS_QUERY_FAILED", "BUDGET_EXCEEDED", "CONTROLLER_AUTH_FAILED"})
AUTH_CODES = frozenset({"AUTHORIZATION_MISSING", "PERMISSION_DENIED", "PRECONTACT_ACTION_REJECTED"})
CSS = """
:root{color-scheme:light;--ink:#17283b;--muted:#516173;--line:#d8e1ea;--paper:#fff;--bg:#f2f5f8}
*{box-sizing:border-box}body{margin:0;background:var(--bg);color:var(--ink);font:16px/1.6 system-ui,-apple-system,sans-serif}
main{max-width:1120px;margin:auto;padding:32px 24px}header{padding:12px 0 26px}.eyebrow{font-size:12px;letter-spacing:.16em;font-weight:700;color:#39617a}
h1{font-size:clamp(28px,5vw,42px);line-height:1.2;margin:12px 0}h2{font-size:20px;margin:0 0 12px}h3{font-size:18px;margin:14px 0 8px}
p{margin:8px 0}.muted,small{color:var(--muted)}.notice{border-left:4px solid #b56b12;background:#fff6e7;padding:16px 20px;margin-bottom:24px}
.grid{display:grid;grid-template-columns:repeat(3,minmax(0,1fr));gap:16px}.card,section.panel{background:var(--paper);border:1px solid var(--line);border-radius:14px;padding:22px}
.card small{font-size:12px}.badge{display:inline-block;padding:3px 10px;border-radius:6px;font-size:13px;font-weight:700;background:#e9edf2;color:#34465a}
.badge.error{background:#ffe8e5;color:#9c291e}.badge.authorization_needed{background:#fff0d2;color:#815000}.badge.verified{background:#e3f2ed;color:#235e4b}
.panel{margin-top:22px}.meta{display:flex;gap:12px 32px;flex-wrap:wrap;font-size:14px}.legend{display:grid;grid-template-columns:repeat(2,minmax(0,1fr));gap:14px}
li{margin:8px 0}footer{font-size:13px;margin:24px 0;color:var(--muted)}@media(max-width:760px){.grid{grid-template-columns:1fr 1fr}.legend{grid-template-columns:1fr}}@media(max-width:480px){main{padding:22px 14px}.grid{grid-template-columns:1fr}}@media print{body{background:white}main{padding:0}.card,.panel{break-inside:avoid}}
"""


def timestamp(value):
    """Never echo unparsed input, including malformed timestamps or timezone labels."""
    if not isinstance(value, str) or len(value) > 40:
        return None
    try:
        result = datetime.fromisoformat(value.replace("Z", "+00:00"))
        return result.astimezone(timezone.utc) if result.tzinfo else None
    except (ValueError, OverflowError):
        return None


def fresh(value, now):
    parsed = timestamp(value)
    return parsed is not None and 0 <= (now - parsed).total_seconds() <= 86400


def safe_facts(facts):
    """Finite values and true JSON booleans only; never interpolate raw values."""
    details = []
    for fact in facts:
        field, value = fact.get("id"), fact.get("value")
        if field == "S01" and isinstance(value, str) and value in {"macos", "windows"}:
            details.append("系统：" + {"macos": "macOS", "windows": "Windows"}[value])
        elif field == "S04" and isinstance(value, str) and value in {"arm64", "aarch64", "x86_64", "amd64", "x64", "x86"}:
            details.append("架构：" + value)
        elif field == "P06" and isinstance(value, dict) and type(value.get("enabled")) is bool:
            details.append("系统代理声明：" + ("开启" if value["enabled"] else "关闭") + "（不代表实际路径）")
        elif field == "P12" and type(value) is bool:
            details.append("TUN 声明：" + ("开启" if value else "关闭") + "（不代表接管已验证）")
        elif field == "P11" and isinstance(value, str) and value in {"rule", "global", "direct"}:
            details.append("代理模式声明：" + value)
    return list(dict.fromkeys(details))


def project(report, now=None):
    """Project only enums/counts/dates. No arbitrary text, values or identifiers survive."""
    now = now or datetime.now(timezone.utc)
    if not isinstance(report, dict) or report.get("schema_version") not in ("guardian-report/0.1", "env-inventory/0.2"):
        raise GuardianError("DASHBOARD_REPORT_UNSUPPORTED")
    facts, findings = report.get("facts", []), report.get("findings", [])
    if not isinstance(facts, list) or not isinstance(findings, list) or len(facts) > 1000 or len(findings) > 1000:
        raise GuardianError("DASHBOARD_REPORT_INVALID")
    if any(not isinstance(x, dict) for x in facts + findings):
        raise GuardianError("DASHBOARD_REPORT_INVALID")
    ids = [fact.get("id") for fact in facts]
    if any(not isinstance(field, str) for field in ids) or len(set(ids)) != len(ids):
        raise GuardianError("DASHBOARD_REPORT_INVALID")
    snapshot = report.get("snapshot", {})
    if not isinstance(snapshot, dict):
        raise GuardianError("DASHBOARD_REPORT_INVALID")
    observed = timestamp(snapshot.get("observed_at"))
    snapshot_fresh = fresh(snapshot.get("observed_at"), now)
    cards = []
    for key, title, module, prefix in GROUPS:
        selected = [f for f in facts if isinstance(f.get("id"), str) and
                    prefix is not None and f["id"] in FACT_IDS and f["id"].startswith(prefix)]
        if key == "tun":
            selected = [f for f in selected if f.get("id") == "P12"]
        current = sum(f.get("state") == "observed" and fresh(f.get("observed_at"), now) for f in selected)
        module_findings = [f for f in findings if f.get("module_id") == module]
        codes = [f.get("code") for f in module_findings if isinstance(f.get("code"), str)]
        if key == "tun":
            codes = []  # Proxy port findings do not establish TUN failure.
        state = "unknown" if prefix else "not_run"
        if any(c in ERROR_CODES for c in codes) or any(f.get("state") == "conflict" for f in selected):
            state = "error"
        elif any(c in AUTH_CODES for c in codes) or any(f.get("state") == "blocked" for f in selected):
            state = "authorization_needed"
        # This schema has no scoped live probe or acceptance contract. Never infer verified.
        cards.append({"key": key, "title": title, "module": module, "state": state,
                      "observed": current if snapshot_fresh else 0, "total": len(selected),
                      "evidence_at": min((timestamp(f.get("observed_at")) for f in selected if f.get("state") == "observed" and fresh(f.get("observed_at"), now)), default=None) if snapshot_fresh else None,
                      "details": safe_facts([f for f in selected if snapshot_fresh and f.get("state") == "observed" and fresh(f.get("observed_at"), now)])})
    execution = report.get("execution_status")
    execution_text = {"completed": "报告生成完成（不代表环境通过）", "failed": "报告执行失败",
                      "blocked": "报告执行受阻", "interrupted": "报告执行中断"}.get(execution if isinstance(execution, str) else "", "执行状态未知")
    return {"cards": cards, "observed_at": observed.isoformat() if observed else "未知",
            "generated_at": now.isoformat(), "snapshot_fresh": snapshot_fresh,
            "synthetic": report.get("record_kind") == "synthetic_example", "execution": execution_text,
            "overall": "error" if execution == "failed" or any(c["state"] == "error" for c in cards) else "unknown"}


def badge(state):
    return '<span class="badge %s">%s · %s</span>' % (escape(state, quote=True), escape(STATES[state][0]), escape(state))


def render(report, now=None):
    view = project(report, now)
    cards = []
    for card in view["cards"]:
        detail = ("当前时间范围内的已观察字段：%d / %d。仅展示白名单事实；采集不等于运行有效。" %
                  (card["observed"], card["total"])) if card["key"] in {"system", "proxy", "tun"} else "当前报告不包含可验收的实时路径证据；不会因报告完成而变绿。"
        section, limitation = COVERAGE[card["key"]]
        evidence_at = card["evidence_at"].isoformat() if card["evidence_at"] else "未知 / 未执行"
        detail += " 证据最早时间（UTC）：" + evidence_at + "。路径：未知 / 未独立绑定。"
        details = "".join("<li>" + escape(item) + "</li>" for item in card["details"])
        cards.append('<article class="card"><small>%s</small><h3>%s</h3>%s<p>%s</p><ul>%s</ul><p class="muted">%s</p><small>设计依据：D-ENV-v0.3 %s</small></article>' %
                     (escape(card["module"]), escape(card["title"]), badge(card["state"]), escape(detail), details, escape(limitation), escape(section)))
    cards.append('<article class="card"><small>PC0 · 操作权限</small><h3>下一步操作</h3>%s<p>此快照不授予任何操作权限。联网探测、配置修改与接触 Claude 均须单独核实并授权。</p></article>' % badge("authorization_needed"))
    legend = ''.join('<div>%s<p class="muted">%s</p></div>' % (badge(s), escape(d)) for s, (_, d) in STATES.items())
    sample = "合成演示 · 不是你的设备检测结果" if view["synthetic"] else "离线报告快照 · 未独立核验来源或目标"
    freshness = "快照时间在 24 小时内；仍不保证当前设置未变化" if view["snapshot_fresh"] else "快照过期、时间缺失或来自未来；请重新获取获准的目标证据"
    return '''<!doctype html>
<html lang="zh-CN"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1">
<meta http-equiv="Content-Security-Policy" content="default-src 'none'; style-src 'unsafe-inline'; base-uri 'none'; form-action 'none'">
<meta name="referrer" content="no-referrer"><title>Claude-Guardian · 环境状态</title><style>''' + CSS + '''</style></head><body><main>
<header><div class="eyebrow">CLAUDE-GUARDIAN / LOCAL STATUS</div><h1>环境状态，一眼看清</h1><p class="muted">系统、代理与网络检查的证据和缺口，保留各自边界。</p></header>
<div class="notice"><strong>''' + escape(sample) + '''</strong><p>这是静态页面，不会自动检查、联网、启动应用或修改设置。环境就绪尚未验证；不提供账号安全保证。</p></div>
<section aria-labelledby="overview"><h2 id="overview">检查概览 · ''' + badge(view["overall"]) + '''</h2><div class="grid">''' + ''.join(cards) + '''</div></section>
<section class="panel"><h2>证据与时间</h2><div class="meta"><span>报告时间（UTC）：''' + escape(view["observed_at"]) + '''</span><span>页面生成（UTC）：''' + escape(view["generated_at"]) + '''</span></div><p>''' + escape(view["execution"]) + '''</p><p>''' + escape(freshness) + '''</p><p class="muted">时间来自报告与生成主机，时钟未外部校验。重新打开同一 HTML 不会刷新状态；请重新生成。来源、设备、用户和命名空间须由宿主独立确认；本页不是完整诊断报告。</p></section>
<section class="panel"><h2>建议下一步</h2><ol><li>确认报告属于本次目标设备、用户及执行环境；过期或目标变化时重新采集</li><li>优先查看原始本地报告中的错误与缺失项；本页仅展示白名单摘要</li><li>需要出口、DNS 或浏览器检查时，先列出端点、数据披露与范围，再申请本次授权</li><li>需要修改配置时，先审阅精确差异、备份与恢复方案；此页面没有执行入口</li></ol></section>
<section class="panel"><h2>状态怎么读</h2><div class="legend">''' + legend + '''</div></section>
<footer>本地文件 · 无脚本 / 无外部资源 / 无自动刷新 · 分享前仍请人工复核摘要。支持报告：guardian-report/0.1 · env-inventory/0.2</footer>
</main></body></html>\n'''


def main(argv=None):
    parser = argparse.ArgumentParser(description="Generate a private offline HTML status snapshot; no probes or auto-open.")
    parser.add_argument("--input", required=True, help="Explicit local guardian-report/0.1 or env-inventory/0.2 JSON file")
    parser.add_argument("--output", required=True, help="New local HTML file; never overwrite")
    args = parser.parse_args(argv)
    try:
        save_new(args.output, render(load_json(args.input)))
    except KeyboardInterrupt:
        sys.stderr.write("DASHBOARD_CANCELLED\n")
        return 3
    except GuardianError as error:
        sys.stderr.write(error.code + "\n")
        return error.exit_code
    except Exception:
        sys.stderr.write("DASHBOARD_INTERNAL_FAILURE\n")
        return 4
    sys.stdout.write("DASHBOARD_SAVED: open the requested local HTML file manually; generation is not environment verification.\n")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
