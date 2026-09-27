---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.reference-capture-preparation",
  "title": "Explicit mesh and clip reference snapshots",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "reference-capture-preparation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-28",
    "base_revision": "4699aec37a16833bfb30cda7159a824173f2390e",
    "limits": "Inspected explicit selected-mesh GLB and viewport/camera clip preparation through typed form/MCP uploads, private capture retention and original-destination guards. Five new native tests cover real GLB staging/selection restoration, preview-range clip planning and state restoration on success/failure using a synthetic render runner, precondition cleanup, original-form attachment and duplicate mesh upload rejection. Native tests use synthetic SDK transport and upload bytes; they do not establish live provider acceptance. The same exact ZIP passes 546 offline native tests on each of Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. Actual desktop capture encoding and keyboard/focus/viewport interaction remain unverified; desktop automation could not access the isolated window. Other OS/CPU and live provider acceptance remain separate. Render pinned capture/Spark preparation, non-image result application remain separate integration. No release approval is claimed.",
    "sources": {
      "scenario/blender/reference_uploads.py": "88fe120d2fa0eadbdce918387dc7c8293334d1829f323164f8afd0bc3c8ce74b",
      "scenario/blender/reference_form.py": "e896ebd0094c92a44448b73c9f9de789fd51cf90eb8b92694646157c31768e9e",
      "scenario/blender/panels.py": "2988683ae9b8e952baa357330f9217b49c2bcae8cbb37e8271fbcefd6e558db2",
      "scenario/blender/props.py": "22c3c7697da88980d60357f9783cd037ccef797acd1308d00a431de12a2a2585",
      "scenario/blender/capture.py": "b8c2caae26103f45ea2bd619578360db3b464faf9f21a2938f033d630975016e",
      "scenario/blender/mesh_export.py": "09361e88cf12290d4d8559355eab17cba196ceb2650ffc67739112c6448de509",
      "scenario/mcp/tools_scenario.py": "3a1823395a802e30994d6d6bbd53dde0edad6bb266cbf7f03f69a6c43cf2be63",
      "tests/blender/test_reference_uploads.py": "e8514012e3d0f0ae885327f6bbb103721d0ee8d1f61eaebf271bf40c0956ea73",
      "tests/blender/test_reference_form.py": "7f08de614aaa707d49d96be75b35bd016a4b517aad8619a5779943cb77010a3e",
      "tests/blender/test_3d_lane.py": "735b6bd9eaa93233b574434e8349b2c632ffb368a488315d4d7546669f684340",
      "scenario/blender/generation.py": "7eb9d9690d6d7e578ab37a7d3dce8464d481c7cd4e13fc069f23b2413fb1dfb1"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_UPLOADS.md).
