---
{
  "type": "Evidence",
  "id": "tests-smoke-readme.smoke-input-restart",
  "title": "Smoke input restart guidance",
  "description": "An interrupted input transfer exits with status 4 and asks for a new input upload run.",
  "evidence": {
    "path": "tests/smoke/README.md",
    "scope": "smoke-input-restart",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed tools.smoke_inputs follow() handling of UploadPlanUnavailable and of uploading or part-uncertain records during resume, with offline real-SDK tests using live-shaped responses. One live zero-spend upload of the committed PNG fixture completed through the fixed path. No paid generation, hosted run or restart of a live interrupted upload was performed. Other document claims retain their separate evidence.",
    "sources": {
      "tools/smoke_inputs.py": "ae7b7cc04bcc60658159ecad4a6a312d8742206ec1aaaf8bc61d511ad4ffc0c2",
      "scenario/core/jobs/uploads.py": "06cacc568478204ddbbba7f67f03d48da85fe492a8db8dcf04df14db35944aef",
      "tests/unit/test_smoke_inputs.py": "15d98d707bf503119fdff0a5b5984a441465428b6fd894a8f4f4b40e24bede79"
    }
  }
}
---

# Smoke input restart guidance

Evidence for [the canonical document](../../../tests/smoke/README.md).
