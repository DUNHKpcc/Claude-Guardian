"""Offline adaptive interview; no network, subprocess, file writes or implicit consent.

Public API: new_state, record_fact, record_facts, set_context, next_question, assessment,
mark_asked, defer_branch, resume_branch, complete_purchase, dumps_state,
loads_state, validate_state. All updates return copies. Persisting returned JSON
is exclusively the host's responsibility and requires explicit opt-in per scope.

Example::
    s = new_state("laptop-a", "claude-a")
    s = record_fact(s, "Q-J01", "first_subscription", source="user:turn-1")
    s = record_fact(s, "Q-C02", "windows", source="user:turn-1")
    question = next_question(s)  # one relevant question, never a whole form
    s = mark_asked(s, question["id"])

Values are sanitized categorical facts, never passwords, card numbers, gift-card
codes or authentication material. The host translates prompts and performs domain
reasoning using references/intake.md. An answer is never an action authorization.
G3 is deliberately always closed here: use the separate action/contact gates.
"""
from copy import deepcopy
from datetime import datetime, timezone
import json
import re

SCHEMA_VERSION = "1.0.0"
FACT_STATES = frozenset({"unasked", "reported", "observed", "inferred", "unknown",
                         "declined", "conflict", "stale", "not_applicable", "deferred"})
JOURNEYS = frozenset({"first_subscription", "returning_subscription", "existing_subscriber", "unknown"})
ALIASES = {"Q-OS01": "Q-C02", "Q-L05": "Q-N06", "Q-Z02": "Q-C12", "Q-G05": "Q-P07"}
RETIRED = "Q-C07"

QUESTION_PROMPTS = {'Q-J01': '这次是第一次准备订阅（包括只用过免费版）、以前订阅过目前无有效订阅准备重订、当前已有订阅，还是不确定？',
 'Q-J02': '你说用过/是老手：现在还有有效订阅，还是准备开通/重新开通？',
 'Q-C01': '主要用网页/Desktop 聊天，还是 Claude Code 编程？这次具体想完成什么？',
 'Q-C02': '这次用 Mac 还是 Windows？',
 'Q-C03': '以前 Claude 账号被明确停用/封禁过吗，还是只遇到报错？',
 'Q-C04': '准备用的 Claude 账号注册了吗？已有账号现在能正常登录吗？',
 'Q-C05': '用本机、虚拟机、VPS，还是先比较？本机默认建议。',
 'Q-C06': '已有账号通过什么方式登录/接入？不懂名称可描述界面。',
 'Q-C08': '你这次想订阅什么套餐？ 选好了直接说；未决定先按用途和预算比较。',
 'Q-C09': '实际在哪个国家/地区使用？是否有跨地区安排？无需详细地址。',
 'Q-C10': '希望逐步指导，还是直接给检查项和命令？',
 'Q-C11': '老用户这次主要是续费/升级、调整使用方案，还是检查环境/解决问题？',
 'Q-C12': '哪些已有项目、历史、客户端或配置不能动？',
 'Q-OS01': '本机是 Mac 还是 Windows？',
 'Q-OS02': '如果 Windows：是 Windows 10/11？具体 Edition（Home、Home Single Language、Pro……）是什么？',
 'Q-OS03': '如果 Mac：macOS 大致版本是什么？',
 'Q-OS04': '如果想更改语言：你指的是 Windows 显示语言，还是键盘输入、地区格式、浏览器或单个 App？',
 'Q-OS05': '如果 Windows 无法改显示语言：是否看到“许可证仅支持一种显示语言”等原文？',
 'Q-OS06': '如果无法改时区：是手动下拉灰色、自动设置开关灰色、报错，还是改完自动恢复？',
 'Q-OS07': '如果时区故障：“自动设置时区”开启吗？电脑是个人管理还是公司/学校管理？',
 'Q-OS08': '如果时间显示异常：实际时间是否准确，还是仅时区偏移/名称不对？',
 'Q-OS09': '是否确有需要修改 Windows/macOS 的语言/时区，还是只想检查能否正常使用 Claude？',
 'Q-OS10': 'Windows 10 是否有合适的安全更新安排（ESU/迁移/组织维护）？',
 'Q-OS11': '如果涉及 macOS 的语言/时间：需要系统级还是单个 App 的变化？',
 'Q-OS12': '当前 OS 选项不在 Mac/Windows 内，本次想了解共用规则还是要选 VM/VPS？',
 'Q-H01': '被限制的是 Claude 账号，还是 Apple/Google 商店账号、支付卡或某个客户端？',
 'Q-H02': '最近一次与本次任务有关的事件，大约何时发生？目前恢复了吗？',
 'Q-H03': '当时显示什么错误/通知？有可脱敏的原文或局部截图吗？',
 'Q-H04': '出现问题前正在注册、登录、订阅、更新客户端还是执行任务？',
 'Q-H05': '当时在什么设备/环境、通过什么客户端和计费渠道使用？',
 'Q-H06': '是否正在申诉、身份核验或处理退款？有没有官方回复要求你完成的事项？',
 'Q-H07': '之后做过哪些退出、重装、清理或配置修改？有需要保留/导出的数据吗？',
 'Q-H08': '本次是否沿用当时的设备/网络/付款工具？哪些变了？',
 'Q-N01': '当前是普通网络直接连接，还是使用代理/VPN/公司网络？软件名称知道就说。',
 'Q-N02': '浏览器、Code、代理分别运行在哪里？使用系统代理、应用代理、TUN 还是不确定？',
 'Q-N03': '网络是否常切换、自动换节点或跨地区？有计划长期固定使用的环境吗？',
 'Q-N04': '还有手机、其他电脑或远程工作区同时/交替使用吗？各自用来做什么？',
 'Q-N05': '已做过哪些网络测试？何时、在哪个设备、用哪个程序测的？',
 'Q-N06': '是否受公司网络、证书、安全软件、代理策略或设备管理限制？',
 'Q-P01': '你提到的购买对象是 Claude 订阅还是 API/其他服务？',
 'Q-P02': '这次相关的原套餐/旧购买渠道及待处理订单是什么？',
 'Q-P03': '可用于付款的设备有 iPhone/iPad、Android，还是只有电脑？',
 'Q-P04': '已有可用的商店账户/余额、银行卡、企业付款方式，还是尚未准备？',
 'Q-P05': '月费和一次性准备费用能接受什么范围？',
 'Q-P06': '更倾向哪种可行付款方式？需要先比较步骤吗？',
 'Q-P07': '后续准备怎样续费？需要说明账单查看与取消入口吗？',
 'Q-A01': 'A1 设备',
 'Q-A02': 'A2 Apple 账户',
 'Q-A03': 'A3 商店地区',
 'Q-A04': 'A4 App 与内购',
 'Q-A05': 'A5 服务账户对应',
 'Q-A06': 'A6 老用户旧订单（条件题）',
 'Q-A07': 'A7 礼品卡',
 'Q-A08': 'A8 结账条件',
 'Q-A09': 'A9 来源',
 'Q-A10': 'A10 后续续费与改区影响',
 'Q-G01': '有可用 Android 设备，并能使用官方 Google Play 与 Claude App 吗？',
 'Q-G02': '有能正常登录验证的 Google 账户吗？Play 国家/地区和付款选项是什么？',
 'Q-G03': '当前购买页能看到目标套餐和可用付款选项吗？',
 'Q-G04': '手机 App 登录的 Claude 是否为这次准备使用的目标账户？',
 'Q-G05': '后续怎样续费，是否需要说明账单与取消入口？',
 'Q-W01': '准备使用的是信用卡/借记卡/企业卡？发行国家或地区是什么？',
 'Q-W02': '结账要求的账单资料能否如实填写？',
 'Q-W03': '是否支持所需的线上/周期付款，出现过拒付或验证提示吗？',
 'Q-W04': '当前结账总额、计费周期和后续续费安排是否符合本次选择？',
 'Q-I01': 'API/服务由哪一平台、哪一个组织或项目计费？',
 'Q-I02': '你是否有该项目的使用与付款权限？',
 'Q-I03': '本次是个人开发还是面向其他用户的服务？预计如何调用？',
 'Q-I04': '预算、费用上限和告警应如何设置？',
 'Q-E01': '是否确有企业结算需求和可用企业主体，而非单纯个人订阅？',
 'Q-E02': '由谁负责企业审核、付款和后续维护？',
 'Q-L01': '目标客户端安装了吗？用哪种方式安装、版本是什么？',
 'Q-L02': '系统/架构是否满足当前客户端要求？',
 'Q-L03': '当前有 MCP、插件、hooks、代理网关或其他开发工具吗？',
 'Q-L04': 'Claude 是否需要读取本机项目、调用本机软件或操作图形界面？',
 'Q-L05': '设备归个人还是组织管理？哪些权限和变更可接受？',
 'Q-V01': '已有虚拟机还是准备新建？使用什么虚拟化软件？',
 'Q-V02': '宿主与客机各是什么系统/架构？',
 'Q-V03': '可供 VM 使用的内存/磁盘大约多少？已有项目需要保留吗？',
 'Q-V04': '虚拟机怎样联网，代理在宿主还是客机？',
 'Q-V05': '需要共享哪些目录、剪贴板或工具？是否已有账号凭据挂载？',
 'Q-V06': '有没有快照/备份和可用的恢复方式？',
 'Q-S01': 'VPS 是 Claude 工作区，还是仅提供代理出口？',
 'Q-S02': '已有 VPS 还是新建？地区、系统和大致资源是什么？',
 'Q-S03': '是否能正常 SSH？有没有独立的控制台/救援入口？',
 'Q-S04': '上面有生产服务、数据库或未备份项目吗？',
 'Q-S05': '项目和数据能否存到远端？需依赖哪些本机应用或硬件？',
 'Q-S06': '服务器月费、流量和维护成本能接受多少？',
 'Q-S07': '希望终端、Remote-SSH 还是远程浏览器？如何备份和维护？',
 'Q-Z01': '这次只要讲解/计划，还是允许指定范围的只读检查？',
 'Q-Z02': '具体有哪些项目、历史、CLI、配置和其他服务必须保留？',
 'Q-Z03': '允许哪些具体变更，是否需要组织管理员处理？',
 'Q-Z04': '有没有备份、回滚或独立救援条件？',
 'Q-Z05': '是否保存/导出不含秘密的本次进度，还是仅留在当前对话？',
 'Q-C07': 'retired；从展示集、调度、画像必填和就绪要求中删除，不复用编号'}
