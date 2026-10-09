---
{
  "type": "Evidence",
  "id": "docs-user-guide.material-lane-guidance",
  "title": "Materials lane result guidance",
  "description": "Materials generation saves texture sets; assignment needs explicit saved-material approval.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "material-lane-guidance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Shared ModelJobs submission marks only Image-lane jobs for automatic application; Materials jobs stop at saved ready results. Unbound job_done events cannot invoke the prototype material callback, which is the only reader of the target_objects metadata still recorded at submission. Ready saved jobs are non-terminal views drawn in the Jobs panel, where Apply saved material targets the active mesh's active slot after confirmation. The Materials lane draws one static hint without reading selection. An installed native regression asserts that hint with and without a selected mesh on Blender 5.1.2 macOS arm64 only. The Materials screenshot predates this hint and still shows the former selection wording. This review does not cover the Tiling control, physical focus/DPI review, other Blender versions or live provider output, and does not establish full Materials or release acceptance.",
    "sources": {
      "scenario/blender/panels.py": "ab3fb26799d66c6e1be50c65babd152e4be496321f4eaea41bafb236c9aa787b",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/blender/generation.py": "d09d69727d3eadc999615ff8e969f982ccc454b20accf4490c2e66093bb0abe4",
      "scenario/blender/apply_material.py": "b8de96e6f25e62b1372e129af31f762d11cb5ce2c3388b77647ee747f4d5566c",
      "scenario/blender/handlers.py": "699dba07a70d4b796f29e2e52799abb62d2ae7d0595b484c1f984f156cae1834",
      "tests/blender/test_material_lane.py": "46df6f83a395bddb1ddcab979939809e8dcbd5a1e990b1d01bbcb12a32de2dc7",
      "tests/blender/test_generation.py": "893b2601f6b694417878ad9d66a703fa6631f133090173b1a28687f135ae961a"
    }
  }
}
---

# Materials lane result guidance

Evidence for [the canonical document](../../USER_GUIDE.md).
