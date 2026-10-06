---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.mesh-export-provenance",
  "title": "Captured mesh export provenance",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "mesh-export-provenance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "45ac4190ff5b528531d7f7abb21e45c1c6720a50",
    "limits": "Inspected pre/post-export source snapshots, immutable exact-byte/source/coordinate metadata, scoped upload persistence and transactional schema-1 upgrade. Export-specific bulk fingerprints have a 256 MiB aggregate per-pass budget across distinct selected datablocks, with bounded string storage and no mesh-application component/type gate. Regressions exercise dense meshes above the edit limit, string/quaternion/matrix/short-vector attributes, source mutation, aggregate rejection before buffer reads/export, and shared-datablock deduplication. Existing tests cover roundtrip coordinates, multi-mesh identities, hash mismatch cleanup, all-scope legacy migration and rollback on corruption. Export remains synchronous and its own time/memory use is not bounded by the snapshot budget. This describes base mesh data and exporter settings, not complete rig/shader/shape-key state, provider alignment, generation quote binding, original-target restoration after restart or automatic application. Export and mesh-application fingerprints use different contracts. No API/dependency change, paid check, new UI surface or release acceptance. Other topics retain their scope. Known capture rejection messages use ScenarioError through the shared UI/MCP upload boundary; regressions verify selection, source/context and file rejection reasons while unexpected exceptions remain sanitized and temporary captures are cleaned before worker admission.",
    "sources": {
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "scenario/core/jobs/upload_store.py": "e5a609291095c112a00184d99795d8d21c177ddc6bc801a5c113bb489df27053",
      "scenario/core/jobs/upload_sources.py": "0178c98d69886cc400785c6a46426c6c35449a0eed317dc77dc07978348c2116",
      "scenario/core/jobs/uploads.py": "198b5591bebeef778c559201c805bf150ec2d7443ebf56d2fbff6c67b5fbb5c3",
      "scenario/core/jobs/workers.py": "86b9ed43e02cff398ab83bdd6f0ddf440691d21b12d4dedddf024715a8611677",
      "scenario/core/jobs/coordinator.py": "969719d07c008b4b718e444d2c6112b053b7ac23351df5a430dfbad36d85eaf3",
      "scenario/blender/job_session.py": "f70cd862d35c149ada785489ea6dfbd00a6f01e9c6d87e5dde5c63c4245dded1",
      "scenario/blender/mesh_provenance.py": "569d17c793421605250ad1c2f77b8d5b417ec644ca1e0fff26fe3b4fdc46df55",
      "scenario/blender/reference_uploads.py": "a43e78f6eaeb194e30ff38310d9c63a6e99fa1c24acfaca3418ada15714af81e",
      "scenario/blender/mesh_export.py": "09361e88cf12290d4d8559355eab17cba196ceb2650ffc67739112c6448de509",
      "tests/unit/test_upload_store.py": "91918364f9c3d39f622221150c08fcb2f5a93a9643eaf383f562a8bc3b931f83",
      "tests/unit/test_upload_sources.py": "65ec8ddae73d30a5f296f178d1f1f50340bcc0f9352a7a1e1b7189aa42974972",
      "tests/blender/test_reference_uploads.py": "93a4d63358cb3c490195e53a82c4c2307e86ed13396c0ce41d7d1a41a84f84b5",
      "tests/blender/test_reference_form.py": "218afa38873131441348d46482d666fc2321ad51f986bfff0f4dd995f1a47e56",
      "scenario/blender/mesh_export_fingerprint.py": "55b40c165f83667d87f61e9007c2fb7fac0097b5d7e90d1dba7ae33ff293dd62"
    }
  }
}
---

# Captured mesh export provenance

Evidence for [the canonical guide](../../SDK_UPLOADS.md).
