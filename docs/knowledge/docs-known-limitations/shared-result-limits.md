---
{
  "type": "Evidence",
  "id": "docs-known-limitations.shared-result-limits",
  "title": "Current shared result, recovery and workflow limits",
  "description": "Supported application formats, uncertain-submission recovery and workflow form boundaries.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "shared-result-limits",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the image, World and material application format checks, saved GLB import preflight, saved-job actions for uncertain records, cloud history save-for-recovery matching, workflow cancellation availability, interactive-node handling and workflow file inputs against source. Uncertain records expose no action and are matched to cloud history only by a remote job ID. Workflow jobs receive no cancel action; the native workflow form directs file inputs to Library or uploaded asset IDs. Documentation-only review: no native, desktop, live provider or paid run, and no claim that cloud recovery covers every uncertain outcome.",
    "sources": {
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/blender/image_application.py": "aedd8fdad1f92ae4abfe2721a0061189fe94c6dc91f7ff85106ceecc56edb0cc",
      "scenario/blender/material_application.py": "bd8035e8cb12c7ee0b38f3027f02d2c4b654ca01d8d1939943e4bac5afe9ef03",
      "scenario/core/scene/panorama.py": "35c61bed172fa3350a4edf663dd062fb689f58779a6229826897e638ac647e95",
      "scenario/blender/model_application.py": "9fb7eda96afa0e79c26a547c2ddd15404a71c2344652a2bf31a4491442d96ca6",
      "scenario/core/scene/glb.py": "4fa2bb409f66a162dae0f916d00e5504fa0e90b64f3d07f76d74ea36d6dc979c",
      "scenario/core/jobs/store.py": "b05eab9cb9a8a83df55889d94acdbd162521e70f71150c15c46e21b62abc554d",
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/workflow_controls.py": "fed4151d8476ead8c14de00ca3a30e7da3c814b55fd060b43b8f60c6db62ba78",
      "scenario/mcp/tools_scenario.py": "5fa8768f9b8356fb9b5071cf7c889305b06e55905a72d4caf62114f9202b0f4d"
    }
  }
}
---

# Current shared result, recovery and workflow limits

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
