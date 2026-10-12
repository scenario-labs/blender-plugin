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
    "limits": "Reviewed the Run a workflow paragraphs against the review controls and labels in saved_job_actions, the review dialog in workflow_steps (its contents, the explicit Stop workflow choice, the consequence text, single use and the refusal of a blocked selection), the 15 second refresh while a step waits, Refresh status after a restart, and the local MCP workflow_job_steps and decide_workflow_step tools, whose guidance asks the agent for the user's explicit choice; the server cannot verify that a person approved a decision. Unit tests cover the review controls, their labels and bindings, steps of another revision, the decision in flight and wrapped error rows, the running-workflow note and its absence while a step is projected. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses) cover the sidebar Jobs, Studio Jobs and Studio Workflows drawing with storage reads and owner creation refused, workflow names, the dialog contents, single use, selection bounds and listed order, long text candidates, the explicit stop with a blocked selection, a changed step, revision or connection, offline refusal, a refused decision shown again, review only after an explicit refresh following a restart, job-row redraws and registration. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. A live agent client was not exercised. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Re-reviewed on 2026-10-10 after the review dialog's decision cells became an even split and its minimum width 540; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for step links: the workflow paragraph now says that Blender reads how the steps connect from the workflow, that a selection in a workflow with a loop can only be stopped when it cannot, and that an approval then warns that results may be missing; installed tests in tests/blender/test_workflow_steps.py and tests/blender/test_workflow_commands.py cover both. Re-reviewed on 2026-10-12 after the review dialog stopped drawing a selection range for an unsupported selection whose limits exceed its candidates; the claims here are unchanged, and only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed.",
    "sources": {
      "scenario/blender/workflow_steps.py": "0382c01baa77f46142a93b9624a228f27e9f3f5bc082f387897a7fd8b9bf2f68",
      "scenario/core/ui/saved_job_actions.py": "b22a28c37971c21776313bdef903af8ee9d24e627774ffd4d14c48ef59e8ab4b",
      "scenario/blender/job_recovery.py": "52bfd17d29a253267467c589a67f59449220038754808de77d596186aed36dc5",
      "scenario/blender/model_jobs.py": "73a4be3cee977332eae60bc44a51a99923d4305cab49fdaeb637d042c8b14b27",
      "scenario/blender/workflow_controls.py": "4de1c7929e512739c96b15f6229f708fd9153fd358f24e9a383647d3117ef8ee",
      "scenario/core/jobs/workflow_nodes.py": "81a15c7f5bc51c74dd94d8abe1f5e1d44d9db12fdea35d79fb2c967f3e65f261",
      "scenario/mcp/tools_scenario.py": "4d6426a08cbef8d9ac3c62392002eaa33367b2c1c6313dbd6d777136631522ef",
      "scenario/mcp/protocol.py": "ee30be5866bbee06918c1145e7e770e90275a4c059c5610d83e6c768a719df7a",
      "tests/blender/test_workflow_steps.py": "ec9171401f6b91c9445116df275a3db82a05554e74ab75e61d7010279382e5ae",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379"
    }
  }
}
---

# Reviewing waiting workflow steps

Evidence for [the canonical document](../../USER_GUIDE.md).
