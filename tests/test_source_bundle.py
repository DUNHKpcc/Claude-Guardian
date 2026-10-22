import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
import zipfile

ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/claude-guardian'

class SourceBundleTests(unittest.TestCase):
    def test_exact_manifest_and_hashes(self):
        manifest = json.loads((SKILL / 'sources/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual({s['id'] for s in manifest['sources']}, {'S01','S02','S03','S04','S05','S06','S07','S08','D-SPEC','D-ENV'})
        for source in manifest['sources']:
            records=[(source['path'],source['distributed_sha256'])]
            records.extend((c['path'],c['sha256']) for c in source.get('companions',[]))
            for relative, digest in records:
                path=SKILL / relative
                self.assertTrue(path.resolve().is_relative_to(SKILL.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
        s6=next(s for s in manifest['sources'] if s['id']=='S06')
        self.assertNotEqual(s6['original_sha256'], s6['distributed_sha256'])
        self.assertTrue(s6['changes'])

    def test_package_reproducible_and_unlisted_files_excluded(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            shutil.copytree(ROOT/'skills',root/'skills',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tools').mkdir()
            shutil.copy(ROOT/'tools/package_skill.py',root/'tools/package_skill.py')
            shutil.copy(ROOT/'LICENSE',root/'LICENSE')
            (root/'skills/claude-guardian/private-report.json').write_text('{"private":"sentinel"}')
            (root/'skills/claude-guardian/references/private-report.md').write_text('private sentinel')
            outputs=[Path(tmp)/'a.zip',Path(tmp)/'b.zip']
            for output in outputs:
                subprocess.run([sys.executable,str(root/'tools/package_skill.py'),'--output',str(output)],check=True,capture_output=True)
            self.assertEqual(outputs[0].read_bytes(),outputs[1].read_bytes())
            with zipfile.ZipFile(outputs[0]) as archive:
                names=archive.namelist()
                self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))
                self.assertIn('claude-guardian/sources/S03-claude-experience.pdf',names)
                self.assertIn('claude-guardian/scripts/status_dashboard.py',names)
                self.assertIn('claude-guardian/scripts/config_edit_plan.py',names)
                self.assertIn('claude-guardian/scripts/native_context.py',names)
                self.assertIn('claude-guardian/scripts/windows_native_context.py',names)
                self.assertIn('claude-guardian/scripts/diagnostic_session.py',names)
                self.assertIn('claude-guardian/scripts/probe_evidence.py',names)
                self.assertIn('claude-guardian/scripts/dns_probe.py',names)
                self.assertIn('claude-guardian/scripts/mihomo_dns_probe.py',names)
                self.assertIn('claude-guardian/scripts/os_dns_probe.py',names)
                self.assertIn('claude-guardian/scripts/windows_dns_probe.py',names)
                self.assertFalse(any('private-report' in name for name in names))

    def test_tampered_source_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            shutil.copytree(ROOT/'skills',root/'skills',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tools').mkdir()
            shutil.copy(ROOT/'tools/package_skill.py',root/'tools/package_skill.py')
            shutil.copy(ROOT/'LICENSE',root/'LICENSE')
            (root/'skills/claude-guardian/sources/S01-server-glossary.md').write_text('changed')
            result=subprocess.run([sys.executable,str(root/'tools/package_skill.py'),'--output',str(Path(tmp)/'out.zip')],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((Path(tmp)/'out.zip').exists())

if __name__ == '__main__':
    unittest.main()
