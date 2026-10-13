---
{
  "type": "Evidence",
  "id": "docs-known-limitations.remote-progress-words",
  "title": "Progress bar threshold limit",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "remote-progress-words",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed progress.LABELS and RemoteProgress.percent and their use by panels.draw_shared_status: pending and queued read as queued, warming-up as starting, in-progress as generating and finalizing as finalizing; a percentage is returned only for in-progress and finalizing when the snapped, floored whole percent is at least 1, so 0.005 and 0.0099999 draw no bar. job_strip._REMOTE_TEXT is derived from the same table, capitalized, and its own 1 to 99 percent rule is unchanged. This supersedes the remote-progress-projection topics' note that a fraction below 0.01 draws a 0% bar. Unit tests cover the table, the threshold and the strip words; MCP job_status still reports the raw remote_status and progress fraction, which were not changed. No live provider progress, desktop interaction or screenshot is claimed. Re-checked on 2026-10-12 after the rebase onto main at 4bd0061d, not a full re-review: since the previous review main changed panels.py (Edit 3D lane routing, workflow cost labels, derived history row kinds and cloud history paging); none of these changes touch draw_shared_status, the progress words or the MCP status fields, so the claims above still hold and these sources' fingerprints are the rebased files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 after the stack's base gained main's saved mesh and splat imports, not a full re-review: test_job_strip.py now names import chips by format (Import GLB model, Import alternate: OBJ) and model_jobs.py adds importable units; neither changes the remote progress words or their projection, so the claims above still hold. These sources' fingerprints are the current files'; the review date and base revision are unchanged. Re-checked on 2026-10-12 after the stack was replayed onto main at ff8d29d8 (Environment lane, compact composer job strip), not a full re-review: main's job strip already took its remote words from progress.LABELS under the REMOTE_LABELS alias, which the merge keeps, so the strip now reads Queued, Starting, Generating and Finalizing with this PR's table; main's strip tests expect Queued for pending and Finalizing for finalizing accordingly. panels.py gained a non-collapsible draw for the composer's job card and studio.py a popup tracking helper, which change neither the progress words nor the preview tiles. These sources' fingerprints are the rebased files'; the review date and base revision are unchanged. On 2026-10-13 the job_strip.py, test_job_strip.py fingerprints were refreshed after a failed job's strip status gained the reason Scenario gave ('Generation failed: ' and the reason, still in the error tone) and the composer's job card started declaring its requested popup width to label_wrap; the new tests cover both. This topic's statements were rechecked against that change and still hold; only fingerprints that matched main before it were refreshed, other drift is left as it was, and the review date is unchanged.",
    "sources": {
      "scenario/core/jobs/progress.py": "550ef71b269daa26141588afff3a6377cb5d0c89ef2ebac799750718ca4ba1fd",
      "scenario/core/ui/job_strip.py": "9526afc75d309886c8f7821b1250e6b5f6cb4d3f776b845417f563e8c485d0ab",
      "scenario/blender/panels.py": "7a75a937fa6de85ca92da5a158dd1efc5a7f0b2fb96e98394a40e63ce8556a72",
      "tests/unit/test_job_progress.py": "c5b7c5b626640a806c8cb09256d770a27d58aad47f81fa7f31e4140915cf77c9",
      "tests/unit/test_job_strip.py": "a5a29129792cd11012f241501c2ba0ceb38c684688c0e854fb87f41a91631260"
    }
  }
}
---

# Progress bar threshold limit

Evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
