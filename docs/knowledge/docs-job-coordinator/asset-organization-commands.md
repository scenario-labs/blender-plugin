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
    "reviewed_at": "2026-10-12",
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed request validation and normalization, including the 200-entry raw and 30-unique tag bounds and refusals naming the limit each enforces, scope refusal before any request, snapshot reads (get_bulk, collection retrieval, bounded exact-name lookup), weakly held single-use issued snapshots, the guard before every write and never after the last, membership and per-asset tag writes, continuation after definite rejections, stopping at the first uncertain, offline or guard failure, the bounded resend after an AlreadyMembers add refusal (one get_bulk read drops the assets now in the collection, the guard admits each resend, and a failed read, a refusal the read cannot explain, any other outcome or the three-request ADD_ATTEMPTS bound stops it; removals and uncertain outcomes are never resent; the result message counts the assets already present, also when the bound stops it, and says the rest were sent again only when a resend reached the service), create dedup and the in-session uncertain-name set, one-read create reconciliation by acknowledged ID or exact name, read-back classification, result states, deactivation clearing snapshots and names, and worker cancellation of queued writes. The closing sentence was re-reviewed: the local MCP tools and the native Library controls use these commands only through the JobSession reviews. Offline SDK MockTransport unit tests cover these paths, including adapted Studio create-once, later-page dedup and no-replay cases, a member added between prepare and apply, every target already a member, another 400 reason, an unexplained refusal, a failed read after the refusal, repeated concurrent adds capped at three requests that still count the assets already present, a guard failure and an uncertain outcome before or on the resend, and a resend stopped by disabled online access before dispatch. The synthetic service refuses a re-add or more than 49 IDs as one 400 that writes nothing, as the service was observed to behave by the hosted Scenario MCP. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Rechecked against the current Library view, including the card under the organized row, read-enabled controls, a settled card kept after an eviction, read-back kept across a running page or collection read and Apply refused while an agent's change applies, and against the owner's collection page slot fix: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged.",
    "sources": {
      "docs/JOB_COORDINATOR.md": "6111a04079ffc4e011d2b800a78c5b3f0f85f249d13c0ab0a3d7bcff15e60573",
      "scenario/core/jobs/organization.py": "64c7cc990c8720827769d8d4ef0adc4715dfd2893c776c15639b7a5a85d186f3",
      "scenario/core/jobs/coordinator.py": "54e97b2ff7a51e563dfff542ccf0f579ce2324393491840bf10efb78939307e9",
      "scenario/core/jobs/workers.py": "2127fde9e058254ccd165426cbfc8166da2813b3e598309c9000becf9565f6d6",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/mcp/tools_scenario.py": "c3597642a8199cde05d1346120532681f7138572e3edf523fa3788489b5f3b3c",
      "tests/unit/test_asset_organization.py": "095cea215498e2e6ca6ba987ed06b7bcfd2a877a0d0c475463c9b9cb4f3f7a93",
      "tests/unit/organization_service.py": "0db133ded5cf6c9c105ad5f7ac55d9d5d5b32f77d5b57007d5bc72e627808222",
      "tests/unit/test_job_coordinator.py": "6915564ac4b7ee0d34ae40afcc916527ad43a0007734964d2ba8fe960f4b033a",
      "tests/unit/test_job_workers.py": "e97f74acc0cdec529e8a05f75df683c0317d45cd47701214396344ebc60a7da8",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f"
    }
  }
}
---

# Asset organization commands

Evidence for [the canonical guide](../../JOB_COORDINATOR.md#asset-organization-commands).
