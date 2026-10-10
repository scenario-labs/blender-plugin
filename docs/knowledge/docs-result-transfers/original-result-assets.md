---
{
  "type": "Evidence",
  "id": "docs-result-transfers.original-result-assets",
  "title": "Untransformed result assets",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "original-result-assets",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Inspected the pinned SDK 2.2.0 assets.retrieve original_assets keyword (originalAssets query alias, boolean, documented as returning the original asset without transformation) and every result asset read in results.py: manifest metadata, fresh download URLs before each transfer and complete text reads now request originals; history prompt previews in sdk_catalog.py and Library pages remain metadata-only default reads. Offline tests check the exact query with and without a project override, boolean validation before transport, a converted default URL rejected by the real size check, and resume of a manifest saved from a default response. Read-only live checks in the default key scope (no generation, dry run or project override): one public upscale-skybox PNG failed the default URL size check and downloaded and verified through original_assets; on all owned assets only url differed and both URLs served identical bytes, including stale OBJ/MTL counts. No raw fallback, retry, authentication or dependency change. Does not establish Blender import of every large panorama, HDRI originals, provider format guarantees or release acceptance. Other topics retain their independent review limits.",
    "sources": {
      "docs/RESULT_TRANSFERS.md": "4df52fb5509a4fb41d89ff2286885914a84e82ce65b5f0141cb08b4f0fdf6cf0",
      "scenario/core/api/sdk_adapter.py": "bc55c58fd1c875c241fd151b51538f96da0996a2f2d1d8694298c6a31d7d28de",
      "scenario/core/jobs/results.py": "57857bf300af500cc4c4978f6942745871511618ce1d9876b41cba90724251f7",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "tests/unit/test_scenario_sdk_contract.py": "f89063a6d6c47b643e4567cb8a8f87c5bc0b4a6e9013b356a8b87d350bc5600d",
      "tests/unit/test_sdk_adapter.py": "0e80120529175cb6c57cbaabc245cbbe32817efc22bfe96fd004d5dbe6ae77b7",
      "tests/unit/test_result_commands.py": "425b7060fc50eef99318a8e189b2ddfe0fad9743e507e3cd449b618ae7d71937",
      "tests/unit/test_prompt_results.py": "75d0751fde141f27431d6808db4a577238b435052105a7a33f56958f10fc4fef",
      "tests/unit/test_cloud_job_recovery.py": "d1d3c5938b4fa52e1339f1a577634193faba5582c31f5f668624144d34117f1a"
    }
  }
}
---

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
