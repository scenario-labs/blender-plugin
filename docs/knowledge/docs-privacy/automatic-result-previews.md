---
{
  "type": "Evidence",
  "id": "docs-privacy.automatic-result-previews",
  "title": "Automatic preview network reads and local icons",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that drawn saved video, 3D and audio results cause get_bulk metadata reads and signed preview downloads on the preview lane only while the online-access predicate allows, polled for a bounded window; that saved images are decoded from verified local copies without a request; that icons are built in memory from rehashed cache files, never through ImagePreviewCollection.load, which wrote a thumbnail under the home directory in a disposable 5.1.2 probe; and that decoding uses bpy.data.temp_data, outside the open blend file. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/blender/result_previews.py": "889d64fa323a08eab15f4312fe2d2a3f2f848c370b200aab7b8c37311628b3cc",
      "scenario/core/jobs/result_previews.py": "f2bef8bfd24c2f75f45c0eaa3f85b7bd4806324bfcc0c3abb4062ed6cd147bef",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "e37a28a280f1c258293e7ddafadac249509b74d9dc6e33131b338519eddaefd4",
      "tests/unit/test_result_previews.py": "b5f75e6c2d562ae9c85dea8a4a6bf89d0a5c9bc3c7d556e5b9baf804ceafc34e",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Automatic preview network reads and local icons

Evidence for [the canonical guide](../../PRIVACY.md).
