---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.cloud-history-recovery",
  "title": "Shared cloud history recovery entry points",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "cloud-history-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Native history and MCP share explicit cloud-job adoption, bounded/deduplicated reads, paused saved views and destination approval. Legacy cache files cannot dispatch import or hide recovery controls. The exact package passes 760 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic desktop input on macOS arm64 Blender 5.1.2 proves native save, disabled pending control, delivery after sidebar closure, repeat inspection, explicit retry after a rejected read, viewport selection and Home keyboard framing, with no submission, download or scene content change. External Python sockets are blocked; disposable profiles are removed and the normal profile stays unchanged. No live cloud refresh, provider latency, completed result application, other OS/DPI or integrated release acceptance; no prototype migration.",
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
      "docs/images/cloud-history-recovery-controls.png": "70b35ac53d4c848d9ed4ed92dde79ff8c553551bc61d5bf13cb7934d6da934ac",
      "docs/images/cloud-history-recovery-saved.png": "af4f05fa7c5acdd9eda18770b770d7b46c0d49d8e7025a7e24a5011ed3b14445"
    }
  }
}
---

# Shared cloud history recovery entry points

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
