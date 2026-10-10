---
{
  "type": "Evidence",
  "id": "docs-result-previews.workflow-review-previews",
  "title": "Previews of workflow review assets",
  "description": "Stills of the assets a waiting workflow step lists for review, fetched on the shared preview lane and cache and decoded into icons by the GUI pump.",
  "evidence": {
    "path": "docs/RESULT_PREVIEWS.md",
    "scope": "workflow-review-previews",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-10",
    "base_revision": "33d00b0554151c4de04731fd1a5e5c64ed50855b",
    "limits": "Reviewed the Workflow review assets section, the scheduler interface sentence and the boundaries against ModelJobs.review_assets and workflow_nodes.preview_assets (an approval's result assets or an asset selection's candidates, bound to the saved revision and review_id without refusing a command in flight), runtime.load_review_previews, ResultPreviewScheduler.request_review with entry keys that separate review assets from saved results and the review flag of retry and status, JobCoordinator.review_preview_targets and ResultCommands.review_targets (1 to 50 distinct IDs of a remote workflow job with a remote ID; a ReviewKey binding scope, request, remote job and asset), the lane's review branch of _preview_record and _preview_remote, review_sources (the image's own url within 8 MiB and 4096 pixels as declared, else its thumbnail, else an immediate failure for a larger image or polling for other kinds), fetch's content and dimension checks, check_still, and the Blender owner review_previews.py (status copies in the GUI pump, at most two decodes per tick and none while a render job runs, through a temporary Non-Color image datablock that is removed, icons of at most 256 pixels per side filled from pixels in a private preview collection, at most 128 tracked assets, released when a step stops waiting or jobs retire). Unit tests use the real SDK with MockTransport and an offline downloader that enforces the host policy; installed tests on the packaged ZIP (macOS arm64 Blender 5.1.2) use synthetic SDK responses and an offline downloader with the runtime's storage policy, and check the decoded icon's size and pixel values directly. Background Blender assigns no icon IDs, so drawn icons were checked with a stand-in ID. No live workflow flow, review asset metadata, url or thumbnail coverage, CDN transfer, timing or size evidence; no desktop interaction, screenshot, DPI or GPU icon display; no MCP preview. No store schema change.",
    "sources": {
      "scenario/core/jobs/result_previews.py": "b17c9f0ebd80e222090c0ad83339b27d7f261a7e1cb5a7bf02d2ca261d9ceb09",
      "scenario/core/jobs/preview_scheduler.py": "aedd1fa55614dd342688a15bba9639fb31f10590d2bbd7dfd4be2344912641d2",
      "scenario/core/jobs/results.py": "a1c52d70390adcc49900e5ef457e0c0c864e0ecb5cd313ecbc268a43994bbc95",
      "scenario/core/jobs/coordinator.py": "c981f84b6000735ebe58ef6a9969efef6e6dc95c4d8f1752affb500550ef437c",
      "scenario/core/jobs/workflow_nodes.py": "8f073ded509b0eb9bc9f7e2eeb5f61fe08eb1b43f4c4d7d80c7227d00501add4",
      "scenario/core/jobs/transfers.py": "809323c378949b690e0cc7b1572a8e621819349e72c622f6b59f287c2bb05024",
      "scenario/blender/review_previews.py": "508f3a424412cc7b95a9d78870b9c765d3b8c3ee2eeb44ddc010cd193d451bba",
      "scenario/blender/runtime.py": "cf15f250833f0e8afd880ce59c902e5a0924fe38ba1ae527d10f2d5a9417565b",
      "scenario/blender/model_jobs.py": "646ef59978fa1ca97709c36e9884506dd58d45cc2a03cc772d6446aaf146986d",
      "scenario/blender/pump.py": "80e487b5d4aa0b872a741d62793fd5ed78eb281516063aba2ba470803e909f74",
      "scenario/blender/job_session.py": "0168da12a1e1937302569984be0eff2cd8b4439ef11dd88a0b5ade163ad23a32",
      "tests/unit/test_workflow_review_previews.py": "12fb0b5f4f8cd6f15c5868996ef108f01192fadf4e9f70f1b62f1b0c6a38a83e",
      "tests/blender/test_workflow_review_previews.py": "4f8100b75a020836378862af5375d04f86b21cf37ba2220553c3525767157452",
      "tests/blender/test_workflow_commands.py": "1c24de554b5e34efdb2ff060f1091c5a77776d8b5eee3856e86f2dc30632a086"
    }
  }
}
---

# Previews of workflow review assets

Evidence for [the canonical document](../../RESULT_PREVIEWS.md).
