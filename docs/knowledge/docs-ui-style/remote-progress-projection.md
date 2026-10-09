---
{
  "type": "Evidence",
  "id": "docs-ui-style.remote-progress-projection",
  "title": "Jobs status words and progress bar",
  "description": "UI rule for shared Jobs rows, the progress bar and stale lines.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed panels.draw_shared_status and draw_active_job: shared rows map saved states to words, use the reading's status word only in the remote state, draw UILayout.progress with the floored percentage only when percent is known, and add one stale line whose text depends on runtime.online(); prototype rows keep their previous text. Studio Jobs reuses SCENARIO_PT_jobs.draw. Installed tests check the label, bar arguments, stale lines and that drawing performs no store reads, ensure calls or meta writes, plus pump redraw counts. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims. No desktop interaction, screenshot, Blender 5.0/5.2 run, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "cf68b0ad25dffe11283878498975c8687d7c2ff8d95cd4afa47ea3a80147c419",
      "scenario/blender/pump.py": "370e0c393cf3655a258ac705857d40756467a530265e6022e86c9c79ba89e7d4",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92",
      "tests/blender/test_model_generation.py": "a7994ea7cf89c4c26b29701682b9cf9e39971e6fef54a031f4394b9ed57e2f66"
    }
  }
}
---

# Jobs status words and progress bar

Evidence for [the canonical document](../../UI_STYLE.md).
