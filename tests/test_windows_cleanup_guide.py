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

    def test_routed_from_skill_and_readme(self):
        skill = (ROOT / 'skills/claude-guardian/SKILL.md').read_text(encoding='utf-8')
        self.assertIn('references/windows-cleanup.md', skill)
        self.assertIn('windows-cleanup.md', (ROOT / 'README.md').read_text(encoding='utf-8'))
        self.assertNotIn('machineID', (ROOT / 'skills/claude-guardian/scripts/native_claude_state_mac.py').read_text(encoding='utf-8').split('"""')[2])


if __name__ == '__main__':
    unittest.main()
