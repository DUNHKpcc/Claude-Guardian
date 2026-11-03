"""Public case completeness and routing, not Windows device acceptance."""
import ipaddress
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian'
CASE = 'sources/S10-windows-deployment-sanitized.md'


class WindowsDeploymentSourceTests(unittest.TestCase):
    def test_full_case_retains_both_deployments_and_the_launcher_postmortem(self):
        text = (ROOT / CASE).read_text(encoding='utf-8')
        sections = re.findall(r'^## ([一二三四五六七八九十]+)、', text, re.MULTILINE)
        self.assertEqual(sections, ['一', '二', '三', '四', '五', '六', '七', '八', '九', '十', '十一'])
        for section in ('# 第二台机器', '# 桌面开关重大缺陷复盘', '## 方法学教训',
                        '## 影响范围', '## 友好版标准配方', '## 六、当前状态与待办',
                        '## 十一、node 机器状态与待办'):
            self.assertIn(section, text)
        self.assertIn('$ws.CreateShortcut', text)
        self.assertIn('Start-Process explorer.exe', text)

    def test_public_copy_has_only_example_addresses_and_user_aliases(self):
        text = (ROOT / CASE).read_text(encoding='utf-8')
        self.assertIn('[REDACTED_SECRET]', text)
        self.assertNotRegex(text, r'/Users/[^\s/]+')
        users = re.findall(r'C:\\Users\\([^\\\s`]+)', text)
        self.assertTrue(users)
        self.assertEqual(set(users), {'USER_A', 'USER_B'})
        examples = (ipaddress.ip_network('203.0.113.0/24'), ipaddress.ip_network('198.18.0.0/15'))
        for literal in re.findall(r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)', text):
            address = ipaddress.ip_address(literal)
            self.assertTrue(any(address in net for net in examples) or
                            literal in {'100.64.0.10', '100.64.0.11'}, literal)

    def test_version_and_acceptance_limits_are_separate_from_original_observations(self):
        text = (ROOT / CASE).read_text(encoding='utf-8')
        for term in ('编者注', '全系不兼容', '不能据此证明所有版本', '默认关闭',
                     'webrtc: no_leak', '`not_run`', '组策略', '没有重新连接设备',
                     '重启、睡眠唤醒、换网', '不代表无特权执行'):
            self.assertIn(term, text)
        manifest = json.loads((ROOT / 'sources/manifest.json').read_text(encoding='utf-8'))
        record = next(source for source in manifest['sources'] if source['id'] == 'S10')
        self.assertEqual(record['path'], CASE)
        self.assertNotEqual(record['original_sha256'], record['distributed_sha256'])
        self.assertTrue(record['changes'])
        self.assertTrue(record['limitations'])

    def test_guides_route_to_the_relevant_case_sections(self):
        text = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        self.assertIn('(' + CASE + ')', text)
        for guide, anchors in (
                ('local-firewall-prompts.md', ('windows-ssh', 'powershell-tools',
                                               'windows-firewall', 'tun-firewall-lifecycle', 'desktop-launcher')),
                ('whole-machine-ipv4.md', ('verge-runtime', 'network-evidence')),
                ('egress-ip-options.md', ('vps-protocols', 'verge-runtime'))):
            body = (ROOT / 'references' / guide).read_text(encoding='utf-8')
            for anchor in anchors:
                self.assertIn('../' + CASE + '#' + anchor, body)
        delivery = (ROOT / 'references/local-firewall-prompts.md').read_text(encoding='utf-8')
        for term in ('三个配置文件都启用', '其他 Allow 规则', '双击 → UAC → 三档状态读回',
                     '不要求所有交付都开发开关'):
            self.assertIn(term, delivery)


if __name__ == '__main__':
    unittest.main()
