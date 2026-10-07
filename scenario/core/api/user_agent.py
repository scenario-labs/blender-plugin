# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""One package-version identity for API and storage requests."""


def user_agent_string():
    """The one User-Agent the extension sends: ScenarioBlender/<version>.

    Imported lazily so that scenario/__init__.py stays free of module-level
    imports and scenario.core keeps importing without bpy.
    """
    from ... import __version__

    return f"ScenarioBlender/{__version__}"
