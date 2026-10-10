---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.multipart-part-plan",
  "title": "Create-response part plans, Transfer Acceleration hosts and explicit restart",
  "description": "Signed part URLs come only from the create response, stay in memory and cannot be resumed after restart.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "multipart-part-plan",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the live multipart contract (scenario-sdk 2.2.0: create returns parts, partsCount, fileSize, contentType and originalFileName; retrieve and trigger_action omit them), the in-memory create-plan cache, retrieval liveness checks, plan lifetime, S3UploadPolicy Transfer Acceleration hosts, the ABANDONED state with its atomic replacement write, restart eligibility, recovery suggestions and the shared UI/MCP restart path. Offline tests use live-shaped responses and cover create-plan validation, absent and mismatched retrieval fields, restart before and after partial transfer, expiry, deactivation, lost claim races, in-flight refusal, missing snapshots and no URL persistence. The fixed shared commands completed one live zero-spend PNG upload (create, one PUT, complete, imported) and its dryRun quote through tools.smoke_inputs and tools.smoke_suite. No GUI interaction, desktop screenshot, Blender 5.0/5.2 run, multipart file above one part or media kind other than PNG image was exercised live. The remote pending upload left by an abandoned record is not aborted. Other document claims retain their separate evidence.",
    "sources": {
      "scenario/core/jobs/uploads.py": "4b6220ed463bd8b2e2be62a7fb1b567929161f36233c396efd005690cc6ac3dc",
      "scenario/core/jobs/upload_store.py": "0e8f7a2799779200e666b76699948cd4c00db734fb71a92a26d9181154785f7a",
      "scenario/core/jobs/upload_sources.py": "711517b315c8aca80f154ceecabc64f4c3d3b67c25e5304191c71b6a1ee617e4",
      "scenario/core/jobs/upload_transfers.py": "701fb7833d9d00a5b984b591de201da031751e0a01efc08ef25d5555eeac0b76",
      "scenario/core/jobs/coordinator.py": "bf64e6b76a4ddd71e4023c9b3085e90b1646fe722570b8fb3df0834530c78213",
      "scenario/core/jobs/workers.py": "d99556bbbb1088206de7cf6668cd98031636bddedadb73b433b5bbc0b318ba6c",
      "tools/smoke_inputs.py": "ae7b7cc04bcc60658159ecad4a6a312d8742206ec1aaaf8bc61d511ad4ffc0c2",
      "scenario/blender/job_session.py": "4ca6cc123fbb96a2bfcfc016fee9c2414ca230097c08cbf7c97e6560b0ccd85c",
      "scenario/blender/reference_uploads.py": "0d78fa5712d1740df1d91698b87fb4a6ea4c482768ec249520b84db9826926d5",
      "scenario/blender/reference_form.py": "989a59fb5468988957a212725951643d43887d4bcdf116d65784bf0ce3613041",
      "scenario/mcp/tools_scenario.py": "ed4971751ef19827711d5bbe49b698b89a0d6b35f20627c94ae64b4d1d595592",
      "tests/blender/test_session_uploads.py": "5e209d9d11467a7b4eb6077f228828f583f9d712ce96d7e1331e34017da0588e",
      "tests/blender/test_upload_commands.py": "e307602a701f8e65b06d9129d3bb9f9219062cb80773c3317b4af682471b0b2c",
      "tests/blender/test_reference_uploads.py": "7b3ddfa61ba562200e7258f53bd372d7782608e05cf977a466db1b86e28c109b",
      "tests/blender/test_reference_form.py": "73ccd343f9ddc28d50074ec287e9b449637deea9d6506949bc754efb347ab585",
      "tests/unit/test_upload_commands.py": "02be6873c4c7d6f72a3db1a96e7b2e97553716ab8ff2cb6ee3e4d851a7709d66",
      "tests/unit/test_upload_inspection.py": "018582057616385030e61ad3f727ccd0409b0097ee7825d84dd5c916e51a0780",
      "tests/unit/test_upload_store.py": "df817fcd22d3a90252e896040763875a5d961ff97f1f65b7eea6226124d301e7",
      "tests/unit/test_upload_transfers.py": "14cfa6e0a8dd825c07546fb5d57fdce365be789968ad47eb89322991167dec77",
      "tests/unit/test_smoke_inputs.py": "15d98d707bf503119fdff0a5b5984a441465428b6fd894a8f4f4b40e24bede79"
    }
  }
}
---

# Create-response part plans, Transfer Acceleration hosts and explicit restart

Evidence for [the canonical document](../../SDK_UPLOADS.md).
