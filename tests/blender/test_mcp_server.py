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
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch

from helpers import submodule


def post(url, payload, method="POST", extra_headers=None):
    data = json.dumps(payload).encode() if payload is not None else None
    headers = {"Content-Type": "application/json", "Accept": "application/json, text/event-stream"}
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
            "127.0.0.1", port, reg, {"name": "test", "version": "0"}, timeout=5.0
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
            {
                "jsonrpc": "2.0",
                "id": 1,
                "method": "initialize",
                "params": {"protocolVersion": "2025-06-18"},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["result"]["serverInfo"]["name"], "test")
        status, body = post(self.url, {"jsonrpc": "2.0", "method": "notifications/initialized"})
        self.assertEqual(status, 202)
        status, body = post(
            self.url,
            {
                "jsonrpc": "2.0",
                "id": 2,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {"text": "hi"}},
            },
        )
        self.assertEqual(json.loads(body["result"]["content"][0]["text"]), {"echo": "hi"})

    def test_methods_need_no_authorization(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        self.assertEqual(post(self.url, ping)[0], 200)
        older_setup = {"Authorization": "Bearer from-an-older-setup"}
        self.assertEqual(post(self.url, ping, extra_headers=older_setup)[0], 200)
        self.assertEqual(post(self.url, None, method="GET")[0], 405)
        status, body = post(self.url.replace("/mcp", "/health"), None, method="GET")
        self.assertEqual(status, 200)
        self.assertTrue(body["ok"])

    def test_timeout_when_main_thread_never_processes(self):
        self.stop.set()
        self.pump.join(timeout=1)
        mutations = []
        self.server.registry.get("echo").handler = lambda args: mutations.append("executed")
        self.server.timeout = 0.3
        status, body = post(
            self.url,
            {
                "jsonrpc": "2.0",
                "id": 3,
                "method": "tools/call",
                "params": {"name": "echo", "arguments": {}},
            },
        )
        self.assertEqual(status, 200)
        self.assertEqual(body["error"]["code"], -32000)
        self.assertIn("not executed", body["error"]["message"])
        self.server.process_pending()
        self.assertEqual(mutations, [])

    def test_stop_releases_queued_http_request_without_executing_on_restart(self):
        self.stop.set()
        self.pump.join(timeout=1)
        mutations = []
        self.server.registry.get("echo").handler = lambda args: mutations.append("executed")
        message = {"id": 1, "method": "tools/call", "params": {"name": "echo"}}
        with ThreadPoolExecutor(max_workers=1) as worker:
            response = worker.submit(post, self.url, message)
            deadline = time.monotonic() + 5
            while self.server._queue.empty() and time.monotonic() < deadline:
                time.sleep(0.001)
            self.assertFalse(self.server._queue.empty())
            self.server.stop()
            status, body = response.result(5)
        self.assertEqual(status, 200)
        self.assertIn("not executed", body["error"]["message"])
        self.server.start()
        self.server.process_pending()
        self.assertEqual(mutations, [])

    def test_origin_header_is_validated(self):
        ping = {"jsonrpc": "2.0", "id": 1, "method": "ping"}
        for method in ("POST", "GET", "DELETE"):
            for origin in ("https://evil.example", "null", "http://[::1"):
                with self.subTest(method=method, origin=origin):
                    self.assertEqual(
                        post(
                            self.url,
                            ping if method == "POST" else None,
                            method=method,
                            extra_headers={"Origin": origin},
                        )[0],
                        403,
                    )
        self.assertEqual(
            post(self.url, ping, extra_headers={"Origin": "http://127.0.0.1:39876"})[0], 200
        )
        self.assertEqual(post(self.url, ping)[0], 200)
        self.assertEqual(
            post(
                self.url.replace("/mcp", "/health"),
                None,
                method="GET",
                extra_headers={"Origin": "https://evil.example"},
            )[0],
            403,
        )
        self.assertEqual(post(self.url, None, method="OPTIONS")[0], 403)

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
                b"Origin: https://evil.example\r\n"
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

    def host_request(self, method, path, hosts, *, port=None):
        """Send one request with exactly these Host headers; return (status, JSON body)."""
        connection = http.client.HTTPConnection("127.0.0.1", port or self.server.port, timeout=5)
        try:
            connection.putrequest(method, path, skip_host=True, skip_accept_encoding=True)
            for host in hosts:
                connection.putheader("Host", host)
            body = b"" if method != "POST" else json.dumps({"id": 1, "method": "ping"}).encode()
            connection.putheader("Content-Length", str(len(body)))
            connection.endheaders(body)
            response = connection.getresponse()
            payload = response.read()
            return response.status, (json.loads(payload) if payload else None)
        finally:
            connection.close()

    def test_rebinding_host_is_refused_before_routing(self):
        port = self.server.port
        with patch.object(self.server, "handle") as dispatch:
            for method, path in [
                ("GET", "/health"),
                ("POST", "/mcp"),
                ("GET", "/mcp"),
                ("DELETE", "/mcp"),
                ("OPTIONS", "/mcp"),
            ]:
                for host in ("evil.example", f"evil.example:{port}", "127.0.0.1.evil.example"):
                    with self.subTest(method=method, path=path, host=host):
                        status, body = self.host_request(method, path, [host])
                        self.assertEqual((status, body), (403, {"error": "forbidden host"}))
                for hosts in ([], ["localhost", "localhost"]):
                    with self.subTest(method=method, path=path, hosts=hosts):
                        status, _body = self.host_request(method, path, hosts)
                        self.assertEqual(status, 400)
            dispatch.assert_not_called()

    def test_loopback_hosts_with_and_without_port_are_accepted(self):
        port = self.server.port
        for host in ("localhost", f"localhost:{port}", "127.0.0.1", f"[::1]:{port}", "[::1]"):
            with self.subTest(host=host):
                status, body = self.host_request("GET", "/health", [host])
                self.assertEqual(status, 200)
                self.assertTrue(body["ok"])
                status, body = self.host_request("POST", "/mcp", [host])
                self.assertEqual((status, body["result"]), (200, {}))

    def test_idle_connection_is_closed_by_the_server(self):
        server_mod = submodule("mcp.server")
        self.assertEqual(server_mod.IDLE_TIMEOUT, 60.0)
        idle = server_mod.McpServer(
            "127.0.0.1", 0, self.server.registry, {}, timeout=5.0, idle_timeout=0.2
        )
        idle.start()
        try:
            port = idle._httpd.server_port
            with socket.create_connection(("127.0.0.1", port), timeout=5) as client:
                client.settimeout(3)
                self.assertEqual(client.recv(1), b"")  # Closed without a response.
            status, _body = self.host_request("GET", "/health", ["localhost"], port=port)
            self.assertEqual(status, 200)
        finally:
            idle.stop()

    def test_non_loopback_bind_address_is_refused(self):
        server_mod = submodule("mcp.server")
        for host in ("0.0.0.0", "192.168.1.20", "::", "localhost"):
            with self.subTest(host=host), self.assertRaisesRegex(ValueError, "binds only"):
                server_mod.McpServer(host, 0, self.server.registry, {})
