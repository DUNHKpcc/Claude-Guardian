"""Explicit CI-owned metadata smoke; ordinary discovery never calls native APIs."""
import contextlib
import importlib.util
import io
import json
import os
from pathlib import Path
import subprocess
import sys
import threading
import unittest
from types import SimpleNamespace
from unittest import mock

ROOT = Path(__file__).resolve().parents[1]
FLAG = 'GUARDIAN_NATIVE_CONTEXT_CI'
LIMIT = 2048
TIMEOUT = 15
# Unknown API/ABI failures are deliberately NOT accepted as headless outcomes.
BLOCKED = frozenset({'CONTEXT_INACTIVE', 'CONTEXT_FOREIGN',
    'CONTEXT_INACTIVE_OR_REMOTE', 'TARGET_USER_CONTEXT_MISMATCH',
    'PERMISSION_DENIED', 'RUNTIME_PATH_INVALID'})
# Diagnostics only: every one of these remains a failing result.
NATIVE_FAILURES = frozenset({'CONTEXT_UNKNOWN', 'CLEANUP_FAILED', 'CONTEXT_EXPIRED',
    'CONTEXT_CHANGED', 'CANCELLED', 'INPUT_INVALID', 'UNSUPPORTED_PLATFORM'})
FAILURE_PHASES = ({(code, phase) for code in NATIVE_FAILURES | {'NATIVE_ERROR', 'UNEXPECTED_ERROR'}
                   for phase in ('capture', 'recheck')}
                  | {('LOAD_FAILED', 'capture'), ('CONTRACT_FAILED', 'recheck')})
DIAGNOSTIC_STAGES = frozenset({'unknown', 'dll_initialization', 'thread_token',
    'process_session', 'active_console', 'process_token', 'token_user',
    'token_statistics', 'token_session', 'token_elevation', 'token_app_container',
    'token_restrictions', 'token_ui_access', 'wts_state', 'wts_protocol',
    'token_cleanup', 'identity_validation', 'runtime_paths', 'collection'})
DIAGNOSTIC_REASONS = frozenset({'unknown', 'api_call_failed', 'return_size_mismatch',
    'sid_pointer_bounds', 'sid_header_invalid', 'sid_size_bounds', 'unexpected_exception'})
MAC_DIAGNOSTIC_STAGES = frozenset({'unknown', 'console_user'})
MAC_DIAGNOSTIC_REASONS = frozenset({'unknown', 'null_result'})
MODULES = {'darwin': 'native_context', 'win32': 'windows_native_context'}
PATH_FIELDS = frozenset({'unknown', 'executable', 'cwd', 'prefix', 'base_prefix'})
PATH_REASONS = frozenset({'unknown', 'invalid_syntax', 'too_deep', 'symlink',
                          'not_directory', 'not_regular_file'})


def enabled():
    return os.environ.get(FLAG) == '1' and os.environ.get('GITHUB_ACTIONS') == 'true'


def load_native():
    name = MODULES[sys.platform]
    spec = importlib.util.spec_from_file_location(name,
        ROOT / 'skills' / 'claude-guardian' / 'scripts' / (name + '.py'))
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


