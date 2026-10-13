---
{
  "type": "Evidence",
  "id": "docs-user-guide.handbook-installation",
  "title": "Handbook navigation and release availability",
  "description": "Published handbook navigation and installation availability.",
  "evidence": {
    "path": "docs/USER_GUIDE.md",
    "scope": "handbook-installation",
    "coverage": "source-reviewed",
    "reviewed_at": "2026-10-13",
    "base_revision": "34ce22e8a4b037312334d98fbec6641da45a9a45",
    "limits": "2026-10-13, after 0.10.0 was published: Install now leads with the official repository (Add Remote Repository with the hosted index), keeps the release ZIP as an alternative that does not update itself, and says the handbook is built from current development and that each automated release attaches its own handbook. Read back the same day: the hosted repo/index.json lists scenario 0.10.0, the handbook returns HTTP 200 and HTTP redirects to HTTPS; the repository install itself is recorded in the release-acceptance Publication section. The deployed handbook shows this text only after this change merges and Pages redeploys. Only docs/USER_GUIDE.md was re-fingerprinted; the other sources are unchanged since 2026-09-26. Earlier (2026-09-26): live handbook inspected at desktop and mobile widths: all 15 images load, all 15 external links resolve, section anchors exist and no horizontal overflow or script exceptions were observed; mobile contents are collapsed initially, with native disclosure and a no-script expanded fallback. This is website and install-documentation acceptance only, not live generation, Blender update-control acceptance, an update between published releases or validation of every illustrated model workflow. Native failure recovery has separate scoped evidence. 2026-10-13 digest note: refreshed after the reference upload and required-argument fixes edited this document's upload and MCP text; this topic's claims were not re-reviewed. 2026-10-13 readability note: refreshed after an editorial rewrite shortened and reorganized the guide, moving verification detail to linked references. The install steps, repository URL, ZIP path and credential setup keep their meaning; the rendered-site checks above describe the earlier text and were not repeated; this topic's claims were not re-reviewed. 2026-10-13 review note: refreshed after the user-guide evidence review corrected wording in Updates, Studio, Run a workflow, Library, Environment and Costs; the install steps, repository URL, ZIP path and credential setup are unchanged, and this topic's claims were not re-reviewed.",
    "sources": {
      "docs/USER_GUIDE.md": "d81c4fbc7ccd6fd05b987dfc9a77f191ad567cc0486b2f9983b755402bad526b",
      "docs/handbook-template.html": "e81175c9a59174cbcec9ecfcf204b1e5cd4c3d4325ab77cb2f86b5507846c244",
      "tools/build_site.py": "f06d48be78cda32048c7b9dd38e321cff187a1a29b8746ff34e6f24ec87a6ca9",
      "tools/build_docs_html.py": "40e8c099acc77be8b3d57edd31f1e2a0ade323d9932e1c822aee98320c01f4a2",
      "tests/unit/test_site.py": "cf30077ae7888dc63e87e2fc12fee20b0b55cad568501a892096aea2afb997dc",
      "tests/unit/test_docs_html.py": "4f13fa6738f636c0034a5eb07c773961efd4396dcf806862695612f20f5762da"
    }
  }
}
---

# Handbook navigation and release availability

Evidence for [the user guide](../../USER_GUIDE.md).
