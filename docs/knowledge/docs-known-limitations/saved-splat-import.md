---
{
  "type": "Evidence",
  "id": "docs-known-limitations.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Point-cloud approximation, thinning, undecodable files, extension flags and unproven default axes.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Checked the splat bullet against splat_application (one sphere per kept splat, no rotations, anisotropic scales, view-dependent colour or sorted blending), the reviewed point limits of at most 2,000,000 with even thinning, decoder rejection of SPZ v4, v1 and compressed PLY files with the saved file kept, the SPZ extension flag reported as spz_extensions and a native notice while extension records stay unread, the FORMAT_AXES defaults and the alternative axes in the review. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No provider file, visual axis check or viewport performance evidence exists.",
    "sources": {
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "dab0ca7fd16ca7dd9366d1c52e64513dd06bb78d1b82bd3dbe887ce9e59bff0a",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
