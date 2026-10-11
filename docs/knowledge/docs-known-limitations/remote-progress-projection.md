---
{
  "type": "Evidence",
  "id": "docs-known-limitations.remote-progress-projection",
  "title": "Advisory, unpersisted remote progress",
  "description": "Limits of the shared job progress projection.",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-11",
    "base_revision": "72723f02a97a7226b1c697c31d8124b77ac92c86",
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "8046852c9bb43eca3d5cb0b987c06df473b99e66cbc6cc5b66c245c38ea2f482",
      "scenario/blender/panels.py": "4edcd5c17b73035fa45bcd6e9d6d76252ba4b984a028f544029bf8e76d0aac1b"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
