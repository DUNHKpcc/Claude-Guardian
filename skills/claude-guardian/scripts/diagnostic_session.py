#!/usr/bin/env python3
"""Narrow PC0 session: live local consent, context metadata, optional host-bound DNS.

No I/O on import. Python callbacks are a trusted-host boundary, not a sandbox.
The standalone terminal adapter cannot attest namespaces or resolver runtime.
"""
from dataclasses import dataclass
from datetime import datetime, timezone
import json
import math
import os
import re
import secrets
import select
import sys
import time

import guardian
import interview_flow
import inventory_cli
import native_context
import windows_native_context
import os_dns_probe
import status_dashboard


class SessionError(Exception):
    pass


@dataclass(frozen=True)
class DNSHost:
    """Supplied in-process by the trusted host, never reconstructed from reports.

    Verifiers must establish current target/user/namespaces, full runtime and
    dependencies (including launch races), and endpoint neutrality respectively.
    They must bound their own work. None can be replaced by a saved JSON flag.
    """
    binding: os_dns_probe.Binding
    verify_binding: object
    verify_runtime: object
    verify_neutral: object


class TerminalConsent:
    """Fresh per-operation nonce; a terminal is not authenticated human/OS consent."""
    def __init__(self, incoming=None, prompt=None, timeout=30.0):
        self.incoming = sys.stdin if incoming is None else incoming
        self.prompt = sys.stderr if prompt is None else prompt
        if type(timeout) not in (int, float) or not .1 <= timeout <= 60 or not math.isfinite(timeout):
            raise SessionError('INPUT_INVALID')
        self.timeout = timeout
        self._last_time = None

    def _clock(self):
        now = time.monotonic()
        if (type(now) not in (int, float) or not 0 <= now < 1e100
                or not math.isfinite(now)
                or (self._last_time is not None and now < self._last_time)):
            raise SessionError('CONSENT_TIMEOUT')
        self._last_time = now
        return now

    def _read_windows_line(self, deadline):
        import msvcrt
        result = []
        while len(result) < 80:
            if self._clock() >= deadline:
                raise SessionError('CONSENT_TIMEOUT')
            if not msvcrt.kbhit():
                time.sleep(.02)
                continue
            char = msvcrt.getwch()
            if char == '\x03':
                raise KeyboardInterrupt
            if char in ('\r', '\n'):
                self.prompt.write('\n')
                self.prompt.flush()
                return ''.join(result) + '\n'
            if char == '\b' and result:
                result.pop()
                self.prompt.write('\b \b')
            elif len(char) == 1 and ' ' <= char <= '~':
                result.append(char)
                self.prompt.write(char)
            else:
                return ''  # EOF/control/extended-key input never grants consent.
            self.prompt.flush()
        return ''

    def _read_line(self, deadline):
        if os.name == 'nt':
            return self._read_windows_line(deadline)
        # No readline: a partial line must not defeat the deadline. POSIX terminal
        # canonical mode normally delivers one complete line at a time.
        result = bytearray()
        while len(result) < 80:
            remaining = deadline - self._clock()
            if remaining <= 0:
                raise SessionError('CONSENT_TIMEOUT')
            ready, _, _ = select.select([self.incoming.fileno()], [], [], remaining)
            if not ready:
                raise SessionError('CONSENT_TIMEOUT')
            chunk = os.read(self.incoming.fileno(), 1)
            if not chunk:
                return ''
            result.extend(chunk)
            if chunk == b'\n':
                return result.decode('ascii', errors='replace')
        return ''

    def __call__(self, scope):
        self._last_time = None
        if os.name not in ('posix', 'nt') or not self.incoming.isatty() or not self.prompt.isatty():
            raise SessionError('LIVE_TERMINAL_REQUIRED')
        # Discard type-ahead: each displayed challenge requires a new response.
        if os.name == 'nt':
            # msvcrt reads the process console, not arbitrary supplied streams.
            if self.incoming.fileno() != 0:
                raise SessionError('LIVE_TERMINAL_REQUIRED')
            import msvcrt
            drain_deadline = self._clock() + min(self.timeout, .25)
            for _ in range(80):
                if self._clock() >= drain_deadline:
                    raise SessionError('CONSENT_TIMEOUT')
                if not msvcrt.kbhit():
                    break
                msvcrt.getwch()
            else:
                raise SessionError('DECLINED')
        else:
            import termios
            termios.tcflush(self.incoming.fileno(), termios.TCIFLUSH)
        nonce = secrets.token_hex(8)
        self.prompt.write(json.dumps(scope, ensure_ascii=True, sort_keys=True) + '\n')
        self.prompt.write('Terminal response is user intent only, not host/OS permission. '
                          'Type APPROVE ' + nonce + ' for this operation; anything else cancels: ')
        self.prompt.flush()
        deadline = self._clock() + self.timeout
        answer = self._read_line(deadline)
        if self._clock() >= deadline:
            raise SessionError('CONSENT_TIMEOUT')
        return answer == 'APPROVE ' + nonce + '\n'


