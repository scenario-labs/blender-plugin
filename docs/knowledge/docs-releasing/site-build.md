---
{
  "type": "Evidence",
  "id": "docs-releasing.site-build",
  "title": "docs/RELEASING.md: site build",
  "description": "Offline composition of the handbook and retained native extension repository.",
  "evidence": {
    "path": "docs/RELEASING.md",
    "scope": "site-build",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-09-25",
    "base_revision": "5d1f5a2062fed59b3a2fdefc621992467d34aea5",
    "limits": "Reviewed the site command, Make entry point, fresh-output staging, guide asset namespace, archive identity and exact retained inventory against offline composition and failure regressions. Existing renderer and release selector/generator contracts remain separate helpers. These checks do not verify release provenance, snapshot freshness or completeness, Pages deployment, release handbook attachment, production runtime or native updates. No publishing or paid service calls are part of this command. Blender 5.0.1 on macOS arm64 generated the real guide plus two synthetic compatibility ranges in isolated offline profiles; inventory replay produced identical bytes across all 22 output files and retained both exact input ZIPs. This native check covers generation, not installation or runtime acceptance on the supported matrix.",
    "sources": {
      "Makefile": "fd8c9225b7f43400aba76db9fa94c730c0b9a4ddba9a8ca74ab7897386fd33b0",
      "tools/build_site.py": "5a88b91baa5432ff0baad60cff8b933c705e4c3bc57f48c61c5a49a0a1ede64e",
      "tools/build_docs_html.py": "40e8c099acc77be8b3d57edd31f1e2a0ade323d9932e1c822aee98320c01f4a2",
      "tools/repository.py": "c41d4cd4964f78acb5fff9d0a20de976d0dcab94e7a14ca24d24e2073e6d191b",
      "tools/release_inventory.py": "44dfc7c3eec4320e0abb0c818ec021468576071183b2ca696e85da0110ac7d51",
      "tests/unit/test_site.py": "b1d97e957d6cb150fa1ecbdd71565e53049aa8ebec2a9530a87eb5e6162c9bfe",
      "tests/unit/test_docs_html.py": "4f13fa6738f636c0034a5eb07c773961efd4396dcf806862695612f20f5762da",
      "tests/unit/test_repository.py": "b6dee9da59ed8bfdec2c9a202f927c6fada49312f3ccb18cfff74f4c80fc9a7b",
      "tests/unit/test_release_inventory.py": "5a5bbffe19bbe34bc4eb1ad23faaa889888eb04b47a76f380e98f884f27b6ce5"
    }
  }
}
---

# docs/RELEASING.md: site build

Evidence for [the canonical document](../../RELEASING.md).
