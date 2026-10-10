---
{
  "type": "Evidence",
  "id": "docs-job-storage.legacy-mesh-sizes",
  "title": "Legacy OBJ and MTL size recovery",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "legacy-mesh-sizes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "78c4a70983f6d5b34fdf5e66ecf94d7fd6df07c8",
    "limits": "Reviewed explicit OBJ/MTL metadata-size tolerance with mandatory complete Content-Length, byte limits, unchanged optional digest verification and atomic local size/receipt correction. Offline regression coverage includes failed-job resume, preservation of prior receipts, incomplete responses, size limits, digest mismatch and store revision guards. No remote metadata write or paid resubmission; local hashes do not establish a remote cryptographic content attestation. Native and live acceptance are reported separately. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: result_metadata adds image_signature_matches for PNG, JPEG and WebP containers; texture roles and the rewritten mesh types are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "docs/JOB_STORAGE.md": "57f6d74fbe5317585dbdc6bfcab1f505e7a4ddda03905c471777596522d8710b",
      "scenario/core/jobs/results.py": "0cf7831eef38f0babd6cba539e0ba93a802f70faf5b53eb44ac34aff7ba98028",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "scenario/core/jobs/result_metadata.py": "088354aff1317747cbed7270114714bd2106773b57a0fccad73836c4c6ab3baf",
      "tests/unit/test_result_commands.py": "bf5bf503923116bd569b506b4c29fd08b49eb38aeda1a21b2e54cc5298a53cf8",
      "tests/unit/test_result_manifest.py": "55a462772b76f36e16e42574174714e8478deadc86c7a6a98d7d8f1c489a3119",
      "tests/unit/test_result_transfers.py": "2092ad9a432f54a8fd94dcf71e1346f7c90bdd9028fa65a999b691cb79d73a30"
    }
  }
}
---

Evidence for [the canonical guide](../../JOB_STORAGE.md).
