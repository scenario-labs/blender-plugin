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
    "limits": "Reviewed the 3D guidance against the per-unit labels, the review summary, the supported formats, OBJ map binding, Non-Color OBJ normal, roughness and metallic maps with the normal map through a Normal Map node at full strength unless the saved MTL sets another -bm, glTF resource binding, embedded FBX textures, external texture rejection and FBX clip timing, splat refusal, the Nothing was imported pause and the 256 MiB per file and 512 MiB per package limits, and the generic-import wording for experimental models. The full installed suite passed 1,256 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 (exact ZIP SHA-256 54cc6483f7ef1f3d94f4af5fee44dffc3144be96758604b5c5c2a1954d4ed2b1), and the installed baseline passed 778 tests on macOS arm64 Blender 5.0.1 and 5.2.1 from separate builds of the same checkout. No desktop recheck of the OBJ normal strength, desktop screenshot of the new controls, live provider package or splat import is claimed. On 2026-10-12 only the OBJ normal strength guidance and the test results were re-reviewed; the other statements keep their 2026-10-10 review. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The 3D guidance statements here were rechecked and are unchanged. The guide keeps #402's Undo paragraph after this import's format and size sentence, names the button to import again by format and drops the earlier clause that this command adds no Undo step; that paragraph is covered by the saved-model-undo topic. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged.",
    "sources": {
      "scenario/blender/job_recovery.py": "ff6c45e43a0dc79666a98ee6c0bdf421cc0e6d4a173c2e5d81d3c448c2796346",
      "scenario/core/ui/saved_job_actions.py": "4315254386cf9c91788694ce8a3a4dd0435ab8325e6727727d21b1efe726120a",
      "scenario/blender/model_application.py": "d956046473b0cc174ea79daa95c07c22f730f192612c6d8cadc4e9229e50a816",
      "scenario/blender/model_jobs.py": "f9bb80a01c12136fd1d463c3cf825c2b049c373aa4ed0f8e4a1022cee8f24838",
      "scenario/core/scene/model_formats.py": "900ae616efe5c6c194712784a9014a67e86fc6c2330766d46c8d27781ca78d08",
      "scenario/core/ui/capability_status.py": "5e18990d7117e420c6046cd01d992fa9dfe7f3dbb09702860ff5a45fc973dcd1",
      "tests/blender/test_model_packages.py": "8ebac60fc363667ba061930806f658149c8d1649750ccd2e0b2670ec1fa963e0",
      "tests/blender/test_model_generation.py": "65f32ea3bda91376a16f5e3331ae917aad6bfd77d0b38c901f223af949632aad"
    }
  }
}
---

# Saved model package import guidance

Evidence for [the canonical document](../../USER_GUIDE.md#3d).
