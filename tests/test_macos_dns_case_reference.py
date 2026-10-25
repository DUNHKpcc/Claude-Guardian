"""Offline documentation checks; these do not validate network behavior."""
from pathlib import Path
import re
import shutil
import subprocess
import sys
import tempfile
import zipfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills' / 'claude-guardian'
DOC = SKILL / 'references' / 'macos-dns-case-lessons.md'


class MacOSDnsCaseReferenceTests(unittest.TestCase):
    def test_evidence_and_permission_limits_remain_explicit(self):
        text = DOC.read_text(encoding='utf-8')
        for required in (
            'PC0', '未完整验证', '生命周期', '配置', '未知',
            'Fake-IP', 'TCP', 'UDP', 'DoH', 'DoT', '回滚',
            '不能证明', '不新增运行能力', '原作者设备当前状态',
        ):
            self.assertIn(required, text)
        self.assertNotRegex(text, r'```(?:sh|bash|shell|ya?ml)\b')

    def test_reference_has_primary_sources_and_no_environment_literals(self):
        text = DOC.read_text(encoding='utf-8')
        for url in (
            'https://wiki.metacubex.one/en/config/dns/',
            'https://wiki.metacubex.one/en/config/inbound/tun/#dns-hijack',
            'https://tailscale.com/docs/reference/quad100',
            'https://tailscale.com/docs/features/client/manage-preferences',
            'https://www.rfc-editor.org/rfc/rfc8828.html',
        ):
            self.assertIn(url, text)
        # Public prose deliberately needs no literal addresses or personal paths.
        for pattern in (
            r'(?<!\d)(?:\d{1,3}\.){3}\d{1,3}(?!\d)',
            r'/Users/[^\s/]+', r'(?i)tail[a-z0-9-]+\.ts\.net',
            r'\butun\d+\b', r'libfile_[a-zA-Z0-9]+',
            r'file_[a-zA-Z0-9]{16,}',
        ):
            self.assertIsNone(re.search(pattern, text), pattern)

    def test_reference_is_reachable_from_skill_and_network_guide(self):
        for path in (SKILL / 'SKILL.md', SKILL / 'references' / 'network-and-remedies.md'):
            self.assertIn('macos-dns-case-lessons.md', path.read_text(encoding='utf-8'))


    def test_required_sections_and_scope_distinctions(self):
        text = DOC.read_text(encoding='utf-8')
        for heading in (
            '## 先分清观察、解释与未知', '## 1. DNS 职责与路径分别记录',
            '## 2. 端口 53 接管不是所有 DNS 的覆盖证明',
            '## 3. IPv6 开关具有不同作用域',
            '## 4. Tailscale、私有解析与应用退出依赖',
            '## 5. 验收矩阵：样本不能互相代证',
            '## 6. 最小变更、回滚与时效', '## 来源与使用范围',
        ):
            self.assertIn(heading, text)
        for caveat in ('来源没有完成全部 WebRTC/UDP 检测',
                       '没有实际退出代理应用后的生命周期测试',
                       '原成功记录只能说明旧条件', '未复测的新状态保持未知',
                       '也不能单独证明 DoH、DoT', '不得覆盖后来发生的合法配置变更'):
            self.assertIn(caveat, text)

    def test_network_guide_points_to_the_network_check(self):
        text = (SKILL / 'references/network-and-remedies.md').read_text(encoding='utf-8')
        for old in ('本版所有主动网络测试均未开放', 'neutral network probes remain unavailable',
                    '尚无通用主动网络 CLI', 'Guarded host libraries', 'PRODUCT-IPV4-20261018'):
            self.assertNotIn(old, text)
        for current in ('network_check.py run', 'never Claude or Anthropic', 'B tier', '--failure-drill',
                        'egress_verifier.py', 'serve_webrtc.py', 'agent-remediation.md#ipv4-only-policy'):
            self.assertIn(current, text)

    def test_package_includes_only_public_reference_and_preserves_source_manifest(self):
        # Synthetic decoys only: never read/copy the private provenance or raw upload.
        with tempfile.TemporaryDirectory() as tmp:
            root = Path(tmp) / 'repo'
            shutil.copytree(ROOT / 'skills', root / 'skills', ignore=shutil.ignore_patterns('__pycache__'))
            (root / 'tools').mkdir()
            shutil.copyfile(ROOT / 'tools/package_skill.py', root / 'tools/package_skill.py')
            shutil.copyfile(ROOT / 'LICENSE', root / 'LICENSE')
            refs = root / 'skills/claude-guardian/references'
            (refs / 'provenance-private.json').write_text('synthetic private provenance sentinel')
            (refs / 'raw-network-experience.md').write_text('synthetic raw upload sentinel')
            output = Path(tmp) / 'reference.zip'
            subprocess.run([sys.executable, str(root / 'tools/package_skill.py'), '--output', str(output)],
                           check=True, capture_output=True)
            with zipfile.ZipFile(output) as archive:
                names = archive.namelist()
                self.assertEqual(archive.read('claude-guardian/references/macos-dns-case-lessons.md'),
                                 DOC.read_bytes())
                self.assertFalse(any('provenance-private' in name or 'raw-network-experience' in name
                                     for name in names))
                self.assertEqual(archive.read('claude-guardian/sources/manifest.json'),
                                 (SKILL / 'sources/manifest.json').read_bytes())
                for name in names:
                    self.assertNotIn(b'synthetic private provenance sentinel', archive.read(name))
                    self.assertNotIn(b'synthetic raw upload sentinel', archive.read(name))

if __name__ == '__main__':
    unittest.main()
