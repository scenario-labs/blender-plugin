---
{
  "type": "Evidence",
  "id": "docs-development-validation.workflow-upload-update-state",
  "title": "Workflow upload state across native package updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "workflow-upload-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed optional seeding of upload_path and workflow upload ID properties, a separate pending-upload scene whose pricing must be refused, snapshots that omit absent fields and the workflow_uploads_preserved report. Local Blender 5.1.2 macOS arm64 runs passed update and offline restart with zero service requests against a version-only synthetic predecessor (reporting true), including one for the candidate with the stopped-upload change, and earlier against a local test predecessor carrying origin/main package sources (reporting false while workflow_references_preserved stayed true). These are synthetic predecessors, not a published release pair, CI evidence or release approval. The stopped-upload change adds no persisted fields: the marker, request ID and upload_path properties are unchanged.",
    "sources": {
      "docs/development/validation.md": "5fb9e3ed4103b27add6db69b2128fe637ca98dfd8bd0f8d364b708966f5505aa",
      "scenario/blender/workflow_controls.py": "86e56c432f605e8c2532b82565a180735dc5eabe28db3e0d877adceb620090d8",
      "scenario/blender/workflow_uploads.py": "2ccb7239d41a1f3aaef0adcc967692ebc04d923d402c917111e62df1ad1d667f",
      "tests/blender/package_update.py": "397aec773589cd484841c891f69d9e72b29e3fd4ae39c06fc6be0dfb26f04197",
      "tools/test_repository_update.py": "7ef5bfca46f27305a528ec309c1907434bb97d79c81356be37b1f3e272d9abaa"
    }
  }
}
---

Evidence for [the canonical guide](../../development/validation.md).
