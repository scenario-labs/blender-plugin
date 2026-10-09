---
{
  "type": "Evidence",
  "id": "docs-development-validation.model-defaults-update-state",
  "title": "Trained-model defaults through the runtime owner across native updates",
  "description": "Owner seeding, owner reads after update and restart, and project isolation of defaults.",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "model-defaults-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the package probe's model_defaults_owner, check_model_defaults (scope equality, per-lane and listed equality with the store, a nonempty saved list), seeding through the owner when the seeding package has one, the restart comparison against the update evidence, the project check of saved and cleared defaults for the same credentials with the default scope and another project, and the runner's model_defaults_preserved expectation read from the candidate archive's core/jobs/model_defaults.py without importing it. Unit tests cover the probe helpers and the runner with candidates with and without the owner, including false or unsupported claims that fail the run. On macOS arm64 Blender 5.1.2 with the candidate ZIP above (sha256 0d675ed1734d9080f7845e678df1c741b2151e3ffc0be36efc59d6258f9db6a1), tools/test_repository_update.py --test-predecessor passed three times with model_defaults_preserved true after update and restart: a candidate-derived predecessor (schema 10 to 10, seeded through the predecessor owner), a predecessor built from the parent PR head 7d209054 (ZIP sha256 2bea7dd3c1f5ab3dbf034318b0ddb33af37b1fe42b4484d9f03531d487cf284c; schema 10 without the owner, seeded through the store) and one built from main 33d00b05 (ZIP sha256 822e504777f582e1634c4db499d8ec753d796945735846eaa08f90e2af45d97a; schema 9, upgraded and then seeded through the candidate owner, predecessor reopen refused with the store unchanged). All predecessors carry synthetic 0.0.0 version metadata, not published release pairs. Blender 5.0, 5.2, Linux and Windows were not run.",
    "sources": {
      "tests/blender/package_update.py": "175ac89f4cc3e233802b3ab287fb089456dbfd81a789701c2c19bd2c1c99120e",
      "tools/test_repository_update.py": "7ec2a6a704cb25446e2a91fdb99fc8675315c8cc2a04e15dd033e863767b6c33",
      "tests/unit/test_repository_update_runner.py": "f12334508b61b8c54aac27dfd7dd2f2dd1885dc124356e534d02538af20ce052",
      "scenario/blender/runtime.py": "4389630c31be63af3ca76f146712d3d4ca197550ae04899bd1e80c394bde637a",
      "scenario/core/jobs/model_defaults.py": "1e4fbf2f0cfb8de6cefd1a45ea82bbb0ecad9a1dd179f3a98b71519ca61dd93d"
    }
  }
}
---

# Trained-model defaults through the runtime owner across native updates

Evidence for [the canonical document](../../development/validation.md).
