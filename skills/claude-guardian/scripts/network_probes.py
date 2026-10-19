"""Explicit, neutral endpoint diagnostics. Importing this module performs no I/O.

PD03 endpoint selection and runtime approval remain caller responsibilities. These
candidates are not standing approval. Evidence is for this probe only, never the
browser, Claude's routing, account eligibility, or an anti-ban guarantee.
"""
from copy import deepcopy
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import threading
import sys
import re
import math
from email.utils import parsedate_to_datetime
from datetime import datetime, timezone
from urllib.parse import urlsplit

try:
    import environment_entry
except ModuleNotFoundError as _entry_import_error:
    if _entry_import_error.name != 'environment_entry':
        raise
    # Preserve the existing standalone file-path import API without sys.path edits.
    import importlib.util as _entry_importlib
    _entry_spec = _entry_importlib.spec_from_file_location(
        '_probe_environment_entry', Path(__file__).with_name('environment_entry.py'))
    environment_entry = _entry_importlib.module_from_spec(_entry_spec)
    _entry_spec.loader.exec_module(environment_entry)

ENDPOINTS = {
    "ipify_v4": ("https://api.ipify.org?format=json", 4),
    "ipify_v6": ("https://api6.ipify.org?format=json", 6),
    "ipify_dual": ("https://api64.ipify.org?format=json", None),
}
MAX_BODY = 4096
MAX_HEADERS = 8192
MAX_RETRY_AFTER_SECONDS = 86400
MAX_RETRY_AFTER_VALUE = 128


class ProbeError(ValueError):
    """Rejected request or bounded transport failure; messages contain no secrets."""


class Response:
    def __init__(self, status, body, retry_after_values=()):
        self.status = status
        self.body = body
        self.retry_after_values = retry_after_values


def parse_retry_after(values=(), *, response_observed_at=None, observed_clock_trusted=False):
    """Sanitized advice only. Never schedules work or treats a cap as permission.

    HTTP-date conversion requires a caller-attested, timezone-aware receipt clock.
    The attestation is evidence supplied by the host, not a clock validation service.
    Excessive delays are withheld rather than shortened into unsafe retry advice.
    """
    trusted = False
    observed_utc = None
    if observed_clock_trusted is True and isinstance(response_observed_at, datetime):
        try:
            if response_observed_at.tzinfo is not None and response_observed_at.utcoffset() is not None:
                observed_utc = response_observed_at.astimezone(timezone.utc)
                trusted = True
        except Exception:
            # Broken/custom timezone callbacks are untrusted clock evidence, not
            # a transport error. Never propagate their potentially private text.
            observed_utc = None
    result = dict(status="missing", delay_seconds=None, maximum_seconds=MAX_RETRY_AFTER_SECONDS,
                  clock_trust="caller_attested" if trusted else "unknown", automatic_retry=False)
    if not isinstance(values, (tuple, list)):
        result["status"] = "invalid"
        return result
    if len(values) > 1:
        result["status"] = "duplicate"
        return result
    if not values:
        return result
    value = values[0]
    if (not isinstance(value, str) or len(value) > MAX_RETRY_AFTER_VALUE
            or any(ord(c) < 32 or ord(c) > 126 for c in value)):
        result["status"] = "invalid"
        return result
    value = value.strip(' ')
    if re.fullmatch(r"[0-9]+", value):
        seconds = int(value)
    else:
        # HTTP-date's three wire formats; reject permissive parser suffixes/CRLF.
        weekday = r"(?:Mon|Tue|Wed|Thu|Fri|Sat|Sun)"
        month = r"(?:Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Oct|Nov|Dec)"
        formats = (weekday + r", [0-9]{2} " + month + r" [0-9]{4} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT",
                   r"(?:Monday|Tuesday|Wednesday|Thursday|Friday|Saturday|Sunday), [0-9]{2}-" + month + r"-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2} GMT",
                   weekday + " " + month + r" [ 0-9][0-9] [0-9]{2}:[0-9]{2}:[0-9]{2} [0-9]{4}")
        if not any(re.fullmatch(pattern, value) for pattern in formats):
            result["status"] = "invalid"
            return result
        try:
            date = parsedate_to_datetime(value)
            if date.tzinfo is None:  # obsolete asctime HTTP-date is always GMT
                date = date.replace(tzinfo=timezone.utc)
        except (ValueError, TypeError, OverflowError):
            result["status"] = "invalid"
            return result
        if not trusted:
            result["status"] = "clock_untrusted"
            return result
        delta = (date - observed_utc).total_seconds()
        if delta < 0:
            result["status"] = "past_date"
            return result
        seconds = math.ceil(delta)
    if seconds > MAX_RETRY_AFTER_SECONDS:
        result["status"] = "exceeds_cap"
        return result
    result.update(status="valid", delay_seconds=seconds)
    return result


