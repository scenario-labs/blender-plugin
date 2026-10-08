---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-composition-controls",
  "title": "Shared Film composition review and master submission",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-composition-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Inspected bounded review ownership, original recipe/scene guards, native/MCP exact-price approval, cancellation, uncertain preparation/submission and declared master recovery discovery. Installed synthetic tests cover command and draw behavior. Isolated macOS arm64 Blender 5.1.2 desktop input on ZIP 6f932e81a802f8569378c38ad3d4b820da779a1f86090272585c9b1db8e1335f verifies preparation cancellation, discard confirmation, exact-price display, Final/Previs navigation preserving the quote, frame-change invalidation, error details, generation confirmation/cancellation, one mocked durable master retained after discard and viewport interaction. SDK transport and media metadata were mocked; external socket/DNS calls were disabled. The normal profile stayed unchanged and the isolated profile was removed. No real media probing, live provider/media acceptance, other OS/DPI, local final assembly/export or complete release acceptance is established. Existing SDK/session ownership and recipe/scene guards are unchanged. Only this composition controls topic was reviewed. Native scene-context switching and deleted/recreated scene tests cover independent temporary mode navigation without scene revision changes. MCP cancellation runs before delivery of a finished probe or estimate. Fresh physical two-window input for these follow-up paths remains pending.",
    "sources": {
      "scenario/blender/film_composition.py": "de10d93d86735f2ed2b66290a3e78d1e750469beb77dd6cb688baac4f0ca4933",
      "scenario/blender/film_composition_controls.py": "b5c4a7a754564a0817be2518f39d4c21279a2e79207a7a0131082fa930d2b782",
      "scenario/blender/film.py": "389330d71a30d680ba760c8ad160f85de5b027aba8f3dbe745e606da1ed1db19",
      "scenario/blender/film_jobs.py": "f8ae6ddc89e2f56142f3eda7bb59966cf4c193c17f4b5cfc50c125c83e4ac708",
      "scenario/blender/model_jobs.py": "1c71898d7ab1c1f0c980d1e1bcb7afe07d6d1427f0dbb187d505e5f8b3806226",
      "scenario/mcp/tools_scenario.py": "6e3de6fb086a2d7d266934d43ec5e2da05c690de1b3677e7f4dc182a05cbd817",
      "tests/blender/test_film_composition_controls.py": "2d7b403e23e0aa39cfa02144185cf7eda4df6ae8d0acfe27a20a2c5f640a3dcf",
      "tests/blender/test_mcp_contracts.py": "fc1725b294eb7d326b8e182f513e468841fe91ebb9222f22941254d8be5de251",
      "tests/unit/test_mcp_descriptions.py": "1d2c6708e0b9f3b36639fffd5251ecd2ee0543d398e81ddb2e995216146df374"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
