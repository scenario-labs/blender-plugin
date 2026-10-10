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
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed request validation and normalization, including the 200-entry raw and 30-unique tag bounds and refusals naming the limit each enforces, scope refusal before any request, snapshot reads (get_bulk, collection retrieval, bounded exact-name lookup), weakly held single-use issued snapshots, the guard before every write and never after the last, membership and per-asset tag writes, continuation after definite rejections, stopping at the first uncertain, offline or guard failure, the bounded resend after an AlreadyMembers add refusal (one get_bulk read drops the assets now in the collection, the guard admits each resend, and a failed read, a refusal the read cannot explain, any other outcome or the three-request ADD_ATTEMPTS bound stops it; removals and uncertain outcomes are never resent; the result message counts the assets already present, also when the bound stops it), create dedup and the in-session uncertain-name set, one-read create reconciliation by acknowledged ID or exact name, read-back classification, result states, deactivation clearing snapshots and names, and worker cancellation of queued writes. Offline SDK MockTransport unit tests cover these paths, including adapted Studio create-once, later-page dedup and no-replay cases, a member added between prepare and apply, every target already a member, another 400 reason, an unexplained refusal, a failed read after the refusal, repeated concurrent adds capped at three requests that still count the assets already present, a guard failure and an uncertain outcome before or on the resend. The synthetic service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave by the hosted Scenario MCP. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "df200233f40a9e77b5d81bbe3cf1e3d23478eab5340a7849b1c823e63a8820fe",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/jobs/coordinator.py": "329f641b24e7cd23603d1eae840072006a080a03b2911dca44d17b8b9aa56e9a",
      "scenario/core/jobs/workers.py": "5f879ca4bec0e2c92975c3e8168d26f65df50ad0b48af65228a0a69ac2bcde5e",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "tests/unit/test_asset_organization.py": "330430da376a3fa3a7f95fa7271f2c4af4024479dbd3570abdcda6266b79c815",
      "tests/unit/organization_service.py": "0db133ded5cf6c9c105ad5f7ac55d9d5d5b32f77d5b57007d5bc72e627808222",
      "tests/unit/test_job_coordinator.py": "f339e800e89f84d7932d8e377888da963a21e7f2e3fd33faf24a61468769f54f",
      "tests/unit/test_job_workers.py": "c7f1bbc64151d9633a3829478d27377791ddbea58a2b57113a1e140f856c46f0"
    }
  }
}
---

# Asset organization commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md#asset-organization-commands).
