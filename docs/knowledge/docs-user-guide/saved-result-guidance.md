---
{
  "type": "Evidence",
  "id": "docs-user-guide.saved-result-guidance",
  "title": "Saved-result limitation pointer, Generations screenshot text and missing-result troubleshooting",
  "description": "Corrections that remove nonexistent result controls and the internal release-blocker sentence.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "saved-result-guidance",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed three statements against source: the saved-jobs paragraph now ends with a pointer to the known limitations instead of an internal release-blocker sentence; the Generations screenshot alternative text no longer names an Import into scene button, which no current control provides, and identifies the image as an earlier layout; the missing-result troubleshooting entry sends recovery to Inspect saved jobs, which the Jobs panel draws at its top, and to Resume download or Check interrupted download. Shared jobs whose download failed or was interrupted keep a nonterminal view status, so the Jobs panel lists them with those controls; Generations draws only terminal views. The entry's opening Generations sentence is retained text and was not re-reviewed. The rest of that paragraph, the Jobs and Generations panel descriptions, lane result descriptions and other troubleshooting entries were not reviewed here and keep their existing limits. Documentation-only review: no native, desktop, live provider or paid run, and the screenshot itself was not recaptured.",
    "sources": {
      "docs/images/panel-generations.png": "1855d84e54682a0fad54de6001bf2cc8c35b7b35e1fecfe5848893348eb2fa1b",
      "scenario/blender/panels.py": "0ea312ede072b4e25c8177120214d404b449ea60db10c02edd12ad5eb985d989",
      "scenario/blender/job_recovery.py": "e39883dfa3dd4604d7b045e109ac6037fa822ef325b25fbb3ae98c86459009eb",
      "scenario/blender/operators.py": "8fb3a35beb010e81f4d4eaecf22688d8baf051ad88cdf2def50664e0da01a103",
      "scenario/blender/model_jobs.py": "bffb88d51557165fbdd5c22c89087c7a690ad15c17607a543b4a2cbc905ea00c",
      "scenario/core/api/jobs.py": "de996209f09e892a5b7f8279a2f0a2a69df944438f94bda73c869e0126e671ba",
      "scenario/core/jobs/records.py": "afe8476e1232d525de1039a43bc68e8c28c1680fee8fadcacde12285e4c67125"
    }
  }
}
---

# Saved-result limitation pointer, Generations screenshot text and missing-result troubleshooting

Evidence for [the canonical document](../../USER_GUIDE.md).
