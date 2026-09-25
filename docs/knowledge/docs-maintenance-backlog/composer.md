---
{
  "type": "Evidence",
  "id": "docs-maintenance-backlog.composer",
  "title": "docs/maintenance/backlog.md: composer",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/maintenance/backlog.md",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-24",
    "limits": "Agent source inspection of the listed files; no live service calls, native runtime rerun or human verification in this review.",
    "sources": {
      "scenario/blender/composer/draw.py": "52a366ce04766edc3aef343c7b115d7e360e8c88a27688c4446be36ecc78c6e8",
      "scenario/blender/composer/modal.py": "5db6dcddc6b8ca2533fcf73f3d7782c0cd3bd47c99ca11eadf3a8c57d68ed632",
      "scenario/blender/model_picker.py": "d5e9a5ddd15899aac0d0e35b03754687430bc80e3e85a77ffb0cfbe2620a2fb0",
      "scenario/blender/params_ui.py": "12a913ecc68b92bce87f73fa158bfea03ee0dc684f20914a063826b230d6fb0c",
      "scenario/blender/prompt_tools.py": "c240d5e4d346fa69a46f33c7bc8d78755b0b00063f86f5eaf44aacf4d7bc0584",
      "scenario/core/api/model_filter.py": "ad728743dae392c8fb14cae621bd6642c9959409e56878336723c17e535e8fbb",
      "scenario/core/api/spark.py": "ec8f1c663a2052d56681a83eab9187101c825f9a370a993eb6e361de68980689"
    },
    "scope": "composer",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/maintenance/backlog.md: composer

Evidence for [the canonical document](../../maintenance/backlog.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
