---
{
  "type": "Evidence",
  "id": "docs-ui-style.project-scope",
  "title": "docs/UI_STYLE.md: optional project selection",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "project-scope",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-08",
    "base_revision": "fa6136ea1a5eb648eea6c2e359bc6ed3aeee3558",
    "limits": "Optional Project ID behavior and native desktop interaction reviewed for source 29de2245b22e64bde6f1713797fd40d3eeb844c9, exact ZIP 3bd0a4b03ec9afe792e9bc36ed8805f1c5df06c38dccc46d5e98bdea2d831764. Installed matrix: 1065 tests per macOS arm64 Blender 5.0.1/5.1.2/5.2.1 run, two Windows-only skips. Native mouse/keyboard edits and inspected screenshots on macOS 27.0.1 arm64 Blender 5.1.2 verify blank/A/B/A/blank scoped saved-job selection, Enter/Tab commit, Escape cancellation, whitespace normalization, local URL rejection without default fallback, connection-status clearing, environment-source layout and viewport selection/zoom/front view. Synthetic credentials/jobs; offline mode and socket audit guard; exact installed bytes and normal profile unchanged. Preliminary automation select-all shortcuts exited Blender; completed using Home/Shift-End selection. Does not claim live project permissions, other OS/DPI desktop coverage, paid service, production updates or integrated release acceptance. Adjacent topics and their evidence are not refreshed.",
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
      "tests/blender/test_offline_runtime.py": "108f24d3d0837765b6fc63962487c804a6335cba8f91f11bc5483b66e2d52a98",
      "tools/desktop_review.py": "beb0d426d252667a787d211966f921e8ff796535e81b4e2558915c8d6dbc1095",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "docs/images/project-scope-default.png": "94cc4214a3b295eabfb31bee6eba49f21c1fd75b7a2be57d0c9a59e9a6098437",
      "docs/images/project-scope-project-a.png": "2799f1410728a9abd1d7c7c6de326bd5683afc4071c78e527719aa590fcfbdac",
      "docs/images/project-scope-environment.png": "78a51f41167237669b2d40a3cee77c8e83540f052327b3128014d2345930765c",
      "docs/images/project-scope-viewport.png": "42cf5ee3e97b80719e73dc8fc77a1f88707734b113ba572cf18aeda2827771f5"
    }
  }
}
---

Evidence for [optional project selection](../../UI_STYLE.md).
