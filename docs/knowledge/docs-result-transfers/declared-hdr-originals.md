---
{
  "type": "Evidence",
  "id": "docs-result-transfers.declared-hdr-originals",
  "title": "Declared HDR originals and 360 projection downloads",
  "description": "Original file selection, byte cap, fail-closed refresh and projection labels.",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "declared-hdr-originals",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed manifest selection of originalFileUrl for image assets declaring image/x-exr or image/aces, the .exr local name, the 128 MiB cap reused from the World file limit, the unchanged storage policy and redirect rules, the Content-Length requirement that replaces the unknown expected size (a response without one ends in download_failed with no file published and no receipt, and the same resume command retries it), fail-closed handling when the declaration or destination is missing or changes, legacy manifests keeping their saved file, and server-declared equirectangular labels. Checked the follow-up actions against the saved media type: World application offers image/x-exr and image/aces (WORLD_MEDIA_TYPES) and applies them only after its OpenEXR container and Rec.709 or ACES AP0 primaries checks, while image import and the import_images action accept image/x-exr but not image/aces; no preview is kept as a fallback. Unit tests use the real downloader with mocked HTTPS (allowed host, off-policy host, oversized length, missing length rejected then retried with an exact length) and synthetic SDK responses; the installed-ZIP test repeats the allowed, off-policy and missing-length cases with Blender 5.1.2 on macOS arm64. Live HDRi output, metadata.type presence, original host, size, whether original storage responses declare Content-Length, chromaticities and Radiance handling are unverified; an original host outside the storage policy or a response without Content-Length would make such jobs fail with download_failed where earlier builds saved the JPEG preview, which the guide states as a release check.",
    "sources": {
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "scenario/core/jobs/transfers.py": "98fd57f44e0b4cd14259d2ddc7495ea2ebc3cf615204ebb30a6f9e5b616b80a2",
      "scenario/core/config.py": "492bbf2d6b0f67cdd08d800986647b2bcf2240e9c7c62069234a6bd05f31e45f",
      "scenario/core/scene/panorama.py": "1d7d8fb6b0a06675baa2168a73c87a49fa4ecab6d4ad34843690d3c26edcf764",
      "tests/unit/test_result_commands.py": "5399126ac8f7255fc8ad569f03bf47a16f91fb986757aefeffa7e858cc707cc5",
      "tests/unit/test_result_metadata.py": "7de18feef6672a981fdbb80e091cf0fc9f6dc752bdefd1553d4afd9b8dea3307",
      "tests/unit/test_config.py": "584d481045715d30223d877f6d3852c22b624d21fa3bce0017cd77935d2bf9ba",
      "tests/blender/test_result_commands.py": "7601fdc6e62e273aed7b1552dfba86a9928b21e3e97573e8ccfab0d57823404c",
      "scenario/blender/world_application.py": "341b67665ec8be9201c3191559d47a31421aae5726bc2ea06b134f8245876895",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/model_jobs.py": "b41f0f4516bd80a255dc50bb2e353f799845be2a271ac37f40860781dec7a6ea"
    }
  }
}
---

# Declared HDR originals and 360 projection downloads

Evidence for [the canonical document](../../RESULT_TRANSFERS.md).
