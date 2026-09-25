---
{
  "type": "Evidence",
  "id": "docs-development-contributions.link-checks",
  "title": "docs/development/contributions.md: link checks",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/development/contributions.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-25",
    "limits": "Link-check policy inspected against the read-only PR scanner, separate scheduled reporter, explicit authentication exceptions, canonical Markdown inventory and offline regression tests. The exact release-owned root CHANGELOG.md is excluded after path validation, including its retained authored preamble and hand-written history; no automated coverage of links anywhere in that file is claimed. Nested authored changelogs and authored adapter targets remain scanned without following redirects. This generated-file exception does not verify release-note destinations or authorize rewriting release files. Offline tests do not establish live URL availability, hosted broken-link rejection or scheduled issue delivery; these remain separate acceptance.",
    "sources": {
      ".github/workflows/links-scheduled.yml": "e8a420c754bf829d64629d360de94f260fe20c0b1bdeb0a6f12fd4c2a7340081",
      ".github/workflows/links.yml": "2fc780cf855f68de99af2ff6bc8de0b67cee4aa72948613a34c4326caff99f31",
      ".lycheeignore": "900f73637c4b5985d01b57e32630d5dda63cd74c7a246c6486204ff1e7abf51c",
      "release-please-config.json": "f7192922c196556279e00e54b82a8ec82a5fe516481f35771e1ad73c0b00adc9",
      "tests/unit/test_links.py": "5e578228c610eaca547e22bb0d573f753bd4bbf14662d98c5d30c296d130b8a2",
      "tools/link_inventory.py": "4f3d16876967bb692f126bff33fc0e3ee25b5d5dde265b7bc68becca9a0db74c",
      "tools/report_link_failure.py": "8034aa3b95acafa2085a6c27cc72fe0f65f24ebdf46a2fd1afbf7075a2d18585"
    },
    "scope": "link-checks",
    "base_revision": "0e2debd9ab58977782fa1f673d7028b1da1ea69f"
  }
}
---

# Link-check evidence

Evidence for [the canonical link-check policy](../../development/contributions.md#link-check).

This topic covers authored Markdown inventory and link-check execution/reporting.
Release notes remain governed by the [release procedure](../../RELEASING.md).
