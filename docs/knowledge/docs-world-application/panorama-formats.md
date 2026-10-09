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
    "limits": "Reviewed the bounded JPEG marker walk (baseline, extended-sequential and progressive Huffman frames; 8-bit three-component samples; 4,096-segment cap; end-of-image marker as the final bytes), OpenEXR chromaticities classification (absent, Rec.709 or ACES AP0 within 0.001; other or malformed primaries rejected for World only), the saved media-type-to-container binding and the explicit ACES2065-1 assignment before packing. Isolated probes and installed-ZIP native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 show Blender-written baseline JPEG decoding as sRGB byte images, EXIF orientation being ignored, AP0 chromaticities selecting ACES2065-1 and AP1/Rec.2020 primaries decoding as Linear Rec.709. Fixtures are synthetic: Blender-written JPEG and directly written uncompressed EXR. Native progressive JPEG decoding, real Scenario JPEG or EXR originals, whether image/aces originals declare AP0 primaries, measured HDR range, seam/pole quality, server-declared projection display and desktop interaction with the new wording are not established. No Scenario service call, SDK change, paid run, #98 completion or release acceptance.",
    "sources": {
      "scenario/core/scene/panorama.py": "813bc6a891c955f67f3c9e345501ac558d662663fb4dbc98549b7ebbe02ecff9",
      "scenario/blender/world_application.py": "8c864f3b7b48fd77ff6a5b94dea86d586a6d312d5782f01f53c13cd893a853f9",
      "scenario/blender/job_session.py": "aa6b64633ca02992f355436eb3601147fa1a7457234c1e795f417a46a851b8eb",
      "tests/unit/test_panorama.py": "6f1f724c68ff3e49dd27b31c6277d146f0e60d3de8b684b60266c46da387b5c2",
      "tests/blender/test_world_application.py": "c20c5a181cac26cb6c656cf58b85c4c985198b1dab928c71dfabd95ae9811a0e",
      "tests/blender/test_session_results.py": "e87afd949fda187702ddac63c0c52f2597fead62c171e2f2afcc9ab217defcf8",
      "tests/blender/helpers.py": "ac061672aabd832e5a6174f5fa3b3d88af90e53af6e618250fe40763484af46e"
    }
  }
}
---

# JPEG and OpenEXR primaries for World panoramas

Evidence for [the canonical document](../../WORLD_APPLICATION.md).
