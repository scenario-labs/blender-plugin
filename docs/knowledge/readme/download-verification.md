---
{
  "type": "Evidence",
  "id": "readme.download-verification",
  "title": "README.md: download verification pointer",
  "description": "Install-step checksum and attestation pointer for automated releases.",
  "evidence": {
    "path": "README.md",
    "scope": "download-verification",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-09",
    "base_revision": "b57c398f35fb2148c82fb8b26f6a40564d3f52ef",
    "limits": "Reviewed the README install-step verification pointer against the release workflow's ZIP and handbook build, SHA256SUMS contents, provenance attestation subjects and the user guide's Verify your download section. No release was built, published or downloaded; checksum and attestation verification of a published asset remains release acceptance.",
    "sources": {
      ".github/workflows/release-please.yml": "d729fcc5f0e069b8eddce853ba24751ab0055b4f40ef2285f80445147ca1ffa3",
      "docs/USER_GUIDE.md": "ab6f2bc57592631e9de286fb4bd3e77f7cc9ecd766beba271647b04910986a52"
    }
  }
}
---

# README.md: download verification pointer

Evidence for [the canonical document](../../../README.md).
