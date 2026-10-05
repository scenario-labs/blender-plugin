---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.jobs-view-projection",
  "title": "Bounded model job display projection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "jobs-view-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Shared model pump, inspection, recovery and submission publish authoritative views by local ID with a fifty-row bound and stable creation-time/ID ordering. Native regression covers duplicates, hydration and repeated ticks. This display policy does not cap durable storage or worker lifetime and adds no new controls or desktop input proof. Hydrated display records currently lack creation timestamps.",
    "sources": {
      "scenario/blender/runtime.py": "bd4657cdd5dd15d3dc1ba4f6a0994fd0cd778e2e19f5be1479ddae008e7f095c",
      "scenario/blender/generation.py": "22f098a20da18bc81c53331c8771959fe35765fea09d609e14bb5f1f589b902e",
      "scenario/blender/model_jobs.py": "1c71898d7ab1c1f0c980d1e1bcb7afe07d6d1427f0dbb187d505e5f8b3806226",
      "tests/blender/test_model_generation.py": "ef5afba63fa18fad1b5ed6b4bb6ef51e758482222144423e3f4c324a594b2504"
    }
  }
}
---

Source evidence for [the runtime guide](../../architecture/runtime.md).
