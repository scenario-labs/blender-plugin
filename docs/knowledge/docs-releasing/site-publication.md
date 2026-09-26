---
{
  "type": "Evidence",
  "id": "docs-releasing.site-publication",
  "title": "docs/RELEASING.md: site-publication",
  "description": "Hosted handbook and native extension update publication.",
  "evidence": {
    "path": "docs/RELEASING.md",
    "scope": "site-publication",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "5e1541029ca27286d2b30861d5c0a239fe45736b",
    "limits": "Reviewed release handbook checksum, attestation and draft-upload wiring; current-main Pages publication with serialized fresh discovery, retention and selected provenance verification; failure/retry and publication-race contracts. No positive adopted-release attestation, hosted deployment, DNS/TLS delivery or production update/state-preservation acceptance is established. The explicit bootstrap publishes only a guide when no adopted tag exists; drafts, prereleases and malformed adopted releases do not trigger fallback. Live read-only GitHub discovery confirmed the initial bootstrap channel. No production release was published.",
    "sources": {
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

# docs/RELEASING.md: site-publication

Evidence for [the canonical document](../../RELEASING.md).
