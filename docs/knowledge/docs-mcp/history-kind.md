---
{
  "type": "Evidence",
  "id": "docs-mcp.history-kind",
  "title": "Cloud history row kinds",
  "description": "How list_generations and the history panel name a cloud row's kind before and after the model catalog loads.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "history-kind",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Source-reviewed kind derivation for MCP list_generations and the native history panel: a legacy record's kind, then the media types and texture roles of matching saved results, then the loaded catalog record's most specific lane, else unknown. Unknown rows resolve again against a catalog loaded after the page, without another history read. Unit tests cover the unknown fallback, result media precedence and catalog lane kinds. One installed synthetic native suite passed on macOS arm64 Blender 5.1.2 (1204 tests, 2 skipped); Blender 5.0 and 5.2, other OS and desktop input were not run. No live history page was read: SDK 2.2.0 job rows carry result asset IDs without media types, so rows without a saved record depend on the catalog, and models outside every generation lane, such as text output, stay unknown.",
    "sources": {
      "scenario/core/history.py": "1dac714c48e832ac110ed258d2496f038024eaa01faa7b9b942fc69a20400fa5",
      "scenario/core/api/catalog.py": "42b88d959ed39454a4bd037d3db457271a0a309d9f693c45c3490959d3c7ac9f",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/blender/history.py": "47336db36d8121fa0cf46e0a2414df143e6eb5e555e43633a555bca7448342c6",
      "scenario/blender/panels.py": "ca6ff80a86023b5bd8a73c58646ea7d783f25b6562694f876797fbb22b460996",
      "scenario/mcp/tools_scenario.py": "f4661b9b8d3b26fd2d19198fe6fff206fd00d0c47c70776a29232f3c1c1b347b",
      "tests/unit/test_history.py": "a49be60ab4cf4853c7040a59e02105c60fd1ad5d44ec3831271b41feddad389d",
      "tests/unit/test_catalog.py": "d1359d755dba092dc2c03c82553f6e164a97dae22407b9613d4ee53e44beb9ed",
      "tests/unit/test_mcp_descriptions.py": "97a596acd0cd872b08cd13397a6b5cc76f92bedb96b6f2d6f4e2da6ddafc0553",
      "tests/blender/test_sdk_history.py": "ddeee35853b9599535198ee1ec1586bc0f7bd7aab34c86f64479489d80f3bc65"
    }
  }
}
---

# Cloud history row kinds

Evidence for [the canonical guide](../../MCP.md).
