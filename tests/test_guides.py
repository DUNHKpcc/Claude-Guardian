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


if __name__ == "__main__":
    unittest.main()
