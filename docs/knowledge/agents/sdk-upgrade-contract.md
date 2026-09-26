---
{
  "type": "Evidence",
  "id": "agents.sdk-upgrade-contract",
  "title": "SDK version and extension contract",
  "description": "Current SDK release and named extension workflow.",
  "evidence": {
    "path": "AGENTS.md",
    "scope": "sdk-upgrade-contract",
    "coverage": "policy",
    "reviewed_at": "2026-09-26",
    "base_revision": "92d7d576b84b0c09767ca50a35cc99908666994e",
    "limits": "Policy review records Python SDK documentation first, API reference and verified first-party contract fallback, named SDK extensions through the configured client, and optional API-key tenant discovery. This does not establish live endpoint acceptance.",
    "sources": {
      "AGENTS.md": "a3ee2633c9f5d560d0f9aa5f024145e58a322fa81bb213d1e5e567c5fc8371e9",
      "scenario/core/api/sdk_extensions.py": "dc084216172a704ab1453811f9e2c9c1b9755af55fee7c2fa305704449b9a369",
      "docs/SDK_ADOPTION.md": "6650e3bc8655d175480eb399de84b5abf2099496dd4f0ea74949bb28064c33a4"
    }
  }
}
---

# SDK version and extension contract

Evidence for [the canonical document](../../../AGENTS.md).
