---
{
  "type": "Evidence",
  "id": "docs-maintainers.handbook-website",
  "title": "Published handbook discovery",
  "description": "Manifest Website link and repository homepage after custom-domain handbook publication.",
  "evidence": {
    "path": "docs/MAINTAINERS.md",
    "scope": "handbook-website",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13, after 0.10.0 was published: the Pages API reports build type workflow, custom domain blender.scenario.com and enforced HTTPS; the handbook returns HTTP 200, HTTP redirects to HTTPS, the manifest's website is https://blender.scenario.com/ and the hosted index.json lists scenario 0.10.0. MAINTAINERS.md's Pages paragraph now says the repository has listed published releases since 0.10.0. docs/USER_GUIDE.md and tests/unit/test_manifest.py were not re-reviewed and keep their earlier fingerprints. Earlier (2026-09-26): inspected the custom-domain manifest contract and guide navigation; live read-back confirmed the repository homepage. Packaged manifest validation is distinct from publication or native update acceptance. No broader repository access, policy or release settings were changed.",
    "sources": {
      "scenario/blender_manifest.toml": "b77719e7bab76f1dcc159c7c281c404e70bf8d5ad9614beb757ebb34aff29110",
      "tests/unit/test_manifest.py": "36722722e3b8fe6c351acb1aad9b121d547f26ba07e50dd197af82600ac525dc",
      "docs/USER_GUIDE.md": "aefa70f872a7dfdab776726baf9243384d9afb513b2ae69a57a52e7acd2ec134",
      ".github/workflows/pages.yml": "b7e6c7c8f3b0b8cbe76595fbb9bb4a9a8ce0191dbb239872157f9c9e9fea8143"
    }
  }
}
---

# Published handbook discovery

Evidence for [the canonical document](../../MAINTAINERS.md).
