---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-job-action-descriptors",
  "title": "Shared saved-job action descriptors",
  "description": "One bpy-free descriptor source for native saved-job controls.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-job-action-descriptors",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "c70c7d1bdba93cf29ce5488fa7d83e92f24596b2",
    "limits": "Reviewed the bpy-free saved_job_actions.describe descriptor builder, its use by job_recovery.result_actions/draw_controls, the extracted panels.draw_active_job, and Studio Jobs/Results reuse of those panels. Offline unit tests cover golden labels, icons, operators, properties, numbering, Blockout review phases, reuse and review rows, unique keys, rejection of unknown actions, no Blender imports, and the MCP recover_local_job action enum, job_status action mapping and prepare_result_application purposes. A temporary offline harness compared the previous draw_controls with the descriptor path over 189,123 synthetic combinations with no difference; it is not committed and was not rerun after rebasing onto main, where the previous code and the descriptors read the same World media type set. Installed native tests on macOS arm64 Blender 5.1.2 validate every descriptor property against the registered operator RNA, ordered drawing, read-only drawing of real saved prepared and remote jobs whose action names equal MCP job_status actions, and Studio pages drawing the sidebar views. The only intended difference concerns a shared view that has actions or a ready state but no saved revision, which projection never produces because it sets the revision, state and actions together: the previous code drew the rows that need no revision (status rows and, for a ready Blockout review, Use saved Blockout plan) and raised KeyError at the first offered control that needed the revision, and the descriptor path draws nothing; unit and installed drawing tests cover it. A newly prepared view without a revision has no actions or saved state and draws nothing in both. World candidates use panorama.WORLD_MEDIA_TYPES (PNG, JPEG and OpenEXR types), the set that ModelJobs.actions and World approval also read; the World confirmation dialog and its media label stay in the apply_saved_world operator. Operators recheck their context token and saved revision or Blockout review; refresh, resume, download check and receipt retry run without a dialog. No collapsible draw_result variant, composer strip, new action, desktop interaction, screenshot, Blender 5.0/5.2 run or live acceptance is claimed. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: saved_job_actions adds MCP_ONLY (use_first_frame), which native descriptors skip and the reuse row ignores; other unknown actions still fail; its unit tests add the MCP_ONLY case; existing cases are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/panels.py": "ffff10ed5d252fca10c6da56156b5e364e0300cbdf88914120d7274d268402f8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_jobs.py": "db89e83391d2d572e6c4b496cdd12aae7d1865d08e2ec4b66d406221716e5430",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "scenario/mcp/tools_scenario.py": "8613fe347b43421261f0462fe3972e777fffb6f35f17f9cd4a26d8b321d25331",
      "tests/unit/test_saved_job_actions.py": "6fec69e9f92ef092c7dcff4e7bb131e889c8f716c19abb726156de71f4d6b4aa",
      "tests/blender/test_result_actions.py": "a0a8de36ed944f1d934c21cd595f773640ea5357f8afa50a7fac9d8e79e8f913",
      "tests/blender/test_studio_view.py": "e6f0fdbdc8aa81bb51880ba4a01da299f54d106babb4e1380216f9d575aed5f7",
      "tests/blender/test_blockout_jobs.py": "fd189d4cb712d98acb24e944857088378d327cb59455d858d4cdf64fce41e37e"
    }
  }
}
---

# Shared saved-job action descriptors

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
