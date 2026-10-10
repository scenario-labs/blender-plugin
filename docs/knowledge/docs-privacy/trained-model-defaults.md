---
{
  "type": "Evidence",
  "id": "docs-privacy.trained-model-defaults",
  "title": "Locally stored trained-model defaults",
  "description": "What the job database keeps for saved lane defaults.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "trained-model-defaults",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the trained_defaults row contents: scope identity, lane, route, model IDs and optional strengths, without prompts, schemas, thumbnails or URLs. No saving surface exists yet; no legal-policy audit.",
    "sources": {
      "scenario/core/jobs/store.py": "5e94feb941bd943939901be0b8e0e447e424da24635cf28b5f44f7f159c60ec6"
    }
  }
}
---

# Locally stored trained-model defaults

Evidence for [the canonical document](../../PRIVACY.md).
