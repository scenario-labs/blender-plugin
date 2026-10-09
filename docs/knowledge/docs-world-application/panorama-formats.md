---
{
  "type": "Evidence",
  "id": "docs-world-application.panorama-formats",
  "title": "JPEG and OpenEXR primaries for World panoramas",
  "description": "Bounded JPEG preflight, OpenEXR chromaticities and saved media-type binding.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "panorama-formats",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the bounded JPEG marker walk (baseline, extended-sequential and progressive Huffman frames; 8-bit three-component samples; 4,096-segment cap; at most 64 scans counted by a byte search for later SOS markers; an end-of-image marker as the final bytes, which catches simple truncation only; one APP1 EXIF segment whose IFD0 Orientation must be absent or 1), the OpenEXR color declaration classification (chromaticities as Rec.709 or ACES AP0 within 0.001, acesImageContainerFlag 1 as AP0, colorInteropID lin_rec709_scene or lin_ap0_scene; other chromaticities, malformed attributes and conflicts rejected for World only; other colorInteropID values unclassified), the decoded color space agreement check (ACES2065-1 for AP0, Linear Rec.709 or sRGB for Rec.709, Blender's own choice otherwise, never overridden) and the saved media-type-to-container binding. Isolated probes on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 show baseline, SOF1 and Pillow progressive JPEG decoding as sRGB byte images, EXIF orientation ignored, AP0 chromaticities or acesImageContainerFlag 1 selecting ACES2065-1 even beside Rec.709 chromaticities or another colorInteropID, lin_ap1_scene selecting ACEScg and lin_rec2020_scene Linear Rec.2020 whatever the chromaticities say, srgb_rec709_display (written by Blender's own Image.save) selecting sRGB, data selecting Non-Color on 5.0.1 only, and AP1/Rec.2020 chromaticities decoding as Linear Rec.709. During review, a 257 KB progressive file with 4,010 scans took about 8 s to load on 5.1.2; the preflight now rejects such files before decoding. Fixtures are synthetic: Blender-written JPEG and EXR, directly written uncompressed EXR and a committed first-party Pillow progressive JPEG. Installed-ZIP native suites built from this tree pass 1,172 tests each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Grayscale JPEG stays rejected, matching the RGB/RGBA rule for PNG panoramas. Real Scenario JPEG or EXR originals, their colorInteropID or primaries, whether image/aces originals declare AP0, measured HDR range, seam/pole quality, wide-gamut JPEG handling beyond documentation, server-declared projection display and desktop interaction with the new wording are not established. No Scenario service call, SDK change, paid run, #98 completion or release acceptance.",
    "sources": {
      "scenario/core/scene/panorama.py": "a66306a9c8d82c14d2f299fa26a62468d4db7f852111b3bfcb47f434e5e2aa63",
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "tests/unit/test_panorama.py": "a5716070211c058ef1b7eff39b38da789de8a0a32782e478a8910d2df404f678",
      "tests/blender/test_world_application.py": "dff1d3a7308e303a67f21225f29e7e403074015ef4d384e66e364a926bee7395",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/blender/helpers.py": "7e11a66ebd38211c2676471d4d1abb40d69bdf27cf5c69316436dc51ec197f7d",
      "scenario/blender/job_recovery.py": "a58038f156137b6a0507443c9dade17092364c78c7d538ef7290c9e94908ebbf",
      "tests/blender/test_model_generation.py": "b873205c0dd69883403c5a0d02e33834f23053eb99489cc9c7193eb39f3ffa61",
      "tests/fixtures/synthetic/panorama-progressive.jpg": "38b9ad4e8d43fd7b0d2114fc4cdfef98ac6bbc5fac03cda5a3364a3d1d362d5c"
    }
  }
}
---

# JPEG and OpenEXR primaries for World panoramas

Evidence for [the canonical document](../../WORLD_APPLICATION.md).
