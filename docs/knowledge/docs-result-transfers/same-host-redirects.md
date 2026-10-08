---
{
  "type": "Evidence",
  "id": "docs-result-transfers.same-host-redirects",
  "title": "Bounded same-host storage redirects",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "same-host-redirects",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "2578af4c4c88fa0b8976899572996d65b9455f85",
    "limits": "Reviewed bounded absolute HTTPS redirects on the original trusted host, shared deadline/permission checks, response cleanup and unchanged byte/hash validation. A previously completed material job was recovered into six verified files after reproducing a same-host HTTP 302 rejection; no generation replay. The 3D result remains rejected for a declared-size mismatch. This does not establish scene application, provider quality, other platform acceptance or complete release acceptance. Signed-storage transport is distinct from Scenario service operations; the SDK adapter and pin are unchanged.",
    "sources": {
      "docs/RESULT_TRANSFERS.md": "d855c90e6658176894ca3ae0f90458daee200dfff7706be0ee388d0a1b772509",
      "scenario/core/jobs/transfers.py": "c92e95990d6b6e13aacc9aceabaa7f4adbbab32fc92c0d7e967abf7be2b58d0f",
      "tests/unit/test_result_transfers.py": "28d68501d58c76f030a7bed3eb8d628b261c7213e326850579a8457e7e90e9e1"
    }
  }
}
---

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
