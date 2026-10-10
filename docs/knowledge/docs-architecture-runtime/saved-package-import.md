---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-package-import",
  "title": "Runtime saved model package import",
  "description": "Runtime map entries for classified saved model units and their claims.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-package-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime map's saved model sentences and the application claims row against ModelJobs, JobSession.apply_recovered_model, model_application and the native and MCP controls: one classified unit per approval, the main-thread preflight before the claim, reuse claims listing every member and unchanged receipt retry. The full installed suite passed 1,253 tests with 2 Windows-only skips on macOS arm64 Blender 5.1.2 only (exact ZIP SHA-256 06f5e16d233224123993950150a7609945d4eaaeed5aa9581ff460ef7958aec3). Splat import and in-place rig transfer remain open.",
    "sources": {
      "scenario/blender/model_jobs.py": "a40917107e28be6b41e7c813bbb0721dd9f4ca3df1365067201687ae1b172dc5",
      "scenario/blender/job_session.py": "07eb472d0ecdc831cb3491b6f7c521436736e138db86a5dd35ed404f83d000a3",
      "scenario/blender/model_application.py": "77c373fe556c7dd66dd47c70b8602254c56c66f9e678e4e489d61c6a6dabef17",
      "scenario/blender/job_recovery.py": "dca1e9698f00e36f052144a88f6aa0a6443908b2e2597f5172964042f5471320",
      "scenario/mcp/tools_scenario.py": "ab08d69c3d107831c5d4e99a050594f10e431cc829c2f3077b22a08fa9668020",
      "tests/blender/test_model_generation.py": "2c5f2efe6eb50b2adada205aa04fd0ac8770f78ca1a9dab737192cad6c508ab3"
    }
  }
}
---

# Runtime saved model package import

Evidence for [the canonical document](../../architecture/runtime.md#active-sdk-cost-previews-and-model-submission).
