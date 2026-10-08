---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.smoke-reference-inputs",
  "title": "Explicit reference inputs for protected smoke suites",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "smoke-reference-inputs",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "03b070b9cb663b63cf8a411f6126efb40d4c66d0",
    "limits": "Scoped implementation inspection of version-2 file/hash plans, separate exact upload-plan authorization, bounded private all-source staging before writes, existing shared SDK/coordinator multipart lifecycle and read-only recovery. Protected budget automation explicitly authorizes references and retains the aggregate generation quote/cap gate. Offline real-SDK/store tests cover uncertainty, scope/hash/binding failures, later-input stop, imported recovery, over-cap prevention and encrypted input-state preservation. Selected scenario-sdk 2.2.0 upload create/retrieve/trigger_action interfaces inspected; no SDK adapter, dependency, provider endpoint, native UI or installed package changes. No live upload, paid generation, protected environment provisioning, hosted paid run, provider output or complete #40/#68 acceptance is claimed. Other source/integration topics retain their earlier evidence.",
    "sources": {
      "tools/smoke_inputs.py": "3386ad525e8d9d9f4214dea1b6d05ec78084dfd02e00abf6305d904d2ef04526",
      "tools/smoke_suite.py": "5b9db4672b8887705028e3d8cd51872cdb8d966eb91889290c3d7ad6194a5ab3",
      "tools/smoke_image.py": "fc9d8b8494e8a125908702c9c09f72129f6aeb46ce91b21e5a67bb8b8ed63c9b",
      "scenario/core/jobs/uploads.py": "0eb0df9afcde2f37fcdba510ada065b489d52be058ab7319362af56be4232bea",
      "scenario/core/jobs/upload_sources.py": "5beb6a3a8a5c4ab696e6a8aff78426c4b6615b9256599a59fbad30ac56cc388e",
      "scenario/core/jobs/upload_store.py": "3b8be69ce6abb8593e7eb28b56403574b6a95534d8c9adf46564bb4941cc502c",
      "scenario/core/jobs/upload_transfers.py": "262f2e57734493cd9b21e9d582ec964cf7dbb4ce9688aa1f1a39b17945b3d7d5",
      "tests/unit/test_smoke_inputs.py": "984ffec1a8a9d446290b5e51870d35d8211db6ebb756745e925a226563e5d85c",
      "tests/unit/test_smoke_ci.py": "62fbc7789fa7f52a9fe8c3ae912af364bf0a50c939fbfa04cab4171020ece76d",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb"
    }
  }
}
---

Evidence for [the canonical guide](../../SDK_ADOPTION.md).
