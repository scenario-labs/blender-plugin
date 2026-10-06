---
{
  "type": "Evidence",
  "id": "docs-ui-style.mirrored-source-review",
  "title": "Mirrored source coordinate review",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "mirrored-source-review",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "82f0abb2e8fe4cdeab78558c17491e250459bc77",
    "limits": "Reviewed native initial coordinate selection for mirrored/zero-scale sources, read-only explanatory UI, unchanged explicit MCP WORLD rejection, and the shared option validation. Tests cover negative, zero and positive determinants, unsupported option rejection/recovery, cancellation and preserved source transforms. The exact ZIP (SHA256 21edce46cf2c0e94095ba27668c2acef3b6b68968dc0dc0082921f1bd0760000) passes 670 native tests on each of macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1. Isolated Blender 5.1.2 desktop interaction exercised the mirrored-source dialog, Escape, coordinate choices, Return, viewport selection/front-view/zoom and separate completed-result reuse. The process exited cleanly with unchanged normal-profile fingerprints and no extra mocked service requests or submissions. Zero-scale behavior has headless native coverage only. No other OS desktop, provider alignment or release acceptance. Other topics retain their own evidence and source-drift warnings. The captured-source follow-up resolves the retained target before selecting the native coordinate default and explanation; the active selection cannot retarget or alter this choice. Three installed regressions cover mirrored/zero-scale captured sources beside a positive-scale selection and a positive-scale source beside a mirrored selection, unchanged strict MCP WORLD requests, cancellation and unchanged jobs/scene/request counts. The follow-up ZIP 03074fe0f5ff70e360e392502a14064f36312dd463058866edeeee58077c541e passes 719 native tests per supported macOS arm64 Blender version. Fresh isolated 5.1.2 desktop input opens the captured mirrored-source dialog while another positive-scale mesh is selected, cancels with Escape, confirms with Return, preserves the captured negative scale, and verifies native Edit Undo/Redo, viewport focus/front view/zoom, unchanged saved job/request counts, clean exit and normal-profile preservation. Historical screenshots remain tied to their named ZIP; zero-scale/reversed-selection and other-platform limits remain explicit.",
    "sources": {
      "scenario/blender/job_recovery.py": "aec651ea38c16357127a9eb78f1e44fb0bbc5062de3dd42b633e1410f78b9637",
      "scenario/blender/model_jobs.py": "b0a643a4f2c0306df401cde5eebec1ceea63da11d57d3cb3a41432fb7ad6f90f",
      "tests/blender/test_model_generation.py": "367d9dbc51a456fc0dda2484f998918ae6034a4435d3d70f60c907975ce687e7",
      "docs/images/mirrored-mesh-before.png": "26550f045da820bb7a77f6857143356b21e83ba8e58c631ca1bd051b6898a45e",
      "docs/images/mirrored-mesh-approval.png": "6b1b1ff17210855949eb246835df377eef68238174c969518243c45ab570177b",
      "docs/images/mirrored-mesh-result.png": "4e2a09a04bce625f6735f1e278b5285f9b58d37fd7d3717069819e1600c406a7",
      "docs/images/captured-mirrored-mesh-approval.png": "191baf9dd0d988d23466e12a6d24f99fa5e5a99ee3bc79ae4f7fb93fac398120"
    }
  }
}
---

# Mirrored source coordinate review

Evidence for [the canonical guide](../../UI_STYLE.md).
