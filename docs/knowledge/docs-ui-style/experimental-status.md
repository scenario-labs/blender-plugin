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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Film sidebar header marker (registered draw_header_preset), the Studio Film page line drawn on every Film sub-page, and the read-only 'not accepted' status for audio2txt/video23d models from a bpy-free helper in the picker's highlighted-model box and the shared persistent Model row used by the sidebar and Studio lanes, Render Image/Video and Edit 3D. The viewport composer's model chip does not show it. Generation works and results stay in saved jobs. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned GLB or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Installed native tests assert the registered header preset draw call, the Studio line, the picker status and Model row presence/absence with read-only drawing (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/core/ui/capability_status.py": "2fd4bae1adc9c9d96ecdc6f165635fa91487a0154f48d028729f5c07550d05b8",
      "scenario/blender/film.py": "ac0efa854242bdacff54711eba99aabb2f86f842e073bffe53669702606239d8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_picker.py": "c949fbdf60dd4f5c7c911e806e3335e7502dd63086d5a1d40d54231c9dd5f1bc",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/render_lanes.py": "812bee11a5c33b3d3f9467303d3ed8f8523dddebfd0ebc69ae78cc6ad8655c3b",
      "scenario/blender/composer/draw.py": "05d1bdd0ef55ac78775207822ea0696daeb2c3934395b3b20d21dd83bb0b9128",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "tests/unit/test_capability_status.py": "54a9ad8b7cf5a1d184bcde5d391f0ed704ba466c088f96cdd0179ee8ae213827",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "1e763f4c22eecaece1be36def00d565460d68dd424f4aad6c09ee8b90db16625",
      "tests/blender/test_model_picker.py": "a9650ac1310cc8d4d044815b4e63aa35d1574a9acf421bafeb76b77e6f8b69fe"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
