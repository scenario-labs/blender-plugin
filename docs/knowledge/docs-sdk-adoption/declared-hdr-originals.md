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
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Inspected the pinned scenario-sdk 2.2.0 AssetRetrieveResponse original_file_url, original_mime_type and AssetMetadata.type literals and the assets.download.request target formats. The existing adapter assets.with_raw_response.retrieve path is unchanged; offline contracts check raw and typed fields with a mock transport. No new SDK method, extension, fallback, retry or authentication change; the known authentication expected failure is unchanged. Live response shape is unverified.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "1247ca79813ac35fe4bedad564e3588c41a52506e16580bb85178161ce875bfb",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/result_metadata.py": "00904085422404c9d6d6a81805ed9c86a224b73f4c59c8516bf0c2de894c8e0f",
      "tests/unit/test_scenario_sdk_contract.py": "dc59f8c5caa62f3bc39d1a2eaa53c82ee7e83d92e1b333931fa965423ad6e7db"
    }
  }
}
---

# SDK 2.2.0 original-file fields used for HDR results

Evidence for [the canonical document](../../SDK_ADOPTION.md).