QUESTION_PROMPTS[RETIRED] = "Retired; never collect account ownership"

# Context is routing metadata supplied explicitly by the host, never inferred
# from expertise, equipment ownership, IP geolocation or a default proposal.
CONTEXT_DEFAULTS = {
    "task": "subscription_preparation", "incident": "none", "incident_resolved": False,
    "incident_origin": "host", "account_incident_resolved": False,
    "ambiguous_experience": False, "subscription_conflict": False,
    "billing_channel": "unselected", "route": "local",
    "route_selection_basis": "default_proposal", "contact_phase": "PC0",
    "os_issue": "none", "language_change_needed": False,
    "timezone_issue": False, "windows10": False, "compatibility_needed": False,
    "budget_needed": False, "gift_card": False, "buying_gift_card": False,
    "changing_store_region": False, "organization_task": False,
    "billing_product_ambiguous": False, "existing_test": False,
    "integration_used": False, "change_planned": False,
    "persistence_requested": False, "purchase_completed": False,
    "paused": False, "blocked_reason": None,
}
# Optional additive fields preserve the published schema-1 input contract.
INCIDENT_CONTEXT_FIELDS = {"incident_origin", "account_incident_resolved"}
ENUM_CONTEXT = {
    "task": {"subscription_preparation", "renew", "upgrade", "change_channel", "billing_issue",
             "environment", "network", "incident", "api", "enterprise", "compare"},
    "incident": {"none", "credential_exposure", "data_risk", "suspension", "identity_review",
                 "duplicate_charge", "unknown_error"},
    "incident_origin": {"host", "legacy_unverified"},
    "billing_channel": {"unselected", "apple", "google", "web", "api", "enterprise", "compare"},
    "route": {"local", "vm", "vps", "compare"},
    "route_selection_basis": {"default_proposal", "explicit_choice", "task_context", "accepted_default"},
    "contact_phase": {"PC0", "PC1", "PC2"},
    "os_issue": {"none", "display_language", "input_method", "locale", "browser_language", "app_language", "timezone"},
}
ACCOUNT_QUESTIONS = {"Q-J01", "Q-J02", "Q-C03", "Q-C04", "Q-C06", "Q-C08"} | {qid for qid in QUESTION_PROMPTS if qid.startswith(("Q-P", "Q-A", "Q-G", "Q-W", "Q-I", "Q-E"))}
SENSITIVE_QUESTIONS = {"Q-J01", "Q-J02", "Q-C03", "Q-C09", "Q-P04", "Q-W02", "Q-I02", "Q-Z01", "Q-Z03", "Q-Z05"}
POSTCONTACT = {"Q-A04", "Q-A05", "Q-A08", "Q-G03", "Q-G04", "Q-W04"}
RESOLVED = {"reported", "observed", "not_applicable"}
BILLING_TASKS = {"renew", "upgrade", "change_channel", "billing_issue"}
PURCHASE_TASKS = {"subscription_preparation", "renew", "upgrade", "change_channel", "compare"}
# Only these explicit current-account categories establish an incident. Historical,
# stale, inferred and refused answers are not evidence of a current emergency.
ACCOUNT_INCIDENT_VALUES = {
    "Q-C03": {"current_suspension": "suspension"},
    "Q-C04": {"suspended": "suspension", "current_suspension": "suspension",
              "identity_review": "identity_review", "unknown_error": "unknown_error"},
}

