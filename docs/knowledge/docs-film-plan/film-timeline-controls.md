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
    "base_revision": "04f434d3ed1375d5a4d4669cb25508d0b74fc0f3",
    "limits": "Shared local scene inspection, single-use timeline review and native/MCP approval over the existing JobSession. Synthetic native tests exercise exact editorial order, live reference identity, deleted/replaced sources, changed timing/camera/revisions, deleted-camera replacement and invalidated RNA rejection, credential retirement, cancellation, saved/reloaded scenes and uncertain cleanup requiring explicit inspection. Existing scenes are explicitly chosen local data; editable recipe markers do not attest generation provenance. No SDK operation, download, result import, job mutation, new worker or store. Exact packaged desktop interaction passes on macOS arm64 Blender 5.1.2: explicit take selection, Escape cancellation, Return confirmation, working-scene preservation, native Undo/Redo, viewport selection/Home navigation and Video Sequencer inspection. Existing scenes and saved jobs remain unchanged. External sockets blocked; zero service requests/downloads; clean exit, isolated-profile cleanup and normal-profile preservation verified. Other OS/DPI, live provider and human motion/audio acceptance remain pending. Capture, finishing/export and integrated release acceptance remain separate. Older uncertain reviews take precedence in display and block every ready approval for that scene. Native checks cover missing choices and deleted RNA fallbacks. Build retains Undo without registering a redo action that cannot reconstruct its single-use approval. Fresh physical input for these follow-up paths remains pending.",
    "sources": {
      "scenario/blender/film_timeline.py": "e0a1f36e199a2c1de7e174280503607d95ae22183bdff781a3bb10a1a077eca7",
      "scenario/blender/film_timeline_controls.py": "2ff4e4556c80d2d17ad146ec285850961cd2ae0e275a2ab96786e3d5736b159e",
      "scenario/blender/film_scene.py": "ae866981d0d94b9ecd825d4f042693b6a62c45633be0bc03f8c2e346d7e9f9c2",
      "scenario/blender/film.py": "bdf7ab9914baca20d50c035439f84af7dbdeec9d348b6adbc4a756b6f66a5693",
      "scenario/blender/job_session.py": "e025e66d5cd43843d27daa0558ffcf3ebca281b02167ee32932b3a211a0de7fc",
      "scenario/mcp/tools_scenario.py": "cf8fe32d3a227fbf77d4127157f9fd81458087599865db0ae2aea0baed3fd318",
      "tests/blender/test_film_timeline_controls.py": "5b0a5b11a2c8febaeff42b5e96a08ea0239e5dbcda5d01d1992db71d87689451",
      "tests/blender/test_film_scene.py": "66f01c87597d360d041efe53f8dd8cd19e560b77477dae0e9ac1028866591b54",
      "tests/blender/test_mcp_contracts.py": "af79316f475b7d7071f8802f417d3d485d673d0e3fa3cf07318ecd56cf497087",
      "tests/unit/test_mcp_descriptions.py": "cfee3fac81daac4d2f9aa7525b68091cf73448509a84f6db96207fa5e9fbce84"
    }
  }
}
---

Source evidence for [the canonical guide](../../FILM_PLAN.md).
