---
{
  "type": "Evidence",
  "id": "docs-user-guide.publication-and-updates",
  "title": "docs/USER_GUIDE.md: publication-and-updates",
  "description": "Hosted handbook and native extension update publication.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "publication-and-updates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13, after 0.10.0 was published: re-reviewed the Updates, switch and Files and folders text against scenario/blender/updates.py, scenario/prefs.py (Updates panel wiring and the credential, project and output preferences), .github/workflows/pages.yml, tools/build_site.py, the Project history (cloud) toggle in scenario/blender/panels.py, Save for recovery in scenario/blender/operators.py, and the strip media copies and their scenario_asset property in scenario/blender/media_application.py and scenario/blender/film_review.py. The hosted index.json lists 0.10.0; the HTTPS install on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 is recorded in the release-acceptance Publication section. A headless switch on macOS arm64 Blender 5.1.2 in a disposable profile installed the published 0.10.0 ZIP into the local repository, seeded its preferences and a storage marker, removed it with Blender's extension remove command, then added the hosted repository and installed from it: the new copy was enabled under a different repository namespace with an empty key and secret and the default Output Folder, and Blender had deleted the old copy's preferences entry and its whole user directory. Blender 5.1.2's bundled extension manager passes the same user directory to the uninstall that Get Extensions runs. The switch was not exercised through the desktop interface, on Blender 5.0 or 5.2, or with real strips, and strip relinking was not exercised. An update between two published releases, with preferences and stored jobs kept, is not yet possible and remains a next-release acceptance check. tests/blender/run_all.py and the other release tooling sources were not re-reviewed and keep their earlier fingerprints. Earlier (2026-09-26): the exact ZIP passed 317 installed baseline tests per version on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; desktop inspection on 5.0.1 covers offline Updates layout and manager handoff; setup and sync dispatch tests include mocks. Bootstrap is restricted to the fixed pre-adoption manifest version and a nonempty historical snapshot, and is retired by release version advancement. A final post-provenance snapshot rejects newly published releases during verification.",
    "sources": {
      "scenario/blender/updates.py": "6678248428a6785dd0a2c0ba042338ee493c3a5da26f6471fc9fc3ad904d52b7",
      "scenario/prefs.py": "8501a51e598083a7414aa1c55c599001747e60caf57a0ce859402422880cf762",
      "tests/blender/test_updates.py": "2c4757ed88172dfde4e50c258ea3ba351ba65f26447d6b49ce07d36eae7daeae",
      "tests/blender/run_all.py": "e2f34d7b752f32b9d03f5761fbccb251ed3506e3506cb8ba91990e642db3ed6d",
      ".github/workflows/pages.yml": "b7e6c7c8f3b0b8cbe76595fbb9bb4a9a8ce0191dbb239872157f9c9e9fea8143",
      ".github/workflows/release-please.yml": "d729fcc5f0e069b8eddce853ba24751ab0055b4f40ef2285f80445147ca1ffa3",
      "tools/prepare_site_release.py": "c26961e1ae22462a398ad28a95335763933cfd463c4de449bb1bbe85b00b07d9",
      "tools/release_inventory.py": "44dfc7c3eec4320e0abb0c818ec021468576071183b2ca696e85da0110ac7d51",
      "tools/verify_release_inventory.py": "7e5ccfb0e66f744d1f273d520644744d2b16e00532a4a23f4d66a90655a3b222",
      "tools/build_site.py": "f06d48be78cda32048c7b9dd38e321cff187a1a29b8746ff34e6f24ec87a6ca9",
      "tools/build_docs_html.py": "40e8c099acc77be8b3d57edd31f1e2a0ade323d9932e1c822aee98320c01f4a2",
      "tests/unit/test_site_release.py": "dd3a76566d53fef0fdff8dfa6a10038f08d2f397bcf8123e57647ea491808795",
      "tests/unit/test_release_provenance.py": "76c4fbc2550f5186e92601fda6cfc5129057115e1c8f55b02ab448d3461d2ec3",
      "tests/unit/test_site.py": "cf30077ae7888dc63e87e2fc12fee20b0b55cad568501a892096aea2afb997dc",
      "tests/unit/test_release_handbook.py": "24dd6f8044ca39f38805e96bbf4e734c2236535551dc3dbbd9c2f567c10f43af",
      "scenario/blender/panels.py": "ed89c44a0d327f3a9de13d62f6bb44116e9ff88defdabc01e805900ee45c3d67",
      "scenario/blender/operators.py": "c4274af0155c9847b9911376727db70251aa09f7515e9ffe88774412ac7fc65d",
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83",
      "scenario/blender/film_review.py": "c5ae003ab2786ae3bf598e2f62faf4d393ca68669d2ca4f5a76c9bfdd0020b3d"
    }
  }
}
---

# docs/USER_GUIDE.md: publication-and-updates

Evidence for [the canonical document](../../USER_GUIDE.md).