class InterviewError(ValueError):
    """Invalid or unsafe interview data."""


def _now():
    return datetime.now(timezone.utc).isoformat()


def canonical(question_id):
    if question_id not in QUESTION_PROMPTS or question_id == RETIRED:
        raise InterviewError("Unknown or retired question ID")
    return ALIASES.get(question_id, question_id)


def _safe(value):
    """Conservative defense in depth, not a promise to detect arbitrary secrets."""
    if isinstance(value, dict):
        for key, child in value.items():
            if not isinstance(key, str):
                raise InterviewError("JSON keys must be strings")
            if re.search(r"password|passwd|secret|token|api.?key|private.?key|card.?number|gift.?code|ownership", key, re.I):
                raise InterviewError("Secret or retired ownership field rejected")
            _safe(child)
    elif isinstance(value, list):
        for item in value:
            _safe(item)
    elif isinstance(value, str):
        if re.search(r"(?:password|passwd|pwd|secret|token|api[_-]?key|authorization)\s*[:=]\s*\S+|[a-z][a-z0-9+.-]*://[^\s/@:]+:[^\s/@]+@|\bBearer\s+[A-Za-z0-9._~-]+", value, re.I):
            raise InterviewError("Credential assignment or credential-bearing URL rejected")
        if len(value) > 2000 or re.search(r"(?:sk-(?:ant-)?|ghp_|github_pat_)[A-Za-z0-9_-]{12,}|-----BEGIN .*PRIVATE KEY|(?:\d[ -]?){13,19}", value):
            raise InterviewError("Unsanitized or oversized value rejected")
    elif isinstance(value, float) and (value != value or abs(value) == float("inf")):
        raise InterviewError("Non-finite numbers are not JSON facts")
    elif value is not None and type(value) not in (bool, int, float):
        raise InterviewError("Only JSON values are supported")


def new_state(target_alias, account_alias, *, task_id="task-1"):
    """Create in-memory state. Aliases must be non-identifying local labels."""
    state = {
        "schema_version": SCHEMA_VERSION, "task_id": task_id,
        "target_alias": target_alias, "account_alias": account_alias,
        "facts": {}, "context": deepcopy(CONTEXT_DEFAULTS),
        "asked_question_ids": [], "deferred_branches": [],
        "current_subscription": {"status": "unknown", "source": None, "observed_at": None},
        "payment_intent": "unresolved", "purchase_intent": "subscription_preparation",
        "persistence_consent": {"private_save": False, "export": False, "public_export": False},
    }
    validate_state(state)
    return state


def _validate_date(value):
    if value is not None:
        try:
            date = datetime.fromisoformat(value.replace("Z", "+00:00"))
            if date.tzinfo is None:
                raise ValueError()
        except (ValueError, TypeError, AttributeError):
            raise InterviewError("Timestamp must be timezone-aware ISO 8601") from None


