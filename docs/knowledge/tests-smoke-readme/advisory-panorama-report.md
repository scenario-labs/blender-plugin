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
    "limits": "Inspected tools/panorama_report.py: collect verifies completed runs through tools.smoke_image.saved_results (selected key pair and project, saved scope, one finished job, receipts, offline adapter), refuses repeated run directories, measures only results whose saved projection is equirectangular (at most 16, after inspect_panorama) and reports run and result positions, contract model IDs only, media type, source, receipt size and SHA-256 and the preflight container facts. report copies the bytes to a private temporary directory, runs blender_env.run with --background, --factory-startup, --python-exit-code 1 and this file, requires measurements for exactly those files and removes the directory. measure_file decodes with bpy.data.images.load, refuses a format or size that disagrees with the preflight or an OpenEXR that is not float, reads pixels with foreach_get and removes the image. Metrics: Rec.709 luminance (first channel for gray), seam edge, neighbor and quarter-turn means and ratios, pole band row variance over image variance (1% of rows, at least one), and for OpenEXR nearest-rank luminance percentiles with exact decimal ranks, min, max, non-finite count and log2(p99.9 / p1). Unit tests cover the metric math on synthetic arrays, a stdlib-only import, the Blender arguments and the host flow on real saved runs with a fake Blender; the native test decodes Blender-written PNG and OpenEXR and helper-written Rec.709 and AP0 OpenEXR files, and passed in quick isolated runs on Blender 5.0.1, 5.1.2 and 5.2.1. One manual host run with real background Blender 5.1.2 on synthetic saved runs measured a smooth PNG and a 9-stop OpenEXR as expected. Measurements are advisory; no live skybox output, threshold or human seam, pole or lighting review is claimed.",
    "sources": {
      "tools/panorama_report.py": "343c70afe583f100c373263fe2d4ed97835ac6fabe09e1edbfe8b9e1edc4f781",
      "tools/smoke_image.py": "9e9da23fcfb42eca4d379004d1b55a6bc6d57c25080d1fdd1a3d1b3ed39ff32a",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde",
      "tests/unit/test_panorama_report.py": "1d92c605ad993df28b29814c841db641d5e38c4def491b89523b644e76863949",
      "tests/blender/test_panorama_report.py": "1281bc1ef28ad45ae8d0613f1975da16dad5bbad71e64096d07eacaa68f65f56"
    }
  }
}
---

# Advisory panorama report

Evidence for [the canonical guide](../../../tests/smoke/README.md#advisory-panorama-report).
