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
    "limits": "2026-10-13: the README's verification instructions moved, unchanged in substance, into the paragraph for installing from a ZIP; the user guide's Verify your download section is unchanged. The published 0.10.0 ZIP and handbook passed shasum -a 256 -c SHA256SUMS and gh attestation verify, recorded in the release-acceptance Publication section. .github/workflows/release-please.yml was not re-reviewed. Earlier (2026-10-09): reviewed the README install-step verification pointer against the release workflow's ZIP and handbook build, SHA256SUMS contents, provenance attestation subjects and the user guide's Verify your download section. 2026-10-13 digest note: refreshed after the reference upload and required-argument fixes edited this document's upload and MCP text; this topic's claims were not re-reviewed. 2026-10-13 readability note: docs/USER_GUIDE.md was refreshed after an editorial rewrite reworded its Verify your download section; the files, commands and limits it states are unchanged. This topic's claims were not re-reviewed. 2026-10-13 review note: docs/USER_GUIDE.md was refreshed after the user-guide evidence review corrected wording elsewhere in the guide; its Verify your download section is unchanged, and this topic's claims were not re-reviewed. 2026-10-13 gallery note: refreshed after the guide gained an explorations gallery; the gallery doesn't touch the sections this topic covers, and its claims were not re-reviewed.",
    "sources": {
      ".github/workflows/release-please.yml": "d729fcc5f0e069b8eddce853ba24751ab0055b4f40ef2285f80445147ca1ffa3",
      "docs/USER_GUIDE.md": "a9e84d847e233ba08cacc75cc0fcbc8c0c7eae455e2862ff8584fe447d0bf90b"
    }
  }
}
---

# README.md: download verification pointer

Evidence for [the canonical document](../../../README.md).