def _parse_curl_response(raw, max_body):
    """Discard all header fields except bounded Retry-After multiplicity/values."""
    header_bytes = 0
    while True:
        block, separator, raw = raw.partition(b"\r\n\r\n")
        header_bytes += len(block) + 4
        if not separator or header_bytes > MAX_HEADERS:
            raise ProbeError("invalid_transport_response")
        lines = block.split(b"\r\n")
        match = re.fullmatch(rb"HTTP/1\.[01] ([0-9]{3})(?: [^\r\n]*)?", lines[0])
        if not match:
            raise ProbeError("invalid_transport_response")
        status = int(match.group(1))
        if 100 <= status < 200:
            continue
        values = []
        for line in lines[1:]:
            if line.startswith((b" ", b"\t")) or b":" not in line:
                raise ProbeError("invalid_transport_response")
            name, value = line.split(b":", 1)
            if name.lower() == b"retry-after":
                # Preserve duplicates; never retain arbitrary header contents.
                if len(values) < 2:
                    values.append(value.strip(b" \t").decode("ascii", errors="replace")
                                  if len(value) <= MAX_RETRY_AFTER_VALUE else None)
        body, separator, code = raw.rpartition(b"\n")
        if not separator or len(code) != 3 or not code.isdigit() or int(code) != status:
            raise ProbeError("invalid_transport_response")
        if len(body) > max_body:
            raise ProbeError("response_too_large")
        return Response(status, body, values)


def _fixed_curl():
    """Trusted OS locations and minimal environment; no inherited loader/TLS hooks."""
    if sys.platform == "win32":
        import ctypes
        buffer = ctypes.create_unicode_buffer(32768)
        try:
            size = ctypes.windll.kernel32.GetWindowsDirectoryW(buffer, len(buffer))
        except (AttributeError, OSError):
            raise ProbeError("transport_unavailable") from None
        if not 0 < size < len(buffer):
            raise ProbeError("transport_unavailable")
        root = buffer.value
        executable = root + "\\System32\\curl.exe"
        env = {"SystemRoot": root, "WINDIR": root, "PATH": root + "\\System32"}
        working_directory = root + "\\System32"
    else:
        executable = next((p for p in ("/usr/bin/curl", "/bin/curl") if Path(p).is_file()), None)
        env = {"PATH": "/usr/bin:/bin", "LC_ALL": "C"}
        working_directory = "/"
    if executable is None or not Path(executable).is_file():
        raise ProbeError("transport_unavailable")
    return executable, env, working_directory


