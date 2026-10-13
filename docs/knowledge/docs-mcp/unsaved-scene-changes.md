---
{
  "type": "Evidence",
  "id": "docs-mcp.unsaved-scene-changes",
  "title": "Unsaved scene changes",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "unsaved-scene-changes",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "df2fac37c5e605854718811ffaf74384d8341033",
    "limits": "Reviewed which tools mark the file modified (scene tools, Film recipe and builds, render form edits including trained choices, Blockout plan approval, World restoration), that refusals, unchanged selections or frames, same-recipe reloads, empty configures and builds that built nothing stay unmarked while part-way failures mark, that a reload of a renamed workflow and a subframe-only frame change mark through reads of the title and subframe, that project defaults and model_defaults stay unmarked, and which deliveries mark later, against the tool handlers and their installed tests. Film build and Blockout notes now describe the recorded step; headless saved mesh edits still record no desktop history. Installed evidence: the 54 tests in tests/blender/test_file_modified.py pass on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Against the main branch's call paths with only the unwired helper present, 27 of the first 38 fail; against earlier heads, 8 review tests for refusals, unchanged state and part-way failures fail, then the title-only workflow reload and the subframe-only frame change. The full installed suite passes on 5.1.2 (1983 tests, 3 Windows-only skips). Blender 5.0 reports every background file as modified, so its runs check the recorded marks and pushes. No desktop quit prompt, live stroke deferral, GUI timer context or Linux/Windows run is recorded here; CI runs the helper and scene-tool classes in the baseline. Scoped 2026-10-13 check for the MCP model description wait, not a re-review: render_form and the render-lane request now await the model description before any change, so a wait or refusal leaves the file unmarked; configure still marks only after its preflight, and prepare inside file_state.marking. The changed files add no other mark. The claims above are unchanged; the review date and base revision are unchanged. Scoped 2026-10-13 check for the Generate workflow confirmation's input labels and measured loop warning, not a re-review: in workflow_controls.py the workflow form load, _loaded and its file_state.marking call are unchanged; the confirmation's invoke reads the form's input labels and its draw only measures and draws labels, so neither marks the file. The claims above are unchanged; only this file's fingerprint was refreshed, and the review date and base revision are unchanged. Re-checked on 2026-10-13: pump.py's only change is a final model_picker.refresh_thumbnails() call after studio.redraw_popups, which refreshes an open model picker once new thumbnails are cached (#440). Each tick still drains catalog events, processes pending local MCP calls and flushes deferred file marks first, so the claims here are unchanged. Only that fingerprint is refreshed; the review date and base revision are unchanged.",
    "sources": {
      "scenario/blender/file_state.py": "899f1eb5423a4d366a7a491a22c8ca08beec4cb83a2b48422abf29ff4de48739",
      "scenario/blender/job_session.py": "1e4715d6a590a15684cfdf8fa956963b26889d6b147c9c745264e06557448138",
      "scenario/blender/model_jobs.py": "bc88dc2c30a6a960cc9b81748584ad80130bc4f7d1647486e0878ae4d349b8bc",
      "scenario/blender/first_frame_handoff.py": "3d931d0a3dcaec027577a94408ccea0a090f7e41c6a89ff589ffeb514f365caf",
      "scenario/blender/prompt_jobs.py": "c2ff180e68b6586f87d41475963d057b24a41b7c54cc6a439ed1d3ca9714d6b4",
      "scenario/blender/blockout_jobs.py": "45f847d5d0269d453bd284c8494be70aefb405264089d9f09ee42187ecabb5c2",
      "scenario/blender/workflow_controls.py": "8b515b7c19fb0c6b4bc797a612a6158dac0bbecffb2a8254d259cb1a4ae956fd",
      "scenario/blender/reference_form.py": "e3828f6fa358e31c45c316e6452e542ca717a7eef646865f4aba6c3f2b4e0df5",
      "scenario/blender/workflow_uploads.py": "39fc4d14f4617c0e27ab0ee27676e5adf537b4dfff2d379ba2666e1afe2cc692",
      "scenario/blender/film.py": "e03d6cd281184ac147f80c8f6beaaae429d7e4c3d0f7f02c1afcfb860e16cb0d",
      "scenario/blender/render_commands.py": "226bf4e14692ce5cdfc3447083d16cfe987946b9c434c9361633b0a6b8402b51",
      "scenario/blender/world_application.py": "60e5fd73a02cbbc7ef67d52665ae9a70b4425432a7e68ae8484b99975b2718db",
      "scenario/blender/pump.py": "5a751724d9c100000d3dabeef7a9190a0ab35cf4cbdc40485f6134f19b9400c8",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/mcp/tools_blender.py": "13bf44bdb3721b13e689ea88c91ad4031444a7ce08bec4bbff01958e23691037",
      "scenario/mcp/tools_scenario.py": "d286fcf60d6d29109ba08e86bd765b927884d5608a64193e94f46e4658d7c92f",
      "tests/blender/test_file_modified.py": "0712f8a7d2b0a4685d624348f399819beb9d21865a3668e488df2288ff7336bf",
      "tests/blender/helpers.py": "283317572fdd825a7d9068ea72b876799a1485dc9502d6d2763518e503a0d61d",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944"
    }
  }
}
---

# Unsaved scene changes

Evidence for [the canonical guide](../../MCP.md).
