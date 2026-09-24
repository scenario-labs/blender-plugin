# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Installed job aliases and authenticated discovery of actual tool descriptions."""

import json
import socket
import unittest
import urllib.request
from unittest.mock import patch

from helpers import isolated_manager, submodule


class McpContractTests(unittest.TestCase):
    def setUp(self):
        self.tools = submodule("mcp.tools_scenario")

    def test_job_status_and_wait_accept_local_or_remote_ids_under_either_spelling(self):
        records = submodule("core.jobs.records")
        with isolated_manager() as manager:
            rec = records.JobRecord.new(
                lane="image", kind="image", model_id="model_fixture", body={"prompt": "fixture"}
            )
            rec.job_id, rec.status = "job_fixture", "success"
            manager.registry.add(rec)
            for field in ("job_id", "id"):
                for reference in (rec.local_id, rec.job_id):
                    with self.subTest(field=field, reference=reference):
                        args = {field: reference, "timeout": 1}
                        result = self.tools.job_status(args)
                        self.assertEqual(result["local_id"], rec.local_id)
                        self.assertEqual(result["job_id"], rec.job_id)
                        self.assertEqual(self.tools.wait_for_job(args)["status"], "success")
                        # Resolving the alias succeeds before the no-files guard.
                        with self.assertRaisesRegex(ValueError, "no downloaded files"):
                            self.tools.import_result(args)
            self.assertEqual(
                self.tools.job_status({"job_id": rec.job_id, "id": "missing"})["local_id"],
                rec.local_id,
            )

    def test_import_alias_dispatches_the_same_tracked_result(self):
        records = submodule("core.jobs.records")
        handlers = submodule("blender.handlers")
        with isolated_manager() as manager, patch.object(handlers, "dispatch") as dispatch:
            rec = records.JobRecord.new(
                lane="image", kind="image", model_id="model_fixture", body={}
            )
            rec.job_id, rec.status = "job_fixture", "success"
            rec.files = ["synthetic-image.png"]
            manager.registry.add(rec)
            for args in ({"job_id": rec.job_id}, {"id": rec.local_id}):
                result = self.tools.import_result(args)
                self.assertEqual(result, {"applied": "image", "files": rec.files})
                dispatch.assert_called_with(("job_done", rec))
            self.assertEqual(dispatch.call_count, 2)

    def test_missing_or_nonstring_reference_fails_before_runtime_access(self):
        runtime = submodule("blender.runtime")
        with patch.object(runtime, "ensure_manager") as manager:
            for method in (
                self.tools.job_status,
                self.tools.wait_for_job,
                self.tools.import_result,
            ):
                for args in ({}, {"job_id": ""}, {"id": " "}, {"job_id": 42}):
                    with self.subTest(method=method.__name__, args=args):
                        with self.assertRaisesRegex(ValueError, "Provide job_id"):
                            method(args)
            manager.assert_not_called()

    def test_authenticated_http_discovery_exposes_all_real_tool_contracts(self):
        protocol = submodule("mcp.protocol")
        server_module = submodule("mcp.server")
        registry = protocol.Registry()
        for spec in (*submodule("mcp.tools_blender").SPECS, *self.tools.SPECS):
            registry.add(spec)
        with socket.socket() as reservation:
            reservation.bind(("127.0.0.1", 0))
            port = reservation.getsockname()[1]
        server = server_module.McpServer(
            "127.0.0.1",
            port,
            "synthetic-contract-token",
            registry,
            {"name": "test", "version": "0"},
        )
        try:
            host, port = server.start()
            request = urllib.request.Request(
                f"http://{host}:{port}/mcp",
                data=json.dumps({"jsonrpc": "2.0", "id": 1, "method": "tools/list"}).encode(),
                headers={
                    "Authorization": "Bearer synthetic-contract-token",
                    "Content-Type": "application/json",
                },
            )
            with urllib.request.urlopen(request, timeout=5) as response:
                tools = json.load(response)["result"]["tools"]
            self.assertEqual(len(tools), 19)
            for tool in tools:
                self.assertIn("Args:", tool["description"])
                self.assertIn("Returns:", tool["description"])
                if tool["name"] in {"job_status", "wait_for_job", "import_result"}:
                    self.assertLessEqual({"job_id", "id"}, set(tool["inputSchema"]["properties"]))
                    self.assertEqual(tool["inputSchema"]["required"], [])
        finally:
            server.stop()

    def test_installed_registry_matches_generated_reference(self):
        from gen_mcp_docs import GROUPS, ROOT, parse_specs

        expected = {tool["name"] for _, path in GROUPS for tool in parse_specs(ROOT / path)}
        service = submodule("blender.mcp_service")
        self.assertEqual(set(service.build_registry().names()), expected)
