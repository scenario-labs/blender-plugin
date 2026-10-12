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
    "limits": "Reviewed that Film shows a visible experimental status in its sidebar header (registered draw_header_preset), on every Studio Film page and in every Film MCP tool description, without hiding or blocking any Film control or command. Installed native tests assert the header preset draw call and the Studio line; an offline unit contract checks every Film tool description (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). This does not establish a Film generation journey or satisfy the release gate. Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. A scoped re-inspection for the shared saved-job descriptor refactor found that tests/blender/test_studio_view.py only gains a separate Studio Jobs/Results drawing test; the Film page test and these claims are unchanged. The review date and earlier evidence are unchanged. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged. On 2026-10-10 the test_mcp_descriptions.py fingerprint was refreshed after a splat option parity test was added; the experimental status assertions are unchanged, and the review date is unchanged. A scoped re-inspection for the compact composer job strip, not a full re-review, covered every change to two sources since their previously recorded fingerprints: scenario/blender/studio.py gains the Film Review sub-page from #364 (its FILM_PAGES and FILM_PANELS entries and the wider Film page description) and moves the popup region registration into track_popup, which the composer's job card shares; tests/blender/test_studio_view.py gains the Film Review page drawing test from #364 and patches the composer modal's geometry hook instead of its layout. draw_view still calls film.draw_experimental before dispatching any Film sub-page, so the Studio Film line now also covers Review, and test_film_page_marks_every_film_tab_experimental iterates FILM_PAGES, including REVIEW; both tests passed in the installed native suite (1,579 tests with 3 Windows-only skips on macOS arm64 Blender 5.1.2 only). film.draw_experimental itself is unchanged, but the other #364 changes to scenario/blender/film.py are not re-reviewed here and its fingerprint stays as recorded. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/film.py": "ac0efa854242bdacff54711eba99aabb2f86f842e073bffe53669702606239d8",
      "scenario/blender/studio.py": "b674510e46115ccf72131903ba416d8c6349641ad8b0190a8550942b7a6b3469",
      "scenario/mcp/tools_scenario.py": "fecde250ae186fbbc35bc55ff610c75a32457c0bef14e14de6a80499dd26ab70",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "e6957b4833c926354e3ca53468f9088e81c6d6cd8f96b42f4c5c96f477ddc3b0",
      "tests/unit/test_mcp_descriptions.py": "16f9e558e9abc040e080dd0ba1157ac57bd8a534a0f710247f5e8e5d007d0c02"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
