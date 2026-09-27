---
{
  "type": "Evidence",
  "id": "docs-sdk-adoption.reference-uploads",
  "title": "Active local MCP reference uploads",
  "description": "Shared upload admission, transfer policy, capture ownership and explicit recovery.",
  "evidence": {
    "path": "docs/SDK_ADOPTION.md",
    "scope": "reference-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "5233c691f89706cc0be1bfc27af55367bf2beda8",
    "limits": "Inspected shared session/worker orchestration, selected SDK 2.2.0 multipart methods, one-attempt mutation claims, upload-only S3 REST host policy, private source/capture lifetime, exact context/revision recovery and original-file preservation. Synthetic native tests cover initialization/completion uncertainty, changed origins, restart inspection and cleanup, and render-format restoration. Unit tests separately cover transfer destination rejection and transport behavior. No form attachment controls, real viewport/camera interaction, live API/S3 acceptance, paid generation or full issue #65/#37 acceptance is claimed. Parent Image integration evidence remains separate.",
    "sources": {
      "scenario/blender/reference_uploads.py": "770f56925a64df02001223582fd2305587db9623257cbb8c45532d80c0234979",
      "scenario/blender/runtime.py": "6c03af36760e5afe1be100e959b17e80dc624acc0bfac9679764ba0ef092695b",
      "scenario/blender/job_session.py": "fa6d4ce20ceff82ef4f0ab6ba73189cd7fd333650df38b8bc54bd1bc8d730cd5",
      "scenario/core/jobs/transfers.py": "4e8617fbbeb043415bc72b42a024515d0c59f7b08bbf4300777351b829179e57",
      "scenario/core/jobs/upload_transfers.py": "262f2e57734493cd9b21e9d582ec964cf7dbb4ce9688aa1f1a39b17945b3d7d5",
      "scenario/core/jobs/upload_sources.py": "2fc272529cc87abb0809e17b12792136d617632721b40df2e7b6d3b81fa7664b",
      "scenario/core/jobs/uploads.py": "fee6cebbb4cf6b8390b788a053fa9ba882f512182c40216f0656670c0319604d",
      "scenario/core/jobs/upload_store.py": "e53e44059fba806e5284f75327277fc7dcfceb7cd8a5f77e7a57696ce6372cf8",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "scenario/mcp/tools_scenario.py": "06d4e6b57d598c5b3130dc7f7028aeb90c6f308a3daaeb2b16ea560c6a810c98",
      "tests/blender/test_reference_uploads.py": "6d1f6aaf4c6f2e3b1e22af1d7455bbabe6c26c2566c81b30856ccd46fc568e1c",
      "tests/blender/test_session_uploads.py": "c51bc1488c072f02b6523f9ccc9f1efadfebca18c1ad94afae690dd4237f25f3",
      "tests/blender/run_all.py": "c76a1753ccc2c4bbed338403820e449e3e0d01aa61bc7e684dcbae1be98b50c4",
      "tests/unit/test_upload_sources.py": "6542f1ddde33fd51caf4d8e66b1acb9ee320ce898592983e87cb77536aff20f4",
      "tests/unit/test_upload_transfers.py": "2d5a988f164d4d531756e35d3ab8a543ca583b23d96953b9bfd64a32f55d18c4",
      "tests/unit/test_upload_commands.py": "821a4b7f718c4ea1d09b7f57e3ca0f31f502b4f02c2378e7e95640cf7b2774cf",
      "tests/unit/test_mcp_descriptions.py": "104a3278279beb2ee40e761da71d23410c721998f707e8c822572f9ee46001bf"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_ADOPTION.md).
