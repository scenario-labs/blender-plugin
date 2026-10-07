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
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Pure recipe and saved-source inspection; exact cut, selected takes, asset-bound rational audio duration, loop/duck phase, bounded layers, immutable draft and changed-source checks. No service call, media measurement, Blender mutation, task reservation or spend approval. Installed helper tests are not active UI/MCP, fresh provider schema, live generation, final-review/export, or human motion/audio acceptance. Only this topic was reviewed, not all claims in the guide. Composition source resolution computes task identities once per recipe instead of once per source; a ten-shot regression counts validation/hash work while existing scope, revision and dependency rejection tests remain in place. Boundary regressions distinguish the 50-shot recipe limit from the 50 combined composition layers, including default score, explicit no-score and previs output; rejected composition leaves the recipe unchanged.",
    "sources": {
      "scenario/core/scene/film_finish.py": "54d2a31b9458d523f669c118b43784c3667bec34ef169fae7990a1852553bdd4",
      "scenario/core/jobs/film_finishing.py": "d12f9eb278432b574c58baca46e62b6f9d7994f00fded099181378d497e79cd8",
      "tests/unit/test_film_finish.py": "f488a3344e0c522fb0bd3a43c895cbd0f39dd166b5ab5f66896e61c4bab7dffa",
      "tests/unit/test_film_finishing.py": "4ff2fc0d77ee824a8132fdbf40aeca82e9b090fce80f13dbf205694de3222ae5",
      "tests/blender/test_film_finishing.py": "1d3e6e855a576d9d32b91679b6ca9af07eba7787962f509982c6993ba41f0041",
      "tests/blender/run_all.py": "eaf3195df6a6a1cddfb1a4093fd02899acc30266427f571cbb56854cb2cb26f2"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
