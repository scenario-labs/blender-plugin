---
{
  "type": "Evidence",
  "id": "docs-releasing.overview",
  "title": "docs/RELEASING.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/RELEASING.md",
    "coverage": "inherited",
    "reviewed_at": "2026-09-24",
    "limits": "Offline repository snapshot section reviewed against exact-inventory validation and failure tests; synthetic and packaged SDK archive generation checked with Blender 5.0.1. Offline release selection and retention reviewed against numeric matrix selection, strict candidate verification and failure tests; selected synthetic archives passed native repository generation and identical replay with Blender 5.0.1. Existing release/publication sections remain inherited, without a fresh claim-by-claim or live verification. These tools do not establish published-release provenance, snapshot completeness, hosting or native update acceptance. Extension-id decision and offline metadata guard section reviewed against manifest tests and runtime storage paths; native validation remains authoritative. Unrelated source fingerprints retain their prior evidence. Version rules inspected against the release configuration; upstream footer/override controls documented without exercising publication.",
    "sources": {
      ".github/workflows/release-please.yml": "8f879d0d9aa9e63d67a18cade277dd7ef081024a9975f983e3c547e3412d659f",
      "release-please-config.json": "f7192922c196556279e00e54b82a8ec82a5fe516481f35771e1ad73c0b00adc9",
      "scenario/blender/runtime.py": "e2aea444fd9ed8568038d709d3e0948a411dd26ba94994bb09efb55a0a2c7e31",
      "scenario/blender_manifest.toml": "7ac4a84b0856f6a7c5ada8182e1c343f097347a25cf5785d81d72b28ec10f444",
      "tests/unit/test_manifest.py": "8f2ad7e74d0af9619cd59b99bb90bc487e9deef8bb7e80bbe0c2fb600131cab2",
      "tests/unit/test_release_inventory.py": "5a5bbffe19bbe34bc4eb1ad23faaa889888eb04b47a76f380e98f884f27b6ce5",
      "tests/unit/test_repository.py": "b6dee9da59ed8bfdec2c9a202f927c6fada49312f3ccb18cfff74f4c80fc9a7b",
      "tools/blender_env.py": "2943b2aaf3bf1de923d078f75635fef439119deb1b5d66da952df878e6a8d428",
      "tools/build.py": "fbbf244b96c4b6ff8f7b4582a00e0c5f0eebbd762acbf9148df7479f23987d9c",
      "tools/release_inventory.py": "44dfc7c3eec4320e0abb0c818ec021468576071183b2ca696e85da0110ac7d51",
      "tools/repository.py": "c41d4cd4964f78acb5fff9d0a20de976d0dcab94e7a14ca24d24e2073e6d191b",
      "tools/wheel_bundle.py": "5189baee1a5381a3be9dd667e0b34357ce6101bd1ea0c7bb03098332ea53c518"
    },
    "scope": "overview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/RELEASING.md: overview

Evidence for [the canonical document](../../RELEASING.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
