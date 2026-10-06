---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.indexed-mesh-lookup",
  "title": "Indexed captured mesh lookup",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "indexed-mesh-lookup",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Inspected selected-asset lookup, credential scope, bounded ambiguity detection, array-position preservation and exact revision rechecks. Offline tests verify the SQLite query plan, selected-only decoding, absent inputs, duplicate input reuse, corruption rejection and preservation of existing schema-2 records including uncertain claims. The derived index is built once at store initialization and maintained by SQLite; no schema version or serialized data change. This does not benchmark service latency or establish live provider, desktop input, published update or release acceptance. Other upload and provenance topics retain their limits.",
    "sources": {
      "scenario/core/jobs/upload_store.py": "d5baf196bc643626c298f452072240254a8fa848194a0245720b7a35942a3611",
      "scenario/core/jobs/uploads.py": "8689f1dd534d08bd27d810a635089cd0d1c982dfc1240de3493789a63b16006a",
      "scenario/core/jobs/coordinator.py": "b805ac89c7b64b09644143ffeb5ca93e36b55215a17d4226fb49d6e89828e6a6",
      "tests/unit/test_upload_store.py": "5411310e8e13883263627784b14940e123219948e1a0f74f3886bd7e441ced01",
      "tests/unit/test_shared_quotes.py": "115b7cd631f84b667894a5eae0cf4c187fd7fb65f100bcfb2726c8da3e2ed536"
    }
  }
}
---

# Indexed captured mesh lookup

Evidence for [the canonical guide](../../SDK_UPLOADS.md#captured-mesh-export-provenance).
