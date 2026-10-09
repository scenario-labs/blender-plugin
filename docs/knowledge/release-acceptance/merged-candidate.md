---
{
  "type": "Evidence",
  "id": "release-acceptance.merged-candidate",
  "title": "Consolidated candidate validation and remaining acceptance",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "merged-candidate",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "6c70d2edb385f6bd9f4a5e53c1eee66c575ebd16",
    "limits": "Records merged-main baseline and corrected candidate e73c700b4fb288acf8956615c40e085c7ee068b5 separately. Corrected ZIP bc241cace5fe1d8158cc00cdc54c1a12c10eaddcafc954c3c1172bafd196494f passes 3927 unit checks with one existing SDK expected failure, 1147 installed tests plus two Windows-only skips per macOS arm64 Blender 5.0.1/5.1.2/5.2.1, native synthetic update/restart and local receipt-checked representative asset application. The failed grayscale material case on main is preserved rather than hidden by its green synthetic suites. The maintainer accepted existing video/audio quality separately; no new paid action or production change occurred. Current physical UI proof is blocked by computer-control native-pipe startup, not an observed Blender crash. Fresh onboarding, live project permissions, full compact capture/submission/application, integrated UI/MCP recovery journeys, alternate-DPI/IME and sustained GPU/audio, protected smoke/required checks, actual 0.10.0 provenance/public delivery and full release acceptance remain unverified. Historical source/artifact records are not recertified. Private probe outputs and reports remain local; repository source fingerprints are not substitutes for those observations.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "48122b7e7c10ef917b3b321bc8b740a9aa592de438e356119b18472f0fe26644",
      "docs/RELEASING.md": "12895529af30035fb49375bbc624043c8d8dedea9a5c5fe67be72af283ebe386",
      "docs/development/validation.md": "80225688b7c146e5cfaba51cc9fbd6aae632765bf862773b30b0e1fdf4daa01f",
      "tools/build.py": "162e00bb52f46770d219c5570d3ceccf3bd98e87055026c5a39944aec39f6bdd",
      "tools/wheel_bundle.py": "5189baee1a5381a3be9dd667e0b34357ce6101bd1ea0c7bb03098332ea53c518",
      "tools/test_blender.py": "44fa88def4cad9ad823230ed207c2c5d6664db3913d8eb4cea4e53dfe4fc0eb2",
      "tools/test_repository_update.py": "a0eba939a15936c7452378a3cf6482c5b92fa169cc36b1b178f4b733a2a9e2ce",
      "tests/blender/package_update.py": "bfb7af35527d2a6dd765c3148e8e84ffb0619cb555d1e1d31152b6d37d7c3560",
      "tools/desktop_review.py": "91db1219a8fa78cb77d4297a7556a47e677975001b2860234c82fa741e1c14e1",
      "tools/desktop_review_scene.py": "40d0cdf90289a286c44e70dc4d3ea5ad70337a849c7d578f161de2933f9bdfc8",
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/blender/model_application.py": "9fb7eda96afa0e79c26a547c2ddd15404a71c2344652a2bf31a4491442d96ca6",
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83",
      "tests/unit/test_panorama.py": "4828ce5a0befd33b4e931d9b9ac75669d8c1a399a23c6ac1ccff948cdfc29654",
      "tests/blender/test_material_application.py": "6fae32e6104d1a54b9e1ee7f38f266915795e29e62365ff9e96ca180416522ba"
    }
  }
}
---

Evidence for the [current candidate and decision](../../maintenance/release-acceptance.md#current-candidate-and-decision).
