---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.catalog-form-seeding",
  "title": "Catalog loads keep captured origins",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "catalog-form-seeding",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed dependency-update origin invalidation against catalog form synchronization and automatically applied trained-model project defaults only. Catalog seeding and model-index restoration avoid RNA update callbacks, so a catalog load no longer makes origins, quotes or approvals captured before it stale; explicit selections and edits still invalidate them. Re-reviewed on 2026-10-12 for the sentence on project defaults: trained_defaults.apply_pending, which the GUI pump, local MCP render inspection and quotes, Save and Clear call, applies a default to a form without an explicit choice through _apply with seed, which stores the model enum index and each LoRA strength (trained_models.write_slots) as raw ID properties, runs generation.on_model_changed itself and re-arms the form's price; Use (trained_defaults.use) still assigns through RNA. The trained catalog events write only slot kinds, names and strength bounds, which have no update callback. JobSession._scene_changed, invalidate_scene and capture are unchanged by main's later job_session.py changes (preview, export and Film review ownership). Installed Blender 5.1.2 regressions cover a session origin across the first load and a restored model index, an MCP approval across a seeding catalog load, and origins captured in two scenes staying current while apply_pending applies a default there, with Use still invalidating one (test_trained_section.test_an_automatic_default_keeps_origins_captured_before_it, which failed before the raw writes). Other origin, render-thread, deletion and history claims retain prior evidence. No desktop timing, other Blender series, live or release acceptance is established.",
    "sources": {
      "scenario/blender/job_session.py": "283300899c616cbb4a2ae9f81751e2ab189c1f5b10c8acaf51da07be56cb6c29",
      "scenario/core/jobs/origins.py": "d1282d67aacdfe2444a776cf1338667bea9ee67392ff3f473db581a0f8059977",
      "scenario/blender/generation.py": "d00e21459c5a0c9a8757e5ed53fc829c3a5d7002797d50e7d69b6d0db712d566",
      "scenario/blender/params_ui.py": "390321d1de6ecc590aa3fb3f2268517c81c6d71f1853880c0d9175edbd9400ef",
      "tests/blender/test_generation.py": "27b397a4c8487f84150cdcd065f407c0fd671e7a01a994c0af04338f82fbc5d4",
      "tests/blender/test_model_generation.py": "8664c2f3cd296fc005a77d3d4009865df3e8b5bfdda3a6bbc9a2ed762bb32b68",
      "scenario/blender/trained_defaults.py": "4cbc49d1c38814b3fc05fc926e73857f0ac50bb5a968551d169ab1845fc3630f",
      "scenario/blender/trained_models.py": "36f16dd75a5cf822bae5be7387c48aad1daa15ed837d2244255661a8f44545f7",
      "tests/blender/test_trained_section.py": "a2cf1bd15d7265f5e06929908c12ed95c87aa2ffd1b5edeb7bbdccf1e28731fa"
    }
  }
}
---

Evidence for the [canonical guide](../../BLENDER_JOB_CONTEXT.md).
