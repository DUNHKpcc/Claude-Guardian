"""Every shipped file and every promised section must be reachable by an Agent that loads SKILL.md.

A document that exists but is never routed to (the short-term-ban timeline and KYC guidance
were once only inside account-onboarding.md) is a defect: the Agent cannot attach what it
cannot find. This test fails when a reference, source, asset or script is not reachable by
following mentions from SKILL.md, when the script index drifts from scripts/, and when a
relative Markdown link or its #anchor does not resolve.
"""
from pathlib import Path
import importlib.util
import re
import sys
import unittest

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'skills/claude-guardian'
SKIP_DIRS = {'__pycache__'}
SKIP_NAMES = {'.DS_Store'}
TEXT_SUFFIXES = {'.md', '.py', '.json', '.html', '.sh'}


def shipped_files():
    return [p for sub in ('references', 'sources', 'assets', 'scripts') for p in sorted((ROOT / sub).rglob('*'))
            if p.is_file() and not (set(p.parts) & SKIP_DIRS) and p.name not in SKIP_NAMES]


def slug(heading):
    """GitHub-style anchor: lower-case, drop punctuation, spaces to hyphens."""
    text = re.sub(r'[^\w\- ]', '', heading.strip().lower(), flags=re.UNICODE)
    return text.replace(' ', '-')


