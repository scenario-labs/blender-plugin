---
{
  "type": "Evidence",
  "id": "docs-result-transfers.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Use of worker splat preparation by saved splat imports and the prototype builder delegation.",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the closing paragraph of worker-side splat preparation: JobSession.prepare_model_import queues ResultCommands.prepare_model_import for saved SPZ, .splat and PLY units, the point-cloud builder creates fresh Geometry Nodes and material data, and the prototype import_spz delegates to it. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. Provider MIME types, SPZ versions, axis conventions and original-file bytes still need live evidence.",
    "sources": {
      "scenario/core/jobs/results.py": "f29048daaca9cafd1a5ceaef4d8eebb70ac2328bae25ded45451be9672dddac7",
      "scenario/blender/job_session.py": "3ab7ea580ca986f9d86eb7a0735a96293627aa53016cc4172820fdc184e98163",
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/blender/apply_splat.py": "95562972fc2a8f49e10ddac30563d55b434160246b6fa323ba288d4d1338c23e",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../RESULT_TRANSFERS.md#worker-side-splat-preparation).
