# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local MCP server over Streamable HTTP. The HTTP thread never touches bpy: tool handlers run on the
main thread through process_pending(), called by the pump (GUI) or serve_blocking() (headless)."""

import hmac
import http.server
import json
import logging
import queue
import socket
import threading
import time
from urllib.parse import urlsplit

from . import protocol

log = logging.getLogger("scenario.mcp")
MAX_BODY = 10 * 1024 * 1024
REJECT_DRAIN_TIMEOUT = 1.0
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})


def origin_allowed(origin):
    """Native clients omit Origin; browser origins must be HTTP(S) loopback."""
    if origin is None:
        return True
    if not isinstance(origin, str) or not origin or any(c.isspace() for c in origin):
        return False
    try:
        parsed = urlsplit(origin)
        _ = parsed.port  # Validate malformed and out-of-range ports too.
        return (
            parsed.scheme in {"http", "https"}
            and parsed.hostname in LOOPBACK_HOSTS
            and parsed.username is None
            and parsed.password is None
            and not parsed.path
            and not parsed.query
            and not parsed.fragment
        )
    except ValueError:
        return False


def token_matches(header, token):
    """Compare only explicit nonempty bearer credentials without timing leaks."""
    if not isinstance(header, str) or not isinstance(token, str) or not token:
        return False
    if not header.startswith("Bearer "):
        return False
    return hmac.compare_digest(header[7:].strip().encode("utf-8"), token.encode("utf-8"))


class _Pending:
    __slots__ = ("handler", "arguments", "event", "result", "error")

    def __init__(self, handler, arguments):
        self.handler, self.arguments = handler, arguments
        self.event = threading.Event()
        self.result, self.error = None, None


class McpServer:
    def __init__(self, host, port, token, registry, server_info, timeout=120.0, blender_version=""):
        if not isinstance(token, str) or not token.strip():
            raise ValueError("A nonempty local MCP bearer token is required")
        self.host, self.port, self.token = host, int(port), token
        self.registry, self.server_info, self.timeout = registry, server_info, timeout
        self.blender_version = blender_version
        self.calls_served = 0
        self._queue = queue.Queue()
        self._httpd = None
        self._thread = None

    @property
    def running(self):
        return self._httpd is not None

    @property
    def url(self):
        return f"http://{self.host}:{self.port}/mcp"

    def start(self):
        last_error = None
        for candidate in range(self.port, self.port + 4):
            try:
                httpd = http.server.ThreadingHTTPServer((self.host, candidate), _make_handler(self))
                httpd.daemon_threads = True
                self.port = candidate
                self._httpd = httpd
                break
            except OSError as err:
                last_error = err
        if self._httpd is None:
            raise OSError(f"no free port from {self.port}: {last_error}")
        self._thread = threading.Thread(
            target=self._httpd.serve_forever,
            kwargs={"poll_interval": 0.25},
            daemon=True,
            name="scenario-mcp-http",
        )
        self._thread.start()
        log.info("MCP server listening on %s", self.url)
        return self.host, self.port

    def stop(self):
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    # -- main-thread executor ---------------------------------------------
    def executor(self, handler, arguments):
        pending = _Pending(handler, arguments)
        self._queue.put(pending)
        if not pending.event.wait(self.timeout):
            raise protocol.ToolTimeout(
                f"no response from Blender's main thread within {self.timeout:g} s"
            )
        if pending.error is not None:
            raise pending.error
        return pending.result

    def process_pending(self, max_items=8):
        done = 0
        while done < max_items:
            try:
                pending = self._queue.get_nowait()
            except queue.Empty:
                return done
            try:
                pending.result = pending.handler(pending.arguments)
            except Exception as err:  # delivered to the HTTP thread as a tool error
                pending.error = err
            finally:
                pending.event.set()
            done += 1
        return done

    def serve_blocking(self, stop_event, interval=0.05):
        while not stop_event.is_set():
            if not self.process_pending():
                time.sleep(interval)

    def handle(self, message):
        response = protocol.handle_message(
            message, self.registry, self.server_info, executor=self.executor
        )
        if isinstance(message, dict) and message.get("method") == "tools/call":
            self.calls_served += 1
        return response


def _make_handler(server):
    class Handler(http.server.BaseHTTPRequestHandler):
        protocol_version = "HTTP/1.1"

        def log_message(self, fmt, *args):
            log.debug("http %s", fmt % args)

        def _send(self, status, body=None, headers=None):
            raw = json.dumps(body).encode("utf-8") if body is not None else b""
            self.send_response(status)
            self.send_header("Content-Type", "application/json")
            self.send_header("Content-Length", str(len(raw)))
            for key, value in (headers or {}).items():
                self.send_header(key, value)
            self.end_headers()
            if raw:
                self.wfile.write(raw)

        def _authorized(self):
            headers = self.headers.get_all("Authorization", [])
            return len(headers) == 1 and token_matches(headers[0], server.token)

        def _content_length(self):
            lengths = self.headers.get_all("Content-Length", [])
            if self.headers.get_all("Transfer-Encoding") or len(lengths) > 1:
                return None
            if not lengths:
                return 0
            value = lengths[0].strip()
            if not value.isascii() or not value.isdecimal() or len(value) > 20:
                return None
            return int(value)

        def _reject(self, status, body, headers=None):
            # RFC 9112 section 9.6: closing with unread request bytes can reset
            # the connection before the peer receives the error response.
            self.close_connection = True
            self._send(status, body, {**(headers or {}), "Connection": "close"})
            self.wfile.flush()
            try:
                self.connection.shutdown(socket.SHUT_WR)
                remaining = self._content_length()
                if remaining is None or remaining > MAX_BODY:
                    return
                deadline = time.monotonic() + REJECT_DRAIN_TIMEOUT
                while remaining:
                    timeout = deadline - time.monotonic()
                    if timeout <= 0:
                        break
                    self.connection.settimeout(timeout)
                    data = self.rfile.read1(min(remaining, 65536))
                    if not data:
                        break
                    remaining -= len(data)
            except OSError:
                # The response was already sent. Timeout/reset only ends drain;
                # rejected bytes are never parsed, queued or retried.
                pass

        def _origin_ok(self):
            origins = self.headers.get_all("Origin", [])
            if len(origins) > 1 or not origin_allowed(origins[0] if origins else None):
                self._reject(403, {"error": "forbidden origin"})
                return False
            return True

        def do_OPTIONS(self):
            self._reject(403, {"error": "forbidden origin"})

        def do_GET(self):
            if not self._origin_ok():
                return
            if self.path.rstrip("/") == "/health":
                return self._send(
                    200,
                    {"ok": True, "blender": server.blender_version, "server": server.server_info},
                )
            if not self._authorized():
                return self._send(401, {"error": "unauthorized"}, {"WWW-Authenticate": "Bearer"})
            self._send(
                405, {"error": "SSE streams are not offered; use POST"}, {"Allow": "POST, DELETE"}
            )

        def do_DELETE(self):
            if not self._origin_ok():
                return
            self._send(200 if self._authorized() else 401, {})

        def do_POST(self):
            if not self._origin_ok():
                return
            if self.path.rstrip("/") != "/mcp":
                return self._reject(404, {"error": "not found"})
            if not self._authorized():
                return self._reject(401, {"error": "unauthorized"}, {"WWW-Authenticate": "Bearer"})
            length = self._content_length()
            if length is None:
                return self._reject(400, {"error": "invalid request framing"})
            if length > MAX_BODY:
                return self._reject(413, {"error": "request too large"})
            raw = self.rfile.read(length) if length else b""
            message, parse_error = protocol.parse_body(raw)
            if parse_error:
                return self._send(400, parse_error)
            if isinstance(message, list):
                responses = [r for r in (server.handle(m) for m in message) if r is not None]
                return self._send(200, responses) if responses else self._send(202)
            response = server.handle(message)
            if response is None:
                return self._send(202)
            self._send(200, response)

    return Handler
