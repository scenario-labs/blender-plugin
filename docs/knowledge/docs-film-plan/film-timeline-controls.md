---
{
  "type": "Evidence",
  "id": "docs-film-plan.film-timeline-controls",
  "title": "Explicit editable Film timeline approval",
  "evidence": {
    "path": "docs/FILM_PLAN.md",
    "scope": "film-timeline-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "e80a947bf4d0fd5500078c9aa22c331038c061f8",
    "limits": "Shared local scene inspection, single-use timeline review and native/MCP approval over the existing JobSession. Synthetic native tests exercise exact editorial order, live reference identity, deleted/replaced sources, changed timing/camera/revisions, deleted-camera replacement and invalidated RNA rejection, credential retirement, cancellation, saved/reloaded scenes and uncertain cleanup requiring explicit inspection. Existing scenes are explicitly chosen local data; editable recipe markers do not attest generation provenance. No SDK operation, download, result import, job mutation, new worker or store. Exact packaged desktop interaction passes on macOS arm64 Blender 5.1.2: explicit take selection, Escape cancellation, Return confirmation, working-scene preservation, native Undo/Redo, viewport selection/Home navigation and Video Sequencer inspection. Existing scenes and saved jobs remain unchanged. External sockets blocked; zero service requests/downloads; clean exit, isolated-profile cleanup and normal-profile preservation verified. Other OS/DPI, live provider and human motion/audio acceptance remain pending. Capture, finishing/export and integrated release acceptance remain separate. Older uncertain reviews take precedence in display and block every ready approval for that scene. Native checks cover missing choices and deleted RNA fallbacks. Build retains Undo without registering a redo action that cannot reconstruct its single-use approval. Fresh physical input for missing-choice and operator-history follow-ups remains pending. Edit Mode preparation remains read-only while native and MCP builds retain the Object Mode boundary. Dismissed review errors leave the panel but remain available through explicit MCP status inspection. Native regression coverage verifies both behaviors. Follow-up ZIP c008687d12a1dc370e841e0daf34abade5d7960d3bbf1458ecb03bca929eba20 passes 958 installed tests on each supported Blender version. Fresh macOS arm64 Blender 5.1.2 physical input verifies inspected dismissal, error removal, viewport selection and Tab into Edit Mode with Build disabled. A shared-command probe prepares in Edit Mode and rejects approval without mutation. Zero service requests/downloads, clean exit, disposable-profile cleanup and normal-profile preservation are verified. This follow-up does not renew the earlier build, Undo/Redo or Sequencer evidence.",
    "sources": {
      "scenario/blender/film_timeline.py": "e72f3cbebeb4ac045c514ca22b01fdce853fcec3d0a595a4b3bcadad87e40df7",
      "scenario/blender/film_timeline_controls.py": "ec844854c2eaafa22930967ed3904997b93d675542e6072f96cc303b3c1b6767",
      "scenario/blender/film_scene.py": "ae866981d0d94b9ecd825d4f042693b6a62c45633be0bc03f8c2e346d7e9f9c2",
      "scenario/blender/film.py": "bdf7ab9914baca20d50c035439f84af7dbdeec9d348b6adbc4a756b6f66a5693",
      "scenario/blender/job_session.py": "e025e66d5cd43843d27daa0558ffcf3ebca281b02167ee32932b3a211a0de7fc",
      "scenario/mcp/tools_scenario.py": "cf8fe32d3a227fbf77d4127157f9fd81458087599865db0ae2aea0baed3fd318",
      "tests/blender/test_film_timeline_controls.py": "4509aa9024d57e07c308d69a8e12cba97414f93018371eb79983af391a743691",
      "tests/blender/test_film_scene.py": "66f01c87597d360d041efe53f8dd8cd19e560b77477dae0e9ac1028866591b54",
      "tests/blender/test_mcp_contracts.py": "af79316f475b7d7071f8802f417d3d485d673d0e3fa3cf07318ecd56cf497087",
      "tests/unit/test_mcp_descriptions.py": "cfee3fac81daac4d2f9aa7525b68091cf73448509a84f6db96207fa5e9fbce84",
      "docs/images/film-timeline-error-before-dismissal.png": "9fb1bba54ac2d431dcfa224eb018c6f553150c9899d6001bdd80c950099dbc8d",
      "docs/images/film-timeline-error-dismissed.png": "2ece4968f8d5ac9e9fb78c6c09da4d280232ea35a8f7ef4a903fff3c5df0122a",
      "docs/images/film-timeline-edit-mode.png": "4388196fb95c217fe7318d5b4f9e0df948d8edc5ea29cfdc0e1a23fa8c146412"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
