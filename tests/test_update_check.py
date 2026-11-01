"""Skill update check: comparison and reporting with GitHub mocked out (ADR-053)."""
import contextlib
import hashlib
import io
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import unittest
from unittest.mock import patch
import urllib.error

REPO = Path(__file__).resolve().parents[1]
SCRIPTS = REPO / 'skills/claude-guardian/scripts'
sys.path.insert(0, str(SCRIPTS))
import update_check as uc

PREFIX = uc.SKILL_PREFIX


def tree_for(files, truncated=False):
    entries = [{'path': PREFIX + name, 'type': 'blob', 'sha': uc.blob_hash(data)} for name, data in files.items()]
    entries.append({'path': PREFIX.rstrip('/'), 'type': 'tree', 'sha': 'x'})
    entries.append({'path': 'README.md', 'type': 'blob', 'sha': uc.blob_hash(b'outside the skill')})
    return {'tree': entries, 'truncated': truncated}


COMMITS = [{'sha': 'abcdef1234567', 'commit': {'committer': {'date': '2026-11-01T08:00:00Z'},
                                               'message': 'docs: newest change\n\nbody'}}]


def fake_fetch(tree, commits=COMMITS, calls=None):
    def fetch(url, timeout):
        if calls is not None:
            calls.append(url)
        if '/git/trees/' in url:
            if isinstance(tree, Exception):
                raise tree
            return tree
        if isinstance(commits, Exception):
            raise commits
        return commits
    return fetch


