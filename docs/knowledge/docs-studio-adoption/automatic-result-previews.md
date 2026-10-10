---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.automatic-result-previews",
  "title": "Automatic previews and progress adoption status",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Retain row status: progress words shared with the composer strip, automatic previews from Scenario's preview images and verified saved images in Jobs, Generations and Studio, without Studio's external ffmpeg or child GLB renders; no Studio preview code was adopted. MCP preview parity, the composer surface and live and desktop acceptance remain. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/blender/result_previews.py": "889d64fa323a08eab15f4312fe2d2a3f2f848c370b200aab7b8c37311628b3cc",
      "scenario/core/jobs/result_previews.py": "f2bef8bfd24c2f75f45c0eaa3f85b7bd4806324bfcc0c3abb4062ed6cd147bef",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "e37a28a280f1c258293e7ddafadac249509b74d9dc6e33131b338519eddaefd4",
      "tests/unit/test_result_previews.py": "b5f75e6c2d562ae9c85dea8a4a6bf89d0a5c9bc3c7d556e5b9baf804ceafc34e",
      "scenario/core/jobs/progress.py": "550ef71b269daa26141588afff3a6377cb5d0c89ef2ebac799750718ca4ba1fd",
      "scenario/core/ui/job_strip.py": "8009e4658006e5127f3fade2e51bedd01a3642e90f44b40ca2789e58512d3c44",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8"
    }
  }
}
---

# Automatic previews and progress adoption status

Evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
