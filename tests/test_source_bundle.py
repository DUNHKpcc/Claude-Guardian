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
    def test_manifest_checks_binary_sources_without_pinning_markdown(self):
        manifest = json.loads((SKILL / 'sources/manifest.json').read_text(encoding='utf-8'))
        self.assertEqual({s['id'] for s in manifest['sources']}, {'S01','S02','S03','S04','S05','S06','S07','S08','S10'})
        for source in manifest['sources'] + manifest.get('collections', []):
            records=[(source['path'],source.get('distributed_sha256'))]
            records.extend((c['path'],c.get('sha256')) for c in source.get('companions',[]))
            for relative, digest in records:
                path=SKILL / relative
                self.assertTrue(path.resolve().is_relative_to(SKILL.resolve()))
                self.assertTrue(path.is_file())
                if path.suffix.lower() == '.md':
                    self.assertIsNone(digest, relative)
                else:
                    self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(),digest)
        s6=next(s for s in manifest['sources'] if s['id']=='S06')
        self.assertRegex(s6['original_sha256'], r'^[0-9a-f]{64}$')
        self.assertTrue(s6['changes'])

    def test_markdown_edits_ship_reproducibly_without_manifest_updates(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            shutil.copytree(ROOT/'skills',root/'skills',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tools').mkdir()
            shutil.copy(ROOT/'tools/package_skill.py',root/'tools/package_skill.py')
            shutil.copy(ROOT/'LICENSE',root/'LICENSE')
            edited = ('sources/S10-windows-deployment-sanitized.md',
                      'sources/S03-extracted-text.md', 'sources/vps-recommendations/INDEX.md')
            for relative in edited:
                path = root/'skills/claude-guardian'/relative
                path.write_bytes(path.read_bytes() + '\n新增说明。\n'.encode('utf-8'))
            manifest_path = root/'skills/claude-guardian/sources/manifest.json'
            original_manifest = manifest_path.read_bytes()
            (root/'skills/claude-guardian/private-report.json').write_text('{"private":"sentinel"}')
            (root/'skills/claude-guardian/references/private-report.md').write_text('private sentinel')
            outputs=[Path(tmp)/'a.zip',Path(tmp)/'b.zip']
            for output in outputs:
                subprocess.run([sys.executable,str(root/'tools/package_skill.py'),'--output',str(output)],check=True,capture_output=True)
            self.assertEqual(outputs[0].read_bytes(),outputs[1].read_bytes())
            self.assertEqual(manifest_path.read_bytes(), original_manifest)
            with zipfile.ZipFile(outputs[0]) as archive:
                names=archive.namelist()
                self.assertTrue(all(info.create_system == 3 for info in archive.infolist()))
                self.assertIn('claude-guardian/sources/S03-claude-experience.pdf',names)
                for relative in edited:
                    self.assertEqual(archive.read('claude-guardian/' + relative),
                                     (root/'skills/claude-guardian'/relative).read_bytes())
                extension = 'references/local-advanced-route.md'
                self.assertEqual(archive.read('claude-guardian/' + extension), (SKILL / extension).read_bytes())
                self.assertIn('claude-guardian/scripts/status_dashboard.py',names)
                self.assertIn('claude-guardian/scripts/config_edit_plan.py',names)
                self.assertIn('claude-guardian/scripts/probe_evidence.py',names)
                self.assertIn('claude-guardian/scripts/network_check.py',names)
                self.assertFalse(any('private-report' in name for name in names))

    def test_changed_original_pdf_rejected(self):
        with tempfile.TemporaryDirectory() as tmp:
            root=Path(tmp)/'repo'
            shutil.copytree(ROOT/'skills',root/'skills',ignore=shutil.ignore_patterns('__pycache__'))
            (root/'tools').mkdir()
            shutil.copy(ROOT/'tools/package_skill.py',root/'tools/package_skill.py')
            shutil.copy(ROOT/'LICENSE',root/'LICENSE')
            (root/'skills/claude-guardian/sources/S03-claude-experience.pdf').write_bytes(b'changed')
            result=subprocess.run([sys.executable,str(root/'tools/package_skill.py'),'--output',str(Path(tmp)/'out.zip')],capture_output=True)
            self.assertNotEqual(result.returncode,0)
            self.assertFalse((Path(tmp)/'out.zip').exists())

if __name__ == '__main__':
    unittest.main()
