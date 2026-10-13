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
    "reviewed_at": "2026-10-12",
    "base_revision": "4ca693cb8f0e02a5c27c12d39bedbbc166b4e725",
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-12 the model_jobs.py fingerprint was refreshed after the saved model package import was rebuilt on this topic's sources. It adds import-unit projection, status fields, per-format import controls and package journeys beside the unchanged progress projection: view.meta import_units is set before _project_remote, and status adds import_units, import_findings and model_import beside lane and the remote fields. Readings and bindings still live only in memory; these claims were rechecked and the review date is unchanged. On 2026-10-12 the model_jobs.py fingerprint was refreshed again after saved splat import was stacked on the package import. It adds splat approval options, worker preparation and import notices to model_jobs.py, with view.meta import_notices set before _project_remote, splat options to the MCP tools, splat labels and notice rows to the descriptors and splat fixtures to the tests. The explicit splat preparation discards a pending automatic application like any explicit import, so the progress projection and delivery predicates are unchanged. These claims were rechecked and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged. A scoped re-inspection for the compact composer job strip found that model_jobs.py only gains the read-only busy and imports_automatically accessors that the composer's job strip reads; the projection, reading, binding and drawing claims are unchanged. The review date and earlier evidence are unchanged. Scoped 2026-10-12 check of the compact job strip rebased onto main, not a full re-review: panels.py only gives draw_result a keyword-only collapsible flag, true by default, that the composer's job card sets false; draw_shared_status, draw_active_job and the Jobs and Generations panels are unchanged. The claims above still hold; the review date and base revision are unchanged. In the paid desktop pass on main 2e89cae8, TripoSplat and Tencent UV Unwrapping reported several intermediate fractions, GPT Image 2 only 3%, and no job reported a queued state; the #424 recheck on dad196a8 at UI scale 1.0 measured the composer strip and pill filling to the reported 3% over a dim track. The composer bar at UI scale 2.0 and the Jobs rows' bars were not measured. Evidence added on 2026-10-13 from a private report, without spend amounts, account details, job identities, private paths or screenshots; the implementation sources were not re-reviewed and the review date is unchanged.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "2f1d9b1f4dfd70898c47590a8b55c76af8f60e2377692e36c85138a4a3187377",
      "scenario/blender/panels.py": "00796fe59694f3cafdc0c49f16539fbfc8921ae5110c18e65eca30abebab5e6e"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
