---
{
  "type": "Evidence",
  "id": "docs-ui-style.project-scope",
  "title": "docs/UI_STYLE.md: optional project selection",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "project-scope",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Inspected the optional saved Project ID, normalized selection, shared SDK catalog/job scope configuration, context retirement, read-only projection guards and refusal of unscoped legacy requests under an override. Exact candidate 10cdfd90623081104c936177a3b7fe0445df81e5cbddb4508882a60044970c3a passes 1057 installed tests on each macOS arm64 Blender 5.0.1/5.1.2/5.2.1 with unchanged normal profiles. Regressions cover selected UI/MCP quote and submission queries, stale approvals/delivery, in-flight receipts, returning to saved scope, invalid IDs no silent default fallback, and suspended prototype resumes while a project override is selected. 3802 offline unit tests pass with the known SDK authentication xfail. Native desktop input/screenshot acceptance remains pending because computer control could enumerate but not target the owned window. No live project permissions, account discovery, cross-platform desktop, paid run, production update or integrated release acceptance is claimed. Adjacent topics are not refreshed.",
    "sources": {
      "scenario/prefs.py": "b0fa6fe1f3f946ca8194980f8de31e6be1b080464be1b9107592b29d23dc939c",
      "scenario/blender/runtime.py": "fa9b138a024e088250b2783eedb4a7a8b1acb22b0a22756ad7a9e1a04d361fbe",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/film_scene_controls.py": "e7ae2babae5279111ad0b72c713b90443c8f373eea81d38eeb9a46e2b25c372e",
      "scenario/blender/film_composition_controls.py": "05f399e8f25e0b950e975a410b98f617780d383076bc6343a9c03d66e24cd975",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "tests/blender/test_credentials.py": "76726d9416872c1b37f0804a0583c7d48464f58ab1b97144cb9eac3c6200dcc9",
      "tests/blender/test_runtime_jobs.py": "7c6b0a44ed0a0ff52170e5808057778870fecb26120f790ec973c1fc337d605a",
      "tests/blender/test_sdk_estimates.py": "e3aae1a387ae8cefefee5b2107c9685d872322a567f9bbcbc2ad6d9050ba5a57",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52",
      "scenario/blender/pump.py": "6ffaf1a2a943d63796cf2d31d68e297b88c6ffd8a5389fb07605a9b8c51134d8",
      "tests/blender/test_offline_runtime.py": "108f24d3d0837765b6fc63962487c804a6335cba8f91f11bc5483b66e2d52a98"
    }
  }
}
---

Evidence for [optional project selection](../../UI_STYLE.md).
