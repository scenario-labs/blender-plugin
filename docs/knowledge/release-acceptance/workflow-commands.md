---
{
  "type": "Evidence",
  "id": "release-acceptance.workflow-commands",
  "title": "Shared local workflow commands",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "workflow-commands",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "d18a95212410a8babc37145b4ff2007e5e2cc011",
    "limits": "Scoped source review of local workflow catalog/schema, exact quote approval, operation-bound durable dispatch and saved-result lifecycle. Installed tests use synthetic SDK responses and real scoped stores. No live upload, paid submission, provider output acceptance, interactive workflow node support, general workflow cancellation or expanded Studio presentation is established. Existing candidate evidence is not replaced by this integration slice.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "fbb868b92e2e187c98bd0f1fce57a4250a5599e69d234c8bdcd4c383e6986418",
      "scenario/blender/job_session.py": "c41e1c27f5e987719beab05513627b5aa2c50a7dc3ce05902c6af477083c7b02",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/mcp/tools_scenario.py": "f0d8e6bf2476a81bbf354a6e006e5c49872f9e3772ac729c2806e0f13bd81310",
      "scenario/mcp/protocol.py": "47cf481043f5441db87c6a80de9ad5d815028b3d2ee3197c46309f9c7062c6b3",
      "scenario/core/api/sdk_adapter.py": "28f759aeaa504bdcb435ff26dbf5fe8515b32c49d20b770467157fd0d0012735",
      "scenario/core/jobs/coordinator.py": "026ec2802838c67969dfe54da6fa2a32ae59a28bcc0b5bf587e7831697899a41",
      "scenario/core/jobs/workers.py": "eadc85cd20d670ec4894e6c94544a823e32e78648507efa3021a2c65fe5a5469",
      "tests/blender/test_workflow_commands.py": "1439fa908ec461b0ed2d2314f2e58e918bfd5bdf1b7c35ea682ab3f641c5db5f",
      "tests/blender/test_mcp_contracts.py": "b4bc582d19381db1292f9fc177574e947b4b8160642ae2b48be859c14896e685",
      "tests/unit/test_mcp_descriptions.py": "3be04a896b006a67aaf53348075ddef3dd21129090b840e5e35c9eecfd1ab591",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd"
    }
  }
}
---

Evidence for [the canonical guide](../../maintenance/release-acceptance.md).
