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
      "scenario/core/jobs/store.py": "af6a1aca80668fb15001ca1ac75dabecef5d7118c045a2223caee9b404c844e1"
    }
  }
}
---

# Locally stored trained-model defaults

Evidence for [the canonical document](../../PRIVACY.md).
