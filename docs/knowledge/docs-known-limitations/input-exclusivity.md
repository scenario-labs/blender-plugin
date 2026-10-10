---
{
  "type": "Evidence",
  "id": "docs-known-limitations.input-exclusivity",
  "title": "Input exclusivity limits",
  "description": "What the shared guard refuses for inputs described as not combinable, and what it leaves to the service.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "limits": "Reviewed 2026-10-10. params.parse_schema records Schema.exclusive from file-input descriptions only (exclusive_clauses markers, clause_inputs label words and the reference fallback) and keeps file-input pairs only; params.validate_requirements refuses a body defining both members. That check runs in generation.build_request for every native lane, forms.prepare_run (so SDKAdapter quotes and submissions) and the MCP raw-body path in tools_scenario._body_for; unit tests cover the captured Seedance 2.0 and Minimax H3 records, Seedance 2.0 Mini and Wan 3.0 wording, refusal with no request, and a Kling-worded setting that is never refused; an installed test_render_lanes test covers the base Video lane refusal. The 11-model count, the lanes named for them (catalog.models_for_lane, which hides deprecated models) and the setting examples come from a free GET-only read of the 709 public models and the 67 curated schemas that day, without a project override; they are service observations that can change, not fixtures. Whether the service rejects each described combination, and whether a dry run checks it, was not tested for the setting examples. tools/audit_payloads.exclusive_findings reads only clauses after the params.EXCLUSIVE_MARKERS phrases (mutually exclusive with; can't, cannot or can not be combined with) and reports HIGH only for a file clause naming no sibling input and MED for such a clause with a setting on either side; other wording is not reported. The weekly workflow keeps --fail-on HIGH, and the offline run over the curated schemas that day exited 0. Re-checked 2026-10-10 for the audit wording: over the 67 cached curated schemas the offline run at --fail-on HIGH exits 0 with MED unguarded-exclusive-setting findings only for Kling V3 Omni Generate Audio, Meshy 7 Multi-Image to 3D and Tripo v3.0 Texturing (plus the unrelated Trellis 2 Retexture multiple-required-files). Luma Ray 3.2 Edit, Meshy 7.1 Multi-Image to 3D, Recraft V4 Styles and Meshy Smart Topology are not curated; run on them from the cached public schemas with --models, the tool lists each at MED. Kling V3 Omni's 4K mode (its reference video says Not supported with 4K, its mode says 4K mode does not support reference video) and its reference-image count (Max 7 without video, 4 with video) use no marker, so the audit reports neither. No native desktop or paid run is claimed.",
    "sources": {
      "scenario/core/schema/params.py": "c94572f3737be87f1f419fb082664b6abe2ade2eca344ba22de589734dae85bb",
      "scenario/core/schema/forms.py": "ef906b4563ccbbd1862a6b8073ad9feb79b9cc1fc15c264caaa02bae30c6c098",
      "scenario/blender/generation.py": "6a4cfa47b950e48488dd5bb5acd122d7310662934b68de7e1c2b089b1a7dbc6d",
      "scenario/mcp/tools_scenario.py": "aec3eb343134655b437721bcecc6504e8cb7ef5013bf8c8ddfb8bf2d111e12fc",
      "scenario/core/api/catalog.py": "b6ba46cea2581665879d6083330fa2aae536af42b31c80420f16ba49e92fb08f",
      "tools/audit_payloads.py": "bc72f41c8aaabaa2554dad87aea6c8bf9368b54a2d1626ec0e80622f6ba76063",
      ".github/workflows/api-contract.yml": "05e92f742cf4430e7391b7f5b371792cd136c7dcfc9d69ade90785edaa3bef68",
      "tests/unit/test_model_payload_validation.py": "c6316ccd6b9e9869e23173172c92162447168fa5e2cd4359cc94491cc448b9cf",
      "tests/unit/test_audit_payloads.py": "6ff851e4204783affeaacc70b6f0c1c2d85a488c271659ead8ea020dfb7dfafd",
      "tests/blender/test_render_lanes.py": "6bb71ad049498cd2a942c231c6876bacbd8d284ec580c4eb4e4fc06a7d3f0aaf"
    },
    "scope": "input-exclusivity",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b"
  }
}
---

# Input exclusivity limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
