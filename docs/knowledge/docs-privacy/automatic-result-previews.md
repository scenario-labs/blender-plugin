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
    "limits": "Reviewed that drawn saved video, 3D and audio results cause get_bulk metadata reads and signed preview downloads on the preview lane only while the online-access predicate allows, polled for a bounded window; that saved images are decoded from verified local copies without a request; that icons are built in memory from rehashed cache files, never through ImagePreviewCollection.load, which wrote a thumbnail under the home directory in a disposable 5.1.2 probe; and that decoding uses bpy.data.temp_data, outside the open blend file. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents.",
    "sources": {
      "scenario/blender/result_previews.py": "f3de3c68e2e7d8401775fe27e3fa3f7e5e4e6ef07cb78dab32e11d3aaeab2641",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "be11193504d7053c384b96dce8249b5296cb955ef72bbfd02e194060dc1d85d8",
      "tests/unit/test_result_previews.py": "967eb2e4e0626ef34c1a1a95821e91bc877880463de4c74ba523892dd2c5d050",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Automatic preview network reads and local icons

Evidence for [the canonical guide](../../PRIVACY.md).
