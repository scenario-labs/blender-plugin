---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-package-import",
  "title": "Saved model package import guidance",
  "description": "User guidance for importing saved GLB, glTF, FBX, OBJ and mesh PLY results.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "72c5340cea11e688f1b62a35cf9c1e5f903193d3",
    "limits": "Reviewed the 3D guidance against the per-unit labels, the review summary, the supported formats, OBJ map binding, Non-Color OBJ normal, roughness and metallic maps with the normal map through a Normal Map node at full strength unless the saved MTL sets another -bm, glTF resource binding, embedded FBX textures, external texture rejection and FBX clip timing, splat refusal, the Nothing was imported pause and the 256 MiB per file and 512 MiB per package limits, and the generic-import wording for experimental models. The full installed suite passed 1,256 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 54cc6483f7ef1f3d94f4af5fee44dffc3144be96758604b5c5c2a1954d4ed2b1), and the installed baseline passed 778 tests on macOS arm64 Blender 5.0.1 and 5.2.1 from separate builds of the same checkout. No desktop recheck of the OBJ normal strength, desktop screenshot of the new controls, live provider package or splat import is claimed. On 2026-10-12 only the OBJ normal strength guidance and the test results were re-reviewed; the other statements keep their 2026-10-10 review. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12, after the splat import branch was rebuilt on top of this one, fingerprints were refreshed for saved splat import and rechecked against its rebuilt sources. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims are unchanged; the review date is unchanged. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The 3D guidance statements here were rechecked and are unchanged. The guide keeps #402's Undo paragraph after this import's format and size sentence, names the button to import again by format and drops the earlier clause that this command adds no Undo step; that paragraph is covered by the saved-model-undo topic. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the fingerprints were refreshed again after the splat import branch was rebuilt on this rebuild. It adds splat options, worker preparation and the point builder beside this import; import_splat records the same Undo checkpoints as import_snapshot. The statements here were rechecked and are unchanged.",
    "sources": {
      "scenario/blender/job_recovery.py": "4b4768790db13f35adbe3d80ee3c52ee63fc34e84955f4a56d2448b65f545eeb",
      "scenario/core/ui/saved_job_actions.py": "d25a4144d0357e0025606e6d3befb7dde6558df45f7c85b8f1db9383d83ba086",
      "scenario/blender/model_application.py": "501ba21b816ecd4db78d9f3da35cfa5b507f2e6cff5409ad87b5d118ad325753",
      "scenario/blender/model_jobs.py": "31ec59656bb44b4e87111e3ea535cd76e9e988b2123d56cdc4aa8968273f6aff",
      "scenario/core/scene/model_formats.py": "900ae616efe5c6c194712784a9014a67e86fc6c2330766d46c8d27781ca78d08",
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "tests/blender/test_model_packages.py": "82504559876668b33118cc3a3d936f614714e17606bef0b4699ded8ef0ad678a",
      "tests/blender/test_model_generation.py": "1627264d78606a37f6414d68ed57ddf8cc5761cfe0268c8e78ed935b0c2290a3"
    }
  }
}
---

# Saved model package import guidance

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
