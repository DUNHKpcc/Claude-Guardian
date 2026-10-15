#!/usr/bin/env python3
"""Render only built-in synthetic dashboard data; browser capture is CI-only."""
import argparse
from datetime import datetime, timezone
import hashlib
from html.parser import HTMLParser
from html import escape
import json
import os
from pathlib import Path
import re
import shutil
import signal
import struct
import subprocess
import sys
import tempfile
import time
import urllib.request

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / 'skills/claude-guardian/scripts'))
import status_dashboard

FONT_COMMIT = 'f8d157532fbfaeda587e826d4cd5b21a49186f7c'
FONT_PATH = 'Sans/OTF/SimplifiedChinese/NotoSansCJKsc-Regular.otf'
FONT_URL = 'https://raw.githubusercontent.com/notofonts/noto-cjk/' + FONT_COMMIT + '/' + FONT_PATH
FONT_SHA256 = '2c76254f6fc379fddfce0a7e84fb5385bb135d3e399294f6eeb6680d0365b74b'
FONT_LIMIT = 20 * 1024 * 1024

NOW = datetime(2026, 10, 15, 12, tzinfo=timezone.utc)
VIEWPORTS = {'desktop': (1440, 1000), 'mobile': (390, 1100)}
FLAGS = ('--headless', '--no-first-run', '--no-default-browser-check',
         '--disable-background-networking', '--disable-component-update',
         '--disable-default-apps', '--disable-sync', '--metrics-recording-only',
         '--force-device-scale-factor=1', '--hide-scrollbars')


class PreviewError(Exception):
    pass


class StaticHTML(HTMLParser):
    """Fail closed if future renderer changes add active or resource-bearing HTML."""
    TAGS = {'html', 'head', 'meta', 'title', 'style', 'body', 'main', 'header',
            'h1', 'span', 'p', 'table', 'caption', 'colgroup', 'col', 'thead',
            'tr', 'th', 'tbody', 'td', 'details', 'summary', 'footer'}

    def handle_starttag(self, tag, attrs):
        if tag not in self.TAGS:
            raise PreviewError('PREVIEW_ACTIVE_HTML_REJECTED')
        attrs = dict(attrs)
        if any(key.startswith('on') or key in {'src', 'href', 'srcset', 'action',
                                             'background', 'style'} for key in attrs):
            raise PreviewError('PREVIEW_RESOURCE_ATTRIBUTE_REJECTED')
        if tag == 'meta' and attrs.get('http-equiv', '').lower() not in {'', 'content-security-policy'}:
            raise PreviewError('PREVIEW_META_REJECTED')

    handle_startendtag = handle_starttag


def synthetic_html():
    report = {'schema_version': 'guardian-report/0.1',
              'record_kind': 'synthetic_example', 'execution_status': 'completed',
              'snapshot': {'observed_at': NOW.isoformat()}, 'findings': [],
              'facts': [{'id': 'S01', 'state': 'observed', 'value': 'macos',
                         'observed_at': NOW.isoformat()},
                        {'id': 'P06', 'state': 'observed', 'value': {'enabled': False},
                         'observed_at': NOW.isoformat()}]}
    html = status_dashboard.render(report, NOW)
    validate_html(html)
    return html


def validate_html(html):
    parser = StaticHTML()
    parser.feed(html)
    parser.close()
    # No CSS escapes, resource functions or imports. The production CSS needs none.
    if re.search(r'url\s*\(|@import|\\', html, re.IGNORECASE):
        raise PreviewError('PREVIEW_EXTERNAL_CSS_REJECTED')
    if "default-src 'none'" not in html or '合成演示' not in html:
        raise PreviewError('PREVIEW_REQUIRED_LABEL_OR_CSP_MISSING')


def require_ci():
    if os.environ.get('GITHUB_ACTIONS') != 'true' or os.environ.get('RUNNER_OS') != 'Linux':
        raise PreviewError('PREVIEW_CAPTURE_REQUIRES_LINUX_GITHUB_ACTIONS')
    if hasattr(os, 'geteuid') and os.geteuid() == 0:
        raise PreviewError('PREVIEW_CAPTURE_REQUIRES_NONROOT_RUNNER')


def find_browser():
    for name in ('google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser'):
        found = shutil.which(name)
        if found:
            return found
    raise PreviewError('PREVIEW_CHROME_MISSING: use the official runner image; no automatic install')