def _now():
    return datetime.now(timezone.utc).isoformat()


def _guard(cancelled):
    if cancelled() is not False:
        raise SessionError('CANCELLED')


def _check(handle, cancelled, backend):
    _guard(cancelled)
    backend.recheck_context(handle, cancelled=cancelled)
    _guard(cancelled)


def execute(target_ref, *, consent, dns_host=None, queries=(), interview=None,
            cancelled=lambda: False):
    """Run a fresh session; return sanitized report and in-memory HTML preview.

    Caller must be an already trusted host for even local metadata access. The
    selected target alias is presented as a declaration, not device proof. Scope
    approval is live and separate for every DNS query. No imported report or
    interview answer is used as authority. At most eight explicit query pairs.
    """
    report = guardian.base('audit', 'session-target')
    report['record_kind'] = 'limited_context_observation'
    report['module_ids'] = ['ENV-01']
    report['not_tested'] = [
        'ENV-02: proxy inventory and runtime routing',
        'ENV-03: live IP/ASN/path tests',
        'ENV-04: DNS packets, actual servers, upstream routes, leak absence, IPv6/UDP coverage',
        'ENV-05: browser/WebRTC', 'ENV-07: real clients and subprocesses',
        'ENV-09: cleanup', 'ENV-10: failure/rollback validation']
    report['limits']['system_dns_sample'] = 'not_run'
    result = {'schema_version': 'guardian-diagnostic-session/0.1',
              'status': 'partial', 'gate_state': 'closed', 'contact_phase': 'precontact',
              'changes': [], 'permission_restorable': False, 'errors': [],
              'dns_availability': 'blocked_missing_trusted_host_integration',
              'report': report}
    bundle = {'schema_version': 'guardian-probe-evidence/0.1',
              'target_ref': 'session-target', 'samples': []}
    backend = windows_native_context if sys.platform == 'win32' else native_context
    local_os = 'windows' if sys.platform == 'win32' else 'macos'
    handle = None
    metadata_only = False
    continuity_failure = None
    def checked():
        # The probe sanitizes callback exceptions. Latch continuity rejection so
        # even a transient context flip cannot disappear on a later recheck.
        nonlocal continuity_failure
        if continuity_failure is not None:
            raise continuity_failure
        try:
            _check(handle, cancelled, backend)
        except (native_context.ContextError, windows_native_context.ContextError, SessionError) as exc:
            continuity_failure = exc
            raise
    def host_check(callback, argument, failure_code):
        # Probe callbacks can have their exceptions converted to OUTPUT_INVALID.
        # Trust loss must survive that sanitization and stop the whole session,
        # rather than look like an ordinary recoverable resolver failure.
        nonlocal continuity_failure
        checked()
        try:
            accepted = callback(argument)
        except Exception:
            continuity_failure = SessionError(failure_code)
            raise continuity_failure from None
        checked()
        if accepted is not True:
            continuity_failure = SessionError(failure_code)
            raise continuity_failure
        return True

    try:
        if (type(target_ref) is not str or not re.fullmatch(r'[A-Za-z][A-Za-z0-9_-]{0,47}', target_ref)
                or not callable(consent) or not callable(cancelled)
                or type(queries) not in (tuple, list) or len(queries) > 8):
            raise SessionError('INPUT_INVALID')
        if sys.platform not in ('darwin', 'win32'):
            raise SessionError('UNSUPPORTED_PLATFORM')
        if interview is not None:
            # Coverage only. Never reuse Q-Z01 or any saved authorization answer.
            assessed = interview_flow.assessment(interview)
            result['interview'] = {'coverage': assessed['G1']['status'],
                                   'action_gate': 'blocked',
                                   'unresolved_count': len(assessed['G1']['unresolved_fields'])}
        if dns_host is not None:
            if (type(dns_host) is not DNSHost or type(dns_host.binding) is not os_dns_probe.Binding
                    or dns_host.binding.target_ref != target_ref
                    or not all(callable(v) for v in (dns_host.verify_binding,
                        dns_host.verify_runtime, dns_host.verify_neutral))):
                raise SessionError('HOST_INTEGRATION_INVALID')
        _guard(cancelled)
        if consent({'operation': 'read_local_context', 'declared_target': target_ref,
                    'scope': (['current_process_identity', 'primary_console_session',
                               'fixed_interpreter_cwd_prefix_path_metadata'] if local_os == 'macos' else
                              ['owned_process_token_identity', 'current_thread_impersonation_check',
                               'current_session_console_state', 'fixed_runtime_path_syntax_only']),
                    'target_association': 'not_independently_verified',
                    'network': 'none', 'changes': 'none'}) is not True:
            raise SessionError('DECLINED')
        _guard(cancelled)
        started = time.monotonic()
        if type(started) not in (int, float) or not 0 <= started < 1e100:
            raise SessionError('CONTEXT_EXPIRED')
        last_tick = started
        def remaining_budget():
            nonlocal last_tick
            _guard(cancelled)
            current = time.monotonic()
            if (type(current) not in (int, float) or not last_tick <= current < started + 60):
                raise SessionError('CONTEXT_EXPIRED')
            last_tick = current
            return started + 60 - current
        try:
            handle = backend.capture_current_context(max_age_seconds=60, cancelled=cancelled)
        except native_context.ContextError as exc:
            if local_os != 'macos' or exc.args != ('RUNTIME_PATH_INVALID',):
                raise
            # An invalid runtime path is not an identity failure. Re-observe only
            # the already approved metadata within the original capture budget.
            # This helper deliberately returns no handle, even if paths now pass.
            remaining = remaining_budget()
            if remaining < .1:
                raise SessionError('CONTEXT_EXPIRED')
            partial = native_context.observe_context_metadata(
                max_seconds=min(5.0, remaining), cancelled=cancelled)
            remaining_budget()
            metadata_only = True
            result['context'] = partial
            result['errors'].append('RUNTIME_PATH_INVALID')
            result['dns_availability'] = 'blocked_context_handle_unavailable'
        if handle is not None:
            checked()
            result['context'] = backend.describe_context(handle)
        report['facts'] = [{'id': 'S01', 'value': local_os, 'state': 'observed',
                            'source_refs': ['native-current-context'], 'observed_at': _now(),
                            'coverage': result['context'].get('coverage', 'limited_process_context')}]
        report['missing_fields'] = ['Target association and execution namespaces unverified',
                                    'Proxy, browser, runtime integrity and environment readiness unknown']
        if local_os == 'windows':
            result['dns_availability'] = 'blocked_windows_session_dns_integration_unavailable'
            if queries:
                raise SessionError('WINDOWS_SESSION_DNS_UNAVAILABLE')
        elif handle is not None and dns_host is not None:
            result['dns_availability'] = 'requires_live_host_checks_and_query_consent'
        for pair in queries if handle is not None else ():
            checked()
            if dns_host is None:
                result['errors'].append('DNS_HOST_INTEGRATION_REQUIRED')
                break
            if type(pair) not in (tuple, list) or len(pair) != 2:
                raise SessionError('INPUT_INVALID')
            scope = os_dns_probe.QueryScope(dns_host.binding, pair[0], pair[1])
            budget = os_dns_probe.Budget()
            os_dns_probe._validate(scope, budget)
            def binding_ok(binding):
                checked()
                return host_check(dns_host.verify_binding, binding, 'TARGET_NOT_BOUND') if binding == dns_host.binding else False
            def runtime_ok(binding):
                checked()
                return host_check(dns_host.verify_runtime, binding, 'RUNTIME_NOT_TRUSTED')
            if not binding_ok(scope.binding):
                raise SessionError('TARGET_NOT_BOUND')
            if not runtime_ok(scope.binding):
                raise SessionError('RUNTIME_NOT_TRUSTED')
            if host_check(dns_host.verify_neutral, scope, 'ENDPOINT_NEUTRALITY_UNVERIFIED') is not True:
                raise SessionError('ENDPOINT_NEUTRALITY_UNVERIFIED')
            checked()
            if consent({'operation': 'system_dns_query', 'declared_target': target_ref,
                        'partial_findings': {'os': 'macos', 'console': 'same_at_observation',
                            'proxy_and_browser': 'not_run', 'environment_readiness': 'unknown'},
                        'absolute_name': scope.absolute_name, 'query_type': scope.query_type,
                        'max_seconds': budget.max_seconds, 'max_api_calls': 1,
                        'disclosure': 'Exact hostname may reach configured system resolvers and their upstream providers; cache or hosts may answer locally',
                        'cancellation_limit': 'Cannot retract traffic already sent',
                        'changes': 'none', 'contact_gate': 'closed'}) is not True:
                raise SessionError('DECLINED')
            checked()
            # One ephemeral approval is consumed only for this exact immutable
            # scope/budget. It is never returned, saved, or shared with next query.
            used = False
            def consume(candidate, candidate_budget):
                nonlocal used
                checked()
                if used or candidate != scope or candidate_budget != budget:
                    return False
                used = True
                return host_check(dns_host.verify_neutral, candidate, 'ENDPOINT_NEUTRALITY_UNVERIFIED')
            probe = os_dns_probe.probe_os_dns(scope, verify_binding=binding_ok,
                verify_runtime=runtime_ok, approve_query=consume, cancelled=cancelled, budget=budget)
            if probe['requests_attempted']:
                report['module_ids'] = ['ENV-01', 'ENV-04']
                report['limits'].update(
                    collector_external_network='explicit_system_dns_samples_only',
                    endpoints='per_query_neutrality_and_consent_required',
                    system_dns_sample='attempted_not_environment_acceptance')
            checked()
            bundle['samples'].append({'result': probe, 'captured_at': _now(),
                'expected_path_kind': 'macos_getaddrinfo',
                'context': {'target_ref': 'session-target', 'path_kind': 'macos_getaddrinfo'}})
            if probe['error_code'] is not None:
                result['errors'].append(probe['error_code'])
                if probe['error_code'] in {'CANCELLED', 'TIMEOUT', 'TARGET_NOT_BOUND',
                        'RUNTIME_NOT_TRUSTED', 'AUTHORIZATION_MISSING', 'CLEANUP_FAILED'}:
                    raise SessionError(probe['error_code'])
        if handle is not None:
            checked()
        else:
            remaining_budget()
    except (KeyboardInterrupt, EOFError):
        result['errors'].append('CANCELLED')
        result['status'] = 'cancelled'
    except (SessionError, native_context.ContextError, windows_native_context.ContextError, os_dns_probe.ProbeError) as exc:
        allowed = {'INPUT_INVALID', 'HOST_INTEGRATION_INVALID', 'CANCELLED', 'DECLINED',
            'LIVE_TERMINAL_REQUIRED', 'CONSENT_TIMEOUT', 'TARGET_NOT_BOUND',
            'RUNTIME_NOT_TRUSTED', 'ENDPOINT_NEUTRALITY_UNVERIFIED',
            'UNSUPPORTED_PLATFORM', 'CONTEXT_EXPIRED', 'CONTEXT_CHANGED', 'CONTEXT_UNKNOWN',
            'CONTEXT_INACTIVE', 'CONTEXT_FOREIGN', 'TARGET_USER_CONTEXT_MISMATCH',
            'RUNTIME_PATH_INVALID', 'PERMISSION_DENIED', 'PC0_TARGET_FORBIDDEN',
            'TIMEOUT', 'AUTHORIZATION_MISSING', 'CLEANUP_FAILED',
            'CONTEXT_INACTIVE_OR_REMOTE', 'WINDOWS_SESSION_DNS_UNAVAILABLE'}
        code = exc.args[0] if exc.args and type(exc.args[0]) is str else ''
        code = code if code in allowed else 'INPUT_INVALID'
        if not result['errors'] or result['errors'][-1] != code:
            result['errors'].append(code)
        result['status'] = 'cancelled' if code in {'CANCELLED', 'DECLINED'} else 'blocked'
    except Exception:
        result['errors'].append('SESSION_FAILED')
        result['status'] = 'blocked'
    if result['status'] in ('blocked', 'cancelled'):
        if metadata_only:
            # A no-handle fallback cannot retain facts after its final budget or
            # cancellation guard fails. Strict-handle history is separate below.
            result.pop('context', None)
            report['facts'] = []
        # Retained evidence remains historical and unavailable for current-target
        # conclusions after interruption/rebinding. DNS failures remain visible.
        for fact in report['facts']:
            fact['state'] = 'stale'
        if 'context' in result:
            result['context']['continuity'] = 'not_current'
        report['execution_status'] = 'blocked'
        for sample in bundle['samples']:
            sample['context'] = {}
        result['evidence_scope'] = 'historical_only_current_context_not_established'
    result['probe_evidence'] = bundle
    result['dashboard_html'] = status_dashboard.render(report, probe_report=bundle)
    return result


