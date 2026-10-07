---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-composition",
  "title": "Unpaid scoped Film composition drafts",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-composition",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Pure recipe and saved-source inspection; exact cut, selected takes, asset-bound rational audio duration, loop/duck phase, bounded layers, immutable draft and changed-source checks. No service call, media measurement, Blender mutation, task reservation or spend approval. Installed helper tests are not active UI/MCP, fresh provider schema, live generation, final-review/export, or human motion/audio acceptance. Only this topic was reviewed, not all claims in the guide. Composition source resolution computes task identities once per recipe instead of once per source; a ten-shot regression counts validation/hash work while existing scope, revision and dependency rejection tests remain in place.",
    "sources": {
      "scenario/core/scene/film_finish.py": "e51114ea696e4eaf3ec61534d0637e76f6ba5335ad8b46102439b79236391a43",
      "scenario/core/jobs/film_finishing.py": "d12f9eb278432b574c58baca46e62b6f9d7994f00fded099181378d497e79cd8",
      "tests/unit/test_film_finish.py": "9f749a31047f12db041f4bc6366aec265f97297d63668ec2b14313a8271f4a6d",
      "tests/unit/test_film_finishing.py": "4ff2fc0d77ee824a8132fdbf40aeca82e9b090fce80f13dbf205694de3222ae5",
      "tests/blender/test_film_finishing.py": "1d3e6e855a576d9d32b91679b6ca9af07eba7787962f509982c6993ba41f0041",
      "tests/blender/run_all.py": "eaf3195df6a6a1cddfb1a4093fd02899acc30266427f571cbb56854cb2cb26f2"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
