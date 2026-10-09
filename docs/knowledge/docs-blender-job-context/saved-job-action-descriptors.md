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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the bpy-free saved_job_actions.describe descriptor builder, its use by job_recovery.result_actions/draw_controls, the extracted panels.draw_active_job, and Studio Jobs/Results reuse of those panels. Offline unit tests cover golden labels, icons, operators, properties, numbering, Blockout review phases, reuse and review rows, unique keys, rejection of unknown actions, no Blender imports, and the MCP recover_local_job action enum, job_status action mapping and prepare_result_application purposes. A temporary offline harness compared the previous draw_controls with the descriptor path over 189,123 synthetic combinations with no difference; it is not committed. Installed native tests on macOS arm64 Blender 5.1.2 validate every descriptor property against the registered operator RNA, ordered drawing, read-only drawing of real saved prepared and remote jobs whose action names equal MCP job_status actions, and Studio pages drawing the sidebar views. The only intended difference is that a view without a saved revision, previously a draw-time KeyError that projection never produces, now draws nothing. No composer strip, new action, desktop interaction, screenshot, Blender 5.0/5.2 run or live acceptance is claimed.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "90e86afc6b3c727abfb6834961da55676e11cdffeb31e19543398b40d5c25ec9",
      "scenario/blender/job_recovery.py": "df318a223982f5aae4e4781826d290277cbb47fe33edead045621144748b2327",
      "scenario/blender/panels.py": "59b7efd2ee247a3b5d788aaf26e17e32abdc97e8966438287bcb31101a49f935",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/blender/model_jobs.py": "871f776b493890d35a74f4aaa67888b15ac6d33a1cdcaa0519eed0ce11140aab",
      "scenario/mcp/tools_scenario.py": "69d5be07239f2f6c9503aa0b5ca86d4e0e1310f7d92b1de44cdbb409c88ab229",
      "tests/unit/test_saved_job_actions.py": "2005061b9bc84bbaf72ba6cdb0bec28d236677dd37ad483b3c7abfdcb35bc546",
      "tests/blender/test_result_actions.py": "d6297248ee854197069398834d24ed705ae802df9b75e24744057a29f1f62045",
      "tests/blender/test_studio_view.py": "46a6636f4ee0c52919d636905a29510f849b97a0b993885a210c0e1c04e6d6e3",
      "tests/blender/test_blockout_jobs.py": "e7ec96601b00871766fdab717ef0ecfc952a8c6e577a373cf9ccc59238363f24"
    }
  }
}
---

# Shared saved-job action descriptors

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
