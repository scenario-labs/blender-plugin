---
{
  "type": "Evidence",
  "id": "docs-maintainers.release-administration",
  "title": "Release administration gate verification",
  "evidence": {
    "path": "docs/MAINTAINERS.md",
    "scope": "release-administration",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Live API readback verifies required ci-ok using its reported GitHub Actions identity; all other integrity settings and the review ruleset remain unchanged. The invalid-title hosted check failed with the PR blocked, then the restored title passed alongside commits and ci-ok. The smoke environment requires a maintainer reviewer, allows self-review, and permits exactly main; configured secret values stay private. A zero-cap hosted run failed before the protected job; a non-main dispatch skipped both jobs without running steps. The approved main run paused for review, then completed five READY jobs and 16 receipt-verified files. Downloaded recovery decryption, quote bindings and offline completed-result resume passed with sockets blocked, zero network calls and unchanged saved jobs. The version-1 plan does not cover reference uploads, uncertain-job recovery, Blender application or media quality. No provider monthly budget or recurring allowance is configured; scheduled allowance stays unset. The prior fix and acceptance documentation are merged; their tested archive identity remains unchanged. Documentation review/merge and remaining release acceptance are not claimed. Dated remote evidence and source fingerprints cannot certify future settings. No publication or unrelated administrative changes. 2026-10-13 note: after 0.10.0 was published, the tag ruleset and immutable releases setting were read back through the GitHub API: the versioning ruleset is active on refs/tags/v* and refs/tags/blender-plugin-v* with creation, update, deletion and non-fast-forward rules and the release App integration as its only bypass actor; immutable releases are enabled and not enforced by the owner. MAINTAINERS.md's ruleset row, its bypass sentence, the security settings row, the Pages paragraph and the admin checklist now say so. The ci-ok, title and smoke environment claims above were not re-read, and the review date is unchanged. 2026-10-13 digest note: refreshed after MAINTAINERS.md's Actions row, Dependabot paragraph and #39 admin item recorded the required full-SHA pinning and the seven-day Dependabot cooldown; this topic's claims were not re-reviewed.",
    "sources": {
      "docs/MAINTAINERS.md": "00f982ba6e0272dead623cb130e1b20d8ade1a00e36b7abe165240ef6ddccab4",
      "docs/maintenance/release-acceptance.md": "975ef61a24ddc8a4ac5c12a55736d5fdf4095e4da810906cce71f89f3317edbb",
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/pr-name.yml": "0e315b620212b21f3058eae7d173813190ab81fd929b5d1178772c2fdbbc79d6",
      ".github/workflows/smoke.yml": "71ea95047895ceefb2ac8220663b2f6ee5a4b2dcf56dd4a8b5c8f3cee9a7b9bb",
      "tools/smoke_ci.py": "89a207725badb7c6d6dff3df54fd2a127b40c457b3954f429d451ea7cf88690a",
      "tools/smoke_suite.py": "7595c08b8c5bae299908f12c9124ab3f2376da0237203f0ecc937aaaf3c38a36",
      "tests/unit/test_smoke_ci.py": "62fbc7789fa7f52a9fe8c3ae912af364bf0a50c939fbfa04cab4171020ece76d"
    }
  }
}
---

Evidence for [the administration record](../../MAINTAINERS.md).