class UpdateCheck(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.addCleanup(shutil.rmtree, self.tmp)
        self.files = {'SKILL.md': b'# skill\n', 'scripts/a.py': b'print(1)\n', 'references/r.md': b'text\n'}
        for name, data in self.files.items():
            (self.tmp / name).parent.mkdir(parents=True, exist_ok=True)
            (self.tmp / name).write_bytes(data)

    def run_check(self, tree, **kw):
        return uc.check(root=self.tmp, fetch=fake_fetch(tree, **kw))

    def test_blob_hash_matches_git(self):
        self.assertEqual(uc.blob_hash(b''), 'e69de29bb2d1d6434b8b29ae775ad8c2e48c5391')
        self.assertEqual(uc.blob_hash(b'hello\n'), 'ce013625030ba8dba906f756967f9e9ca394464a')
        if shutil.which('git'):
            data = (REPO / 'LICENSE').read_bytes()
            out = subprocess.run(['git', 'hash-object', '--stdin'], input=data, capture_output=True, check=True).stdout
            self.assertEqual(uc.blob_hash(data), out.decode().strip())

    def test_identical_files_are_up_to_date_and_list_recent_updates(self):
        report = self.run_check(tree_for(self.files))
        self.assertEqual(report['status'], 'up_to_date')
        self.assertEqual((report['changed'], report['upstream_only'], report['local_only']), ([], [], []))
        self.assertEqual(report['recent_updates'], [{'sha': 'abcdef1', 'date': '2026-11-01', 'subject': 'docs: newest change'}])
        self.assertIn('已是最新', uc.summary(report))

    def test_changed_new_and_local_only_files_are_reported(self):
        remote = dict(self.files, **{'scripts/a.py': b'print(2)\n', 'references/new.md': b'new\n'})
        del remote['references/r.md']
        report = self.run_check(tree_for(remote))
        self.assertEqual(report['status'], 'update_available')
        self.assertEqual(report['changed'], ['scripts/a.py'])
        self.assertEqual(report['upstream_only'], ['references/new.md'])
        self.assertEqual(report['local_only'], ['references/r.md'])
        text = uc.summary(report)
        for term in ('有更新', 'scripts/a.py', 'references/new.md', '本地独有', 'docs: newest change'):
            self.assertIn(term, text)

    def test_only_local_extra_files_do_not_count_as_an_update(self):
        (self.tmp / 'my-notes.md').write_bytes(b'mine\n')
        report = self.run_check(tree_for(self.files))
        self.assertEqual(report['status'], 'up_to_date')
        self.assertEqual(report['local_only'], ['my-notes.md'])

    def test_crlf_checkout_is_not_reported_as_changed(self):
        # Windows clones with core.autocrlf=true hold CRLF files whose git blobs are LF.
        (self.tmp / 'references/r.md').write_bytes(b'text\r\n')
        self.assertEqual(self.run_check(tree_for(self.files))['status'], 'up_to_date')

    def test_caches_license_and_symlinks_are_ignored(self):
        (self.tmp / 'scripts/__pycache__').mkdir()
        (self.tmp / 'scripts/__pycache__/a.cpython-312.pyc').write_bytes(b'\0')
        (self.tmp / 'scripts/b.pyc').write_bytes(b'\0')
        (self.tmp / '.DS_Store').write_bytes(b'\0')
        (self.tmp / 'LICENSE').write_bytes(b'GPL\n')
        try:
            (self.tmp / 'link.md').symlink_to(self.tmp / 'SKILL.md')
        except (OSError, NotImplementedError):
            pass
        report = self.run_check(tree_for(self.files))
        self.assertEqual(report['local_only'], [])

    def test_network_failure_rate_limit_and_bad_replies_fail_closed_without_blocking(self):
        cases = [
            uc.CheckError('连不上 GitHub：timed out'),
            {'tree': [], 'truncated': False},  # no SKILL.md upstream
            {'nope': 1},
            tree_for(self.files, truncated=True),
        ]
        for tree in cases:
            report = self.run_check(tree)
            self.assertEqual(report['status'], 'check_failed', tree)
            self.assertIn('用已安装的版本继续', uc.summary(report))

    def test_commit_history_failure_still_answers(self):
        report = self.run_check(tree_for(self.files), commits=uc.CheckError('限流'))
        self.assertEqual((report['status'], report['recent_updates']), ('up_to_date', []))
        report = self.run_check(tree_for(self.files), commits=[{'broken': True}, 'x'])
        self.assertEqual(report['recent_updates'], [])

    def test_missing_skill_md_locally_fails(self):
        (self.tmp / 'SKILL.md').unlink()
        report = self.run_check(tree_for(self.files))
        self.assertEqual(report['status'], 'check_failed')

    def test_requests_go_only_to_github_api_for_the_skill_path(self):
        calls = []
        uc.check(root=self.tmp, repo='o/r', ref='main', fetch=fake_fetch(tree_for(self.files), calls=calls))
        self.assertEqual(len(calls), 2)
        self.assertTrue(all(u.startswith('https://api.github.com/repos/o/r/') for u in calls), calls)
        self.assertIn('path=skills%2Fclaude-guardian', calls[1])
        for url in calls:
            self.assertNotIn('claude.ai', url)
            self.assertNotIn('anthropic', url)

    def test_fetch_json_maps_http_and_network_errors(self):
        def raise_(exc):
            def opener(*a, **k):
                raise exc
            return opener
        for exc, term in ((urllib.error.HTTPError('u', 403, 'x', {}, None), '限流'),
                          (urllib.error.HTTPError('u', 500, 'x', {}, None), 'HTTP 500'),
                          (urllib.error.URLError('timed out'), '连不上 GitHub'),
                          (TimeoutError('slow'), '连不上 GitHub')):
            with patch.object(uc.urllib.request, 'urlopen', raise_(exc)):
                with self.assertRaises(uc.CheckError) as ctx:
                    uc.fetch_json('https://api.github.com/x', 1)
                self.assertIn(term, str(ctx.exception))

    def test_fetch_json_rejects_oversized_and_non_json_replies(self):
        class Reply(io.BytesIO):
            def __enter__(self):
                return self

            def __exit__(self, *a):
                return False
        for body, term in ((b'x' * (uc.MAX_BYTES + 1), '过大'), (b'<html>', 'JSON')):
            with patch.object(uc.urllib.request, 'urlopen', lambda *a, **k: Reply(body)):
                with self.assertRaises(uc.CheckError) as ctx:
                    uc.fetch_json('https://api.github.com/x', 1)
                self.assertIn(term, str(ctx.exception))

    def test_cli_exit_codes_json_and_cancel(self):
        for status, code in (('up_to_date', 0), ('update_available', 1), ('check_failed', 2)):
            report = {'status': status, 'repo': 'o/r', 'ref': 'main', 'reason': 'x', 'changed': [],
                      'upstream_only': [], 'local_only': [], 'recent_updates': []}
            out = io.StringIO()
            with patch.object(uc, 'check', return_value=report), contextlib.redirect_stdout(out):
                self.assertEqual(uc.main(['check', '--json']), code)
            self.assertEqual(json.loads(out.getvalue())['status'], status)
        err = io.StringIO()
        with patch.object(uc, 'check', side_effect=KeyboardInterrupt), contextlib.redirect_stderr(err):
            self.assertEqual(uc.main(['check']), 130)
        for bad in (['check', '--timeout', '0'], ['check', '--repo', 'noslash'], []):
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                uc.main(bad)

    def test_help_runs_without_network(self):
        out = subprocess.run([sys.executable, '-I', str(SCRIPTS / 'update_check.py'), '--help'],
                             capture_output=True, text=True, check=True).stdout
        self.assertIn('api.github.com', out)

    def test_skill_md_tells_the_agent_to_check_first_and_not_block(self):
        skill = (REPO / 'skills/claude-guardian/SKILL.md').read_text(encoding='utf-8')
        start = skill.split('## 开始方式', 1)[1].split('\n1. ', 1)[0]
        for term in ('scripts/update_check.py check', 'references/skill-update.md', '不阻塞'):
            self.assertIn(term, start)
        guide = (REPO / 'skills/claude-guardian/references/skill-update.md').read_text(encoding='utf-8')
        for term in ('每个会话开始时查一次', 'Skill 目录之外', '不阻塞任务', 'B 档', '开一个新会话', '回滚'):
            self.assertIn(term, guide)
        # The backup and the temporary clone live outside the Skill directory; the guide must not deny it.
        self.assertNotIn('整个过程不改 Skill 目录以外的东西', guide)


if __name__ == '__main__':
    unittest.main()
