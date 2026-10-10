---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.automatic-result-previews",
  "title": "Automatic previews and progress adoption status",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Retain row status: progress words shared with the composer strip, automatic previews from Scenario's preview images and verified saved images in Jobs, Generations and Studio, without Studio's external ffmpeg or child GLB renders; no Studio preview code was adopted. MCP preview parity, the composer surface and live and desktop acceptance remain. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "9641290006e618426c3f00bf3476b1b0a49d720e146e3e1751694d87f03b2d6f",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "b225436ec6d86f9ab048ce8843ea44fc9e777ab51ff9af1568931e933099dbed",
      "scenario/core/jobs/progress.py": "550ef71b269daa26141588afff3a6377cb5d0c89ef2ebac799750718ca4ba1fd",
      "scenario/core/ui/job_strip.py": "8009e4658006e5127f3fade2e51bedd01a3642e90f44b40ca2789e58512d3c44",
      "scenario/blender/studio.py": "d4ba0b268cdcc1a6d9477cb5f190ebb18233010de5b5963fecf941ba05995fb8"
    }
  }
}
---

# Automatic previews and progress adoption status

Evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
