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
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed request validation and normalization, including the 200-entry raw and 30-unique tag bounds and refusals naming the limit each enforces, scope refusal before any request, snapshot reads (get_bulk, collection retrieval, bounded exact-name lookup), weakly held single-use issued snapshots, the guard before every write and never after the last, membership and per-asset tag writes, continuation after definite rejections, stopping at the first uncertain, offline or guard failure, the bounded resend after an AlreadyMembers add refusal (one get_bulk read drops the assets now in the collection, the guard admits each resend, and a failed read, a refusal the read cannot explain, any other outcome or the three-request ADD_ATTEMPTS bound stops it; removals and uncertain outcomes are never resent; the result message counts the assets already present, also when the bound stops it), create dedup and the in-session uncertain-name set, one-read create reconciliation by acknowledged ID or exact name, read-back classification, result states, deactivation clearing snapshots and names, and worker cancellation of queued writes. Offline SDK MockTransport unit tests cover these paths, including adapted Studio create-once, later-page dedup and no-replay cases, a member added between prepare and apply, every target already a member, another 400 reason, an unexplained refusal, a failed read after the refusal, repeated concurrent adds capped at three requests that still count the assets already present, a guard failure and an uncertain outcome before or on the resend. The synthetic service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave by the hosted Scenario MCP. No live collection, tag or bulk request was made from this repository; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No native Library or local MCP control, desktop interaction or release acceptance is claimed.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "c4dce8d26afc21078f0cf18f4d980f816a64747d2df9648a54c64e58a0edd84e",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/core/jobs/coordinator.py": "756f6e4fbbacd158ce3527ac251cd878514008ff800c225038225dd8f49eb4a8",
      "scenario/core/jobs/workers.py": "b51f30678c5a94649ee6838e82e128bcce591bc231267acfe1ec5d0f40337418",
      "scenario/core/api/sdk_adapter.py": "43eb582d077677e2975c21e13cd3164b319c96f14a36988c6b9f04ca56124121",
      "tests/unit/test_asset_organization.py": "0c71682a9e02a2d1a4f0f197f214861302eb70046c841ceb42264b4c3c33b5cb",
      "tests/unit/organization_service.py": "0db133ded5cf6c9c105ad5f7ac55d9d5d5b32f77d5b57007d5bc72e627808222",
      "tests/unit/test_job_coordinator.py": "6915564ac4b7ee0d34ae40afcc916527ad43a0007734964d2ba8fe960f4b033a",
      "tests/unit/test_job_workers.py": "c7f1bbc64151d9633a3829478d27377791ddbea58a2b57113a1e140f856c46f0"
    }
  }
}
---

# Asset organization commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md#asset-organization-commands).
