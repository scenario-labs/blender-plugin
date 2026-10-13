# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A ScenarioError message names an HTTP status only when the failure has one."""

import pytest

from scenario.core.api.errors import NetworkError, ScenarioError


@pytest.mark.parametrize(
    ("error", "text"),
    [
        (ScenarioError(0, "Loading the model description"), "Loading the model description"),
        (ScenarioError("0", "The estimate context changed"), "The estimate context changed"),
        (NetworkError(0, "Could not reach Scenario"), "Could not reach Scenario"),
        (ScenarioError(0, "Unavailable", trace_id="trace-1"), "Unavailable (trace trace-1)"),
        (ScenarioError(404, "Model not found"), "404 Model not found"),
        (ScenarioError(503, "Unavailable", trace_id="trace-1"), "503 Unavailable (trace trace-1)"),
    ],
    ids=lambda value: value if isinstance(value, str) else type(value).__name__,
)
def test_message_has_a_status_prefix_only_for_an_http_status(error, text):
    assert str(error) == text
    assert error.reason == text.removeprefix(f"{error.status} ").split(" (trace ")[0]


def test_status_zero_keeps_its_attributes():
    error = ScenarioError(0, "Could not reach Scenario", trace_id="trace-1", path="/v1/models")
    assert error.status == 0 and not error.is_auth
    assert (error.reason, error.trace_id, error.path) == (
        "Could not reach Scenario",
        "trace-1",
        "/v1/models",
    )
