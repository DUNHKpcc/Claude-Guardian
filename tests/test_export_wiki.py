"""Wiki export: pages render from the repository, links resolve, nothing personal slips in."""
import importlib.util
from pathlib import Path
import re
import tempfile
import unittest

REPO = Path(__file__).resolve().parents[1]
SPEC = importlib.util.spec_from_file_location('export_wiki', REPO / 'tools/export_wiki.py')
w = importlib.util.module_from_spec(SPEC)
SPEC.loader.exec_module(w)


class ExportWiki(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.files, cls.problems = w.build('abc1234')

    def test_builds_without_problems_and_every_page_has_the_generated_banner(self):
        self.assertEqual(self.problems, [])
        self.assertEqual(len(self.files), len(w.PAGES) + 2)
        for name, text in self.files.items():
            self.assertTrue(text.startswith(w.MARKER), name)
        for title, source, _ in w.PAGES:
            text = self.files[w.page_name(title) + '.md']
            self.assertIn('自动生成', text)
            self.assertIn('abc1234', text)
            self.assertIn(source.split('/', 1)[1], text)
            self.assertTrue((w.ROOT / source).is_file(), source)

    def test_page_names_are_unique_and_filesystem_safe(self):
        names = [w.page_name(title) for title, _, _ in w.PAGES]
        self.assertEqual(len(names), len(set(names)))
        for name in names + ['Home', '_Sidebar']:
            self.assertFalse(re.search(r'[\\/:*?"<>|\s]', name), name)

    def test_home_and_sidebar_list_every_page_and_the_channel(self):
        for title, _, group in w.PAGES:
            link = '[%s](%s)' % (title, w.page_name(title))
            self.assertIn(link, self.files['Home.md'])
            self.assertIn(link, self.files['_Sidebar.md'])
            self.assertIn('## ' + group, self.files['Home.md'])
        self.assertIn('https://t.me/+q4D4_Qf_FIs5NDk1', self.files['Home.md'])
        self.assertIn('1048450370', self.files['Home.md'])
        self.assertIn('不承诺免封', self.files['Home.md'])

    def test_no_relative_link_is_left_and_wiki_links_point_to_real_pages(self):
        pages = {w.page_name(title) for title, _, _ in w.PAGES} | {'Home'}
        for name, text in self.files.items():
            for chunk_is_code, chunk in w.split_fences(text):
                if chunk_is_code:
                    continue
                for target in re.findall(r'\]\(([^)\s]+)\)', chunk):
                    if re.match(r'(https?:|mailto:|#)', target):
                        continue
                    self.assertIn(target.partition('#')[0], pages, '%s -> %s' % (name, target))

    def test_links_to_other_exported_pages_and_to_repository_files_are_rewritten(self):
        vps = self.files['VPS-路线.md']
        self.assertIn('](线路优化', vps)  # exported page: wiki link
        self.assertRegex(vps, r'\]\(https://github\.com/DUNHKpcc/Claude-Guardian/blob/main/skills/claude-guardian/references/routes-and-platforms\.md')
        relay = self.files['VPS-线路优化与家宽中转教程.md']
        self.assertIn('/raw/main/skills/claude-guardian/sources/R02-images/single-relay.png', relay)

    def test_links_inside_code_fences_are_not_rewritten(self):
        sample = 'see [a](references/x.md)\n```\n[a](../should-stay.md)\n```\n'
        problems = []
        out = w.rewrite_links(sample, w.ROOT / 'references/account-onboarding.md', problems)
        self.assertIn('[a](../should-stay.md)', out)
        self.assertEqual(len(problems), 1)  # the unresolved link outside the fence is reported

    def test_forbidden_content_is_detected(self):
        for bad in ('出口 165.254.188.47', '路径 /Users/someone/x', '用户 dpccskisw', 'Q群 1124987353', '手机 13812345678',
                    'password = hunter2hunter2', 'vless://abc'):
            problems = []
            w.check_forbidden('x.md', bad, problems)
            self.assertTrue(problems, bad)
        ok = []
        w.check_forbidden('x.md', 'QQ：1048450370 与 203.0.113.9', ok)
        self.assertEqual(ok, [])

    def test_cli_writes_pages_and_only_removes_stale_generated_ones(self):
        with tempfile.TemporaryDirectory() as tmp:
            out = Path(tmp)
            (out / 'Old-Generated.md').write_text(w.MARKER + '\nold', encoding='utf-8')
            (out / 'Hand-Written.md').write_text('keep me', encoding='utf-8')
            self.assertEqual(w.main(['--output', str(out), '--commit', 'abc1234']), 0)
            self.assertFalse((out / 'Old-Generated.md').exists())
            self.assertEqual((out / 'Hand-Written.md').read_text(encoding='utf-8'), 'keep me')
            self.assertTrue((out / 'Home.md').is_file())
            self.assertEqual(len(list(out.glob('*.md'))), len(w.PAGES) + 3)  # pages + Home + _Sidebar + hand-written


if __name__ == '__main__':
    unittest.main()
