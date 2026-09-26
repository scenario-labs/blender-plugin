---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.result-transfers",
  "title": "docs/architecture/runtime.md: result transfers",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "limits": "Explicit JobSession World application was reviewed against owned verification, original-context checks, core claims, exact receipt-bound decoding and installed native failure/rollback/persistence cases. Other lifecycle, component, format and restoration claims retain prior evidence. One selected asset completes the job; there is no per-asset journal or atomic blend-file save. Active UI/MCP, authoritative account/project discovery, production storage policy, undo/recovery UX and live acceptance remain separate; no human approval is implied. Form-source fingerprint reviewed after the copyright-holder spelling correction; implementation bytes and prior coverage limits are unchanged. Explicit interrupted-download recovery and cooperative OS locking reviewed against scoped revision checks, receipt verification, process-exit exclusion tests and the JobSession restart test. No active UI/MCP wiring, older-writer compatibility, orphan-file adoption, scene recovery or live storage acceptance is established.",
    "sources": {
      "scenario/core/jobs/results.py": "0ee36347a8c5be6ff84a36ae2dd54e9c64461de0a83bff513f29ac0bd7712889",
      "scenario/core/jobs/transfers.py": "549e02649dab7061492a5bb1100a836daf1112972a9ad01c2c0d39facb6ac098",
      "tests/blender/test_result_commands.py": "bcb919c9a8dfcd3498959492b5bb49a3f1395b6923282f38182cc9b12c68089e",
      "tests/blender/test_session_results.py": "53f5a82cd68593b5e12d8fda48aa376a2eaa64c75481daec5da3296fe139b9c6",
      "tests/unit/test_result_commands.py": "3cd76a6a01b8e72b7da99b130d037b54f6ec71e4dde3742c633626598da46422",
      "tests/unit/test_result_manifest.py": "e718f316b9f33faefdae53d59bf04c80b48645d52f3dd0bc80a2beae426e5d67",
      "scenario/core/jobs/store.py": "8cc29310bcdc8ab633fed2382e11865aa4995ba45bb316db7141de3b9d1f1e4b",
      "scenario/core/jobs/coordinator.py": "6841e0cf2ceb85c28552f635a85b84ae269e0c7497ce3bea2c37abbbeee7c028",
      "scenario/core/jobs/workers.py": "81c2939dc51bbf6a8e7f96573fb95d200d3667476f621834f61239c26f37883d",
      "scenario/blender/job_session.py": "2c3556f02febd16087d03a9ca85dcc92b8be562065fcb811b7cdf0c20050102c",
      "tests/unit/test_job_store.py": "2ae8ae015465bb63ce1bde0161b5b7489c616ac5931b467fd97697f6a4018c81"
    },
    "scope": "result-transfers",
    "base_revision": "42883c40e1071c15f163f87102668b20d8bdf982"
  }
}
---

# docs/architecture/runtime.md: result transfers

Evidence for [the canonical document](../../architecture/runtime.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
