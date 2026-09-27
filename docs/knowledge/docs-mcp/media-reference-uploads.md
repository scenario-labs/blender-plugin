---
{
  "type": "Evidence",
  "id": "docs-mcp.media-reference-uploads",
  "title": "Typed local media reference uploads",
  "description": "Explicit upload kinds and persisted metadata through the shared session and local MCP.",
  "evidence": {
    "path": "docs/MCP.md",
    "scope": "media-reference-uploads",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "29abc71f35c858af941328e02282aaaa865e595a",
    "limits": "Reviewed explicit image/audio/video/3d filename and MIME admission, default-image compatibility, persisted metadata returned by MCP status/recovery, and reuse of SDK 2.2.0 upload methods without an adapter or dependency change. Native tests use synthetic bytes and mocked transport to cover exact SDK metadata, immutable staging, rejected kinds/extensions, remote metadata mismatch, uncertain initialization without replay, restart and cleanup. This establishes transport and lifecycle behavior, not media decoding, live API/provider format acceptance, non-image UI preparation, sidecar discovery, paid generation or complete issue acceptance. Multipart response fixtures distinguish the storage fileName from originalFileName; the pre-PUT guard validates the latter and rejects changed or absent original names. Public upload MIME declarations remain distinct from generated asset aliases; strict declared MIME matching is retained.",
    "sources": {
      "scenario/blender/reference_uploads.py": "be3455c20dcff30e44dc6e984c66cd31f7664db1ee095ad3917956e3ce90bac4",
      "scenario/blender/job_session.py": "6df07b116f3eea2efb46a6cfe2f60025ec3a0ba821119c181378f14e26dd7ab8",
      "scenario/core/api/sdk_adapter.py": "c7cb9b64ab84f51977c98961698b953756842a7c8baeec2a583a1c78a903d0bb",
      "scenario/core/jobs/uploads.py": "9cf44ecdce8f1d7cd2595f403a70027dcf5e3c6617ec93800b5d5b88886048d1",
      "scenario/core/jobs/upload_sources.py": "2fc272529cc87abb0809e17b12792136d617632721b40df2e7b6d3b81fa7664b",
      "scenario/mcp/tools_scenario.py": "dab58d2abd0b1753eca90789badb00fdb0287fd97e380c4945a39a0998b83bb0",
      "tests/blender/test_reference_uploads.py": "6ec7794b438bcf4a5ba2d38ea2aada7511fe18f20f6a91b0b32790e54dfb4983",
      "tests/blender/test_session_uploads.py": "3e6a245be0dd98773757e9832f2f09d5ab2eb73ec1f5c9a22c230cb141df7dab",
      "tests/unit/test_mcp_descriptions.py": "104a3278279beb2ee40e761da71d23410c721998f707e8c822572f9ee46001bf",
      "tests/unit/test_upload_commands.py": "aea26b23c25be14ae2cf1eef2d8d01de42424f6b216ff40a1c4663b74143049b",
      "tests/blender/test_upload_commands.py": "3a8ca543fc4f5d1df7429d9735c647576902e22ebbe5a0ef3d4685e6f4301ba4"
    }
  }
}
---

Source evidence for [the canonical guide](../../MCP.md).
