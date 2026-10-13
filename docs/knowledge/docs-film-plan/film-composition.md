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
    "limits": "Pure recipe and saved-source inspection; exact cut, selected takes, asset-bound rational audio duration, loop/duck phase, bounded layers, immutable draft and changed-source checks. No service call, media measurement, Blender mutation, task reservation or spend approval. Installed helper tests are not active UI/MCP, fresh provider schema, live generation, final-review/export, or human motion/audio acceptance. Only this topic was reviewed, not all claims in the guide. Composition source resolution computes task identities once per recipe instead of once per source; a ten-shot regression counts validation/hash work while existing scope, revision and dependency rejection tests remain in place. Boundary regressions distinguish the 50-shot recipe limit from the 50 combined composition layers, including default score, explicit no-score and previs output; rejected composition leaves the recipe unchanged. On 2026-10-13 a scoped re-inspection for readable Film source errors, not a full re-review, covered every change to scenario/core/scene/film_finish.py, tests/unit/test_film_finish.py and tests/unit/test_film_finishing.py since their recorded fingerprints. required_sources now raises FilmSourceError naming up to five undeclared source tasks; for the looping score implied by an omitted audio_tracks it names that task and the audio_tracks: [] alternative, and a picture/audio conflict names its task. recipe_warnings warns, without failing a load, only when no task is named score, the default; because a load cannot know a later preparation's score_task_id, its text states that condition and the score_task_id and audio_tracks: [] alternatives. Unit tests cover both messages, previs, explicit no-score and the declared default score, the typed overrun and the saved-source errors naming their task; the unit suite passed (7,195 passed, 1 expected failure). scenario/core/jobs/film_finishing.py also changed here but was already stale on main, so its fingerprint is unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/scene/film_finish.py": "8f98cdf6678c43d5436f8941ff06f83b975c741c6e2374e909035b5744b7ff5b",
      "scenario/core/jobs/film_finishing.py": "d12f9eb278432b574c58baca46e62b6f9d7994f00fded099181378d497e79cd8",
      "tests/unit/test_film_finish.py": "fee05adc58910acb460f89d6e119a30b9e7982f4553c3952ab4ba83dcc8a1aba",
      "tests/unit/test_film_finishing.py": "c0ca8d2ff2a7e5a5bd02f8f801185d19989ac9b6091498e94d1a9ed5ed15a042",
      "tests/blender/test_film_finishing.py": "1d3e6e855a576d9d32b91679b6ca9af07eba7787962f509982c6993ba41f0041",
      "tests/blender/run_all.py": "eaf3195df6a6a1cddfb1a4093fd02899acc30266427f571cbb56854cb2cb26f2"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
