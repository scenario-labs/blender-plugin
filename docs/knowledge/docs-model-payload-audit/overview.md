---
{
  "type": "Evidence",
  "id": "docs-model-payload-audit.overview",
  "title": "docs/MODEL_PAYLOAD_AUDIT.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/MODEL_PAYLOAD_AUDIT.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "limits": "Current SDK audit CLI, scope-partitioned live cache, explicit offline inputs and report/threshold/failure behavior reviewed against the selected SDK 2.1.0 artifact and synthetic transport/local-file tests. Existing parser heuristics are retained, not a complete JSON Schema or UI validation. Private per-run defaults and explicit persistent-cache root/scope/ancestor checks reviewed with adversarial directory and cleanup regressions. Offline fixtures retain read-only access; Extended ACL verification, Windows ownership and same-user interference remain outside these checks. Scheduled/manual schema-audit workflow, fresh cache, validated models, attempt-specific report artifact and separate exact-title issue reporter reviewed with offline API fakes and actual shell exit/input/download-outcome regressions. Secrets and issue writes are separated by job; no workflow dispatch, live Scenario read, hosted artifact or failure-deduplication acceptance is claimed. Default temporary-cache teardown failure preserves completed report output, emits a fixed diagnostic and returns exit 2; this failure path is covered by synthetic filesystem regressions without live calls. The weekly reporter includes cache cleanup among exit-2 failure diagnoses; hosted acceptance remains pending. Audit artifact identity is carried from the successful upload through job outputs; report-only reruns, missing identities and failed downloads are covered by offline shell/CLI regressions. This does not establish hosted rerun acceptance. The shared reporter source was separately re-inspected for scoped pagination, exact-title matching, duplicate rejection and uncertain-write handling; only that formerly stale fingerprint is renewed. Re-checked 2026-10-10: audit_one adds the HIGH unparsed-exclusive-input finding when a file description carries an exclusivity marker (params.exclusive_clauses) but parse_schema recognized no sibling file input; recognized pairs are Schema.exclusive and shared validation refuses them. test_audit_payloads covers an unrecognized clause and the captured Seedance 2.0 and Minimax H3 records without that finding. An offline run over the Render Video lane schemas read on that date reported one model, whose excluded sibling is not a file input.",
    "sources": {
      ".github/workflows/api-contract.yml": "05e92f742cf4430e7391b7f5b371792cd136c7dcfc9d69ade90785edaa3bef68",
      "scenario/core/api/catalog.py": "eeb58620545eb0438efc120fe46d7860f7df16e383f3a4b4c55b3282b7b17df9",
      "scenario/core/api/sdk_adapter.py": "a18daa427bd16d7b9bfbf0ed322fe4d7c3bdca27f161db8766f28042ec8e5a0b",
      "scenario/core/schema/forms.py": "f13c662733ae8badc4a16c21f32b545e93c55d8f1dee2c8816cfce8b940df33a",
      "scenario/core/schema/params.py": "17055f6619bef706452ec7282d7ba2121fbf90735a9cd2cfc6a26fa5a52bd889",
      "tests/unit/test_api_contract_workflow.py": "ded66870b2f407678585dfc70759e6b2a337e9b409c1098289ce2c72ee445293",
      "tests/unit/test_audit_payloads.py": "7466425499abfcfe87ece1a53d908dbd464f9d38f70580e4d1ce214194c61bad",
      "tests/unit/test_ci_failure.py": "7025a2956f419582420cd2f45ac16e7f0b9220d13ee5852cde260fa94359913c",
      "tests/unit/test_dev_config.py": "e0f4931e237c4ccf562baa5ba92517130e676228030e474efcf389bc0be4e07e",
      "tools/audit_payloads.py": "4fa342a36dbaca1bce72308f41019fd8d4053713095b1f5bb821f9c90582a8cd",
      "tools/dev_config.py": "c3dbb5a4fb5c96a695f17cb436d15992f7b5efd11238c839d9ab44b9e9c7ac52",
      "tools/report_api_failure.py": "9857af0c95b92b7d984c679a617cbdea7136ebbc6784a08be199e33f17b2310a",
      "tools/report_ci_failure.py": "ee37f34c4ecebee0513f4f4053f004b5ad6401cb60fc1b943abd045cd69fd0b0"
    },
    "scope": "overview",
    "base_revision": "5c605a11ddadd254eab845d068f91349a3c89721"
  }
}
---

# docs/MODEL_PAYLOAD_AUDIT.md: overview

Evidence for [the canonical document](../../MODEL_PAYLOAD_AUDIT.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
