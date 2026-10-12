---
{
  "type": "Evidence",
  "id": "docs-ui-style.experimental-status",
  "title": "Explicit experimental status for Film and unaccepted capabilities",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "experimental-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed the Film sidebar header marker (registered draw_header_preset), the Studio Film page line drawn on every Film sub-page, and the read-only 'not accepted' status for audio2txt/video23d models from a bpy-free helper in the picker's highlighted-model box and the shared persistent Model row used by the sidebar and Studio lanes, Render Image/Video and Edit 3D. The viewport composer's model chip does not show it. These models can be submitted and results stay in saved jobs; provider behavior and result handling are not accepted. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned model (GLB, glTF, FBX, OBJ or mesh PLY) or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Installed native tests assert the registered header preset draw call, the Studio line, the picker status and Model row presence/absence with read-only drawing (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established. A scoped re-inspection for the shared saved-job descriptor refactor found that tests/blender/test_studio_view.py only gains a separate Studio Jobs/Results drawing test; the Film page test and these claims are unchanged. The review date and earlier evidence are unchanged. On 2026-10-10 the generic-import wording was rechecked for saved model package import: ModelJobs.actions offers import_model for importable GLB, glTF, FBX, OBJ and mesh PLY units, and the estimate_cost/generate descriptions and their unit contract now say a returned model or media file. Other claims and the review date are unchanged. Scoped 2026-10-11 check of the native first-frame control, not a full re-review: render_lanes._draw_first_frame only adds a read-only From a saved result label under a Render Video first-frame slot with intact saved-result provenance, and render_lanes.first_frame_route_lines now supplies the two route lines it already drew for an exclusive first frame; the drawing this topic covers is unchanged. The claims above still hold; the review date and base revision are unchanged. A scoped re-inspection for the compact composer job strip, not a full re-review, covered every change to two sources since their previously recorded fingerprints: scenario/blender/studio.py gains the Film Review sub-page from #364 (its FILM_PAGES and FILM_PANELS entries and the wider Film page description) and moves the popup region registration into track_popup, which the composer's job card shares; tests/blender/test_studio_view.py gains the Film Review page drawing test from #364 and patches the composer modal's geometry hook instead of its layout. draw_view still calls film.draw_experimental before dispatching any Film sub-page, so the Studio Film line now also covers Review, and test_film_page_marks_every_film_tab_experimental iterates FILM_PAGES, including REVIEW; both tests passed in the installed native suite (1,579 tests with 3 Windows-only skips on macOS arm64 Blender 5.1.2 only). film.draw_experimental itself is unchanged, but the other #364 changes to scenario/blender/film.py are not re-reviewed here and its fingerprint stays as recorded. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "scenario/blender/film.py": "ac0efa854242bdacff54711eba99aabb2f86f842e073bffe53669702606239d8",
      "scenario/blender/studio.py": "b674510e46115ccf72131903ba416d8c6349641ad8b0190a8550942b7a6b3469",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/panels.py": "bed7253191c6652514967c599590ec667aa67790a726880a5cfc1fd4ed46877e",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7",
      "scenario/blender/composer/draw.py": "db9ce841a722d8b7761786bd1ea44c6a1d7e189ce0673560d5e604f35a78c0cf",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "tests/unit/test_capability_status.py": "9b193ceca20c160ba7d49ba8bc5fa7310d08274ecebe52c3fc74f205567d9e53",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "e6957b4833c926354e3ca53468f9088e81c6d6cd8f96b42f4c5c96f477ddc3b0",
      "tests/blender/test_model_picker.py": "2db431d736b07a17576cdf167b464f677042f5e7b9b3b87bb7f5ee73b514b2ca"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
