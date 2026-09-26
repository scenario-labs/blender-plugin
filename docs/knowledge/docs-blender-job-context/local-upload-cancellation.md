---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.local-upload-cancellation",
  "title": "docs/BLENDER_JOB_CONTEXT.md: local upload cancellation",
  "description": "Revision-guarded cancellation before remote initialization.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "local-upload-cancellation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "4570d8fce08fdb9666333bbbd0ec6d37fea723b9",
    "limits": "Reviewed only cancellation of prepared upload intent through the shared coordinator, workers and JobSession. Tests cover cancellation/initialization races, full queues, scope and revision rejection, source preservation, persistence failure, origin loss and restart. No remote abort, source cleanup, active UI/MCP controls or live upload acceptance is established. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/uploads.py": "0d51d04c4ea0b0536adec7e662e55236f453c65ba08ef1757c78116749282dc9",
      "scenario/core/jobs/coordinator.py": "94d6bfa70be183ef2a031c63211816ad5e2e95721d647b878219aeadeecd67ee",
      "scenario/core/jobs/workers.py": "a9a10e8f68087f5c14f3827dc1ff52b51d25f2905ee4c362a36e931b3a410a5c",
      "scenario/blender/job_session.py": "9992bed5d0fe72c7c39c23751964b845cf9006eca19e32b131c5f986d81fa1c0",
      "tests/unit/test_upload_commands.py": "821a4b7f718c4ea1d09b7f57e3ca0f31f502b4f02c2378e7e95640cf7b2774cf",
      "tests/blender/test_session_uploads.py": "75ba2c97be0102a931e37c3ea6ffb10cf4dc033aa006c1daa17e50bfc14d4eff",
      "scenario/core/jobs/upload_store.py": "e53e44059fba806e5284f75327277fc7dcfceb7cd8a5f77e7a57696ce6372cf8"
    }
  }
}
---

# Local upload cancellation

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
