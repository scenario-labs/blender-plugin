---
{
  "type": "Evidence",
  "id": "readme.publication-and-updates",
  "title": "README.md: publication-and-updates",
  "description": "Hosted handbook and native extension update publication.",
  "evidence": {
    "path": "README.md",
    "scope": "publication-and-updates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13, after 0.10.0 was published: README Install now leads with the official repository and keeps the ZIP as an alternative; Updates says the repository offers releases from 0.10.0, that a ZIP copy does not update itself, and summarizes the switch: uninstall first, which deletes the ZIP copy's storage including stored jobs and strip media, install from the repository and enter the key again; past generations remain under Project history (cloud). Checked against scenario/blender/updates.py, the Updates panel wiring in scenario/prefs.py, the Project history (cloud) toggle in scenario/blender/panels.py, the strip media copies in scenario/blender/media_application.py, .github/workflows/pages.yml, the hosted index.json listing 0.10.0 and the headless switch recorded in the user guide's publication-and-updates topic. HTTPS install evidence is in the release-acceptance Publication section. No update between two published releases or production state preservation is established yet; tests/blender/run_all.py keeps its earlier fingerprint. Earlier (2026-09-26): the installed ZIP baseline passed 317 tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; desktop 5.0.1 inspection covers Updates layout, offline gating, native-manager handoff and return to keyboard viewport navigation.",
    "sources": {
      "scenario/blender/updates.py": "6678248428a6785dd0a2c0ba042338ee493c3a5da26f6471fc9fc3ad904d52b7",
      "scenario/prefs.py": "8501a51e598083a7414aa1c55c599001747e60caf57a0ce859402422880cf762",
      "tests/blender/test_updates.py": "2c4757ed88172dfde4e50c258ea3ba351ba65f26447d6b49ce07d36eae7daeae",
      "tests/blender/run_all.py": "e2f34d7b752f32b9d03f5761fbccb251ed3506e3506cb8ba91990e642db3ed6d",
      ".github/workflows/pages.yml": "b7e6c7c8f3b0b8cbe76595fbb9bb4a9a8ce0191dbb239872157f9c9e9fea8143",
      "scenario/blender/panels.py": "ed89c44a0d327f3a9de13d62f6bb44116e9ff88defdabc01e805900ee45c3d67",
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83"
    }
  }
}
---

# README.md: publication-and-updates

Evidence for [the canonical document](../../../README.md).
