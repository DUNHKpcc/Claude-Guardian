"""Export the user-facing tutorials to GitHub Wiki pages.

The repository stays the single source of truth: ``skills/claude-guardian/`` is what the
Agent reads and what the tests guard, so nothing is moved out of it. This tool renders a
copy for the wiki (a separate git repository, ``<repo>.wiki.git``) with links rewritten,
a "generated, edit in the repo" banner, a Home page and a sidebar. It fails if a link
cannot be resolved or if personal data or a credential-looking value slips in.

    python tools/export_wiki.py --output /path/to/Claude-Guardian.wiki [--commit SHA]
"""
import argparse
from pathlib import Path
import re
import subprocess
import sys

REPO = Path(__file__).resolve().parents[1]
ROOT = REPO / 'skills/claude-guardian'
GITHUB = 'https://github.com/DUNHKpcc/Claude-Guardian'
MARKER = '<!-- generated-by: tools/export_wiki.py -->'
IMAGE_SUFFIXES = {'.png', '.jpg', '.jpeg', '.gif', '.svg', '.webp'}
FORBIDDEN = (r'165\.254\.188\.47', r'10\.72\.18\.', r'dpccskisw', r'DpccProject', r'/Users/[A-Za-z0-9_.-]+',
             r'1124987353', r'\b1[3-9]\d{9}\b', r'(?i)\b(?:password|passwd|token|secret)\s*[:=]\s*\S{8,}',
             r'vless://', r'vmess://', r'trojan://', r'ss://[A-Za-z0-9+/=]{16,}')

# (wiki page title, source relative to skills/claude-guardian, group)
PAGES = [
    ('账号注册与养号节奏', 'references/account-onboarding.md', '入门'),
    ('手机端防封要点', 'references/mobile-guidance.md', '入门'),
    ('固定出口 IP 的来源', 'references/egress-ip-options.md', '出口 IP'),
    ('整机统一出口 只走 IPv4', 'references/whole-machine-ipv4.md', '出口 IP'),
    ('本机路线 Clash 与防火墙', 'references/local-firewall-prompts.md', '三条路线'),
    ('VM 路线', 'references/vm-guidance.md', '三条路线'),
    ('VPS 路线', 'references/vps-guidance.md', '三条路线'),
    ('线路优化', 'references/line-optimization.md', '三条路线'),
    ('macOS 清理教程', 'sources/S06-macos-cleanup-sanitized.md', '清理'),
    ('Windows 清理', 'references/windows-cleanup.md', '清理'),
    ('VPS Claude 教程 文字版', 'sources/S08-extracted-text.md', '所有者提供的教程'),
    ('VPS 线路优化与家宽中转教程', 'sources/R02-vps-line-optimization.md', '所有者提供的教程'),
]
GROUP_ORDER = ['入门', '出口 IP', '三条路线', '清理', '所有者提供的教程']
CHANNEL = ('- Telegram 频道：[https://t.me/+q4D4_Qf_FIs5NDk1](https://t.me/+q4D4_Qf_FIs5NDk1)\n'
           '- QQ：1048450370\n')


class ExportError(Exception):
    pass


def page_name(title):
    """GitHub turns spaces in a page file name into hyphens; keep the name filesystem-safe."""
    return re.sub(r'[\\/:*?"<>|]', '', title).replace(' ', '-')


def sources():
    return {(ROOT / source).resolve(): title for title, source, _ in PAGES}


def split_fences(text):
    """Yield (is_code, chunk) so links inside fenced code are never rewritten."""
    chunks, current, fence = [], [], False
    for line in text.splitlines(keepends=True):
        if line.lstrip().startswith('```'):
            if not fence and current:
                chunks.append((False, ''.join(current)))
                current = []
            current.append(line)
            if fence:
                chunks.append((True, ''.join(current)))
                current = []
            fence = not fence
            continue
        current.append(line)
    if current:
        chunks.append((fence, ''.join(current)))
    return chunks


def rewrite_links(text, source, problems):
    exported = sources()

    def fix(match):
        bang, label, target = match.group(1), match.group(2), match.group(3)
        if re.match(r'(https?:|mailto:|#)', target):
            return match.group(0)
        path_part, _, fragment = target.partition('#')
        resolved = (source.parent / path_part).resolve()
        if not resolved.exists():
            problems.append('%s: unresolved link %s' % (source.relative_to(ROOT), target))
            return match.group(0)
        suffix = '#' + fragment if fragment else ''
        if resolved in exported and not bang:
            return '[%s](%s%s)' % (label, page_name(exported[resolved]), suffix)
        relative = resolved.relative_to(REPO).as_posix()
        if resolved.suffix.lower() in IMAGE_SUFFIXES:
            return '%s[%s](%s/raw/main/%s)' % (bang, label, GITHUB, relative)
        return '%s[%s](%s/blob/main/%s%s)' % (bang, label, GITHUB, relative, suffix)

    out = []
    for is_code, chunk in split_fences(text):
        out.append(chunk if is_code else re.sub(r'(!?)\[([^\]]*)\]\(([^)\s]+)\)', fix, chunk))
    return ''.join(out)


