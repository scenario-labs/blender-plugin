---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.upload-restart",
  "title": "JobSession upload restart command",
  "description": "Queued abandonment and restaging under a current origin.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "upload-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed JobSession.restart_upload admission, worker queuing, completion origin and the reference facade's origin reuse rule. Installed native tests on macOS arm64 Blender 5.1.2 restart an upload from a new session and complete its replacement. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/blender/job_session.py": "4ca6cc123fbb96a2bfcfc016fee9c2414ca230097c08cbf7c97e6560b0ccd85c",
      "scenario/blender/reference_uploads.py": "bbc2b4f5e8a50bef31694d8764953d21b9b4c45b0f9cf3139f15dbf2a6e3c10f",
      "scenario/core/jobs/workers.py": "d99556bbbb1088206de7cf6668cd98031636bddedadb73b433b5bbc0b318ba6c",
      "scenario/core/jobs/uploads.py": "06cacc568478204ddbbba7f67f03d48da85fe492a8db8dcf04df14db35944aef",
      "tests/blender/test_session_uploads.py": "5e209d9d11467a7b4eb6077f228828f583f9d712ce96d7e1331e34017da0588e",
      "tests/blender/test_reference_uploads.py": "7b3ddfa61ba562200e7258f53bd372d7782608e05cf977a466db1b86e28c109b"
    }
  }
}
---

# JobSession upload restart command

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
