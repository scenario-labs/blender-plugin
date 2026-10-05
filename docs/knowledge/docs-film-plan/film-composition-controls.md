---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-composition-controls",
  "title": "Shared Film composition review and master submission",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-composition-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "e4da254583900a68da7414e0ac2744656831e47f",
    "limits": "Inspected bounded review ownership, original recipe/scene guards, native/MCP exact-price approval, cancellation, uncertain preparation/submission and declared master recovery discovery. Installed synthetic tests cover command and draw behavior. Isolated macOS arm64 Blender 5.1.2 desktop input on ZIP 6f932e81a802f8569378c38ad3d4b820da779a1f86090272585c9b1db8e1335f verifies preparation cancellation, discard confirmation, exact-price display, Final/Previs navigation preserving the quote, frame-change invalidation, error details, generation confirmation/cancellation, one mocked durable master retained after discard and viewport interaction. SDK transport and media metadata were mocked; external socket/DNS calls were disabled. The normal profile stayed unchanged and the isolated profile was removed. No real media probing, live provider/media acceptance, other OS/DPI, local final assembly/export or complete release acceptance is established. Existing SDK/session ownership and recipe/scene guards are unchanged. Only this composition controls topic was reviewed.",
    "sources": {
      "scenario/blender/film_composition.py": "de10d93d86735f2ed2b66290a3e78d1e750469beb77dd6cb688baac4f0ca4933",
      "scenario/blender/film_composition_controls.py": "b5c4a7a754564a0817be2518f39d4c21279a2e79207a7a0131082fa930d2b782",
      "scenario/blender/film.py": "06796510e036744cf87d24e5c48a3708c3cf9f729d353d40130bfa627ab980a9",
      "scenario/blender/film_jobs.py": "f8ae6ddc89e2f56142f3eda7bb59966cf4c193c17f4b5cfc50c125c83e4ac708",
      "scenario/blender/model_jobs.py": "1c71898d7ab1c1f0c980d1e1bcb7afe07d6d1427f0dbb187d505e5f8b3806226",
      "scenario/mcp/tools_scenario.py": "bb4b40a7c3245777f1dbc79e44419211f6375f525a8830ea5ceaf6daa7a588fe",
      "tests/blender/test_film_composition_controls.py": "16efcf94b53e5dd85a661c4b34a2967afe066ba745cb0a30f1906c8f33998bab",
      "tests/blender/test_mcp_contracts.py": "fc1725b294eb7d326b8e182f513e468841fe91ebb9222f22941254d8be5de251",
      "tests/unit/test_mcp_descriptions.py": "1d2c6708e0b9f3b36639fffd5251ecd2ee0543d398e81ddb2e995216146df374"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
