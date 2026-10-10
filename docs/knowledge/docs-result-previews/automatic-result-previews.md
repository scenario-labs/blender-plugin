---
{
  "type": "Evidence",
  "id": "docs-result-previews.automatic-result-previews",
  "title": "Automatic previews in Blender and incomplete server downloads",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Blender preview controller: the first twelve Jobs and Generations rows, one store read per saved revision, still-only requests for at most four downloaded results ranked by kind, texture role and saved order, one main-thread decode per tick inside bpy.data.temp_data with the 8192-pixel and 8192 by 4096 bounds, an 8-bit RGBA PNG through save_render with a Standard view transform, icons from cache files rehashed by size and SHA-256 inside the cache root and built with ImagePreview.image_pixels_float, never ImagePreviewCollection.load, at most 64 undrawn icons, retry and retirement. Reviewed the lane's declared-dimension check of local image copies (PNG, JPEG, WebP and OpenEXR data and display windows within 2 MiB), with OpenEXR limited to one version-2 part without deep data, a channel list without layered names and channels times pixels within the RGBA bound, after offline probes in which a generated multi-part file crashed Blender 5.0.1, 5.1.2 and 5.2.1 and a layered file loaded as a multilayer image without a single picture; the OpenEXR rules have unit tests with synthetic headers and probe files, not an installed-ZIP test, and the server transfer rule it inherits from #359, no longer carried here as a copy: any failure of the transfer itself, including a redirect to another host, stays pending with fresh metadata until the window's final poll, a transfer stopped by disabled online access reports offline, and receipt, format, dimension and metadata failures fail at once. Timings and the OS thumbnail write by ImagePreviewCollection.load were measured in disposable offline Blender probes on macOS arm64 with generated files; real photographs and other machines can differ. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents.",
    "sources": {
      "scenario/blender/result_previews.py": "f3de3c68e2e7d8401775fe27e3fa3f7e5e4e6ef07cb78dab32e11d3aaeab2641",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "969bd75231ed09bc81d32d27089405b47281cfe98391907d6769623d3350af8c",
      "tests/blender/test_result_preview_tiles.py": "be11193504d7053c384b96dce8249b5296cb955ef72bbfd02e194060dc1d85d8",
      "tests/unit/test_result_previews.py": "967eb2e4e0626ef34c1a1a95821e91bc877880463de4c74ba523892dd2c5d050",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Automatic previews in Blender and incomplete server downloads

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
