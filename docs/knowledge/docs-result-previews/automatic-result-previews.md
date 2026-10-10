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
    "limits": "Reviewed the Blender preview controller: the first twelve Jobs and Generations rows, one store read per saved revision, still-only requests for at most four downloaded results ranked by kind, texture role and saved order, one main-thread decode per tick inside bpy.data.temp_data with the 8192-pixel and 8192 by 4096 bounds, an 8-bit RGBA PNG through save_render with a Standard view transform, icons from cache files rehashed by size and SHA-256 inside the cache root and built with ImagePreview.image_pixels_float, never ImagePreviewCollection.load, at most 64 undrawn icons, retry and retirement. Reviewed the lane's declared-dimension check of local image copies (PNG, JPEG, WebP and OpenEXR data and display windows within 2 MiB), with OpenEXR limited to one version-2 part without deep data, a channel list without layered names and channels times pixels within the RGBA bound, after offline probes in which a generated multi-part file crashed Blender 5.0.1, 5.1.2 and 5.2.1 and a layered file loaded as a multilayer image without a single picture; the OpenEXR rules have unit tests with synthetic headers and probe files, not an installed-ZIP test, and the server transfer rule this stack carries from #359: any failure of the transfer itself, including a redirect to another host, stays pending with fresh metadata until the window's final poll, a transfer stopped by disabled online access reports offline, and receipt, format, dimension and metadata failures fail at once. Timings and the OS thumbnail write by ImagePreviewCollection.load were measured in disposable offline Blender probes on macOS arm64 with generated files; real photographs and other machines can differ. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "0ddb83960e3d86bd8d691785dc8f239cd4951961716cb859c3006fa6d479b2fe",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Automatic previews in Blender and incomplete server downloads

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
