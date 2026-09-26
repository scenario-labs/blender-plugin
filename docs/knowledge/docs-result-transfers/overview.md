---
{
  "type": "Evidence",
  "id": "docs-result-transfers.overview",
  "title": "docs/RESULT_TRANSFERS.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/RESULT_TRANSFERS.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-26",
    "limits": "Existing guide indexed during this intake, without a fresh claim-by-claim or live verification; consult current integration status and issue acceptance. Windows private-storage path handling and its offline/native regression sources were inspected; later importer compatibility and live storage acceptance remain separate. Explicit interrupted-download recovery and cooperative OS locking reviewed against scoped revision checks, receipt verification, process-exit exclusion tests and the JobSession restart test. No active UI/MCP wiring, older-writer compatibility, orphan-file adoption, scene recovery or live storage acceptance is established.",
    "sources": {
      "scenario/core/jobs/results.py": "0ee36347a8c5be6ff84a36ae2dd54e9c64461de0a83bff513f29ac0bd7712889",
      "scenario/core/jobs/store.py": "8cc29310bcdc8ab633fed2382e11865aa4995ba45bb316db7141de3b9d1f1e4b",
      "scenario/core/jobs/transfers.py": "ca3aafdd915d908be78db5b0a7f3a535f0274e6f3ccc7e0cef7c2d88a90f212d",
      "tests/blender/test_job_store.py": "4aeb6a009869cf3daf12aab611d468e9ecc377d18386b9de62a273efe17de1d9",
      "tests/blender/test_result_commands.py": "bcb919c9a8dfcd3498959492b5bb49a3f1395b6923282f38182cc9b12c68089e",
      "tests/blender/test_result_transfers.py": "f728030d1d9213fc5a7a9e044413e64c53aab0a2b2c1587becf1e3c9504adb73",
      "tests/unit/test_result_commands.py": "3cd76a6a01b8e72b7da99b130d037b54f6ec71e4dde3742c633626598da46422",
      "tests/unit/test_result_manifest.py": "08415c5fb8afdac8e9aab8e22b7ea6f18652954a41b6dba8fdc160ad1dda5288",
      "tests/unit/test_result_transfers.py": "09e4378a9482222b477cbb3700eb04889696f1bd332b0daaf77ce9ee02a0f244",
      "scenario/core/jobs/coordinator.py": "6841e0cf2ceb85c28552f635a85b84ae269e0c7497ce3bea2c37abbbeee7c028",
      "scenario/core/jobs/workers.py": "81c2939dc51bbf6a8e7f96573fb95d200d3667476f621834f61239c26f37883d",
      "scenario/blender/job_session.py": "2c3556f02febd16087d03a9ca85dcc92b8be562065fcb811b7cdf0c20050102c",
      "tests/unit/test_job_store.py": "2ae8ae015465bb63ce1bde0161b5b7489c616ac5931b467fd97697f6a4018c81",
      "tests/blender/test_session_results.py": "53f5a82cd68593b5e12d8fda48aa376a2eaa64c75481daec5da3296fe139b9c6"
    },
    "scope": "overview",
    "base_revision": "42883c40e1071c15f163f87102668b20d8bdf982"
  }
}
---

# docs/RESULT_TRANSFERS.md: overview

Evidence for [the canonical document](../../RESULT_TRANSFERS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
