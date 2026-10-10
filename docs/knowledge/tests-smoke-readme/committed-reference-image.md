---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.committed-reference-image",
  "title": "Committed reference image in a version-2 smoke plan",
  "description": "Illustrative plan naming the first-party fixture by repository path and exact digest.",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "committed-reference-image",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the documented version-2 plan that names the first-party reference render by repository-relative path, real SHA-256, image kind and PNG type, with placeholder model ID and parameter name. An offline unit test extracts that plan from the guide, validates it with the input-plan checker, resolves its file beneath the repository root and stages the bytes through the shared upload staging with the documented digest. The protected workflow passes the checkout as the input root. No upload, quote, generation, provider acceptance of this image or hosted run is claimed, and the existing smoke-reference-inputs topic keeps its own review.",
    "sources": {
      "tests/fixtures/synthetic/reference-toadstool-512.png": "b70e8debff0ba0fc7dd8823a9a38229600e3fd7b8f22a1a32c490b4310182e02",
      "tests/unit/test_reference_fixture.py": "475556b4c88fd0dec70fa6e342b803e03ccdd439936d48ffd748346cf7676eb2",
      "tools/smoke_inputs.py": "3386ad525e8d9d9f4214dea1b6d05ec78084dfd02e00abf6305d904d2ef04526",
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb"
    }
  }
}
---

# Committed reference image in a version-2 smoke plan

Evidence for [the canonical guide](../../../tests/smoke/README.md).
