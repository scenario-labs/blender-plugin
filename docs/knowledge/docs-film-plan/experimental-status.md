---
{
  "type": "Evidence",
  "id": "docs-film-plan.experimental-status",
  "title": "Explicit experimental status for Film and unaccepted capabilities",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "experimental-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed that Film shows a visible experimental status in its sidebar header (registered draw_header_preset), on every Studio Film page and in every Film MCP tool description, without hiding or blocking any Film control or command. Installed native tests assert the header preset draw call and the Studio line; an offline unit contract checks every Film tool description (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). This does not establish a Film generation journey or satisfy the release gate. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/blender/film.py": "ac0efa854242bdacff54711eba99aabb2f86f842e073bffe53669702606239d8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/mcp/tools_scenario.py": "b1226d92dd5b5aba2be56a4e3079d437ec93a865b63ba5a911d1338962115d42",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "1e763f4c22eecaece1be36def00d565460d68dd424f4aad6c09ee8b90db16625",
      "tests/unit/test_mcp_descriptions.py": "b568866568aa4d33840106780e3483494217deb0e5c1cc95a271f94d7fbf9b35"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