def observe(module):
    """Only fixed enums leave the child; exceptions and private handles never do."""
    phase = 'capture'
    try:
        handle = module.capture_current_context(max_age_seconds=5)
        phase = 'recheck'
        report = module.recheck_context(handle)
        expected = {'platform': sys.platform, 'gate_state': 'closed', 'changes': [],
            'filesystem_namespace': 'unknown', 'network_namespace': 'unknown',
            'runtime_integrity': 'not_verified', 'native_platform_validation': 'not_run',
            'target_association': 'requires_trusted_host_assertion'}
        if sys.platform == 'win32':
            expected.update(binding_state='blocked', desktop_user_relation='unknown')
        if not isinstance(report, dict) or any(report.get(k) != v for k, v in expected.items()):
            return {'state': 'failed', 'code': 'CONTRACT_FAILED', 'phase': phase}
        return {'state': 'observed', 'code': 'CONTINUITY_OBSERVED', 'phase': phase}
    except module.ContextError as error:
        code = str(error)
        if code in BLOCKED:
            result = {'state': 'blocked', 'code': code, 'phase': phase}
            if sys.platform == 'darwin' and code == 'RUNTIME_PATH_INVALID' and hasattr(error, 'path_field'):
                for field, allowed in (('path_field', PATH_FIELDS), ('path_reason', PATH_REASONS)):
                    value = getattr(error, field, 'unknown')
                    result[field] = value if type(value) is str and value in allowed else 'unknown'
            return result
        result = {'state': 'failed', 'code': code if code in NATIVE_FAILURES else 'NATIVE_ERROR', 'phase': phase}
        if sys.platform == 'win32':
            for field, allowed in (('stage', DIAGNOSTIC_STAGES), ('reason', DIAGNOSTIC_REASONS)):
                value = getattr(error, field, 'unknown')
                result[field] = value if type(value) is str and value in allowed else 'unknown'
        elif sys.platform == 'darwin':
            for field, allowed in (('stage', MAC_DIAGNOSTIC_STAGES), ('reason', MAC_DIAGNOSTIC_REASONS)):
                value = getattr(error, field, 'unknown')
                result[field] = value if type(value) is str and value in allowed else 'unknown'
        return result
    except Exception:
        return {'state': 'failed', 'code': 'UNEXPECTED_ERROR', 'phase': phase}


def child_main():
    if not enabled() or sys.platform not in MODULES:
        return 2
    # Suppress even accidental Python diagnostics. Parent discards native stderr
    # and validates stdout without ever printing unexpected bytes.
    try:
        with open(os.devnull, 'w') as sink, contextlib.redirect_stdout(sink), contextlib.redirect_stderr(sink):
            result = observe(load_native())
    except Exception:
        result = {'state': 'failed', 'code': 'LOAD_FAILED', 'phase': 'capture'}
    sys.stdout.write(json.dumps(result, separators=(',', ':')) + '\n')
    return 0 if result['state'] != 'failed' else 1


def run_child():
    """Fixed self-child, no shell/commands from input; bounded bytes and lifetime."""
    try:
        process = subprocess.Popen([sys.executable, '-I', str(Path(__file__).resolve()), '--native-child'],
            cwd=ROOT, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL, bufsize=0)
    except OSError:
        raise AssertionError('Native smoke child launch failed') from None
    output = bytearray()
    overflow = threading.Event()
    read_failed = threading.Event()
    cleanup_failed = threading.Event()

    def kill_owned():
        try:
            process.kill()
        except Exception:
            cleanup_failed.set()

    def stop_and_reap():
        kill_owned()
        # Reap is attempted even if kill fails. Neither failure may leak details.
        try:
            process.wait(timeout=2)
        except Exception:
            cleanup_failed.set()

    def drain():
        try:
            while True:
                chunk = process.stdout.read(min(256, LIMIT + 1 - len(output)))
                if not chunk:
                    break
                output.extend(chunk)
                if len(output) > LIMIT:
                    overflow.set()
                    kill_owned()
                    break
        except Exception:
            read_failed.set()

    reader = threading.Thread(target=drain, daemon=True)
    started = False
    timed_out = False
    try:
        reader.start()
        started = True
        process.wait(timeout=TIMEOUT)
    except subprocess.TimeoutExpired:
        timed_out = True
        stop_and_reap()
    except Exception:
        cleanup_failed.set()
        stop_and_reap()
    finally:
        try:
            if started:
                reader.join(timeout=2)
            if reader.is_alive():
                cleanup_failed.set()
            else:
                process.stdout.close()
        except Exception:
            cleanup_failed.set()
    if cleanup_failed.is_set():
        raise AssertionError('Native smoke child cleanup failed') from None
    if timed_out:
        raise AssertionError('Native smoke child timed out')
    if overflow.is_set() or read_failed.is_set():
        raise AssertionError('Native smoke output boundary failed')
    return decode_result(process.returncode, bytes(output))


