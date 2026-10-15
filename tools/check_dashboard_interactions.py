#!/usr/bin/env python3
"""CI-only real Chrome keyboard/layout checks on the built-in synthetic page.

Uses Node's standard library and an owned Chrome debugging pipe, without page
script evaluation, CSP overrides, a debug TCP listener or sandbox relaxation.
Protocol reference: https://chromedevtools.github.io/devtools-protocol/
"""
import argparse
import hashlib
import json
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile
import render_dashboard_preview as preview

FLAGS = ('keyboard_focus_order', 'visible_focus_indicator', 'enter_toggle',
         'space_toggle', 'all_details_expanded', 'horizontal_overflow_absent')


FAILURE_CODES = frozenset(('INTERACTION_ALL_OPEN_FAILED', 'INTERACTION_ARGUMENTS', 'INTERACTION_BROWSER_EXITED', 'INTERACTION_BROWSER_REAP_TIMEOUT', 'INTERACTION_BROWSER_START_FAILED', 'INTERACTION_COMMAND_FAILED', 'INTERACTION_COMMAND_TIMEOUT', 'INTERACTION_DETAILS_COUNT', 'INTERACTION_DOCUMENT_MISMATCH', 'INTERACTION_ENTER_DID_NOT_COLLAPSE', 'INTERACTION_ENTER_DID_NOT_EXPAND', 'INTERACTION_EVENT_LIMIT', 'INTERACTION_FAILED', 'INTERACTION_FOCUS_INDICATOR_MISSING', 'INTERACTION_HORIZONTAL_OVERFLOW', 'INTERACTION_KEYBOARD_FOCUS_ORDER', 'INTERACTION_LOAD_TIMEOUT', 'INTERACTION_NAVIGATION_FAILED', 'INTERACTION_NOT_INITIALLY_COLLAPSED', 'INTERACTION_PIPE_CLOSED', 'INTERACTION_PIPE_ERROR', 'INTERACTION_PROTOCOL_INVALID', 'INTERACTION_PROTOCOL_LIMIT', 'INTERACTION_REQUIRES_CI', 'INTERACTION_SPACE_DID_NOT_COLLAPSE', 'INTERACTION_SPACE_DID_NOT_EXPAND', 'INTERACTION_TOTAL_TIMEOUT', 'INTERACTION_UNEXPECTED_PAGE_RESOURCE', 'INTERACTION_UNEXPECTED_REPLY', 'INTERACTION_VERSION_INVALID'))
FAILURE_STAGES = frozenset(('Accessibility.enable', 'Accessibility.getFullAXTree', 'Browser.getVersion', 'CSS.enable', 'CSS.getComputedStyleForNode', 'DOM.describeNode', 'DOM.enable', 'DOM.getAttributes', 'DOM.getDocument', 'DOM.querySelectorAll', 'Emulation.setDeviceMetricsOverride', 'Input.dispatchKeyEvent', 'Network.enable', 'Page.bringToFront', 'Page.enable', 'Page.getLayoutMetrics', 'Page.navigate', 'Target.attachToTarget', 'Target.closeTarget', 'Target.createTarget', 'cleanup', 'save_result', 'startup', 'unknown'))


class InteractionFailure(preview.PreviewError):
    def __init__(self, code, stage):
        self.code = code if isinstance(code, str) and code in FAILURE_CODES else 'INTERACTION_FAILED'
        self.stage = stage if isinstance(stage, str) and stage in FAILURE_STAGES else 'unknown'
        super().__init__('code=' + self.code + ' stage=' + self.stage)


def read_failure(path):
    """Read only the owned private bounded diagnostic, never raw browser logs."""
    def unique(pairs):
        obj = {}
        for key, value in pairs:
            if key in obj:
                raise ValueError('duplicate')
            obj[key] = value
        return obj
    try:
        with path.open('rb') as stream:
            data = stream.read(1025)
        if len(data) > 1024:
            raise ValueError('oversized')
        record = json.loads(data.decode('utf-8'), object_pairs_hook=unique)
        if (not isinstance(record, dict) or set(record) != {'schema_version', 'code', 'stage'} or
                record['schema_version'] != 'guardian-interaction-failure/0.1' or
                not isinstance(record['code'], str) or record['code'] not in FAILURE_CODES or
                not isinstance(record['stage'], str) or record['stage'] not in FAILURE_STAGES):
            raise ValueError('invalid')
        return InteractionFailure(record['code'], record['stage'])
    except (OSError, ValueError, UnicodeError, RecursionError):
        return InteractionFailure('INTERACTION_FAILED', 'unknown')


