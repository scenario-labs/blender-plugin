# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Real bundled SDK/dependency imports and synthetic service calls inside Blender."""

import hashlib
import importlib
import importlib.metadata
import json
import sys
import unittest
import zipfile
from decimal import Decimal
from pathlib import Path
from unittest.mock import patch

import bpy
from helpers import addon, online_access, submodule

EVIDENCE = {}


class SDKBundleTests(unittest.TestCase):
    def test_dependencies_and_native_binary_match_installed_wheel_bytes(self):
        installed = Path(addon().__file__).parent
        lock = json.loads((installed / "sdk-wheel-lock.json").read_text())
        local = Path(bpy.utils.resource_path("USER")) / "extensions/.local"
        binary = Path(importlib.import_module("pydantic_core._pydantic_core").__file__).resolve()
        distribution = importlib.metadata.distribution("pydantic-core")
        relative = binary.relative_to(Path(distribution.locate_file("")).resolve()).as_posix()
        matched = []
        for wheel in lock["wheels"]:
            if wheel["package"] == "pydantic-core":
                with zipfile.ZipFile(installed / "wheels" / wheel["filename"]) as archive:
                    if (
                        relative in archive.namelist()
                        and archive.read(relative) == binary.read_bytes()
                    ):
                        matched.append(wheel["filename"])
        self.assertEqual(len(matched), 1)
        versions = {}
        for wheel in lock["wheels"]:
            name = wheel["package"]
            # Platform wheels can differ even in Python source line endings.
            # Compare source and binary against the same exact loaded artifact.
            if name == "pydantic-core" and wheel["filename"] != matched[0]:
                continue
            if name in versions:
                continue
            distribution = importlib.metadata.distribution(name)
            self.assertEqual(distribution.version, wheel["version"])
            site_packages = Path(distribution.locate_file("")).resolve()
            self.assertTrue(site_packages.is_relative_to(local), name)
            module = importlib.import_module(name.replace("-", "_"))
            path = Path(module.__file__).resolve()
            self.assertTrue(path.is_relative_to(site_packages), name)
            relative = path.relative_to(site_packages).as_posix()
            with zipfile.ZipFile(installed / "wheels" / wheel["filename"]) as archive:
                self.assertEqual(path.read_bytes(), archive.read(relative), name)
            versions[name] = distribution.version
        from pydantic import BaseModel

        class Record(BaseModel):
            count: int

        self.assertEqual(Record(count="7").count, 7)
        EVIDENCE.update(
            versions=versions,
            python=list(sys.version_info[:3]),
            native_wheel=matched[0],
            native_sha256=hashlib.sha256(binary.read_bytes()).hexdigest(),
            installed_dependency_sources_verified=True,
        )

    def adapter(self, respond, project=None, bearer=False):
        import httpx

        module = submodule("core.api.sdk_adapter")
        credentials = (
            module.Credentials(bearer_token="fixture-bearer")
            if bearer
            else module.Credentials("fixture-key", "fixture-secret")
        )
        return self.enterContext(
            module.SDKAdapter(
                credentials,
                online=lambda: bool(bpy.app.online_access),
                project_id=project,
                base_url="https://service.example.invalid/v1",
                transport=httpx.MockTransport(respond),
            )
        )

    def test_catalog_and_exact_estimate_use_bundled_sdk_and_real_permission(self):
        import httpx

        requests = []

        def respond(request):
            requests.append(request)
            if request.method == "GET":
                return httpx.Response(
                    200, json={"models": [{"id": "fixture-model", "future": True}]}
                )
            return httpx.Response(200, content=b'{"creativeUnitsCost":0.10000000000000001}')

        client = self.adapter(respond, project="fixture-project")
        module = submodule("core.api.sdk_adapter")
        with online_access(False), self.assertRaises(module.AdapterError):
            client.models()
        self.assertEqual(requests, [])
        with online_access(True):
            self.assertEqual(client.models(), [{"id": "fixture-model", "future": True}])
            quote = client.estimate_model(
                {
                    "id": "fixture-model",
                    "type": "custom",
                    "inputs": [{"name": "prompt", "type": "string", "required": True}],
                },
                {"prompt": "synthetic"},
            )
        self.assertEqual(quote.cost, Decimal("0.10000000000000001"))
        self.assertEqual(
            dict(requests[-1].url.params), {"dryRun": "true", "projectId": "fixture-project"}
        )
        self.assertEqual(json.loads(requests[-1].content), {"prompt": "synthetic"})
        self.assertTrue(client.owns_estimate(quote))

    def test_single_model_page_preserves_wrapper_and_scope_in_bundled_sdk(self):
        import httpx

        requests = []
        page = {
            "models": [{"id": "fixture-model", "future": True}],
            "nextPaginationToken": "opaque+/= cursor",
            "futurePage": 42,
        }

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json=page)

        client = self.adapter(respond, project="fixture-project")
        module = submodule("core.api.sdk_adapter")
        with online_access(False), self.assertRaises(module.AdapterError):
            client.model_page(page_size=5)
        self.assertEqual(requests, [])
        with online_access(True):
            self.assertEqual(client.model_page(page_size=5), page)
        self.assertEqual(len(requests), 1)
        self.assertEqual(
            dict(requests[0].url.params),
            {"privacy": "public", "pageSize": "5", "projectId": "fixture-project"},
        )

    def test_bearer_scope_overrides_ambient_sdk_auth_in_blender(self):
        import httpx

        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(200, json={"job": {"id": "fixture-job"}})

        with patch.dict(
            "os.environ",
            {
                "SCENARIO_SDK_API_KEY": "ambient-key",
                "SCENARIO_SDK_API_SECRET": "ambient-secret",
                "SCENARIO_CUSTOM_HEADERS": "Authorization: Bearer ambient\nHost: wrong.invalid",
                "SCENARIO_BASE_URL": "https://wrong.invalid",
            },
        ):
            client = self.adapter(respond, bearer=True)
            with online_access(True):
                client.job("fixture-job")
        self.assertEqual(requests[0].headers["Authorization"], "Bearer fixture-bearer")
        self.assertEqual(requests[0].headers["Host"], "service.example.invalid")
        self.assertNotIn("projectId", requests[0].url.params)

    def test_failed_estimate_is_single_attempt_and_sanitized(self):
        import httpx

        requests = []

        def respond(request):
            requests.append(request)
            return httpx.Response(
                503, json={"error": "fixture-secret"}, headers={"Retry-After": "0"}
            )

        client = self.adapter(respond)
        module = submodule("core.api.sdk_adapter")
        with online_access(True), self.assertRaises(module.AdapterError) as error:
            client.estimate_workflow({"id": "fixture-workflow", "inputs": []}, {})
        self.assertEqual(len(requests), 1)
        self.assertNotIn("fixture-secret", str(error.exception))
