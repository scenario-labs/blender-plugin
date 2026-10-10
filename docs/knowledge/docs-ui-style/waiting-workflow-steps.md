---
{
  "type": "Evidence",
  "id": "docs-ui-style.waiting-workflow-steps",
  "title": "Native review of waiting workflow steps",
  "description": "Jobs rows and the Studio Workflows page draw one review control per waiting step, and a single-use dialog sends one decision or Stop workflow through the shared entry.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Waiting workflow steps section, the Explicit Studio view and Workflow controls sentences that now point to it, against saved_job_actions.describe (review controls only for the view's saved revision, the unidentified-step row, the decision in flight, wrapped decision errors and the running-workflow note), job_recovery.result_actions and workflow_steps (step_view and waiting_step in ModelJobs, the review operator's poll, invoke, draw and execute, draw_pending and workflow_name), the Generate confirmation text, the pump's job-row comparison and registration. Drawing reads memory and scene forms only; invoke fills operator properties; execute sends through runtime.decide_workflow_step. Unit tests cover the review controls, their labels and bindings, steps of another revision, the decision in flight and wrapped error rows, the running-workflow note and its absence while a step is projected. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses) cover the sidebar Jobs, Studio Jobs and Studio Workflows drawing with storage reads and owner creation refused, workflow names, the dialog contents, single use, selection bounds and listed order, long text candidates, the explicit stop with a blocked selection, a changed step, revision or connection, offline refusal, a refused decision shown again, review only after an explicit refresh following a restart, job-row redraws and registration. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Previews of review assets are not implemented. The earlier review of the status row (2026-10-10) is superseded by this section. Re-reviewed on 2026-10-10 after the review dialog's decision became one segmented control of two equal cells (an even split; the Select cell alone may be disabled) and its minimum width became 540, the Generate workflow confirmation's width for the same 70-character wrapping; the section now links the decision to the segmented-choice rule, and an installed test asserts the even split and the width; only the fingerprints of scenario/blender/workflow_steps.py and tests/blender/test_workflow_steps.py were refreshed. Re-reviewed on 2026-10-10 for step links: the dialog draws BLOCKED unverified for a selection whose links could not be read in a workflow with a loop, with Select disabled, and workflow_steps._draw_approval adds the UNLINKED warning above the result list when links_complete is false. Installed tests cover an unverified live-shaped selection offering only Stop workflow, the approval warning without a readable definition and the results a definition links without the warning. No screenshot or physical desktop evidence of the warning was collected.",
    "sources": {
      "scenario/blender/workflow_steps.py": "2184f484dcfa32b373aa5bd28e1f1fdb9d5452d4e1aaefd74cbae14073d311a1",
      "scenario/core/ui/saved_job_actions.py": "b22a28c37971c21776313bdef903af8ee9d24e627774ffd4d14c48ef59e8ab4b",
      "scenario/blender/job_recovery.py": "52bfd17d29a253267467c589a67f59449220038754808de77d596186aed36dc5",
      "scenario/blender/model_jobs.py": "73a4be3cee977332eae60bc44a51a99923d4305cab49fdaeb637d042c8b14b27",
      "scenario/blender/workflow_controls.py": "4de1c7929e512739c96b15f6229f708fd9153fd358f24e9a383647d3117ef8ee",
      "scenario/blender/pump.py": "0bf7a25ec4cf67ea8f6b919cc955bb6fbfb0134e44088ac7d8eb5aed61a5cb7e",
      "scenario/blender/registry.py": "effd72a4ab072e9eafbe74112cafe270aafcd3f8f89e3fee370ef6a143377009",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/jobs/workflow_nodes.py": "81a15c7f5bc51c74dd94d8abe1f5e1d44d9db12fdea35d79fb2c967f3e65f261",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379",
      "tests/blender/test_workflow_steps.py": "98302e99e25f675fc7bab8564be2fc06d431664d70105fd04b250fcf9b07a30f",
      "tests/blender/test_workflow_commands.py": "447c9446dc4791b4b27567e18d922a42d5f80db52b32ae8dc2fd8f7b75f1cbda",
      "tests/blender/test_workflow_controls.py": "afc505d09463a3566164253e59b3c4b13739af20076556d3160af93a21e361da"
    }
  }
}
---

# Native review of waiting workflow steps

Evidence for [the canonical document](../../UI_STYLE.md).
