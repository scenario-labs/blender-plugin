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
    "limits": "Scoped source and installed-test review of asynchronous complete saved-plan reads, single-use destination approval, deleted-scene status/drawing safety, native/MCP parity and local plan replacement without geometry or new submission. 740 installed tests pass each on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Synthetic installed desktop rendering only: computer-control window/input failures leave native focus, cancellation and Undo/Redo interaction pending. No paid/live provider, other OS desktop, Film or integrated release acceptance. Existing topics retain separate evidence.",
    "sources": {
      "scenario/blender/blockout_recovery.py": "884cb1c1a482837eb9f17be8ebf08cfd86ef0b8ba5d69dc5041c1ce4579b8b6c",
      "scenario/blender/blockout_jobs.py": "b0451f11b71bbe25c2cf00a1b1dc90498efbf795e494d039ea415e2ebf9cdd4f",
      "scenario/blender/job_session.py": "7f40e24ae6dfecba75bb0353f4c6ce5e580677b1397bf679bfd048a0c2aee838",
      "scenario/blender/runtime.py": "bbf2a6a457d13db9a8159add5f39f6b927fb055cfaa91008c81930c7d034dd00",
      "scenario/blender/job_recovery.py": "984826e58cb6d4ea47ce7708824c2dc93b8ca7d1aaaca24578ca8c555e064ad9",
      "scenario/blender/model_jobs.py": "93758190ff21f930cea9f664dbdcd5942459058ac0df7e9914dcf991daf8bfae",
      "scenario/mcp/tools_scenario.py": "0aeb78ff1ff9e3499804b2ffb69edab42d72fc1d8655fe2d673db8ce06392fc2",
      "scenario/core/jobs/results.py": "ec817fa50b5ed82012233df0ede33266573368bc74b38d02aee30eba87ec775b",
      "tests/blender/test_blockout_jobs.py": "bb6c780ba9e43a41e6d9513563a18929bf26b1faf853342e315bc867d04528cd",
      "tests/blender/test_mcp_contracts.py": "68158253fc8fe5b96c707312ac9ef687071bff5d8017c840b6b1af049d955fd3",
      "tests/unit/test_mcp_descriptions.py": "50926aefc19145edc9976c9e814aa56185766281e6d297d8f3efa41ccbb4ace4"
    }
  }
}
---

# Explicit saved Blockout plan recovery

Evidence for [the canonical guide](../../USER_GUIDE.md).
