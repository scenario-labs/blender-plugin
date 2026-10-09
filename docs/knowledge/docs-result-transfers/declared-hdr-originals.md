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
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed manifest selection of originalFileUrl for image assets declaring image/x-exr or image/aces, the .exr local name, the 128 MiB cap reused from the World file limit, the unchanged storage policy and redirect rules, fail-closed handling when the declaration or destination is missing or changes, legacy manifests keeping their saved file, and server-declared equirectangular labels. Unit tests use the real downloader with mocked HTTPS (allowed host, off-policy host, oversized length) and synthetic SDK responses; the installed-ZIP test repeats the allowed and off-policy cases with Blender 5.1.2 on macOS arm64. Live HDRi output, original host, size, chromaticities and Radiance handling are unverified.",
    "sources": {
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/result_metadata.py": "00904085422404c9d6d6a81805ed9c86a224b73f4c59c8516bf0c2de894c8e0f",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "scenario/core/config.py": "492bbf2d6b0f67cdd08d800986647b2bcf2240e9c7c62069234a6bd05f31e45f",
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "tests/unit/test_result_commands.py": "e4640308f9f2f8fb26d518741d188f10bd2b480fda1ef82292b1d9f23255299e",
      "tests/unit/test_result_metadata.py": "7de18feef6672a981fdbb80e091cf0fc9f6dc752bdefd1553d4afd9b8dea3307",
      "tests/unit/test_config.py": "584d481045715d30223d877f6d3852c22b624d21fa3bce0017cd77935d2bf9ba",
      "tests/blender/test_result_commands.py": "67841d71c2b37c02b9bd1d0d9fe911aecb8e902d3116c33abee1462390a4dc53"
    }
  }
}
---

# Declared HDR originals and 360 projection downloads

Evidence for [the canonical document](../../RESULT_TRANSFERS.md).
