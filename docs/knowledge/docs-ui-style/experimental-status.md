---
{
  "type": "Evidence",
  "id": "docs-ui-style.experimental-status",
  "title": "Explicit experimental status for Film and unapplied capabilities",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "experimental-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Film sidebar header marker (draw_header_preset), the Studio Film page line drawn on every Film sub-page, and the model picker's highlighted-model status for audio2txt/video23d capabilities from a bpy-free helper. Installed native tests assert the drawn labels and read-only drawing (1,152 installed tests passed with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only). Display-only status; no model, Film task, estimate or approval is hidden or blocked. Speech-to-text and video-to-motion result handling remains #190. No paid/live generation, physical desktop interaction, screenshot, other Blender version, other OS/DPI or release acceptance is established.",
    "sources": {
      "scenario/core/ui/capability_status.py": "b331367989bb5fe32b55d594382b8b5e169a0968875a603239b1ddad40d83ed1",
      "scenario/blender/film.py": "52e3218efd2529738d885921d87b64580c1ea5828da513a1d5e3b2288b75ce0d",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8",
      "scenario/blender/model_picker.py": "30ca6f6fb5e0f245c5a96036bdc6bfba30e565f6203697d70ac478159a770983",
      "tests/unit/test_capability_status.py": "fec4b7e7123b14f07aaf6c816a58dd98cd359f92d8897266811ce7932234c5cc",
      "tests/blender/test_film_controls.py": "cecff78aeb5a08baddeeb00c235277c86eb919f0764a9c47a69b00af73b9c48b",
      "tests/blender/test_studio_view.py": "1e763f4c22eecaece1be36def00d565460d68dd424f4aad6c09ee8b90db16625",
      "tests/blender/test_model_picker.py": "1aaafb61fb4295a4b73d0c7ea34ac76749b8918e920fe11ec298007e99508aea"
    }
  }
}
---

Source evidence for [the canonical guide](../../UI_STYLE.md).
