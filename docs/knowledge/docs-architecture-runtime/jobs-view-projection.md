---
{
  "type": "Evidence",
  "id": "docs-architecture-runtime.jobs-view-projection",
  "title": "Scoped model job display projection",
  "evidence": {
    "path": "docs/architecture/runtime.md",
    "scope": "jobs-view-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-06",
    "base_revision": "4589f22964cc9cf99e53ec37bb8c5dbe6948c96b",
    "limits": "Shared model pump, inspection, recovery and submission replace authoritative views by local ID while retaining all shared rows and their stable observed order. The fifty-row limit applies only to prototype rows. Native regressions cover duplicate IDs, legacy collisions, more than fifty shared rows, an active recovered zero-timestamp row, hydration and repeated ticks. This display policy does not cap durable storage or worker lifetime and adds no new controls or desktop input proof.",
    "sources": {
      "scenario/blender/runtime.py": "d7ba35bfa11867c1489ff8943fd468d170ec9fa7cf51e25956b3d0e6da158f18",
      "scenario/blender/generation.py": "0d53b27213d1eb0f476bf46e13e96b51afdd85b7ca921462bdf87e3853940b7e",
      "scenario/blender/model_jobs.py": "615c411c9a961e1b410ef5905ff3a1b8016cccd3fd9a69af824aa4a911c45569",
      "tests/blender/test_model_generation.py": "3eb80e5b9328d575568736c51291118b0046045191aceff7c537de1fd178f7c7"
    }
  }
}
---

Source evidence for [the runtime guide](../../architecture/runtime.md).
