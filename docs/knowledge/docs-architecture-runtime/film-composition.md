---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.film-composition",
  "title": "Unpaid scoped Film composition drafts",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "film-composition",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Pure recipe and saved-source inspection; exact cut, selected takes, asset-bound rational audio duration, loop/duck phase, bounded layers, immutable draft and changed-source checks. No service call, media measurement, Blender mutation, task reservation or spend approval. Installed helper tests are not active UI/MCP, fresh provider schema, live generation, final-review/export, or human motion/audio acceptance. Only this topic was reviewed, not all claims in the guide.",
    "sources": {
      "scenario/core/scene/film_finish.py": "e51114ea696e4eaf3ec61534d0637e76f6ba5335ad8b46102439b79236391a43",
      "scenario/core/jobs/film_finishing.py": "c069872429651a3f333a828e5f13f3be7f8c5e893acf5548f646d73406be1a06",
      "tests/unit/test_film_finish.py": "9f749a31047f12db041f4bc6366aec265f97297d63668ec2b14313a8271f4a6d",
      "tests/unit/test_film_finishing.py": "2dc39a46eca6f067059d67dd47cb80b1da4a7377f7f366a75991cf73065a53dc",
      "tests/blender/test_film_finishing.py": "1d3e6e855a576d9d32b91679b6ca9af07eba7787962f509982c6993ba41f0041",
      "tests/blender/run_all.py": "eaf3195df6a6a1cddfb1a4093fd02899acc30266427f571cbb56854cb2cb26f2"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