def validate_result(result):
    required = {'schema_version', 'record_kind', 'browser_version', 'evidence_kind',
                'network_isolation_verified', 'viewports'}
    if not isinstance(result, dict) or set(result) != required:
        raise preview.PreviewError('INTERACTION_INVALID_RESULT')
    if (result['schema_version'] != 'guardian-dashboard-interaction/0.1' or
            result['record_kind'] != 'synthetic_example' or
            result['evidence_kind'] != 'ci_real_chrome_keyboard_and_layout' or
            result['network_isolation_verified'] is not False or
            not isinstance(result['browser_version'], str) or
            not 1 <= len(result['browser_version']) <= 200):
        raise preview.PreviewError('INTERACTION_INVALID_RESULT')
    rows = result['viewports']
    if not isinstance(rows, list) or len(rows) != 2:
        raise preview.PreviewError('INTERACTION_INVALID_RESULT')
    for row, dimensions in zip(rows, preview.VIEWPORTS.values()):
        keys = set(FLAGS) | {'width', 'height', 'summary_count', 'page_document_requests', 'page_subresource_requests'}
        if not isinstance(row, dict) or set(row) != keys:
            raise preview.PreviewError('INTERACTION_INVALID_RESULT')
        expected = dict(width=dimensions[0], height=dimensions[1], summary_count=12,
                        page_document_requests=1, page_subresource_requests=0)
        if any(type(row[k]) is not int or row[k] != v for k, v in expected.items()) or any(row[k] is not True for k in FLAGS):
            raise preview.PreviewError('INTERACTION_FAILED_ASSERTION')
    return result


def check(output, ci_font=False):
    preview.require_ci()
    browser = preview.find_browser()
    node = shutil.which('node')
    if not node:
        raise preview.PreviewError('INTERACTION_NODE_MISSING')
    output = Path(output).absolute()
    # Never overwrite or populate an existing directory with mixed artifacts.
    output.mkdir(parents=False, exist_ok=False, mode=0o700)
    with tempfile.TemporaryDirectory(prefix='guardian-interaction-') as temp:
        work = Path(temp)
        env = preview.font_environment(work) if ci_font else None
        preview.cjk_fonts(env)
        html = preview.synthetic_html()
        page = work / 'synthetic.html'
        page.write_text(html, encoding='utf-8')
        profile = work / 'owned-profile'
        profile.mkdir(mode=0o700)
        raw = work / 'result.json'
        diagnostic = work / 'failure.json'
        command = [node, str(Path(__file__).with_suffix('.cjs')), browser, str(page), str(profile), str(raw), str(diagnostic)]
        # Node and Chrome share the owned group; cleanup includes ordinary Chrome
        # helpers after the Node leader exits, and runs on timeout/error as well.
        try:
            preview.run_browser(command, timeout=90, env=env)
        except subprocess.CalledProcessError:
            raise read_failure(diagnostic) from None
        if not raw.is_file() or raw.stat().st_size > 16384:
            raise preview.PreviewError('INTERACTION_RESULT_MISSING_OR_OVERSIZED')
        try:
            result = validate_result(json.loads(raw.read_text(encoding='utf-8')))
        except (ValueError, UnicodeError) as error:
            raise preview.PreviewError('INTERACTION_INVALID_RESULT') from error
        result['html_sha256'] = hashlib.sha256(html.encode()).hexdigest()
        result['scope'] = 'Synthetic CI Chrome interaction only; no actual diagnostic, desktop, or whole-browser network-isolation acceptance'
        result['cjk_font_source'] = 'pinned_ephemeral_preview_font' if ci_font else 'runner_fontconfig'
        with (output / 'interaction.json').open('x', encoding='utf-8') as stream:
            json.dump(result, stream, ensure_ascii=False, indent=2)
            stream.write('\n')
    return result


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--output', required=True, help='New dedicated synthetic artifact directory')
    parser.add_argument('--ci-font', action='store_true', help='Explicit pinned ephemeral CI font used by existing preview')
    args = parser.parse_args(argv)
    try:
        check(args.output, args.ci_font)
    except KeyboardInterrupt:
        print('INTERACTION_CANCELLED', file=sys.stderr)
        return 3
    except InteractionFailure as error:
        print('INTERACTION_FAILED: ' + str(error) + '; no acceptance result published', file=sys.stderr)
        return 2
    except (preview.PreviewError, OSError, subprocess.SubprocessError):
        print('INTERACTION_FAILED: no acceptance result published', file=sys.stderr)
        return 2
    print('INTERACTION_PASSED: synthetic CI browser interaction only')
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
