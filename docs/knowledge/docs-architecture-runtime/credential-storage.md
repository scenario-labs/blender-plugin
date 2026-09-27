---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.credential-storage",
  "title": "Credential-bound local job storage",
  "description": "Local API-key scope and its active catalog binding, without server identity discovery.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "credential-storage",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "40c844be54ce827bc84d23fcd2d56505be941f7a",
    "limits": "Inspected local HMAC scope derivation, complete key publication under an OS-held lock without hard links, scoped JobStore access and active catalog/store retirement. Offline unit tests cover restart, key/secret/service/team/project isolation, thread/process concurrent initialization, bounded lock contention, unsupported-hard-link initialization, malformed or missing key preservation and filesystem failures. Installed native tests cover runtime reset, selected credential source, credential retirement and missing-key failure with network disabled. Local identities are not server principal claims; storage is not encryption. No shared JobSession activation, paid generation, prototype migration, project selector or live tenant validation is claimed. Existing parent permissions and Windows ACLs remain caller-owned. New scope lock files remain empty to avoid pre-lock sentinel writes under Windows mandatory locking.",
    "sources": {
      "scenario/core/jobs/credential_storage.py": "add164599e440041f76f94f9347114d829a0df3ef2e158cf533b8084805da074",
      "scenario/core/jobs/store.py": "8cc29310bcdc8ab633fed2382e11865aa4995ba45bb316db7141de3b9d1f1e4b",
      "scenario/core/api/sdk_catalog.py": "8b3964e8d8e2a0112445e76fef75e1a2b3bf4819d23ac3856cadfa0b690c8b23",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "scenario/blender/runtime.py": "2c170dc783d50332ee060854d90298b3e34d172a1cc1fe35ad7c4f625eabab78",
      "tests/unit/test_credential_storage.py": "3355b3a0b02545f8e621c9545eae01110ce44cf5add590bf5768821039b4db94",
      "tests/unit/test_sdk_catalog.py": "ccec2dcb8cb0e1b75bd9f0b82c909fde5ba47df8b06886058e1ce21078eeef29",
      "tests/blender/test_credential_storage.py": "41a2e52361595bae7700b03a8f39a4c385530a6d29b524a9e0f1b0fb04ec049e"
    }
  }
}
---

# Credential-bound local job storage

Evidence for [the canonical document](../../architecture/runtime.md).
