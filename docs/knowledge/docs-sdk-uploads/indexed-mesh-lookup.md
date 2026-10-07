---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.indexed-mesh-lookup",
  "title": "Indexed captured mesh lookup",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "indexed-mesh-lookup",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-07",
    "base_revision": "895e401941108a2a9f7cdb5d92995652426fcb9e",
    "limits": "Inspected selected-asset lookup, credential scope, bounded ambiguity detection, array-position preservation and exact revision rechecks. Offline tests verify the SQLite query plan, selected-only decoding, absent inputs, duplicate input reuse, corruption rejection and preservation of existing schema-2 records including uncertain claims. The derived index is built once at store initialization and maintained by SQLite; no schema version or serialized data change. This does not benchmark service latency or establish live provider, desktop input, published update or release acceptance. Other upload and provenance topics retain their limits. Malformed JSON is excluded from the derived index while direct reads still reject and preserve damaged records. Model and workflow quotes cap distinct 3D asset lookups at 128 across all parameters, including unmatched assets; duplicate IDs share the budget. Offline regressions cover new and existing indexes, same and other credential scopes, and the exact lookup boundary.",
    "sources": {
      "scenario/core/jobs/upload_store.py": "3b8be69ce6abb8593e7eb28b56403574b6a95534d8c9adf46564bb4941cc502c",
      "scenario/core/jobs/uploads.py": "8689f1dd534d08bd27d810a635089cd0d1c982dfc1240de3493789a63b16006a",
      "scenario/core/jobs/coordinator.py": "4d3dbf6b05113f9b01a3fd0bfbb702b89fc4320ebfb47cc1a3ae11b5f5407b71",
      "tests/unit/test_upload_store.py": "1a81f3da906de1c054ab5bb271207d5a259da720740aad1c12d206e05418c550",
      "tests/unit/test_shared_quotes.py": "0c486e4f75c978e40a1b893120ae2f0d7f0b28620f77b3e1b93bca292bd4c063"
    }
  }
}
---

# Indexed captured mesh lookup

Evidence for [the canonical guide](../../SDK_UPLOADS.md#captured-mesh-export-provenance).
