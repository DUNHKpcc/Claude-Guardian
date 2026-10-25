"""Issue #12: new search channels, direct forum-search use, and the short-term ban timeline."""
from pathlib import Path
import unittest

ROOT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian'
SKILL = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
ONBOARDING = (ROOT / 'references/account-onboarding.md').read_text(encoding='utf-8')
EGRESS = (ROOT / 'references/egress-ip-options.md').read_text(encoding='utf-8')


class Issue12Sources(unittest.TestCase):
    def test_channels_owner_pointers_and_direct_search_are_documented(self):
        for term in ('IDC Flare', 'https://idcflare.com/', 'https://vpshub.org/zh/', 'VPSHub', '家宽拼车去 IDC Flare 找',
                     '家宽去 Linux.do（L 站）的 VPS 分区找', 'https://linux.do/t/topic/2971757',
                     'https://www.nodeseek.com/post-968032-1', 'https://linux.do/t/topic/585764',
                     '直接当帖子和论坛的搜索工具', 'site:nodeseek.com', 'Cloudflare 验证', '不绕过'):
            self.assertIn(term, SKILL)
        self.assertIn('帖子与论坛搜索工具', SKILL.split('---', 2)[1])
        self.assertIn('IDC Flare', EGRESS)
        self.assertIn('请用户自己上网搜索', EGRESS)  # still no recommendation of specific sellers
        self.assertIn('不推荐具体卖家', EGRESS)

    def test_short_term_ban_timeline_gives_direction_then_evidence(self):
        for term in ('A0b', '注册后几分钟到 1 小时', '开 Pro/Max 后几分钟到当天', '第一次跑 Claude Code 后 0.5 小时到数小时',
                     '注册后 1 到 2 天', '几周到几个月后', '先定排查方向', '查证据定原因'):
            self.assertIn(term, ONBOARDING)

    def test_no_contact_number_is_added_to_authored_docs(self):
        for path in (ROOT / 'references').glob('*.md'):
            self.assertNotIn('1124987353', path.read_text(encoding='utf-8'), path.name)
        self.assertNotIn('1124987353', SKILL)


if __name__ == '__main__':
    unittest.main()
