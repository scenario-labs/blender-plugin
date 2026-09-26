# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named compatibility methods for gaps in the selected official SDK.

Internal to SDKAdapter: reuse its configured client, never own a second
transport. The adapter supplies permission/lifetime checks, parsing and safe
errors. Add only verified operations with an upstream issue and wire tests.
"""


class SDKResourceExtensions:
    """Temporary resources absent from scenario-sdk 2.1.0.

    https://github.com/scenario-labs/scenario-sdk-python/issues/29
    Replace these calls when a selected SDK release has equivalent generated
    methods and passes the discovery query/authentication contracts.
    """

    def __init__(self, sdk):
        self._sdk = sdk

    def teams(self):
        import httpx

        # Discovery must not inherit projectId/teamId: a stale project can
        # prevent the caller from discovering accessible teams.
        return self._sdk.get("/teams", cast_to=httpx.Response, options={"params": {}})

    def projects(self, team_id):
        import httpx

        # projectId can make the authorizer derive a different team. Only the
        # explicit team belongs in this query, even on a project-bound adapter.
        return self._sdk.get(
            "/projects", cast_to=httpx.Response, options={"params": {"teamId": team_id}}
        )
