---
{
  "type": "Evidence",
  "id": "docs-blender-job-context.saved-reuse-output-status",
  "title": "Session output status across reuse",
  "evidence": {
    "path": "docs/BLENDER_JOB_CONTEXT.md",
    "scope": "saved-reuse-output-status",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "a3f9ea976a2a425729f55b6f5a09607c5d473328",
    "limits": "Reviewed current-session aggregation of image, model-object and material references across original and repeated saved-result application. Native regressions cover earlier output visibility, deleted references, reused Blender display names and deduplication after receipt-only recovery, including a lost receipt response. Known scene outputs remain visible during receipt recovery while durable uncertainty still blocks replay. This changes inspection only, not claims, generation, World restoration ownership or persistence. Names are not durable IDs; retired sessions do not reconstruct these references. No new UI interaction, service operation, provider quality, other-OS desktop or release acceptance is claimed.",
    "sources": {
      "scenario/blender/model_jobs.py": "2253264d13af5bf88fff09901ab21a1d96cbceaf7448ee36fdf64db4606d1ef8",
      "tests/blender/test_model_generation.py": "517564ac7aa499e9bc60df41fc2a4a9adc727497018f09750597a6be08f87917"
    }
  }
}
---

# Session output status across reuse

Evidence for [the canonical guide](../../BLENDER_JOB_CONTEXT.md).