def validate_state(state):
    """Fail closed for unknown versions, fields, aliases, secret keys or malformed facts."""
    if not isinstance(state, dict) or state.get("schema_version") != SCHEMA_VERSION:
        raise InterviewError("Unsupported interview schema version")
    required = {"schema_version", "task_id", "target_alias", "account_alias", "facts", "context",
                "asked_question_ids", "deferred_branches", "current_subscription", "payment_intent",
                "purchase_intent", "persistence_consent"}
    if set(state) != required:
        raise InterviewError("Unexpected or missing state fields")
    _safe(state)
    for name in ("task_id", "target_alias", "account_alias"):
        if not isinstance(state[name], str) or not re.fullmatch(r"[A-Za-z0-9_-]{1,80}", state[name]):
            raise InterviewError("Use short non-identifying aliases")
    ctx = state["context"]
    if (not isinstance(ctx, dict) or set(ctx) - set(CONTEXT_DEFAULTS)
            or set(CONTEXT_DEFAULTS) - set(ctx) - INCIDENT_CONTEXT_FIELDS):
        raise InterviewError("Invalid routing context")
    for name, default in CONTEXT_DEFAULTS.items():
        if name not in ctx:
            continue
        if name in ENUM_CONTEXT and (not isinstance(ctx[name], str) or ctx[name] not in ENUM_CONTEXT[name]):
            raise InterviewError("Invalid context enum: " + name)
        if isinstance(default, bool) and type(ctx[name]) is not bool:
            raise InterviewError("Routing flags must be booleans")
    if ctx["blocked_reason"] is not None and not isinstance(ctx["blocked_reason"], str):
        raise InterviewError("Invalid blocker")
    if not isinstance(ctx.get("route"), str):
        raise InterviewError("Invalid route")
    if ctx["route_selection_basis"] == "accepted_default" and ctx["route"] != "local":
        raise InterviewError("Only local is the default proposal")
    if not isinstance(state["facts"], dict):
        raise InterviewError("Facts must be an object")
    for qid, fact in state["facts"].items():
        if canonical(qid) != qid:
            raise InterviewError("Store canonical IDs only")
        keys = {"value", "state", "source", "subject_ref", "observed_at", "applies_when",
                "required_for", "sensitivity", "clarification_count", "blocker_reason"}
        if not isinstance(fact, dict) or set(fact) != keys or not isinstance(fact["state"], str) or fact["state"] not in FACT_STATES:
            raise InterviewError("Invalid fact envelope")
        expected_subject = state["account_alias" if qid in ACCOUNT_QUESTIONS else "target_alias"]
        if fact["subject_ref"] != expected_subject:
            raise InterviewError("Fact target mismatch; question requires its specific account/device role")
        if fact["state"] == "inferred" and qid in SENSITIVE_QUESTIONS:
            raise InterviewError("Inference cannot establish protected facts")
        if fact["state"] in {"reported", "observed", "inferred"} and not fact["source"]:
            raise InterviewError("Fact provenance is required")
        if fact["state"] in {"unknown", "declined", "unasked", "deferred"} and fact["value"] is not None:
            raise InterviewError("Missing or refused facts must not masquerade as values")
        if type(fact["clarification_count"]) is not int or not 0 <= fact["clarification_count"] <= 1:
            raise InterviewError("At most one clarification is permitted")
        if fact["sensitivity"] != "low" or not isinstance(fact["required_for"], list) or any(x not in {"intake", "plan", "purchase", "apply"} for x in fact["required_for"]):
            raise InterviewError("Invalid fact metadata")
        for field in ("source", "applies_when", "blocker_reason"):
            if fact[field] is not None and not isinstance(fact[field], str):
                raise InterviewError("Fact metadata must be text or null")
        _validate_date(fact["observed_at"])
        if qid in {"Q-J01", "Q-J02"} and fact["state"] in RESOLVED and (not isinstance(fact["value"], str) or fact["value"] not in JOURNEYS):
            raise InterviewError("Invalid subscription journey")
    for field in ("asked_question_ids", "deferred_branches"):
        if not isinstance(state[field], list) or len(state[field]) != len(set(state[field])):
            raise InterviewError("Progress lists must be unique")
    for qid in state["asked_question_ids"]:
        if canonical(qid) != qid:
            raise InterviewError("Progress must use canonical IDs")
    if any(branch not in {"incident", "core", "os", "network", "payment", "local", "vm", "vps", "protection"} for branch in state["deferred_branches"]):
        raise InterviewError("Invalid deferred branch")
    consent = state["persistence_consent"]
    if not isinstance(consent, dict) or set(consent) != {"private_save", "export", "public_export"} or any(type(v) is not bool for v in consent.values()):
        raise InterviewError("Invalid persistence consent")
    current = state["current_subscription"]
    if not isinstance(current, dict) or set(current) != {"status", "source", "observed_at"} or current["status"] not in {"unknown", "none_reported", "active_reported", "observed_active", "conflict"}:
        raise InterviewError("Invalid current subscription")
    _validate_date(current["observed_at"])
    journey_facts = [fact for qid, fact in state["facts"].items() if qid in {"Q-J01", "Q-J02"}
                     and fact["state"] in {"reported", "observed"}]
    if len({fact["value"] for fact in journey_facts}) > 1:
        raise InterviewError("Conflicting subscription journey records")
    expected_status = {"first_subscription": {"none_reported"}, "returning_subscription": {"none_reported"},
                       "existing_subscriber": {"active_reported", "observed_active"}, "unknown": {"unknown"}}
    selected_journey = journey_facts[0]["value"] if journey_facts else "unknown"
    if current["status"] not in expected_status[selected_journey] | {"conflict"}:
        raise InterviewError("Derived subscription status contradicts current journey evidence")
    if state["payment_intent"] not in {"unresolved", "new_subscription", "resubscribe", "renew", "upgrade", "change_channel", "troubleshoot", "none"}:
        raise InterviewError("Invalid payment intent")
    if state["purchase_intent"] not in {"subscription_preparation", "completed", "none"}:
        raise InterviewError("Invalid purchase intent")
    return state


def record_fact(state, question_id, value=None, *, state_name="reported", source=None,
                subject_ref=None, observed_at=None, blocker_reason=None, clarification=False):
    """Absorb each useful fact in a reply; does not mark actions authorized.

    Replacing an answer is an explicit host correction. Cross-object answers fail
    rather than overwrite a different machine/account's facts. Unknown/refused
    answers are terminal until the user volunteers a correction.
    """
    validate_state(state)
    qid = canonical(question_id)
    result = deepcopy(state)
    _normalize_incident_context(result)
    if qid in {"Q-J01", "Q-J02", "Q-C02", "Q-C03", "Q-C04", "Q-C05", "Q-C08", "Q-C11", "Q-P06"} and value is not None and not isinstance(value, str):
        raise InterviewError("This routing fact requires a categorical string")
    old = result["facts"].get(qid, {})
    count = old.get("clarification_count", 0) + int(clarification)
    if count > 1:
        raise InterviewError("Clarification exhausted; permit unknown, decline or pause")
    fact = {"value": value, "state": state_name, "source": source,
            "subject_ref": subject_ref or state["account_alias" if qid in ACCOUNT_QUESTIONS else "target_alias"], "observed_at": observed_at or _now(),
            "applies_when": "current task and target", "required_for": ["intake", "plan"],
            "sensitivity": "low", "clarification_count": count, "blocker_reason": blocker_reason}
    result["facts"][qid] = fact
    if qid in {"Q-J01", "Q-J02"}:
        # These IDs describe one fact. A correction supersedes the alternative
        # entry instead of allowing registry priority to override recency.
        other = "Q-J02" if qid == "Q-J01" else "Q-J01"
        result["facts"].pop(other, None)
        result["current_subscription"] = {"status": "unknown", "source": source, "observed_at": fact["observed_at"]}
        result["payment_intent"] = "unresolved"
    if qid in {"Q-J01", "Q-J02"} and state_name in {"reported", "observed"}:
        status = {"first_subscription": "none_reported", "returning_subscription": "none_reported",
                  "existing_subscriber": "active_reported", "unknown": "unknown"}.get(value)
        result["current_subscription"] = {"status": status, "source": source, "observed_at": fact["observed_at"]}
        result["payment_intent"] = {"first_subscription": "new_subscription", "returning_subscription": "resubscribe"}.get(value, "unresolved")
    if qid == "Q-C05" and state_name in {"reported", "observed"} and value in {"local", "vm", "vps", "compare"}:
        result["context"].update(route=value, route_selection_basis="explicit_choice" if value != "compare" else "default_proposal")
    if qid == "Q-C05" and state_name in {"reported", "observed"} and value == "accepted_default":
        # Accept only the actual local proposal, never silently replace a chosen
        # VM/VPS or a comparison with a different route. Repeating the same
        # accepted answer is harmless; it is still not execution permission.
        context = result["context"]
        if context["route"] != "local" or context["route_selection_basis"] not in {"default_proposal", "accepted_default"}:
            raise InterviewError("No current local default proposal to accept")
        context["route_selection_basis"] = "accepted_default"
    if qid == "Q-C11" and state_name in {"reported", "observed"} and value in ENUM_CONTEXT["task"]:
        result["context"]["task"] = value
        result["payment_intent"] = value if value in {"renew", "upgrade", "change_channel"} else "none"
    if qid == "Q-P06" and state_name in {"reported", "observed"} and value in ENUM_CONTEXT["billing_channel"]:
        result["context"]["billing_channel"] = value
    if qid in ACCOUNT_INCIDENT_VALUES and state_name in {"reported", "observed"}:
        if result["context"]["incident_origin"] == "legacy_unverified":
            # This fresh account correction replaces an unattributed old cache,
            # not a separately identified host incident.
            result["context"].update(incident="none", incident_origin="host")
    if (qid in ACCOUNT_INCIDENT_VALUES and state_name in {"reported", "observed"}
            and value in ACCOUNT_INCIDENT_VALUES[qid]):
        # A fresh current report reopens triage. Do not cache the derived incident
        # in host context: corrections/staleness must not leave it stuck there or
        # overwrite a separately reported credential/data emergency.
        if (_account_incident(state) != ACCOUNT_INCIDENT_VALUES[qid][value]
                or _account_incident_resolved(state)):
            _refresh_incident_answers(result)
        result["context"]["account_incident_resolved"] = False
    validate_state(result)
    return result