def anchors(path):
    found = set()
    text = path.read_text(encoding='utf-8')
    for match in re.finditer(r'^#{1,6}\s+(.*?)\s*$', text, re.M):
        found.add(slug(re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', match.group(1))))
    found.update(re.findall(r'<a id="([^"]+)"', text))
    return found


class SkillDiscoverability(unittest.TestCase):
    def test_every_shipped_file_is_reachable_from_skill_md(self):
        files = shipped_files()
        texts = {p: p.read_text(encoding='utf-8') for p in files + [ROOT / 'SKILL.md'] if p.suffix in TEXT_SUFFIXES}
        reached, frontier = {ROOT / 'SKILL.md'}, [ROOT / 'SKILL.md']
        while frontier:
            current = frontier.pop()
            if current.suffix != '.md':
                continue  # Only prose routes an Agent; code importing code does not.
            body = texts[current]
            for candidate in files:
                if candidate not in reached and (candidate.name in body or candidate.relative_to(ROOT).as_posix() in body):
                    reached.add(candidate)
                    frontier.append(candidate)
        missing = [p.relative_to(ROOT).as_posix() for p in files if p not in reached]
        self.assertEqual(missing, [], 'not reachable from SKILL.md by any chain of mentions')

    def test_every_reference_and_top_level_source_is_named_directly_in_skill_md(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        names = [p.name for p in sorted((ROOT / 'references').glob('*.md'))]
        names += [p.name for p in sorted((ROOT / 'sources').iterdir()) if p.is_file() and p.name not in SKIP_NAMES]
        self.assertEqual([n for n in names if n not in skill], [], 'name it in SKILL.md (table or on-demand list)')

    def test_script_index_matches_scripts_and_assets(self):
        index = (ROOT / 'references/scripts-index.md').read_text(encoding='utf-8')
        scripts = [p.name for p in (ROOT / 'scripts').glob('*.py')]
        self.assertEqual([n for n in scripts if n not in index], [], 'script missing from scripts-index.md')
        listed = set(re.findall(r'`([a-z_0-9]+\.py)`', index))
        self.assertEqual(sorted(listed - set(scripts)), [], 'scripts-index.md lists a script that does not exist')
        assets = [p.relative_to(ROOT).as_posix() for p in (ROOT / 'assets').rglob('*') if p.is_file() and p.name not in SKIP_NAMES]
        self.assertEqual([a for a in assets if a not in index], [], 'asset missing from scripts-index.md')

    def test_relative_markdown_links_and_anchors_resolve(self):
        problems = []
        for doc in [ROOT / 'SKILL.md'] + sorted((ROOT / 'references').glob('*.md')):
            for target in re.findall(r'\]\(([^)\s]+)\)', doc.read_text(encoding='utf-8')):
                if re.match(r'(https?:|mailto:)', target):
                    continue
                path_part, _, fragment = target.partition('#')
                resolved = doc if not path_part else (doc.parent / path_part).resolve()
                if not resolved.exists():
                    # Links that leave the shipped skill (repository docs) are not part of the package.
                    if ROOT in resolved.parents or resolved == ROOT:
                        problems.append('%s -> %s (missing file)' % (doc.name, target))
                    continue
                if fragment and resolved.suffix == '.md' and slug(fragment) not in anchors(resolved) and fragment not in anchors(resolved):
                    problems.append('%s -> %s (missing anchor)' % (doc.name, target))
        self.assertEqual(problems, [])

    def test_anchor_check_is_not_vacuous(self):
        self.assertEqual(slug('Cleanup, migration, and recovery (M13 / ENV-09)'), 'cleanup-migration-and-recovery-m13--env-09')
        self.assertIn('a0b短期封号时间线出问题时先对照排查方向', anchors(ROOT / 'references/account-onboarding.md'))
        self.assertNotIn('no-such-section', anchors(ROOT / 'references/account-onboarding.md'))

    def test_promised_topics_are_routed_in_the_material_table(self):
        skill = (ROOT / 'SKILL.md').read_text(encoding='utf-8')
        rows = [line for line in skill.splitlines() if line.startswith('|')]

        def row(term):
            found = [line for line in rows if line.startswith('| ' + term) or line.startswith('| **' + term)]
            self.assertTrue(found, 'no table row mentions %s' % term)
            return found[0]
        ban = row('账号被封或被限')
        for link in ('account-onboarding.md#a0b', 'S03-claude-experience.pdf', 'accounts-and-payments.md#a3', 'S04-claude-guide.md',
                     'incidents-and-integrations.md'):
            self.assertIn(link, ban)
        for term, must in (('Windows 清理', 'windows-cleanup.md'), ('macOS 清理', 'cleanup-cli-usage.md'),
                           ('整机统一出口', 'whole-machine-ipv4.md'), ('线路优化', 'line-optimization.md'),
                           ('VPS 路线', 'vps-guidance.md'), ('VM 路线', 'vm-guidance.md'),
                           ('手机端', 'mobile-guidance.md'), ('本机路线固定出口', 'egress-ip-options.md')):
            self.assertIn(must, row(term))
        self.assertIn('## 每台机器环境不同', skill)
        self.assertIn('## 少打扰用户', skill)
        for term in ('IDC Flare', 'VPSHub'):
            self.assertTrue(any(term in line for line in rows), term)


def load(name, path):
    spec = importlib.util.spec_from_file_location(name, path)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


class SectionLevelDiscoverability(unittest.TestCase):
    """The file is reachable; this makes every section of it reachable too."""

    @classmethod
    def setUpClass(cls):
        cls.generator = load('gen_section_index', REPO / 'tools/gen_section_index.py')

    def test_committed_section_index_is_up_to_date(self):
        self.assertEqual((ROOT / 'references/section-index.md').read_text(encoding='utf-8'), self.generator.render(),
                         'run: python tools/gen_section_index.py')

    def test_every_h2_h3_section_of_every_reference_is_linked_from_the_index(self):
        index = (ROOT / 'references/section-index.md').read_text(encoding='utf-8')
        missing = []
        for path in sorted((ROOT / 'references').glob('*.md')):
            if path.name == 'section-index.md':
                continue
            for level, text, anchor in self.generator.headings(path):
                if level > 1 and '(%s#%s)' % (path.name, anchor) not in index:
                    missing.append('%s#%s' % (path.name, anchor))
        self.assertEqual(missing, [])

    def test_index_covers_a_meaningful_number_of_sections_and_the_skill_points_to_it(self):
        index = (ROOT / 'references/section-index.md').read_text(encoding='utf-8')
        self.assertGreaterEqual(len(re.findall(r'^\s*- \[', index, re.M)), 200)
        self.assertIn('references/section-index.md', (ROOT / 'SKILL.md').read_text(encoding='utf-8'))

    def test_every_anchor_locator_the_interview_can_emit_resolves(self):
        scripts = str(ROOT / 'scripts')
        sys.path.insert(0, scripts)
        try:
            flow = load('interview_flow_for_locators', ROOT / 'scripts/interview_flow.py')
        finally:
            sys.path.remove(scripts)
        source = (ROOT / 'scripts/interview_flow.py').read_text(encoding='utf-8')
        locators = re.findall(r"add\('(\w+)', '\w+', '(#[^']+)'\)", source)
        locators += [(key, anchor) for key, anchor in
                     (('routes', a) for a in re.findall(r"'(#r-[^']+)'", source))]
        self.assertGreaterEqual(len(locators), 8)
        for key, anchor in locators:
            target = ROOT / flow.REFERENCE_PATHS[key]
            self.assertIn(anchor[1:], anchors(target), '%s %s' % (key, anchor))


if __name__ == '__main__':
    unittest.main()
