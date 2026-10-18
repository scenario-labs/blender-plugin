---
{
  "type": "Evidence",
  "id": "docs-model-payload-audit",
  "title": "docs/MODEL_PAYLOAD_AUDIT.md evidence",
  "evidence": {
    "path": "docs/MODEL_PAYLOAD_AUDIT.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-18",
    "reviewed_revision": "04c30c3b7815ff8983a59c0e37a05608db23455e",
    "limits": "Source-reviewed against the audit tool, API contract workflow, failure reporters and SDK adapter. No live audit, workflow dispatch or Scenario call; hosted scheduling and issue reporting were not re-run.",
    "sources": [
      ".github/workflows/api-contract.yml",
      "docs/MODEL_PAYLOAD_AUDIT.md",
      "pyproject.toml",
      "scenario/blender_manifest.toml",
      "scenario/core/api/catalog.py",
      "scenario/core/api/sdk_adapter.py",
      "scenario/core/schema/forms.py",
      "scenario/core/schema/params.py",
      "scenario/sdk-wheel-lock.json",
      "tests/blender/test_sdk_bundle.py",
      "tests/fixtures/models/model_hdri-skybox.json",
      "tests/fixtures/models/model_hunyuan-world-image-to-skybox.json",
      "tests/fixtures/models/model_sc-upscale-flux-skybox.json",
      "tests/fixtures/models/model_scenario-skybox-flux.json",
      "tests/fixtures/models/model_scenario-skybox-gpt.json",
      "tests/unit/test_api_contract_workflow.py",
      "tests/unit/test_audit_payloads.py",
      "tests/unit/test_ci_failure.py",
      "tests/unit/test_dev_config.py",
      "tests/unit/test_scenario_sdk_contract.py",
      "tests/unit/test_wheel_bundle.py",
      "tools/audit_payloads.py",
      "tools/dev_config.py",
      "tools/report_api_failure.py",
      "tools/report_ci_failure.py",
      "uv.lock"
    ]
  }
}
---

Evidence for [the canonical document](../MODEL_PAYLOAD_AUDIT.md).
