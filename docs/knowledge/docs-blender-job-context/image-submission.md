---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.image-submission",
  "title": "Shared Image quote and durable submission",
  "description": "Active Image UI and MCP submission through the selected JobSession.",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "image-submission",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected session-owned Image quotes, exact input/cost matching, one-time consumption, durable claim before SDK dispatch, main-thread display projection and original-scope receipt retention. Native synthetic tests cover UI/MCP payload parity, native Generate operator, stale scene/credentials, duplicate clicks, lost response and write acknowledgement, claim failure and restart inspection. Other lanes, shared local-reference upload, remote progress/cancellation, result delivery, actual native input/focus and live paid acceptance remain outside this slice.",
    "sources": {
      "scenario/blender/model_jobs.py": "231eff7b866d78ed5366d085ae6b166936a521b7cdade328a805a6f498647677",
      "scenario/blender/generation.py": "39205a8f8ac225801a11f5888b1394db77d3c8daa06e23ed0e392db2a7290857",
      "scenario/blender/runtime.py": "750a3fd5a1f886a994c9522b325788cd0147572607baac06181f0a83187280fd",
      "scenario/blender/job_session.py": "df0f10aeb5eff3358284a8aa1ba297cb384ae47943f87df831e0e67f5786d23d",
      "scenario/mcp/tools_scenario.py": "0bf0b47403a8dce60449e4689cb8853f947de612dc9ba202f0aa58a3cd0f14f0",
      "scenario/core/jobs/coordinator.py": "b0d46de3342bc6e7afcb3acb4bde8fef8b07e6c5c502a4caa992a19b9560621c",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/blender/test_model_generation.py": "584f6e2d0a75cc274d5437d5ad54d440457f7b3a901b39e4ed68e98552f3f564",
      "tests/blender/test_sdk_estimates.py": "31f5ab2037bb3b2f9ff1cb80207d0d2891bea9e84b931b994f68a19a7724e822"
    }
  }
}
---

# Shared Image quote and durable submission

Evidence for [the canonical document](../../BLENDER_JOB_CONTEXT.md).
