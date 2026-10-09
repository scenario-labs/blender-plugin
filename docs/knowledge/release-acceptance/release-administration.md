---
{
  "type": "Evidence",
  "id": "release-acceptance.release-administration",
  "title": "Release administration gate verification",
  "evidence": {
    "path": "docs/maintenance/release-acceptance.md",
    "scope": "release-administration",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "88b6b3ec8ebd5707581f6d39f0fd158c784873a2",
    "limits": "Live API reads verify required ci-ok was added using its reported GitHub Actions integration identity, with all other integrity settings and the review ruleset preserved. The smoke environment has a required maintainer reviewer, allows self-review, and permits exactly main. Authorized private plan/test credentials and recovery passphrase are stored as environment secrets; values are not public. The repository scheduled allowance remains unset. Hosted zero-cap admission fails without entering the protected job, and the authorized dispatch pauses for reviewer approval. Live result completion, downloaded recovery decryption, negative PR-title proof and documentation merge are not claimed until separately recorded. This is dated remote configuration evidence; source fingerprints cannot certify continued settings or paid execution. No release publication or unrelated administrative changes.",
    "sources": {
      "docs/MAINTAINERS.md": "1769481dfe59f2b3215813b94470a0fcbd60c72c0457bf1435cfdba477210667",
      "docs/maintenance/release-acceptance.md": "f6def773623f625520086a12b2fd8e37cf1d3224da3b37ee70f24b57b2a70b93",
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

Evidence for [the administration record](../../maintenance/release-acceptance.md).
