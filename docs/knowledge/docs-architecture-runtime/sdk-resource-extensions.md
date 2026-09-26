---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.sdk-resource-extensions",
  "title": "Named SDK resource extensions",
  "description": "Optional discovery fallbacks and API-key implicit tenant scope.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "sdk-resource-extensions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "92d7d576b84b0c09767ca50a35cc99908666994e",
    "limits": "Inspected selected SDK 2.2.0 low-level GET response/options behavior and named teams/projects extensions. Offline tests cover explicit credential isolation, query separation, permission/lifetime, single-attempt errors, malformed responses and API-key generation without tenant parameters or discovery. No live endpoint acceptance, exhaustive discovery pagination, server principal/default-project inference or active durable-runtime integration is claimed. Neighboring Scenario MCP implementation informed the route contracts; no private records or code were copied.",
    "sources": {
      "scenario/core/api/sdk_extensions.py": "dc084216172a704ab1453811f9e2c9c1b9755af55fee7c2fa305704449b9a369",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "tests/unit/test_sdk_extensions.py": "b4139c11dcd5692f655ba899242b421b093814ce4d3843cd0ab291ae43530a53",
      "tests/unit/test_scenario_sdk_contract.py": "6ed4c17fe08cb62363448716437a140a0f4297eb154a31e90dd69daa5134fa21",
      "tests/blender/test_sdk_bundle.py": "60d92e8726c5b7ab82b1fe9d95817ce659b1a6f4f00887e15a04b337a2c8daca"
    }
  }
}
---

# Named SDK resource extensions

Evidence for [the canonical document](../../architecture/runtime.md).
