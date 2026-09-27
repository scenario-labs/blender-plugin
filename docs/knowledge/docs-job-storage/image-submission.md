---
{
  "type": "Evidence",
  "id": "docs-job-storage.image-submission",
  "title": "Shared Image quote and durable submission",
  "description": "Active Image UI and MCP submission through the selected JobSession.",
  "evidence": {
    "path": "docs/JOB_STORAGE.md",
    "scope": "image-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected session-owned Image quotes, exact input/cost matching, one-time consumption, durable claim before SDK dispatch, main-thread display projection and original-scope receipt retention. Native synthetic tests cover UI/MCP payload parity, native Generate operator, stale scene/credentials, duplicate clicks, lost response and write acknowledgement, claim failure and restart inspection. Other lanes, shared local-reference upload, remote progress/cancellation, result delivery, actual native input/focus and live paid acceptance remain outside this slice.",
    "sources": {
      "scenario/blender/model_jobs.py": "02efd3c8e5515c4b38ce1d234ce74f995d7c34146f8d657d95a1e63d1dbb4b3a",
      "scenario/blender/generation.py": "c42b741a24cbdc9f2d20db1f73433a0b0a003170b6cb66bac37eadad5e9e31a8",
      "scenario/blender/runtime.py": "750a3fd5a1f886a994c9522b325788cd0147572607baac06181f0a83187280fd",
      "scenario/blender/job_session.py": "df0f10aeb5eff3358284a8aa1ba297cb384ae47943f87df831e0e67f5786d23d",
      "scenario/mcp/tools_scenario.py": "0bf0b47403a8dce60449e4689cb8853f947de612dc9ba202f0aa58a3cd0f14f0",
      "scenario/core/jobs/coordinator.py": "b0d46de3342bc6e7afcb3acb4bde8fef8b07e6c5c502a4caa992a19b9560621c",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/blender/test_model_generation.py": "1ef942a0ea89579f6b799e9ed1aa17085954289c1828fd4e6299c8d44dd16bb1",
      "tests/blender/test_sdk_estimates.py": "31f5ab2037bb3b2f9ff1cb80207d0d2891bea9e84b931b994f68a19a7724e822"
    }
  }
}
---

# Shared Image quote and durable submission

Evidence for [the canonical document](../../JOB_STORAGE.md).
