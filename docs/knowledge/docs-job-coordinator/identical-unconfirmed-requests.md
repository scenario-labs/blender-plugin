---
{
  "type": "Evidence",
  "id": "docs-job-coordinator.identical-unconfirmed-requests",
  "title": "Identical unconfirmed request guard",
  "evidence": {
    "path": "docs/JOB_COORDINATOR.md",
    "scope": "identical-unconfirmed-requests",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "3221af5a67583d5a992e9f25f9c41d00abed8924",
    "limits": "Reviewed the coordinator refusal after the dry run, before preparation and inside the locked submission claim, the scoped SQLite lookup that decodes only matching submitting or uncertain rows, the session-only reviewed mark with revision checks, the native Mark reviewed action and its confirmation, MCP omission and refusal of that action, and the adapter refusal of a dry run that carries a job with the session-wide stop of automatic pricing. Synthetic SDK transports, offline unit tests and the installed Blender 5.1.2 macOS arm64 suite only; no live service, paid run, desktop interaction proof or provider behaviour for a job-carrying dry run is established.",
    "sources": {
      "scenario/core/jobs/coordinator.py": "50f3725c3f8e66613de22f9892d36816f07e9d17ede9eda8fe3369d5813e0ca3",
      "scenario/core/jobs/store.py": "4a6c2d23df588ba24882b6e727d3a5b77f87fee9b55eb49088ca19c02be7e445",
      "scenario/core/api/sdk_adapter.py": "1acf3827b2fb56a6583fdbbf75b3d5f7c160763f006ff1e639a9d77c59393c26",
      "scenario/blender/job_session.py": "bb8e3baadacfc57d65befddd014e1461daab2cabb65b22792c5498a6fae33042",
      "scenario/blender/model_jobs.py": "320357d976cbc763c3ca2594af722e9351b50f8c9da9654dcb8f79c8a397cc99",
      "scenario/blender/generation.py": "693c8d2f4053b3a453a5946bd29afd16cfc9a092906542af5bd69814c8885bda",
      "scenario/blender/pump.py": "2e46694014cea3312b45c13473297b9bbddaea7f722a23cf13f169589e0709fd",
      "scenario/blender/job_recovery.py": "8c5067cc8d07970bd7f644ae9f4e3bcd2f1a4240aa1e563fe0e9a67f471a3811",
      "scenario/blender/blockout_jobs.py": "c388284557a0418ba5a036ecc0a184ad6d6c72f82d1fcff8191fe9d5ed3068f8",
      "scenario/core/ui/saved_job_actions.py": "c511896cc54a046231f6a84b6b3a0fe5a4f3ac9ff92f46fe4d3610453eb69def",
      "scenario/mcp/tools_scenario.py": "704d598cc6bbdff6a9a26866f2c376c19033790ad6d1feec39de4976b75ba293",
      "tests/unit/test_job_coordinator.py": "fdb3d2bb656b11de8d3af229d9376d783b526902006e36fb8d26cade636a1bb2",
      "tests/unit/test_job_workers.py": "7658f7b7edf6fcfacf146be5cc1f2b9041dbfe98cbd0450ddd82b026a85b45c1",
      "tests/unit/test_job_store.py": "762ca179b749d662bd26b67cfd0c52a4058dc1d23935847bbd332b999e12d5c0",
      "tests/unit/test_sdk_adapter.py": "723ccc0a44f5468f42432e8a1d8e8e1690b434579138b628e63e0e4fed17cc0e",
      "tests/unit/test_saved_job_actions.py": "942ccbbbb1f770d717ade6425c259c7b7674b6701b5f8b1ed98c238a601eb12d",
      "tests/blender/test_model_generation.py": "4765251407d9939e6232646916a9685a459e34dce1182b905524db11d4ec34bd",
      "tests/blender/test_workflow_commands.py": "adf7f0292a188b430a30f7e434e6867a65a4dbe14cf9e79d6139a44be088f4ef",
      "tests/blender/test_prompt_tools.py": "939e959296a1eecefb5a87d3aa7f1ea0d7187e77427700f49ecf3fd4f796099b"
    }
  }
}
---

# Identical unconfirmed request guard

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