def bold_to_html(text):
    """CommonMark does not close ``**bold**`` after CJK punctuation when text follows it
    (``**……。**后面``), so GitHub shows literal asterisks. <strong> renders everywhere.
    Fenced code is left alone; inline code spans are protected while the markers are
    matched, so bold that contains code (``**不要整删 `~/.claude`。**``) still converts."""
    out = []
    for is_code, chunk in split_fences(text):
        if is_code:
            out.append(chunk)
            continue
        lines = []
        for line in chunk.splitlines(keepends=True):
            spans = []

            def hide(match):
                spans.append(match.group(0))
                return '\x00%d\x00' % (len(spans) - 1)

            hidden = re.sub(r'`[^`\n]*`', hide, line)
            hidden = re.sub(r'\*\*(?=\S)(.+?)(?<=\S)\*\*', r'<strong>\1</strong>', hidden)
            lines.append(re.sub(r'\x00(\d+)\x00', lambda m: spans[int(m.group(1))], hidden))
        out.append(''.join(lines))
    return ''.join(out)


def check_forbidden(name, text, problems):
    for pattern in FORBIDDEN:
        for match in re.finditer(pattern, text):
            if match.group(0) == '1048450370':
                continue
            problems.append('%s: forbidden pattern %s' % (name, pattern))
            break


def render_page(title, source, commit, problems):
    path = ROOT / source
    body = path.read_text(encoding='utf-8')
    body = rewrite_links(body, path.resolve(), problems)
    relative = path.relative_to(REPO).as_posix()
    banner = ('%s\n> 本页由仓库 [`%s`](%s/blob/main/%s) 自动生成（提交 `%s`）。**请到仓库修改，不要直接改 wiki**，否则下次同步会被覆盖。\n\n'
              % (MARKER, relative, GITHUB, relative, commit))
    return bold_to_html(banner + body)


def render_home(commit):
    lines = [MARKER, '# Claude-Guardian Wiki', '',
             '让 Agent 带着真实经验，陪你把 Claude 的使用环境准备好、查清楚、配稳。这里放面向用户的教程；规则、依据和脚本在[仓库](%s)里。' % GITHUB, '',
             '> 教程里的命令和路径只是起点：每个人的系统版本、应用版本和环境都不一样。让你的 Agent 先核对实际环境，再按差异调整；做不了的时候停下，不要硬来。不承诺免封。', '']
    for group in GROUP_ORDER:
        lines.append('## %s' % group)
        lines.append('')
        for title, _, g in PAGES:
            if g == group:
                lines.append('- [%s](%s)' % (title, page_name(title)))
        lines.append('')
    lines += ['## 交流与反馈', '', CHANNEL.rstrip('\n'), '- 问题反馈：[Issues](%s/issues)' % GITHUB,
              '- 你在自己环境里用过某一项？[真机使用反馈](%s/issues/new?template=device-report.yml)（作者只在一台 Mac 上验证过，其余由使用者验证，成功或失败都有用）' % GITHUB, '',
              '不要在频道、群或 Issue 里发真实账号、凭据、订阅链接、节点密码或完整代理配置。', '',
              '页面由仓库 `tools/export_wiki.py` 生成（提交 `%s`）。' % commit, '']
    return bold_to_html('\n'.join(lines))


def render_sidebar():
    lines = [MARKER, '**[首页](Home)**', '']
    for group in GROUP_ORDER:
        lines.append('**%s**' % group)
        for title, _, g in PAGES:
            if g == group:
                lines.append('- [%s](%s)' % (title, page_name(title)))
        lines.append('')
    return bold_to_html('\n'.join(lines))


def build(commit):
    """Return ({file name: text}, problems) without touching the disk."""
    problems, files = [], {}
    for title, source, _ in PAGES:
        files[page_name(title) + '.md'] = render_page(title, source, commit, problems)
    files['Home.md'] = render_home(commit)
    files['_Sidebar.md'] = render_sidebar()
    for name, text in files.items():
        check_forbidden(name, text, problems)
    return files, problems


def head_commit():
    try:
        return subprocess.run(['git', '-C', str(REPO), 'rev-parse', '--short', 'HEAD'], capture_output=True,
                              text=True, check=True, timeout=10).stdout.strip()
    except (OSError, subprocess.SubprocessError):
        return 'unknown'


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument('--output', required=True, type=Path, help='a clone of the .wiki.git repository (or an empty directory)')
    parser.add_argument('--commit', default=None, help='source commit shown in the banner (default: HEAD)')
    args = parser.parse_args(argv)
    files, problems = build(args.commit or head_commit())
    if problems:
        print('\n'.join(problems), file=sys.stderr)
        return 2
    args.output.mkdir(parents=True, exist_ok=True)
    for stale in args.output.glob('*.md'):
        if stale.name not in files and MARKER in stale.read_text(encoding='utf-8', errors='replace'):
            stale.unlink()
    for name, text in files.items():
        (args.output / name).write_text(text, encoding='utf-8')
    print('wrote %d pages to %s' % (len(files), args.output))
    return 0


if __name__ == '__main__':
    sys.exit(main())
