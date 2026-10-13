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
    "base_revision": "d3e6589fa7df0e49de39696c2fbaae591daa0c22",
    "limits": "Reviewed CU display formatting for prompt approvals, generation controls and job/history prices against the web generation indicator: three fractional digits below 10000 and three significant compact digits above. Formatting is presentation only; native approval retains the original exact server decimal and rejects the rounded label as an approval value. Unit boundary cases and native quote/draw/approve/result regression pass. The exact packaged ZIP passed 566 native tests on Blender 5.0.1, 5.1.2 and 5.2.1 on macOS arm64. A Blender 5.1.2 isolated desktop fixture displayed 0.123 CU while retaining 0.1234567890123456789, recorded zero submissions before approval and one synthetic submission after it, and delivered the original field. No live pricing, paid service call, final render, cross-platform desktop or release acceptance is established. Costs bullet on a price check that starts a job re-reviewed on 2026-10-13 against the adapter refusal and the pump's session-wide stop of automatic prices. Costs bullet on generating again re-reviewed on 2026-10-13: the button keeps its price and re-enables once Scenario confirmed the job and the short delay passed; an edit prices the form again.",
    "sources": {
      "scenario/core/ui/costs.py": "109a0094781678057033a16003803f2768e37bc7fe10066bf0f5422c8634af61",
      "scenario/blender/prompt_tools.py": "1f465204554e10fae9f0903c84f8f834ba8a492451f1c855bde083cca36527e4",
      "scenario/blender/panels.py": "dae2c8208afb394dc1c4673facbc5de653972ef7fe0f5b3a5c4848c2c1092f15",
      "scenario/blender/operators.py": "81d7e4feae3c5464d7f70f38aec449f459d2ba5181df3d006d415ab24c2f270c",
      "tests/unit/test_cu_display.py": "45e569a98b3d9973049b5d48088ecb209e342ee8aff61a5ee2ea13b7d0018333",
      "tests/blender/test_prompt_tools.py": "939e959296a1eecefb5a87d3aa7f1ea0d7187e77427700f49ecf3fd4f796099b",
      "scenario/blender/pump.py": "2e46694014cea3312b45c13473297b9bbddaea7f722a23cf13f169589e0709fd",
      "scenario/blender/model_jobs.py": "320357d976cbc763c3ca2594af722e9351b50f8c9da9654dcb8f79c8a397cc99",
      "scenario/core/api/sdk_adapter.py": "1acf3827b2fb56a6583fdbbf75b3d5f7c160763f006ff1e639a9d77c59393c26",
      "scenario/blender/generation.py": "033b2d4f091f23355d105c5e214806a274a6a27a8f8f5c12a1fd9dd8973daa59"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
