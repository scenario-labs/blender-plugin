---
{
  "type": "Evidence",
  "id": "docs-ui-style.offline-generation-status",
  "title": "Offline generation status",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "offline-generation-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Source-reviewed offline display, pending estimate retention, selected-scene pricing and Image ready-handle presentation guards. The GUI pump requests prices only for the selected scene; another scene keeps its pending request without an error until it is selected. Submission still validates exact quotes. Native tests use an offline SDK transport and switch the window scene in background Blender; this does not certify live pricing, two windows showing different scenes, all keyboard layouts or integrated release acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "b21688ae1dcf8a2883943dcc630497b2e62d4f2df3d423d09c745ecfa14d1e90",
      "scenario/blender/panels.py": "9d92e8074690c6174edd831af81bfd01e69197ca2f16e65d97f95afae63ed027",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/composer/draw.py": "2514a1ae064493dae895b60704dc3d0795467b7a819400053cbcc19e53032719",
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "tests/blender/test_sdk_estimates.py": "07de12d4f429c6bd8b4d954ee7fc150df6c5eb3df532d8203711860846c465d3"
    }
  }
}
---

# Offline generation status

Supports the [UI style guide](../../UI_STYLE.md#buttons) for offline composer labels,
disabled Image actions and estimates retained until network access returns or
their scene is selected.
