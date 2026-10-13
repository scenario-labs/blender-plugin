---
{
  "type": "Evidence",
  "id": "docs-user-guide.cu-display",
  "title": "Readable CU amounts with exact quote approval",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "cu-display",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "3221af5a67583d5a992e9f25f9c41d00abed8924",
    "limits": "Reviewed CU display formatting for prompt approvals, generation controls and job/history prices against the web generation indicator: three fractional digits below 10000 and three significant compact digits above. Formatting is presentation only; native approval retains the original exact server decimal and rejects the rounded label as an approval value. Unit boundary cases and native quote/draw/approve/result regression pass. The exact packaged ZIP passed 566 native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. A Blender 5.1.2 isolated desktop fixture displayed 0.123 CU while retaining 0.1234567890123456789, recorded zero submissions before approval and one synthetic submission after it, and delivered the original field. No live pricing, paid service call, final render, cross-platform desktop or release acceptance is established. Costs bullet on a price check that starts a job re-reviewed on 2026-10-13 against the adapter refusal and the pump's session-wide stop of automatic prices.",
    "sources": {
      "scenario/core/ui/costs.py": "109a0094781678057033a16003803f2768e37bc7fe10066bf0f5422c8634af61",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/blender/panels.py": "dc4233043faf284ef8461a7d0cab9a07c75809bc5b148dd42b77494041a955cf",
      "scenario/blender/operators.py": "81d7e4feae3c5464d7f70f38aec449f459d2ba5181df3d006d415ab24c2f270c",
      "tests/unit/test_cu_display.py": "45e569a98b3d9973049b5d48088ecb209e342ee8aff61a5ee2ea13b7d0018333",
      "tests/blender/test_prompt_tools.py": "939e959296a1eecefb5a87d3aa7f1ea0d7187e77427700f49ecf3fd4f796099b",
      "scenario/blender/pump.py": "be8a40cc7c999a79e72dd62da20b9ceed3e32fde6436ec5b02f48f15b2d32201",
      "scenario/blender/model_jobs.py": "e8a81c2f386fc5edb944da8e13e02a5d9769450d16fe8e34c215380a2535bcfc",
      "scenario/core/api/sdk_adapter.py": "c08a94f319c08d8427a3a3f7aeceb690915d964a99cafbbc25d5f004c2781b93"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
