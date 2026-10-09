---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.film-video-export",
  "title": "Owned offline Film video export",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "film-video-export",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the session-owned export thread and its independence from the shared workers and local media slot. Native/MCP export controls and the case-study bundle remain unimplemented. Local macOS arm64 runs of the installed export module pass on Blender 5.0.1, 5.1.2 and 5.2.1, including a real child export verified by Blender's decode check and by an installed ffprobe; Linux/Windows evidence comes from CI. No human playback, desktop interaction or native/MCP control is established.",
    "sources": {
      "scenario/blender/job_session.py": "96ed0e4825912df5de7dd939c8e963f7846e268326e256441e6c2e618801c55c",
      "scenario/core/jobs/coordinator.py": "08cfc053a4b27cac03e4002dab7429de06516ccdfeec9d1243a84e3414e7ba1d",
      "scenario/core/jobs/local_export.py": "ca449fe8eb3969af94534488bfadd3789c98985205dc421225431398c4a81164",
      "scenario/core/jobs/workers.py": "beb81e0452ad08b1691feebbf20a558b2c60c098ca28114d5255b4073208755d"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
