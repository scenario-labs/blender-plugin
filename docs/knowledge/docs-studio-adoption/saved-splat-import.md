---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Gaussian splat row: retained decoders and prototype path, new shared saved-job point-cloud import.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Gaussian splats row: spz.py and apply_splat.py are retained, the prototype import_spz now decodes through splats.decode and delegates to splat_application.build_points (fresh mesh, node group and material), and shared saved jobs import SPZ, .splat and Gaussian PLY results through worker decoding and a reviewed claim. test_spz, test_splat_and_reload and test_splat_application pass. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. Live provider files, default axes and desktop review remain open.",
    "sources": {
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/apply_splat.py": "95562972fc2a8f49e10ddac30563d55b434160246b6fa323ba288d4d1338c23e",
      "scenario/blender/apply_3d.py": "563c404b3c5704eb35ae0f10fee8359f95d2e18011fa9b120e23037ad2eadfd7",
      "tests/blender/test_splat_and_reload.py": "57bb8a1793030b30352211c89944d0dfcff832fc9939a6b52502923b53e3f47a",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71",
      "tests/unit/test_spz.py": "07e5ba1dd1cd710cdc1e18c1de9de5ea56ea1b03e9e57d06974fbdc6d02860ab"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../STUDIO_ADOPTION.md).
