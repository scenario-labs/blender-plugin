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
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13: the README's verification instructions moved, unchanged in substance, into the paragraph for installing from a ZIP; the user guide's Verify your download section is unchanged. The published 0.10.0 ZIP and handbook passed shasum -a 256 -c SHA256SUMS and gh attestation verify, recorded in the release-acceptance Publication section. .github/workflows/release-please.yml was not re-reviewed. Earlier (2026-10-09): reviewed the README install-step verification pointer against the release workflow's ZIP and handbook build, SHA256SUMS contents, provenance attestation subjects and the user guide's Verify your download section.",
    "sources": {
      ".github/workflows/release-please.yml": "d729fcc5f0e069b8eddce853ba24751ab0055b4f40ef2285f80445147ca1ffa3",
      "docs/USER_GUIDE.md": "8b284a0978ab368af8a995024463c80c85212decd5f2e883b83c97cea013c5ed"
    }
  }
}
---

# README.md: download verification pointer

Evidence for [the canonical document](../../../README.md).
