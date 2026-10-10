---
{
  "type": "Evidence",
  "id": "docs-known-limitations.automatic-result-previews",
  "title": "Automatic preview limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "automatic-result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the stated limits against the controller and core: row and result caps, the bounded polling window and explicit Retry, clips fetched but not drawn, Scenario's image for videos, waveforms only behind the Waveform control, the 8192-pixel image bounds, one main-thread decode per tick with probe timings, no image decoding in background Blender and no MCP preview tool. Live thumbnail coverage, timing and redirect targets remain unestablished. Installed-ZIP native tests (tests/blender/test_result_preview_tiles.py) ran on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 with synthetic PNG images, a synthetic SDK transport and an offline storage stub; drawing was checked through recording layouts and MagicMock panels, not physical input. No desktop interaction, screenshot, UI-scale review, live Scenario thumbnail or other operating system is claimed.",
    "sources": {
      "scenario/blender/result_previews.py": "b7b67af43f0be12d483c7211d67b07bff74fb6393a0e0d9aba5bbbd95281b867",
      "scenario/core/jobs/result_previews.py": "9641290006e618426c3f00bf3476b1b0a49d720e146e3e1751694d87f03b2d6f",
      "scenario/core/jobs/results.py": "5a32f47329d5c71653429b682b8f7e662218b2319b5cfcad7ffe0a46eb8bd6fa",
      "scenario/core/jobs/preview_scheduler.py": "82e9f844d23182c83bb1ac50b4585c4def319160cbcb4c55cd81a77b51122499",
      "tests/blender/test_result_preview_tiles.py": "1e49d3bc815fbec5108860fc645b8d0ef355dadc11d53f01d132663bf4ec98be",
      "tests/unit/test_result_previews.py": "b225436ec6d86f9ab048ce8843ea44fc9e777ab51ff9af1568931e933099dbed"
    }
  }
}
---

# Automatic preview limits

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