def cjk_fonts(env=None):
    command = shutil.which('fc-list')
    if not command:
        raise PreviewError('PREVIEW_FONTCONFIG_MISSING')
    result = subprocess.run([command, ':lang=zh', 'family'], check=True,
                            capture_output=True, text=True, timeout=15, env=env)
    families = sorted(set(line.strip() for line in result.stdout.splitlines() if line.strip()))
    if not families:
        raise PreviewError('PREVIEW_CJK_FONT_MISSING: no automatic font installation')
    return families[:20]


class NoFontRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        raise PreviewError('PREVIEW_FONT_REDIRECT_REJECTED')


def download_font():
    """One credential-free pinned HTTPS read; never accept redirects or bad hashes."""
    opener = urllib.request.build_opener(urllib.request.ProxyHandler({}), NoFontRedirect())
    started = time.monotonic()
    chunks = []
    count = 0
    with opener.open(FONT_URL, timeout=30) as response:
        if response.status != 200 or response.geturl() != FONT_URL:
            raise PreviewError('PREVIEW_FONT_RESPONSE_REJECTED')
        length = response.headers.get('Content-Length')
        if length is not None and (not length.isdecimal() or int(length) > FONT_LIMIT):
            raise PreviewError('PREVIEW_FONT_SIZE_REJECTED')
        while True:
            chunk = response.read(min(65536, FONT_LIMIT + 1 - count))
            count += len(chunk)
            if count > FONT_LIMIT:
                raise PreviewError('PREVIEW_FONT_SIZE_REJECTED')
            if time.monotonic() - started > 60:
                raise PreviewError('PREVIEW_FONT_DOWNLOAD_TIMEOUT')
            if not chunk:
                break
            chunks.append(chunk)
    data = b''.join(chunks)
    if hashlib.sha256(data).hexdigest() != FONT_SHA256:
        raise PreviewError('PREVIEW_FONT_HASH_MISMATCH')
    return data


def font_environment(work):
    fonts = work / 'fonts'
    cache = work / 'font-cache'
    fonts.mkdir(mode=0o700)
    cache.mkdir(mode=0o700)
    # Verify all bytes before any font parser sees the asset.
    (fonts / 'NotoSansCJKsc-Regular.otf').write_bytes(download_font())
    config = work / 'fonts.conf'
    config.write_text('<?xml version="1.0"?><fontconfig><dir>' + escape(str(fonts)) +
                      '</dir><cachedir>' + escape(str(cache)) + '</cachedir></fontconfig>',
                      encoding='utf-8')
    env = dict(os.environ)
    env['FONTCONFIG_FILE'] = str(config)
    env['FONTCONFIG_PATH'] = str(work)
    env.pop('FONTCONFIG_SYSROOT', None)
    return env


def png_dimensions(path):
    data = path.read_bytes()
    if len(data) < 33 or data[:8] != b'\x89PNG\r\n\x1a\n' or data[12:16] != b'IHDR':
        raise PreviewError('PREVIEW_INVALID_PNG')
    return struct.unpack('>II', data[16:24])


def wait_browser_exit(process, timeout):
    """Observe Linux child exit without reaping, reserving its PID until group cleanup."""
    deadline = time.monotonic() + timeout
    while True:
        info = os.waitid(os.P_PID, process.pid, os.WEXITED | os.WNOHANG | os.WNOWAIT)
        if info is not None:
            return info.si_status if info.si_code == os.CLD_EXITED else -info.si_status
        if time.monotonic() >= deadline:
            raise subprocess.TimeoutExpired(process.args, timeout)
        time.sleep(min(0.05, max(0, deadline - time.monotonic())))


def run_browser(command, timeout=60, env=None):
    """Own one new POSIX process group; discard logs and kill remaining members.

    Descendants that deliberately escape this group are outside this guarantee.
    No process search, existing profile or unrelated browser group is targeted.
    """
    options = {'env': env} if env is not None else {}
    process = subprocess.Popen(command, start_new_session=True,
                               stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, **options)
    try:
        returncode = wait_browser_exit(process, timeout)
        if returncode:
            raise subprocess.CalledProcessError(returncode, command)
    finally:
        # Also clear ordinary helper processes after a successful leader exit.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as error:
            # Best effort reap of the owned leader remains bounded if kill failed.
            try:
                process.wait(timeout=5)
            except subprocess.TimeoutExpired:
                pass
            raise PreviewError('PREVIEW_PROCESS_GROUP_CLEANUP_FAILED') from error
        try:
            process.wait(timeout=5)
        except subprocess.TimeoutExpired as error:
            raise PreviewError('PREVIEW_PROCESS_REAP_TIMEOUT') from error


