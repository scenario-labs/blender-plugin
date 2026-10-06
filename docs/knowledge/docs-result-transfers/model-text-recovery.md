---
{
  "type": "Evidence",
  "id": "docs-result-transfers.model-text-recovery",
  "title": "Scoped model text recovery",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "model-text-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected coordinator and worker retrieval of one selected text asset from a successful saved model job, canonical SDK kind/MIME fields, complete previews, bounded full-body reads, credential/project isolation, restart, revision and retirement guards. Offline SDK MockTransport tests only; no JobSession, native Blockout or MCP wiring, scene mutation, paid request or live provider acceptance. Existing topic evidence retains its separate scope.",
    "sources": {
      "scenario/core/jobs/results.py": "ec817fa50b5ed82012233df0ede33266573368bc74b38d02aee30eba87ec775b",
      "scenario/core/jobs/coordinator.py": "c26d2b634d1a8488609dce9baeb59fee957f560356ed067f3774b7f54eb1edd0",
      "scenario/core/jobs/workers.py": "15cd06acc7c85b0524232265583f6f1e66a2a27c33d8f73207ecacfb67454771",
      "tests/unit/test_prompt_results.py": "1c92e1748f5fa57f0047e4471e7fb95104f8e5efa66628373bf254529ddbb25a"
    }
  }
}
---

# Scoped model text recovery

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
