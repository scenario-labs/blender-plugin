---
{
  "type": "Evidence",
  "id": "docs-studio-adoption.studio-020-additions",
  "title": "Studio 0.2.0 capability reconciliation",
  "evidence": {
    "path": "docs/STUDIO_ADOPTION.md",
    "scope": "studio-020-additions",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "Source review on 2026-10-13 of Studio 0.2.0 at 204c847ad6f999e1050070a35e58af666b28ff9c against canonical main at the base revision, by reading code only. Checked in canonical source for the table's canonical claims: the local MCP server's Origin and token checks and the absence of a Host check and per-connection timeout; MCP generate accepting any approved cost equal to the fresh estimate, with no spending switch or cap; upload_reference accepting any readable path with an accepted extension; the generic refresh failure handler that pauses delivery and the client-wide max_retries=0; the stored but unused payload_sha256 and the warning-only uncertain state; estimates reading only creativeUnitsCost; one shared shot camera and marker collection per file; video and audio strips inserted into the working scene with no use_sequencer handling; texture-smoothness mapped to smoothness and inverted; the Film text em dash rewrite; and the focused composer prompt consuming unhandled keys. Upstream behavior is described from its source and documents only; upstream test counts, headless checks, GUI passes and paid runs were not reproduced. No Blender session, desktop interaction, live service call or paid operation was used. Owner issues #447 to #456 were opened from this review.",
    "sources": {
      "scenario/mcp/server.py": "2268544089dbab0e37a8ee64544942afb1b0970eab8f32201b13e7d9995e6db1",
      "scenario/mcp/tools_scenario.py": "112da784a70a39e76b052acc966f7378c924cb86ec3246a9fe0625685088d0f7",
      "scenario/blender/reference_uploads.py": "53f03716813f4a3480fa808a820f6269de566b5c1710448e2f56c3e12702fad3",
      "scenario/blender/model_jobs.py": "956e032cbe134fc57a3f0aa2e996a1f06388b80f8f0561b16bd703763995240e",
      "scenario/core/api/sdk_adapter.py": "0add4688710b00326fc31381d028e42cd9b5415f84bd168f45b5a8434a48aa19",
      "scenario/core/jobs/coordinator.py": "4f7172c38f6cab5b69131502b9c7d74fe8544d03b8371d752190fb6b25e312d5",
      "scenario/blender/shot_planner.py": "1a332a637731b63baeb9e46f9df62c316e441794ea82dd9ea6b6d2496a5018e0",
      "scenario/blender/apply_video.py": "48e4654a7601c2ec5d52302a0ba59968eded05e9dca838207402ca74c772ad61",
      "scenario/blender/apply_audio.py": "9cc2291528ad82aeffa2cc424a33846e52666e71d0b1cff43a8d8bf1abde8989",
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83",
      "scenario/core/jobs/result_metadata.py": "c16b9788e7836ea2ab77a8675506bea1409989da935de801f16c30ee626f5cb1",
      "scenario/core/scene/film_plan.py": "72f93ffa71878fe8136d24fb7b588f9268ca2da38ae34501832844a56992fc20",
      "scenario/blender/composer/modal.py": "45104e3c6c7081ef6b969551c2c04387524595f23ff8ce4bcbb70dea7e52957a",
      "scenario/core/jobs/transfers.py": "af6442afac9d146fab63563a04f62e97440b6eef9099b579a3f2dfe4fcae2e2c"
    }
  }
}
---

Source evidence for [the canonical guide](../../STUDIO_ADOPTION.md).
