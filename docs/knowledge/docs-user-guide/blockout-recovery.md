---
{
  "type": "Evidence",
  "id": "docs-user-guide.blockout-recovery",
  "title": "Explicit saved Blockout plan recovery",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "blockout-recovery",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Scoped source and installed-test review of asynchronous complete saved-plan reads, single-use destination approval, native/MCP parity and local plan replacement without geometry or new submission. 740 installed tests pass each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic installed desktop rendering only: computer-control window/input failures leave native focus, cancellation and Undo/Redo interaction pending. No paid/live provider, other OS desktop, Film or integrated release acceptance. Existing topics retain separate evidence.",
    "sources": {
      "scenario/blender/blockout_recovery.py": "527df624c6b4f44932fe99cec346bc5c394acb306c5bd866bfd2633f81f04f4b",
      "scenario/blender/blockout_jobs.py": "b0451f11b71bbe25c2cf00a1b1dc90498efbf795e494d039ea415e2ebf9cdd4f",
      "scenario/blender/job_session.py": "7f40e24ae6dfecba75bb0353f4c6ce5e580677b1397bf679bfd048a0c2aee838",
      "scenario/blender/runtime.py": "bbf2a6a457d13db9a8159add5f39f6b927fb055cfaa91008c81930c7d034dd00",
      "scenario/blender/job_recovery.py": "984826e58cb6d4ea47ce7708824c2dc93b8ca7d1aaaca24578ca8c555e064ad9",
      "scenario/blender/model_jobs.py": "93758190ff21f930cea9f664dbdcd5942459058ac0df7e9914dcf991daf8bfae",
      "scenario/mcp/tools_scenario.py": "0aeb78ff1ff9e3499804b2ffb69edab42d72fc1d8655fe2d673db8ce06392fc2",
      "scenario/core/jobs/results.py": "ec817fa50b5ed82012233df0ede33266573368bc74b38d02aee30eba87ec775b",
      "tests/blender/test_blockout_jobs.py": "615cc7d289154413d695f717aba172702ec77d9c95f0e79fec425b6a141893aa",
      "tests/blender/test_mcp_contracts.py": "68158253fc8fe5b96c707312ac9ef687071bff5d8017c840b6b1af049d955fd3",
      "tests/unit/test_mcp_descriptions.py": "50926aefc19145edc9976c9e814aa56185766281e6d297d8f3efa41ccbb4ace4"
    }
  }
}
---

# Explicit saved Blockout plan recovery

Evidence for [the canonical guide](../../USER_GUIDE.md).
