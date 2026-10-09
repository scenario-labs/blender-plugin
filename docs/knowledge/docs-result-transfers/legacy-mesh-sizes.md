---
{
  "type": "Evidence",
  "id": "docs-result-transfers.legacy-mesh-sizes",
  "title": "Legacy OBJ and MTL size recovery",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "legacy-mesh-sizes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "78c4a70983f6d5b34fdf5e66ecf94d7fd6df07c8",
    "limits": "Reviewed explicit OBJ/MTL metadata-size tolerance with mandatory complete Content-Length, byte limits, unchanged optional digest verification and atomic local size/receipt correction. Offline regression coverage includes failed-job resume, preservation of prior receipts, incomplete responses, size limits, digest mismatch and store revision guards. No remote metadata write or paid resubmission; local hashes do not establish a remote cryptographic content attestation. Native and live acceptance are reported separately.",
    "sources": {
      "docs/RESULT_TRANSFERS.md": "578a12ab06328569e07ec270c40bf0f16d848bb3e0496340d7a241fc38b34589",
      "scenario/core/jobs/results.py": "0cf7831eef38f0babd6cba539e0ba93a802f70faf5b53eb44ac34aff7ba98028",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "tests/unit/test_result_commands.py": "bf5bf503923116bd569b506b4c29fd08b49eb38aeda1a21b2e54cc5298a53cf8",
      "tests/unit/test_result_manifest.py": "55a462772b76f36e16e42574174714e8478deadc86c7a6a98d7d8f1c489a3119",
      "tests/unit/test_result_transfers.py": "2092ad9a432f54a8fd94dcf71e1346f7c90bdd9028fa65a999b691cb79d73a30"
    }
  }
}
---

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
