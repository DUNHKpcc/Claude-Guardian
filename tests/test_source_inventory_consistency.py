import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/claude-guardian'
HISTORICAL_PATH = ROOT / 'docs/source-manifest.json'
LIBRARY_PATH = SKILL / 'references/source-library.md'
BASELINE_HASHES = {
    'S01': 'e2660c1b049d73e7a927594743f079cb0a5f10be9f72bad7928f10a5838bb68b',
    'S02': '9fc0962d5386011d3c292fd30a8f8530544899a82bda62d9c574ff62d4e52c75',
    'S03': 'ffd8ab0e3f8c597733f842c3b17e4bea8d9ac9585f6a21d4e12039b0b32ed792',
    'S04': '281b2881c5a016b5188aa71c1e7162e1742c98170d9685f2a4e24503ee7a5992',
    'S05': 'f2a975d359161312763f02d6c5d2b4e796e52a57edf2a9ecb233445c8d2389d9',
    'S06': 'c49c3bfab9823e15a46bc13aeccf2045dd16bb8d3e553b90ae3aca2f52d75f99',
    'D-SPEC': '6c520d5ee50c914dcf519e5e63ba15641654e9b828c51c30f7fd3b80b6ba0562',
    'D-ENV': 'ea396f8bf36d37165761ac0d3fe2528eb1c1824c5abfda772a5c1b2b7240eef4',
}


class SourceInventoryConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.historical = json.loads(HISTORICAL_PATH.read_text(encoding='utf-8'))
        self.current = json.loads((SKILL / 'sources/manifest.json').read_text(encoding='utf-8'))
        self.sources = {source['id']: source for source in self.current['sources']}
        self.library = LIBRARY_PATH.read_text(encoding='utf-8')

    def test_historical_manifest_points_to_canonical_current_inventory(self):
        self.assertEqual(self.historical.get('inventory_scope'), 'historical-input-snapshot')
        relative = self.historical['current_inventory_manifest']
        self.assertEqual((HISTORICAL_PATH.parent / relative).resolve(),
                         (SKILL / 'sources/manifest.json').resolve())
        self.assertEqual(self.historical['baseline_date'], '2026-10-15')

    def test_original_eight_input_names_hashes_and_roles_are_preserved(self):
        expected = {
            (self.sources[source_id]['original_filename'], digest,
             'design-baseline' if source_id.startswith('D-') else 'reference-only')
            for source_id, digest in BASELINE_HASHES.items()
        }
        actual = {(item['file'], item['sha256'], item['role'])
                  for item in self.historical['files']}
        self.assertEqual(len(self.historical['files']), 8)
        self.assertEqual(actual, expected)

    def test_obsolete_distribution_flags_are_explicitly_historical(self):
        self.assertEqual({item.get('source_id') for item in self.historical['files']},
                         set(BASELINE_HASHES))
        for item in self.historical['files']:
            with self.subTest(source=item['source_id']):
                self.assertNotIn('redistribution', item)
                self.assertEqual(item['baseline_redistribution'],
                                 'not included; original rights not established')
                self.assertEqual(item['sha256'],
                                 self.sources[item['source_id']]['original_sha256'])

    def test_reading_count_and_sections_match_the_packaged_inventory(self):
        reading_ids = {source['id'] for source in self.current['sources']
                       if source['category'] == 'reading'}
        design_ids = {source['id'] for source in self.current['sources']
                      if source['category'] == 'design'}
        self.assertEqual(reading_ids, {'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07'})
        self.assertEqual(design_ids, {'D-SPEC', 'D-ENV'})
        self.assertIn('## 七份阅读来源', self.library)
        self.assertNotIn('六份阅读来源', self.library)
        self.assertNotIn('六个阅读来源', self.library)
        sections = re.findall(r'^### (S\d+)：', self.library, flags=re.MULTILINE)
        self.assertEqual(len(sections), len(reading_ids))
        self.assertEqual(set(sections), reading_ids)
        self.assertLess(self.library.index('### S07：'),
                        self.library.index('## 设计规范：'))

    def test_reading_index_separates_initial_inputs_later_s07_and_missing_sources(self):
        self.assertIn('最初八个输入文件', self.library)
        self.assertIn('S07 后续补入', self.library)
        self.assertIn('S08 仍未提供；S09 为外部仓库参考', self.library)
        self.assertNotIn('本阅读库没有宣称打包它们', self.library)
        self.assertNotIn('S08', self.sources)
        self.assertNotIn('S09', self.sources)
        self.assertIn('派生文字辅助文件，不另计为独立来源', self.library)

    def test_index_links_cover_current_sources_and_derived_companion_with_valid_hashes(self):
        links = set(re.findall(r'\]\((\.\./sources/[^)]+)\)', self.library))
        self.assertIn('../sources/manifest.json', links)
        expected_paths = set()
        companions = []
        for source in self.current['sources']:
            records = [(source['path'], source['distributed_sha256'])]
            companions.extend(source.get('companions', []))
            records.extend((item['path'], item['sha256'])
                           for item in source.get('companions', []))
            for relative, digest in records:
                path = (SKILL / relative).resolve()
                self.assertTrue(path.is_relative_to(SKILL.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                expected_paths.add(path)
        linked_paths = {(LIBRARY_PATH.parent / link).resolve() for link in links}
        self.assertEqual(linked_paths, expected_paths | {(SKILL / 'sources/manifest.json').resolve()})
        self.assertEqual([item['path'] for item in companions], ['sources/S03-extracted-text.md'])
        self.assertNotEqual(self.sources['S06']['original_sha256'],
                            self.sources['S06']['distributed_sha256'])


if __name__ == '__main__':
    unittest.main()
