# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Typed errors raised by the Scenario REST client."""


class ScenarioError(Exception):
    """An HTTP-level or API-level failure. `status` is 0 when there is no HTTP status.

    Network failures and the extension's own refusals use status 0. The message
    names the status before the reason only when there is one, so clients and
    logs never see a bare "0" prefix.
    """

    def __init__(self, status, reason, *, trace_id=None, body=None, path=None):
        self.status = int(status)
        self.reason = str(reason)
        self.trace_id = trace_id
        self.body = body
        self.path = path
        prefix = f"{self.status} " if self.status else ""
        suffix = f" (trace {trace_id})" if trace_id else ""
        super().__init__(f"{prefix}{self.reason}{suffix}")

    @property
    def is_auth(self):
        return self.status in (401, 403)


class NetworkError(ScenarioError):
    """DNS, TLS, timeout or connection failure. Retried by the client."""
