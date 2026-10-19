"""Offline documentation regressions; not native or network acceptance."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / 'skills/claude-guardian/references/agent-remediation.md').read_text(encoding='utf-8')


class NeutralProbeGuidanceTests(unittest.TestCase):
    def test_explicit_version_and_old_plan_boundary(self):
        self.assertIn('受控中性 HTTPS 样本的 /0.2 入口', GUIDE)
        self.assertIn('旧保存计划不会自动升级', GUIDE)
        self.assertIn('configuration 和 PC1／PC2 接触继续要求原严格条件', GUIDE)

    def test_unknown_route_is_sample_not_direct_or_machine_proof(self):
        self.assertIn('direct_socket_os_route_tun_unknown', GUIDE)
        self.assertIn('不宣称绕开 TUN 或确为直连', GUIDE)
        self.assertIn('single_context_sample_not_whole_machine', GUIDE)
        self.assertIn('浏览器路径未观察', GUIDE)

    def test_trusted_host_and_unsupported_paths_are_explicit(self):
        self.assertIn('默认没有可信 reader 时拒绝', GUIDE)
        self.assertIn('不是独立身份验证', GUIDE)
        self.assertIn('explicit_proxy` 未新增内置执行器', GUIDE)
        self.assertIn('browser、未适配的 DNS／诊断入口不因 /0.2 获得能力', GUIDE)

    def test_permissions_and_post_send_changes_remain_truthful(self):
        self.assertIn('approved_proxy_endpoints', GUIDE)
        self.assertIn('不能代替地址许可', GUIDE)
        self.assertIn('request_count=1', GUIDE)
        self.assertIn('不声称零请求、不自动重试', GUIDE)

    def test_diagnostics_do_not_claim_identity_or_clean_shutdown(self):
        self.assertIn('CONTEXT_UNKNOWN', GUIDE)
        self.assertIn('console_user/null_result', GUIDE)
        self.assertIn('清理失败不能称监听器或全部连接已经关闭', GUIDE)
        self.assertIn('服务退出或超时不会撤销页面已发出的 STUN', GUIDE)
        self.assertIn('诊断改进不等于已修好原生根因', GUIDE)
