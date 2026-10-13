---
{
  "type": "Evidence",
  "id": "docs-user-guide.workflow-library-references",
  "title": "Confirmed scoped Library references for workflow inputs",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "workflow-library-references",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "a0a0c9259535a483acff2f3d52a9e161449ececc",
    "limits": "Reviewed against the shortened guide's claims for this topic: file inputs accept a Library asset or an asset ID (step 3 of Run a workflow); Use as reference with Reference destination set to Workflow adds an asset to a workflow input after confirmation; existing references are kept, so one is removed first to replace it. Checked against library_view.py (the Workflow destination, a confirmation naming the asset, scene, workflow and input, attachment only through an issued approval after an origin check), workflow_references.py (only matching, unmarked inputs of the loaded workflow are offered; attachment rechecks the form signature, connection scope and value; Clear reference or Clear references empties and unticks the whole input after confirmation), core/schema/forms.py append_file_reference (a single input must be empty; arrays append without duplicates within their maximum and allowed values; minimums are left to pricing), workflow_controls.py (typed asset IDs, the Clear button, and pricing that refuses a Library-bound input whose value or connection changed) and registry.py. Correction proposed for the guide: a workflow input has no per-reference removal, so replacing one array entry means Clear references and new selections. The implementation still enforces the persisted connection binding, saved file-enum choices and removed-scene refusal that the guide no longer describes. Unit tests run: tests/unit/test_forms.py, 40 passed. Installed native tests in test_workflow_references.py were read, not run. The release acceptance guide's desktop check of the Library reference ran on pre-rebase heads, before these sources. Native desktop interaction (Library and Workflows pages, the confirmation dialog, focus, DPI, IME), other platforms and live acceptance remain under #66/#68. No live service calls or spending occurred, and this does not close issue or release scope. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "a9e84d847e233ba08cacc75cc0fcbc8c0c7eae455e2862ff8584fe447d0bf90b",
      "scenario/blender/workflow_references.py": "64eb574c5c8c377dcfbe91c91f0dab27ffcbb52445f68628c460aa0274ff5535",
      "scenario/blender/workflow_controls.py": "8b515b7c19fb0c6b4bc797a612a6158dac0bbecffb2a8254d259cb1a4ae956fd",
      "scenario/blender/library_view.py": "b6a0757506308b0a106a914389d6a25fad9533bc132018e5b904f183c4633737",
      "scenario/blender/registry.py": "c3a880832b4cf47ce530ecea582a5c73e53c8f346d5a6521b7c023bab31cd9e3",
      "scenario/core/schema/forms.py": "6c13428b31421d71aa28f2f8fd2c95c7594eaa31fcadd49fc92782c462e274f6",
      "tests/blender/test_workflow_references.py": "f882cfa2a0ba49f0ad354f0b9bab1f2a6ba6a5ee08dde71c0a6910ea88f1aba7",
      "tests/unit/test_forms.py": "dfd29abbabf2674e05d5dccb8e2d07c76f75f6215a684986cdab373369866e03",
      "tests/blender/run_all.py": "bcce33605252d54bbc0e78e45f0806809c9ec1b515b0c0fe0e97f0a4372b0944"
    }
  }
}
---

Evidence for [the canonical guide](../../USER_GUIDE.md).
