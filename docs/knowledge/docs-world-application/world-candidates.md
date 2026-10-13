---
{
  "type": "Evidence",
  "id": "docs-world-application.world-candidates",
  "title": "Saved World candidates and numbering",
  "description": "Which saved results the World action offers and how its buttons are numbered.",
  "evidence": {
    "path": "docs/WORLD_APPLICATION.md",
    "scope": "world-candidates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed on 2026-10-13 for the 2:1 World offer (#440). World candidates by metadata are unchanged: panorama.world_candidate keeps PNG, JPEG and OpenEXR media types and excludes saved results whose metadata declares a texture role. ModelJobs now offers them less those whose declared size, read for the current download receipt, fails panorama.is_world_size, the 2:1 and 32-megapixel rule the World preflight applies to the actual bytes. The projected world_assets list, ModelJobs.actions (and so MCP job_status apply_world) and prepare_world_application share ModelJobs._world_offer; preparation refuses such an asset with NOT_WORLD_SIZE before its action check, for the native operator and MCP prepare_result_application alike. The sizes come from ResultCommands.world_sizes, a preview-lane command reached through JobSession, JobWorkers and JobCoordinator.world_sizes, which reads at most WORLD_HEADER_BYTES (2 MiB) of each candidate's receipt file with result_previews.local_image_size, without hashing or store writes. ModelJobs queues one read at a time from its poll for downloaded candidates of ready, apply_failed or applied jobs and keeps each (receipt SHA-256, size) in memory. A size not read yet, a failed read or a header that declares no size keeps the offer by design, so the confirmation-time preflight of the actual bytes stays the authority; a square image can show the button until its read finishes. Drawing reads only the projection: saved_job_actions.describe, drawn by job_recovery.draw_controls, offers Set panorama as World (N) only for a projected world_assets entry whose media type is in the World result types job_recovery passes, and numbers it by its position among all results, as model imports such as Import GLB model (N) do; a view without world_assets offers no World button. Unit tests cover is_world_size against the preflight and the header read (2:1, 1:1 and 16:9 PNG, JPEG and OpenEXR headers, stale receipts, maps, unreadable or far frame headers, validation, cancellation and the preview lane). Installed tests (exact ZIP, isolated profile, macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1) cover 2:1 PNG and JPEG offered and prepared, a square JPEG, a 16:9 PNG and a 3 x 5 PNG neither drawn nor prepared through MCP or the native operator, drawing without a store or size read, an unread size and a JPEG whose frame header lies beyond the read bound staying offered and failing locally at application, a composer job card without the World choice for a 3 x 5 result, and the earlier 3D package and texture set cases keeping material maps out. A free read of a live 3D package on 2026-10-10 showed its four PNG maps declaring texture roles at 2048x2048. No desktop interaction review of the changed offer, other OS, paid generation, #98 completion or release acceptance. Review follow-up on 2026-10-13: the 512-entry eviction is removed, because it reread evicted candidates every poll once more than 512 were shown. Each poll that walks the views now forgets the sizes of jobs no longer in them, so a shown job keeps its size and is not read again, and each read takes at most the preview scheduler's BATCH_LIMIT (32) candidates, enforced by ResultCommands.world_sizes too, with the next poll reading the rest. Native tests cover the pruning and the batched follow-up reads, and a unit test a full batch; fingerprints of the files this follow-up edits were refreshed.",
    "sources": {
      "scenario/core/scene/panorama.py": "0a3402f1f3abdc2835f0d3a3c3db14cbf47f6c49dbd0bc82b5b82c4c022f4beb",
      "scenario/core/jobs/result_metadata.py": "c16b9788e7836ea2ab77a8675506bea1409989da935de801f16c30ee626f5cb1",
      "scenario/core/jobs/results.py": "63e4366d5e94439406650cced8e311900be385b17b65bc1c0780e1cd38f0171f",
      "scenario/core/jobs/coordinator.py": "fb1fb04d0a474b9fabf3bd6f1dcdc716c07f0e29e409997f8817053912d36c72",
      "scenario/core/jobs/workers.py": "ef94b6776f240f438b26f6af8e9101095674d5f69ba63491d9534deb2949502d",
      "scenario/blender/job_session.py": "735db76ac83aa1c0e0a35532ed2a2fdd40cdbc67323f5f6e24f39ab2279720a6",
      "scenario/blender/model_jobs.py": "4c8e5c07cc81a0dbe681388a209cade4cddd3ca81b949c94e8fdc9b9463a1089",
      "scenario/blender/job_recovery.py": "c54a49382b2f750a8db4a59dc425d4a64efa504bdf298b478d5353ea79a27ff6",
      "scenario/mcp/tools_scenario.py": "2d5996c120f2a4a5f3f4f7a2c0a329c182fdd7d7c7facfe525e5e4afd59efcdf",
      "scenario/core/ui/saved_job_actions.py": "5ebffb75b77ab676e19b85637e1cd62482991eb857bec567054fbb75d45e25d6",
      "tests/unit/test_panorama.py": "5158690c05b8b43e636147bee58448d5d35949a41fc5bb40377c89df50c65dd3",
      "tests/unit/test_world_sizes.py": "03aa0ef595e70ee0d0c7f0e7cb2d4feb4fa1d6ea9195eafa11bda7896de80c63",
      "tests/unit/test_saved_job_actions.py": "dda2a3fe9bd4a6201beb32c2d7963ca91d7f6b001eb9cc1887552e10214adea6",
      "tests/blender/test_model_generation.py": "b4b8560032649218aa9077f3c0cdc976e3226866d3ca01804eace8e0a158bb85",
      "tests/blender/test_panorama_lane.py": "3a79d0e8dab3dc926e08717c2354b8bc5d4d0eafbcf1e28e63096379942f1788",
      "tests/blender/test_composer_jobs.py": "636f82ee951d9fc5c388e94f80ec133800870c91ca5a0459524c42f98c8e57e8",
      "tests/blender/test_result_actions.py": "dcd7c1665df882cad2ee4da6a894634888e2bca662879b5f4ede68dc65538e8c"
    }
  }
}
---

# Saved World candidates and numbering

Evidence for [the canonical document](../../WORLD_APPLICATION.md).
