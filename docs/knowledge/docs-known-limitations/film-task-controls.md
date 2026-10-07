---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-task-controls",
  "title": "Shared Film task controls and exact approval",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-task-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-05",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Native/MCP preparation of individual validated Film model/upload tasks, stable production identity in saved scene data, exact quote approval, stale-context rejection and reuse of the existing session/model lifecycle. Offline tests cover both entry points, persistence acknowledgement loss, uncertain restart, saved uploads, scene storage and no automatic application. Deleted-scene lookup cannot break drawing; completed delivery waits for the unchanged original scene instead of losing its quote during a scene switch. The accepted ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. The exact ZIP also passed isolated macOS arm64 Blender 5.1.2 desktop input: native recipe loading and task selection, Escape/Return upload association and exact-price approval, probe-guard refusal, discarded estimate, one mocked submission/result with no scene application, duplicate-task refusal, cancelled/confirmed production identity changes, and viewport selection/Home framing. SDK responses and result bytes were synthetic; external sockets were blocked. The test profile was removed and the normal profile stayed unchanged. Screenshots record the exact approval and saved state. Other OS desktop behavior and issue #263 remain unaccepted. No paid/live Film acceptance, scene construction, shot capture, finishing/export or release authorization is established.",
    "sources": {
      "scenario/blender/film.py": "669aafdd2efbfa1b2b58f7af6342e498231a570e74edba55cf12abeaefc8927d",
      "scenario/blender/film_jobs.py": "b6e056c5963c55f81433b6731910a39e49764389f130bea0788c7b41ffa83736",
      "scenario/blender/model_jobs.py": "1c71898d7ab1c1f0c980d1e1bcb7afe07d6d1427f0dbb187d505e5f8b3806226",
      "scenario/blender/runtime.py": "480869c7a3d5d6cddccc90c1fba9f23b83205eb72abe0f0dc6169183e1adcf81",
      "scenario/blender/registry.py": "b5a2c2bbe1d536dd12ea1eaa56eb200e3d24f0892cee1330a8c2f65c6bd06a6a",
      "scenario/blender/job_session.py": "4df7f649e6d0f9b835a953cd1c4b00079b2d3c5528e25bf310f1412ff22a1728",
      "scenario/mcp/tools_scenario.py": "301ba810bfdb235c303d941252c848b8105acde369c006f9eda6c937cd7f36a6",
      "tests/blender/test_film_controls.py": "2214a1ec70731cb6de261d16265ee42d380f20aff3373c54ba96b76eee5b0c09",
      "tests/blender/test_mcp_contracts.py": "a734866e18a61582373d80be7a761b5bf564cbfe88d8ad537eef846192ea7ea8",
      "tests/unit/test_mcp_descriptions.py": "fce22b8d7a25d39c47f534bc9eb9cdafb9ca269a9b39a062cce92549ade1c437",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd",
      "docs/images/film-task-approval.png": "c034928b84ce5adff2da76a80b41b1d82bf5179d6cf3f6deb24e0238d9374525",
      "docs/images/film-task-saved.png": "ee029b990dc25313d5417d18c7c108e0c408f3439eee2f523cf60c5171cb7a54"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
