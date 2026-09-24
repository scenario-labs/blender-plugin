# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
import http.client
import json
import socket
import threading
import time
import unittest
import urllib.error
import urllib.request
from unittest.mock import patch

from helpers import submodule


def post(url, token, payload, method="POST", extra_headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    headers.update(extra_headers or {})
    req = urllib.request.Request(url, data=data, method=method, headers=headers)
    try:
        with urllib.request.urlopen(req, timeout=10) as resp:
            body = resp.read()
            return resp.status, (json.loads(body) if body else None)
    except urllib.error.HTTPError as err:
        return err.code, None


class McpServerTests(unittest.TestCase):
    def setUp(self):
        protocol = submodule("mcp.protocol")
        server_mod = submodule("mcp.server")
        reg = protocol.Registry()
        reg.add(
            protocol.ToolSpec(
                "echo",
                "Echo",
                {"type": "object", "properties": {"text": {"type": "string"}}},
                lambda a: {"echo": a.get("text")},
            )
        )
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        self.server = server_mod.McpServer(
            "127.0.0.1", port, "tok", reg, {"name": "test", "version": "0"}, timeout=5.0
        )
        host, port = self.server.start()
        self.url = f"http://{host}:{port}/mcp"
        self.stop = threading.Event()
        self.pump = threading.Thread(target=self._pump, daemon=True)
        self.pump.start()

    def _pump(self):
        while not self.stop.is_set():
            self.server.process_pending()
            time.sleep(0.02)

    def tearDown(self):
        self.stop.set()
        self.server.stop()
        self.pump.join(timeout=2)

    def test_initialize_list_and_call_over_http(self):
        status, body = post(
            self.url,
            "tok",
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["serverInfo"]["name"], "test")
        status, body = post(
            self.url, "tok", {"jsonrpc": "2.0", "method": "notifications/initialized"}
        )
        self.assertEqual(status, 202)
        status, body = post(
            self.url,
            "tok",
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"text": "hi"}},
            },
        )
        self.assertEqual(json.loads(body["result"]["content"][0]["text"]), {"echo": "hi"})

    def test_auth_and_methods(self):
        self.assertEqual(
            post(self.url, None, {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0], 401
        )
        self.assertEqual(
            post(self.url, "wrong", {"jsonrpc": "2.0", "id": 1, "method": "ping"})[0], 401
        )
        self.assertEqual(post(self.url, "tok", None, method="GET")[0], 405)
        status, body = post(self.url.replace("/mcp", "/health"), None, None, method="GET")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_timeout_when_main_thread_never_processes(self):
        self.stop.set()
        self.pump.join(timeout=1)
        self.server.timeout = 0.3
        status, body = post(
            self.url,
            "tok",
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {}},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["error"]["code"], -32000)

    def test_origin_header_is_validated(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        for method in ("POST", "GET", "DELETE"):
            for origin in ("https://evil.example", "null", "http://[::1"):
                with self.subTest(method=method, origin=origin):
                    self.assertEqual(
                        post(
                            self.url,
                            "tok",
                            ping if method == "POST" else None,
                            method=method,
                            extra_headers={"Origin": origin},
                        )[0],
                        403,
                    )
        self.assertEqual(
            post(self.url, "tok", ping, extra_headers={"Origin": "http://127.0.0.1:39876"})[0], 200
        )
        self.assertEqual(post(self.url, "tok", ping)[0], 200)
        self.assertEqual(post(self.url, "tök", ping)[0], 401)
        self.assertEqual(
            post(
                self.url.replace("/mcp", "/health"),
                None,
                None,
                method="GET",
                extra_headers={"Origin": "https://evil.example"},
            )[0],
            403,
        )
        self.assertEqual(post(self.url, "tok", None, method="OPTIONS")[0], 403)

    def test_origin_rejection_sends_response_before_draining_delayed_body(self):
        finished = threading.Event()
        handler_class = self.server._httpd.RequestHandlerClass
        finish = handler_class.finish

        def observed_finish(handler):
            try:
                finish(handler)
            finally:
                finished.set()

        with (
            patch.object(handler_class, "finish", observed_finish),
            patch.object(self.server, "handle") as dispatch,
            socket.create_connection(("127.0.0.1", self.server.port), timeout=2) as client,
        ):
            client.sendall(
                b"POST /mcp HTTP/1.1\r\nHost: localhost\r\n"
                b"Authorization: Bearer tok\r\nOrigin: https://evil.example\r\n"
                b"Content-Length: 5\r\n\r\n"
            )
            response = http.client.HTTPResponse(client)
            response.begin()
            self.assertEqual(response.status, 403)
            self.assertEqual(response.getheader("Connection"), "close")
            self.assertIsNone(response.getheader("Access-Control-Allow-Origin"))
            self.assertEqual(json.loads(response.read()), {"error": "forbidden origin"})
            self.assertFalse(finished.wait(0.05))
            client.sendall(b"abcde")
            self.assertTrue(finished.wait(2))
            dispatch.assert_not_called()

    def test_duplicate_security_headers_are_rejected_without_cors(self):
        import http.client
        from urllib.parse import urlsplit

        address = urlsplit(self.url)
        for headers, status in [
            ([("Origin", "http://localhost"), ("Origin", "https://evil.example")], 403),
            ([("Authorization", "Bearer tok"), ("Authorization", "Bearer wrong")], 401),
        ]:
            connection = http.client.HTTPConnection(address.hostname, address.port, timeout=5)
            try:
                connection.putrequest("POST", "/mcp")
                for key, value in headers:
                    connection.putheader(key, value)
                connection.putheader("Content-Length", "0")
                connection.endheaders()
                response = connection.getresponse()
                self.assertEqual(response.status, status)
                self.assertIsNone(response.getheader("Access-Control-Allow-Origin"))
                response.read()
            finally:
                connection.close()
