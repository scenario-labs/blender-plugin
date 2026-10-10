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
    "limits": "Reviewed that readings and bindings live only in ModelJobs memory and view meta, that unknown and zero fractions draw no percentage, and that restarted views need an explicit refresh or resume before a reading exists. Which providers report intermediate fractions, desktop review and other platforms are not established. Scoped 2026-10-12 check of the Render Video first-frame handoff, not a full re-review: ModelJobs adds the use_first_frame action, its single-use approval, the verify_first_frame command and the session-local first_frame status field; polling, delivery predicates, progress projection, bindings and other actions are unchanged. The claims above still hold; the review date and base revision are unchanged. Scoped 2026-10-12 check of the native first-frame control, not a full re-review: ModelJobs.poll also writes first_frame_assets, the eligible still asset IDs, into each saved view's meta for the native descriptor; status words, progress, delivery, offline lines and redraws are unchanged. The claims above still hold; the review date and base revision are unchanged. On 2026-10-12 the model_jobs.py fingerprint was refreshed after the saved model package import was rebuilt on this topic's sources. It adds import-unit projection, status fields, per-format import controls and package journeys beside the unchanged progress projection: view.meta import_units is set before _project_remote, and status adds import_units, import_findings and model_import beside lane and the remote fields. Readings and bindings still live only in memory; these claims were rechecked and the review date is unchanged. On 2026-10-12 the model_jobs.py fingerprint was refreshed again after saved splat import was stacked on the package import. It adds splat approval options, worker preparation and import notices to model_jobs.py, with view.meta import_notices set before _project_remote, splat options to the MCP tools, splat labels and notice rows to the descriptors and splat fixtures to the tests. The explicit splat preparation discards a pending automatic application like any explicit import, so the progress projection and delivery predicates are unchanged. These claims were rechecked and the review date is unchanged. On 2026-10-12 review fixes made a PLY verify on the ordinary queue while the local-operation slot is busy, importing only as a mesh, and made the native model import dialog report a ScenarioError reason. This topic's statements were rechecked against that change and are unchanged; the changed fingerprints were refreshed and the review date is unchanged. A scoped re-inspection for the compact composer job strip found that model_jobs.py only gains the read-only busy and imports_automatically accessors that the composer's job strip reads; the projection, reading, binding and drawing claims are unchanged. The review date and earlier evidence are unchanged.",
    "sources": {
      "scenario/core/jobs/progress.py": "bf8bea9be0d1ba3c6ca7c2495fecf61eb67481ffb7499d1e30633cc154871af5",
      "scenario/blender/model_jobs.py": "cbc0f42f69be5533efb2c22c5582f3a90f6d87d1ed873aa86ee124bd3743410d",
      "scenario/blender/panels.py": "6865424bb96bd545a60a72ae5fad6531eccc97016fdd8eac21857d29eecf5415"
    }
  }
}
---

# Advisory, unpersisted remote progress

Evidence for [the canonical document](../../KNOWN_LIMITATIONS.md).
