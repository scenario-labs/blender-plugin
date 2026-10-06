---
{
  "type": "Evidence",
  "id": "docs-world-application.world-scene-restoration",
  "title": "World restoration across scenes",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "world-scene-restoration",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "a868553e40ef09ac5233e4899ba66103472196c1",
    "limits": "Reviewed per-destination World restoration using scene identities owned by one session, independent of ordinary origin revisions; persistence-receipt retry without reassignment; guarded restoration and independent handle removal. Exact ZIP 24c7731dc6f339d55f826dfd27e68f0b90052b2c987fe9572431d5dbe6c353ca passed 694 installed tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Regressions cover separate scenes, rename, deleted/recreated scene rejection, receipt retry from another active scene, render-thread revision reset, history-callback retirement, stale approvals and expired-handle pruning. Isolated 5.1.2 native review cancellation/confirmation, scene selection and viewport input after a synthetic render-thread callback restored both original Worlds, retained durable claims, made no extra mock requests and exited cleanly with unchanged normal profile. Screenshots retain the prior 8676574595eb6fcc21cee719467184bc87c6d3f73a9986741edc643749f2e9dc artifact provenance; UI_STYLE records both runs. No physical desktop Undo/Redo, live provider, other OS desktop, persistent undo, or release acceptance.",
    "sources": {
      "scenario/blender/model_jobs.py": "ee9edadea350f2bbc3e082f69071862d862c51d3167bc306d41d57ee5fb408da",
      "scenario/blender/job_session.py": "9930de9c6bde4c611dadffc328ccbf4490ce84e861d8118910ac85bbbc81e0f8",
      "scenario/blender/world_application.py": "95a10cae5b1ec3fdc758a18dcb4e70a50ffe10961c1ab38e0c5bb9ea6dbe8934",
      "scenario/blender/job_recovery.py": "fe34f477610695ca8631184fa208d736ad49b360617c9cb1b2546ca1832bc926",
      "tests/blender/test_model_generation.py": "3d13b1523ff8a5bc11c86ab731208e8718018a9afbf721e3bfaef23a8f51c1b4",
      "docs/images/world-scene-restore-approval.png": "6c8d6fa28c74cfb53bbf9c2b0786286b57da00c2cc75edaad6f3a843f451e0db",
      "docs/images/world-scenes-restored.png": "b45bf138e784fa6d93c4519a283b8376aa455174f69a0819917239e2a31d6bb7"
    }
  }
}
---

# World restoration across scenes

Evidence for [the canonical guide](../../WORLD_APPLICATION.md).
