import hashlib
import json
from pathlib import Path
import re
import unittest


ROOT = Path(__file__).resolve().parents[1]
SKILL = ROOT / 'skills/claude-guardian'
LIBRARY_PATH = SKILL / 'references/source-library.md'


class SourceInventoryConsistencyTests(unittest.TestCase):
    def setUp(self):
        self.current = json.loads((SKILL / 'sources/manifest.json').read_text(encoding='utf-8'))
        self.sources = {source['id']: source for source in self.current['sources']}
        self.library = LIBRARY_PATH.read_text(encoding='utf-8')


    def test_reading_count_and_sections_match_the_packaged_inventory(self):
        reading_ids = {source['id'] for source in self.current['sources']
                       if source['category'] == 'reading'}
        self.assertEqual(reading_ids, {'S01', 'S02', 'S03', 'S04', 'S05', 'S06', 'S07', 'S08'})
        self.assertFalse(any(source['category'] == 'design' for source in self.current['sources']))
        self.assertIn('## 八份阅读来源', self.library)
        self.assertNotIn('六份阅读来源', self.library)
        self.assertNotIn('六个阅读来源', self.library)
        sections = re.findall(r'^### (S\d+)：', self.library, flags=re.MULTILINE)
        self.assertEqual(len(sections), len(reading_ids))
        self.assertEqual(set(sections), reading_ids)
        self.assertNotIn('## 设计规范：', self.library)
        self.assertNotIn('sources/design', self.library)


    def test_index_links_cover_current_sources_and_derived_companion_with_valid_hashes(self):
        links = set(re.findall(r'\]\((\.\./sources/[^)]+)\)', self.library))
        self.assertIn('../sources/manifest.json', links)
        expected_paths = set()
        companions = []
        collection_ids = {item['id'] for item in self.current.get('collections', [])}
        for source in self.current['sources'] + self.current.get('collections', []):
            records = [(source['path'], source['distributed_sha256'])]
            companions.extend(source.get('companions', []))
            records.extend((item['path'], item['sha256'])
                           for item in source.get('companions', []))
            for relative, digest in records:
                path = (SKILL / relative).resolve()
                self.assertTrue(path.is_relative_to(SKILL.resolve()))
                self.assertEqual(hashlib.sha256(path.read_bytes()).hexdigest(), digest)
                # A collection is linked from the library only through its index
                # file; its member files are covered by that index's own test.
                if source['id'] in collection_ids and relative != source['path']:
                    continue
                expected_paths.add(path)
        linked_paths = {(LIBRARY_PATH.parent / link).resolve() for link in links}
        self.assertEqual(linked_paths, expected_paths | {(SKILL / 'sources/manifest.json').resolve()})
        self.assertEqual([item['path'] for item in companions if item['path'].startswith('sources/S')],
                         ['sources/S03-extracted-text.md', 'sources/S03-source-text.md',
                          'sources/S08-extracted-text.md'])
        self.assertNotEqual(self.sources['S06']['original_sha256'],
                            self.sources['S06']['distributed_sha256'])


if __name__ == '__main__':
    unittest.main()
