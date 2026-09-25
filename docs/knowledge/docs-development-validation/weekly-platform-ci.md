---
{
  "type": "Evidence",
  "id": "docs-development-validation.weekly-platform-ci",
  "title": "docs/development/validation.md: weekly platform ci",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/validation.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-25",
    "limits": "Weekly workflow, canonical fetch/test commands and reporting boundaries inspected. Default-branch run 36137526586 on the recorded revision passed the full 341-test suite separately on macOS arm64 and Windows x64, with Blender 5.1.2 / Python 3.13, zero failures/errors/network violations and unchanged normal profiles. Windows skipped POSIX signal shutdown and FIFO tests. Downloaded artifacts were inspected for candidate ZIP, installed dependency identity and reports. These are separate exact ZIPs of one source, not a common release candidate or desktop/GPU/audio/provider acceptance. Branch-only deliberate failures exercise hosted issue reporting separately; temporary probes are removed from the final diff. Offline reporter/workflow contracts remain passing; no new workflow behavior, permissions or runtime implementation is introduced. Runs 36139299591 and 36139443654 deliberately failed both OS jobs and successfully reported to the same per-OS issues 224 and 225; the repeated dispatch commented without creating duplicates. These probes verify reporting and preserve failing job conclusions, not native failure recovery or timeout acceptance.",
    "sources": {
      ".github/workflows/blender-os.yml": "2a4303266ca0aacb374d1ec40c6e0b21a80acd7dae18d7b3956a3c42619412b1",
      "tests/unit/test_ci_failure.py": "7457b7e5a04c9e37816226594d86a27049bf6c4dffc967206a9f6d476ee7b672",
      "tools/fetch_blender.py": "54779acbe1518c3b57b533311acdef0eac1e4efbb8ed462052192652106f8098",
      "tools/report_ci_failure.py": "2e0cc31745a8897e7ca72a622642dbd9f76bf5a902cf0a8e7bc87195da30568e"
    },
    "scope": "weekly-platform-ci",
    "base_revision": "5d1f5a2062fed59b3a2fdefc621992467d34aea5"
  }
}
---

# docs/development/validation.md: weekly platform ci

Evidence for [the canonical document](../../development/validation.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
