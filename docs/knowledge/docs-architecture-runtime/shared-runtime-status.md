---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.shared-runtime-status",
  "title": "Shared runtime connections and remaining acceptance boundaries",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "shared-runtime-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "3a699a172a0513ef66ffc92aa1ee5b47523a8f3e",
    "limits": "Reviewed the active connection summary, lazy catalog/store/session boundary, shared model quote/submission and result routing, worker retirement, native/MCP destination approvals and explicit recovery. Replaces stale future-integration statements with implemented paths while retaining uncertain-submission/application, format/provider, workflow upload, physical UI and live release gates. Inspected runtime and session ownership, ModelJobs quote/poll/control/application dispatch, native saved-job controls, MCP prepare/apply entry points and existing runtime/session/model-generation regressions. This documentation correction changes no package bytes and provides no new native, live-service, human, Film presentation/export or release acceptance evidence. Other guide sections retain their existing topic-specific evidence and limits.",
    "sources": {
      "docs/architecture/runtime.md": "52b07a5ebe5e26346384633b827267365ce24cdbb0c856f9d4ac7843b317d1ce",
      "scenario/blender/runtime.py": "a999a4790a44bd1174fda0b4ba88d25db17d877400de30cf0b87f32096cd92aa",
      "scenario/blender/job_session.py": "3e25f86663d7024d22813e854aa26db84f64dc9a90f4b681c86961167f8a43d8",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d",
      "scenario/core/jobs/workers.py": "716c07192e4fede52e5dcb696591d4183fd382bff34a72b695a51cddd41410a2",
      "tests/blender/test_runtime_jobs.py": "7c6b0a44ed0a0ff52170e5808057778870fecb26120f790ec973c1fc337d605a",
      "tests/blender/test_job_session.py": "4bd4561da96485dcbce97d89c5063fe800bfc86f7e6a97bee339bcb93744d399",
      "tests/blender/test_model_generation.py": "0ea4f5ef5c1211f922d453df93b0ef98d886c19c20faea2bf477ff6c2ce57b52"
    }
  }
}
---

Evidence for [the runtime map](../../architecture/runtime.md).
