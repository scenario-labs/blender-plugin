---
{
  "type": "Evidence",
  "id": "tests-fixtures-readme.rendered-reference-image",
  "title": "First-party rendered reference image fixture",
  "description": "Reproducible Blender 5.1.2 Workbench render with pinned file and pixel digests.",
  "evidence": {
    "path": "tests/fixtures/README.md",
    "scope": "rendered-reference-image",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the committed first-party 512x512 8-bit RGB toadstool render, the script that builds its scene from code with seed 40 in an empty factory scene and renders it with Workbench in background Blender 5.1.2 only, and the isolated offline command wrapper used to run it. The script decodes Blender's PNG output and writes a canonical PNG with only IHDR, one IDAT and IEND and unfiltered rows; check mode compares decoded pixels with an explicit tolerance that defaults to exact. On macOS arm64 with the Metal backend, the documented write command reproduced identical file bytes and check reported zero differing pixels; an unpinned scratch copy produced the same pixels with Blender 5.0.1 and 5.2.1 on that machine. Other GPUs, drivers, operating systems and zlib builds were not checked. Offline unit tests pin the file and pixel digests, size and chunk layout, compare Pillow's decoding, check the plain backdrop border and exercise every PNG row filter and malformed inputs; they never render. The decoder inflates image data at most one byte past the size its header declares, so a small file that would expand far beyond that size fails before being inflated in full. Reading a PNG file stops one byte past the 8 MiB file limit, so a larger file fails before being read in full. No recording, provider output, external asset, Scenario service call, live upload or paid generation is involved.",
    "sources": {
      "tests/fixtures/synthetic/reference-toadstool-512.png": "b70e8debff0ba0fc7dd8823a9a38229600e3fd7b8f22a1a32c490b4310182e02",
      "tools/render_reference_fixture.py": "d8a665c87b368601c2b65708651891e36bea61b7a17d2be7f82e0355536441ea",
      "tests/unit/test_reference_fixture.py": "bb044e83aaed2888e0be38722eabdffaa86a643d6bb572915d556de628377715",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde"
    }
  }
}
---

# First-party rendered reference image fixture

Evidence for [the canonical document](../../../tests/fixtures/README.md).
