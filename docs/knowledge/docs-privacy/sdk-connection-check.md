---
{
  "type": "Evidence",
  "id": "docs-privacy.sdk-connection-check",
  "title": "docs/PRIVACY.md: SDK connection check",
  "evidence": {
    "path": "docs/PRIVACY.md",
    "scope": "sdk-connection-check",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-26",
    "base_revision": "03c5128eb05fc4bbae14e49a1941b98c3b6bf2f2",
    "limits": "Reviewed Test connection worker ownership, background completion delivery, selected credentials, cache preservation, safe errors, stale-event rejection and status icons. Offline unit contracts and 351 tests against the same packaged ZIP pass on macOS arm64 with Blender 5.0.1, 5.1.2 and 5.2.1. An isolated Blender 5.0.1 desktop check confirmed the native button shows pending with an hourglass while cached models remain loaded; desktop error/success and focus acceptance were not completed. No live service, paid execution or account/project identity discovery is claimed. Other guide topics retain their independent evidence limits.",
    "sources": {
      "scenario/core/api/sdk_catalog.py": "73341abb8a32e91dd10c3fe272fb9f49922b648bfef7103b7938d3a69bbefc82",
      "scenario/core/api/sdk_adapter.py": "c6e89405e668a38a0d68237c9cab183cfcb8ef289fc8396595979dbf44c71b80",
      "scenario/core/jobs/manager.py": "617b457a53e818967c4a2066e293547f38c26e4570b3fbee2bdfca33805eae3d",
      "scenario/blender/runtime.py": "b009cd6e73abbf455969cb13e02ec4f0338097e1d499235146afe8233f9fbeb1",
      "scenario/blender/operators.py": "1df5bfafbe59f312b28749f61124968909518999e46fd309d4807c7e2eff2bc6",
      "scenario/blender/handlers.py": "cb3a06061f5a4f2f71a66d05e215602422037fa10f610b4384af26d6d64fe6a8",
      "tests/unit/test_sdk_connection.py": "0e0998d5dc3fd489b1f6de81605b8a0ce4efd0c06f47b913d0cb750fa0996f62",
      "tests/blender/test_sdk_connection.py": "e593a57c07871119573a547321b7017169979247bf4fdc52315a9f0fa3744b42",
      "tests/blender/run_all.py": "3473dde987385d7d6037877c334aa5ceac3956dd2b1185edec18d157715127da",
      "scenario/blender/panels.py": "0a0fb6c4aca46cbc9306b839c7f9b48f0f004389a366f0ff83f7ed483d0bb063"
    }
  }
}
---

Evidence for [the canonical document](../../PRIVACY.md).
