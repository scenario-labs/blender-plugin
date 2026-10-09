---
{
  "type": "Evidence",
  "id": "docs-ui-style.model-description-status",
  "title": "Model description loading, failure and retry",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "model-description-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Source-reviewed form, composer note, Retry loading model, offline refusal and MCP description reads for lanes without a schema. Native tests patch online access, the catalog and the background read; drawing is checked with a recording layout, not screenshots. The SDK catalog rejects unparseable form schemas before caching. Exact ZIP 6e4accda55132b60b56fd3692e89a72ad75fb4f660de34a03d31709493072eb3 passes 1159 installed tests on macOS arm64 Blender 5.1.2 only. This does not establish live Scenario failures, desktop focus or interaction, Blender 5.0 or 5.2 runs, or release acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "adc94a2a625889b8d0f7561b17a349131d18c794218b07cc1d7007358d495ed4",
      "scenario/blender/generation.py": "1f3f61dba20e3c3b891801440cf8b02f5d89ae1209288b32acaf639affd14c4c",
      "scenario/blender/panels.py": "bd37c935cac097e50258f772cc38ba2fb1f4b69e089c08d0a28261b32322a5f2",
      "scenario/blender/render_lanes.py": "ccf9178bc587f97a79c7d663311f0d3622f8d19e32ede912000b4198cc7d43aa",
      "scenario/blender/operators.py": "41a8a513e4adec195e56794c7430078a95a46ddc1c48e2e682a24d2ff656512f",
      "scenario/blender/composer/draw.py": "77b2f8b213f8db6d7f0eb99ece44ee431cd345a3302bf771f750747bf8be867f",
      "scenario/blender/runtime.py": "43003d6a75ea5b11f2459ba56d39db94d43359a1cd1564765a10471d7979889e",
      "scenario/core/api/sdk_catalog.py": "d2405048078890ff64037a359281ec1413cfd114e8bc599aa9bc29889f9638d3",
      "scenario/core/jobs/manager.py": "f79ea01367faf949a139d7daaeb55ff47e58d86cc98fd58e5ed3c6bcfd6183ab",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "tests/blender/test_generation.py": "003ce425848eb8eb3fc15d0a28e724bebe31ed78ddef69a925e0838df61e4ae5",
      "tests/unit/test_sdk_catalog.py": "332f4adfe0a83aac06e9512273b91b1276a2a8b7384b53bc2cb88290254ee67e",
      "tests/unit/test_catalog_delivery.py": "f1359ecdaff5b7b1eee25406bcc320de657273ed62d115c6c549e843d06e0ac3"
    }
  }
}
---

Supports [the model chooser](../../UI_STYLE.md#the-model-chooser) rules for a form whose model description is loading, failed, unrequested or blocked by disabled online access.
