---
{
  "type": "Evidence",
  "id": "docs-user-guide.remote-progress-words",
  "title": "Jobs progress words in the user guide",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "remote-progress-words",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed progress.LABELS and RemoteProgress.percent and their use by panels.draw_shared_status: pending and queued read as queued, warming-up as starting, in-progress as generating and finalizing as finalizing; a percentage is returned only for in-progress and finalizing when the snapped, floored whole percent is at least 1, so 0.005 and 0.0099999 draw no bar. job_strip._REMOTE_TEXT is derived from the same table, capitalized, and its own 1 to 99 percent rule is unchanged. This supersedes the remote-progress-projection topics' note that a fraction below 0.01 draws a 0% bar. Unit tests cover the table, the threshold and the strip words; MCP job_status still reports the raw remote_status and progress fraction, which were not changed. No live provider progress, desktop interaction or screenshot is claimed.",
    "sources": {
      "scenario/core/jobs/progress.py": "550ef71b269daa26141588afff3a6377cb5d0c89ef2ebac799750718ca4ba1fd",
      "scenario/core/ui/job_strip.py": "8009e4658006e5127f3fade2e51bedd01a3642e90f44b40ca2789e58512d3c44",
      "scenario/blender/panels.py": "c5ba66faaa0b5732a75e5519a4f6755fc06ef2db07374686835cf5ba32ab5389",
      "tests/unit/test_job_progress.py": "c5b7c5b626640a806c8cb09256d770a27d58aad47f81fa7f31e4140915cf77c9",
      "tests/unit/test_job_strip.py": "067fa57d8bc9d64af32fcfddb475e014313c7feb7c025bbe5ae5363888ebbe4b"
    }
  }
}
---

# Jobs progress words in the user guide

Evidence for [the canonical guide](../../USER_GUIDE.md).
