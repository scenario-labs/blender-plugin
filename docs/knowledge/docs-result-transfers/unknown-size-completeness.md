---
{
  "type": "Evidence",
  "id": "docs-result-transfers.unknown-size-completeness",
  "title": "Completeness of storage downloads without an expected size",
  "description": "A download without an expected size needs a matching Content-Length before publication.",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "unknown-size-completeness",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed ResultDownloader.download: when no expected size is supplied, a response without Content-Length is rejected before reading, as under the legacy OBJ/MTL size policy; a declared length must be a bounded decimal within the byte cap and the streamed body must match it; a known expected size still bounds a body without Content-Length. Rejection publishes nothing and returns no receipt. Callers on this tree and on main pass an exact size for prompt text and every asset result, the legacy OBJ/MTL path keeps requiring Content-Length, and only declared EXR originals pass no size. Unit tests drive a real http.client.HTTPResponse with a close-delimited body cut short (rejected), a declared length with a short body (incomplete) and an exact length (published), plus the command-level failure, retry and installed-ZIP cases. Python 3.11 HTTPSConnection wraps its socket with the ssl default suppress_ragged_eofs=True, so a peer close without close_notify reads as end of data; a local TLS server closing without close_notify confirmed the previous code published a truncated body and this code rejects it (scratch experiment, not committed). Whether Scenario storage responses for originals declare Content-Length is not verified live.",
    "sources": {
      "scenario/core/jobs/transfers.py": "98fd57f44e0b4cd14259d2ddc7495ea2ebc3cf615204ebb30a6f9e5b616b80a2",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "tests/unit/test_result_transfers.py": "5a9541ec58eb1a8da05418a231d789c36aeb2d50dcde1d700aba134b958d1725",
      "tests/unit/test_result_commands.py": "5399126ac8f7255fc8ad569f03bf47a16f91fb986757aefeffa7e858cc707cc5",
      "tests/blender/test_result_commands.py": "7601fdc6e62e273aed7b1552dfba86a9928b21e3e97573e8ccfab0d57823404c"
    }
  }
}
---

# Completeness of storage downloads without an expected size

Evidence for [the canonical document](../../RESULT_TRANSFERS.md).