def capture(output, ci_font=False):
    require_ci()
    if not ci_font:
        return capture_with_environment(output)
    with tempfile.TemporaryDirectory(prefix='guardian-font-') as temp:
        env = font_environment(Path(temp))
        return capture_with_environment(output, env, {
            'url': FONT_URL, 'sha256': FONT_SHA256, 'license': 'OFL-1.1',
            'license_url': 'https://github.com/notofonts/noto-cjk/blob/' + FONT_COMMIT + '/Sans/LICENSE'})


def capture_with_environment(output, env=None, font_metadata=None):
    require_ci()
    browser = find_browser()
    fonts = cjk_fonts(env)
    version = subprocess.run([browser, '--version'], check=True, capture_output=True,
                             text=True, timeout=15).stdout.strip()
    if not version or len(version) > 200:
        raise PreviewError('PREVIEW_INVALID_BROWSER_VERSION')
    # Refuse existing destinations, including symlinks; never upload mixed user files.
    output = Path(output).absolute()
    output.mkdir(parents=False, exist_ok=False, mode=0o700)
    html = synthetic_html()
    manifest = {'schema_version': 'guardian-dashboard-preview/0.1',
                'record_kind': 'synthetic_example', 'browser_version': version,
                'fixture_time': NOW.isoformat(), 'cjk_font_families': fonts,
                'html_sha256': hashlib.sha256(html.encode()).hexdigest(),
                'scope': 'Layout preview only; no device, DNS, proxy or Claude verification',
                'network_isolation_verified': False, 'screenshots': {}}
    if font_metadata is not None:
        manifest['preview_font_asset'] = font_metadata
    # Browser profile, HTML and logs are never placed in the artifact directory.
    with tempfile.TemporaryDirectory(prefix='guardian-preview-') as temp:
        work = Path(temp)
        page = work / 'synthetic.html'
        page.write_text(html, encoding='utf-8')
        for name, (width, height) in VIEWPORTS.items():
            png = work / (name + '.png')
            profile = work / (name + '-profile')
            profile.mkdir(mode=0o700)
            command = [browser, *FLAGS, '--user-data-dir=' + str(profile),
                       '--window-size=%d,%d' % (width, height),
                       '--screenshot=' + str(png), page.as_uri()]
            run_browser(command, env=env)
            if png_dimensions(png) != (width, height):
                raise PreviewError('PREVIEW_VIEWPORT_MISMATCH')
            data = png.read_bytes()
            (output / png.name).write_bytes(data)
            manifest['screenshots'][png.name] = {'width': width, 'height': height,
                                                'sha256': hashlib.sha256(data).hexdigest()}
    (output / 'manifest.json').write_text(json.dumps(manifest, ensure_ascii=False,
                                                    indent=2) + '\n', encoding='utf-8')
    return manifest


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New HTML file or new screenshot directory')
    parser.add_argument('--capture-ci', action='store_true', help='Run installed Chrome on GitHub Linux runner only')
    parser.add_argument('--ci-font', action='store_true', help='Explicit CI-only pinned ephemeral Noto CJK asset download')
    args = parser.parse_args(argv)
    if args.ci_font and not args.capture_ci:
        parser.error('--ci-font requires --capture-ci')
    try:
        if args.capture_ci:
            capture(args.output, ci_font=args.ci_font)
        else:
            with open(args.output, 'x', encoding='utf-8') as stream:
                stream.write(synthetic_html())
    except KeyboardInterrupt:
        print('PREVIEW_CANCELLED', file=sys.stderr)
        return 3
    except (PreviewError, OSError, subprocess.SubprocessError) as error:
        # Do not print arbitrary subprocess output or environment values.
        print(str(error) if isinstance(error, PreviewError) else
              'PREVIEW_FAILED: ' + type(error).__name__, file=sys.stderr)
        return 2
    print('PREVIEW_SAVED: synthetic layout only; no actual diagnostic checks')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
