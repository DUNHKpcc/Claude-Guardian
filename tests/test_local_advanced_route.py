"""Platform-specific remote guidance under the shared local-route principles."""
from pathlib import Path
import unittest


ROOT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian'


class LocalAdvancedRouteTests(unittest.TestCase):
    def test_mac_guidance_uses_native_access_and_independent_recovery(self):
        text = (ROOT / 'references/local-advanced-route.md').read_text(encoding='utf-8')
        self.assertIn('<a id="mac-access"></a>', text)
        access = text.split('### Mac：远程登录与桌面会话', 1)[1].split('## 3.', 1)[0]
        for term in ('远程登录', '仅这些用户', 'SSH', 'SFTP', 'Tailscale', '屏幕共享', '登录用户'):
            self.assertIn(term, access)
        recovery = text.split('### Mac：PF 与独立恢复', 1)[1].split('## 4.', 1)[0]
        for term in ('guardian-pf-killswitch.sh', '180 秒保险丝', 'launchd', '回滚', 'status'):
            self.assertIn(term, recovery)
        for block in (access, recovery):
            for windows_only in ('SYSTEM', 'schtasks', 'PowerShell', 'administrators_authorized_keys'):
                self.assertNotIn(windows_only, block)
        self.assertNotIn('待验证', text)

    def test_mac_entry_keeps_remote_assistance_optional(self):
        main = (ROOT / 'references/local-firewall-prompts.md').read_text(encoding='utf-8')
        mac = main.split('## Mac', 1)[1].split('## Windows', 1)[0]
        self.assertIn('local-advanced-route.md#mac-access', mac)
        extension = (ROOT / 'references/local-advanced-route.md').read_text(encoding='utf-8')
        for term in ('目标机已有 Agent', '用户明确选择远程协助', '不新增路线值', 'C 档'):
            self.assertIn(term, extension)
        self.assertIn('support.apple.com/guide/mac-help/', extension)


if __name__ == '__main__':
    unittest.main()
