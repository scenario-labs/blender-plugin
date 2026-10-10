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
    "limits": "Reviewed the Waiting workflow steps section, the Explicit Studio view and Workflow controls sentences that now point to it, against saved_job_actions.describe (review controls only for the view's saved revision, the unidentified-step row, the decision in flight, wrapped decision errors and the running-workflow note), job_recovery.result_actions and workflow_steps (step_view and waiting_step in ModelJobs, the review operator's poll, invoke, draw and execute, draw_pending and workflow_name), the Generate confirmation text, the pump's job-row comparison and registration. Drawing reads memory and scene forms only; invoke fills operator properties; execute sends through runtime.decide_workflow_step. Unit tests cover the review controls, their labels and bindings, steps of another revision, the decision in flight and wrapped error rows, the running-workflow note and its absence while a step is projected. Installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2, synthetic SDK responses) cover the sidebar Jobs, Studio Jobs and Studio Workflows drawing with storage reads and owner creation refused, workflow names, the dialog contents, single use, selection bounds and listed order, long text candidates, the explicit stop with a blocked selection, a changed step, revision or connection, offline refusal, a refused decision shown again, review only after an explicit refresh following a restart, job-row redraws and registration. No screenshot or physical desktop input, focus, DPI or IME evidence of the review rows or dialog was collected; it is pending for an unlocked desktop session. No live or paid request was made: the service's handling of repeated or concurrent decisions, rejection inside a ForEach iteration, omitting projectId for API-key decisions and the charge after an approval or selection are not live-verified. Previews of review assets are not implemented. The earlier review of the status row (2026-10-10) is superseded by this section.",
    "sources": {
      "scenario/blender/workflow_steps.py": "82c868fd18b362c83c494b72445165f8b1144218c33261ea32d4fe933f397f71",
      "scenario/core/ui/saved_job_actions.py": "b22a28c37971c21776313bdef903af8ee9d24e627774ffd4d14c48ef59e8ab4b",
      "scenario/blender/job_recovery.py": "52bfd17d29a253267467c589a67f59449220038754808de77d596186aed36dc5",
      "scenario/blender/model_jobs.py": "5588e3c4ad43bdd8eba1239fa5b7134217dd2f68900b4c038e7d6b4766906cc2",
      "scenario/blender/workflow_controls.py": "4de1c7929e512739c96b15f6229f708fd9153fd358f24e9a383647d3117ef8ee",
      "scenario/blender/pump.py": "0bf7a25ec4cf67ea8f6b919cc955bb6fbfb0134e44088ac7d8eb5aed61a5cb7e",
      "scenario/blender/registry.py": "effd72a4ab072e9eafbe74112cafe270aafcd3f8f89e3fee370ef6a143377009",
      "scenario/blender/runtime.py": "bd150ee52a66ca16520617cd1c1d67336862c165db3a8c62ca7b2861c9e37148",
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/core/jobs/workflow_nodes.py": "24a72b8fdeffe9ff9540d5fd57fff10ece53559bbc5ab571880c00298f537a51",
      "tests/unit/test_saved_job_actions.py": "ac7679b2665509d333855b3c7f26bed297c856a26391a200aa800444f9f16379",
      "tests/blender/test_workflow_steps.py": "530ba44c89c0ac09aaa415f6bec0e34ec5b12aba6e61d1525a3000a990fd8e77",
      "tests/blender/test_workflow_commands.py": "928f4e45ae6c7d3e44e87dda2c7914f6f6ff3a26a85ab707e7ee3d91c68e898e",
      "tests/blender/test_workflow_controls.py": "afc505d09463a3566164253e59b3c4b13739af20076556d3160af93a21e361da"
    }
  }
}
---

# Native review of waiting workflow steps

Evidence for [the canonical document](../../UI_STYLE.md).
