---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.credential-storage",
  "title": "Credential-bound local job storage",
  "description": "Local API-key scope and its active catalog binding, without server identity discovery.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "credential-storage",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "40c844be54ce827bc84d23fcd2d56505be941f7a",
    "limits": "Inspected local HMAC scope derivation, complete key publication, scoped JobStore access and active catalog/store retirement. Offline unit tests cover restart, key/secret/service/team/project isolation, concurrent initialization, malformed or missing key preservation and filesystem failures. Installed native tests cover runtime reset, selected credential source, credential retirement and missing-key failure with network disabled. Local identities are not server principal claims; storage is not encryption. No shared JobSession activation, paid generation, prototype migration, project selector or live tenant validation is claimed. Existing parent permissions and Windows ACLs remain caller-owned.",
    "sources": {
      "scenario/core/jobs/credential_storage.py": "15694a9c7b1f5ef9570da5655e11ffa2580612034d8989edbd72e8bd56f2e4f0",
      "scenario/core/jobs/store.py": "8cc29310bcdc8ab633fed2382e11865aa4995ba45bb316db7141de3b9d1f1e4b",
      "scenario/core/api/sdk_catalog.py": "8b3964e8d8e2a0112445e76fef75e1a2b3bf4819d23ac3856cadfa0b690c8b23",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "scenario/blender/runtime.py": "2c170dc783d50332ee060854d90298b3e34d172a1cc1fe35ad7c4f625eabab78",
      "tests/unit/test_credential_storage.py": "e1f237c4ab30089f9a4c6dabed2b9c8a23d6243688ac8ffedf534e25c60799bd",
      "tests/unit/test_sdk_catalog.py": "ccec2dcb8cb0e1b75bd9f0b82c909fde5ba47df8b06886058e1ce21078eeef29",
      "tests/blender/test_credential_storage.py": "c3c14c4ed1a7f7baff40435009411128e481dcfde149f946f89cf50d1aea77e9"
    }
  }
}
---

# Credential-bound local job storage

Evidence for [the canonical document](../../SDK_ADOPTION.md).
