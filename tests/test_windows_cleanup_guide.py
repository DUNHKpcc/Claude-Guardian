"""Windows cleanup prompts: official paths present, protected set intact, no identity rotation."""
from pathlib import Path
import re
import unittest

ROOT = Path(__file__).resolve().parents[1]
GUIDE = (ROOT / 'skills/claude-guardian/references/windows-cleanup.md').read_text(encoding='utf-8')


class WindowsCleanupGuide(unittest.TestCase):
    def test_official_windows_paths_and_sources_are_cited(self):
        for term in (r'%USERPROFILE%\.claude', r'%USERPROFILE%\.claude.json', r'%USERPROFILE%\.claude\.credentials.json',
                     r'%USERPROFILE%\.local\bin\claude.exe', r'%USERPROFILE%\.local\share\claude',
                     r'%APPDATA%\Code\User\globalStorage\anthropic.claude-code', r'%APPDATA%\Anthropic',
                     r'%APPDATA%\Claude\claude_desktop_config.json', r'%APPDATA%\Claude\logs',
                     'https://code.claude.com/docs/en/claude-directory', 'https://code.claude.com/docs/en/setup',
                     'https://code.claude.com/docs/en/authentication',
                     'https://support.claude.com/en/articles/12622703-deploy-claude-desktop-for-windows',
                     'https://modelcontextprotocol.io/docs/develop/connect-local-servers'):
            self.assertIn(term, GUIDE)

    def test_protected_set_tiers_and_boundaries_are_stated(self):
        for term in ('始终保护', 'projects', 'history.jsonl', 'settings.json', 'skills', 'plugins', '.credentials.json',
                     '可再生', '桌面端持久数据', 'claude_desktop_config.json', '没有内置清理宿主',
                     '没有在真实 Windows 机器上跑过', '-WhatIf', 'C 档', '不永久删除', '官方没有写出的'):
            self.assertIn(term, GUIDE)
        self.assertIn('Move-Item', GUIDE)
        self.assertIn('Get-FileHash', GUIDE)
        self.assertIn('-Depth 100', GUIDE)

    def test_no_identity_rotation_or_unsafe_deletion_is_offered(self):
        self.assertIn('不轮换设备标识', GUIDE)
        code = '\n'.join(re.findall(r'```powershell\n(.*?)```', GUIDE, re.S))
        for forbidden in ('Remove-Item', 'userID', 'machineID', 'Set-TimeZone', 'reg ', 'Remove-AppxPackage -'):
            self.assertNotIn(forbidden, code)

    def test_backup_compares_relative_path_size_and_hash(self):
        # Regression (issue #16): comparing only the set of hashes passes a file copied to the wrong place.
        code = '\n'.join(re.findall(r'```powershell\n(.*?)```', GUIDE, re.S))
        self.assertIn('-Property Rel, Size, Hash', code)
        self.assertNotIn('ForEach-Object { $_.Hash }', code)

    def test_quarantine_stays_on_source_volume_and_copy_is_not_completion(self):
        for term in ('隔离目录放在原件所在的同一个盘', '放的是备份', '副本建好不等于清理完成', '清理未完成',
                     'stages.log', 'quarantined'):
            self.assertIn(term, GUIDE)

    def test_host_policy_block_stops_reports_and_hands_over(self):
        section = GUIDE.split('### 被宿主策略或权限拦截时', 1)[1].split('## 6.', 1)[0]
        for term in ('blocked by policy', '立即停止', '不换命令、不换工具', 'Agent 宿主策略', '本项目的门禁',
                     'Windows 文件权限或占用', '原因不明就写不明', '只读核对现状', '脱敏', '单独确认',
                     '交接单', '准确范围', '会话记录和自动记忆', '还原', '不要求用户上传', '只读核对'):
            self.assertIn(term, section)
        self.assertIn('issue #16', GUIDE)

    def test_routed_from_skill_and_readme(self):
        skill = (ROOT / 'skills/claude-guardian/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/windows-cleanup.md', skill)
        self.assertIn('windows-cleanup.md', (ROOT / 'README.md').read_text(encoding='utf-8'))
        self.assertNotIn('machineID', (ROOT / 'skills/claude-guardian/scripts/native_claude_state_mac.py').read_text(encoding='utf-8').split('"""')[2])


if __name__ == '__main__':
    unittest.main()
