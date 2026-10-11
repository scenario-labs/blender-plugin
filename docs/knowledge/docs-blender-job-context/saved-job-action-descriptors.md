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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed the bpy-free saved_job_actions.describe descriptor builder, its use by job_recovery.result_actions/draw_controls, the extracted panels.draw_active_job, and Studio Jobs/Results reuse of those panels. Offline unit tests cover golden labels, icons, operators, properties, numbering, Blockout review phases, reuse and review rows, unique keys, rejection of unknown actions, no Blender imports, and the MCP recover_local_job action enum, job_status action mapping and prepare_result_application purposes. A temporary offline harness compared the previous draw_controls with the descriptor path over 189,123 synthetic combinations with no difference; it is not committed and was not rerun after rebasing onto main, where the previous code and the descriptors read the same World media type set. Installed native tests on macOS arm64 Blender 5.1.2 validate every descriptor property against the registered operator RNA, ordered drawing, read-only drawing of real saved prepared and remote jobs whose action names equal MCP job_status actions, and Studio pages drawing the sidebar views. The only intended difference concerns a shared view that has actions or a ready state but no saved revision, which projection never produces because it sets the revision, state and actions together: the previous code drew the rows that need no revision (status rows and, for a ready Blockout review, Use saved Blockout plan) and raised KeyError at the first offered control that needed the revision, and the descriptor path draws nothing; unit and installed drawing tests cover it. A newly prepared view without a revision has no actions or saved state and draws nothing in both. World candidates use panorama.WORLD_MEDIA_TYPES (PNG, JPEG and OpenEXR types), the set that ModelJobs.actions and World approval also read; the World confirmation dialog and its media label stay in the apply_saved_world operator. Operators recheck their context token and saved revision or Blockout review; refresh, resume, download check and receipt retry run without a dialog. No collapsible draw_result variant, composer strip, new action, desktop interaction, screenshot, Blender 5.0/5.2 run or live acceptance is claimed. Re-checked on main after #370: ModelJobs.actions lists cancel for a remote model record only while its latest owned refresh or cancel retrieval confirmed an inference job with the same remote ID, so a freshly inspected saved remote job draws Refresh status and Resume download without Cancel generation, and its descriptor action names still equal MCP job_status actions. The installed expectation was corrected to that behavior and test_result_actions now runs in the PR baseline; the offer after a confirming refresh belongs to the inference-cancellation topic, not to this read-only drawing test. Later drift in panels.py (derived history row kind), studio.py and test_studio_view.py (Film review page) and tools_scenario.py (other tools; the job_status action mapping and recover_local_job enum are unchanged) does not alter these descriptor claims. Installed Blender 5.1.2 macOS arm64 baseline and full suites passed with the correction. Scoped 2026-10-11 check of the native first-frame control, not a full re-review: saved_job_actions no longer has MCP_ONLY and describes use_first_frame as one scenario.use_saved_first_frame control per asset ID that ModelJobs projects in first_frame_assets, numbered over every saved asset, with no operator icon like the other controls; job_recovery registers that operator; the unit vocabulary, MCP purpose parity and installed registered-property tests include it. Other descriptors, their order and the read-only drawing are unchanged. In the current model_jobs.py, re-checked 2026-10-11 after restacking on main 7fb15252, ModelJobs.poll still sets the saved revision, state and actions together (now with world_assets and first_frame_assets). The World media type claim above is superseded by the merged World candidate change: ModelJobs.actions and World approval now read panorama.world_candidate, which excludes material maps, and saved_job_actions numbers the projected world_assets over every saved asset; this scoped check does not re-review that change. The other claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "e9f143bc0b13abd87595a526d4d1702506e229c4c209987932586103c70867bc",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/panels.py": "c47a4301db4e2383c240dc2bde3dc86fd1d7a910a43c2da4a02dad235e0539b3",
      "scenario/blender/studio.py": "7a4a6b694ba4becb7a51dac11f95838a35d9f2a3dc752d85a50e1b1cd0f1f071",
      "scenario/blender/model_jobs.py": "553e74a31bfdef53e93216e48b650d23d8c6bf2da99a1431e63d4722c956d49c",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "scenario/mcp/tools_scenario.py": "e85b856e5a82acc83e8cf9096af20fbc180d7729e5db3d16e589a940559f60e4",
      "tests/unit/test_saved_job_actions.py": "6fec69e9f92ef092c7dcff4e7bb131e889c8f716c19abb726156de71f4d6b4aa",
      "tests/blender/test_result_actions.py": "f9ef9207e0052aba850d165dfdefc05a09b2894fd59e8cb4d5c0e8172a65c1ad",
      "tests/blender/test_runtime_jobs.py": "9cbc0a763541264ae1c3f291a7754c09755066f60dc11f03206ba1fe8f398cf3",
      "tests/blender/test_studio_view.py": "d65762fbbcf6ce9dd63356097697c30b9b22a8fb07bec0866c3ae64e79ad8c7c",
      "tests/blender/test_blockout_jobs.py": "fd189d4cb712d98acb24e944857088378d327cb59455d858d4cdf64fce41e37e",
      "tests/blender/run_all.py": "5fa3f8c12ade901f48a21021eba62e61cb80f8e2edac569f67c4f1c54960f195"
    }
  }
}
---

# Shared saved-job action descriptors

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
