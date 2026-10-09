# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Named compatibility methods for gaps in the selected official SDK.

Internal to SDKAdapter: reuse its configured client, never own a second
transport. The adapter supplies permission/lifetime checks, parsing and safe
errors. Add only verified operations with an upstream issue and wire tests.
"""

from urllib.parse import quote

# RFC 3986 pchar: the same path-segment encoding as the generated SDK methods.
_PATH_SEGMENT_SAFE = "!$&'()*+,;=:@"


class SDKResourceExtensions:
    """Temporary resources absent from scenario-sdk 2.2.0.

    Each method names its upstream issue. Replace a call when a selected SDK
    release has an equivalent generated method that passes the same request,
    scope, authentication and retry contracts.
    """

    def __init__(self, sdk):
        self._sdk = sdk

    def teams(self):
        """https://github.com/scenario-labs/scenario-sdk-python/issues/29"""
        import httpx

        # Discovery must not inherit projectId/teamId: a stale project can
        # prevent the caller from discovering accessible teams.
        return self._sdk.get("/teams", cast_to=httpx.Response, options={"params": {}})

    def projects(self, team_id):
        """https://github.com/scenario-labs/scenario-sdk-python/issues/29"""
        import httpx

        # projectId can make the authorizer derive a different team. Only the
        # explicit team belongs in this query, even on a project-bound adapter.
        return self._sdk.get(
            "/projects", cast_to=httpx.Response, options={"params": {"teamId": team_id}}
        )

    def workflow_user_selection(self, workflow_id, *, body, project_id=None):
        """Answer one waiting user-selection step with a single PUT.

        https://github.com/scenario-labs/scenario-sdk-python/issues/33
        The API reference documents this route; SDK 2.2.0 has no generated
        method. Remove this fallback once the pinned SDK provides
        workflows.user_selection and it passes the decision contracts.
        """
        import httpx

        if not isinstance(workflow_id, str) or not workflow_id:
            raise ValueError("A workflow identifier is required")
        # A decision can resume paid steps or stop the workflow: never replay it,
        # whatever retry policy the client was given.
        return self._sdk.put(
            f"/workflows/{quote(workflow_id, safe=_PATH_SEGMENT_SAFE)}/user-selection",
            cast_to=httpx.Response,
            body=body,
            options={
                "params": {} if project_id is None else {"projectId": project_id},
                "max_retries": 0,
            },
        )
