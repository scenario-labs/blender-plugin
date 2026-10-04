---
{
  "type": "Evidence",
  "id": "docs-user-guide.film-task-controls",
  "title": "Shared Film task controls and exact approval",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "film-task-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Native/MCP preparation of individual validated Film model/upload tasks, stable production identity in saved scene data, exact quote approval, stale-context rejection and reuse of the existing session/model lifecycle. Offline tests cover both entry points, persistence acknowledgement loss, uncertain restart, saved uploads, scene storage and no automatic application. The accepted ZIP is tested on macOS arm64 Blender 5.0.1/5.1.2/5.2.1. Desktop control remains unavailable (cgWindowNotFound); a prior GUI fixture only reached a synthetic ready quote and exited without submitting. Native input/focus/viewport acceptance remains pending. No paid/live Film acceptance, scene construction, shot capture, finishing/export or release authorization is established.",
    "sources": {
      "scenario/blender/film.py": "669aafdd2efbfa1b2b58f7af6342e498231a570e74edba55cf12abeaefc8927d",
      "scenario/blender/film_jobs.py": "c98462d510e980a47125838ee9a79ccd843e9c3ccb25a21b35f5e153e7e65ac8",
      "scenario/blender/model_jobs.py": "1c71898d7ab1c1f0c980d1e1bcb7afe07d6d1427f0dbb187d505e5f8b3806226",
      "scenario/blender/runtime.py": "480869c7a3d5d6cddccc90c1fba9f23b83205eb72abe0f0dc6169183e1adcf81",
      "scenario/blender/registry.py": "b5a2c2bbe1d536dd12ea1eaa56eb200e3d24f0892cee1330a8c2f65c6bd06a6a",
      "scenario/blender/job_session.py": "4df7f649e6d0f9b835a953cd1c4b00079b2d3c5528e25bf310f1412ff22a1728",
      "scenario/mcp/tools_scenario.py": "301ba810bfdb235c303d941252c848b8105acde369c006f9eda6c937cd7f36a6",
      "tests/blender/test_film_controls.py": "47e7ac1e7261e8862ddf97c3a14461b1b8f0c1c0eab305a00b35d11893a37274",
      "tests/blender/test_mcp_contracts.py": "a734866e18a61582373d80be7a761b5bf564cbfe88d8ad537eef846192ea7ea8",
      "tests/unit/test_mcp_descriptions.py": "fce22b8d7a25d39c47f534bc9eb9cdafb9ca269a9b39a062cce92549ade1c437",
      "tests/unit/test_mcp_docs.py": "92887a224070de8781b7206b574cf2a9dbc8e809772bb202b89c2c097c428cbd"
    }
  }
}
---

Source evidence for [the canonical guide](../../USER_GUIDE.md).
