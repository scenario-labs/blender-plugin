---
{
  "type": "Evidence",
  "id": "docs-privacy.native-updates",
  "title": "Privacy: native update destinations",
  "description": "Native repository and browser-link disclosure.",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "native-updates",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "5e1541029ca27286d2b30861d5c0a239fe45736b",
    "limits": "Reviewed native update setup/check delegation, lack of Scenario credential forwarding, and explicit handbook/release browser links. Literal-host disclosure regression updated. Blender owns repository metadata and its network implementation; this review does not establish production HTTPS availability or perform an exhaustive network audit.",
    "sources": {
      "scenario/blender/updates.py": "7391e0fd941bc24d8ddecc168d03858fad186a3f834c927c4ba92e2dae586862",
      "scenario/prefs.py": "52b84d7c54f32fc6540687815439a615117bb17a535de62ee665f8b3d0e98038",
      "tests/unit/test_privacy_docs.py": "95ab3af9437096bcd34d0a4cdd0be4818d43d553355f6427c2ff22fc4271b821"
    }
  }
}
---

# Privacy: native update destinations

Evidence for [the canonical document](../../PRIVACY.md).
