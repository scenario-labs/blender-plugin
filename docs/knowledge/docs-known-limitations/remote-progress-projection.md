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
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "ff575c16838b19ef950d8825dc80d8d42c1b81f89a3763f5c50245da091fa33a",
      "scenario/blender/panels.py": "683cbe1ba4486ce2e59cc203bbac153d9ea6c31e3f0bc7710cf01bb028019d54"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