def record_facts(state, answers, *, source=None):
    """Atomically absorb normalized facts from one reply, before choosing a question.

    The host extracts explicit facts; this is not a natural-language parser.
    Each item uses question_id, value, optional state and source. Per-item source
    overrides the shared source. Duplicate canonical/alternative journey IDs are
    rejected instead of applying order-dependent corrections within one reply.
    Journey facts precede derived task updates regardless of JSON order. A
    resolved old-subscriber task conflicts with an explicit first/returning
    subscription journey and requires host clarification, not a guessed intent.
    Invalid input returns no partial state and never mutates the caller's state.
    No envelope field can grant action, contact or persistence permission.
    """
    validate_state(state)
    if not isinstance(answers, list) or not 1 <= len(answers) <= len(QUESTION_PROMPTS):
        raise InterviewError("Expected a bounded nonempty answer list")
    seen = set()
    for item in answers:
        if not isinstance(item, dict) or not isinstance(item.get("question_id"), str) or set(item) - {"question_id", "value", "state", "source"}:
            raise InterviewError("Invalid answer envelope")
        state_name = item.get("state", "reported")
        if type(state_name) is not str or state_name not in FACT_STATES:
            raise InterviewError("Invalid answer state")
        qid = canonical(item["question_id"])
        identity = "Q-J01" if qid == "Q-J02" else qid
        if identity in seen:
            raise InterviewError("Duplicate fact in one reply; clarify before recording")
        seen.add(identity)
    result = deepcopy(state)
    observed_at = _now()
    ordered = sorted(answers, key=lambda item: 0 if item["question_id"] in {"Q-J01", "Q-J02"}
                     else 1 if item["question_id"] in ACCOUNT_INCIDENT_VALUES else 2)
    for item in ordered:
        if (item["question_id"] == "Q-C11" and item.get("state", "reported") in {"reported", "observed"}
                and journey(result) in {"first_subscription", "returning_subscription"}):
            raise InterviewError("Old-subscriber task conflicts with subscription journey; clarify first")
        result = record_fact(result, item["question_id"], item.get("value"),
                             state_name=item.get("state", "reported"),
                             source=item.get("source", source), observed_at=observed_at)
    return result


def set_context(state, **changes):
    """Set explicit routing facts, not permissions. Context never opens G3.

    incident_resolved alone resolves the currently presented incidents for legacy
    callers. With an explicit incident it applies only to that host incident;
    account_incident_resolved can independently resolve current account evidence.
    Reporting an incident again after resolution starts a fresh episode unless
    the caller explicitly includes incident_resolved=True in the same update.
    """
    validate_state(state)
    result = deepcopy(state)
    _normalize_incident_context(result)
    result["context"].update(changes)
    if "incident" in changes:
        result["context"]["incident_origin"] = "host"
    if ("incident" in changes and changes["incident"] != "none"
            and (changes["incident"] != state["context"]["incident"]
                 or state["context"]["incident_resolved"])
            and "incident_resolved" not in changes):
        result["context"]["incident_resolved"] = False
    if ("incident_resolved" in changes and "incident" not in changes
            and "account_incident_resolved" not in changes):
        # Existing callers use this to resolve the incidents currently presented.
        result["context"]["account_incident_resolved"] = changes["incident_resolved"]
    if ("incident" in changes and result["context"]["incident"] != "none"
            and not result["context"]["incident_resolved"]
            and (state["context"]["incident"] != changes["incident"]
                 or state["context"]["incident_resolved"] or _legacy_incident_review(state))):
        _refresh_incident_answers(result)
    validate_state(result)
    return result


def journey(state):
    for qid in ("Q-J02", "Q-J01"):
        fact = state["facts"].get(qid, {})
        if fact.get("state") in {"reported", "observed"} and fact.get("value") in JOURNEYS:
            return fact["value"]
    return "unknown"


def _value(state, qid):
    fact = state["facts"].get(canonical(qid), {})
    return fact.get("value") if fact.get("state") in {"reported", "observed"} else None


def _account_incident(state):
    """Derive account triage from current evidence, never from persisted caches."""
    for qid, categories in ACCOUNT_INCIDENT_VALUES.items():
        if qid == "Q-C03" and _legacy_incident_review(state):
            continue
        value = _value(state, qid)
        if isinstance(value, str) and value in categories:
            return categories[value]
    return "none"


def _urgent_incident(state):
    context = state["context"]
    return ((not context["incident_resolved"] and not _legacy_incident_review(state)
             and context["incident"] != "none")
            or (not _account_incident_resolved(state) and _account_incident(state) != "none"))


def _account_incident_resolved(state):
    return state["context"].get("account_incident_resolved", state["context"]["incident_resolved"])


def _legacy_incident_review(state):
    context = state["context"]
    origin = context.get("incident_origin")
    return (origin == "legacy_unverified" or
            (origin is None and context["incident"] == "suspension" and "Q-C03" in state["facts"]))


