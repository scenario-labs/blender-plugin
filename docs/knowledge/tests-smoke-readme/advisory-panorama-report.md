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
    "reviewed_at": "2026-10-12",
    "base_revision": "4bd0061d73f6d049a86adac37119cc7a2c37741c",
    "limits": "Inspected tools/panorama_report.py: collect verifies completed runs through tools.smoke_image.saved_results (selected key pair and project, saved scope, one finished job, receipts, offline adapter), refuses a run directory named twice, compared by resolved path before any run is verified, measures only results whose saved projection is equirectangular, refusing more than 16 of them before any is read for measurement, and reports run and result positions, contract model IDs only, media type, source, receipt size and SHA-256 and the preflight container facts. report writes the bytes and the manifest to a private temporary directory with O_CREAT, O_EXCL, O_WRONLY and O_BINARY where the platform defines it (mode 0600), reads every copy back and refuses with exit 1, before starting Blender, unless its size and SHA-256 match the download receipt, runs blender_env.run with --background, --factory-startup, --python-exit-code 1 and this file, requires measurements for exactly those files and removes the directory. measure_file decodes with bpy.data.images.load, refuses a format or size that disagrees with the preflight or an OpenEXR that is not float, reads pixels with foreach_get and removes the image. Metrics: Rec.709 luminance (first channel for gray), seam edge, neighbor and quarter-turn means and ratios, pole band row variance over image variance (1% of rows, at least one), and for OpenEXR nearest-rank luminance percentiles with exact decimal ranks, min, max, non-finite count and log2(p99.9 / p1). Unit tests cover the metric math on synthetic arrays, a stdlib-only import, the Blender arguments and the host flow on real saved runs with a fake Blender, including a sentinel O_BINARY bit reaching os.open for every copy and the manifest and a copy with CRLF line endings refused before Blender with its directory removed (no Windows run), a second spelling of the same run directory refused as a repeat, and a lowered cap refused with no result read; the native test decodes Blender-written PNG and OpenEXR and helper-written Rec.709 and AP0 OpenEXR files, and passed in the installed suite on Blender 5.1.2 with the copy check and, before it (the Blender side is unchanged), in quick isolated runs on 5.0.1 and 5.2.1. A manual host run with the copy check and real background Blender 5.1.2 on synthetic saved runs measured a smooth PNG and a 9-stop OpenEXR as written; Blender labelled that OpenEXR, which declares no chromaticities, sRGB while its float values stayed as written. Measurements are advisory; no live skybox output, threshold or human seam, pole or lighting review is claimed. Re-checked 2026-10-12 after restacking on main 4bd0061d (with #380): smoke_image.create_file now also writes quote and suite records with O_BINARY (#382), and saved_results, which the report reuses, is unchanged. Re-checked 2026-10-12 after contract_body began passing schema.exclusive to validate: the claims above are unchanged by that one-line change and its offline test. Re-checked 2026-10-12 after review: collect compares run directories by Path.resolve instead of Path.absolute (saved_results already refused a spelling with .. or a symbolic link, so a repeat could not be measured twice, but it was reported as a symbolic link after the first run was read) and gathers the projected results of every run, stopping at the 17th, before verified_bytes and inspect_panorama read any of them.",
    "sources": {
      "tools/panorama_report.py": "ac131f2f969a7973b385e7bdfbc495b43779a44b97040ceede63d24c27da7adc",
      "tools/smoke_image.py": "3fc1b8decae54b0e0553d5501843bc4ce64936566e6da98f39e2970b1425f461",
      "tools/blender_env.py": "53df246afea605b7c45f4c67296872a0d62571da3336268b6e84c303314eddde",
      "tests/unit/test_panorama_report.py": "1deb78b7e0e1b206cf6f0fcc876f986776d173df4b730d3562d4106275c97556",
      "tests/blender/test_panorama_report.py": "1281bc1ef28ad45ae8d0613f1975da16dad5bbad71e64096d07eacaa68f65f56"
    }
  }
}
---

# Advisory panorama report

Evidence for [the canonical guide](../../../tests/smoke/README.md#advisory-panorama-report).
