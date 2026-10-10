---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.model-smoke",
  "title": "SDK adoption: shared model acceptance commands",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "model-smoke",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected shared Image/Material/Video/GLB/audio quote/submit/resume commands, exact approval and cap, selected scope, durable single attempt and receipt verification. Offline SDK transport and SQLite regressions exercise all five result kinds and unchanged spend/recovery safeguards. Prior script credential/opt-in coverage moves into shared entry-point tests. Existing version-1 Image quotes remain valid. No live service call, reference upload automation, decoder, native scene interaction, Film, protected multi-suite CI or aggregate budget acceptance is claimed. Neighboring topics retain their own scope. Material schema-3 quotes retain normalized map selections/defaults and output count; offline regressions reject missing roles and changed recovery expectations against the saved request digest. Explicit subsets and texture-only requests are supported. Old material quotes cannot submit; known jobs still recover bytes without claiming completeness. Counts do not establish per-variant grouping or decoded map quality. The shared create_file helper now adds os.O_BINARY where the platform defines it, so Windows text-mode translation cannot make the saved quote record differ from its printed approval digest. Offline tests substitute a stand-in flag bit and check the open flags and the printed quote digest against the saved bytes; no Windows run was performed. Rechecked model retrieval (now mapping 403/404 to unavailable), estimate and submission SDK methods, texture-role metadata and the shared entry-point credential tests against current sources.",
    "sources": {
      "tools/smoke_image.py": "77b17f03efed4c3a7a543cc03bc24908870d4dbe8d91b0a0b88eda2fdb8cfb39",
      "tools/smoke_model.py": "cf65eae775a588b784706505c8fe98169d83169fab026fc55d75e7739c16119b",
      "tests/smoke/README.md": "545f9f5de431a5f8b108ddf825030c52fa97593f3fbbfdd1c4f7c7e1823e4427",
      "tests/smoke/smoke_image.py": "b5649c9baff7c164c0e786c41c232a65a77e706a82d9b8a34d6b10275848709a",
      "tests/smoke/smoke_material.py": "fdf557f414c9804c32295d164fbe76df92f34bab455647d3049558cc37d52179",
      "tests/smoke/smoke_video.py": "0f329c6f080b4968dfc47b6d8058e4142b2416815e5c1ea9d90e4b10643e7970",
      "tests/smoke/smoke_image_to_3d.py": "41571fc1ff61018009e50f74977d1b0ab21e6f88f9f96450cf7ad2a5ac8ae19f",
      "tests/unit/test_smoke_image.py": "84a1c8d579038939a072d1223d06bdf656816085e037c916b0831865938857b7",
      "tests/unit/test_dev_config.py": "4d27e2c077a7037ee173f35c6fc1d5dae92aa986d5c9cec4081fbcea5340db9a",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52",
      "scenario/core/jobs/result_metadata.py": "87921d743217e5c81ddd1c11dcade42aef15c4aeed6d2a1189391c94f940153c",
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "tests/fixtures/models/model_patina-material.json": "281caebfa479542d14cd59e4861c91c0737653a869bd021d6cbd2d20d0be7dfa",
      "scenario/core/scene/material_plan.py": "0c6a5b8bbdc0613f220f7e440aaf144f6980025e298ea32a1e9e8ed50bcb932a"
    }
  }
}
---

Evidence for [model acceptance commands](../../SDK_ADOPTION.md#model-acceptance-commands).
