"""Explicit, neutral endpoint diagnostics. Importing this module performs no I/O.

PD03 endpoint selection and runtime approval remain caller responsibilities. These
candidates are not standing approval. Evidence is for this probe only, never the
browser, Claude's routing, account eligibility, or an anti-ban guarantee.
"""
import ipaddress
import json
import os
from pathlib import Path
import subprocess
import threading
import sys
from datetime import datetime, timezone

ENDPOINTS = {
    "ipify_v4": ("https://api.ipify.org?format=json", 4),
    "ipify_v6": ("https://api6.ipify.org?format=json", 6),
    "ipify_dual": ("https://api64.ipify.org?format=json", None),
}
MAX_BODY = 4096


class ProbeError(ValueError):
    """Rejected request or bounded transport failure; messages contain no secrets."""


class Response:
    def __init__(self, status, body):
        self.status = status
        self.body = body


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

    def request(self, url, *, connect_timeout, total_timeout, max_body):
        executable, env, working_directory = _fixed_curl()
        command = [str(executable), "--disable", "--silent", "--show-error",
                   "--connect-timeout", str(connect_timeout), "--max-time", str(total_timeout),
                   "--retry", "0", "--proto", "=https", "--http1.1", "--proxy", "",
                   "--noproxy", "*", "--max-filesize", str(max_body),
                   "--write-out", "\n%{http_code}", "--url", url]
        try:
            proc = subprocess.Popen(command, stdin=subprocess.DEVNULL, stdout=subprocess.PIPE,
                                    stderr=subprocess.DEVNULL, env=env, cwd=working_directory,
                                    shell=False, bufsize=0)
        except OSError:
            raise ProbeError("transport_unavailable") from None
        chunks = []
        overflow = threading.Event()
        failed = threading.Event()
        cleanup_failed = False

        def kill_child():
            try:
                proc.kill()
            except OSError:
                pass

        def read_bounded():
            try:
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
        raw = b"".join(chunks)
        body, separator, code = raw.rpartition(b"\n")
        if not separator or len(code) != 3 or not code.isdigit():
            raise ProbeError("invalid_transport_response")
        return Response(int(code), body)


def probe_https_ip(endpoint_id, *, approved_endpoints, approved_paths, target_ref,
                   path_kind="direct_socket_os_route_tun_unknown", transport=None):
    """One request, no retries; approved_endpoints must contain the exact URL.

    approved_paths must explicitly include the requested path for this run.

    target_ref is a caller-verified local target/context alias, never transmitted.
    An injected transport must expose path_kind and request(url,
    connect_timeout=5,total_timeout=10,max_body=4096) -> Response. Caller must
    separately authorize/configure explicit_proxy transports (including endpoint
    and proxy); those must preserve TLS verification, bounds and redirect denial.
    Injection is a trusted adapter boundary, not a sandbox for untrusted plugins.
    Raw address is local evidence; redact/alias it before sharing ordinary reports.
    """
    if endpoint_id not in ENDPOINTS:
        raise ProbeError("endpoint_not_allowlisted")
    url, expected_family = ENDPOINTS[endpoint_id]
    if not isinstance(approved_endpoints, (list, tuple, set, frozenset)) or url not in approved_endpoints:
        raise ProbeError("exact_endpoint_consent_required")
    if not isinstance(target_ref, str) or not target_ref.strip() or len(target_ref) > 128:
        raise ProbeError("target_binding_required")
    if path_kind not in ("direct_socket_os_route_tun_unknown", "explicit_proxy"):
        raise ProbeError("unsupported_path_kind")
    if not isinstance(approved_paths, (list, tuple, set, frozenset)) or path_kind not in approved_paths:
        raise ProbeError("explicit_path_consent_required")
    transport = transport if transport is not None else SystemRouteTransport()
    if getattr(transport, "path_kind", None) != path_kind:
        raise ProbeError("transport_path_mismatch")
    result = dict(endpoint=url, endpoint_id=endpoint_id, target_ref=target_ref,
                  sample_type="probe_https", path_kind=path_kind,
                  expected_address_family=expected_family, observed_address_family=None,
                  observed_ip=None, status="unknown", http_status=None, error=None,
                  path_association="unknown", browser_path="not_observed",
                  started_at=datetime.now(timezone.utc).isoformat(), request_count=1,
                  limits={"connect_seconds": 5, "total_seconds": 10, "max_body_bytes": MAX_BODY,
                          "retries": 0},
                  interpretation="One neutral HTTPS sample; no safety or target-route certification")
    try:
        response = transport.request(url, connect_timeout=5, total_timeout=10, max_body=MAX_BODY)
        result["http_status"] = response.status
        if not isinstance(response.body, bytes) or len(response.body) > MAX_BODY:
            raise ProbeError("response_too_large_or_invalid")
        if 300 <= response.status < 400:
            raise ProbeError("redirect_rejected")
        if response.status == 429:
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
        result.update(status="observed", observed_ip=str(parsed), observed_address_family=parsed.version)
    except ProbeError as exc:
        # Only controlled adapter errors should be raised as ProbeError.
        allowed = {"transport_unavailable", "transport_unsupported", "response_too_large",
                   "transport_cleanup_failed", "transport_read_failed", "timeout", "dns_error", "connect_error", "tls_error", "transport_error",
                   "invalid_transport_response", "response_too_large_or_invalid",
                   "redirect_rejected", "rate_limited_no_retry", "http_error", "invalid_ip_json",
                   "unexpected_address_family", "non_public_echo_address"}
        result["error"] = str(exc) if str(exc) in allowed else "transport_error"
    except TimeoutError:
        result["error"] = "timeout"
    except Exception:
        result["error"] = "transport_error"  # Never echo credential-bearing exception text.
    result["finished_at"] = datetime.now(timezone.utc).isoformat()
    return result
