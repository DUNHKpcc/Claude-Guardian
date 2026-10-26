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

    def test_fake_ip_leak_boundaries_and_cache_flush_are_documented(self):
        net = (REFS / "network-and-remedies.md").read_text(encoding="utf-8")
        rem = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        for term in ("fake-ip-filter", "own DoH/DoT", "Fake-IP itself is not"):
            self.assertIn(term, net)
        for term in ("ipconfig /flushdns", "dscacheutil -flushcache", "mDNSResponder", "198.18.0.0/15"):
            self.assertIn(term, rem)

    def test_account_warmup_guidance_is_labelled_community_experience(self):
        section = (REFS / "account-onboarding.md").read_text(encoding="utf-8")
        for term in ("邮箱注册", "Proton", "至少使用 3 天", "至少使用 15 天",
                     "重置卡", "教育邮箱", "合法渠道购买", "不伪造教育邮箱", "新号遇到 KYC", "不承诺免封"):
            self.assertIn(term, section)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/account-onboarding.md", skill)
        self.assertNotIn("社区经验，未经验证", skill)
        self.assertNotIn("保证不封", section)

    def test_owner_sources_are_attached_and_s02_is_first_payment_reference(self):
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("资料随答附带", 1)[1]
        for term in ("sources/S02-ai-payments.md", "第一项", "S03-claude-experience.pdf",
                     "S05-local-protection.md", "S06-macos-cleanup-sanitized.md", "S01-server-glossary.md"):
            self.assertIn(term, section)
        acc = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        for term in ("支付任务的核心参考", "../sources/S02-ai-payments.md", "证据等级", "不推荐", "当前官方页面核对"):
            self.assertIn(term, acc)
        lib = (REFS / "source-library.md").read_text(encoding="utf-8")
        self.assertIn("第一项必须是 S02", lib)
        for link in ("S01-server-glossary.md", "S02-ai-payments.md", "S04-claude-guide.md",
                     "S05-local-protection.md", "S06-macos-cleanup-sanitized.md", "S07-vps-script-catalog.md",
                     "S03-claude-experience.pdf"):
            self.assertTrue((ROOT / "skills" / "claude-guardian" / "sources" / link).exists(), link)

    def test_local_route_egress_ip_options_and_vps_reports_are_wired(self):
        egress = (REFS / "egress-ip-options.md").read_text(encoding="utf-8")
        for term in ("纯净机场 IP", "自建梯", "家宽拼车", "Max", "Pro", "## 推荐", "不代买",
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

    def test_mobile_guidance_is_wired_to_registration_and_in_app_purchase(self):
        mobile = (REFS / "mobile-guidance.md").read_text(encoding="utf-8")
        for term in ("网络出口", "IPv6", "DNS", "WebRTC", "系统时区", "定位权限", "Billing Address",
                     "拔掉 SIM 卡", "S03-claude-experience.pdf", "不承诺免封"):
            self.assertIn(term, mobile)
        self.assertIn("mobile-guidance.md", (REFS / "account-onboarding.md").read_text(encoding="utf-8"))
        acc = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        self.assertGreaterEqual(acc.count("mobile-guidance.md"), 2)
        self.assertIn("mobile-guidance.md", (REFS / "intake.md").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[mobile-guidance.md](references/mobile-guidance.md)", skill)

    def test_vm_guidance_is_wired_and_script_is_sanitized(self):
        vm = (REFS / "vm-guidance.md").read_text(encoding="utf-8")
        for term in ("Omarchy", "macOS", "LAN 独立网卡", "shared NAT", "egress-ip-options.md", "fail-closed",
                     "install-flclash-killswitch.sh", "180 秒", "LAN_NET", "account-onboarding.md", "mobile-guidance.md"):
            self.assertIn(term, vm)
        self.assertIn("vm-guidance.md", (REFS / "routes-and-platforms.md").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[vm-guidance.md](references/vm-guidance.md)", skill)
        vm_row = [l for l in skill.splitlines() if l.startswith("| VM 路线")][0]
        for link in ("vps-recommendations/INDEX.md", "S07-vps-script-catalog.md", "install-flclash-killswitch.sh"):
            self.assertIn(link, vm_row)
        vps_row = [l for l in skill.splitlines() if l.startswith("| VPS 路线（开发机")][0]
        for link in ("vps-guard.sh", "install-flclash-killswitch.sh"):
            self.assertIn(link, vps_row)
        self.assertIn("assets/webrtc-probe.html", skill)
        script = (ROOT / "skills" / "claude-guardian" / "assets" / "vm-killswitch" / "install-flclash-killswitch.sh").read_text(encoding="utf-8")
        for personal in ("165.254", "10.72.18", "dpccskisw"):
            self.assertNotIn(personal, script)
        for term in ("flclash_killswitch", "policy drop", "LAN_NET", "EXPECTED_EXIT_IP", "apply_armed"):
            self.assertIn(term, script)
        for name, terms in (("install-flclash-tun.sh", ("sha256sum", "Checksum verification failed", "FLCLASH_VERSION", "ARCH")),
                            ("enable-guest-ssh.sh", ("SSH_SRC", "sshd -t", "ufw allow in on"))):
            body = (ROOT / "skills" / "claude-guardian" / "assets" / "vm-killswitch" / name).read_text(encoding="utf-8")
            for term in terms:
                self.assertIn(term, body, name)
            self.assertNotIn("dpccskisw", body, name)
        vm_doc = (REFS / "vm-guidance.md").read_text(encoding="utf-8")
        for term in ("enable-guest-ssh.sh", "install-flclash-tun.sh", "3a. Linux 客机的搭建顺序", "再装防火墙"):
            self.assertIn(term, vm_doc)

    def test_advanced_route_is_an_overlay_with_sanitized_scripts_and_shared_fixes(self):
        skill_root = ROOT / "skills" / "claude-guardian"
        adv = (REFS / "advanced-route.md").read_text(encoding="utf-8")
        for term in ("反向隧道", "fail-closed", "KillMode=process", "permitlisten=127.0.0.1:2222", "不是第四种环境",
                     "管理通道自身的出站", "table 2022", "VPS 单点", "C 档", "180 秒保险丝"):
            self.assertIn(term, adv)
        routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")
        card = routes.split("## R-ADV 进阶路线卡", 1)[1].split("## 来源与维护", 1)[0]
        for term in ("不新增路线值", "PC0", "PC1/PC2", "验收", "恢复", "批准", "C 档"):
            self.assertIn(term, card)
        for index in range(1, 5):
            self.assertRegex(card, rf"(?m)^### A{index} ")
        skill = (skill_root / "SKILL.md").read_text(encoding="utf-8")
        adv_row = [l for l in skill.splitlines() if l.startswith("| 进阶路线")][0]
        for link in ("advanced-route.md", "install-reverse-tunnel.sh", "flclash-crash-heal.sh", "install-flclash-killswitch.sh"):
            self.assertIn(link, adv_row)
        for name in ("install-reverse-tunnel.sh", "flclash-crash-heal.sh"):
            body = (skill_root / "assets" / "remote-hardening" / name).read_text(encoding="utf-8")
            for personal in ("128.241", "dpccskisw", "omarchy_tunnel_key", "BEGIN OPENSSH", "LS0tLS1CRUdJTiBPUEVOU1NI"):
                self.assertNotIn(personal, body, name)
        tunnel = (skill_root / "assets" / "remote-hardening" / "install-reverse-tunnel.sh").read_text(encoding="utf-8")
        for term in ("KEY_PATH", "chown", "600", "ExitOnForwardFailure=yes", "VPS_HOST 必须是 IPv4"):
            self.assertIn(term, tunnel)
        heal = (skill_root / "assets" / "remote-hardening" / "flclash-crash-heal.sh").read_text(encoding="utf-8")
        for term in ("KillMode=process", "DBUS_SESSION_BUS_ADDRESS", "ExecStartPre=+", "TUN 不存在"):
            self.assertIn(term, heal)
        # Shared fixes live in the VM/VPS guidance and scripts, not only in the advanced route.
        vm = (REFS / "vm-guidance.md").read_text(encoding="utf-8")
        for term in ("GLOBAL", "TUNNEL_UNIT", "priority 用 10", "198.18.0.0/15", "ip rule show", "ip -6 addr show scope global",
                     "NTP", "FLCLASH_HELPER_OWNER_UID", "libayatana-indicator"):
            self.assertIn(term, vm)
        ks = (skill_root / "assets" / "vm-killswitch" / "install-flclash-killswitch.sh").read_text(encoding="utf-8")
        for term in ("TUNNEL_UNIT", "tunnel4", "tunnel_ports"):
            self.assertIn(term, ks)
        tun = (skill_root / "assets" / "vm-killswitch" / "install-flclash-tun.sh").read_text(encoding="utf-8")
        for term in ("FLCLASH_HELPER_OWNER_UID", "RuntimeDirectory=flclash"):
            self.assertIn(term, tun)
        vps = (REFS / "vps-guidance.md").read_text(encoding="utf-8")
        for term in ("ClientAliveInterval 15", "permitlisten=127.0.0.1:2222", "advanced-route.md"):
            self.assertIn(term, vps)

    def test_vps_route_is_a_dev_machine_with_consistent_environment(self):
        vps = (REFS / "vps-guidance.md").read_text(encoding="utf-8")
        for term in ("开发机", "环境一致", "Ubuntu 24.04", "x86_64", "S08-vps-claude-tutorial.pdf",
                     "R02-vps-line-optimization.md", "vps-guard.sh", "install-flclash-killswitch.sh", "180 秒保险丝",
                     "5900 和 6080 绝不直接开放到公网", "不要把本机浏览器和 VPS 混用", "egress-ip-options.md", "account-onboarding.md"):
            self.assertIn(term, vps)
        routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")
        self.assertIn("P1a 系统、环境一致、出口与防火墙", routes)
        self.assertIn("属于本机路线选 IP 出口的选项", routes)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("[vps-guidance.md](references/vps-guidance.md)", skill)
        vps_row = [l for l in skill.splitlines() if l.startswith("| VPS 路线（开发机")][0]
        for link in ("S08-vps-claude-tutorial.pdf", "R02-vps-line-optimization.md", "vps-recommendations/INDEX.md", "S07-vps-script-catalog.md"):
            self.assertIn(link, vps_row)
        root = ROOT / "skills" / "claude-guardian"
        for rel in ("sources/S08-vps-claude-tutorial.pdf", "sources/S08-extracted-text.md",
                    "sources/R02-vps-line-optimization.md", "sources/S03-source-text.md"):
            self.assertTrue((root / rel).is_file(), rel)
        guard = (root / "assets" / "vps-firewall" / "vps-guard.sh").read_text(encoding="utf-8")
        for term in ("vps_guard", "policy drop", "ADMIN_NET", "180", "render"):
            self.assertIn(term, guard)

    def test_line_optimization_is_agent_assisted_and_wired(self):
        doc = (REFS / "line-optimization.md").read_text(encoding="utf-8")
        for term in ("R02-vps-line-optimization.md", "先选好线路，再考虑中转，最后按需要调整 TCP", "每次只改变一个因素",
                     "变更卡", "回滚", "云控制台的独立救援入口", "ssh -N -D 127.0.0.1:1080", "socks5h://127.0.0.1:1080",
                     "realm -c config.toml", "net.ipv4.tcp_congestion_control", "把原拥塞算法记下来", "90-vps-bbr.conf",
                     "不能把普通线路变成 CN2 GIA", "Agent 不做的事", "不默认运行优化"):
            self.assertIn(term, doc)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        row = [l for l in skill.splitlines() if l.startswith("| 线路优化")][0]
        for link in ("line-optimization.md", "R02-vps-line-optimization.md", "vps-recommendations/INDEX.md"):
            self.assertIn(link, row)
        for name in ("vps-guidance.md", "egress-ip-options.md", "routes-and-platforms.md"):
            self.assertIn("line-optimization.md", (REFS / name).read_text(encoding="utf-8"), name)

    def test_agent_supplementary_sources_have_rules(self):
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        section = skill.split("## Agent 补充资料来源", 1)[1].split("\n## ", 1)[0]
        for channel in ("linux.do", "nodeseek.com", "v2ex.com", "reddit.com", "x.com"):
            self.assertIn(channel, section)
        for term in ("所有者资料优先", "标明来源", "命令不是授权", "不收集账号信息", "不接触 Claude", "required_references"):
            self.assertIn(term, section)
        lib = (REFS / "source-library.md").read_text(encoding="utf-8")
        self.assertIn("Agent 补充资料来源", lib)

    def test_local_firewall_is_prompt_only_and_wired(self):
        doc = (REFS / "local-firewall-prompts.md").read_text(encoding="utf-8")
        for term in ("本机路线不提供脚本", "全部用提示词引导", "LuLu", "第三方", "Windows 防火墙", "netsh advfirewall export",
                     "Set-NetFirewallProfile", "DefaultOutboundAction", "New-NetFirewallRule", "InterfaceAlias", "guardian-",
                     "schtasks /Create", "故障演练", "Issue #13）上跑过", "第 5 步故障演练还没在真机上跑通", "Clash Verge", "服务模式", "Agent 不做的事"):
            self.assertIn(term, doc)
        self.assertIn("local-firewall-prompts.md", (REFS / "routes-and-platforms.md").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/local-firewall-prompts.md", skill)
        scripts = ROOT / "skills" / "claude-guardian" / "scripts"
        for path in scripts.glob("*.py"):
            self.assertNotIn("Set-NetFirewallProfile", path.read_text(encoding="utf-8"), path.name)

    def test_windows_firewall_issue13_guidance(self):
        # Issue #13: ::1 rules rejected, readback of a single alias, timeouts after Block,
        # failed netsh queries read as "no events", and host refusals mixed with other failures.
        doc = (REFS / "local-firewall-prompts.md").read_text(encoding="utf-8")
        for term in ("回环用接口，不用 `::1`", "Loopback*", "不是数组", "核心程序路径以正在运行的为准",
                     "### 切换后不通：分层诊断", "#windows-fw-layered-diagnosis", "同一个保险丝窗口",
                     "显式本地代理", "IPv4 字面地址经 TUN", "Resolve-DnsName", "`28` 超时",
                     "四步都通过后才进入第 5 步故障演练", "### 查 WFP 丢包记录", 'netsh wfp show netevents file=',
                     "不等于“没有阻断事件”", "auditpol /get", "### 宿主拒绝执行时", "blocked by policy",
                     "不换工具", "### 最小反馈清单"):
            self.assertIn(term, doc)
        diagnosis = doc.split("### 切换后不通：分层诊断", 1)[1].split("\n### ", 1)[0]
        self.assertLess(diagnosis.index("显式本地代理"), diagnosis.index("IPv4 字面地址经 TUN"))
        self.assertLess(diagnosis.index("IPv4 字面地址经 TUN"), diagnosis.index("Resolve-DnsName"))

    def test_readme_is_not_defensive(self):
        # The README states what the project does; boundaries live in one short list.
        for name, heading, dropped in (
                ("README.md", "## 几条底线", ("## 它不是什么", "## 核心场景", "## 工作流与门禁机制",
                                             "### 开始前要知道", "不是已完成检查或修复的演示结果",
                                             "加载受第三方服务可用性影响")),
                ("README.en.md", "## Ground rules", ("## What it is not", "## Core scenarios", "## Workflow and gates",
                                                    "### Before you start", "not demonstrations of completed",
                                                    "depends on that third-party service"))):
            body = (ROOT / name).read_text(encoding="utf-8")
            self.assertIn(heading, body, name)
            for text in dropped:
                self.assertNotIn(text, body, name)
            for link in ("authorization-tiers.md", "local-firewall-prompts.md", "windows-cleanup.md",
                         "contact-and-safety.md", "device-report.yml"):
                self.assertIn(link, body, name)

    def test_kyc_ip_consistency_and_pro_abandon_rule(self):
        # Owner 2026-10-25: KYC checks the IP; a mismatch with payment/usage raises risk; Pro hit by KYC later: abandon.
        payments = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        a3 = payments.split("### A3 ", 1)[1].split("\n## ", 1)[0]
        for term in ("KYC 会检查 IP", "支付、日常使用环境不一致", "network_check.py run", "Pro 用了一段时间后才遇到 KYC，直接弃号"):
            self.assertIn(term, a3)
        onboarding = (REFS / "account-onboarding.md").read_text(encoding="utf-8")
        for term in ("KYC 会检查 IP", "Pro 用了一段时间后遇到 KYC，直接弃号"):
            self.assertIn(term, onboarding)

    def test_self_built_proxy_checks_client_compatibility(self):
        # Owner 2026-10-25: desktop Clash Verge connecting while Shadowrocket/FlClash fail must not happen.
        doc = (REFS / "egress-ip-options.md").read_text(encoding="utf-8")
        section = doc.split("## 自建梯提示词（简版）", 1)[1].split("\n## ", 1)[0]
        for term in ("重点注意版本兼容性", "桌面端 Clash Verge 能连上、移动端小火箭和 FlClash 连不上",
                     "用户所有客户端都支持", "每一个客户端", "只测了桌面端不算"):
            self.assertIn(term, section)

    def test_trace_and_linux_cleanup_follow_owner_decisions(self):
        # Owner 2026-10-25: proxy/VPN logs and IP-lookup shell lines; only those lines; ask before moving
        # conversation records (recommend yes); debug is regenerable; Linux covered; no mobile this round.
        trace = (REFS / "trace-cleanup.md").read_text(encoding="utf-8")
        for term in ("io.github.clash-verge-rev.clash-verge-rev/logs", "log-level: warning", "VPN 客户端日志",
                     "只删查 IP 的命令", "unset HISTFILE", "grep -a -i -v -E", "history delete --contains",
                     "HistorySavePath", "ClearHistory()", "ipinfo\\.io", "保险起见建议移走", "系统日志",
                     "C 档", "隔离目录"):
            self.assertIn(term, trace)
        self.assertNotIn("Shadowrocket", trace)
        linux = (REFS / "linux-cleanup.md").read_text(encoding="utf-8")
        for term in ("~/.cache/claude-cli-nodejs", "`debug`", "保险起见建议移走", "$CLAUDECODE", "diff -r",
                     "~/.claude/.credentials.json", "trace-cleanup.md"):
            self.assertIn(term, linux)
        windows = (REFS / "windows-cleanup.md").read_text(encoding="utf-8")
        self.assertIn("调试日志 `debug`", windows)
        protected = windows.split("**始终保护，不进入任何清理范围：**", 1)[1].split("\n", 1)[0]
        for name in ("`projects`", "`history.jsonl`", "`debug`"):
            self.assertNotIn(name, protected)
        self.assertIn("保险起见建议移走", windows)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        for name in ("references/trace-cleanup.md", "references/linux-cleanup.md", "保险起见建议移走"):
            self.assertIn(name, skill)

    def test_skill_md_tells_the_agent_how_to_talk(self):
        # Owner 2026-10-25: the Agent echoed "不保证/不成立/不改变/不背书" back to users.
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        voice = skill.split("## 和用户说话的方式（先读这一节）", 1)[1].split("\n## ", 1)[0]
        self.assertLess(skill.index("## 和用户说话的方式"), skill.index("## 开始方式"))
        for term in ("写给你执行的规则，不是念给用户听的台词", "不说这些句式", "免封只在用户问到时说一次",
                     "所有者的经验按事实直接说", "已确认 / 还没查 / 下一步"):
            self.assertIn(term, voice)
        rest = skill.replace(voice, "")
        for hedge in ("不保证", "不成立", "不代表", "不等于", "不构成", "不证明", "不承诺", "背书", "不宣称", "不推定", "不断言"):
            self.assertNotIn(hedge, rest, hedge)

    def test_dashboard_and_action_strings_do_not_lecture(self):
        scripts = ROOT / "skills" / "claude-guardian" / "scripts"
        for name in ("status_dashboard.py", "agent_remediation.py", "probe_evidence.py"):
            body = (scripts / name).read_text(encoding="utf-8")
            for hedge in ("不证明", "不代表", "不等于", "不宣称", "不是完整阻断证明"):
                self.assertNotIn(hedge, body, (name, hedge))

    def test_beginner_combo_is_stated_directly(self):
        # Owner fact 2026-10-25: the beginner combo and the phone-then-KYC-within-24h verdict.
        doc = (REFS / "account-onboarding.md").read_text(encoding="utf-8")
        section = doc.split("## A0a：新手试错推荐组合", 1)[1].split("\n## ", 1)[0]
        for term in ("苹果内购", "Gmail 或 Outlook", "VPS 纯净个人 IP", "VM 或本机", "**Pro**",
                     "退款成功率高、稳定率高", "24 小时内又要 KYC", "基本宣判死刑"):
            self.assertIn(term, section)
        for hedge in ("单例", "未核实", "只是推测", "稳妥做法", "不承诺"):
            self.assertNotIn(hedge, section)
        self.assertIn("基本宣判死刑", doc.split("## A0a", 1)[0])
        self.assertIn("account-onboarding.md#a0a", (REFS / "accounts-and-payments.md").read_text(encoding="utf-8"))
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("references/account-onboarding.md#a0a", skill)

    def test_no_touch_rules_live_in_their_modules(self):
        # Owner rule 2026-10-25: no 代充 (payment B1), no low-quality KYC 代过 (A3), no 成品号/成品邮箱 (A0).
        pay = (REFS / "accounts-and-payments.md").read_text(encoding="utf-8")
        b1 = pay.split("### B1 ", 1)[1].split("\n### ", 1)[0]
        a3 = pay.split("### A3 ", 1)[1].split("\n### ", 1)[0]
        self.assertIn("**不碰代充", b1)
        self.assertIn("**不碰低质量的 KYC 代过", a3)
        onboarding = (REFS / "account-onboarding.md").read_text(encoding="utf-8")
        a0 = onboarding.split("## A0a", 1)[0]
        self.assertIn("**不碰成品号、成品邮箱", a0)
        for section in (b1, a3, a0):
            for hedge in ("单例", "未核实", "只是推测", "稳妥做法"):
                self.assertNotIn(hedge, section)

    def test_host_library_contracts_live_outside_skill_md(self):
        # ADR-044: SKILL.md is loaded on every run; the library contracts are read on demand.
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        libs = (REFS / "host-libraries.md").read_text(encoding="utf-8")
        self.assertLess(len(skill.encode("utf-8")), 32000)
        self.assertIn("## 内置脚本与宿主库", skill)
        self.assertIn("references/host-libraries.md", skill)
        self.assertNotIn("当前尚无开放的内置生产配置写入适配器", skill)
        for heading in ("## Agent内部修复入口（按动作能力分流）", "## 限定静态盘点入口", "## 本地环境状态面板",
                        "### 私有配置候选（不可应用）", "## 环境入口校验", "## 旧目标范围契约与整机结论",
                        '<a id="environment-entry"></a>', '<a id="prepared-recovery"></a>', "## C5：限定清理宿主交接"):
            self.assertIn(heading, libs)
            self.assertNotIn(heading, skill)
        for term in ("NATIVE_REPAIR_ADAPTER_UNAVAILABLE", "guardian-retained-repair/0.3", "restore-prepared",
                     "apply_supported始终false", "不能 pass", "cleanup_cli.main"):
            self.assertIn(term, libs)

    def test_guides_do_not_understate_recorded_real_device_runs(self):
        # ADR-039 recorded a real Mac `established` run; Issue #13 ran Windows firewall steps 1-4.
        egress = (REFS / "whole-machine-ipv4.md").read_text(encoding="utf-8")
        self.assertNotIn("没有在真实设备上跑过", egress)
        self.assertIn("ADR-039", egress)
        firewall = (REFS / "local-firewall-prompts.md").read_text(encoding="utf-8")
        self.assertNotIn("没有在真实机器上实测", firewall)
        # 3a032dc removed the firewall "不承诺" disclaimer on purpose.
        self.assertNotIn("不承诺免封", firewall)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        header = skill.split("## 开始方式", 1)[0]
        for text in ("有限只读检查", "仍有未验收项", "不是默认执行权限"):
            self.assertNotIn(text, header)

    def test_s08_screenshots_ip_report_and_macos_guest_are_covered(self):
        root = ROOT / "skills" / "claude-guardian"
        text = (root / "sources" / "S08-extracted-text.md").read_text(encoding="utf-8")
        for term in ("## 截图说明", "IP.Check.Place", "LazyVim", "Remote - SSH", "黑名单"):
            self.assertIn(term, text)
        vps = (REFS / "vps-guidance.md").read_text(encoding="utf-8")
        for term in ("## 怎么读 IP 检测报告", "风险评分", "风险因子", "邮局连通性及黑名单", "不推导免封概率"):
            self.assertIn(term, vps)
        vm = (REFS / "vm-guidance.md").read_text(encoding="utf-8")
        for term in ("### macOS 客机", "远程登录", "local-firewall-prompts.md#mac", "不自己写 PF 规则"):
            self.assertIn(term, vm)
        for path in (ROOT / "README.md",):
            body = path.read_text(encoding="utf-8")
            self.assertNotIn("acceptance-rebuild-ledger.json)", body, path.name)
            self.assertNotIn("docs/evidence/rebuild-inventory-export-boundaries.md", body, path.name)

    def test_r02_images_resolve_and_validation_log_is_gone(self):
        root = ROOT / "skills" / "claude-guardian" / "sources"
        r02 = (root / "R02-vps-line-optimization.md").read_text(encoding="utf-8")
        self.assertNotIn("![[", r02)
        for rel in ("R02-images/single-relay.png", "R02-images/dual-tunnel.png"):
            self.assertIn(rel, r02)
            self.assertTrue((root / rel).is_file(), rel)
        import re
        for target in re.findall(r"\]\((vps-recommendations/[^)]+)\)", r02):
            self.assertTrue((root / target).is_file(), target)
        self.assertFalse((ROOT / "docs" / "validation.md").exists())
        for path in [ROOT / "README.md"] + sorted((ROOT / "docs").glob("*.md")):
            if path.name == "decisions.md":
                continue
            self.assertNotIn("](validation.md)", path.read_text(encoding="utf-8"), path.name)

    def test_authorization_tiers_are_defined_and_wired(self):
        doc = (REFS / "authorization-tiers.md").read_text(encoding="utf-8")
        for term in ("范围确认单", "A 范围内自行做", "B 整个计划批准一次", "C 必须当场确认", "判定方法", "计划批准单", "确认单",
                     "用户**不需要全程在场**", "不变的硬规则", "沉默、超时、默认选项都不算确认", "持久化改内核参数",
                     "默认出站切成阻止", "注册、登录、KYC、OAuth、付款、订阅、凭据"):
            self.assertIn(term, doc)
        agents = (ROOT / "AGENTS.md").read_text(encoding="utf-8")
        self.assertIn("authorization-tiers.md", agents)
        self.assertNotIn("取得本次授权；不能靠代码中的布尔值替代真实确认", agents)
        for name in ("contact-and-safety.md", "agent-remediation.md", "local-firewall-prompts.md",
                     "line-optimization.md", "vm-guidance.md", "vps-guidance.md"):
            self.assertIn("authorization-tiers.md", (REFS / name).read_text(encoding="utf-8"), name)
        skill = (ROOT / "skills" / "claude-guardian" / "SKILL.md").read_text(encoding="utf-8")
        self.assertIn("## 授权档位", skill)
        self.assertIn("[authorization-tiers.md](references/authorization-tiers.md)（必附）", skill)

    def test_authorization_records_are_documented(self):
        doc = (REFS / "authorization-tiers.md").read_text(encoding="utf-8")
        for term in ("状态机里的可追溯记录", "record_scope_confirmation", "record_plan_approval", "use_critical_confirmation",
                     "user:", "user_performs_this", "永久的", "不复活"):
            self.assertIn(term, doc)
        self.assertNotIn("目前没有写进状态机", doc)
        self.assertIn("authorization", (REFS / "intake.md").read_text(encoding="utf-8"))

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
                     "不能指向宿主代理", "S08"):
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
            self.assertIn("官方", body)
            self.assertNotIn("sources/design", body)
        self.assertIn("S02", self.accounts)
        self.assertIn("所有者提供的资料", self.incidents)

    def test_guides_are_not_remote_execution_scripts(self):
        # A prose runbook must not embed unchecked fetch-and-execute commands.
        for body in (self.routes, self.accounts, self.incidents):
            self.assertNotRegex(body, r"(?i)(?:curl|wget)[^\n]*\|\s*(?:sudo\s+)?(?:sh|bash)")
            self.assertNotRegex(body, r"(?m)^\s*(?:TODO|TBD|FIXME)\s*[:：]")


class RemediationGuideContracts(unittest.TestCase):
    """agent-remediation.md after ADR-048: short, practical, IPv4-only with Windows adapter IPv6 off."""

    @classmethod
    def setUpClass(cls):
        cls.guide = (REFS / "agent-remediation.md").read_text(encoding="utf-8")
        cls.skill = (REFS.parent / "SKILL.md").read_text(encoding="utf-8")
        cls.network = (REFS / "network-and-remedies.md").read_text(encoding="utf-8")
        cls.routes = (REFS / "routes-and-platforms.md").read_text(encoding="utf-8")

    def section(self, anchor):
        return self.guide.split('<a id="%s"></a>' % anchor, 1)[1].split("\n## ", 2)[1]

    def test_guide_is_short_and_has_no_dead_sections(self):
        self.assertLess(len(self.guide.encode("utf-8")), 16000)
        for gone in ("ENV-06", "PRODUCT-IPV4-20261018", "/0.2 入口", "尚未实现", "network_probes",
                     "diagnostic_session", "os_dns_probe", "不整机关闭 IPv6"):
            self.assertNotIn(gone, self.guide)
        for anchor in ("post-repair-stability", "ipv4-only-policy", "windows-adapter-ipv6-hint"):
            self.assertEqual(self.guide.count('<a id="%s"></a>' % anchor), 1)
        self.assertIn("references/agent-remediation.md#ipv4-only-policy", self.skill)

    def test_loop_detects_with_network_check_and_retests(self):
        loop = self.guide.split("## 一次任务的闭环", 1)[1].split('<a id="post-repair-stability"></a>', 1)[0]
        for term in ("guardian.py check", "network_check.py run", "agent_remediation.py select", "原值→新值",
                     "读回", "复测", "不覆盖用户后来的修改"):
            self.assertIn(term, loop)

    def test_post_repair_checks(self):
        section = self.section("post-repair-stability")
        for term in ("自启", "持久化源", "四层", "睡眠唤醒", "换网", "--failure-drill", "唯一的控制通道",
                     "serve_webrtc.py", "IP 漂移", "ipconfig /flushdns", "dscacheutil -flushcache", "198.18.0.0/15"):
            self.assertIn(term, section)

    def test_ipv4_only_policy(self):
        policy = self.section("ipv4-only-policy")
        for term in ("所有普通应用", "子进程", "后台服务", "DoH", "QUIC", "WebRTC", "不直连", "ipv6: false",
                     "Windows 默认关闭网卡 IPv6", "不回退到 IPv6", "TUN 和 Clash 的 global 模式是两回事",
                     "用户明确要求的例外", "窄范围模式", "DHCP", "egress_verifier.py"):
            self.assertIn(term, policy)
        self.assertIn("同一电脑默认统一代理路径", self.skill)
        self.assertIn("agent-remediation.md#ipv4-only-policy", self.network)
        self.assertIn("browser-only 不能豁免整机网络要求", self.routes)

    def test_windows_adapter_ipv6_is_off_by_default(self):
        section = self.section("windows-adapter-ipv6-hint")
        for term in ("默认关闭", "B 档", "Get-NetAdapterBinding", "Disable-NetAdapterBinding",
                     "Enable-NetAdapterBinding", "ms_tcpip6", "ncpa.cpl", "记原值", "虚拟网卡", "组织管理",
                     "network_check.py run"):
            self.assertIn(term, section)
        scripts = ROOT / "skills" / "claude-guardian" / "scripts"
        for path in scripts.glob("*.py"):
            self.assertNotIn("Disable-NetAdapterBinding", path.read_text(encoding="utf-8"), path.name)


if __name__ == "__main__":
    unittest.main()
