---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.application-receipts",
  "title": "docs/architecture/runtime.md: application receipt recovery",
  "description": "Owner-local retry of known application outcomes without scene replay.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "application-receipts",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "4570d8fce08fdb9666333bbbd0ec6d37fea723b9",
    "limits": "Reviewed only explicit receipt retry: original outcome binding, exact saved-successor acknowledgement, ownership, weak retention, unchanged scene/network behavior, deactivation and shutdown. Offline unit and installed native fixtures cover persistence failures before and after commit. No restart reconstruction, uncertain scene reconciliation, active UI/MCP wiring, atomic blend-file save or live service acceptance is established. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "d83584d86a19d7556c0a7b7bff8087c2ef5ed1f395741cc91bb50999fdf166c0",
      "scenario/blender/job_session.py": "e01af6c3773fd73fe28ef89fd2c450c7720e545d5998908f0b443e7bb16f3e08",
      "tests/unit/test_application_claims.py": "93f4727073539148007fffd2fd67636cf76a0d3e1e532e4c633ca4977c194239",
      "tests/blender/test_session_results.py": "0bdb9defa2a359bb583b4414aaf91d0a7a2e300e93d649eeea1efc17f359d6d0"
    }
  }
}
---

# Application receipt recovery

Evidence for [the canonical document](../../architecture/runtime.md).
