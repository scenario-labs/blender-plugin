---
{
  "type": "Evidence",
  "id": "docs-known-limitations.uncertain-submissions",
  "title": "Uncertain submission recovery limits",
  "description": "No automatic reconciliation of uncertain submissions; cloud recovery for completed model jobs only.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "uncertain-submissions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the uncertain-submission entry against source and tests. A lost submission response moves the saved job to the uncertain state, which only a stored remote job ID can leave; saved-job views mark it unconfirmed and expose no action, and prompt helpers refuse another request for that field. Cloud history lists only custom model jobs, Save for recovery and local MCP recover_cloud_job adopt only a successful custom or inference job whose model ID matches, and adoption matches existing records by remote job ID, so the uncertain record stays unconfirmed beside the recovered one. Workflow and Prompt Spark job types are neither listed nor adoptable, so they have no in-Blender recovery. Documentation-only review: no native, desktop, live provider or paid run; the Scenario web app's presentation of workflow and prompt-helper jobs was not inspected.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "a8b7efb39e74a1a34f350ff7274e2e714a06933383743744dd22e6e1b7d7096d",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/core/jobs/results.py": "0cf7831eef38f0babd6cba539e0ba93a802f70faf5b53eb44ac34aff7ba98028",
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/prompt_jobs.py": "8fc6c9b949806c086e8595a0aa6221bb217cc3d3b32c92a7e7eb9cabc4714313",
      "scenario/blender/workflow_controls.py": "fed4151d8476ead8c14de00ca3a30e7da3c814b55fd060b43b8f60c6db62ba78",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/unit/test_cloud_job_recovery.py": "6663d26d37a13fba59d3c9e74579e84be0b39a264f4a2f4ee2d243b138da1499",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52",
      "tests/blender/test_workflow_commands.py": "dcae5af50aa9e4530d734d84e578bf417c0816f14a98fac1b33e830161bb3e85",
      "tests/blender/test_prompt_tools.py": "edbc16f517593a051a20e5aa5c8e57095fa64ddd3691ba6bc3acc59d9b064f1c"
    }
  }
}
---

# Uncertain submission recovery limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
