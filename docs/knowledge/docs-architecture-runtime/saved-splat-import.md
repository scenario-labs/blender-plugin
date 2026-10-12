---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.saved-splat-import",
  "title": "Saved Gaussian splat import",
  "description": "Runtime map sentence for worker-decoded splats built as point clouds.",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "saved-splat-import",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the runtime map's saved model sentence against ModelJobs and JobSession: SPZ, .splat and Gaussian PLY results are decoded in the local-operation slot with reviewed options and built on the main thread as a new mesh, Geometry Nodes group and material under the same claim and receipt rules. The full installed suite passed 1,271 tests with 2 Windows-only skips on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1; Linux and Windows CI runs are not claimed. In-place rig transfer remains open.",
    "sources": {
      "scenario/blender/model_jobs.py": "6d091ac315d207654aa209d3b84b5ea51b85dbf8fbf1eba02423dccc64471a4d",
      "scenario/blender/job_session.py": "3ab7ea580ca986f9d86eb7a0735a96293627aa53016cc4172820fdc184e98163",
      "scenario/blender/splat_application.py": "0395a8ce98a15e45d2d7dc78ad4b3f4b0e1578b1b97010b00b70670cabf7454a",
      "scenario/core/jobs/workers.py": "2d7b0820062d5a702d742f64fa25fd6c9ca472f0d1f258c7ea8fd17f81a2ba0a",
      "tests/blender/test_model_generation.py": "5e9481456f39de8b2fb18913ed38c73c72180424c953ab578f267c09e0377669"
    }
  }
}
---

# Saved Gaussian splat import

Evidence for [the canonical document](../../architecture/runtime.md).
