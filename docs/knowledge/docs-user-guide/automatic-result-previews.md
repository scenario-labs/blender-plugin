---
{
  "type": "Evidence",
  "id": "docs-user-guide.automatic-result-previews",
  "title": "Previews in Jobs and Generations",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the user-facing preview claims against the controller and scheduler: downloaded saved jobs only, at most four results each for the first twelve jobs of Jobs and of Generations, Scenario preview images for video, 3D and audio, images decoded from the verified downloaded file, about five minutes of online polling before Retry preview (N), image previews with Online Access disabled, and the disposable result-previews cache. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "176794d01ab7df94fa49089b3fd566f4d493fd79f7c26f557dff61f8f7102de7",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "0ddb83960e3d86bd8d691785dc8f239cd4951961716cb859c3006fa6d479b2fe"
    }
  }
}
---

# Previews in Jobs and Generations

Evidence for [the canonical guide](../../USER_GUIDE.md).
