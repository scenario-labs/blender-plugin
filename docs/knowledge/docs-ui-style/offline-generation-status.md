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
    "limits": "Source-reviewed offline display, pending estimate retention, selected-scene pricing and Image ready-handle presentation guards. The GUI pump requests prices only for the selected scene; another scene keeps its pending request without an error until it is selected. A price delivered while another scene is selected returns its form to a pending request, which the pump prices once that scene is selected; other delivery failures keep their error. A price delivered after its scene was switched away and back, or otherwise changed, still shows an error, and a ready quote can become stale after such a round trip while its form still shows the price; submission rejects the stale origin before any request. Submission still validates exact quotes. Native tests use an offline SDK transport and switch the window scene in background Blender; this does not certify live pricing, two windows showing different scenes, all keyboard layouts or integrated release acceptance.",
    "sources": {
      "docs/UI_STYLE.md": "2b754f61ec1dd5f72428b66753b768928a9401736391506bd5bff902a608982d",
      "scenario/blender/panels.py": "9d92e8074690c6174edd831af81bfd01e69197ca2f16e65d97f95afae63ed027",
      "scenario/blender/pump.py": "14ca29af007afa5dbf35c7f39a3caf39a709914a16f8cefa938dff58efcf7f2d",
      "scenario/blender/composer/draw.py": "2514a1ae064493dae895b60704dc3d0795467b7a819400053cbcc19e53032719",
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "scenario/blender/generation.py": "a5587d1af175fe0019fbf63e9426800f328acac48a05e35a7dac8a98fc3db3bd",
      "tests/blender/test_sdk_estimates.py": "4b265a72790084cdde25e3c39c1ada7f782ebc272f36bbccc710a3108fdc8923"
    }
  }
}
---

# Offline generation status

Supports the [UI style guide](../../UI_STYLE.md#buttons) for offline composer labels,
disabled Image actions and estimates retained until network access returns or
their scene is selected.
