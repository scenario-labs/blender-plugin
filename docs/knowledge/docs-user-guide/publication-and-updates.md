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
    "reviewed_at": "2026-09-26",
    "base_revision": "5e1541029ca27286d2b30861d5c0a239fe45736b",
    "limits": "Reviewed update setup/check/manual fallback, repository namespace implications and release handbook download instructions. The exact ZIP passed 317 installed baseline tests per version on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Desktop inspection on 5.0.1 covers offline Updates layout and manager handoff; setup/sync dispatch tests include mocks. Hosted repository, real update/state preservation and desktop interaction on 5.1/5.2 remain acceptance gates.",
    "sources": {
      "scenario/blender/updates.py": "7391e0fd941bc24d8ddecc168d03858fad186a3f834c927c4ba92e2dae586862",
      "scenario/prefs.py": "52b84d7c54f32fc6540687815439a615117bb17a535de62ee665f8b3d0e98038",
      "tests/blender/test_updates.py": "2c4757ed88172dfde4e50c258ea3ba351ba65f26447d6b49ce07d36eae7daeae",
      "tests/blender/run_all.py": "e2f34d7b752f32b9d03f5761fbccb251ed3506e3506cb8ba91990e642db3ed6d",
      ".github/workflows/pages.yml": "5234ed4ef59ab18e24a1c5d37d7924390b9094bc55e709994e3a23952cccbff3",
      ".github/workflows/release-please.yml": "d729fcc5f0e069b8eddce853ba24751ab0055b4f40ef2285f80445147ca1ffa3",
      "tools/prepare_site_release.py": "524c06143bd85cc86ff6035cef9ba072f58f4bdef68d8be8ee1d1dd6700a70cf",
      "tools/release_inventory.py": "44dfc7c3eec4320e0abb0c818ec021468576071183b2ca696e85da0110ac7d51",
      "tools/verify_release_inventory.py": "7e5ccfb0e66f744d1f273d520644744d2b16e00532a4a23f4d66a90655a3b222",
      "tools/build_site.py": "788667fede96693e7dd311b30e3b92eae62b9ee3c84cc44102d99e5f803df895",
      "tools/build_docs_html.py": "40e8c099acc77be8b3d57edd31f1e2a0ade323d9932e1c822aee98320c01f4a2",
      "tests/unit/test_site_release.py": "d1d82aa6709e851cb60c3f6ebdfd560125bcdc4f6b576cf35c02b6b99c615a49",
      "tests/unit/test_release_provenance.py": "76c4fbc2550f5186e92601fda6cfc5129057115e1c8f55b02ab448d3461d2ec3",
      "tests/unit/test_site.py": "cf30077ae7888dc63e87e2fc12fee20b0b55cad568501a892096aea2afb997dc",
      "tests/unit/test_release_handbook.py": "24dd6f8044ca39f38805e96bbf4e734c2236535551dc3dbbd9c2f567c10f43af"
    }
  }
}
---

# docs/USER_GUIDE.md: publication-and-updates

Evidence for [the canonical document](../../USER_GUIDE.md).
