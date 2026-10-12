---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.saved-package-import",
  "title": "Saved model package adoption",
  "description": "Studio adoption row for classified, receipt-checked saved model imports.",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the 3D imports row: shared saved jobs classify GLB, glTF, FBX, OBJ and mesh PLY results into ordered units with one explicit, receipt-checked import per unit, and the prototype Add to scene path in apply_3d is unchanged. Live provider package shapes and desktop review remain open; Gaussian splat adoption is not advanced. On 2026-10-10 fingerprints were refreshed after saved splat import. Statements here about splat refusal, splats not being offered or splat import remaining open describe the package review only and are superseded: SPZ, .splat and PLY units are now prepared on a worker and offered, a PLY without splat data continues through this package snapshot, and the summary gains a splat field, as covered by the saved-splat-import topic of this document. The package snapshot, image guard, claim and rollback claims were rechecked and are unchanged; the review date is unchanged. On 2026-10-10 fingerprints were refreshed after import_snapshot began reading bound OBJ normal, roughness and metallic maps as Non-Color by saved texture role and adding a Normal Map node only when one is missing; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 fingerprints were refreshed after rewrite_mtl began adding -bm 1 to a bound normal statement without one, so an imported OBJ normal map has full Strength; the statements here were rechecked and are unchanged, as is the review date. On 2026-10-12 this branch was rebuilt on main 72c5340c without the unmerged remote progress branch it had been stacked on. The replay conflicted only in imports, ModelJobs fields, the view projection, status and the job_status description, where main's cancellation, World candidate and workflow cost code was kept beside this import. These statements were rechecked against the rebuilt sources and are unchanged; the unit suite passed and the fingerprints were refreshed. The installed results named here are from the earlier head. On 2026-10-12 the branch was rebuilt again, on main 4bd0061d, which now holds #369 (remote progress), #402 (saved model import undo), #377 and #379 (the saved image first-frame handoff and its native control), #401 (composer session end), #373 (asset organization reviews), #378 (MCP organization tools) and #380 (Library organization); the earlier notes' main without #369 no longer applies. The replay kept #369's remote projection, status fields, job_status paragraph and test helpers, and the handoff's use_first_frame action, native first-frame descriptor and operator, first_frame status field and video_first_frame purpose, beside this import, and moved #402's two desktop Undo checkpoints from apply_model into import_snapshot, which every saved model format uses; apply_model, now called only by Film shots, records none. The 3D imports row was rechecked and is unchanged. The unit suite and the full installed suite on macOS arm64 Blender 5.1.2 passed against the rebuilt code; the fingerprints were refreshed and the review date is unchanged. On 2026-10-12 the fingerprints were refreshed again after the splat import branch was rebuilt on this rebuild. It adds splat options, worker preparation and the point builder beside this import; import_splat records the same Undo checkpoints as import_snapshot. The statements here were rechecked and are unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged. Scoped 2026-10-12 check of the compact composer job strip, not a full re-review: model_jobs.py only gains the read-only busy and imports_automatically accessors that the strip reads; the import-unit projection, model application approvals and import commands are unchanged. The claims above still hold; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/model_application.py": "5e3f5039a516f67d552e030e86119e24887b14c85580dc302ebda9be07e0d849",
      "scenario/blender/job_recovery.py": "b6e28f0b4c8b1ff282ffc5e2d1a574bde07867a7e94176e667b05ad5232a342e",
      "scenario/blender/apply_3d.py": "563c404b3c5704eb35ae0f10fee8359f95d2e18011fa9b120e23037ad2eadfd7",
      "tests/blender/test_model_packages.py": "82504559876668b33118cc3a3d936f614714e17606bef0b4699ded8ef0ad678a"
    }
  }
}
---

# Saved model package adoption

Evidence for [the canonical document](../../STUDIO_ADOPTION.md#capability-decisions).
