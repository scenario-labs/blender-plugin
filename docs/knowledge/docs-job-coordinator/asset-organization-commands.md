---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.asset-organization-commands",
  "title": "docs/JOB_COORDINATOR.md: asset organization commands",
  "description": "Guarded single collection and tag writes with read-back classification on the shared coordinator.",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "asset-organization-commands",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed request validation and normalization, including the 200-entry raw and 30-unique tag bounds and refusals naming the limit each enforces, scope refusal before any request, snapshot reads (get_bulk, collection retrieval, bounded exact-name lookup), weakly held single-use issued snapshots, the guard before every write and never after the last, membership and per-asset tag writes, continuation after definite rejections, stopping at the first uncertain, offline or guard failure, create dedup and the in-session uncertain-name set, one-read create reconciliation by acknowledged ID or exact name, read-back classification, result states, deactivation clearing snapshots and names, and worker cancellation of queued writes. Offline SDK MockTransport unit tests cover these paths, including adapted Studio create-once, later-page dedup and no-replay cases. No live collection, tag or bulk request was made; service name uniqueness, re-adding a member, DELETE body survival, tag normalization and live limits remain unverified. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "219fa9ca813e867140815a582f4ca58e2c2989f8385a5a5dd5af28633d67fc32",
      "scenario/core/jobs/organization.py": "7f69ce28e4c54e3c2b819cc76735d001671de6bcfcb12145b2cd90b059e8b84d",
      "scenario/core/jobs/coordinator.py": "329f641b24e7cd23603d1eae840072006a080a03b2911dca44d17b8b9aa56e9a",
      "scenario/core/jobs/workers.py": "5f879ca4bec0e2c92975c3e8168d26f65df50ad0b48af65228a0a69ac2bcde5e",
      "scenario/core/api/sdk_adapter.py": "8741ed98d0d4ace8a4d1c21a65aaf79f85eeabf69023477d23fa028f4911bb95",
      "tests/unit/test_asset_organization.py": "d6c5980c089df56f83c54f1ebfba186e0939100d9912286ba44554c75c9dced4",
      "tests/unit/organization_service.py": "799ce65ddd48602fa9701060c8723aabeaa30d3134c73ecb49450412cfddacaf",
      "tests/unit/test_job_coordinator.py": "f339e800e89f84d7932d8e377888da963a21e7f2e3fd33faf24a61468769f54f",
      "tests/unit/test_job_workers.py": "c7f1bbc64151d9633a3829478d27377791ddbea58a2b57113a1e140f856c46f0"
    }
  }
}
---

# Asset organization commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md#asset-organization-commands).
