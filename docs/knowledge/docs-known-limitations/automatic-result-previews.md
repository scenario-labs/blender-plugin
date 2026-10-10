---
{
  "type": "Evidence",
  "id": "docs-known-limitations.automatic-result-previews",
  "title": "Automatic preview limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the stated limits against the controller and core: row and result caps, the bounded polling window and explicit Retry, clips fetched but not drawn, Scenario's image for videos, waveforms only behind the Waveform control, the 8192-pixel image bounds, multi-part, deep and layered OpenEXR files refused before decoding, one main-thread decode per tick with probe timings, no image decoding in background Blender and no MCP preview tool. Live thumbnail coverage, timing and redirect targets remain unestablished. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed. The controller decodes image copies and icons with the shared preview_decode helper from #384, re-checked here; its own copy of that decode was removed, and semi-transparent high bit-depth pixels are now unpremultiplied before the sRGB conversion as the helper documents.",
    "sources": {
      "scenario/blender/result_previews.py": "f3de3c68e2e7d8401775fe27e3fa3f7e5e4e6ef07cb78dab32e11d3aaeab2641",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "f6a9702a09824cb28c46d99cfa1a37fa194d64ba2ad1c830bf11884e1b66d31f",
      "scenario/core/jobs/preview_scheduler.py": "b4deebeae3ff7a09c5b602df8af8f96608838a8b675e79c2fd6614a6b128186b",
      "tests/blender/test_result_preview_tiles.py": "be11193504d7053c384b96dce8249b5296cb955ef72bbfd02e194060dc1d85d8",
      "tests/unit/test_result_previews.py": "967eb2e4e0626ef34c1a1a95821e91bc877880463de4c74ba523892dd2c5d050",
      "scenario/blender/preview_decode.py": "30c21fe513960e0aa4730122721115301784ed2e4a5b2e724cd670845fa978f9"
    }
  }
}
---

# Automatic preview limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
