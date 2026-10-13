---
{
  "type": "Evidence",
  "id": "docs-known-limitations.waiting-workflow-steps",
  "title": "Waiting workflow step limits",
  "description": "Rejecting a waiting step is the only workflow stop; nested steps, loop-fed selections, previews and live behavior remain limited.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that ModelJobs.control refuses cancel on a running workflow job with WorkflowCancelUnavailable and that rejection through ModelJobs.decide is the only stop; that pending_steps reads top-level flow nodes only; that a selection feeding a ForEach loop, a nested workflow or an unlisted node type is blocked to reject only; that steps carry asset IDs or text until Load previews fetches previews, images above 8 MiB or 4096 pixels per side and other kinds being previewed only through a server thumbnail, with no MCP preview; and that the native dialog draws at most 12 wrapped lines per text candidate. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for review asset previews: the entry now says review assets and candidates are IDs or text until Load previews fetches private previews, that a PNG, JPEG or WebP asset over 8 MiB or 4096 pixels per side, or another kind of asset, is previewed only through a server thumbnail Scenario offers, that MCP returns no preview, and that the review assets and preview sources of real flows and desktop evidence of the previews are unverified; checked against review_sources, review_previews.py and their tests, added as sources. Only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes (temporary-data decoding and lost-cache retries): the entry's preview sources, thumbnail fallback, MCP and desktop limitations are unchanged; only the fingerprints of review_previews.py and the review preview tests were refreshed. Re-reviewed on 2026-10-10 for step links: the entry now says that any selection in a workflow with a loop can only be rejected when the links between its steps cannot be read from the job or the workflow definition, and that an approval then warns about incomplete review assets; the parser, MCP and installed tests listed here cover it. Re-reviewed on 2026-10-12 after the review dialog stopped drawing a selection range for an unsupported selection whose limits exceed its candidates; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-checked on 2026-10-12 after restacking the review previews on that fix: the two changes to scenario/blender/workflow_steps.py are independent, both claims hold, and its fingerprint now covers both. The paid desktop pass on main 2e89cae8 at UI scale 1.0 ran one private test workflow with a selection and three approvals: previews loaded, 2 of 3 candidates were chosen, an approval was sent, a decision from a dialog after its step was decided elsewhere was refused with 'The workflow step changed; review it again', and Stop workflow canceled the job with only the step that had run charged. Concurrent decisions, omitted project IDs, rejection inside a loop, other node types and UI scale 2.0 remain unverified. Evidence added on 2026-10-13 from a private report, without spend amounts, account details, job identities, private paths or screenshots; the implementation sources were not re-reviewed and the review date is unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "a495102b2780ac37e4260493cea3cfbd8bd0c7130fde4954ae301e511ab701e0",
      "scenario/blender/workflow_steps.py": "99b00e703c3c9c599cc9c19edf8bcde1eeaa98e52b8bdc441e28bd7576dea57a",
      "scenario/core/jobs/workflow_nodes.py": "ed3b7769ac9ad2195bc5a32febf00b1abbd5df027d059a3e9c45918aa0f6ec7a",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "tests/unit/test_workflow_nodes.py": "6556b51d3750e58c0be73596829e52f4ca448121504cab0c3900831ab1c1aacd",
      "tests/blender/test_workflow_steps.py": "ec9171401f6b91c9445116df275a3db82a05554e74ab75e61d7010279382e5ae",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "scenario/blender/review_previews.py": "65a68e371515d154f6be66e4fc49bbfe9bb075bbeebdeb987db83a40abd9f504",
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "tests/unit/test_workflow_review_previews.py": "41040fae354b6f8584513af9e9e2e029e6a746d97644452fce548634dccbc308",
      "tests/blender/test_workflow_review_previews.py": "d4c46ed53bf965383091a63da3f94caa41036b8dad377296bd2dd406e3ab7a67",
      "tests/unit/test_workflow_step_links.py": "3dbf4b8351072c6be1ada09a7a92e11ba0a273e3c307b339a274f3779af8ef61"
    }
  }
}
---

# Waiting workflow step limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
