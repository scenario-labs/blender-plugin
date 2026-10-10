---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.texture-result-roles",
  "title": "Durable texture result roles",
  "description": "Allowlisted texture semantics independent of MIME and atomic shared-store upgrade.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "texture-result-roles",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Inspected SDK 2.2.0 asset raw-response fields, MIME-first allowlisted texture semantics, durable manifest role preservation, fresh-download role checks, and atomic schema 2/3 to 4 upgrades. Unit tests cover all supported role labels, unknown/malformed metadata, nonimage labels, restart, changed roles, no metadata enrichment, truncation, all scopes/states, recovered destinations, corrupt rows and failed commits. Installed-ZIP tests exercise role persistence and version 3 upgrade with Blender Python on macOS arm64 5.0.1/5.1.2/5.2.1. Existing SDK method and retry/authentication behavior unchanged. No raw metadata, prompt or URL retention, no new endpoint/fallback, material assignment, texture-set selection, decoder/color-space guarantees, live provider acceptance, desktop changes or release acceptance. Other source topics retain their independent review limits. Scoped 2026-10-10 check of the Render Video first-frame handoff, not a full re-review: its unit tests add the image signature cases; texture-role cases are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/jobs/result_metadata.py": "5a454fcd5024e015dc4b4ae5ff40909f6b121ef6d73a4bdd70def58985da17c4",
      "scenario/core/jobs/results.py": "1adbac9da2310b3632028afa78b5305b58cb7df86f0b9784de07bd6d3653a131",
      "scenario/core/jobs/store.py": "bf8c638af4ae4a7335450eb4329827944912813433deeccba8f3c97d0faa2f6f",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/unit/test_result_metadata.py": "d4f4036235a01b6108d5926ec6ce4ff224ce50ed536ff7b2788fb574e6abf658",
      "tests/unit/test_result_commands.py": "b556e9e584f538a843ab50989926c486575b55f2431276e7b6c959492fe7751e",
      "tests/unit/test_result_manifest.py": "7c1aa7dbfb94ca8f2404ea465042cd94a9bd2244bdf3dfb23a46e4e7ff63567c",
      "tests/unit/test_job_store.py": "c35180cf61c27e729ac2c4646a579995aba90d618bc82ed7e54d49f3694c2d46",
      "tests/unit/test_scenario_sdk_contract.py": "f8cde40bb848e527098795a52240364ea3f6a609993fb995863567caf0c27b39",
      "tests/blender/test_job_store.py": "d23b58f99d95658971671a4382777c09c4afb1f52761ed106e990dbcae901a24"
    }
  }
}
---

# Durable texture result roles

Evidence for [the canonical document](../../JOB_COORDINATOR.md).
