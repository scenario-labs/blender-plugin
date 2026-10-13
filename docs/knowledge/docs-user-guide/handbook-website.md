---
{
  "type": "Evidence",
  "id": "docs-user-guide.handbook-website",
  "title": "Published handbook discovery",
  "description": "Manifest Website link and repository homepage after custom-domain handbook publication.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "handbook-website",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13, after 0.10.0 was published: the manifest's website is https://blender.scenario.com/, the handbook returns HTTP 200 and HTTP redirects to HTTPS, and the hosted index.json lists scenario 0.10.0 with that website. The guide's Website-link paragraph is unchanged. Earlier (2026-09-26): inspected the custom-domain manifest contract and guide navigation; live read-back confirmed handbook HTTP 200, custom domain and enforced HTTPS, and the repository homepage. Packaged manifest validation is distinct from publication or native update acceptance. No broader repository access, policy or release settings were changed. 2026-10-13 digest note: refreshed after the reference upload and required-argument fixes edited this document's upload and MCP text; this topic's claims were not re-reviewed. 2026-10-13 readability note: refreshed after an editorial rewrite moved the Website-link sentence into Updates; it still says the Get Extensions Website link opens this handbook at blender.scenario.com. This topic's claims were not re-reviewed. 2026-10-13 review note: refreshed after the user-guide evidence review corrected wording elsewhere in the guide; the Website-link sentence in Updates is unchanged, and this topic's claims were not re-reviewed.",
    "sources": {
      "scenario/blender_manifest.toml": "b77719e7bab76f1dcc159c7c281c404e70bf8d5ad9614beb757ebb34aff29110",
      "tests/unit/test_manifest.py": "36722722e3b8fe6c351acb1aad9b121d547f26ba07e50dd197af82600ac525dc",
      "docs/USER_GUIDE.md": "d81c4fbc7ccd6fd05b987dfc9a77f191ad567cc0486b2f9983b755402bad526b",
      ".github/workflows/pages.yml": "b7e6c7c8f3b0b8cbe76595fbb9bb4a9a8ce0191dbb239872157f9c9e9fea8143"
    }
  }
}
---

# Published handbook discovery

Evidence for [the canonical document](../../USER_GUIDE.md).
