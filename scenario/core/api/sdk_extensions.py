# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named compatibility methods for gaps in the selected official SDK.

Internal to SDKAdapter: reuse its configured client, never own a second
transport. The adapter supplies permission/lifetime checks, parsing and safe
errors. Add only verified operations with an upstream issue and wire tests.
"""


class SDKResourceExtensions:
    """Temporary resources the selected scenario-sdk cannot serve yet.

    SDK 2.5.0 generates every operation the adapter uses, so none is needed.
    Each method added here names its upstream issue. Replace a call when a
    selected SDK release has an equivalent generated method that passes the
    same request, scope, authentication and retry contracts.
    """

    def __init__(self, sdk):
        self._sdk = sdk
