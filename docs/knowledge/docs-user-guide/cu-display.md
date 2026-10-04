---
{
  "type": "Evidence",
  "id": "docs-user-guide.cu-display",
  "title": "Readable CU amounts with exact quote approval",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "cu-display",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-04",
    "base_revision": "93c0f72f5f1303662a338cfd9dbd1f6faf68c14b",
    "limits": "Reviewed CU display formatting for prompt approvals, generation controls and job/history prices against the web generation indicator: three fractional digits below 10000 and three significant compact digits above. Formatting is presentation only; native approval retains the original exact server decimal and rejects the rounded label as an approval value. Unit boundary cases and native quote/draw/approve/result regression pass. The exact packaged ZIP passed 566 native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. A Blender 5.1.2 isolated desktop fixture displayed 0.123 CU while retaining 0.1234567890123456789, recorded zero submissions before approval and one synthetic submission after it, and delivered the original field. No live pricing, paid service call, final render, cross-platform desktop or release acceptance is established.",
    "sources": {
      "scenario/core/ui/costs.py": "109a0094781678057033a16003803f2768e37bc7fe10066bf0f5422c8634af61",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/blender/panels.py": "dc4233043faf284ef8461a7d0cab9a07c75809bc5b148dd42b77494041a955cf",
      "scenario/blender/operators.py": "81d7e4feae3c5464d7f70f38aec449f459d2ba5181df3d006d415ab24c2f270c",
      "tests/unit/test_cu_display.py": "45e569a98b3d9973049b5d48088ecb209e342ee8aff61a5ee2ea13b7d0018333",
      "tests/blender/test_prompt_tools.py": "deecd1c9fc819c5657631e861434aed3123df9fbc598990d745c8ebdccf5c0b0"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
