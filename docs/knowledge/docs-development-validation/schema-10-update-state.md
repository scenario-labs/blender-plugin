---
{
  "type": "Evidence",
  "id": "docs-development-validation.schema-10-update-state",
  "title": "Schema 10 state and real predecessor code across native updates",
  "description": "Store schema evidence, schema 10 seeding and previous-ZIP test predecessors.",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "schema-10-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the package probe's store_schema reports, schema 10 seeding before update or after the post-update upgrade, its restart checks, and the runner's archive schema parsing and --previous-zip --test-predecessor mode. On macOS arm64 Blender 5.1.2 a predecessor built from b57c398f (ZIP sha256 18b5dab6a335f9e3390a9f0982c2d97fe6a698fd5717d6729bbecd3b4833f418, schema 9) was upgraded through the native updater to a candidate built from this change (ZIP sha256 317d3f6b867aefcd5e0297eed948d2ce7cb37e0384cb822f46fd75dfa98ae883, schema 10): all six prior jobs, the other scope, uploads, mesh and Film bindings, local claims, workflow references and scene survived update and offline restart, and the schema 10 state written after the upgrade survived restart. A candidate-derived predecessor run also passed with schema 10 seeded before update. Both predecessors are synthetic 0.0.0 version metadata, not published release pairs. Blender 5.0, 5.2, Linux and Windows were not run for this change.",
    "sources": {
      "tests/blender/package_update.py": "55924e344010e52cc51dbe1de73cb96a8390e1835964e046057b0d06512e7e07",
      "tools/test_repository_update.py": "52b4b296d3e83e80e9f754ed0b18dc87d153c8ab5415e266d900aa4f1b0e4066",
      "tests/unit/test_repository_update_runner.py": "24f957fdb4676e52bb42b5363192b0b69c82e84c27fa40e9049afaa2c2d58629",
      "scenario/core/jobs/store.py": "af6a1aca80668fb15001ca1ac75dabecef5d7118c045a2223caee9b404c844e1"
    }
  }
}
---

# Schema 10 state and real predecessor code across native updates

Evidence for [the canonical document](../../development/validation.md).
