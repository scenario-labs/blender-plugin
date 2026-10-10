---
{
  "type": "Evidence",
  "id": "docs-known-limitations.film-case-study",
  "title": "Film case-study bundle limits",
  "evidence": {
    "path": "docs/KNOWN_LIMITATIONS.md",
    "scope": "film-case-study",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the stated refusals, shared thread and residual-byte limit. Inspected the portable Film case-study bundle adapted from Emmanuel de Maistre's Scenario Studio film_export.py at e2b0277064f0c502d46524fba1d006d0ac83f846: core/scene/film_case_study.py (approved-take selection over current master, audio, hero, shot and dialogue takes and their $task dependencies; a sanitizer that drops credential and identity keys, omits URLs, data URIs, known private identifiers and Scenario-shaped service identifiers in free text while keeping recipe identifiers; a sanitized recipe that keeps approved tasks, drops project_id and must validate again; a ledger with title, kind, recipe model, provenance, saved state, exact quoted cost and result media types plus the CU total, without request, job, asset, upload, project or team identifiers, URLs, paths or parameters; the manifest with format, generator, Studio attribution, scenes, approved tasks, continuity audit and opening steps; and the opening guide), core/jobs/local_case_study.py (bundle and neutral media names, specification bounds, stamped media copies with hashes, the bundle and verification children, report checks requiring only bundle-relative Media references, neutral packed names, no libraries or private properties, a chunk-overlapping scan of the uncompressed library and a marker check of every document, ZIP archiving with stored media and deflated documents under one top folder, a full member reread against SHA-256, cancellation, free-space preflight and path-free errors), the StagedFile/StagedBundle generalization of local_export.publish with the .zip destination suffix, coordinator export_case_study and suffix-aware publish_film_export, LocalExportWorker.export_case_study, JobSession.export_case_study and film_case_study, blender/film_case_study.py (inspection of review scenes and current director timelines with their shot origins, a user_map closure of the chosen scenes, refusals for linked or overridden data, movie clips, cache files, volumes, clip and mask strips, packed sound strip audio, sound strip modifiers or retiming, image sequences and multi-file packed images, the main-thread snapshot, ledger inputs from this scope's saved jobs and uploads, scan markers including extension storage and source media folders, and handles extending FilmExportCommands with timeline and shot invalidation), the standalone film_case_study_worker.py (filler-then-final path rewrites, sound strip rebuilds that keep timing, settings, properties, animation and drivers, image repacking, neutral packed names, //render/ output paths, removal of identifying Scenario properties and verification reports), the native Film > Case study panel and operators, the Studio Film Review page, the runtime poll, the shared export-thread check in FilmExportCommands and the MCP tools film_case_study_sources, prepare_film_case_study, export_film_case_study and film_case_study_review under the Output Folder agent policy. Unit tests cover the documents, sanitizer, recipe reload, ledger, specification bounds, media copies and stamps, child reports, private scans across chunks, archive rereads, cancellation, .zip destinations, bundle publish and the owned export thread. Installed synthetic tests build a real bundle from a review and a timeline with a textured, tagged shot, reopen the extracted archive in a fresh offline Blender that resolves every relative file, keeps the rebuilt sound strip's animation and renders a frame, and check that no archived byte holds a private identifier or the source, storage or output folders; they also cover inspection filters, destination refusals, exact and agent approvals, the native dialogs, progress, cancellation, a failed save with copy-only re-publish, timeline and shot invalidation, the shared export thread, read-only drawing, Edit Mode gating, shutdown cleanup and registration. The full installed suite ran on macOS arm64 Blender 5.1.2; the case-study module alone also ran on 5.0.1 and 5.2.1; the PR records the exact ZIP. The fixture used an offline SDK transport and mocked review ffprobe; no service call, upload, download or spend occurred. No physical desktop interaction, screenshot, Windows or Linux run, Windows path behavior, real provider media, human review of a bundle or release acceptance is established, and unused bytes Blender keeps in fields this export does not rewrite are not cleared. Only this case-study topic was reviewed.",
    "sources": {
      "scenario/core/scene/film_case_study.py": "b0f2faf94f63134194a8711bec1e76d9b8e92343728d9ac13c46537588455978",
      "scenario/core/jobs/local_case_study.py": "ce098adeed9136c06aabefe3aed32641f1bae6ce90d562bcdedaccec8a3bbf8d",
      "scenario/core/jobs/local_export.py": "dcda1746f5f904c3addda76d6b6241182e977eb2911db87f5e3c6071f03e12f5",
      "scenario/core/jobs/coordinator.py": "9308935363643d04dd01b57cf82b2ed35e2c8f42416f11d1df114ef31b586195",
      "scenario/core/jobs/workers.py": "90c3353adef7f1fec1db2faa749243feb62d87d5f5587b5a2b6771f1d1f05c56",
      "scenario/blender/film_case_study.py": "8f2e50b167848bc930b88cba0fefeeb73b5362490af903da1e1830329b3c0ae5",
      "scenario/blender/film_case_study_worker.py": "126e98214e2a38258bf90c49e1fde21bde25a81cff10735a6d74108452833163",
      "scenario/blender/film_case_study_controls.py": "4e4faaea143f1774c9962d0a9e68f1c7d3f450da05024fdcf7a2ab158cedf44b",
      "scenario/blender/film_export.py": "b39154618c30e7273ba59b059f5b1e1e3fb7e585a995b624d2fcda9f9dd02376",
      "scenario/blender/job_session.py": "ad9be0bcb9632b400d0019253d5e4b11fb7dbc29bc3e80cfc5521531727c0a6a",
      "scenario/blender/runtime.py": "adea7cdba77072ce43e5a25d720608170ce30977753e9aafb19ba7175b45cbdd",
      "scenario/blender/film.py": "f6f3b695ce4ebb3cb36fb82c40393b416b587578f2ec140f9319dd5b2009e398",
      "scenario/blender/studio.py": "234c69d7f358a70b3f44a5a2bb72d0bc2aad657ba8ba711500f28c74bb43b6ee",
      "scenario/mcp/tools_scenario.py": "6fc17cfde2565d33d92bf0a7aab6e8dd48e1e037cf559e32f2b5fa6484c1c720",
      "tests/unit/test_film_case_study.py": "f2d54057d099a20466963bba1a7c209ac303726a474a1bc9361f7a3978e0e124",
      "tests/unit/test_local_case_study.py": "f2e6e635dc281d7556cc0b1d82786540252cc326b4a2cdcdecd4dcc7a506aa30",
      "tests/unit/test_mcp_descriptions.py": "26114b20019fc5c036a72b6c79b2183ee623ba5d3712f4abeff88ca6003073c8",
      "tests/blender/test_film_case_study.py": "cfa5b0fb31796f16c76c8d287f5ef84fc808e45895f4c86715ba11e05e79f849",
      "tests/blender/test_studio_view.py": "bf5c0182730bf72ee3a38e3f97e48643d51b79fc7993e08fae69b9e5557cd909",
      "tests/blender/test_mcp_contracts.py": "47d48b4ac9f1737f7fb1c36330507833a4eb1eadf7325cad7cbc0bfe40ea2db0"
    }
  }
}
---

Source evidence for [the canonical guide](../../KNOWN_LIMITATIONS.md).
