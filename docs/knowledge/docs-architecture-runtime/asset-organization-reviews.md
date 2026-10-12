---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.asset-organization-reviews",
  "title": "Shared asset organization reviews in the runtime map",
  "description": "Where organization reviews sit in the shared runtime, which surfaces use them and what they leave open.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "asset-organization-reviews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "3acb9625dc28bc74a6b764163ce6a6ca27144528",
    "limits": "Reviewed the runtime-map claims: the pure bpy-free contract, including guarded writes that are never resent after an uncertain outcome (the one bounded resend after an already-member add refusal is described in the command contract), coordinator and worker execution through the selected adapter, the session-owned entry point, pump polling independent of an open view (which also discards a finished collection page nobody takes within the review lifetime, so an abandoned read holds no admission slot), connection-scoped session-local reviews kept across undo and scene switches and retired on file load or credential or project change, no job, upload or store schema change and no spending, that the local MCP tools prepare, apply and inspect these reviews, and that the native Library uses the same owner. The library-reads paragraph points to these reviews. No live collection or tag write was made from this repository, and a desktop pass on an earlier candidate made reads only; the observed already-member 400 and one-transaction add, service name uniqueness, DELETE body survival, tag normalization and live limits remain unverified here. No desktop interaction or release acceptance is claimed. Rechecked against the current Library view, including the card under the organized row, read-enabled controls, a settled card kept after an eviction, read-back kept across a running page or collection read and Apply refused while an agent's change applies, and against the owner's collection page slot fix: the view still prepares, applies and discards only through the shared owner, sends nothing new and draws read-only, so these claims are unchanged.",
    "sources": {
      "docs/architecture/runtime.md": "4fd8326ed4eefb6766088348d7229ab5a02650457dfe1bd800e8b42bd0f241b5",
      "scenario/core/jobs/organization.py": "69ad48086ff2b763c565a22bce2bf60e142afbc10e757c56d938daf2198fbeba",
      "scenario/blender/asset_organization.py": "2cddba739852c4f914398b8c9fd1d98029122fdb468aab61456268183f1fc75f",
      "scenario/blender/job_session.py": "f065103af678936bdd575474698ae7d36cea79f4269ae668fb5d7acd865ddddf",
      "scenario/blender/runtime.py": "5ff43fb59215fed469c0638a660a679a6c15fd63a0148169031e01a4b6dfcfd7",
      "scenario/mcp/tools_scenario.py": "c3597642a8199cde05d1346120532681f7138572e3edf523fa3788489b5f3b3c",
      "tests/blender/test_organization_session.py": "58804761b378747da91cb6e088b8e68ecdd4b6ce355b69f55892c5299383f450",
      "tests/blender/test_asset_organization.py": "b00e136dfcf7667b1d93bb54b3efc84c1643380e88e8524ea12238edb6e793d5",
      "scenario/blender/library_view.py": "8f69ff39c990e3cc6cffd2c5980397c8d1b68241bf6f31d58885d52ca6fc0254",
      "tests/blender/test_library_organization.py": "4422a822b32be3bb3e48b34318ebe2f69db471f943a970f09af5c5af6d832b70"
    }
  }
}
---

# Shared asset organization reviews

Evidence for [the canonical guide](../../architecture/runtime.md#shared-asset-organization-reviews).
