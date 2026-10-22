"""Offline documentation contracts, not proof of deployed/platform behavior."""
import re
import unittest
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
REFS = ROOT / "skills" / "claude-guardian" / "references"


class GuidanceContracts(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")
        cls.accounts = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        cls.incidents = (REFS / "incidents-and-integrations.md").read_text(encoding="utf-8")

    def test_windows_adapter_ipv6_hint_is_prompt_only(self):
        text = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        section = text.split('<a id="windows-adapter-ipv6-hint"></a>', 1)[1].split('<a id="selected-rule-scope"></a>', 1)[0]
        for term in ("ncpa.cpl", "Disable-NetAdapterBinding", "Enable-NetAdapterBinding",
                     "ms_tcpip6", "原值→新值", "外层传输不依赖 IPv6", "不提供、也不新增自动修改网卡的脚本"):
            self.assertIn(term, section)
        scripts = ROOT / "skills" / "claude-guardian" / "scripts"
        for path in scripts.glob("*.py"):
            self.assertNotIn("Disable-NetAdapterBinding", path.read_text(encoding="utf-8"), path.name)

    def test_fake_ip_leak_boundaries_and_cache_flush_are_documented(self):
        net = (REFS / "network-and-remedies.md").read_text(encoding="utf-8")
        rem = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        for term in ("fake-ip-filter", "own DoH/DoT", "Fake-IP itself is not"):
            self.assertIn(term, net)
        for term in ("ipconfig /flushdns", "dscacheutil -flushcache", "mDNSResponder", "Fake-IP 本身不算泄漏"):
            self.assertIn(term, rem)

    def test_account_warmup_guidance_is_labelled_community_experience(self):
        section = (REFS / "account-onboarding.md").read_text(encoding="utf-8")
        for term in ("社区经验", "未经本项目验证", "邮箱注册", "Proton", "至少使用 3 天", "至少使用 15 天",
                     "重置卡", "教育邮箱", "不购买、租借或伪造", "不是官方门槛", "不能据此断言"):
            self.assertIn(term, section)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("社区经验，未经验证", skill)
        self.assertNotIn("保证不封", section)

    def test_owner_sources_are_attached_and_s02_is_first_payment_reference(self):
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("资料随答附带", 1)[1]
        for term in ("sources/S02-ai-payments.md", "第一项", "S03-claude-experience.pdf",
                     "S05-local-protection.md", "S06-macos-cleanup-sanitized.md", "S01-server-glossary.md"):
            self.assertIn(term, section)
        acc = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        for term in ("支付任务的核心参考", "../sources/S02-ai-payments.md", "证据等级", "不推荐", "当前官方页面核验"):
            self.assertIn(term, acc)
        lib = (REFS / "source-library.md").read_text(encoding="utf-8")
        self.assertIn("第一项必须是 S02", lib)
        for link in ("S01-server-glossary.md", "S02-ai-payments.md", "S04-claude-guide.md",
                     "S05-local-protection.md", "S06-macos-cleanup-sanitized.md", "S07-vps-script-catalog.md",
                     "S03-claude-experience.pdf"):
            self.assertTrue((ROOT / "skills" / "claude-guardian" / "sources" / link).exists(), link)

    def test_local_route_egress_ip_options_and_vps_reports_are_wired(self):
        egress = (REFS / "egress-ip-options.md").read_text(encoding="utf-8")
        for term in ("纯净机场 IP", "自建梯", "家宽拼车", "Max", "Pro", "所有者推荐", "不代买",
                     "请用户自己上网搜索", "3x-ui", "CN2 GIA", "小火箭", "FlClash", "Clash Verge"):
            self.assertIn(term, egress)
        self.assertNotIn("社区观点并不一致", egress)
        routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")
        self.assertIn("L2a 固定出口 IP 的来源", routes)
        self.assertIn("选 VM 或 VPS 路线时不触发", routes)
        skill_root = ROOT / "skills" / "claude-guardian"
        index = (skill_root / "sources" / "vps-recommendations" / "INDEX.md").read_text(encoding="utf-8")
        pdfs = sorted((skill_root / "sources" / "vps-recommendations").glob("*.pdf"))
        self.assertEqual(len(pdfs), 17)
        for pdf in pdfs:
            self.assertIn(pdf.name, index)
        skill_text = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("sources/vps-recommendations/INDEX.md", skill_text)
        self.assertIn("必附", skill_text)
        for heading in ("## 业务", "## 性价比", "## 高端家宽"):
            self.assertIn(heading, index)

    def test_independent_route_lifecycles_have_ordered_cards(self):
        # Each route includes intake, preparation, contact, ordinary use and recovery.
        for prefix, count in (("L", 3), ("V", 4), ("P", 5)):
            with self.subTest(route=prefix):
                positions = []
                for index in range(1, count + 1):
                    match = re.search(rf"^### {prefix}{index} .+$", self.routes, re.M)
                    self.assertIsNotNone(match)
                    positions.append(match.start())
                self.assertEqual(positions, sorted(positions))
        for start, end in (("## R-LOCAL 独立", "## R-VM 独立"),
                           ("## R-VM 独立", "## R-VPS 独立"),
                           ("## R-VPS 独立", "## 来源与维护")):
            section = self.routes.split(start, 1)[1].split(end, 1)[0]
            for term in ("PC0", "PC1/PC2", "验收", "恢复", "批准"):
                self.assertIn(term, section)

    def test_routes_preserve_free_tools_and_rescue_constraints(self):
        for term in ("LuLu", "系统内置防火墙", "零新增费用", "独立救援",
                     "额外出口仅当需求确立", "临时组件", "tmux", "WSL",
                     "不能指向宿主代理", "S08 未提供"):
            self.assertIn(term, self.routes)

    def test_account_cards_cover_all_channels_and_post_purchase(self):
        for index in range(1, 8):
            self.assertRegex(self.accounts, rf"(?m)^### B{index} ")
        for index in range(1, 4):
            self.assertRegex(self.accounts, rf"(?m)^### A{index} ")
        for term in ("Q-A01–Q-A10", "Q-G01–Q-G05", "Q-W01–Q-W04",
                     "Q-I01–Q-I04", "Q-E01–Q-E02", "续费", "重复扣款",
                     "不先买卡", "本人完成支付", "含税总额"):
            self.assertIn(term, self.accounts)

    def test_integrations_and_incidents_have_full_cards(self):
        for prefix, count in (("I", 3), ("J", 3), ("K", 5)):
            for index in range(1, count + 1):
                self.assertRegex(self.incidents, rf"(?m)^### {prefix}{index} ")
        for term in ("CPA", "new-api", "Pi Agent", "stdio", "幂等", "孤立子进程",
                     "数据导出", "事实草稿模板", "原渠道退款", "响应来源"):
            self.assertIn(term, self.incidents)

    def test_contact_and_evidence_boundaries_are_explicit(self):
        for name, body in (("routes", self.routes), ("accounts", self.accounts),
                           ("incidents", self.incidents)):
            with self.subTest(document=name):
                for term in ("PC0", "PC1", "PC2", "Codex", "unknown", "授权"):
                    self.assertIn(term, body)
                self.assertRegex(body, "未.*(核验|测)|不.*能力声明")
        self.assertIn("不运行 `claude --version`", self.routes)
        self.assertIn("不通过浏览器、搜索、MCP 或 shell 主动请求", self.accounts)
        self.assertIn("公开页面也不例外", self.incidents)

    def test_incident_containment_distinguishes_agent_and_user_tasks(self):
        # Regression: exposure alone must not authorize stopping a user's jobs.
        a3 = self.accounts.split("### A3 ", 1)[1].split("## M03", 1)[0]
        self.assertIn("助手立即停止自己尚未发出的重试", a3)
        self.assertIn("停止用户正在运行的依赖任务前必须取得明确批准", a3)
        overview = self.incidents.split("## Cleanup", 1)[0]
        self.assertIn("assistant’s own unsent retries", overview)
        self.assertIn("user’s running dependent automation requires explicit approval", overview)
        self.assertNotIn("step and stop dependent automation", overview)

    def test_evidence_export_requires_approval_for_local_and_remote_targets(self):
        evidence = self.incidents.split("### K3 ", 1)[1].split("### K4 ", 1)[0]
        self.assertIn("具体内容和精确保存目的地的批准", evidence)
        self.assertIn("本地私有路径与远端存储均适用", evidence)
        self.assertIn("不能因本地保存而省略授权", evidence)
        self.assertNotIn("以本地私有位置或用户批准的存储保存", evidence)

    def test_relative_links_resolve_inside_repository(self):
        for name, body in (("routes", self.routes), ("accounts", self.accounts),
                           ("incidents", self.incidents)):
            for target in re.findall(r"\]\(([^)]+)\)", body):
                if "://" in target or target.startswith("#"):
                    continue
                with self.subTest(document=name, target=target):
                    resolved = (REFS / target.split("#", 1)[0]).resolve()
                    self.assertTrue(resolved.is_relative_to(ROOT))
                    self.assertTrue(resolved.is_file())

    def test_historical_sources_are_not_current_claims(self):
        for body in (self.routes, self.accounts, self.incidents):
            self.assertIn("历史", body)
            self.assertIn("官方", body)
            self.assertRegex(body, "本次.*(没有|未).*?(核验|访问|请求)")
        self.assertIn("社区经验", self.accounts)
        self.assertIn("来源观点", self.incidents)

    def test_guides_are_not_remote_execution_scripts(self):
        # A prose runbook must not embed unchecked fetch-and-execute commands.
        for body in (self.routes, self.accounts, self.incidents):
            self.assertNotRegex(body, r"(?i)(?:curl|wget)[^\n]*\|\s*(?:sudo\s+)?(?:sh|bash)")
            self.assertNotRegex(body, r"(?m)^\s*(?:TODO|TBD|FIXME)\s*[:：]")


class PostRepairStabilityGuidanceContracts(unittest.TestCase):
    """Prose regression checks only; substantive review and real observations remain separate."""

    @classmethod
    def setUpClass(cls):
        cls.guide = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        cls.skill = (REFS.parent / "SKILL.md").read_text(encoding="utf-8")

    def stability_section(self):
        match = re.search(
            r'<a id="post-repair-stability"></a>\n'
            r'## 修复后的出口稳定性与生命周期复验\n(.*?)'
            r'(?=\n<a id="environment-entry"></a>)', self.guide, re.S)
        self.assertIsNotNone(match, "The repair loop needs its scoped stability guidance")
        return match.group(1)

    def test_existing_repair_entry_reaches_one_authoritative_section(self):
        section = self.stability_section()
        self.assertEqual(self.guide.count('<a id="post-repair-stability"></a>'), 1)
        loop = self.guide.split("## 一次任务的闭环", 1)[1].split(
            '<a id="post-repair-stability"></a>', 1)[0]
        self.assertIn("#post-repair-stability", loop)
        self.assertIn("取消、拒绝、目标失配", loop)
        self.assertIn("不把无关任务", loop)
        self.assertIn("references/agent-remediation.md", self.skill)
        self.assertIn("执行和复测，详见", self.skill)
        self.assertIn("同一修复闭环", section)
        for target in re.findall(r"\]\(([^)]+)\)", section):
            if target.startswith("#"):
                self.assertIn('<a id="' + target[1:] + '"></a>', self.guide)
            elif "://" not in target:
                resolved = (REFS / target.split("#", 1)[0]).resolve()
                self.assertTrue(resolved.is_relative_to(ROOT))
                self.assertTrue(resolved.is_file())

    def test_persistence_and_four_evidence_levels_do_not_certify_each_other(self):
        section = self.stability_section()
        for term in ("macOS", "Windows", "VM", "VPS", "实际目标", "子进程",
                     "自启", "启动顺序", "持久化源", "生成配置", "配置修订",
                     "规则声明", "应用已载入", "目标进程实际采用", "端到端观察",
                     "check", "inventory", "回执", "不能代替", "curl", "保存许可"):
            self.assertIn(term, section)
        self.assertIn("继承变量不证明采用", section)
        self.assertIn("回执不证明应用载入或网络生效", section)
        self.assertIn("只修改生成配置可能被", section)

    def test_failure_policy_uses_current_scope_and_explicit_exceptions(self):
        section = self.stability_section()
        for term in ("IPv4_ONLY", "禁止直连", "未经批准的备用出口", "IPv6 fallback",
                     "代理到目标", "Codex", "独立恢复通道", "其他应用",
                     "系统 IPv6", "内网／VPN", "回环", "组织规则", "明确例外"):
            self.assertIn(term, section)
        self.assertIn("整机强制覆盖未建立仍是 blocker", section)
        self.assertIn("不自动换节点", section)

    def test_lifecycle_and_protocol_observations_keep_uncovered_paths_unknown(self):
        section = self.stability_section()
        for term in ("系统重启", "睡眠唤醒", "换网", "GUI 退出", "内核停止",
                     "订阅更新", "新连接尝试", "独立恢复", "唯一控制通道",
                     "系统解析", "代理核心", "浏览器", "UDP/TCP", "DoH", "DoT",
                     "STUN", "WebRTC", "媒体路径", "AAAA", "ICE", "unknown",
                     "not_run", "not_applicable", "IP 漂移", "住宅", "固定 IP",
                     "提供方", "免封保证"):
            self.assertIn(term, section)
        self.assertIn("旧结论只适用于旧条件", section)
        self.assertIn("无响应不是阻断证明", section)
        self.assertIn("只能支持其实际采样范围", section)

    def test_guidance_grants_no_live_changes_or_continuous_monitoring(self):
        section = self.stability_section()
        for term in ("具体授权", "原值→新值", "备份", "恢复", "PC0", "unsupported",
                     "不新增脚本、守护进程", "不影响现有配置的测试",
                     "不授权真实设置、保存／重载", "逐项", "不声称已执行",
                     "持续监视", "永久守护", "不自动恢复旧许可"):
            self.assertIn(term, section)
        self.assertIn("暂停依赖步骤", section)
        self.assertNotRegex(section, r"```(?:sh|bash|shell|ya?ml)\b")
        self.assertNotRegex(section, r"(?i)(?:curl|wget)[^\n]*\|\s*(?:sudo\s+)?(?:sh|bash)")


class WholeDevicePathGuidanceContracts(unittest.TestCase):
    """Dated prose scope contracts, not new routing or enforcement capability."""

    @classmethod
    def setUpClass(cls):
        cls.guide = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        cls.skill = (REFS.parent / "SKILL.md").read_text(encoding="utf-8")
        cls.network = (REFS / "network-and-remedies.md").read_text(encoding="utf-8")
        cls.routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")

    def current_policy(self):
        match = re.search(
            r'<a id="ipv4-only-policy"></a>\n'
            r'## 现行整机统一路径与明确例外（2026-10-19）\n(.*?)'
            r'(?=\n### PRODUCT-IPV4-20261018：旧兼容规划契约)', self.guide, re.S)
        self.assertIsNotNone(match, "The dated whole-device requirement must be explicit")
        return match.group(1)

    def test_current_default_is_whole_device_and_old_outputs_remain_limited(self):
        policy = self.current_policy()
        for term in ("2026-10-19", "优先于", "同一目标电脑", "所有普通应用",
                     "子进程", "后台服务", "VM／WSL／容器", "未知", "不等于已经启用"):
            self.assertIn(term, policy)
        self.assertIn("同一电脑默认统一代理路径", self.skill)
        self.assertIn("references/agent-remediation.md#ipv4-only-policy", self.skill)
        self.assertNotIn("## Claude 目标流量默认仅允许 IPv4", self.skill)
        for term in ("claude_target_application_traffic", "other_applications=unchanged",
                     "不代表整机合规", "不能改写返回字段"):
            self.assertIn(term, self.guide)
        self.assertIn("旧目标范围方法", self.network)
        self.assertIn("不定义现行整机默认", self.network)
        self.assertIn("agent-remediation.md#ipv4-only-policy", self.network)
        self.assertIn("browser-only 不能豁免整机网络要求", self.routes)
        self.assertIn("局部观察示例，不是整机验收", self.routes)
        local_intake = self.routes.split("### L1 ", 1)[1].split("### L2 ", 1)[0]
        self.assertIn("防护机制按整机覆盖需求和具体批准评估", local_intake)
        self.assertNotIn("浏览器-only 跳过开发运行时、CLI、MCP 和系统防火墙安装", local_intake)

    def test_takeover_disclosure_precedes_specific_approval(self):
        policy = self.current_policy()
        for term in ("配置前", "TUN", "接管方式", "受影响应用", "LAN／VPN",
                     "控制连接", "具体批准", "独立恢复", "原值→新值",
                     "TUN 不等于 Clash 的 global 模式", "不天然提供 kill switch",
                     "不影响现有配置的测试", "不授权真实设置、保存／重载"):
            self.assertIn(term, policy)
        self.assertLess(policy.index("配置前"), policy.index("取得具体批准"))
        self.assertIn("PC0", policy)
        self.assertIn("故障演练另行批准", policy)

    def test_application_exceptions_are_explicit_and_separately_verified(self):
        policy = self.current_policy()
        for term in ("用户明确要求", "独立路径", "精确程序", "子进程", "共享运行时",
                     "目的范围", "协议", "地址族", "优先级", "正常与故障", "分别验收",
                     "不能仍称全软件同一路径", "不能从软件名称推断", "撤回或改变"):
            self.assertIn(term, policy)
        self.assertIn("仅 Claude 的窄范围模式", policy)
        self.assertIn("不是旧默认的自动恢复", policy)
        local_network = self.routes.split("### L2 ", 1)[1].split("### L3 ", 1)[0]
        self.assertIn("不得未经具体批准将 Codex 改为 DIRECT", local_network)
        self.assertIn("不能称全软件零旁路", local_network)
        self.assertNotIn("不能改变 Codex 为 DIRECT", local_network)

    def test_bypass_checks_and_infrastructure_exceptions_are_bounded(self):
        policy = self.current_policy()
        for term in ("TCP／UDP／DNS", "DoH", "QUIC", "WebRTC", "有效路由",
                     "TUN 排除", "过滤器", "DIRECT", "fallback", "IPv6 字面地址",
                     "bootstrap", "回环", "DHCP", "局域网", "目的地址范围",
                     "端口", "必要性", "不得无限放行整个代理进程", "引导循环"):
            self.assertIn(term, policy)
        self.assertIn("Codex／救援获准独立直连也必须列为例外", policy)
        self.assertIn("不能声称全软件零旁路", policy)
        self.assertIn("不能因它使用 UDP 或忽略系统代理就自动排除", policy)
        self.assertIn("普通业务域名解析不自动归入 bootstrap 例外", policy)

    def test_ipv4_evidence_and_lifecycle_cannot_claim_unestablished_enforcement(self):
        policy = self.current_policy()
        for term in ("IPv4_ONLY", "IPv6 fallback", "代理上游外层", "逐层明确",
                     "不自动沿用旧目标模式的外层 IPv6 例外", "不直接全局关闭 IPv6",
                     "禁止直连", "未经批准的备用出口", "规则声明", "应用载入",
                     "进程采用", "端到端观察", "同一代理链不保证同一公网 IP",
                     "样本一致只支持", "整机强制覆盖未建立不能 pass",
                     "unknown", "unsupported", "持续保护未建立"):
            self.assertIn(term, policy)
        self.assertIn("#post-repair-stability", policy)
        self.assertIn("不新增脚本、守护进程", policy)
        self.assertNotRegex(policy, r"```(?:sh|bash|shell|ya?ml)\b")


if __name__ == "__main__":
    unittest.main()