def _normalize_incident_context(state):
    """Upgrade only missing lifecycle metadata in an already validated copy.

    Published schema-1 cached Q-C03 suspension without provenance. It cannot be
    distinguished from an explicit host incident, so require fresh clarification
    rather than asserting either current suspension or resolution.
    """
    context = state["context"]
    if "incident_origin" not in context:
        legacy = _legacy_incident_review(state)
        context["incident_origin"] = "legacy_unverified" if legacy else "host"
        if legacy:
            fact = state["facts"]["Q-C03"]
            fact.update(state="stale", clarification_count=0,
                        blocker_reason="Legacy incident attribution and current status require confirmation")
            state["asked_question_ids"] = [qid for qid in state["asked_question_ids"] if qid != "Q-C03"]
    context.setdefault("account_incident_resolved", context["incident_resolved"])


def _refresh_incident_answers(state):
    """A new incident cannot reuse another episode's object, notice or recovery."""
    incident_ids = set(_ids("H", 1, 8))
    for qid in incident_ids & state["facts"].keys():
        state["facts"][qid].update(state="stale", clarification_count=0,
                                   blocker_reason="New incident requires current episode evidence")
    state["asked_question_ids"] = [qid for qid in state["asked_question_ids"] if qid not in incident_ids]


def _ids(prefix, start, end):
    return ["Q-%s%02d" % (prefix, i) for i in range(start, end + 1)]


def applicable_questions(state):
    """Return ordered branch requirements for the host, never a user-facing form."""
    validate_state(state)
    c = state["context"]
    requirements = []
    def add(branch, stage, ids):
        for qid in ids:
            qid = canonical(qid)
            if not any(x["id"] == qid for x in requirements):
                requirements.append({"id": qid, "branch": branch, "stage": stage,
                                     "postcontact": qid in POSTCONTACT})
    urgent = _urgent_incident(state)
    if urgent:
        add("incident", "I0", _ids("H", 1, 7))
        # Do not delay protective/official incident handling with purchasing.
        return requirements
    if _legacy_incident_review(state):
        add("incident", "I0", ["Q-C03"])
        return requirements
    add("core", "I1", ["Q-J02" if (c["ambiguous_experience"] and journey(state) == "unknown") or _value(state, "Q-J02") in JOURNEYS - {"unknown"} else "Q-J01"])
    j = journey(state)
    if j == "existing_subscriber" and c["task"] == "subscription_preparation":
        add("core", "I1", ["Q-C11"])
    purchase = (c["task"] in PURCHASE_TASKS and (j != "existing_subscriber" or c["task"] != "subscription_preparation") and not c["purchase_completed"])
    add("core", "I2", ["Q-C02", "Q-C01"])
    os = _value(state, "Q-C02")
    if os == "windows":
        add("os", "I2", ["Q-OS02"])
        if c["os_issue"] != "none":
            add("os", "I2", ["Q-OS09"])
        if c["os_issue"] in {"display_language", "input_method", "locale", "browser_language", "app_language"}:
            add("os", "I2", ["Q-OS04"])
        if c["os_issue"] == "display_language":
            add("os", "I2", ["Q-OS05"])
        if c["timezone_issue"] or c["os_issue"] == "timezone":
            add("os", "I2", _ids("OS", 6, 8))
        if c["windows10"]:
            add("os", "I2", ["Q-OS10"])
    elif os == "macos":
        add("os", "I2", ["Q-OS03"])
        if c["os_issue"] != "none":
            add("os", "I2", ["Q-OS09", "Q-OS11"])
    elif os in {"linux", "mobile_only", "other"}:
        add("os", "I2", ["Q-OS12"])
    if purchase:
        add("core", "I2", ["Q-C08"])
    add("core", "I3", ["Q-C03", "Q-C04"])
    if c["route_selection_basis"] == "default_proposal":
        add("core", "I3", ["Q-C05"])
    if _value(state, "Q-C04") not in (None, "unregistered"):
        add("core", "I3", ["Q-C06"])
    if (_value(state, "Q-C03") in {"past_suspension", "past_incident"}
            or (c["incident_resolved"] and c["incident"] != "none")
            or (_account_incident_resolved(state) and _account_incident(state) != "none")):
        add("incident", "I3", _ids("H", 1, 8))
    add("network", "I4", ["Q-C09", "Q-N01", "Q-N02", "Q-N03", "Q-N04", "Q-N06"])
    if c["existing_test"]:
        add("network", "I4", ["Q-N05"])
    old = c["subscription_conflict"] or (j == "existing_subscriber" and c["task"] in BILLING_TASKS)
    if old:
        add("payment", "I4", ["Q-P02"])
    if purchase or c["task"] in {"api", "enterprise", "billing_issue"}:
        if c["billing_product_ambiguous"]:
            add("payment", "I4", ["Q-P01"])
        channel = c["billing_channel"]
        if channel in {"unselected", "compare"}:
            add("payment", "I4", ["Q-P03", "Q-P04", "Q-P06"])
        if c["budget_needed"] or _value(state, "Q-C08") in {"compare", "undecided"}:
            add("payment", "I4", ["Q-P05"])
        add("payment", "I4", ["Q-P07"])
        if channel == "apple":
            add("payment", "I4", _ids("A", 1, 5))
            if old:
                add("payment", "I4", ["Q-A06"])
            if c["gift_card"]:
                add("payment", "I4", ["Q-A07", "Q-A08"])
            if c["buying_gift_card"]:
                add("payment", "I4", ["Q-A09"])
            add("payment", "I4", ["Q-A10"])
        elif channel == "google":
            add("payment", "I4", _ids("G", 1, 5))
        elif channel == "web":
            add("payment", "I4", _ids("W", 1, 4))
        if channel == "api" or c["task"] == "api":
            add("payment", "I4", ["Q-I01", "Q-I03", "Q-I04"])
            if c["organization_task"]:
                add("payment", "I4", ["Q-I02"])
        if channel == "enterprise" or c["task"] == "enterprise":
            add("payment", "I4", _ids("E", 1, 2))
    if c["route_selection_basis"] != "default_proposal" and c["route"] != "compare":
        route = c["route"]
        if route == "local":
            add(route, "I5", ["Q-L01", "Q-L04"])
            if c["compatibility_needed"]:
                add(route, "I5", ["Q-L02"])
            if c["integration_used"]:
                add(route, "I5", ["Q-L03"])
        elif route == "vm":
            add(route, "I5", _ids("V", 1, 6))
        elif route == "vps":
            add(route, "I5", _ids("S", 1, 7))
    add("protection", "I5", ["Q-C12", "Q-Z01", "Q-C10"])
    if c["change_planned"]:
        add("protection", "I5", ["Q-Z03", "Q-Z04"])
    if c["persistence_requested"]:
        add("protection", "I5", ["Q-Z05"])
    return requirements


