---
{
  "type": "Evidence",
  "id": "docs-job-storage.saved-result-reuse-approval",
  "title": "Saved result reuse approval",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "saved-result-reuse-approval",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "93c0f72f5f1303662a338cfd9dbd1f6faf68c14b",
    "limits": "Reviewed completed-result UI/MCP admission through fresh destination approval, exact selected assets and separate local claims. Original generation stays applied; stale approval, unfinished claims and pending receipts block replay. Native synthetic tests cover image, media, static model, material and World reuse, restart, confirmed rollback and lost receipt responses. Exact package passes 619 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Desktop material reuse proof on 5.1.2 includes visible approval, packed target material, viewport/keyboard/selection interaction, unchanged mocked requests and normal profile. Most recent World restoration only; no persistent scene undo or uncertainty reset. No live provider acceptance, other OS desktop proof, SDK service changes, paid tests, crash resolution or release authorization. Other guide topics retain their own evidence.",
    "sources": {
      "scenario/blender/job_session.py": "a0d7e692eb1cd6c92a31c006788f98033b34c9ea259a0ad7e8a6d5c3de506f79",
      "scenario/blender/model_jobs.py": "9e694c6c2de26d213411fae8cad262aaba9d84d56ca8267bb7cbe8f744d72c7d",
      "scenario/blender/job_recovery.py": "db457391e6f2c541bf75e269b7ab5014217ad098e5e7599319eeb30cd11c2f05",
      "scenario/mcp/tools_scenario.py": "3ab7c49cf17656cad572375f744bb4868ae572d0b1e36b5b4bc4db119f980dcf",
      "tests/blender/test_model_generation.py": "9114c85e7442540e9eb6b4cc16a668452a32ccb82a98edbd8aad33a75fff0863",
      "scenario/core/jobs/coordinator.py": "3fa2983e2e5f078548e9710b57c9ca04d0810bdeebed9bcca55fd3da3c750c16",
      "scenario/core/jobs/store.py": "884a342106149d9e56f25d7bc2462a342b9f555dddf9f44084e408bed3734244"
    }
  }
}
---

# Saved result reuse approval

Evidence for [the canonical guide](../../JOB_STORAGE.md).
