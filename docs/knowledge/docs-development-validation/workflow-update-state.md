---
{
  "type": "Evidence",
  "id": "docs-development-validation.workflow-update-state",
  "title": "Workflow reference state across native package updates",
  "evidence": {
    "path": "docs/development/validation.md",
    "scope": "workflow-update-state",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "d55f21eee597284d2482780c7c93f84115a119ff",
    "limits": "Reviewed optional workflow-form seeding, complete signature/normalized-value snapshots, selected-scope bindings and rejection under other credential/project stores. Real installed update/offline-restart checks pass on Blender 5.0.1/5.1.2/5.2.1 macOS arm64 against the exact candidate and synthetic predecessor recorded in release acceptance; all report workflow_references_preserved true with zero service requests and normal-profile preservation. A predecessor without workflow properties reports false on 5.1.2 while retaining existing state checks. No new state is invented for absent predecessor fields, and no published pair, live service, physical UI or release approval is claimed.",
    "sources": {
      "docs/development/validation.md": "80225688b7c146e5cfaba51cc9fbd6aae632765bf862773b30b0e1fdf4daa01f",
      "tools/test_repository_update.py": "a0eba939a15936c7452378a3cf6482c5b92fa169cc36b1b178f4b733a2a9e2ce",
      "tests/blender/package_update.py": "bfb7af35527d2a6dd765c3148e8e84ffb0619cb555d1e1d31152b6d37d7c3560",
      "tests/unit/test_repository_update_runner.py": "54091880dec3597c3400c7342ef53e7bf681935ce81e9e3f1f8b6c199412726e",
      "scenario/blender/workflow_controls.py": "fed4151d8476ead8c14de00ca3a30e7da3c814b55fd060b43b8f60c6db62ba78",
      "scenario/blender/workflow_references.py": "fdba9ab838d66a9ed6fcd1bc06f5486bc1c2ce1023d99a5c15ae8d01b431cc04"
    }
  }
}
---

Evidence for [the canonical guide](../../development/validation.md).