class SystemRouteTransport:
    """curl subprocess, no config, credentials, inherited proxy, or redirects.

    OS routing/TUN remains intact. This does not prove an ISP-direct path.
    Uses a fixed system curl location, not PATH; no installation is attempted.
    stdout is bounded even on curl versions without --max-filesize support.
    """
    path_kind = "direct_socket_os_route_tun_unknown"

    def __init__(self, *, context_reader=None):
        # A live host callback from the existing target/authorization workflow,
        # never a deserialized approval, cached plan or automatic alias inference.
        self._context_reader = context_reader

    def current_probe_context(self):
        if not callable(self._context_reader):
            raise ProbeError('probe_context_binding_required')
        return self._context_reader()

    def request(self, url, *, connect_timeout, total_timeout, max_body):
        executable, env, working_directory = _fixed_curl()
        command = [str(executable), "--disable", "--silent", "--show-error",
                   "--connect-timeout", str(connect_timeout), "--max-time", str(total_timeout),
                   "--retry", "0", "--proto", "=https", "--http1.1", "--proxy", "",
                   "--noproxy", "*", "--max-filesize", str(max_body),
                   "--include", "--write-out", "\n%{http_code}", "--url", url]
        try:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, env=env, cwd=working_directory,
                                    shell=False, bufsize=0)
        except OSError:
            raise ProbeError("transport_unavailable") from None
        chunks = []
        overflow = threading.Event()
        failed = threading.Event()
        incomplete_headers = threading.Event()
        cleanup_failed = False

        def kill_child():
            try:
                proc.kill()
            except OSError:
                pass

        def read_bounded():
            try:
                header_count = 0
                while True:
                    block = bytearray()
                    while not block.endswith(b"\r\n\r\n"):
                        value = proc.stdout.read(1)
                        if not value:
                            # A curl DNS/connect/TLS failure can end before headers.
                            # Do not kill here: preserve its native exit code while
                            # the existing bounded parent wait reaps the process.
                            incomplete_headers.set()
                            return
                        block.extend(value)
                        header_count += len(value)
                        if header_count > MAX_HEADERS:
                            overflow.set()
                            kill_child()
                            return
                    chunks.append(bytes(block))
                    status_line = bytes(block).split(b"\r\n", 1)[0]
                    match = re.fullmatch(rb"HTTP/1\.[01] ([0-9]{3})(?: [^\r\n]*)?", status_line)
                    if not match:
                        raise ValueError("invalid status")
                    if not 100 <= int(match.group(1)) < 200:
                        break
                remaining = max_body + 5  # body + newline/status + one overflow byte
                while remaining:
                    value = proc.stdout.read(remaining)
                    if not value:
                        return
                    chunks.append(value)
                    remaining -= len(value)
                overflow.set()
                kill_child()
            except Exception:
                failed.set()
                kill_child()

        reader = threading.Thread(target=read_bounded, daemon=True)
        reader_started = False
        try:
            reader.start()
            reader_started = True
            proc.wait(timeout=total_timeout + 1)  # parent deadline, including DNS
        except subprocess.TimeoutExpired:
            raise ProbeError("timeout") from None
        finally:
            # Also runs for KeyboardInterrupt/SystemExit and reader startup errors.
            # Never leave a live curl intentionally, or wait without a bound.
            if proc.poll() is None:
                kill_child()
            try:
                proc.wait(timeout=1)
            except (subprocess.TimeoutExpired, OSError):
                cleanup_failed = True
            if reader_started:
                reader.join(timeout=1)
                cleanup_failed = cleanup_failed or reader.is_alive()
            try:
                proc.stdout.close()  # unbuffered pipe: no buffered-reader lock wait
            except OSError:
                cleanup_failed = True
        if cleanup_failed:
            raise ProbeError("transport_cleanup_failed")
        if failed.is_set():
            raise ProbeError("transport_read_failed")
        if overflow.is_set() or proc.returncode == 63:
            raise ProbeError("response_too_large")
        if proc.returncode:
            phase = {2: "transport_unsupported", 5: "dns_error", 6: "dns_error",
                     7: "connect_error", 28: "timeout", 35: "tls_error", 60: "tls_error"}
            raise ProbeError(phase.get(proc.returncode, "transport_error"))
        if incomplete_headers.is_set():
            raise ProbeError("invalid_transport_response")
        return _parse_curl_response(b"".join(chunks), max_body)


def _contains_permission(values, expected):
    # Built-in containers/plain strings only: final permission checks must not
    # run caller-defined membership/equality callbacks after entry revalidation.
    return (type(values) in (list, tuple, set, frozenset)
            and all(type(value) is str for value in values) and expected in values)


