---
{
  "type": "Evidence",
  "id": "docs-ui-style.workflow-cost-reporting",
  "title": "Workflow loop quote warnings and History workflow totals",
  "description": "Nonblocking one-pass loop quote warnings and documented job and workflow totals in History.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "workflow-cost-reporting",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Source review of ForEach loop detection from the retrieved workflow definition in the shared adapter (unknown for a missing or malformed flow or a nested workflow step), the nonblocking native Generate (from N CU) label and warning, and the MCP loop_steps, quote_may_understate and cost_warning fields on estimate_workflow and run_workflow. The exact quoted string remains the approval value; job_status still reports the approved quote, not the final charge. History rows report billing.cuCost plus cuCostDetails add-ons; workflow runs sum their step charges from metadata.flow job IDs and step workflowJobId, read missing steps on the history worker through jobs.retrieve (24 per page) and report cost unavailable instead of 0. Malformed billing on a listed row still fails the page; drawing performs no reads. Unit and installed synthetic tests cover detection, flags, labels, single submission, sums, missing or malformed steps, cycles, nesting and draw-time reads. Free read-only job list/retrieve calls in a test account's default scope confirmed a workflow job's own cuCost of 0, step add-ons in cuCostDetails and step identity fields, and that a completed three-iteration ForEach run charged its loop step once per iteration; no paid, dry-run or generation request was made for this review. Nested workflow pricing, deleted step jobs, screenshots, physical input and live loop runs were not observed. The exact ZIP with SHA-256 88b130a76f46aa1a0b9024cfb14fd61387ab6bc8d35eda545f101edd9fc43bf2 passes 1,207 installed tests (2 Windows-only skips) on macOS arm64 Blender 5.1.2 only. This does not establish #65 or #68 acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "5e39f5011aed502bdf7010ff410898ef2273d821fc4b8dc10007c16e2614e690",
      "scenario/core/api/sdk_adapter.py": "29677f52ab64dad83cb44ddb166ee4b7ab414fa816f348cc5cda9f4aa6991fd6",
      "scenario/core/ui/costs.py": "1b7d7a47dc07f4bb2cfbf84e1c3310512b93aa89b2154e0ca00b45a4e8c3069b",
      "scenario/core/history.py": "e1af45a8502893026c4e28e2c154fe5cbb730fa07f24610616a95963aa24368e",
      "scenario/core/api/sdk_catalog.py": "3cf31246efc31cd46c9dcd7fbf726512ea4b1eecd42cc0e2881e3d2166f6f4df",
      "scenario/core/jobs/manager.py": "e222802758731753852f46dc4c6d6c14ef56d9ab2b3602b98a5fa7ef291e5ad8",
      "scenario/blender/history.py": "2dee6ead2c4ef24754cce15acf0971b72eb1ce59dd1cbf2eb1f90963023da6b7",
      "scenario/blender/model_jobs.py": "9d439b7072db4d1810262986503b99a7aee82124341672716e33c9e345e030e5",
      "scenario/blender/panels.py": "2ebd594cc3dfd5213d48687530fa715e69801eb1205ac2cfdfa4a201499a8f5f",
      "scenario/blender/workflow_controls.py": "437f27cf870fc8383f6002fbabf31718e79bdec0e5f461ccfcd3232e3391d09b",
      "scenario/mcp/tools_scenario.py": "96e0b5c41f984671c2ec52ccdf32b0df7ff94fa998d437812707861e7a7ea7f2",
      "tests/unit/test_sdk_adapter.py": "9e44272bc3794da0aea4499fc408604cccd8bbee228e2d90f730272cd25d8e6e",
      "tests/unit/test_cu_display.py": "84fa9a0f5d5957e34c5132febc5b6b2d49c645cc62810faf4ed09a5d5829de7f",
      "tests/unit/test_history.py": "bd37632ac5d4ed4a6167157a70e47924fff95413e898fb5c99daa0d7f212ef5a",
      "tests/unit/test_sdk_history.py": "9f26ae998cfcb5f09534ff9c383f66e00a5cf777c63d31862ef5d396090e947f",
      "tests/blender/test_workflow_commands.py": "2fc51568754a8b3ef08435660a94216ea0f8c7a288ff2831ccb3aab471213497",
      "tests/blender/test_workflow_controls.py": "0c8d8b2c74dba7b198dd23bb72d5fcd7d2a5b06cbc6c0c68751eb758638bc919",
      "tests/blender/test_sdk_history.py": "86e10b59e2a01ca0e354268d61ef225ae6d49e33d20f9ee80fc11424de73fe41"
    }
  }
}
---

# Workflow loop quote warnings and History workflow totals

Evidence for [the canonical guide](../../UI_STYLE.md).
