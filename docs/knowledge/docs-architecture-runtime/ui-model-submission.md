---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.ui-model-submission",
  "title": "Shared native model quotes and durable submission",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "ui-model-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "6fa30d06b43c6d3ce4e903b45e8635034e4ecb39",
    "limits": "Inspected native form quote routing, original-lane completion, exact single-use submission and rejection of unfinished file/capture/Spark inputs. Seven new native tests cover UI/MCP payload parity, lane isolation, all-form button readiness, repricing after 130 real form edits without losing other UI/MCP approvals, changed inputs/origins, durable uncertain responses after restart and no implicit preparation. The same exact ZIP passes 541 offline native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Transport and credentials are synthetic. Desktop keyboard/generation interaction remains unverified for this change. Render capture/Spark preparation, implicit mesh export, Film and non-image result application remain separate integration; render forms cannot generate until preparation is integrated. No live provider acceptance or release approval is claimed.",
    "sources": {
      "scenario/blender/generation.py": "7eb9d9690d6d7e578ab37a7d3dce8464d481c7cd4e13fc069f23b2413fb1dfb1",
      "scenario/blender/model_jobs.py": "505277706caf7b036024b57db64bd5ca96e783c3ee53a1e6ead9f44cc030ca21",
      "scenario/mcp/tools_scenario.py": "db57a9eadb551da40b4ada0cc0b8017c1e2cb238b734beff3b216a93429f4103",
      "tests/blender/test_model_generation.py": "f8cf1a696fe12932007aaeeb3241e645d73d0280bc34fe30212ca64b1da531e9",
      "scenario/blender/panels.py": "abd2f5971abdb9314d7f06cf94645218484a3d5dfd273371b25492efa283e175"
    }
  }
}
---

Source evidence for [the canonical guide](../../architecture/runtime.md).
