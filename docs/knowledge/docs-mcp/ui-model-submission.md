---
{
  "type": "Evidence",
  "id": "docs-mcp.ui-model-submission",
  "title": "Shared native model quotes and durable submission",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "ui-model-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "6fa30d06b43c6d3ce4e903b45e8635034e4ecb39",
    "limits": "Inspected native form quote routing, original-lane completion, exact single-use submission and rejection of unfinished file/capture/Spark inputs. Six new native tests cover UI/MCP payload parity, lane isolation, all-form button readiness, repricing, changed inputs/origins, durable uncertain responses after restart and no implicit preparation. The same exact ZIP passes 540 offline native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Transport and credentials are synthetic. Desktop keyboard/generation interaction remains unverified for this change. Render capture/Spark preparation, implicit mesh export, Film and non-image result application remain separate integration; render forms cannot generate until preparation is integrated. No live provider acceptance or release approval is claimed.",
    "sources": {
      "scenario/blender/generation.py": "25be4fd22b111959901bfcbdb97eb291a6a5c26d294150b9133b80af06776049",
      "scenario/blender/model_jobs.py": "505277706caf7b036024b57db64bd5ca96e783c3ee53a1e6ead9f44cc030ca21",
      "scenario/mcp/tools_scenario.py": "db57a9eadb551da40b4ada0cc0b8017c1e2cb238b734beff3b216a93429f4103",
      "tests/blender/test_model_generation.py": "a9d65eaa9fd48558b55b838f3e2911533c9d238e6db8c16884b09a8a6429766a",
      "scenario/blender/panels.py": "abd2f5971abdb9314d7f06cf94645218484a3d5dfd273371b25492efa283e175"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
