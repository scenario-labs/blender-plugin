---
{
  "type": "Evidence",
  "id": "docs-releasing.release-provenance",
  "title": "Read-only retained release provenance verification",
  "description": "GitHub verification policy and exact staged artifact boundaries.",
  "evidence": {
    "path": "docs/RELEASING.md",
    "scope": "release-provenance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "5d1f5a2062fed59b3a2fdefc621992467d34aea5",
    "limits": "Selected local inventories and ZIPs are checked with the existing archive/bundle validators. Current release/checksum/tag reads and GitHub CLI attestation flags bind both assets to the repository, release workflow, main ref and resolved commit; the release workflow explicitly requires triggering, checkout and release commits to agree. Offline fakes exercise policy arguments, rejected attestations, changed/withdrawn releases, annotated tag bounds, byte preservation, staged cleanup and existing outputs. Cryptographic verification is delegated to the installed authenticated gh CLI, not implemented or proven by the fakes. No published adopted release has been accepted by these tests; first-release live provenance, complete newest-release discovery, remote atomicity, site publication and native runtime acceptance remain separate gates. The local summary cannot authorize future publishing without fresh verification.",
    "sources": {
      "tools/verify_release_inventory.py": "7e5ccfb0e66f744d1f273d520644744d2b16e00532a4a23f4d66a90655a3b222",
      "tests/unit/test_release_provenance.py": "76c4fbc2550f5186e92601fda6cfc5129057115e1c8f55b02ab448d3461d2ec3",
      "tools/release_inventory.py": "44dfc7c3eec4320e0abb0c818ec021468576071183b2ca696e85da0110ac7d51",
      "tools/repository.py": "c41d4cd4964f78acb5fff9d0a20de976d0dcab94e7a14ca24d24e2073e6d191b",
      ".github/workflows/release-please.yml": "72a2af0eae492c029031fa8e1e8cf5fdf64cf84c3b8474953c270f127ad79047"
    }
  }
}
---

# Release provenance verification

Evidence for [the release procedure](../../RELEASING.md#verify-selected-release-provenance).
