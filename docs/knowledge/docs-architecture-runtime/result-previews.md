---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-previews",
  "title": "Result preview runtime component",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "result-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the shared-runtime connection of the preview scheduler, preview lane and cache root, including retirement that waits for an idle preview lane before shutdown, a maintenance-only preview lane command that keeps the cache budget once previews settle, and a session that runs jobs without previews when the cache root cannot be created. Only the workflow review previews schedule previews; saved-result UI, MCP and live acceptance remain open. Re-reviewed on 2026-10-10: the Result previews row now names the stills of waiting workflow steps' review assets and the review_previews decoder in the GUI pump; checked against request_review, runtime.load_review_previews and review_previews.py, added as a source with pump.py. Only the fingerprints of touched sources that matched the base were refreshed. Re-reviewed on 2026-10-10 after two review preview fixes (temporary-data decoding and lost-cache retries in review_previews.py): the Result previews row still names the review_previews decoder in the GUI pump, which still only reads scheduler statuses and calls request_review and retry; the claims are unchanged and only the review_previews.py fingerprint was refreshed.",
    "sources": {
      "scenario/blender/job_session.py": "856baab7ec8aa2786f27ee482b0acc30a8f895fe547664e905b43304ad0ed08a",
      "scenario/blender/runtime.py": "56d4afe7ddb394b23d735c1f7b9e981c4a032963323ac50473f26b09ba9bd6ef",
      "scenario/core/jobs/workers.py": "dece4686af0b0889b99341a99d6d5143d48cdf63919fecef90299b834fbe9bc3",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "scenario/blender/review_previews.py": "65a68e371515d154f6be66e4fc49bbfe9bb075bbeebdeb987db83a40abd9f504",
      "scenario/blender/pump.py": "80e487b5d4aa0b872a741d62793fd5ed78eb281516063aba2ba470803e909f74"
    }
  }
}
---

# Result preview runtime component

Evidence for [the runtime map](../../architecture/runtime.md).
