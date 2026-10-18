# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""What every request to the telemetry relay shares: its address, the context and one POST.

The relay on blender.scenario.com holds the analytics token and accepts only the shapes
its allowlist names; this module mirrors the context part of that allowlist, so nothing is
sent that the relay would drop. The relay is a first-party protocol of its own, not a
Scenario API operation, so it uses the standard library rather than the SDK adapter.
"""

import json
import platform
import re
import ssl
import urllib.request

import certifi

from ..api.user_agent import user_agent_string

BASE_URL = "https://blender.scenario.com/telemetry/v1"
TIMEOUT = 5.0
MAX_BODY = 64 * 1024  # the relay refuses larger bodies with 413
VERSION = re.compile(r"[0-9]+\.[0-9]+\.[0-9]+")
_SYSTEMS = {"Darwin": "macos", "Windows": "windows", "Linux": "linux"}
_MACHINES = {"arm64": "arm64", "aarch64": "arm64", "x86_64": "x64", "amd64": "x64", "x64": "x64"}


def sanitize_context(value):
    """The context fields the relay accepts; an invalid or unknown field is left out."""
    if not isinstance(value, dict):
        return {}
    context = {}
    for key in ("extension_version", "blender_version"):
        version = value.get(key)
        if isinstance(version, str) and VERSION.fullmatch(version):
            context[key] = version
    if value.get("os") in ("macos", "windows", "linux", "other"):
        context["os"] = value["os"]
    if value.get("arch") in ("arm64", "x64", "other"):
        context["arch"] = value["arch"]
    return context


def context(extension_version, blender_version, *, system=None, machine=None):
    """Versions, operating system and processor family; nothing that identifies the machine."""
    system = platform.system() if system is None else system
    machine = platform.machine() if machine is None else machine
    return sanitize_context(
        {
            "extension_version": extension_version,
            "blender_version": blender_version,
            "os": _SYSTEMS.get(system, "other"),
            "arch": _MACHINES.get(str(machine).lower(), "other"),
        }
    )


def post_json(url, payload, timeout=TIMEOUT, *, opener=None):
    """POST one JSON body and return the HTTP status; a refusal or failure raises.

    No retry: urllib raises HTTPError for a 4xx or 5xx reply, and URLError or another
    OSError when the relay cannot be reached. Callers decide what a failure means. TLS
    verifies against the bundled certifi roots, as result transfers do: Blender's own
    Python may not find the system's certificates.
    """
    body = json.dumps(payload, separators=(",", ":")).encode("utf-8")
    if len(body) > MAX_BODY:
        raise ValueError("telemetry body exceeds the relay's limit")
    request = urllib.request.Request(
        url,
        data=body,
        method="POST",
        headers={"Content-Type": "application/json", "User-Agent": user_agent_string()},
    )
    context = ssl.SSLContext(ssl.PROTOCOL_TLS_CLIENT)
    context.load_verify_locations(cafile=certifi.where())
    with (opener or urllib.request.urlopen)(request, timeout=timeout, context=context) as response:
        return response.status
