---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.declared-hdr-originals",
  "title": "SDK 2.2.0 original-file fields used for HDR results",
  "description": "Raw and typed assets.retrieve fields for originals and skybox types.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "declared-hdr-originals",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the pinned scenario-sdk 2.2.0 AssetRetrieveResponse original_file_url, original_mime_type and AssetMetadata.type literals and the assets.download.request target formats. The adapter's asset read still uses assets.with_raw_response.retrieve without the denial mapping added for model reads; offline contracts check raw and typed fields with a mock transport, next to the models.get_bulk and trained-model listing contracts. No new SDK method, extension, fallback, retry or authentication change; the known authentication expected failure is unchanged. Live response shape is unverified.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "aa638824ce7af67c9b70d12b759f361ab88f41cb0bc7f39213f1ce1d3e8d39ff",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "tests/unit/test_scenario_sdk_contract.py": "badf4fe9c1262bbfcb9b4ac266cb1106ca5bea508c7990380b13fcf7fd982c22"
    }
  }
}
---

# SDK 2.2.0 original-file fields used for HDR results

Evidence for [the canonical document](../../SDK_ADOPTION.md).
