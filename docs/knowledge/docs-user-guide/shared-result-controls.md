---
{
  "type": "Evidence",
  "id": "docs-user-guide.shared-result-controls",
  "title": "Shared saved-job panel controls and composer collapse",
  "description": "Jobs/Generations controls shown for shared saved jobs, 3D result import formats and composer collapse behavior.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "shared-result-controls",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the Jobs and Generations panel descriptions, the 3D generation import paragraph, two troubleshooting entries and the floating composer's Settings and collapse wording against source. Shared job views receive files only after verified image import, so prototype 3D, video, audio, variant and progress-percentage controls are not reached; explicit recovery and application labels come from saved-job actions. Model import accepts one self-contained GLB and does not change viewport shading. An outside click commits and leaves the prompt without collapsing the card. Documentation-only review: no native, desktop, live provider or paid run. Output Folder and file-location claims, material Tiling and arrival wording, Film wording, screenshots and Edit 3D Generate readiness were not reviewed here.",
    "sources": {
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/blender/media_application.py": "5b803f80ce102b7a60dceb77a103394f67386593dd8a6d9a0d733e99effd8c83",
      "scenario/blender/model_application.py": "9fb7eda96afa0e79c26a547c2ddd15404a71c2344652a2bf31a4491442d96ca6",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/props.py": "f33955bbca26a36c8439ea3d57b2ef75110947ac8605cd21c2e903dac60d3bdb",
      "scenario/blender/composer/modal.py": "362aa797f4f52a8e8e320a024f64bd187eab39cdc32fbc8f26c03d4d168daebb",
      "scenario/blender/composer/state.py": "063ea956a996356b7dd1b28cc16b7dc4aaa1806a9336efe7d0d79052afbf5f79",
      "scenario/core/ui/composer_layout.py": "ec5a7e92e881a9c356f1a20619170b1cf4f2a930db15dbe057e5bead2d11453a",
      "scenario/core/jobs/records.py": "afe8476e1232d525de1039a43bc68e8c28c1680fee8fadcacde12285e4c67125",
      "scenario/core/api/jobs.py": "de996209f09e892a5b7f8279a2f0a2a69df944438f94bda73c869e0126e671ba",
      "scenario/core/history.py": "70f03b84bd4eaa98712332b97ee492180d91f1663825e8f967cfbb7a9cfce781"
    }
  }
}
---

# Shared saved-job panel controls and composer collapse

Evidence for [the canonical document](../../USER_GUIDE.md).
