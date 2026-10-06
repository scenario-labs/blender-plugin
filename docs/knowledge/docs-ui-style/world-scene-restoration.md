---
{
  "type": "Evidence",
  "id": "docs-ui-style.world-scene-restoration",
  "title": "World restoration across scenes",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "world-scene-restoration",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "a868553e40ef09ac5233e4899ba66103472196c1",
    "limits": "Reviewed session file/scene identity keys for per-destination World restoration, persistence-receipt retry without reassignment, guarded restoration and independent handle removal. Exact ZIP 8676574595eb6fcc21cee719467184bc87c6d3f73a9986741edc643749f2e9dc passed 692 installed tests each on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Regressions cover separate scenes, rename, deleted/recreated scene rejection and receipt retry from another active scene. Isolated 5.1.2 native review cancellation/confirmation, scene selection and viewport input restored both original Worlds, retained durable claims, made no extra mock requests and exited cleanly with unchanged normal profile. No live provider, other OS desktop, persistent undo, or release acceptance.",
    "sources": {
      "scenario/blender/model_jobs.py": "b9bc778b53db0d1798f95f94e2ef57d8ba538145e7f7569a38c908222bafb8f0",
      "scenario/blender/job_session.py": "a31bc7e5e07c37294e9d3057e5061d3cffb16f859db86ea4e527c14b348399de",
      "scenario/blender/world_application.py": "95a10cae5b1ec3fdc758a18dcb4e70a50ffe10961c1ab38e0c5bb9ea6dbe8934",
      "scenario/blender/job_recovery.py": "fe34f477610695ca8631184fa208d736ad49b360617c9cb1b2546ca1832bc926",
      "tests/blender/test_model_generation.py": "c69858a8121cf7090cd5925f87ca843095651a6fbac363ae0c1aa4cd6d019cef",
      "docs/images/world-scene-restore-approval.png": "6c8d6fa28c74cfb53bbf9c2b0786286b57da00c2cc75edaad6f3a843f451e0db",
      "docs/images/world-scenes-restored.png": "b45bf138e784fa6d93c4519a283b8376aa455174f69a0819917239e2a31d6bb7"
    }
  }
}
---

# World restoration across scenes

Evidence for [the canonical guide](../../UI_STYLE.md).
