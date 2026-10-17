# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Make the repo root importable so `import scenario.core...` works without Blender."""

import pathlib
import socket
import sys

import pytest

ROOT = pathlib.Path(__file__).resolve().parents[2]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

FIXTURES = ROOT / "tests" / "fixtures"

_LOOPBACK = {"127.0.0.1", "::1", "localhost"}
_REAL_CONNECT = socket.socket.connect
_REAL_CONNECT_EX = socket.socket.connect_ex


def _guarded_connect(real):
    def connect(self, address, *args, **kwargs):
        if self.family == getattr(socket, "AF_UNIX", None):
            return real(self, address, *args, **kwargs)
        host = str(address[0]) if isinstance(address, tuple) and address else str(address)
        if host not in _LOOPBACK:
            raise RuntimeError(
                f"network access is not allowed in unit tests (tried {address!r}); "
                "use @pytest.mark.allow_network only for an explicit network test"
            )
        return real(self, address, *args, **kwargs)

    return connect


@pytest.fixture(autouse=True)
def _no_network(request, monkeypatch):
    """Catch accidental service connections while keeping local MCP tests usable."""
    if request.node.get_closest_marker("allow_network"):
        return
    monkeypatch.setattr(socket.socket, "connect", _guarded_connect(_REAL_CONNECT))
    monkeypatch.setattr(socket.socket, "connect_ex", _guarded_connect(_REAL_CONNECT_EX))


@pytest.fixture(autouse=True)
def _instant_sdk_retries(monkeypatch):
    """Skip the SDK's retry waits; the attempts and their order are unchanged.

    SDKAdapter retries allow-listed reads with the SDK's own backoff, which
    would otherwise sleep for real in every test that fails such a read.
    Tests that check the waits record them with their own fixture.
    """
    import time

    try:
        import scenario_sdk._base_client as base
    except ImportError:
        return
    monkeypatch.setattr(base, "time", _SleeplessTime(time))


class _SleeplessTime:
    def __init__(self, module):
        self._module = module

    def sleep(self, seconds):
        pass

    def __getattr__(self, name):
        return getattr(self._module, name)
