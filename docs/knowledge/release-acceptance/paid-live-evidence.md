---
{
  "type": "Evidence",
  "id": "release-acceptance.paid-live-evidence",
  "title": "0.10.0 paid live acceptance and remaining checks",
  "description": "Paid live runs, observed service behavior and the pending 0.10.0 checks with owners and reasons.",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "paid-live-evidence",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-12",
    "base_revision": "ff8d29d879487719fde8fd9b4089438ae0ba2c78",
    "limits": "Records the maintainer-authorized paid runs of 2026-10-10 as reported privately: Render Image with GPT Image 2 (two jobs); Render Video with Seedance 2.0 Fast, whose first attempt with the frame sent as image beside reference videos failed on the service and was reimbursed, then succeeded with the frame as reference image 1; Flux 360, HDRi Skybox and a 2x skybox upscale whose download failed until #391 and then resumed without resubmission; four trained-model jobs on FLUX.1 Dev and FLUX.2 Dev; and private test workflows for approval, rejection and selection decisions, including the loop-selection overcharge that #395 and open #403 to #405 address. All ran from local MCP in background or script-driven Blender 5.1.2 on macOS arm64, on pre-merge builds, one key in its default scope; one submission per case and no output-quality review. The hosted five-lane smoke run of 2026-10-09 is referenced from the maintainer record, not re-reviewed. Quote values, costs, budgets, saved identities and private workflow definitions are deliberately omitted. Checked on main that first_frame_target routes an exclusive first frame to the first reference-image array, that the World format label for image/aces comes from the media type, that SDKAdapter.asset passes original_assets, that uploads take signed parts only from the create response, and that workflow quotes count loop steps. Seedance 2.0 Mini's first-frame exclusivity is recorded as a known service-side issue reported to the Scenario backend team, as stated by the maintainer. Pending owners and reasons come from the reports, pull request descriptions and the maintainer: the paid GUI checks (job card, workflow dialogs, first-frame quote, splat and FBX imports) were refused by agent permission rules, and IME after F2, listening and private trained models are human checks. Final candidate fields remain TODO placeholders; nothing here authorizes spending or publication.",
    "sources": {
      "docs/maintenance/release-acceptance.md": "7aed742285c254d80a8db19bca365fa17ce620cb7613d22fbed807fc6b851e3b",
      "docs/MAINTAINERS.md": "baf6be9a4e47a0be9890629e3257ecbf9da668d2d3602b47e0a5425e28da26f1",
      "scenario/blender/render_lanes.py": "059119b06a18bcd0083c93dd51f00f923140db33776a2ccb56366e0ad78669b7",
      "scenario/core/scene/panorama.py": "3680feac102599bf04bf5b0e6a7a63f0d292c9536f9833848ba5217c8619a890",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/core/jobs/uploads.py": "df83f0035ccffd13578d9fc0fffb28dfc43bf503a54b4971186230dc2b5a9f4f",
      "scenario/mcp/tools_scenario.py": "0395590f270b006523b1505379e0d7925eca8dc6b0f527d5a5ff2137ecf0f56c",
      "scenario/core/ui/costs.py": "07f305f86ad6d9acdb0667fcdb2625ca9e9d803bcbb0b7cf7c33b60cca609539"
    }
  }
}
---

# 0.10.0 paid live acceptance and remaining checks

Evidence for [the paid live runs and pending checks](../../maintenance/release-acceptance.md#pending-checks).
