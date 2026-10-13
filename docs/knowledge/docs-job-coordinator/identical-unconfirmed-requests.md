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
      "scenario/core/jobs/coordinator.py": "c6c0f45e3ede225313e6524e3bba512b702e180ae91d6f8766c988037d442e81",
      "scenario/core/jobs/store.py": "4a6c2d23df588ba24882b6e727d3a5b77f87fee9b55eb49088ca19c02be7e445",
      "scenario/core/api/sdk_adapter.py": "c08a94f319c08d8427a3a3f7aeceb690915d964a99cafbbc25d5f004c2781b93",
      "scenario/blender/job_session.py": "bb8e3baadacfc57d65befddd014e1461daab2cabb65b22792c5498a6fae33042",
      "scenario/blender/model_jobs.py": "e8a81c2f386fc5edb944da8e13e02a5d9769450d16fe8e34c215380a2535bcfc",
      "scenario/blender/generation.py": "693c8d2f4053b3a453a5946bd29afd16cfc9a092906542af5bd69814c8885bda",
      "scenario/blender/pump.py": "be8a40cc7c999a79e72dd62da20b9ceed3e32fde6436ec5b02f48f15b2d32201",
      "scenario/blender/job_recovery.py": "8c5067cc8d07970bd7f644ae9f4e3bcd2f1a4240aa1e563fe0e9a67f471a3811",
      "scenario/blender/blockout_jobs.py": "c388284557a0418ba5a036ecc0a184ad6d6c72f82d1fcff8191fe9d5ed3068f8",
      "scenario/core/ui/saved_job_actions.py": "c511896cc54a046231f6a84b6b3a0fe5a4f3ac9ff92f46fe4d3610453eb69def",
      "scenario/mcp/tools_scenario.py": "704d598cc6bbdff6a9a26866f2c376c19033790ad6d1feec39de4976b75ba293",
      "tests/unit/test_job_coordinator.py": "076d7f6fbea637dbc70f868bebd5aa9ec902c62d1fd3227e4bce6be32791f1d0",
      "tests/unit/test_job_workers.py": "7658f7b7edf6fcfacf146be5cc1f2b9041dbfe98cbd0450ddd82b026a85b45c1",
      "tests/unit/test_job_store.py": "762ca179b749d662bd26b67cfd0c52a4058dc1d23935847bbd332b999e12d5c0",
      "tests/unit/test_sdk_adapter.py": "e496061f89d60da284ae056478c85c254b2cffc77992904e1b86a344a381b01b",
      "tests/unit/test_saved_job_actions.py": "942ccbbbb1f770d717ade6425c259c7b7674b6701b5f8b1ed98c238a601eb12d",
      "tests/blender/test_model_generation.py": "b5ae7d892591ea6cca6d34e926f59bb87d004aee7807623a68470ccdb035a562",
      "tests/blender/test_workflow_commands.py": "adf7f0292a188b430a30f7e434e6867a65a4dbe14cf9e79d6139a44be088f4ef",
      "tests/blender/test_prompt_tools.py": "939e959296a1eecefb5a87d3aa7f1ea0d7187e77427700f49ecf3fd4f796099b"
    }
  }
}
---

# Identical unconfirmed request guard

Evidence for [the canonical guide](../../JOB_COORDINATOR.md).
