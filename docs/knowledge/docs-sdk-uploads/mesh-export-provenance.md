---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.mesh-export-provenance",
  "title": "Captured mesh export provenance",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "mesh-export-provenance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Inspected pre/post-export source snapshots, immutable exact-byte/source/coordinate metadata, scoped upload persistence and transactional schema-1 upgrade. Synthetic tests cover roundtrip coordinates, source mutation rejection, multi-mesh identities, hash mismatch cleanup, all-scope legacy migration and rollback on corruption. This describes base mesh data and exporter settings, not complete rig/shader/shape-key state, provider alignment, generation quote binding, original-target restoration after restart or automatic application. No API/dependency change, paid check, new UI surface or release acceptance. Other topics retain their scope.",
    "sources": {
      "scenario/core/jobs/mesh_source.py": "6448123e64f6d3f012de62b714f2fcffdeb173d530f6fd316d4022f354595229",
      "scenario/core/jobs/upload_store.py": "e5a609291095c112a00184d99795d8d21c177ddc6bc801a5c113bb489df27053",
      "scenario/core/jobs/upload_sources.py": "0178c98d69886cc400785c6a46426c6c35449a0eed317dc77dc07978348c2116",
      "scenario/core/jobs/uploads.py": "198b5591bebeef778c559201c805bf150ec2d7443ebf56d2fbff6c67b5fbb5c3",
      "scenario/core/jobs/workers.py": "86b9ed43e02cff398ab83bdd6f0ddf440691d21b12d4dedddf024715a8611677",
      "scenario/core/jobs/coordinator.py": "bee462236fdf4f20ecbf16dce3880f1b796eb4d050a93ab8923464a6996bad8a",
      "scenario/blender/job_session.py": "69a8594b2a469933762983d409c8a1987410bcbe73beb26ce11ebcc9a899ca9e",
      "scenario/blender/mesh_provenance.py": "e6e6ffd4b928abff5d58319678f5deff2c7775e1c3e71e3b498885c643f63301",
      "scenario/blender/reference_uploads.py": "a43e78f6eaeb194e30ff38310d9c63a6e99fa1c24acfaca3418ada15714af81e",
      "scenario/blender/mesh_export.py": "09361e88cf12290d4d8559355eab17cba196ceb2650ffc67739112c6448de509",
      "tests/unit/test_upload_store.py": "91918364f9c3d39f622221150c08fcb2f5a93a9643eaf383f562a8bc3b931f83",
      "tests/unit/test_upload_sources.py": "65ec8ddae73d30a5f296f178d1f1f50340bcc0f9352a7a1e1b7189aa42974972",
      "tests/blender/test_reference_uploads.py": "8ca8c09de043a2011fd812cf9921c8b4580c4fc929ee3a70dffef3c6000f7285",
      "tests/blender/test_reference_form.py": "218afa38873131441348d46482d666fc2321ad51f986bfff0f4dd995f1a47e56"
    }
  }
}
---

# Captured mesh export provenance

Evidence for [the canonical guide](../../SDK_UPLOADS.md).
