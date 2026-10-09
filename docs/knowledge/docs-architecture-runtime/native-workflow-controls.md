---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.native-workflow-controls",
  "title": "Native shared workflow input and approval controls",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "native-workflow-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "7e468fb915d91cbdeb0f67de37a61cb1b51aa497",
    "limits": "Reviewed native workflow forms, saved schema/choice reconstruction, shared metadata/quote commands, exact normalized-payload confirmation, scene/form guards and runtime retirement. Installed synthetic tests cover shared UI/MCP approval, single use, input changes, navigation, continuing jobs, form reopen and conditional/default values. Physical input, screenshots, scrolling, DPI, live workflows, integrated reference upload/library selection, interactive nodes and general workflow cancellation remain unverified or unimplemented. Remaining desktop and live acceptance is tracked under #66/#68 separately from review readiness. This does not establish complete issue or release acceptance. No paid or live service calls were made. Review follow-up verifies shared always-required inclusion, idle projection/unused-price reclamation and catalog-only session delivery without weakening form/quote guards. Rebased candidate passes 1,105 installed tests on each supported Blender version and 3,852 unit tests with the known SDK authentication expected failure. Intentional exception handlers now document their recovery boundaries.",
    "sources": {
      "docs/architecture/runtime.md": "53f8a762cc7a7470f9d84b9c1260b77bc058bcf2493879aa165039d2c1bdaadf",
      "scenario/blender/workflow_controls.py": "9f6a20ca93d3a2051183b918b2c791f64a2c8f29bd89b84fe13b92777542849f",
      "scenario/blender/runtime.py": "75fd5dc75d7321b15a070fd634ec9f832cda3f04e65f72fd8425a7436d17d009",
      "scenario/blender/registry.py": "bd10f5774a17555183deb09fc77edf18b0ed524b5b44d147ef0ac1aa5a0dacc5",
      "scenario/blender/studio.py": "5c0829aeed2faaba49ca20e9f87099753876c81f0397e02d4cdaacea1d26b89c",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/job_session.py": "e8878bb6b527d478199b0e4d3023736f2823c5a57204b6ce43e8a5fe924e58f1",
      "scenario/core/schema/forms.py": "f13c662733ae8badc4a16c21f32b545e93c55d8f1dee2c8816cfce8b940df33a",
      "scenario/mcp/tools_scenario.py": "f0d8e6bf2476a81bbf354a6e006e5c49872f9e3772ac729c2806e0f13bd81310",
      "tests/blender/test_workflow_controls.py": "a31c273634e6fdd8bb9e9fb41cc78a7d068f385aaa1fdf8049ab84f260eb61f0",
      "tests/blender/test_workflow_commands.py": "dcae5af50aa9e4530d734d84e578bf417c0816f14a98fac1b33e830161bb3e85",
      "tests/blender/run_all.py": "c5cba1b723a3f76c62a76c87902b24e64ad59d67fa9db3f1342185048dae4519",
      "scenario/core/schema/params.py": "b26c51fbe84dd3eb71a690c39231ff8a332ef42d937b574e3c1102e97d8cd8e7"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
