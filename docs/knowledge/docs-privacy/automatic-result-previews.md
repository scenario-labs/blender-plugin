---
{
  "type": "Evidence",
  "id": "docs-privacy.automatic-result-previews",
  "title": "Automatic preview network reads and local icons",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that drawn saved video, 3D and audio results cause get_bulk metadata reads and signed preview downloads on the preview lane only while the online-access predicate allows, polled for a bounded window; that saved images are decoded from verified local copies without a request; that icons are built in memory from rehashed cache files, never through ImagePreviewCollection.load, which wrote a thumbnail under the home directory in a disposable 5.1.2 probe; and that decoding uses bpy.data.temp_data, outside the open blend file. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "9641290006e618426c3f00bf3476b1b0a49d720e146e3e1751694d87f03b2d6f",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "b225436ec6d86f9ab048ce8843ea44fc9e777ab51ff9af1568931e933099dbed",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024"
    }
  }
}
---

# Automatic preview network reads and local icons

Evidence for [the canonical guide](../../PRIVACY.md).