def _proxy_endpoint(transport):
    """Read exact credential-free endpoint from a trusted existing adapter.

    This validates an adapter binding, not protocol support or a proxy executor.
    Nothing here resolves/connects, and the endpoint is never included in output.
    """
    try:
        value = transport.proxy_endpoint
        if (type(value) is not str or len(value) > 2048
                or any(ord(char) < 33 or ord(char) > 126 for char in value)
                or '%' in value or '\\' in value):
            raise ValueError()
        parsed = urlsplit(value)
        if (parsed.scheme not in ('http', 'https', 'socks5', 'socks5h')
                or parsed.username is not None or parsed.password is not None
                or not parsed.hostname or parsed.port is None
                or not 1 <= parsed.port <= 65535 or parsed.path
                or parsed.query or parsed.fragment or '?' in value or '#' in value):
            raise ValueError()
        host = parsed.hostname
        if ':' in host:
            ipaddress.IPv6Address(host)
        elif re.fullmatch(r'[A-Za-z0-9](?:[A-Za-z0-9.-]*[A-Za-z0-9])?', host) is None:
            raise ValueError()
    except Exception:
        raise ProbeError('concrete_proxy_endpoint_binding_required') from None
    return value


def probe_https_ip(endpoint_id, *, approved_endpoints, approved_paths, target_ref,
                   path_kind="direct_socket_os_route_tun_unknown", transport=None,
                   response_clock=None, entry_request=None, approved_proxy_endpoints=None):
    """One request, no retries; approved_endpoints must contain the exact URL.

    approved_paths must explicitly include the requested path for this run.
    entry_request must pass active_probe for the same target; it grants no
    endpoint/path consent, target verification, or remote adapter capability.
    Optional response_clock() is called immediately after transport returns and
    yields (aware receipt datetime, explicit trust bool). Default local clock is
    untrusted; the helper does not verify clock synchronization. Never provide a
    pre-request timestamp. This guidance cannot authorize waiting or another call.

    Version 0.2 requires a trusted adapter current_probe_context() callback with
    the current, exact versioned context; declarations alone cannot bind runtime.
    Only shell HTTPS execution is supported here. Browser contexts require their
    own actual profile/origin adapter and cannot reuse shell evidence. The built-in
    SystemRouteTransport accepts a live context_reader from the existing host.
    Version 0.2 explicit_proxy also requires the trusted adapter's credential-free
    concrete proxy_endpoint in separately approved_proxy_endpoints for this run.
    No explicit proxy executor is supplied by this module.
    Unknown upstream protocol remains unknown. This single sample is not whole-
    machine acceptance. Version 0.1 keeps its previous strict eligibility.

    target_ref is a caller-verified local target/context alias, never transmitted.
    An injected transport must expose path_kind and request(url,
    connect_timeout=5,total_timeout=10,max_body=4096) -> Response. Caller must
    separately authorize/configure explicit_proxy transports (including endpoint
    and proxy); those must preserve TLS verification, bounds and redirect denial.
    Injection is a trusted adapter boundary, not a sandbox for untrusted plugins.
    Raw address is local evidence; redact/alias it before sharing ordinary reports.
    """
    try:
        environment_entry.assess_entry(entry_request)
        if (entry_request['schema_version'] == environment_entry.PROBE_ENTRY_SCHEMA
                and entry_request['probe_context']['executor'] != 'shell'):
            raise ProbeError('unsupported_probe_executor')
        entry = environment_entry.require_entry(
            entry_request, 'active_probe', target_ref, probe_executor='shell', probe_path=path_kind)
        entry_snapshot = deepcopy(entry_request)
    except (environment_entry.InvalidProjection, environment_entry.EntryBlocked) as exc:
        raise ProbeError(str(exc)) from None
    neutral_context = (entry_request['probe_context']
                       if entry_request['schema_version'] == environment_entry.PROBE_ENTRY_SCHEMA else None)
    if neutral_context is not None:
        if neutral_context['executor'] != 'shell':
            raise ProbeError('unsupported_probe_executor')
        if neutral_context['transport_path'] != path_kind:
            raise ProbeError('probe_context_path_mismatch')
    if transport is None and entry['target_role'] != 'local':
        raise ProbeError('target_binding_required')
    if endpoint_id not in ENDPOINTS:
        raise ProbeError("endpoint_not_allowlisted")
    url, expected_family = ENDPOINTS[endpoint_id]
    if not _contains_permission(approved_endpoints, url):
        raise ProbeError("exact_endpoint_consent_required")
    if not isinstance(target_ref, str) or not target_ref.strip() or len(target_ref) > 128:
        raise ProbeError("target_binding_required")
    if path_kind not in ("direct_socket_os_route_tun_unknown", "explicit_proxy"):
        raise ProbeError("unsupported_path_kind")
    if not _contains_permission(approved_paths, path_kind):
        raise ProbeError("explicit_path_consent_required")
    transport = transport if transport is not None else SystemRouteTransport()
    try:
        adapter_path = getattr(transport, "path_kind", None)
    except Exception:
        raise ProbeError('transport_error') from None
    if adapter_path != path_kind:
        raise ProbeError("transport_path_mismatch")
    read_context = None
    if neutral_context is not None:
        try:
            read_context = transport.current_probe_context
        except Exception:
            raise ProbeError('probe_context_binding_required') from None
        if not callable(read_context):
            raise ProbeError('probe_context_binding_required')

    def read_adapter_snapshot():
        if read_context is None:
            return None
        try:
            current_path = transport.path_kind
        except Exception:
            raise ProbeError('transport_error') from None
        if type(current_path) is not str or current_path != path_kind:
            raise ProbeError('transport_path_mismatch')
        try:
            current = read_context()
            environment_entry.validate_probe_context(current)
            # Freeze each field before another descriptor can mutate shared data.
            current = deepcopy(current)
        except Exception:
            raise ProbeError('probe_context_binding_required') from None
        if current != entry_snapshot['probe_context']:
            raise ProbeError('probe_context_mismatch')
        proxy = _proxy_endpoint(transport) if path_kind == 'explicit_proxy' else None
        if proxy is not None and not _contains_permission(approved_proxy_endpoints, proxy):
            raise ProbeError('exact_proxy_endpoint_consent_required')
        return current_path, current, proxy

    adapter_snapshot = read_adapter_snapshot()

    def check_adapter_snapshot():
        current = read_adapter_snapshot()
        if current != adapter_snapshot:
            # Path/context differences already have their own fixed error codes.
            raise ProbeError('proxy_endpoint_changed')

    # Bind once before the final entry check: a request descriptor can invoke a
    # trusted-host callback too. Looking it up at the call site would leave a
    # withdrawal/resource-change gap after that check.
    try:
        send_request = transport.request
    except Exception:
        raise ProbeError('transport_error') from None
    if not callable(send_request):
        raise ProbeError('transport_error')
    if neutral_context is not None:
        # Bounded unified checks: initial snapshot above, a post-descriptor
        # refresh, then one verification sweep for persistent cross-field changes
        # caused by those refresh callbacks (e.g. endpoint refresh changes the
        # namespace, or context refresh changes path). Never wait for arbitrary
        # callbacks to converge. This is a trusted-host adapter boundary, not a
        # sandbox against malicious Python that defers mutation to the last read.
        check_adapter_snapshot()
        check_adapter_snapshot()
    # Trusted adapter properties may run callbacks; revalidate the full current
    # declaration, including resource aliases, before its first transport call.
    try:
        environment_entry.require_entry(
            entry_request, 'active_probe', target_ref, probe_executor='shell', probe_path=path_kind)
    except (environment_entry.InvalidProjection, environment_entry.EntryBlocked) as exc:
        raise ProbeError(str(exc)) from None
    if entry_request != entry_snapshot:
        raise ProbeError('ENTRY_CHANGED')
    def check_scoped_permissions():
        # Plain-container checks do not invoke host callbacks.
        if not _contains_permission(approved_endpoints, url):
            raise ProbeError('exact_endpoint_consent_required')
        if not _contains_permission(approved_paths, path_kind):
            raise ProbeError('explicit_path_consent_required')
        if (adapter_snapshot is not None and adapter_snapshot[2] is not None
                and not _contains_permission(approved_proxy_endpoints, adapter_snapshot[2])):
            raise ProbeError('exact_proxy_endpoint_consent_required')

    # Adapter callbacks cannot withdraw independently scoped permission and then
    # send under the earlier membership check.
    check_scoped_permissions()
    result = dict(endpoint=url, endpoint_id=endpoint_id, target_ref=target_ref,
                  sample_type="probe_https", path_kind=path_kind,
                  expected_address_family=expected_family, observed_address_family=None,
                  observed_ip=None, status="unknown", http_status=None, error=None,
                  path_association="unknown", browser_path="not_observed",
                  started_at=datetime.now(timezone.utc).isoformat(), request_count=1,
                  limits={"connect_seconds": 5, "total_seconds": 10, "max_body_bytes": MAX_BODY,
                          "retries": 0, "max_header_bytes": MAX_HEADERS},
                  retry_after=None,
                  interpretation="One neutral HTTPS sample; no safety or target-route certification")
    if neutral_context is not None:
        result.update(probe_context=deepcopy(entry_snapshot['probe_context']),
                      final_egress_declaration=deepcopy(entry_snapshot['final_egress']),
                      resource_declaration=deepcopy(entry_snapshot['network']),
                      coverage='single_context_sample_not_whole_machine',
                      probe_binding_status='matched_trusted_host_assertion_not_independently_verified')
    try:
        response = send_request(url, connect_timeout=5, total_timeout=10, max_body=MAX_BODY)
        observed_at, clock_trusted = datetime.now(timezone.utc), False
        if response_clock is not None:
            try:
                observed_at, clock_trusted = response_clock()
            except Exception:
                observed_at, clock_trusted = None, False
        result["http_status"] = response.status
        if not isinstance(response.body, bytes) or len(response.body) > MAX_BODY:
            raise ProbeError("response_too_large_or_invalid")
        if 300 <= response.status < 400:
            raise ProbeError("redirect_rejected")
        if response.status == 429:
            result["retry_after"] = parse_retry_after(
                getattr(response, "retry_after_values", ()),
                response_observed_at=observed_at,
                observed_clock_trusted=clock_trusted)
            raise ProbeError("rate_limited_no_retry")
        if response.status != 200:
            raise ProbeError("http_error")
        try:
            payload = json.loads(response.body.decode("utf-8"))
            address = payload.get("ip") if isinstance(payload, dict) else None
            if not isinstance(address, str) or "%" in address:
                raise ValueError()
            parsed = ipaddress.ip_address(address)
        except (UnicodeError, ValueError, TypeError, RecursionError):
            raise ProbeError("invalid_ip_json") from None
        if expected_family is not None and parsed.version != expected_family:
            raise ProbeError("unexpected_address_family")
        if not parsed.is_global:
            raise ProbeError("non_public_echo_address")
        if neutral_context is not None:
            # A response/clock callback can change the current context after the
            # one request. Do not relabel that old sample as current acceptance.
            # Later withdrawal does not imply the already-sent request lacked
            # permission at send time; request_count remains one, with no retry.
            try:
                check_adapter_snapshot()
                check_adapter_snapshot()
                environment_entry.require_entry(
                    entry_request, 'active_probe', target_ref,
                    probe_executor='shell', probe_path=path_kind)
                if entry_request != entry_snapshot:
                    raise ValueError()
                check_scoped_permissions()
            except Exception:
                raise ProbeError('probe_context_changed_after_send') from None
        result.update(status="observed", observed_ip=str(parsed), observed_address_family=parsed.version)
    except ProbeError as exc:
        # Only controlled adapter errors should be raised as ProbeError.
        allowed = {"transport_unavailable", "transport_unsupported", "response_too_large",
                   "transport_cleanup_failed", "transport_read_failed", "timeout", "dns_error", "connect_error", "tls_error", "transport_error",
                   "invalid_transport_response", "response_too_large_or_invalid",
                   "redirect_rejected", "rate_limited_no_retry", "http_error", "invalid_ip_json",
                   "unexpected_address_family", "non_public_echo_address", "probe_context_changed_after_send"}
        result["error"] = str(exc) if str(exc) in allowed else "transport_error"
    except TimeoutError:
        result["error"] = "timeout"
    except Exception:
        result["error"] = "transport_error"  # Never echo credential-bearing exception text.
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    return result