def run(argv=None, *, incoming=None, outgoing=None, prompt=None):
    outgoing = sys.stdout if outgoing is None else outgoing
    try:
        parser = inventory_cli.Parser(prog='diagnostic_session.py', description=__doc__)
        parser.add_argument('--target-ref', required=True, help='Declared current Mac/Windows alias; not identity proof')
        parser.add_argument('--dashboard-output', help='Explicit new local hydrated HTML path; never auto-opened')
        args = parser.parse_args(argv)
        if args.dashboard_output:
            if sys.platform == 'win32':
                guardian.validate_windows_output_path(args.dashboard_output)
            inventory_cli._path(args.dashboard_output)
        result = execute(args.target_ref, consent=TerminalConsent(incoming, prompt))
        html = result.pop('dashboard_html')
        if args.dashboard_output:
            guardian.save_new(args.dashboard_output, html)
            result['dashboard_saved'] = True
        code = 3 if result['status'] == 'cancelled' else 2 if result['status'] == 'blocked' else 0
    except inventory_cli.HelpRequested as exc:
        result, code = {'status': 'help', 'help': exc.text}, 0
    except (inventory_cli.InputError, guardian.GuardianError, SessionError):
        result, code = {'status': 'blocked', 'error_code': 'INVALID_ARGUMENTS_OR_SAVE_FAILED'}, 2
    except (OSError, ValueError):
        result, code = {'status': 'blocked', 'error_code': 'SESSION_FAILED'}, 2
    outgoing.write(json.dumps(result, ensure_ascii=True, sort_keys=True) + '\n')
    return code


if __name__ == '__main__':
    raise SystemExit(run())
