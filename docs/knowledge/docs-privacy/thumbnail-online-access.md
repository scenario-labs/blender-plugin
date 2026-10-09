---
{
  "type": "Evidence",
  "id": "docs-privacy.thumbnail-online-access",
  "title": "docs/PRIVACY.md: thumbnail online access",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "thumbnail-online-access",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed only the model picker thumbnail permission statement. ensure_thumbnail starts no download while Blender is offline; on the main thread it captures the selected catalog's permission Event, refreshed by sync_catalog_context on pump ticks and cleared on retirement, or a module Event mirrored from runtime.online() when no catalog is selected. The worker checks that predicate once before download_file, not during a transfer or its single retry. Installed native tests on Blender 5.1.2 macOS arm64 cover offline, online, cached and withdrawn-before-connect paths with a mocked downloader; no live CDN request, physical desktop interaction or other Blender version is claimed. The composer topic keeps its own older model picker review and fingerprint.",
    "sources": {
      "scenario/blender/model_picker.py": "28640e2b99044c33a546fb8d9f721842bd4deca02f7941253f6378ff384c0498",
      "scenario/core/api/sdk_catalog.py": "87a745ceeedf95a1700adbbe86dcfc3f15c865dfd123c6b2d73c2a2eb83f5886",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/pump.py": "86f5c8416f58b2d83ec525fb350e555c0a9631cc34cdd119d9172dfc41fe7a15",
      "scenario/core/api/assets.py": "88d5d6df75cd4586f09e37e4d12b4421a4e4750fb0a64ea3aadfa9de7ae220dd",
      "tests/blender/test_model_picker.py": "218665f14a544eb41126e238b30f3f297253d405bdb444ec55c6cf3463465a31",
      "tests/blender/helpers.py": "07472d7a74b13541b3c4b554d55dc65d667832a5407bfe589d358948871465fe"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
