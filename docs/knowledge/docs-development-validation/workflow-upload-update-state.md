---
{
  "type": "Evidence",
  "id": "docs-development-validation.workflow-upload-update-state",
  "title": "Workflow upload state across native package updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "workflow-upload-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed optional seeding of upload_path and workflow upload ID properties, a separate pending-upload scene whose pricing must be refused, snapshots that omit absent fields and the workflow_uploads_preserved report. Local Blender 5.1.2 macOS arm64 runs passed update and offline restart with zero service requests against a version-only synthetic predecessor (reporting true), including one for the candidate with the stopped-upload change, and earlier against a local test predecessor carrying origin/main package sources (reporting false while workflow_references_preserved stayed true). These are synthetic predecessors, not a published release pair, CI evidence or release approval. The stopped-upload change adds no persisted fields: the marker, request ID and upload_path properties are unchanged. The later change that keeps stopped-upload notes through undo and redo holds them only in memory and adds no persisted field; the update run was not repeated for it. Rebased onto base_revision, which adds store schema and schema 10 evidence to the same update report: the probe keeps both the job origin constant and the workflow fixtures, the runner expects workflow_uploads_preserved beside that evidence, and the offline runner test that fakes the report now includes it. The native update run was not repeated after this rebase; the later abandoned-upload delivery fix adds no persisted field.",
    "sources": {
      "docs/development/validation.md": "dc45f0a685ef5741406ca0c10f1de4f18604f7187396bb0d75411161960f866a",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_uploads.py": "b4c391e0b8f1b932acacc29dda46cd24b8d076654aaede61dee8ff400bc2dde0",
      "tests/blender/package_update.py": "c877e937a708c2842286893f98c4ade1cd4dfb96a08f6a5f2105d673564bdca8",
      "tools/test_repository_update.py": "2de946b95a11592bc0ad4ff8e3c071d97b0a1aeb3116f5f5232612ae9910d441",
      "tests/unit/test_repository_update_runner.py": "49e2f17c5b0e92cfd46865f9a0485d26f7d4a20e796a86198f9beaa77650aaae"
    }
  }
}
---

Evidence for [the canonical guide](../../development/validation.md).
