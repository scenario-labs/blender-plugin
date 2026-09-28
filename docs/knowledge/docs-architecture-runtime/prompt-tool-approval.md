---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.prompt-tool-approval",
  "title": "Shared prompt tool approval",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "prompt-tool-approval",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Reviewed explicit exact-price approval for native and MCP New/Rewrite/Translate through the shared SDK session, durable one-shot submission, unchanged-field delivery and read-only saved-text recovery. 2895 offline unit tests passed with the known SDK authentication xfail; the exact candidate ZIP passed 558 native tests each on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Blender 5.1.2 desktop interaction verified price visibility, zero submissions before approval, one synthetic submission, full result delivery, field editing, viewport selection/zoom and clean exit with normal profile unchanged. A disposable copy used a distinct app identifier and local development signature; the extension ZIP was unchanged. Initial fixture/window failures and interrupted computer-control typing attempts limit broader keyboard/clipboard acceptance; #263 remains unresolved. No live calls, automatic render Spark, redirected native recovery, other-lane result acceptance or release acceptance is established. The SDK pin and database schema are unchanged.",
    "sources": {
      "scenario/blender/prompt_jobs.py": "c687fe60e21210c4fcad6eed846dc320ec5465d9e0f2b742d262309740e438ec",
      "scenario/blender/prompt_tools.py": "91b17a4496883d581e051ace99290c05a008947379015ff78ba7e36c80a60139",
      "scenario/blender/runtime.py": "8f1e553da4e961344ea3f0b636685451386466302dde5805526b7ae973cc1943",
      "scenario/blender/generation.py": "eaa8dce2b8ad54e2cf694e4551b337951dc105872e0da317866c134cd1d78165",
      "scenario/blender/job_session.py": "b949d5d83698e810237ccc32e610aab4d0a896b9b5bde26d072f268ab8a8208a",
      "scenario/blender/model_jobs.py": "bbb74ca22e37cdb4dba1490f8c021ea9646ed6506accfdd71939fc2f237ddb9b",
      "scenario/core/api/sdk_adapter.py": "6cc3758eebf05f066a0aa11ed4d5c6ec96fb87b72f02f3d609cfdd97b88b044e",
      "scenario/core/jobs/coordinator.py": "52d58dcd5193ae578e7e0d65367c6d8d0120bc23b69dbd105cfdb78ad020ae16",
      "scenario/core/jobs/workers.py": "6b44fce393ed15fddc1189626ce0bd725c7f1b1ae28378694db84026af59dfe1",
      "scenario/core/jobs/store.py": "f367c5df685e2376665489c8c274f6e4567e86d4306b91f07cc014cf6d80ffbd",
      "scenario/core/jobs/results.py": "8cc0ee6f0f280300327a06b700a6356dcdae289b51e8ebffd45268e8541e7012",
      "scenario/mcp/tools_scenario.py": "9e9aeee3e9806e19ccc2245fc6103b3efaff1c1c108fa2d4ebe2c438cd7ff436",
      "tests/blender/test_prompt_tools.py": "0ddbf0ebb71689a84f225ce95e6a960f2f056b94d0f47ac9d4ae50ef5d7fe2e4",
      "tests/unit/test_sdk_adapter.py": "f9df4ef657e0c4ab76e72bfe80ede1ea8bf0a0b9c3026579332603035a1bc7f5",
      "tests/unit/test_scenario_sdk_contract.py": "2371c6dcfea85cc312e98b1e53e69967331bf3dab32b639dc6f665a13bab7a9b",
      "tests/unit/test_prompt_results.py": "470e071b794aaa5a04ccd1d103642f5aea7608789a674d90fcd7581e45da61c3",
      "tests/unit/test_job_coordinator.py": "18bcecb3c7f27465f316df1ac544268199da650466abfb387c6aa1c148597750",
      "docs/images/prompt-price-approval.png": "1e841ee921525b8280d2c0da7fe86916560c182229db9b02cdbef3f6447b86a2",
      "docs/images/prompt-result-delivery.png": "e11d92c1c3193851c4fd51fb03eecf3524e567f8f350a9b5fb37b3596b1af7bc"
    }
  }
}
---

Evidence for [the canonical guide](../../architecture/runtime.md).
