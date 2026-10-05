---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-timeline-controls",
  "title": "Explicit editable Film timeline approval",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-timeline-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Shared local scene inspection, single-use timeline review and native/MCP approval over the existing JobSession. Synthetic native tests exercise exact editorial order, live reference identity, deleted/replaced sources, changed timing/camera/revisions, credential retirement, cancellation, saved/reloaded scenes and uncertain cleanup requiring explicit inspection. Existing scenes are explicitly chosen local data; editable recipe markers do not attest generation provenance. No SDK operation, download, result import, job mutation, new worker or store. Desktop layout/input/focus/viewport/Undo-Redo and live media acceptance remain pending; the new controls are draft. Capture, finishing/export and integrated release acceptance remain separate.",
    "sources": {
      "scenario/blender/film_timeline.py": "029d1807954d90a7b3260b72924655ddaa0c787c061f15509c9ad2d54dd7f30e",
      "scenario/blender/film_timeline_controls.py": "a19afcdbefac45a301d16348eda4c2d4033cf6f062e5f117e30dd977674e4d88",
      "scenario/blender/film_scene.py": "ae866981d0d94b9ecd825d4f042693b6a62c45633be0bc03f8c2e346d7e9f9c2",
      "scenario/blender/film.py": "bdf7ab9914baca20d50c035439f84af7dbdeec9d348b6adbc4a756b6f66a5693",
      "scenario/blender/job_session.py": "e025e66d5cd43843d27daa0558ffcf3ebca281b02167ee32932b3a211a0de7fc",
      "scenario/mcp/tools_scenario.py": "cf8fe32d3a227fbf77d4127157f9fd81458087599865db0ae2aea0baed3fd318",
      "tests/blender/test_film_timeline_controls.py": "73607e53e06500f6dda6ddc20babd3b6c4bf7296b8f004938e05da74a79f4ae6",
      "tests/blender/test_film_scene.py": "66f01c87597d360d041efe53f8dd8cd19e560b77477dae0e9ac1028866591b54",
      "tests/blender/test_mcp_contracts.py": "af79316f475b7d7071f8802f417d3d485d673d0e3fa3cf07318ecd56cf497087",
      "tests/unit/test_mcp_descriptions.py": "cfee3fac81daac4d2f9aa7525b68091cf73448509a84f6db96207fa5e9fbce84"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
