# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit live-tool configuration. uv owns dotenv loading; never log values."""

import os
from dataclasses import dataclass, field

from scenario.core.config import Credentials


@dataclass(frozen=True)
class LiveSettings:
    credentials: Credentials = field(repr=False)
    project_id: str | None = field(default=None, repr=False)


def live_settings(environ=None):
    environ = os.environ if environ is None else environ
    credentials = Credentials(
        (environ.get("SCENARIO_TEST_API_KEY") or "").strip(),
        (environ.get("SCENARIO_TEST_API_SECRET") or "").strip(),
    )
    if not credentials.valid:
        raise SystemExit(
            "no test credentials: export SCENARIO_TEST_API_KEY and SCENARIO_TEST_API_SECRET, "
            "or copy .env.example to .env.local and run with uv run --locked --env-file .env.local"
        )
    project_id = (environ.get("SCENARIO_TEST_PROJECT_ID") or "").strip() or None
    return LiveSettings(credentials, project_id)
