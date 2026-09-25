---
{
  "type": "Evidence",
  "id": "docs-model-payload-audit.overview",
  "title": "docs/MODEL_PAYLOAD_AUDIT.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/MODEL_PAYLOAD_AUDIT.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "limits": "Current SDK audit CLI, scope-partitioned live cache, explicit offline inputs and report/threshold/failure behavior reviewed against the selected SDK 2.1.0 artifact and synthetic transport/local-file tests. Existing parser heuristics are retained, not a complete JSON Schema or UI validation. No live service acceptance, weekly workflow or failure-issue automation is claimed. Private per-run defaults and explicit persistent-cache root/scope/ancestor checks reviewed with adversarial directory and cleanup regressions. Offline fixtures retain read-only access; Extended ACL verification, Windows ownership and same-user interference remain outside these checks. Default temporary-cache teardown failure preserves completed report output, emits a fixed diagnostic and returns exit 2; this failure path is covered by synthetic filesystem regressions without live calls.",
    "sources": {
      "scenario/core/api/catalog.py": "eeb58620545eb0438efc120fe46d7860f7df16e383f3a4b4c55b3282b7b17df9",
      "scenario/core/api/sdk_adapter.py": "a18daa427bd16d7b9bfbf0ed322fe4d7c3bdca27f161db8766f28042ec8e5a0b",
      "scenario/core/schema/forms.py": "f13c662733ae8badc4a16c21f32b545e93c55d8f1dee2c8816cfce8b940df33a",
      "scenario/core/schema/params.py": "b26c51fbe84dd3eb71a690c39231ff8a332ef42d937b574e3c1102e97d8cd8e7",
      "tests/unit/test_audit_payloads.py": "93974c49bb4affdd41f6d1949d1ca156269bd9c21c02bf6d22b4f59bfc0540f2",
      "tests/unit/test_dev_config.py": "e0f4931e237c4ccf562baa5ba92517130e676228030e474efcf389bc0be4e07e",
      "tools/audit_payloads.py": "518a4d1972faf72298f3dadc5d8656e2b17be67fb31ed3fd93263ff62ffef257",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52"
    },
    "scope": "overview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/MODEL_PAYLOAD_AUDIT.md: overview

Evidence for [the canonical document](../../MODEL_PAYLOAD_AUDIT.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