def next_question(state):
    """Choose one unanswered relevant question, or None on pause/terminal coverage.

    An emitted question is not yet asked: call mark_asked after delivering it.
    Unknown/declined/deferred answers are not re-asked automatically. Stale or
    conflicting facts receive at most one clarification. PC0 never asks the host
    to launch Claude or perform a live payment check.
    """
    validate_state(state)
    if state["context"]["paused"] or state["context"]["blocked_reason"]:
        return None
    for item in applicable_questions(state):
        if item["branch"] in state["deferred_branches"]:
            continue
        if item["postcontact"] and state["context"]["contact_phase"] == "PC0":
            continue
        fact = state["facts"].get(item["id"], {})
        status = fact.get("state", "unasked")
        if item["id"] == "Q-C03" and _legacy_incident_review(state) and status in RESOLVED:
            status = "stale"
        clarification = status in {"conflict", "stale"}
        if status != "unasked" and not (clarification and fact.get("clarification_count", 0) == 0):
            continue
        if item["id"] in state["asked_question_ids"] and not clarification:
            continue
        return {**item, "prompt": QUESTION_PROMPTS[item["id"]], "clarification": clarification,
                "allowed_outcomes": ["reported", "unknown", "declined", "deferred"],
                "requires_action_authorization": False}
    return None


def mark_asked(state, question_id):
    validate_state(state)
    qid = canonical(question_id)
    result = deepcopy(state)
    if qid not in {i["id"] for i in applicable_questions(state)}:
        raise InterviewError("Question is not applicable")
    if qid not in result["asked_question_ids"]:
        result["asked_question_ids"].append(qid)
    fact = result["facts"].get(qid)
    if fact and (fact["state"] in {"conflict", "stale"} or
                 (qid == "Q-C03" and _legacy_incident_review(state))):
        fact["clarification_count"] = 1
    validate_state(result)
    return result


def defer_branch(state, branch):
    result = deepcopy(validate_state(state))
    if branch not in result["deferred_branches"]:
        result["deferred_branches"].append(branch)
    validate_state(result)
    return result


def resume_branch(state, branch):
    result = deepcopy(validate_state(state))
    if branch in result["deferred_branches"]:
        result["deferred_branches"].remove(branch)
    return result


def assessment(state):
    """Separate coverage, planning readiness and action authorization explicitly."""
    validate_state(state)
    required = applicable_questions(state)
    unresolved = []
    for item in required:
        fact = state["facts"].get(item["id"], {})
        reason = None
        if item["branch"] in state["deferred_branches"]:
            reason = "branch_deferred"
        elif item["id"] == "Q-C03" and _legacy_incident_review(state):
            reason = "legacy_incident_unverified"
        elif item["postcontact"] and state["context"]["contact_phase"] == "PC0":
            reason = "requires_contact_gate"
        elif fact.get("state", "unasked") not in RESOLVED:
            reason = fact.get("state", "unasked")
        if reason:
            unresolved.append({"id": item["id"], "reason": reason})
    c = state["context"]
    if c["route_selection_basis"] == "default_proposal" and not any(x["id"] == "Q-C05" for x in unresolved):
        unresolved.append({"id": "Q-C05", "reason": "route_unconfirmed"})
    if journey(state) == "unknown" and not any(x["id"] in {"Q-J01", "Q-J02"} for x in unresolved):
        unresolved.append({"id": "Q-J01", "reason": "journey_unknown"})
    urgent = _urgent_incident(state)
    outcome = "complete" if not unresolved else "partial"
    if urgent:
        outcome = "emergency_deferred"
    if c["paused"]:
        outcome = "paused"
    if c["blocked_reason"]:
        outcome = "blocked"
    return {"stage": next((i["stage"] for i in required if any(u["id"] == i["id"] for u in unresolved)), "I6"),
            "G1": {"status": outcome, "unresolved_fields": unresolved},
            "G2": {"status": "pass" if outcome == "complete" else "blocked", "conditional_plan_only": outcome != "complete"},
            "G3": {"status": "blocked", "reason": "Interview answers are not specific action authorization; action and contact gates must be checked separately"},
            "active_branches": list(dict.fromkeys(i["branch"] for i in required)),
            "deferred_branches": list(state["deferred_branches"]),
            "route_confirmation": "unconfirmed" if c["route_selection_basis"] == "default_proposal" else "confirmed",
            "current_subscription": deepcopy(state["current_subscription"])}


def complete_purchase(state, *, source, observed_at=None, observed=False):
    """Record a reported/observed completed purchase without executing one."""
    result = record_fact(state, "Q-J01", "existing_subscriber", source=source,
                         state_name="observed" if observed else "reported", observed_at=observed_at)
    result["facts"].pop("Q-J02", None)
    result["current_subscription"]["status"] = "observed_active" if observed else "active_reported"
    result["context"].update(purchase_completed=True, task="environment")
    result["purchase_intent"] = "completed"
    result["payment_intent"] = "none"
    validate_state(result)
    return result


def dumps_state(state, *, host_opt_in=False, scope="private_save"):
    """Return validated private JSON only with explicit host permission for scope.

    This function does not write files. An answer to Q-Z05 alone never authorizes
    storage; host_opt_in must represent separately obtained specific permission.
    Pattern screening cannot guarantee removal of all identifying/secret data.
    Public publication requires a separate manually reviewed artifact, not this state.
    """
    result = deepcopy(validate_state(state))
    _normalize_incident_context(result)
    if scope == "public_export":
        raise InterviewError("Public export requires a separately reviewed redacted artifact")
    if scope not in result["persistence_consent"] or host_opt_in is not True:
        raise InterviewError("Explicit host opt-in for persistence/export is required")
    result["persistence_consent"][scope] = True
    return json.dumps(result, ensure_ascii=False, sort_keys=True, allow_nan=False)


