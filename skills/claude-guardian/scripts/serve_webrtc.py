"""Finite loopback-only server for one fixed, opt-in WebRTC asset.

Starting this helper does not open a browser or initiate STUN. The served page
still requires explicit per-run consent and a user click in the intended browser
profile. Expiry stops the HTTP listener; it cannot revoke a previously loaded page.
No results, credentials, request logs, or user data are collected by this server.
"""
import argparse
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import math
from pathlib import Path
import socket
import threading
import time

ROUTE = '/webrtc-probe.html'
DEFAULT_DURATION = 300
MAX_DURATION = 900
MAX_CONNECTIONS = 8
ASSET = Path(__file__).resolve().parent.parent / 'assets' / 'webrtc-probe.html'


class _AssetHandler(BaseHTTPRequestHandler):
    protocol_version = 'HTTP/1.0'
    server_version = 'GuardianLocalProbe'
    sys_version = ''

    def log_message(self, *_args):
        pass

    def log_error(self, *_args):
        pass

    def send_error(self, code, message=None, explain=None):
        # Never reflect request paths, headers, methods, credentials, or exceptions.
        self._reply(code, b'Request rejected.\n', 'text/plain; charset=utf-8')

    def _reply(self, code, body, content_type):
        self.close_connection = True
        self.send_response(code)
        self.send_header('Content-Type', content_type)
        self.send_header('Content-Length', str(len(body)))
        self.send_header('Connection', 'close')
        self.send_header('Cache-Control', 'no-store')
        self.send_header('X-Content-Type-Options', 'nosniff')
        self.send_header('Referrer-Policy', 'no-referrer')
        self.send_header('X-Frame-Options', 'DENY')
        self.send_header('Cross-Origin-Resource-Policy', 'same-origin')
        self.send_header('Permissions-Policy', 'camera=(), microphone=(), geolocation=()')
        self.send_header('Content-Security-Policy', "default-src 'none'; script-src 'unsafe-inline'; style-src 'unsafe-inline'; connect-src 'none'; base-uri 'none'; form-action 'none'; frame-ancestors 'none'")
        self.end_headers()
        if self.command != 'HEAD':
            self.wfile.write(body)

    def _serve_asset(self):
        hosts = self.headers.get_all('Host', [])
        if hosts != [self.server.authority]:
            return self._reply(421, b'Invalid local host.\n', 'text/plain')
        origins = self.headers.get_all('Origin', [])
        if origins and origins != ['http://' + self.server.authority]:
            return self._reply(403, b'Origin rejected.\n', 'text/plain')
        if self.headers.get('Sec-Fetch-Site') == 'cross-site':
            return self._reply(403, b'Cross-site request rejected.\n', 'text/plain')
        if self.headers.get_all('Transfer-Encoding') or self.headers.get_all('Content-Length'):
            return self._reply(400, b'Request body not supported.\n', 'text/plain')
        # BaseHTTPRequestHandler normalizes a leading '//'; inspect the original
        # target as well so this endpoint accepts only one exact origin-form path.
        request_parts = self.requestline.split()
        if self.path != ROUTE or len(request_parts) < 2 or request_parts[1] != ROUTE:
            return self._reply(404, b'Not found.\n', 'text/plain')
        self._reply(200, self.server.asset, 'text/html; charset=utf-8')

    do_GET = _serve_asset
    do_HEAD = _serve_asset


class _BoundedServer(ThreadingHTTPServer):
    daemon_threads = True
    block_on_close = False
    allow_reuse_address = False

    def __init__(self, asset):
        self.asset = asset
        self.connections = set()
        self.connection_lock = threading.Lock()
        self.closing = False
        super().__init__(('127.0.0.1', 0), _AssetHandler)
        self.authority = '127.0.0.1:' + str(self.server_port)
        self.timeout = 0.05

    def process_request(self, request, client_address):
        with self.connection_lock:
            if self.closing or len(self.connections) >= MAX_CONNECTIONS:
                self.shutdown_request(request)
                return
            self.connections.add(request)
        request.settimeout(1.0)
        try:
            super().process_request(request, client_address)
        except Exception:
            with self.connection_lock:
                self.connections.discard(request)
            self.shutdown_request(request)
            raise

    def process_request_thread(self, request, client_address):
        try:
            super().process_request_thread(request, client_address)
        finally:
            with self.connection_lock:
                self.connections.discard(request)

    def handle_error(self, request, client_address):
        pass  # No tracebacks with request/user data.

    def server_close(self):
        with self.connection_lock:
            self.closing = True
            connections = tuple(self.connections)
        for connection in connections:
            try:
                connection.shutdown(socket.SHUT_RDWR)
            except OSError:
                pass
            connection.close()
        super().server_close()


class LocalProbeServer:
    """Explicit construction binds 127.0.0.1 on an OS-selected ephemeral port.

    Use as a context manager. serve() blocks until a finite deadline or cancellation
    and always closes listener and active requests. This is a single-use server.
    There is intentionally no host, port, directory, or asset-path option.
    """
    def __init__(self):
        if ASSET.is_symlink() or not ASSET.is_file():
            raise RuntimeError('Fixed WebRTC asset unavailable')
        asset = ASSET.read_bytes()
        if len(asset) > 128 * 1024:
            raise RuntimeError('Fixed WebRTC asset exceeds size limit')
        self._server = _BoundedServer(asset)
        self._cancel = threading.Event()
        self._started = False
        self._closed = False
        self.url = 'http://' + self._server.authority + ROUTE

    def __enter__(self):
        return self

    def __exit__(self, *_args):
        self.close()

    def close(self):
        self._cancel.set()
        if not self._closed:
            self._closed = True
            self._server.server_close()

    def serve(self, duration_seconds=DEFAULT_DURATION, cancel_event=None):
        if (isinstance(duration_seconds, bool) or not isinstance(duration_seconds, (int, float))
                or not math.isfinite(duration_seconds) or not 0 < duration_seconds <= MAX_DURATION):
            raise ValueError('Duration must be greater than zero and at most 900 seconds')
        if self._started or self._closed:
            raise RuntimeError('Server is single-use')
        self._started = True
        deadline = time.monotonic() + duration_seconds
        try:
            while not self._cancel.is_set() and not (cancel_event and cancel_event.is_set()):
                remaining = deadline - time.monotonic()
                if remaining <= 0:
                    break
                self._server.timeout = min(0.05, remaining)
                try:
                    self._server.handle_request()
                except (OSError, ValueError):
                    if not self._cancel.is_set():
                        raise
        finally:
            self.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--duration', type=float, default=DEFAULT_DURATION,
                        help='HTTP listener lifetime in seconds, greater than 0 and at most 900 (default 300)')
    args = parser.parse_args(argv)
    if not math.isfinite(args.duration) or not 0 < args.duration <= MAX_DURATION:
        parser.error('duration must be greater than 0 and at most 900 seconds')
    try:
        with LocalProbeServer() as server:
            print(server.url, flush=True)
            print('Open manually in the intended browser profile. No probe runs until consent and click. Ctrl+C stops the local server.', flush=True)
            server.serve(args.duration)
    except KeyboardInterrupt:
        return 130
    except (OSError, RuntimeError):
        print('Local WebRTC helper unavailable; no probe was started.', flush=True)
        return 1
    return 0


if __name__ == '__main__':
    raise SystemExit(main())
