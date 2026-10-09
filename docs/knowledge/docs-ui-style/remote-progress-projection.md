---
{
  "type": "Evidence",
  "id": "docs-ui-style.remote-progress-projection",
  "title": "Jobs status words and progress bar",
  "description": "UI rule for shared Jobs rows, the progress bar and stale lines.",
  "evidence": {
    "path": "docs/UI_STYLE.md",
    "scope": "remote-progress-projection",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "fb699b8555f7cee62147794516cc7aaa224864f7",
    "limits": "Reviewed panels.draw_shared_status and draw_active_job: shared rows map saved states to words, use the reading's status word only in the remote state, draw UILayout.progress with the snapped, floored percentage only when percent is known, and with online access off add the SHARED_OFFLINE_TEXT line for remote, cancel_requested and succeeded rows whether or not a reading exists; otherwise a stale reading adds Status is not updating. A measured fraction below 0.01 floors to a 0% bar. SCENARIO_PT_jobs and SCENARIO_PT_generations split rows with JobRecord.is_terminal; ModelJobs.poll gives a SUCCEEDED view the non-terminal display status awaiting-download through _DISPLAY_STATUS, so a job that finished on Scenario stays a Jobs row with its finished on Scenario word and offline Download paused line, and Generations does not draw it before its results are saved. Prototype rows keep their previous text. Studio Jobs reuses SCENARIO_PT_jobs.draw. Installed tests check the label, bar arguments, offline lines with and without a reading, a real job drained to succeeded with online access off and drawn through SCENARIO_PT_jobs.draw_header and draw (1 Job, the finished on Scenario label and the Download paused line, no bar) while SCENARIO_PT_generations.draw does not draw it, that SHARED_OFFLINE_TEXT names exactly ModelJobs.NEEDS_SCENARIO, the stale line, the canceling label with a rebound reading, that drawing performs no store reads, ensure calls or meta writes, and pump redraw counts including an online access change. Installed native tests on macOS arm64 Blender 5.0.1, 5.1.2 and 5.2.1 cover these claims. No desktop interaction, screenshot, other operating system or live provider progress is claimed.",
    "sources": {
      "scenario/blender/panels.py": "18b655d47e620589b822b643248d81135d7dd37aa1c23350ccfd020b797b2fdf",
      "scenario/blender/pump.py": "dca1e1db201d017f99ce2d006292b1a990a81b224639fefbc5964ce3cdff61f1",
      "scenario/blender/studio.py": "ccdc50f2047cbab1792b1dd2a52a2b9e0c36ba9a85c315a7794d344e06b3e544",
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "tests/blender/test_model_generation.py": "bdac7e6d4f3909bf1c03abe96b49753b77f2e655728b388bcf485bb55b9669c8",
      "scenario/blender/model_jobs.py": "2daeab1ce44043c115f8956bd70e08ad19a73d2e70140f72f4e8fbda7a3e524f",
      "scenario/core/jobs/records.py": "afe8476e1232d525de1039a43bc68e8c28c1680fee8fadcacde12285e4c67125"
    }
  }
}
---

# Jobs status words and progress bar

Evidence for [the canonical document](../../UI_STYLE.md).
