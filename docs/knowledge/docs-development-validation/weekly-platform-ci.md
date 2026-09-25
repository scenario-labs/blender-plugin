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
    "limits": "Canonical validation policy with inspected offline unit workflow, coverage reporting and connection-guard contracts; unit-process core/MCP coverage and matrix results do not establish subprocess coverage, native Blender compatibility or live service acceptance. Source-manifest preflight, supplied-ZIP bypass and failure/status preservation reviewed against build/runner code and offline regressions; native runtime and other claims retain prior limits. Reusable CI orchestration and fail-closed aggregate reviewed against all six caller workloads; this does not establish repository required-check settings or live service acceptance. Native update fixture reviewed against isolated profile guards, loopback-only repository configuration, server failure cleanup and exact synthetic installed-byte/enabled-state checks; local Blender 5.0.1 mechanism evidence does not establish production add-on upgrades, hosted publication, GUI controls or arbitrary subprocess socket enforcement. Unrelated evidence fingerprints retain prior review scope. Locator CLI, GUI make alias and existing offline capture artifact/profile behavior inspected; no new supported-platform GUI compatibility or live service acceptance is implied. Manifest-version CLI and documented environment boundaries inspected against discovery and offline tests; simulated platform locations do not establish native acceptance on those platforms. Inspected the actions-pinned house-rule implementation, CLI and failure tests; this scoped offline convention check does not establish general YAML validity, release tag provenance, other house rules, REUSE coverage or administrative settings. Optional uv-managed hooks and staged secret/path guard inspected with disposable Git regression coverage; full-tree prototype normalization, complete secret detection and repository protection remain separate. Generic offline command wrapper, owned profile lifetime, child status/cleanup and unmanaged native-suite exit contract inspected against source and focused process tests; Blender 5.0.1 exercised the wrapper and exact packaged baseline. This does not establish arbitrary-script sandboxing, live service acceptance or broader platform compatibility. Compatible fetch version/cache syntax, repository output directory, exact-manifest archive reuse and Make aliases inspected against command parsing and artifact-identity regression tests. Native Blender 5.0.1 exercised explicit repository output and no-build/fresh validation of an exact ZIP. Historical normal-profile, validation-bypass and shared-profile semantics remain unsupported; no broader platform or live-service acceptance is inferred. Workflow convention tests inspect explicit PR permissions, local reusable dependencies and declared contexts, and execute the actual ci-ok shell for each failure/missing-result case. They are a bounded block-style source check, not general YAML validation or proof of hosted token permissions, scheduling or administrative rules. Weekly macOS/Windows workflow and exact-title failure reporting inspected with offline pagination, failure and actual shell exit-status regressions; hosted dispatch, platform runtime and real issue deduplication remain separate acceptance evidence. Downstream current-run matrix reporting, bounded attempt identity, failed-only reruns and setup/timeout/artifact failure wording reviewed with offline regressions; intentional workflow cancellation remains excluded and hosted timeout reporting awaits execution. Knowledge CI now checks registry-base reachability against the full-history origin/main ref; workflow permissions and native behavior are unchanged. Independent OS issue-report failures reviewed with ambiguity and uncertain-write regressions; a partial report still fails the job and never retries an uncertain write. Restored the listed native-tool fingerprint after inspecting the source used by the weekly workflow; an earlier rebase had replaced its existing evidence with an older digest. Reconciled the scoped-label reporter from main with independent OS failure handling; offline OS and link-reporter regressions cover their combination. Real failure-issue delivery remains unverified.",
    "sources": {
      ".github/workflows/blender-os.yml": "2a4303266ca0aacb374d1ec40c6e0b21a80acd7dae18d7b3956a3c42619412b1",
      "tests/unit/test_ci_failure.py": "7457b7e5a04c9e37816226594d86a27049bf6c4dffc967206a9f6d476ee7b672",
      "tools/fetch_blender.py": "54779acbe1518c3b57b533311acdef0eac1e4efbb8ed462052192652106f8098",
      "tools/report_ci_failure.py": "2e0cc31745a8897e7ca72a622642dbd9f76bf5a902cf0a8e7bc87195da30568e"
    },
    "scope": "weekly-platform-ci",
    "base_revision": "0e2debd9ab58977782fa1f673d7028b1da1ea69f"
  }
}
---

# docs/development/validation.md: weekly platform ci

Evidence for [the canonical document](../../development/validation.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
