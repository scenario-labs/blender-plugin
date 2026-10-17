# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Local MCP server over Streamable HTTP. The HTTP thread never touches bpy: tool handlers run on the
main thread through process_pending(), called by the pump (GUI) or serve_blocking() (headless)."""

import contextlib
import http.server
import json
import logging
import math
import queue
import socket
import socketserver
import threading
import time
from urllib.parse import urlsplit

from . import protocol

log = logging.getLogger("scenario.mcp")
MAX_BODY = 10 * 1024 * 1024
REJECT_DRAIN_TIMEOUT = 1.0
# A socket read or write that makes no progress for this long ends the connection, so an idle
# keep-alive connection or a stalled request no longer holds a server thread. It never applies
# while a request waits for Blender's main thread or a job: that wait reads nothing.
IDLE_TIMEOUT = 60.0
BIND_HOST = "127.0.0.1"
LOOPBACK_HOSTS = frozenset({"127.0.0.1", "localhost", "::1"})
_running = threading.local()


def host_allowed(value):
    """DNS-rebinding guard: the Host header must name loopback, with an optional port.

    127.0.0.1, localhost or [::1] in any letter case, optionally followed by :port. A browser
    sends the host name of the page it loaded, so a rebound page is refused even though its
    name now resolves to 127.0.0.1.
    """
    if not isinstance(value, str):
        return False
    value = value.strip(" \t").lower()
    if value.startswith("[::1]"):
        name, rest = "::1", value[5:]
    else:
        # An unbracketed IPv6 address splits at its first colon and is refused.
        name, colon, port = value.partition(":")
        rest = colon + port
    if name not in LOOPBACK_HOSTS:
        return False
    if not rest:
        return True
    port = rest[1:]
    return (
        rest[0] == ":"
        and port.isascii()
        and port.isdecimal()
        and len(port) <= 5
        and 0 < int(port) <= 65535
    )


def executing_tool():
    """True while this thread runs an agent's tool call on Blender's main thread.

    Blender glue uses it to tell an agent's change to a file field from the user's choice.
    """
    return getattr(_running, "depth", 0) > 0


@contextlib.contextmanager
def _running_tool():
    _running.depth = getattr(_running, "depth", 0) + 1
    try:
        yield
    finally:
        _running.depth -= 1


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


class _Pending:
    def __init__(self, handler, arguments, timeout):
        self.handler, self.arguments = handler, arguments
        self.event = threading.Event()
        self.result = None
        self.error: Exception | None = None
        self.deadline = time.monotonic() + timeout
        self._lock = threading.Lock()
        self._state = "queued"

    def _cancel(self, reason):
        self._state = "cancelled"
        self.error = protocol.ToolTimeout(reason)
        self.handler = self.arguments = None
        self.event.set()

    def cancel(self, reason):
        with self._lock:
            if self._state == "queued":
                self._cancel(reason)

    def begin(self):
        with self._lock:
            if self._state != "queued":
                return False
            if time.monotonic() >= self.deadline:
                self._cancel("request expired in Blender's queue; the tool was not executed")
                return False
            self._state = "running"
            return True

    def finish(self, result=None, error: Exception | None = None):
        with self._lock:
            self.result, self.error = result, error
            self._state = "done"
            self.handler = self.arguments = None
            self.event.set()

    def outcome(self):
        with self._lock:
            if self._state == "queued":
                self._cancel("request expired in Blender's queue; the tool was not executed")
            elif self._state == "running":
                raise protocol.ToolTimeout(
                    "the tool started but has not finished; its outcome is unknown. "
                    "Inspect the operation before retrying; do not resubmit automatically"
                )
            error = self.error
            if error is not None:
                raise error
            return self.result


class _HTTPServer(http.server.ThreadingHTTPServer):
    """HTTPServer.server_bind resolves the bind address with socket.getfqdn(), a reverse DNS
    query that can wait for a resolver timeout while start() holds Blender's main thread.
    Nothing reads server_name, so record the address as given instead."""

    def server_bind(self):
        socketserver.TCPServer.server_bind(self)
        self.server_name, self.server_port = self.server_address[:2]


class McpServer:
    def __init__(
        self,
        host,
        port,
        registry,
        server_info,
        timeout=120.0,
        blender_version="",
        idle_timeout=IDLE_TIMEOUT,
    ):
        if host != BIND_HOST:
            raise ValueError(f"The local MCP server binds only to {BIND_HOST}")
        if type(idle_timeout) not in (int, float) or not 0 < idle_timeout < math.inf:
            raise ValueError("idle_timeout must be a positive number of seconds")
        self.host, self.port = host, int(port)
        self.registry, self.server_info, self.timeout = registry, server_info, timeout
        self.idle_timeout = idle_timeout
        self.blender_version = blender_version
        self.calls_served = 0
        self._queue = queue.Queue()
        self._admission = threading.Lock()
        self._stopped = False
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
                httpd = _HTTPServer((self.host, candidate), _make_handler(self))
                httpd.daemon_threads = True
                self.port = candidate
                self._httpd = httpd
                break
            except OSError as err:
                last_error = err
        if self._httpd is None:
            raise OSError(f"no free port from {self.port}: {last_error}")
        with self._admission:
            self._stopped = False
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
        with self._admission:
            self._stopped = True
            while True:
                try:
                    pending = self._queue.get_nowait()
                except queue.Empty:
                    break
                pending.cancel("MCP server stopped before execution; the tool was not executed")
        if self._httpd is not None:
            self._httpd.shutdown()
            self._httpd.server_close()
            self._httpd = None

    # -- main-thread executor ---------------------------------------------
    def executor(self, handler, arguments):
        pending = _Pending(handler, arguments, self.timeout)
        with self._admission:
            if self._stopped:
                raise protocol.ToolTimeout("MCP server is stopped; the tool was not executed")
            self._queue.put(pending)
        pending.event.wait(max(0.0, pending.deadline - time.monotonic()))
        return pending.outcome()

    def process_pending(self, max_items=8):
        done = 0
        while done < max_items:
            with self._admission:
                try:
                    pending = self._queue.get_nowait()
                except queue.Empty:
                    return done
                admitted = not self._stopped and pending.begin()
            done += 1
            if not admitted:
                continue
            try:
                with _running_tool():
                    result = pending.handler(pending.arguments)
            except Exception as err:  # delivered to the HTTP thread as a tool error
                pending.finish(error=err)
            except BaseException:
                # Preserve main-thread interruption, but release the HTTP caller
                # with a tool failure rather than a timeout or false success.
                pending.finish(error=RuntimeError("Tool execution was interrupted"))
                raise
            else:
                pending.finish(result=result)
        return done

    def serve_blocking(self, stop_event, interval=0.05, *, before_process=None):
        while not stop_event.is_set():
            if before_process is not None:
                before_process()
            if stop_event.is_set():
                break
            if not self.process_pending():
                stop_event.wait(interval)

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
        # StreamRequestHandler.setup applies it to every read and write on the connection.
        timeout = server.idle_timeout

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

        def _admitted(self):
            """Check Host, then Origin, before any routing or body read."""
            hosts = self.headers.get_all("Host", [])
            if len(hosts) != 1:
                # RFC 9112 section 3.2: a request without exactly one Host gets 400.
                self._reject(400, {"error": "exactly one Host header is required"})
                return False
            if not host_allowed(hosts[0]):
                self._reject(403, {"error": "forbidden host"})
                return False
            origins = self.headers.get_all("Origin", [])
            if len(origins) > 1 or not origin_allowed(origins[0] if origins else None):
                self._reject(403, {"error": "forbidden origin"})
                return False
            return True

        def do_OPTIONS(self):
            if self._admitted():  # Browser preflights are never offered.
                self._reject(403, {"error": "forbidden origin"})

        def do_GET(self):
            if not self._admitted():
                return
            if self.path.rstrip("/") == "/health":
                return self._send(
                    200,
                    {"ok": True, "blender": server.blender_version, "server": server.server_info},
                )
            self._send(
                405, {"error": "SSE streams are not offered; use POST"}, {"Allow": "POST, DELETE"}
            )

        def do_DELETE(self):
            if not self._admitted():
                return
            self._send(200, {})

        def do_POST(self):
            if not self._admitted():
                return
            if self.path.rstrip("/") != "/mcp":
                return self._reject(404, {"error": "not found"})
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
