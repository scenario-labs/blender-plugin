---
{
  "type": "Evidence",
  "id": "docs-result-transfers.original-result-assets",
  "title": "Untransformed result assets",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "scope": "original-result-assets",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Inspected the pinned SDK 2.2.0 assets.retrieve original_assets keyword (originalAssets query alias, boolean, documented as returning the original asset without transformation) and every result asset read in results.py: manifest metadata, fresh download URLs before each transfer and complete text reads now request originals; history prompt previews in sdk_catalog.py and Library pages remain metadata-only default reads. Offline tests check the exact query with and without a project override, boolean validation before transport, a converted default URL rejected by the real size check, and resume of a manifest saved from a default response. Read-only live checks in the default key scope (no generation, dry run or project override): one public upscale-skybox PNG failed the default URL size check and downloaded and verified through original_assets; on all owned assets only url differed and both URLs served identical bytes, including stale OBJ/MTL counts. Rechecked after rebasing onto declared EXR originals: those reads also send the flag and an offline test confirms the saved original still downloads from originalFileUrl. No raw fallback, retry, authentication or dependency change. Does not establish Blender import of every large panorama, HDRI originals, provider format guarantees or release acceptance. Other topics retain their independent review limits.",
    "sources": {
      "docs/RESULT_TRANSFERS.md": "d38d0ccd70013973eb9de863a299a0b9576fefd38997015580dc9e8639e6d8a2",
      "scenario/core/api/sdk_adapter.py": "5defec57295fdb530070a3e754d975a051f36d47854ee9d7666626c2290bd13d",
      "scenario/core/jobs/results.py": "aeef4981f728712590c249d365950dcca6e9baafda4fd34f06ff608d7455d4f5",
      "scenario/core/api/sdk_catalog.py": "500ebca1a4da228ba0c96b7fa904e322602d67985837f1bdaaa7f19b93fc39a8",
      "tests/unit/test_scenario_sdk_contract.py": "cc6178a87b521304b5158929c2948e2798d0428f9a4c790aac37c26a808e7e30",
      "tests/unit/test_sdk_adapter.py": "0e80120529175cb6c57cbaabc245cbbe32817efc22bfe96fd004d5dbe6ae77b7",
      "tests/unit/test_result_commands.py": "2802711295366246397e3f8f9abd97d7a4ce322752f3a78110421c42b8de9d53",
      "tests/unit/test_prompt_results.py": "75d0751fde141f27431d6808db4a577238b435052105a7a33f56958f10fc4fef",
      "tests/unit/test_cloud_job_recovery.py": "d1d3c5938b4fa52e1339f1a577634193faba5582c31f5f668624144d34117f1a"
    }
  }
}
---

Evidence for [the canonical guide](../../RESULT_TRANSFERS.md).