def loads_state(serialized):
    """Validate resume data; never inherit action permissions from saved answers."""
    if not isinstance(serialized, str) or len(serialized) > 250000:
        raise InterviewError("Invalid or oversized saved interview")
    def unique_pairs(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise InterviewError("Duplicate JSON keys")
            obj[key] = value
        return obj
    try:
        result = json.loads(serialized, object_pairs_hook=unique_pairs,
                            parse_constant=lambda value: (_ for _ in ()).throw(InterviewError("Non-finite JSON number")))
    except (ValueError, TypeError, RecursionError) as exc:
        raise InterviewError("Invalid saved interview: " + str(exc)) from None
    validate_state(result)
    _normalize_incident_context(result)
    # Saved permission is historical evidence, not new permission to save/export.
    result["persistence_consent"] = {key: False for key in result["persistence_consent"]}
    return result


# Machine-readable schema entrypoint; runtime validation adds cross-field and
# target-binding constraints not expressible in this compact schema.
STATE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "$id": "urn:claude-guardian:interview:1.0.0", "type": "object",
    "required": list(new_state("target", "account")), "additionalProperties": False,
    "properties": {
        "schema_version": {"const": SCHEMA_VERSION},
        **{key: {"type": "string"} for key in ("task_id", "target_alias", "account_alias", "payment_intent", "purchase_intent")},
        **{key: {"type": "object"} for key in ("facts", "context", "current_subscription", "persistence_consent")},
        **{key: {"type": "array", "items": {"type": "string"}, "uniqueItems": True} for key in ("asked_question_ids", "deferred_branches")},
    },
}


def invalidate_facts(state, question_ids, *, reason):
    """Mark only relevant changed/expired facts stale; retain their provenance.

    The host chooses affected fields based on current task and evidence age.
    There is deliberately no arbitrary permanent validity or global re-interview.
    """
    result = deepcopy(validate_state(state))
    if not isinstance(reason, str) or not reason:
        raise InterviewError("A refresh reason is required")
    question_ids = list(question_ids)
    for question_id in question_ids:
        qid = canonical(question_id)
        if qid in result["facts"]:
            result["facts"][qid].update(state="stale", blocker_reason=reason, clarification_count=0)
        if qid in result["asked_question_ids"]:
            result["asked_question_ids"].remove(qid)
    if any(qid in {"Q-J01", "Q-J02"} for qid in question_ids) and journey(result) == "unknown":
        result["current_subscription"] = {"status": "unknown", "source": None, "observed_at": None}
        result["payment_intent"] = "unresolved"
    validate_state(result)
    return result


def begin_task(state, *, task_id, task, target_alias=None, account_alias=None):
    """Start an explicitly requested new task without silently reusing its old goal.

    Same-target facts are retained. A new device keeps only explicitly account-bound
    subscription/account facts; a new account starts fresh. No data/credentials move.
    A new purchase target must be supplied afresh; previous C08 is not entitlement.
    """
    validate_state(state)
    target_alias = target_alias or state["target_alias"]
    account_alias = account_alias or state["account_alias"]
    if (target_alias, account_alias) != (state["target_alias"], state["account_alias"]):
        result = new_state(target_alias, account_alias, task_id=task_id)
        if account_alias == state["account_alias"]:
            # A different device does not imply a different subscription.
            keep = {"Q-J01", "Q-J02", "Q-C03", "Q-C04", "Q-C06"}
            result["facts"] = {qid: deepcopy(fact) for qid, fact in state["facts"].items()
                               if qid in keep and fact["subject_ref"] == account_alias}
            result["current_subscription"] = deepcopy(state["current_subscription"])
            if _legacy_incident_review(state):
                result["context"].update(incident=state["context"]["incident"],
                                         incident_origin="legacy_unverified")
            if _account_incident(state) != "none":
                # A device change does not create a new account incident or undo
                # the host's explicit resolution of the retained account facts.
                result["context"]["account_incident_resolved"] = _account_incident_resolved(state)
    else:
        result = deepcopy(state)
        old_task = result["task_id"]
        result["task_id"] = task_id
        for fact in result["facts"].values():
            if fact["subject_ref"] == old_task:
                fact["subject_ref"] = task_id
        reset_ids = {"Q-C01", "Q-C11", "Q-Z01", "Q-Z03", "Q-Z04", "Q-Z05"}
        if task in PURCHASE_TASKS:
            reset_ids |= {"Q-C08", "Q-P05", "Q-P06", "Q-P07"} | POSTCONTACT
        for qid in reset_ids:
            result["facts"].pop(qid, None)
        result["asked_question_ids"] = [q for q in result["asked_question_ids"] if q not in reset_ids]
        result["deferred_branches"] = []
        result["persistence_consent"] = {key: False for key in result["persistence_consent"]}
        result["context"].update(paused=False, blocked_reason=None, purchase_completed=False,
                                 change_planned=False, persistence_requested=False, contact_phase="PC0")
    result["context"]["task"] = task
    result["purchase_intent"] = "subscription_preparation" if task in PURCHASE_TASKS else "none"
    result["payment_intent"] = task if task in {"renew", "upgrade", "change_channel"} else "unresolved" if task in PURCHASE_TASKS else "none"
    validate_state(result)
    return result


FACT_SCHEMA = {
    "type": "object", "additionalProperties": False,
    "required": ["value", "state", "source", "subject_ref", "observed_at", "applies_when",
                 "required_for", "sensitivity", "clarification_count", "blocker_reason"],
    "properties": {
        "value": {}, "state": {"enum": sorted(FACT_STATES)},
        **{key: {"type": ["string", "null"]} for key in ("source", "observed_at", "applies_when", "blocker_reason")},
        "subject_ref": {"type": "string"}, "sensitivity": {"const": "low"},
        "clarification_count": {"type": "integer", "minimum": 0, "maximum": 1},
        "required_for": {"type": "array", "items": {"enum": ["intake", "plan", "purchase", "apply"]}},
    },
}
STATE_SCHEMA["properties"]["facts"] = {
    "type": "object", "additionalProperties": False,
    "properties": {qid: FACT_SCHEMA for qid in QUESTION_PROMPTS if qid != RETIRED and qid not in ALIASES},
}
STATE_SCHEMA["properties"]["context"] = {
    "type": "object", "additionalProperties": False,
    "required": [key for key in CONTEXT_DEFAULTS if key not in INCIDENT_CONTEXT_FIELDS],
    "properties": {key: {"enum": sorted(ENUM_CONTEXT[key])} if key in ENUM_CONTEXT else
                   {"type": "boolean"} if type(value) is bool else {"type": ["string", "null"]}
                   for key, value in CONTEXT_DEFAULTS.items()},
}
STATE_SCHEMA["properties"]["persistence_consent"] = {
    "type": "object", "additionalProperties": False,
    "required": ["private_save", "export", "public_export"],
    "properties": {key: {"type": "boolean"} for key in ("private_save", "export", "public_export")},
}
