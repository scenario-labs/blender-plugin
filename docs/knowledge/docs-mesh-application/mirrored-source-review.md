---
{
  "type": "Evidence",
  "id": "docs-mesh-application.mirrored-source-review",
  "title": "Mirrored source approval and local history",
  "evidence": {
    "path": "docs/MESH_APPLICATION.md",
    "scope": "mirrored-source-review",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed native initial coordinate selection for mirrored/zero-scale sources, read-only explanatory UI, unchanged explicit MCP WORLD rejection, and the shared option validation. Tests cover negative, zero and positive determinants, unsupported option rejection/recovery, cancellation and preserved source transforms. The exact ZIP (SHA256 21edce46cf2c0e94095ba27668c2acef3b6b68968dc0dc0082921f1bd0760000) passes 670 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Isolated Blender 5.1.2 desktop interaction exercised the mirrored-source dialog, Escape, coordinate choices, Return, viewport selection/front-view/zoom and separate completed-result reuse. The process exited cleanly with unchanged normal-profile fingerprints and no extra mocked service requests or submissions. Zero-scale behavior has headless native coverage only. No other OS desktop, provider alignment or release acceptance. Reviewed the new mesh_edit local-application purpose through the session claim, storage allowlist, persisted decoding and status projection. Native and unit regressions distinguish model imports from mesh replacements after reopening storage and retain the original generation record and existing purpose labels. No schema field or version change, historical reclassification, live provider or global undo claim. Other topics retain their own evidence and source-drift warnings. The captured-source follow-up resolves the retained target before selecting the native coordinate default and explanation; the active selection cannot retarget or alter this choice. Three installed regressions cover mirrored/zero-scale captured sources beside a positive-scale selection and a positive-scale source beside a mirrored selection, unchanged strict MCP WORLD requests, cancellation and unchanged jobs/scene/request counts. The follow-up ZIP 03074fe0f5ff70e360e392502a14064f36312dd463058866edeeee58077c541e passes 719 native tests per supported macOS arm64 Blender version. Fresh isolated 5.1.2 desktop input opens the captured mirrored-source dialog while another positive-scale mesh is selected, cancels with Escape, confirms with Return, preserves the captured negative scale, and verifies native Edit Undo/Redo, viewport focus/front view/zoom, unchanged saved job/request counts, clean exit and normal-profile preservation. Historical screenshots remain tied to their named ZIP; zero-scale/reversed-selection and other-platform limits remain explicit.",
    "sources": {
      "scenario/blender/job_recovery.py": "aec651ea38c16357127a9eb78f1e44fb0bbc5062de3dd42b633e1410f78b9637",
      "scenario/blender/model_jobs.py": "b0a643a4f2c0306df401cde5eebec1ceea63da11d57d3cb3a41432fb7ad6f90f",
      "scenario/blender/job_session.py": "9aed31fe6298e1c80c33899e19dc8cd2735539706843c9e4c0b334d054837fcb",
      "scenario/core/jobs/store.py": "39148598ed88286b9933dcf4fe52e847d7ab073999a2c581c2f971e882a0911c",
      "tests/blender/test_model_generation.py": "367d9dbc51a456fc0dda2484f998918ae6034a4435d3d70f60c907975ce687e7",
      "tests/unit/test_job_store.py": "5261ac660f822580f26c2ec6a29c31ee2dafad1e96d9032f60db2b0b3fe437dd"
    }
  }
}
---

# Mirrored source approval and local history

Evidence for [the canonical guide](../../MESH_APPLICATION.md).