def decode_result(returncode, output):
    # Exit status is process metadata, never child text. Bound and type-check it.
    status = str(returncode) if type(returncode) is int and -(2**31) <= returncode < 2**32 else 'unknown'
    if len(output) > LIMIT:
        raise AssertionError('Native smoke output boundary failed; exit=' + status)
    try:
        report = json.loads(output)
    except (ValueError, UnicodeError):
        raise AssertionError('Native smoke invalid envelope; exit=' + status) from None
    if (type(report) is not dict or set(report) not in (
            {'state', 'code', 'phase'}, {'state', 'code', 'phase', 'stage', 'reason'},
            {'state', 'code', 'phase', 'path_field', 'path_reason'})
            or any(type(value) is not str for value in report.values())
            or report['phase'] not in ('capture', 'recheck')):
        raise AssertionError('Native smoke invalid envelope; exit=' + status)
    diagnostic = ''
    if 'path_field' in report:
        if (report['state'] != 'blocked' or report['code'] != 'RUNTIME_PATH_INVALID'
                or report['path_field'] not in PATH_FIELDS or report['path_reason'] not in PATH_REASONS):
            raise AssertionError('Native smoke invalid envelope; exit=' + status)
    if 'stage' in report:
        diagnostic_known = (
            (report['stage'] in DIAGNOSTIC_STAGES and report['reason'] in DIAGNOSTIC_REASONS)
            or (report['stage'] in MAC_DIAGNOSTIC_STAGES and report['reason'] in MAC_DIAGNOSTIC_REASONS))
        if (report['state'] != 'failed' or report['code'] not in NATIVE_FAILURES | {'NATIVE_ERROR'}
                or not diagnostic_known):
            raise AssertionError('Native smoke invalid envelope; exit=' + status)
        diagnostic = '; stage=' + report['stage'] + '; reason=' + report['reason']
    if report['state'] == 'failed' and (report['code'], report['phase']) in FAILURE_PHASES:
        # Only the reviewed literal enum pair crosses this boundary, never raw
        # output or exception messages. Even exit=0 cannot turn failure into pass.
        raise AssertionError('Native smoke child failed; exit=' + status
                             + '; code=' + report['code'] + '; phase=' + report['phase'] + diagnostic)
    if not ((report['state'] == 'blocked' and report['code'] in BLOCKED)
            or (report['state'] == 'observed' and report['code'] == 'CONTINUITY_OBSERVED'
                and report['phase'] == 'recheck')):
        raise AssertionError('Native smoke invalid envelope; exit=' + status)
    if type(returncode) is not int or returncode != 0:
        raise AssertionError('Native smoke inconsistent exit status; exit=' + status)
    return report


class NativeContextSmokeTests(unittest.TestCase):
    def test_ci_owned_native_context(self):
        if sys.platform not in MODULES:
            self.skipTest('n/a: no macOS or Windows native context on this platform')
        if not enabled():
            self.skipTest('native context CI smoke explicitly disabled')
        report = run_child()
        if report['state'] == 'blocked':
            diagnostic = ('; path_field=' + report['path_field'] + '; path_reason=' + report['path_reason']
                          if 'path_field' in report else '')
            self.skipTest('CI native context blocked during ' + report['phase'] + ': ' + report['code']
                          + diagnostic
                          + '; remaining ABI paths unverified; no desktop acceptance')
        print('CI native context: continuity observed; gate closed; no desktop acceptance', flush=True)


