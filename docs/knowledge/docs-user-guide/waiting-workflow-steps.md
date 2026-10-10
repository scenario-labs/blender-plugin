---
{
  "type": "Evidence",
  "id": "docs-user-guide.waiting-workflow-steps",
  "title": "Reviewing waiting workflow steps",
  "description": "A waiting workflow step is reviewed in Jobs or Studio Workflows and approved, selected or stopped once; a running step cannot be canceled.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Run a workflow paragraphs against the review controls and labels in saved_job_actions, the review dialog in workflow_steps (its contents, the explicit Stop workflow choice, the consequence text, single use and the refusal of a blocked selection), the 15 second refresh while a step waits, Refresh status after a restart, and the local MCP workflow_job_steps and decide_workflow_step tools, whose guidance asks the agent for the user's explicit choice; the server cannot verify that a person approved a decision. Unit tests cover the review controls, their labels and bindings, steps of another revision, the decision in flight and wrapped error rows, the running-workflow note and its absence while a step is projected. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses) cover the sidebar Jobs, Studio Jobs and Studio Workflows drawing with storage reads and owner creation refused, workflow names, the dialog contents, single use, selection bounds and listed order, long text candidates, the explicit stop with a blocked selection, a changed step, revision or connection, offline refusal, a refused decision shown again, review only after an explicit refresh following a restart, job-row redraws and registration. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. A live agent client was not exercised. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for review asset previews: the Run a workflow paragraph now describes Load previews (private copies of images up to 8 MiB and 4096 pixels per side, otherwise Scenario's thumbnail when offered, shown in Jobs, Workflows and the review), Retry previews, and that loading needs Online Access and never decides, spends or applies, instead of saying the review has no previews; checked against review_previews.py, result_previews.review_sources and the load operator, added as sources with the installed review preview tests. The decision claims are unchanged; only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes: the paragraph now says Retry previews tries the unavailable previews again, since a still Blender could not decode is checked and decoded again rather than fetched; checked against ReviewPreviews.request and the installed retry tests. The other claims are unchanged; only the fingerprints of review_previews.py and the installed review preview tests were refreshed. Re-reviewed on 2026-10-10 for step links: the workflow paragraph now says that Blender reads how the steps connect from the workflow, that a selection in a workflow with a loop can only be stopped when it cannot, and that an approval then warns that results may be missing; installed tests in tests/blender/test_workflow_steps.py and tests/blender/test_workflow_commands.py cover both. Re-reviewed on 2026-10-12 after the review dialog stopped drawing a selection range for an unsupported selection whose limits exceed its candidates; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-checked on 2026-10-12 after restacking the review previews on that fix: the two changes to scenario/blender/workflow_steps.py are independent, both claims hold, and its fingerprint now covers both.",
    "sources": {
      "scenario/blender/workflow_steps.py": "99b00e703c3c9c599cc9c19edf8bcde1eeaa98e52b8bdc441e28bd7576dea57a",
      "scenario/core/ui/saved_job_actions.py": "b22a28c37971c21776313bdef903af8ee9d24e627774ffd4d14c48ef59e8ab4b",
      "scenario/blender/job_recovery.py": "425f54316c84067f910f15a1873a7d5175a372e4cf357bca517966cdcc6a5d8e",
      "scenario/blender/model_jobs.py": "a495102b2780ac37e4260493cea3cfbd8bd0c7130fde4954ae301e511ab701e0",
      "scenario/blender/workflow_controls.py": "4de1c7929e512739c96b15f6229f708fd9153fd358f24e9a383647d3117ef8ee",
      "scenario/core/jobs/workflow_nodes.py": "ed3b7769ac9ad2195bc5a32febf00b1abbd5df027d059a3e9c45918aa0f6ec7a",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "scenario/mcp/protocol.py": "ee30be5866bbee06918c1145e7e770e90275a4c059c5610d83e6c768a719df7a",
      "tests/blender/test_workflow_steps.py": "ec9171401f6b91c9445116df275a3db82a05554e74ab75e61d7010279382e5ae",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379",
      "scenario/blender/review_previews.py": "65a68e371515d154f6be66e4fc49bbfe9bb075bbeebdeb987db83a40abd9f504",
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "tests/blender/test_workflow_review_previews.py": "d4c46ed53bf965383091a63da3f94caa41036b8dad377296bd2dd406e3ab7a67"
    }
  }
}
---

# Reviewing waiting workflow steps

Evidence for [the canonical document](../../USER_GUIDE.md).
