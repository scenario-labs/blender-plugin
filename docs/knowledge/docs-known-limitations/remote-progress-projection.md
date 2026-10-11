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
    "base_revision": "1d86f53d3489b23f2447be69cb589140e2f3ba64",
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "5a378d786f8c775bf097673c9962f449a868506e234ed9e829f0d221ad059d4f",
      "scenario/blender/panels.py": "8c9ed56c0d83b4c0cfd4578e7158c05f1df895f7c2765319c0894c1ca0491e83"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
