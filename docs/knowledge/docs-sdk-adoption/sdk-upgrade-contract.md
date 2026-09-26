---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.sdk-upgrade-contract",
  "title": "SDK version and extension contract",
  "description": "Current SDK release and named extension workflow.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "sdk-upgrade-contract",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "92d7d576b84b0c09767ca50a35cc99908666994e",
    "limits": "Scoped review of SDK 2.2.0 pin, wheel hash, unchanged runtime dependency closure and MIT notice, adopted method signatures and raw response/query contracts. Estimates use the documented string true and submission omits dryRun. Authentication workaround and missing discovery resources remain tracked. This record updates current SDK-version references only; unrelated implementation claims retain their prior evidence. No live service or paid acceptance is claimed.",
    "sources": {
      "pyproject.toml": "b60c17fedfd6a9ee2ceb6c3093247fa08f513ae32aa0e59a4a90173da61e4672",
      "uv.lock": "a7b510cd1251679c6ff54186dffd8ca2a18da32a414dc1b427715da9f411a51d",
      "scenario/sdk-wheel-lock.json": "1c933e40d98552b6952b8093990619e30c87cba18b5af90801d84ffd9f62dd8c",
      "scenario/blender_manifest.toml": "d6014304fb07ea0dc422715c1fa6a481f3aac9c6705ed43dece2bf49372e6dd9",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/unit/test_scenario_sdk_contract.py": "6ed4c17fe08cb62363448716437a140a0f4297eb154a31e90dd69daa5134fa21",
      "tests/unit/test_wheel_bundle.py": "59b7da96a9afc57f0f288a1ad915b0a134b4fcc4aeae0cf9b1807db59dfd64c1",
      "tests/blender/test_sdk_bundle.py": "60d92e8726c5b7ab82b1fe9d95817ce659b1a6f4f00887e15a04b337a2c8daca"
    }
  }
}
---

# SDK version and extension contract

Evidence for [the canonical document](../../SDK_ADOPTION.md).
