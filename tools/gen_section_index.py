"""Generate references/section-index.md: every H2/H3 section of every reference, with its anchor.

The Agent can open a whole file, but a section that nothing points to is easily missed
(the short-term-ban timeline once was). This index points to all of them. Run
``python tools/gen_section_index.py`` after editing a reference; the test
``tests/test_skill_discoverability.py`` fails when the committed index is out of date.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1] / 'skills/claude-guardian'
REFERENCES = ROOT / 'references'
OUTPUT = REFERENCES / 'section-index.md'
SKIP = {'section-index.md'}


def slug(heading):
    """GitHub-style anchor: lower-case, drop punctuation, spaces to hyphens."""
    return re.sub(r'[^\w\- ]', '', heading.strip().lower(), flags=re.UNICODE).replace(' ', '-')


def headings(path):
    """(level, text, anchor) for every H1-H3 outside fenced code, with GitHub's -N suffix on repeats."""
    seen, found, fence = {}, [], False
    for line in path.read_text(encoding='utf-8').splitlines():
        if line.lstrip().startswith('```'):
            fence = not fence
            continue
        match = None if fence else re.match(r'^(#{1,3})\s+(.*?)\s*$', line)
        if not match:
            continue
        text = re.sub(r'\[([^\]]*)\]\([^)]*\)', r'\1', match.group(2))
        base = slug(text)
        count = seen.get(base, 0)
        seen[base] = count + 1
        found.append((len(match.group(1)), match.group(2), base if count == 0 else '%s-%d' % (base, count)))
    return found


def render():
    lines = ['# 章节索引', '',
             '`references/` 里每个文件的每个二、三级小节都列在这里，附锚点链接。找某个主题时，先按 [SKILL.md 的资料表](../SKILL.md) 定位文件，再在这里找具体小节，不必通读整份文件。'
             '本页由 `tools/gen_section_index.py` 生成，请不要手改；改了某份 reference 的标题后重新生成。', '']
    for path in sorted(REFERENCES.glob('*.md')):
        if path.name in SKIP:
            continue
        found = headings(path)
        title = next((text for level, text, _ in found if level == 1), path.stem)
        sections = [(level, text, anchor) for level, text, anchor in found if level > 1]
        lines += ['## %s' % path.name, '', '%s（%d 节）' % (title, len(sections)), '']
        for level, text, anchor in sections:
            lines.append('%s- [%s](%s#%s)' % ('  ' if level == 3 else '', text.replace('|', '\\|'), path.name, anchor))
        lines.append('')
    return '\n'.join(lines).rstrip('\n') + '\n'


def main():
    OUTPUT.write_text(render(), encoding='utf-8')
    print('wrote', OUTPUT.relative_to(ROOT.parents[1]))
    return 0


if __name__ == '__main__':
    sys.exit(main())
