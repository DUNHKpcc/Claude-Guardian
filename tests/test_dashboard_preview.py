"""Synthetic capture contracts. Browser calls are mocked; this is not visual QA."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import struct
import sys
import time
import subprocess
import tempfile
import unittest
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
spec = importlib.util.spec_from_file_location('dashboard_preview', ROOT / 'tools/render_dashboard_preview.py')
preview = importlib.util.module_from_spec(spec)
spec.loader.exec_module(preview)


def fake_png(width, height):
    # Header fixture only. It must never be delivered as a real screenshot.
    return b'\x89PNG\r\n\x1a\n' + struct.pack('>I', 13) + b'IHDR' + struct.pack('>II', width, height) + b'\x00' * 9


class PreviewTests(unittest.TestCase):
    def test_fixture_deterministic_and_real_renderer(self):
        first = preview.synthetic_html()
        self.assertEqual(first, preview.synthetic_html())
        self.assertIn('合成演示', first)
        self.assertIn('无自动检测', first)
        self.assertEqual(first.count('data-check='), 11)
        self.assertIn(preview.status_dashboard.CSS, first)

    def test_active_html_and_external_css_rejected(self):
        for fragment in ('<script></script>', '<img src="https://example.com">',
                         '<p onclick="x()">x</p>', '<meta http-equiv="refresh" content="1">',
                         '<style>@import "https://example.com";</style>',
                         '<style>body{background:url(https://example.com)}</style>',
                         '<style>body{background:u\\72l(x)}</style>'):
            with self.subTest(fragment=fragment), self.assertRaises(preview.PreviewError):
                preview.validate_html(preview.synthetic_html() + fragment)

    def test_browser_not_invoked_outside_ci(self):
        with patch.dict(os.environ, {}, clear=True), patch.object(preview.subprocess, 'run') as run:
            with self.assertRaises(preview.PreviewError):
                preview.capture('unused')
            run.assert_not_called()

    def test_root_runner_rejected(self):
        with patch.dict(os.environ, {'GITHUB_ACTIONS': 'true', 'RUNNER_OS': 'Linux'}), \
             patch.object(preview.os, 'geteuid', return_value=0, create=True):
            with self.assertRaises(preview.PreviewError):
                preview.require_ci()

    def test_missing_browser_and_font_fail_without_install(self):
        with patch.object(preview.shutil, 'which', return_value=None):
            with self.assertRaises(preview.PreviewError): preview.find_browser()
            with self.assertRaises(preview.PreviewError): preview.cjk_fonts()
        with patch.object(preview.shutil, 'which', return_value='/usr/bin/fc-list'), \
             patch.object(preview.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='')):
            with self.assertRaises(preview.PreviewError): preview.cjk_fonts()

    def test_html_cli_never_opens_browser_or_overwrites(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(preview.subprocess, 'run') as run, \
             contextlib.redirect_stdout(io.StringIO()), contextlib.redirect_stderr(io.StringIO()):
            path = Path(tmp) / 'preview.html'
            self.assertEqual(preview.main(['--output', str(path)]), 0)
            before = path.read_bytes()
            self.assertEqual(preview.main(['--output', str(path)]), 2)
            self.assertEqual(path.read_bytes(), before)
            run.assert_not_called()

    def test_capture_contract_and_exact_artifact_contents(self):
        commands = []
        def run(command, **kwargs):
            commands.append(command)
            if command[-1] == '--version':
                return subprocess.CompletedProcess(command, 0, stdout='Google Chrome test-version\n')
            png = Path(next(arg.split('=', 1)[1] for arg in command if arg.startswith('--screenshot=')))
            width, height = map(int, next(arg.split('=', 1)[1] for arg in command if arg.startswith('--window-size=')).split(','))
            profile = Path(next(arg.split('=', 1)[1] for arg in command if arg.startswith('--user-data-dir=')))
            self.assertTrue(profile.is_dir())
            self.assertEqual(list(profile.iterdir()), [])
            self.assertTrue(command[-1].startswith('file://'))
            self.assertNotIn('--no-sandbox', command)
            self.assertNotIn('--disable-web-security', command)
            png.write_bytes(fake_png(width, height))
            return subprocess.CompletedProcess(command, 0)
        with tempfile.TemporaryDirectory() as tmp, \
             patch.object(preview, 'require_ci'), \
             patch.object(preview, 'find_browser', return_value='/usr/bin/google-chrome'), \
             patch.object(preview, 'cjk_fonts', return_value=['Noto Sans CJK SC']), \
             patch.object(preview.subprocess, 'run', side_effect=run), \
             patch.object(preview, 'run_browser', side_effect=run):
            output = Path(tmp) / 'artifact'
            manifest = preview.capture(output)
            self.assertEqual({p.name for p in output.iterdir()}, {'desktop.png', 'mobile.png', 'manifest.json'})
            self.assertEqual(json.loads((output / 'manifest.json').read_text()), manifest)
            self.assertFalse(manifest['network_isolation_verified'])
            self.assertEqual(manifest['cjk_font_families'], ['Noto Sans CJK SC'])
            self.assertEqual(len(commands), 3)
            with self.assertRaises(FileExistsError): preview.capture(output)

    def test_timeout_never_creates_success_manifest(self):
        with tempfile.TemporaryDirectory() as tmp, patch.object(preview, 'require_ci'), \
             patch.object(preview, 'find_browser', return_value='/usr/bin/google-chrome'), \
             patch.object(preview, 'cjk_fonts', return_value=['CJK']), \
             patch.object(preview.subprocess, 'run', return_value=subprocess.CompletedProcess([], 0, stdout='Chrome test')), \
             patch.object(preview, 'run_browser', side_effect=subprocess.TimeoutExpired('chrome', 60)):
            output = Path(tmp) / 'artifact'
            with self.assertRaises(subprocess.TimeoutExpired): preview.capture(output)
            self.assertFalse((output / 'manifest.json').exists())


    # These tests mock Linux behavior even on Windows, which has no SIGKILL.
    @patch.object(preview.signal, 'SIGKILL', 9, create=True)
    def test_browser_group_cleanup_success_timeout_cancel_and_failure(self):
        for outcome in (0, 7, subprocess.TimeoutExpired('browser', 60), KeyboardInterrupt()):
            with self.subTest(outcome=type(outcome).__name__), \
                 patch.object(preview.subprocess, 'Popen') as popen, \
                 patch.object(preview.os, 'killpg', create=True) as killpg, \
                 patch.object(preview, 'wait_browser_exit') as wait_exit:
                process = popen.return_value
                process.pid = 54321
                if isinstance(outcome, BaseException):
                    wait_exit.side_effect = outcome
                else:
                    wait_exit.return_value = outcome
                process.wait.return_value = 0
                if outcome == 0:
                    preview.run_browser(['synthetic-browser'])
                else:
                    with self.assertRaises((subprocess.SubprocessError, KeyboardInterrupt)):
                        preview.run_browser(['synthetic-browser'])
                popen.assert_called_once_with(['synthetic-browser'], start_new_session=True,
                    stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                killpg.assert_called_once_with(54321, preview.signal.SIGKILL)
                self.assertEqual(process.wait.call_args_list[-1].kwargs, {'timeout': 5})

    @patch.object(preview.signal, 'SIGKILL', 9, create=True)
    def test_cleanup_failure_is_explicit_and_reap_bounded(self):
        with patch.object(preview.subprocess, 'Popen') as popen, \
             patch.object(preview.os, 'killpg', side_effect=PermissionError(), create=True), \
             patch.object(preview, 'wait_browser_exit', return_value=0):
            popen.return_value.wait.side_effect = subprocess.TimeoutExpired('browser', 5)
            with self.assertRaisesRegex(preview.PreviewError, 'CLEANUP_FAILED'):
                preview.run_browser(['synthetic-browser'])
        with patch.object(preview.subprocess, 'Popen') as popen, \
             patch.object(preview.os, 'killpg', create=True), \
             patch.object(preview, 'wait_browser_exit', return_value=0):
            popen.return_value.wait.side_effect = subprocess.TimeoutExpired('browser', 5)
            with self.assertRaisesRegex(preview.PreviewError, 'REAP_TIMEOUT'):
                preview.run_browser(['synthetic-browser'])

    @unittest.skipUnless(sys.platform == 'linux', 'POSIX owned process group regression')
    def test_owned_child_tree_is_stopped_on_timeout_without_browser(self):
        with tempfile.TemporaryDirectory() as tmp:
            marker = str(Path(tmp) / 'descendant-survived')
            ready = Path(tmp) / 'ready'
            child = "import pathlib,time;time.sleep(1);pathlib.Path(%r).write_text('bad')" % marker
            leader = ("import subprocess,sys,time,pathlib;"
                      "subprocess.Popen([sys.executable,'-c',%r]);"
                      "pathlib.Path(%r).write_text('ready');time.sleep(30)") % (child, str(ready))
            # No browser or network: descendants inherit only DEVNULL log handles.
            with self.assertRaises(subprocess.TimeoutExpired):
                preview.run_browser([sys.executable, '-c', leader], timeout=0.5)
            self.assertTrue(ready.exists(), 'child creation must occur before timeout')
            time.sleep(0.8)
            self.assertFalse(Path(marker).exists())

    def font_response(self, opener, data=b'synthetic font bytes', headers=None):
        response = opener.return_value.open.return_value.__enter__.return_value
        response.status = 200
        response.geturl.return_value = preview.FONT_URL
        response.headers = headers or {}
        response.read.side_effect = [data, b'']
        return response

    def test_pinned_font_download_hash_and_byte_bounds(self):
        data = b'synthetic font bytes'
        with patch.object(preview.urllib.request, 'build_opener') as opener, \
             patch.object(preview, 'FONT_SHA256', preview.hashlib.sha256(data).hexdigest()):
            self.font_response(opener, data)
            self.assertEqual(preview.download_font(), data)
            opener.return_value.open.assert_called_once_with(preview.FONT_URL, timeout=30)
            handlers = opener.call_args.args
            self.assertEqual(handlers[0].proxies, {})
            self.assertIsInstance(handlers[1], preview.NoFontRedirect)
        with patch.object(preview.urllib.request, 'build_opener') as opener:
            self.font_response(opener)
            with self.assertRaisesRegex(preview.PreviewError, 'HASH_MISMATCH'):
                preview.download_font()
        for headers in ({'Content-Length': str(preview.FONT_LIMIT + 1)}, {'Content-Length': '-1'}):
            with patch.object(preview.urllib.request, 'build_opener') as opener:
                response = self.font_response(opener, headers=headers)
                with self.assertRaisesRegex(preview.PreviewError, 'SIZE_REJECTED'):
                    preview.download_font()
                response.read.assert_not_called()
        with patch.object(preview.urllib.request, 'build_opener') as opener, \
             patch.object(preview, 'FONT_LIMIT', 4):
            self.font_response(opener, b'12345')
            with self.assertRaisesRegex(preview.PreviewError, 'SIZE_REJECTED'):
                preview.download_font()

    def test_font_redirect_http_error_and_timeout_fail_closed(self):
        with self.assertRaisesRegex(preview.PreviewError, 'REDIRECT_REJECTED'):
            preview.NoFontRedirect().redirect_request(None, None, 302, '', {}, 'https://other.example/font')
        for status, url in ((403, preview.FONT_URL), (200, 'https://other.example/font')):
            with patch.object(preview.urllib.request, 'build_opener') as opener:
                response = self.font_response(opener)
                response.status = status
                response.geturl.return_value = url
                with self.assertRaisesRegex(preview.PreviewError, 'RESPONSE_REJECTED'):
                    preview.download_font()
                response.read.assert_not_called()
        with patch.object(preview.urllib.request, 'build_opener') as opener, \
             patch.object(preview.time, 'monotonic', side_effect=[0, 61]):
            self.font_response(opener)
            with self.assertRaisesRegex(preview.PreviewError, 'DOWNLOAD_TIMEOUT'):
                preview.download_font()
        with patch.object(preview.urllib.request, 'build_opener') as opener:
            opener.return_value.open.side_effect = OSError('network unavailable')
            with self.assertRaises(OSError): preview.download_font()

    def test_font_environment_owned_paths_and_no_global_mutation(self):
        before = dict(os.environ)
        with tempfile.TemporaryDirectory() as tmp, patch.object(preview, 'download_font', return_value=b'fixture'):
            work = Path(tmp)
            env = preview.font_environment(work)
            self.assertEqual(dict(os.environ), before)
            config = Path(env['FONTCONFIG_FILE']).read_text()
            self.assertIn(str(work / 'fonts'), config)
            self.assertIn(str(work / 'font-cache'), config)
            self.assertNotIn('<include', config)
            self.assertNotIn('/etc/fonts', config)
            self.assertEqual(env['FONTCONFIG_PATH'], str(work))
            self.assertNotIn('FONTCONFIG_SYSROOT', env)

    def test_font_download_requires_explicit_ci_optin(self):
        with patch.object(preview, 'require_ci'), patch.object(preview, 'capture_with_environment'), \
             patch.object(preview, 'download_font') as download:
            preview.capture('unused')
            download.assert_not_called()
        with patch.dict(os.environ, {}, clear=True), patch.object(preview, 'download_font') as download:
            with self.assertRaises(preview.PreviewError): preview.capture('unused', ci_font=True)
            download.assert_not_called()

    def test_invalid_png_and_dimensions(self):
        with tempfile.TemporaryDirectory() as tmp:
            path = Path(tmp) / 'test.png'
            path.write_bytes(b'not a png')
            with self.assertRaises(preview.PreviewError): preview.png_dimensions(path)
            path.write_bytes(fake_png(390, 1100))
            self.assertEqual(preview.png_dimensions(path), (390, 1100))


if __name__ == '__main__':
    unittest.main()
