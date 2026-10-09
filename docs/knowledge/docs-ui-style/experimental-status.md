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
    "limits": "Reviewed the Film sidebar header marker (registered draw_header_preset), the Studio Film page line drawn on every Film sub-page, and the read-only 'not accepted' status for audio2txt/video23d models from a bpy-free helper in the picker's highlighted-model box and the shared persistent Model row used by the sidebar and Studio lanes, Render Image/Video and Edit 3D. The viewport composer's model chip does not show it. These models can be submitted and results stay in saved jobs; provider behavior and result handling are not accepted. ModelJobs.actions and prepare_result_application offer generic import by file type, so a returned GLB or media file may import, but speech-to-text and video-to-motion handling is not accepted (#190). Installed native tests assert the registered header preset draw call, the Studio line, the picker status and Model row presence/absence with read-only drawing (1,154 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Display-only status; no model, Film task, estimate or approval is hidden or blocked. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/core/ui/capability_status.py": "2fd4bae1adc9c9d96ecdc6f165635fa91487a0154f48d028729f5c07550d05b8",
      "scenario/blender/film.py": "ac0efa854242bdacff54711eba99aabb2f86f842e073bffe53669702606239d8",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_picker.py": "951e3b936dcb76070987f18ce7886c3f2eb3f94740f860926014e867830944f6",
      "scenario/blender/panels.py": "bed7253191c6652514967c599590ec667aa67790a726880a5cfc1fd4ed46877e",
      "scenario/blender/render_lanes.py": "ccf9178bc587f97a79c7d663311f0d3622f8d19e32ede912000b4198cc7d43aa",
      "scenario/blender/composer/draw.py": "2514a1ae064493dae895b60704dc3d0795467b7a819400053cbcc19e53032719",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "tests/unit/test_capability_status.py": "54a9ad8b7cf5a1d184bcde5d391f0ed704ba466c088f96cdd0179ee8ae213827",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "1e763f4c22eecaece1be36def00d565460d68dd424f4aad6c09ee8b90db16625",
      "tests/blender/test_model_picker.py": "2db431d736b07a17576cdf167b464f677042f5e7b9b3b87bb7f5ee73b514b2ca"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
