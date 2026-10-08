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
    "base_revision": "78c4a70983f6d5b34fdf5e66ecf94d7fd6df07c8",
    "limits": "Reviewed bounded absolute HTTPS redirects on the original trusted host, shared deadline/permission checks, response cleanup and unchanged byte/hash validation. A previously completed material job was recovered into six verified files after reproducing a same-host HTTP 302 rejection; no generation replay. That earlier 3D check stopped at a declared-size mismatch; legacy mesh recovery is covered separately. This does not establish scene application, provider quality, other platform acceptance or complete release acceptance. Signed-storage transport is distinct from Scenario service operations; the SDK adapter and pin are unchanged.",
    "sources": {
      "docs/RESULT_TRANSFERS.md": "578a12ab06328569e07ec270c40bf0f16d848bb3e0496340d7a241fc38b34589",
      "scenario/core/jobs/transfers.py": "36a1a3d9482bfec2ed79b2205a935198f195591b2ed64f991318dd7a21b2fb3b",
      "tests/unit/test_result_transfers.py": "2092ad9a432f54a8fd94dcf71e1346f7c90bdd9028fa65a999b691cb79d73a30"
    }
  }
}
---

Evidence for [signed result downloads](../../RESULT_TRANSFERS.md).