class SmokeBoundaryTests(unittest.TestCase):
    """All synthetic, including on Mac/Windows; no native calls or child launch."""
    def module(self):
        class ContextError(Exception):
            pass
        return SimpleNamespace(ContextError=ContextError,
            capture_current_context=mock.Mock(return_value=object()),
            recheck_context=mock.Mock(return_value={
                'platform': sys.platform, 'gate_state': 'closed', 'changes': [],
                'filesystem_namespace': 'unknown', 'network_namespace': 'unknown',
                'runtime_integrity': 'not_verified', 'native_platform_validation': 'not_run',
                'target_association': 'requires_trusted_host_assertion',
                'binding_state': 'blocked', 'desktop_user_relation': 'unknown'}))

    def test_explicit_flag_and_ci_both_required(self):
        for env, expected in (({}, False), ({FLAG: '1'}, False),
                ({'GITHUB_ACTIONS': 'true'}, False),
                ({FLAG: 'true', 'GITHUB_ACTIONS': 'true'}, False),
                ({FLAG: '1', 'GITHUB_ACTIONS': 'true'}, True)):
            with mock.patch.dict(os.environ, env, clear=True):
                self.assertEqual(enabled(), expected)

    def test_child_no_native_when_disabled_or_linux(self):
        with mock.patch(__name__ + '.load_native') as load:
            with mock.patch(__name__ + '.enabled', return_value=False):
                self.assertEqual(child_main(), 2)
            with mock.patch(__name__ + '.enabled', return_value=True), mock.patch.object(sys, 'platform', 'linux'):
                self.assertEqual(child_main(), 2)
            load.assert_not_called()

    def test_observed_contract_both_platforms(self):
        for platform in MODULES:
            with mock.patch.object(sys, 'platform', platform):
                module = self.module()
                self.assertEqual(observe(module)['state'], 'observed')
                module.capture_current_context.assert_called_once_with(max_age_seconds=5)
                module.recheck_context.assert_called_once_with(module.capture_current_context.return_value)
                module.recheck_context.return_value['gate_state'] = 'open'
                self.assertEqual(observe(module)['state'], 'failed')

    def test_blocked_codes_and_phase(self):
        for code in BLOCKED:
            for phase in ('capture', 'recheck'):
                module = self.module()
                getattr(module, {'capture': 'capture_current_context', 'recheck': 'recheck_context'}[phase]).side_effect = module.ContextError(code)
                self.assertEqual(observe(module), {'state': 'blocked', 'code': code, 'phase': phase})

    def test_unknown_or_cleanup_exception_is_failure_and_redacted(self):
        module = self.module()
        for error in (module.ContextError('CONTEXT_UNKNOWN'), module.ContextError('CLEANUP_FAILED'),
                      module.ContextError('CONTEXT_EXPIRED'), RuntimeError('PRIVATE-PATH-TOKEN')):
            module.capture_current_context.side_effect = error
            result = observe(module)
            self.assertEqual(result['state'], 'failed')
            self.assertNotIn('PRIVATE', json.dumps(result))

    def test_mac_path_diagnostic_is_allowlisted_and_stays_blocked(self):
        with mock.patch.object(sys, 'platform', 'darwin'):
            module = self.module()
            for field, reason in (('executable', 'symlink'), ('cwd', 'not_directory'),
                                  ('PRIVATE-PATH', 'PRIVATE-TOKEN'), ([], {})):
                error = module.ContextError('RUNTIME_PATH_INVALID')
                error.path_field, error.path_reason = field, reason
                module.capture_current_context.side_effect = error
                result = observe(module)
                self.assertEqual(result['state'], 'blocked')
                self.assertEqual(result['code'], 'RUNTIME_PATH_INVALID')
                self.assertEqual(decode_result(0, json.dumps(result).encode()), result)
                self.assertNotIn('PRIVATE', json.dumps(result))
            result.update(path_field='executable', path_reason='symlink')
            for altered in (dict(result, path_field='PRIVATE'), dict(result, path_reason='PRIVATE'),
                            dict(result, code='CONTEXT_INACTIVE'), dict(result, state='observed')):
                with self.assertRaises(AssertionError):
                    decode_result(0, json.dumps(altered).encode())

    def test_envelope_rejects_leaks_and_invalid_states(self):
        for value in (b'PRIVATE', b'"PRIVATE"', b'{}', b'x' * (LIMIT + 1),
                b'{"state":"observed","code":"CONTINUITY_OBSERVED","phase":"capture"}',
                b'{"state":"blocked","code":"CONTEXT_UNKNOWN","phase":"capture"}',
                b'{"state":"blocked","code":"CONTEXT_FOREIGN","phase":"capture","sid":"PRIVATE"}'):
            with self.assertRaises(AssertionError) as failure:
                decode_result(0, value)
            self.assertNotIn('PRIVATE', str(failure.exception))
        with self.assertRaises(AssertionError):
            decode_result(1, b'PRIVATE')

    def test_windows_diagnostic_vocab_remains_failure(self):
        with mock.patch.object(sys, 'platform', 'win32'):
            for stage in DIAGNOSTIC_STAGES:
                for reason in DIAGNOSTIC_REASONS:
                    module = self.module()
                    error = module.ContextError('CONTEXT_UNKNOWN')
                    error.stage, error.reason = stage, reason
                    module.capture_current_context.side_effect = error
                    report = observe(module)
                    self.assertEqual(report, dict(state='failed', code='CONTEXT_UNKNOWN',
                                                  phase='capture', stage=stage, reason=reason))
                    with self.assertRaises(AssertionError) as failure:
                        decode_result(1, json.dumps(report).encode())
                    self.assertEqual(str(failure.exception),
                        'Native smoke child failed; exit=1; code=CONTEXT_UNKNOWN; phase=capture'
                        + '; stage=' + stage + '; reason=' + reason)

    def test_mac_console_null_diagnostic_is_failure_not_headless_skip(self):
        with mock.patch.object(sys, 'platform', 'darwin'):
            module = self.module()
            error = module.ContextError('CONTEXT_UNKNOWN')
            error.stage, error.reason = 'console_user', 'null_result'
            module.capture_current_context.side_effect = error
            report = observe(module)
        self.assertEqual(report, dict(state='failed', code='CONTEXT_UNKNOWN',
                                      phase='capture', stage='console_user', reason='null_result'))
        for status in (0, 1):
            with self.assertRaises(AssertionError) as failure:
                decode_result(status, json.dumps(report).encode())
            self.assertEqual(str(failure.exception),
                'Native smoke child failed; exit=' + str(status)
                + '; code=CONTEXT_UNKNOWN; phase=capture; stage=console_user; reason=null_result')

    def test_mac_unknown_native_diagnostic_attributes_are_redacted(self):
        with mock.patch.object(sys, 'platform', 'darwin'):
            for value in ('PRIVATE-PATH', [], {}, 123, None):
                module = self.module()
                error = module.ContextError('CONTEXT_UNKNOWN')
                error.stage = error.reason = value
                module.capture_current_context.side_effect = error
                report = observe(module)
                self.assertEqual((report['stage'], report['reason']), ('unknown', 'unknown'))
                self.assertNotIn('PRIVATE', json.dumps(report))

    def test_windows_unknown_attributes_are_redacted(self):
        with mock.patch.object(sys, 'platform', 'win32'):
            for value in ('PRIVATE-PATH', [], {}, 123, None):
                module = self.module()
                error = module.ContextError('CONTEXT_UNKNOWN')
                error.stage = error.reason = value
                module.capture_current_context.side_effect = error
                report = observe(module)
                self.assertEqual((report['stage'], report['reason']), ('unknown', 'unknown'))
                self.assertNotIn('PRIVATE', json.dumps(report))
            module.capture_current_context.side_effect = module.ContextError('CONTEXT_UNKNOWN')
            report = observe(module)
            self.assertEqual((report['stage'], report['reason']), ('unknown', 'unknown'))

    def test_parent_rejects_nonallowlisted_or_nonfailure_diagnostics(self):
        base = dict(state='failed', code='CONTEXT_UNKNOWN', phase='capture',
                    stage='token_user', reason='return_size_mismatch')
        cases = []
        for field in ('stage', 'reason'):
            for value in ('PRIVATE', [], {}, 123, None):
                cases.append(dict(base, **{field: value}))
            missing = base.copy()
            del missing[field]
            cases.append(missing)
        cases.extend([dict(base, state='blocked', code='CONTEXT_FOREIGN'),
                      dict(base, state='observed', code='CONTINUITY_OBSERVED', phase='recheck'),
                      dict(base, stage='console_user'), dict(base, reason='null_result'),
                      dict(base, code='LOAD_FAILED'), dict(base, secret='PRIVATE')])
        for report in cases:
            with self.assertRaises(AssertionError) as failure:
                decode_result(1, json.dumps(report).encode())
            self.assertEqual(str(failure.exception), 'Native smoke invalid envelope; exit=1')

    def test_known_failure_diagnostics_still_fail(self):
        for code, phase in FAILURE_PHASES:
            for exitcode in (0, 1, -9, 3221225477):
                payload = json.dumps({'state': 'failed', 'code': code, 'phase': phase}).encode()
                with self.assertRaises(AssertionError) as failure:
                    decode_result(exitcode, payload)
                self.assertEqual(str(failure.exception),
                    'Native smoke child failed; exit=' + str(exitcode)
                    + '; code=' + code + '; phase=' + phase)

    def test_failure_diagnostics_reject_unknown_or_private_data(self):
        cases = [b'PRIVATE-STDOUT', b'x' * (LIMIT + 1)]
        for report in ({'state': 'failed', 'code': 'PRIVATE', 'phase': 'capture'},
                       {'state': 'failed', 'code': 'LOAD_FAILED', 'phase': 'PRIVATE'},
                       {'state': 'failed', 'code': 'LOAD_FAILED', 'phase': 'recheck'},
                       {'state': 'failed', 'code': 'LOAD_FAILED', 'phase': 'capture', 'private': 'PRIVATE'}):
            cases.append(json.dumps(report).encode())
        for payload in cases:
            with self.assertRaises(AssertionError) as failure:
                decode_result(1, payload)
            self.assertNotIn('PRIVATE', str(failure.exception))
            self.assertIn('exit=1', str(failure.exception))
        for exitcode in ('PRIVATE', True, 2**100):
            with self.assertRaises(AssertionError) as failure:
                decode_result(exitcode, b'PRIVATE')
            self.assertEqual(str(failure.exception), 'Native smoke invalid envelope; exit=unknown')

    def test_success_envelope_cannot_override_failed_exit(self):
        for state, code, phase in (('blocked', 'CONTEXT_FOREIGN', 'capture'),
                                   ('observed', 'CONTINUITY_OBSERVED', 'recheck')):
            payload = json.dumps(dict(state=state, code=code, phase=phase)).encode()
            with self.assertRaisesRegex(AssertionError, 'inconsistent exit status; exit=1'):
                decode_result(1, payload)

    def test_valid_envelopes_and_successful_child(self):
        for report in ({'state': 'observed', 'code': 'CONTINUITY_OBSERVED', 'phase': 'recheck'},
                       {'state': 'blocked', 'code': 'CONTEXT_FOREIGN', 'phase': 'capture'}):
            payload = json.dumps(report).encode()
            child = mock.Mock(stdout=io.BytesIO(payload), returncode=0)
            with mock.patch.object(subprocess, 'Popen', return_value=child):
                self.assertEqual(run_child(), report)
            child.kill.assert_not_called()
            self.assertTrue(child.stdout.closed)

    def test_launch_failure_does_not_expose_path(self):
        with mock.patch.object(subprocess, 'Popen', side_effect=OSError('PRIVATE-PATH')):
            with self.assertRaisesRegex(AssertionError, '^Native smoke child launch failed$'):
                run_child()

    def test_child_loader_exception_is_sanitized_failure(self):
        with mock.patch(__name__ + '.enabled', return_value=True), \
             mock.patch.object(sys, 'platform', 'darwin'), \
             mock.patch(__name__ + '.load_native', side_effect=RuntimeError('PRIVATE')), \
             contextlib.redirect_stdout(io.StringIO()) as output:
            self.assertEqual(child_main(), 1)
        self.assertEqual(json.loads(output.getvalue()),
                         {'state': 'failed', 'code': 'LOAD_FAILED', 'phase': 'capture'})

    def test_fixed_child_and_output_limit(self):
        child = mock.Mock(stdout=io.BytesIO(b'x' * (LIMIT + 100)), returncode=0)
        with mock.patch.object(subprocess, 'Popen', return_value=child) as launch:
            with self.assertRaisesRegex(AssertionError, 'output boundary'):
                run_child()
        child.kill.assert_called_once()
        args, kwargs = launch.call_args
        self.assertEqual(args[0], [sys.executable, '-I', str(Path(__file__).resolve()), '--native-child'])
        self.assertEqual(kwargs['stderr'], subprocess.DEVNULL)
        self.assertNotIn('shell', kwargs)

    def test_timeout_kills_and_reaps_child(self):
        child = mock.Mock(stdout=io.BytesIO(b''), returncode=-1)
        child.wait.side_effect = [subprocess.TimeoutExpired('fixed', TIMEOUT), 0]
        with mock.patch.object(subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(AssertionError, 'timed out'):
                run_child()
        child.kill.assert_called_once()
        self.assertEqual(child.wait.call_args_list, [mock.call(timeout=TIMEOUT), mock.call(timeout=2)])


    def test_cleanup_errors_are_sanitized_and_reap_attempted(self):
        for failure in ('kill', 'initial_wait', 'reap', 'close'):
            with self.subTest(failure=failure):
                pipe = mock.Mock(wraps=io.BytesIO(b''))
                child = mock.Mock(stdout=pipe, returncode=-1)
                child.wait.side_effect = [subprocess.TimeoutExpired('fixed', TIMEOUT), 0]
                if failure == 'kill':
                    child.kill.side_effect = OSError('PRIVATE-CLEANUP-DETAIL')
                elif failure == 'initial_wait':
                    child.wait.side_effect = [OSError('PRIVATE-WAIT-DETAIL'), 0]
                elif failure == 'reap':
                    child.wait.side_effect = [subprocess.TimeoutExpired('fixed', TIMEOUT),
                                              OSError('PRIVATE-REAP-DETAIL')]
                else:
                    pipe.close.side_effect = OSError('PRIVATE-CLOSE-DETAIL')
                with mock.patch.object(subprocess, 'Popen', return_value=child):
                    with self.assertRaisesRegex(AssertionError, '^Native smoke child cleanup failed$'):
                        run_child()
                child.kill.assert_called_once()
                self.assertEqual(child.wait.call_args_list,
                                 [mock.call(timeout=TIMEOUT), mock.call(timeout=2)])
                pipe.close.assert_called_once()

    def test_overflow_kill_failure_is_sanitized(self):
        child = mock.Mock(stdout=io.BytesIO(b'x' * (LIMIT + 1)), returncode=0)
        child.kill.side_effect = OSError('PRIVATE-KILL-DETAIL')
        with mock.patch.object(subprocess, 'Popen', return_value=child):
            with self.assertRaisesRegex(AssertionError, '^Native smoke child cleanup failed$'):
                run_child()
        child.wait.assert_called_once_with(timeout=TIMEOUT)

    def test_reader_start_failure_reaps_child(self):
        child = mock.Mock(stdout=io.BytesIO(b''), returncode=0)
        reader = mock.Mock()
        reader.start.side_effect = RuntimeError('PRIVATE-THREAD-DETAIL')
        reader.is_alive.return_value = False
        with mock.patch.object(subprocess, 'Popen', return_value=child), \
             mock.patch.object(threading, 'Thread', return_value=reader):
            with self.assertRaisesRegex(AssertionError, '^Native smoke child cleanup failed$'):
                run_child()
        child.kill.assert_called_once()
        child.wait.assert_called_once_with(timeout=2)
        reader.join.assert_not_called()
        self.assertTrue(child.stdout.closed)


if __name__ == '__main__':
    if sys.argv[1:] == ['--native-child']:
        sys.exit(child_main())
    unittest.main()
