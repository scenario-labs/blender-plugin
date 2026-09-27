---
{
  "type": "Evidence",
  "id": "docs-sdk-uploads.typed-reference-forms",
  "title": "Typed reference upload and attachment forms",
  "description": "Shared typed uploads with lane, input and destination guards in generation forms.",
  "evidence": {
    "path": "docs/SDK_UPLOADS.md",
    "scope": "typed-reference-forms",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-27",
    "base_revision": "4d03890a54e5bd93cf7ad9d1397f2ba367c10579",
    "limits": "Reviewed typed form admission, explicit lane and input-kind binding, read-only UI drawing, pending-upload generation guard, persisted kind/scope markers and saved-reference confirmation with a captured destination. Seven new native tests cover non-image lanes, mixed input kinds, tab switches, matching saved uploads, stale destinations/model/slot/type, no duplicate upload and draw-time immutability. The same ZIP passes 529 offline native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. An isolated Blender 5.0.1 desktop fixture verifies physical prompt entry, audio upload into Video, saved-reference confirmation without another transfer and viewport focus/navigation; before/after and confirmation screenshots were inspected and the normal profile was unchanged. Transports and credentials are synthetic; no live upload, paid generation, clip/mesh capture integration, non-image UI shared submission or complete release acceptance is claimed.",
    "sources": {
      "scenario/blender/reference_form.py": "07140573431116fed924c87362c6f39d64cf574a32e42fda49c32c4f067f3442",
      "scenario/blender/reference_uploads.py": "be3455c20dcff30e44dc6e984c66cd31f7664db1ee095ad3917956e3ce90bac4",
      "scenario/blender/generation.py": "add487ba125ff012dcd0f73acaa1640d91f1a8be4eda71008c7c9c36e3972832",
      "scenario/blender/panels.py": "79d459ff51a4dd91484b1bb2860ba8e6855dc95b6de65ceeb17567fb0744f609",
      "tests/blender/test_reference_form.py": "2792ddccb5da7fefd47902693b55e521c94128821a39f9c107002264b3aa91b8",
      "tests/blender/test_reference_uploads.py": "6ec7794b438bcf4a5ba2d38ea2aada7511fe18f20f6a91b0b32790e54dfb4983"
    }
  }
}
---

Source evidence for [the canonical guide](../../SDK_UPLOADS.md).
