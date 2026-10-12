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
    "limits": "Checked the splat bullet against splat_application (one sphere per kept splat, no rotations, anisotropic scales, view-dependent colour or sorted blending), the reviewed point limits of at most 2,000,000 with even thinning, decoder rejection of SPZ v4, v1 and compressed PLY files with the saved file kept, the SPZ extension flag reported as spz_extensions and a native notice while extension records stay unread, the FORMAT_AXES defaults and the alternative axes in the review. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. No provider file, visual axis check or viewport performance evidence exists. On 2026-10-12 this branch was rebuilt on the saved package import branch after that branch was rebuilt on main 72c5340c, which now holds #356, without the unmerged remote progress branch. The replay conflicted only in imports, the view projection, the job_status description, the generated prepare_result_application row, a transfer guide paragraph and test fixtures. These statements were rechecked against the rebuilt sources, including main's later coordinator, worker and result changes (Film export runs outside the local-operation slot; the splat preparation still uses it and registers one verification for one claim), and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again on the package import branch, itself rebuilt on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, job_status paragraph and test helpers, and the handoff's runtime wrapper, apply_saved_result branch, MCP purpose and native first-frame descriptor and operator, beside this import, and import_splat now records #402's two desktop Undo checkpoints when the saved-result command asks for history. The limitation statements were rechecked and are unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/splat_application.py": "0bbd5b488b2f3b3874db281fa1f7516d919d566bea2a22c77c1258054b10c729",
      "scenario/blender/model_jobs.py": "9e8739c8255bb778c4b45fb07e69cda41fcdc536308542c3f1a84d45156f3f22",
      "scenario/core/scene/splats.py": "a8462e1b261ffe3c56eb4476cf457bd19c29147ff1306460863254669907a1ad",
      "scenario/core/scene/spz.py": "dab0ca7fd16ca7dd9366d1c52e64513dd06bb78d1b82bd3dbe887ce9e59bff0a",
      "scenario/core/scene/splat_ply.py": "ff720f28a5d09bac5cb3d4fd1779dd9e5eddf9b5400e9fe1f6367ed9e3e638bf",
      "tests/blender/test_splat_application.py": "3cf88d7c33560200411c2cbe9ab3282efdb73a2d18f8e518f1b1b64247997d71",
      "tests/blender/test_model_generation.py": "f884c59fcd384e04b7025218f542cb64726385d660acc2e1880b3f7af58e239e"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
