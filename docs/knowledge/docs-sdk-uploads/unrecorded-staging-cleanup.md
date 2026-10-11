---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.unrecorded-staging-cleanup",
  "title": "Unrecorded staged copy cleanup after failed preparation or restart",
  "description": "Preparation and restart remove a new private copy that no saved record references when recording fails.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "unrecorded-staging-cleanup",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed UploadCommands.prepare and restart after staging: a failure of the origin guard, an inactive owner or the store write calls _discard_unrecorded and re-raises the original exception unchanged. The helper removes the new copy through UploadSources.discard only when UploadStore.get finds no record for the fresh request ID, and keeps it when a record exists or the store cannot be read. Only prepare and restart stage upload copies; every other upload entry point reaches prepare. Offline unit tests cover preparation stopped by an origin change, deactivation, StoreConflict or StoreError from create, a create that commits before failing and an unreadable store, alongside the existing restart cases. A process crash between staging and persistence can still leave a private orphan; automatic orphan retention and arbitrary staging cleanup remain unimplemented. No native Blender run or live service request was performed for this change. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/uploads.py": "df83f0035ccffd13578d9fc0fffb28dfc43bf503a54b4971186230dc2b5a9f4f",
      "scenario/core/jobs/upload_sources.py": "711517b315c8aca80f154ceecabc64f4c3d3b67c25e5304191c71b6a1ee617e4",
      "scenario/core/jobs/upload_store.py": "0e8f7a2799779200e666b76699948cd4c00db734fb71a92a26d9181154785f7a",
      "scenario/core/jobs/coordinator.py": "86d723261acb1fda7ef9718248be03c46de52cf6086277f15b673a46487551f5",
      "tests/unit/test_upload_commands.py": "fbba32b54382916d0dc5ca4b342156575435634bb805b794401b49d95473ac4a"
    }
  }
}
---

# Unrecorded staged copy cleanup after failed preparation or restart

Evidence for [the canonical document](../../SDK_UPLOADS.md).
