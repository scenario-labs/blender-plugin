---
{
  "type": "Evidence",
  "id": "docs-user-guide.remote-progress-projection",
  "title": "Jobs panel progress wording",
  "description": "User-facing description of shared job status words and progress.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Jobs bullet against panels.SHARED_STATUS_TEXT, progress.LABELS and the percent rule, the two-second POLL_INTERVAL with redraw on change, the stale line texts and restart behaviour that needs the Refresh status or Resume download descriptor labels. Installed native tests on macOS arm64 Blender 5.1.2 cover these claims. No desktop interaction, screenshot, Blender 5.0/5.2 run, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "cf68b0ad25dffe11283878498975c8687d7c2ff8d95cd4afa47ea3a80147c419",
      "scenario/blender/model_jobs.py": "ef10249154c8842a96da012d07395bf8c1554bc762542cdc27f1539ae1590e85",
      "scenario/blender/pump.py": "370e0c393cf3655a258ac705857d40756467a530265e6022e86c9c79ba89e7d4",
      "scenario/core/jobs/progress.py": "286563456f871fb3073ad32932cc3d9b750f12b9d263abef2fe931cbc5568f92",
      "scenario/core/ui/saved_job_actions.py": "db27851f0e2026a9e418ed111d74d4ac468b2a49b84b72ab8c75446dc2a68bae",
      "tests/blender/test_model_generation.py": "a7994ea7cf89c4c26b29701682b9cf9e39971e6fef54a031f4394b9ed57e2f66"
    }
  }
}
---

# Jobs panel progress wording

Evidence for [the canonical document](../../USER_GUIDE.md).
