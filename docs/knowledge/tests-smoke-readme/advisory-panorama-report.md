---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.advisory-panorama-report",
  "title": "Advisory panorama report",
  "description": "Offline receipt checks and isolated Blender measurements of saved 360 results.",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "advisory-panorama-report",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected tools/panorama_report.py: collect verifies completed runs through tools.smoke_image.saved_results (selected key pair and project, saved scope, one finished job, receipts, offline adapter), refuses repeated run directories, measures only results whose saved projection is equirectangular (at most 16, after inspect_panorama) and reports run and result positions, contract model IDs only, media type, source, receipt size and SHA-256 and the preflight container facts. report writes the bytes and the manifest to a private temporary directory with O_CREAT, O_EXCL, O_WRONLY and O_BINARY where the platform defines it (mode 0600), reads every copy back and refuses with exit 1, before starting Blender, unless its size and SHA-256 match the download receipt, runs blender_env.run with --background, --factory-startup, --python-exit-code 1 and this file, requires measurements for exactly those files and removes the directory. measure_file decodes with bpy.data.images.load, refuses a format or size that disagrees with the preflight or an OpenEXR that is not float, reads pixels with foreach_get and removes the image. Metrics: Rec.709 luminance (first channel for gray), seam edge, neighbor and quarter-turn means and ratios, pole band row variance over image variance (1% of rows, at least one), and for OpenEXR nearest-rank luminance percentiles with exact decimal ranks, min, max, non-finite count and log2(p99.9 / p1). Unit tests cover the metric math on synthetic arrays, a stdlib-only import, the Blender arguments and the host flow on real saved runs with a fake Blender, including a sentinel O_BINARY bit reaching os.open for every copy and the manifest and a copy with CRLF line endings refused before Blender with its directory removed (no Windows run); the native test decodes Blender-written PNG and OpenEXR and helper-written Rec.709 and AP0 OpenEXR files, and passed in the installed suite on Blender 5.1.2 with the copy check and, before it (the Blender side is unchanged), in quick isolated runs on 5.0.1 and 5.2.1. A manual host run with the copy check and real background Blender 5.1.2 on synthetic saved runs measured a smooth PNG and a 9-stop OpenEXR as written; Blender labelled that OpenEXR, which declares no chromaticities, sRGB while its float values stayed as written. Measurements are advisory; no live skybox output, threshold or human seam, pole or lighting review is claimed.",
    "sources": {
      "tools/panorama_report.py": "71b395184d500a8e5d8325aeb4c9096a8c7b5efc2a37e58e017bdef11c58eb7b",
      "tools/smoke_image.py": "09be50abb53f4edf1ce037eab6cad0006f33800c7ac07aa8f0ef09a1dfeada77",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde",
      "tests/unit/test_panorama_report.py": "3aa2581666244b50e3e838de8158f47dcd2572a1946b77b3a505654bdff12ccf",
      "tests/blender/test_panorama_report.py": "1281bc1ef28ad45ae8d0613f1975da16dad5bbad71e64096d07eacaa68f65f56"
    }
  }
}
---

# Advisory panorama report

Evidence for [the canonical guide](../../../tests/smoke/README.md#advisory-panorama-report).
