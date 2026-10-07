---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.blockout-recovery",
  "title": "Explicit saved Blockout plan recovery",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "blockout-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "ea77f3a542be698301bd0a414579d4a9e40650bb",
    "limits": "Scoped saved-plan recovery and native/MCP parity, including destination-bound single-use approval and plan-only replacement. Review fixes: guided invalid-plan refinement before quoting, reclaiming finished action handles while retaining uncertain jobs, and pruning deleted saved-plan destinations only after pending reads are drained. The exact b0bc4c291aa5d910beb53d34974526c74e5971d3462b326006cb521c697faeec package passes 746 installed tests on each macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic Blender 5.1.2 desktop checks verify saved-plan cancellation, confirmation, native Undo/Redo, separate Build and viewport front-view/zoom input, with no further submission and an unchanged normal profile. No live provider, other OS/DPI desktop, Film or integrated release acceptance. Unchanged neighboring source fingerprints retain their earlier evidence.",
    "sources": {
      "scenario/blender/blockout_recovery.py": "d61814f62adf8d7d16d4bd688e4e8764b1b0ae502b2fe75e32f314b918f22ef5",
      "scenario/blender/blockout_jobs.py": "d2ee582d3755a4e879012387303b60f344c8bcd2fbada345abe6b2196987ec92",
      "scenario/blender/job_session.py": "7f40e24ae6dfecba75bb0353f4c6ce5e580677b1397bf679bfd048a0c2aee838",
      "scenario/blender/runtime.py": "bbf2a6a457d13db9a8159add5f39f6b927fb055cfaa91008c81930c7d034dd00",
      "scenario/blender/job_recovery.py": "984826e58cb6d4ea47ce7708824c2dc93b8ca7d1aaaca24578ca8c555e064ad9",
      "scenario/blender/model_jobs.py": "93758190ff21f930cea9f664dbdcd5942459058ac0df7e9914dcf991daf8bfae",
      "scenario/mcp/tools_scenario.py": "0aeb78ff1ff9e3499804b2ffb69edab42d72fc1d8655fe2d673db8ce06392fc2",
      "scenario/core/jobs/results.py": "ec817fa50b5ed82012233df0ede33266573368bc74b38d02aee30eba87ec775b",
      "tests/blender/test_blockout_jobs.py": "867fc53b29f6e252aa6cbef32073606ff1f515ce9caa20dae241b43635bb8e6c",
      "tests/blender/test_mcp_contracts.py": "68158253fc8fe5b96c707312ac9ef687071bff5d8017c840b6b1af049d955fd3",
      "tests/unit/test_mcp_descriptions.py": "50926aefc19145edc9976c9e814aa56185766281e6d297d8f3efa41ccbb4ace4"
    }
  }
}
---

# Explicit saved Blockout plan recovery

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
