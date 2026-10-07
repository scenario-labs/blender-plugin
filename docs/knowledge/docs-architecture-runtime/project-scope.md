---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.project-scope",
  "title": "docs/architecture/runtime.md: optional project selection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "project-scope",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Inspected the optional saved Project ID, normalized selection, shared SDK catalog/job scope configuration, context retirement, read-only projection guards and retirement of unscoped prototype requests for every selection. The preceding candidate 44d4a61354c8f91e2fe93e93e6834259216787ee1403562308de322d27844b42 passes 1058 installed tests on each macOS arm64 Blender 5.0.1/5.1.2/5.2.1 with unchanged normal profiles. Regressions cover selected UI/MCP quote and submission queries, stale approvals/delivery, in-flight receipts, returning to saved scope, invalid IDs no silent default fallback, and prototype record preservation across online/project changes after automatic resume retirement. The updated retirement archive and tests are recorded in the separate legacy-job-retirement topic. 3807 offline unit tests pass with the known SDK authentication xfail. Native desktop input/screenshot acceptance remains pending because computer control could enumerate but not target the owned window. No live project permissions, account discovery, cross-platform desktop, paid run, production update or integrated release acceptance is claimed. Adjacent topics are not refreshed.",
    "sources": {
      "scenario/prefs.py": "b0fa6fe1f3f946ca8194980f8de31e6be1b080464be1b9107592b29d23dc939c",
      "scenario/blender/runtime.py": "f85b53a9684831297fc07b6715d3286169c2713dc1116bbdb8220a979dcefe4f",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/film_scene_controls.py": "e7ae2babae5279111ad0b72c713b90443c8f373eea81d38eeb9a46e2b25c372e",
      "scenario/blender/film_composition_controls.py": "05f399e8f25e0b950e975a410b98f617780d383076bc6343a9c03d66e24cd975",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "tests/blender/test_credentials.py": "3878d0df15efe4b0bb2aec40b06aa1bd6118e4fb7146b3c011b16cfee32e306a",
      "tests/blender/test_runtime_jobs.py": "7c6b0a44ed0a0ff52170e5808057778870fecb26120f790ec973c1fc337d605a",
      "tests/blender/test_sdk_estimates.py": "75860b7e67b6fdf42bdf34959d858719aa62a4425f11213ac6062b5d9e7c741b",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52",
      "scenario/blender/pump.py": "aae6c6a454ef558d76ce5de90d08ced87f1f5904087d28f2d3ca49ed3bc1e11c",
      "tests/blender/test_offline_runtime.py": "3429f261772abd43507d88a666ad9135a606c8927b20bf4e504c81c7d29c2c6e"
    }
  }
}
---

Evidence for [optional project selection](../../architecture/runtime.md).
