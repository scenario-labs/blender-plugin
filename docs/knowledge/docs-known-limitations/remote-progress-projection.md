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
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "e49b0513dbaaa8c7805da01af007b0e0ff0598ac2c52f6d9afd583a9980b4163",
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
