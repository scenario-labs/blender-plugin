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
    "limits": "Reviewed the Blender preview controller: the first twelve Jobs and Generations rows, one store read per saved revision, still-only requests for at most four downloaded results ranked by kind, texture role and saved order, one main-thread decode per tick inside bpy.data.temp_data with the 8192-pixel and 8192 by 4096 bounds, an 8-bit RGBA PNG through save_render with a Standard view transform, icons from cache files rehashed by size and SHA-256 inside the cache root and built with ImagePreview.image_pixels_float, never ImagePreviewCollection.load, at most 64 undrawn icons, retry and retirement. Reviewed the lane's declared-dimension check of local image copies (PNG, JPEG, WebP and OpenEXR data and display windows within 2 MiB), with OpenEXR limited to one version-2 part without deep data, a channel list without layered names and channels times pixels within the RGBA bound, after offline probes in which a generated multi-part file crashed Blender 5.0.1, 5.1.2 and 5.2.1 and a layered file loaded as a multilayer image without a single picture; the OpenEXR rules have unit tests with synthetic headers and probe files, not an installed-ZIP test, and the server transfer rule it inherits from #359, no longer carried here as a copy: any failure of the transfer itself, including a redirect to another host, stays pending with fresh metadata until the window's final poll, a transfer stopped by disabled online access reports offline, and receipt, format, dimension and metadata failures fail at once. Timings and the OS thumbnail write by ImagePreviewCollection.load were measured in disposable offline Blender probes on macOS arm64 with generated files; real photographs and other machines can differ. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents. Re-checked for the roughness caption fix: the caption labels moved to ROLE_LABEL in core.jobs.result_previews, which now has a label for every role in result_metadata.TEXTURE_ROLES, including roughness from 3d-texture-roughness, so no texture map is captioned by its kind alone. A unit test asserts that its keys equal TEXTURE_ROLES and an installed tile test captions roughness and smoothness maps; for this change the native suite ran on macOS arm64 Blender 5.1.2 only. The other claims are unchanged.",
    "sources": {
      "scenario/blender/result_previews.py": "889d64fa323a08eab15f4312fe2d2a3f2f848c370b200aab7b8c37311628b3cc",
      "scenario/core/jobs/result_previews.py": "f2bef8bfd24c2f75f45c0eaa3f85b7bd4806324bfcc0c3abb4062ed6cd147bef",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "e37a28a280f1c258293e7ddafadac249509b74d9dc6e33131b338519eddaefd4",
      "tests/unit/test_result_previews.py": "b5f75e6c2d562ae9c85dea8a4a6bf89d0a5c9bc3c7d556e5b9baf804ceafc34e",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "scenario/blender/runtime.py": "ed7c47498c849441926d2d3032aac00a6b20744e1e8ad75a7f31ca044ab57db2",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c"
    }
  }
}
---

# Automatic previews in Blender and incomplete server downloads

Evidence for [the canonical guide](../../RESULT_PREVIEWS.md).
