---
{
  "type": "Evidence",
  "id": "docs-ui-style.waiting-workflow-steps",
  "title": "Waiting workflow step status row",
  "description": "The shared descriptors draw a status row without an operator for a waiting workflow step.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "waiting-workflow-steps",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that review_step becomes a status descriptor without an operator, drawn by job_recovery.draw_action as a label, before the recovery controls, and that drawing reads only in-memory views. Unit tests check the descriptor order and fields; an installed test checks the label on a projected view. Physical desktop evidence, screenshots, DPI and IME are pending. No native review or decision control exists yet. Re-reviewed on 2026-10-10 after ModelJobs gained read_steps, decision_outcome and the workflow cancel explanation and the installed tests gained MCP step tool cases: the status row, its descriptor and read-only drawing are unchanged, and this document still describes no native review or decision control.",
    "sources": {
      "scenario/core/ui/saved_job_actions.py": "751b2d03f53d0439121dc4528f3fb8b1c683f9368a692b12b5c90cf50b51240e",
      "scenario/blender/job_recovery.py": "da8df6bde6c9a0613565ea0563e7f1211086448d75e9419414f9c738038bda63",
      "scenario/blender/model_jobs.py": "0541e5fdad595a51693e30270c3e187d631bfb279f6089fb188aac810b5cac7f",
      "tests/unit/test_saved_job_actions.py": "b5888fd4d1efce167fc71464bb8080b4c0b48cdf72ede9d7029fb73377e6f01a",
      "tests/blender/test_workflow_commands.py": "601e3ea00167217427fe3185e37fec40ddc522bec339524b530dbfaac00f004e"
    }
  }
}
---

# Waiting workflow step status row

Evidence for [the canonical document](../../UI_STYLE.md).
