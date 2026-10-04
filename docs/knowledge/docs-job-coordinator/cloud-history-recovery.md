---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.cloud-history-recovery",
  "title": "Shared cloud history recovery entry points",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "cloud-history-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Native history and MCP share explicit cloud-job adoption, bounded/deduplicated reads, paused saved views and destination approval. Legacy cloud cache files cannot dispatch import or hide recovery controls. Synthetic installed functional tests and a macOS Blender 5.1.2 rendering check; mouse/keyboard/focus interaction remains pending because computer control cannot locate the isolated window. No paid/live provider or integrated release acceptance, no prototype registry migration.",
    "sources": {
      "scenario/blender/model_jobs.py": "5152fda72e78e3a11ed45dbda38251659caa1c8c116be568b77170d2cf78906d",
      "scenario/blender/generation.py": "d19a174a7e3e362d384ab04ff31233571688a48dadafcfe70f21f6db6d4e669f",
      "scenario/blender/operators.py": "4de1ebb739f8163d9a2d1cec4052290a7bde372e40972f17517c6cd3029ddab1",
      "scenario/blender/panels.py": "a6d70fce03b372a471bd004542c954d220b01cab5da962cf60e1799c572fc798",
      "scenario/mcp/tools_scenario.py": "1f0cf79f3205c4f6972a87c8704d5f0faecfccb177fbf6edbbdb1c61681dca0d",
      "scenario/blender/job_session.py": "72dbb693cc852bb2e123aad6e2af5b3772449c446456c7eca678245a17188dc9",
      "scenario/core/jobs/coordinator.py": "70788f976e8fe429f594525e09e00f97833b9f09840fd69eb4446fa83e932eb2",
      "tests/blender/test_model_generation.py": "62c746c033870326e34fc11880d5eea0ae2c595423af297657302486ab8c54d4",
      "tests/blender/test_sdk_history.py": "78584d9ce3217b28f82e1ca9e2cc870b1470a444c7ee98a39cc59b3f2b8369e4",
      "tests/blender/test_mcp_contracts.py": "9917e64d6283f12a070d6c22619bf2628bfb6aeebdd86f87d61f3b6d5a5dda83",
      "tests/unit/test_mcp_descriptions.py": "26de29defdfc81f1766e9308c2c2867fdfaecbd354104856436c07b53b36ba42",
      "docs/images/cloud-history-recovery-controls.png": "8c65cab03dfcd2040f98e5232f0581d2985d84356cadbc3ad74ad374b68cc294"
    }
  }
}
---

# Shared cloud history recovery entry points

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
