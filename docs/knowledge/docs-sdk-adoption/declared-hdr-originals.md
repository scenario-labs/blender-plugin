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
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Inspected the pinned scenario-sdk 2.2.0 AssetRetrieveResponse original_file_url, original_mime_type and AssetMetadata.type literals and the assets.download.request target formats. The existing adapter assets.with_raw_response.retrieve path is unchanged; offline contracts check raw and typed fields with a mock transport. No new SDK method, extension, fallback, retry or authentication change; the known authentication expected failure is unchanged. Live response shape is unverified.",
    "sources": {
      "scenario/core/api/sdk_adapter.py": "1247ca79813ac35fe4bedad564e3588c41a52506e16580bb85178161ce875bfb",
      "scenario/core/jobs/results.py": "e06c043bbff65e56b4b910de0e1e763da39a49c05b0ef0397b888f00b93a72f5",
      "scenario/core/jobs/result_metadata.py": "775986522c43e4b837f3deb333f964ca721eb6b8c74bd0282f40824a19c4af17",
      "tests/unit/test_scenario_sdk_contract.py": "dc59f8c5caa62f3bc39d1a2eaa53c82ee7e83d92e1b333931fa965423ad6e7db"
    }
  }
}
---

# SDK 2.2.0 original-file fields used for HDR results

Evidence for [the canonical document](../../SDK_ADOPTION.md).
