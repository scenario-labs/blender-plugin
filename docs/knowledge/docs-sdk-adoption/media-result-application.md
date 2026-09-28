---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.media-result-application",
  "title": "Explicit saved video and audio application",
  "description": "Receipt-bound media strip insertion through shared UI and MCP approval.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "media-result-application",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "474858e8e0df57f915385e82a7cfdf40f86c6fd9",
    "limits": "Inspected selected saved-media approval, exact scene/frame revalidation, existing worker verification, receipt-bound local snapshot, Blender strip insertion and rollback, durable claim and receipt-only recovery. Offline native tests decode MP4/WebM and MP3/WAV/OGG; isolated macOS arm64 Blender 5.1.2 desktop verifies WAV approval and one strip with unchanged mock submissions, keyboard/editor/viewport interaction and normal profile. Exact ZIP and desktop app-copy qualification are recorded in UI_STYLE.md. One selected asset consumes the job claim; local media files remain required and copying up to 512 MiB is synchronous. No paid calls, human listening, other OS desktop acceptance, mesh/material/World/Film completion, #263 resolution or release acceptance.",
    "sources": {
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83",
      "scenario/blender/job_session.py": "375dc1d2c18a3b165b190c000d06f6c60a2dbd5f27712f62efc742030a43e68d",
      "scenario/blender/model_jobs.py": "f69f19853cfdd99b44f527c092b7b935be480f61199b73e80e224c59c0103766",
      "scenario/blender/job_recovery.py": "6fe84f821ca9382e3a5a675d40517ba18189f370836bd94e7a432af48d6e7b5c",
      "scenario/blender/runtime.py": "28048b98830e93fd5d90d99d9b4966d11394d42b7f5bfdf3f82d37f21824d541",
      "scenario/mcp/tools_scenario.py": "0f6e376608017b8a63d8233c64a32ae39be0557ae3b3dd4048066fabd2281026",
      "tests/blender/test_media_application.py": "e9712551d2b95824d240030c74fb876963fe206d224991668de1c5f1f95f5723",
      "tests/blender/test_session_results.py": "abf066db37b5065da617ecfadb4c718dddba6aa4596382e764495f8185af68b6",
      "tests/blender/test_model_generation.py": "0d25ac664da022bd3504694ef53236a4b7c691ef3f0130a4cab24709fca77a82",
      "tests/fixtures/README.md": "8d09801414c1d61cbb621c499cf69be79457ac1b76d9403cc102a295817c3813",
      "tests/fixtures/synthetic/video-six-frames.mp4": "c2b435908a9adc6cd5903c0fda352cee6cd861a1eecfc7f31c0fa517460597e0",
      "tests/fixtures/synthetic/video-six-frames.webm": "ef20c4c9c90de8b84004a0ae876533fd90225a5391914449b1c9874fc0bc4c34",
      "tests/fixtures/synthetic/audio-silence.mp3": "bc8fd0776b541b2ca6fb7899318d4ea5ccac64ddf5fc1341423c285986832531",
      "tests/fixtures/synthetic/audio-silence.ogg": "d11b5d2e8bcba2c89ef1e745b69591124f1e63d7ba1f4afc974c08765ee79e69",
      "docs/images/saved-media-approval.png": "d12bb00750724ca2a7a2059092bc823cc2011e3f43cc2c5d2ad9e6387823cd3a",
      "docs/images/saved-media-result.png": "1629fc4e2fa73c99a9a3515c450af36a760d9fa8ccd9bc7b8631ef60155de442"
    }
  }
}
---

# Explicit saved video and audio application

Evidence for [the canonical document](../../SDK_ADOPTION.md).
