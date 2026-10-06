---
{
  "type": "Evidence",
  "id": "docs-material-application.scene-switch-approval-guard",
  "title": "Selected scene guard for saved material reuse",
  "evidence": {
    "path": "docs/MATERIAL_APPLICATION.md",
    "scope": "scene-switch-approval-guard",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "c62a6a7ee51b27b0103e9a07097366279340a2e2",
    "limits": "Reviewed the existing selected-scene guard at saved material admission and asynchronous delivery, including its shared use by image, media, model and World application. Two installed native regressions prove a scene switch consumes the approval without a durable local claim, job/result mutation, material/image changes or extra mocked service requests; a fresh approval after returning succeeds. The current exact ZIP (SHA256 1a6279749de0d335bdaac29396d6bd5eb2692d4cbc342f77fb01081b675abf68) passes 630 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 in isolated profiles. Runtime behavior is unchanged by this clarification. No fresh desktop interaction, live provider, other OS or release acceptance is claimed. Other saved-reuse topics retain their separate evidence and source-drift warnings.",
    "sources": {
      "scenario/blender/job_session.py": "a0d7e692eb1cd6c92a31c006788f98033b34c9ea259a0ad7e8a6d5c3de506f79",
      "scenario/blender/model_jobs.py": "9e694c6c2de26d213411fae8cad262aaba9d84d56ca8267bb7cbe8f744d72c7d",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "tests/blender/test_job_session.py": "c82d1561183d031e6f423e72c5994e405accec2d9dd821dffa83eda471a1c376",
      "tests/blender/test_model_generation.py": "f5424e70bf30f93d9b0f7b2967241f4ab7792cc711849bdf5c7377d1cbcca61d"
    }
  }
}
---

# Selected scene guard for saved material reuse

Evidence for [the canonical guide](../../MATERIAL_APPLICATION.md).
