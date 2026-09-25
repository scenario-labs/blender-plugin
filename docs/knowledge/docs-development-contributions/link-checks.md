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
    "limits": "Link-check policy inspected against the read-only PR scanner, separate scheduled reporter, explicit authentication exceptions, canonical Markdown inventory and offline regression tests. The exact release-owned root CHANGELOG.md is excluded after path validation, including its retained authored preamble and hand-written history; no automated coverage of links anywhere in that file is claimed. Nested authored changelogs and authored adapter targets remain scanned without following redirects. This generated-file exception does not verify release-note destinations or authorize rewriting release files. Offline tests do not establish live URL availability, hosted broken-link rejection or scheduled issue delivery; these remain separate acceptance. Retired prototype plans and their directory-wide exception are removed; proposed Markdown under any documentation directory is scanned, including a regression using the former directory name. No release publication or historical-link verification is inferred. Per-host concurrency, request spacing and retry wait inspected against pinned lychee 0.24.2 options after hosted GNU.org rate limiting; status acceptance and redirect rejection remain unchanged. The hosted negative PR and two manual failures both rejected the intentional 301/307 probes and reported to one tracking issue. After removing the probes, the paced branch dispatch completed with no errors and skipped the reporter. Final default-branch evidence must be recorded after merge; no permanent URL availability is implied. GNU.org-specific serialization and 10-second request spacing inspected against the pinned upstream configuration schema after the global defaults still yielded 429. The explicit shared configuration and PR path trigger cover local, PR and scheduled scans. Per-host statistics expose remaining throttling. Independent runners do not share a limiter; this configuration does not establish permanent availability or make 429 a successful response. A local full scan still rejected both GNU links with serialized 10-second spacing. Single-request curl probes to the same GPL FAQ returned 429 with lychee/0.24.2 and 200 with the explicit repository link-checker identity; the successful page contained the expected title and AllCompatibility fragment. GNU.org now receives that explicit per-host User-Agent rather than an impersonated browser identity. This is evidence of client-identity-sensitive responses, not proof of the server implementation or a guarantee for every runner. A focused Markdown scan with pinned Lychee 0.24.2 and the exact configuration passed both GNU links with two successful requests; a loopback header probe confirmed that the host override reaches the server.",
    "sources": {
      ".github/workflows/links-scheduled.yml": "e8a420c754bf829d64629d360de94f260fe20c0b1bdeb0a6f12fd4c2a7340081",
      ".github/workflows/links.yml": "0aa7b79270cacf205cb0b77527cf5e5b7604342faf775f8454a6438a51dfc6e6",
      ".lycheeignore": "900f73637c4b5985d01b57e32630d5dda63cd74c7a246c6486204ff1e7abf51c",
      "release-please-config.json": "f7192922c196556279e00e54b82a8ec82a5fe516481f35771e1ad73c0b00adc9",
      "tests/unit/test_links.py": "4139c23fb4152066cfdce135ed9521397c187d16f2b3193274ac594d6bab1515",
      "tools/link_inventory.py": "0ac73e81a96ddde2402ebd7d601192c6629de7663c3c1b165e785cd09de7398b",
      "tools/report_link_failure.py": "8034aa3b95acafa2085a6c27cc72fe0f65f24ebdf46a2fd1afbf7075a2d18585",
      "lychee.toml": "d94826ab35a6dd8d2aaf2523c312b847a080bee0d77841cb4d4244359fd91123"
    },
    "scope": "link-checks",
    "base_revision": "0a2cf9529c18a75a6d168c9708dec65d0c69b85c"
  }
}
---

# Link-check evidence

Evidence for [the canonical link-check policy](../../development/contributions.md#link-check).

This topic covers authored Markdown inventory and link-check execution/reporting.
Release notes remain governed by the [release procedure](../../RELEASING.md).
