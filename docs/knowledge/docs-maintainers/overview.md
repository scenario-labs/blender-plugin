---
{
  "type": "Evidence",
  "id": "docs-maintainers.overview",
  "title": "docs/MAINTAINERS.md: overview",
  "description": "Repository evidence for the named source family and canonical document.",
  "evidence": {
    "path": "docs/MAINTAINERS.md",
    "coverage": "policy",
    "reviewed_at": "2026-09-25",
    "limits": "Scoped repository policy and read-only GitHub settings read-back, with actual state distinguished from pending owner/admin decisions. Public source fingerprints cover the linked local contracts; live API evidence is recorded in the PR and must be read back before an administrative action. No settings, token scopes, grants, visibility, release publication or hosted acceptance were changed or inferred. 2026-10-13 note: the social preview paragraph and the #19 admin item now record the uploaded card, read back through GraphQL (usesCustomOpenGraphImage true, image URL on repository-images.githubusercontent.com), the repository page's og:image, and a byte comparison of the served image with docs/images/social-preview.png. A rendered shared-link preview in another application was not checked and stays an open recheck once link caches refresh; #19 is closed. 2026-10-13: the Actions row, the Dependabot paragraph and the #39 admin item now record required full-SHA pinning and the seven-day cooldown. The setting was read back with `gh api repos/scenario-labs/blender-plugin/actions/permissions` (allowed_actions all, sha_pinning_required true); a reviewer can re-run that command. Review follow-up on 2026-10-13: this topic was re-read for the pinning and cooldown change, so fingerprints of files the change edits now match them.",
    "sources": {
      ".github/CODEOWNERS": "6195d5d3ae33bda4050af6370b0231928507d52952ad5bd31f04f1a0a739bdc8",
      ".github/dependabot.yml": "e9e9d0d08cc7300deb06b90a19116dd21a426dbe7b639419517444347dd31204",
      ".github/workflows/ci.yml": "9805ee9848f2eed06b0b9f108bcd7054592d61b431f8f4b57d4098f5cf43c344",
      ".github/workflows/release-please.yml": "72a2af0eae492c029031fa8e1e8cf5fdf64cf84c3b8474953c270f127ad79047",
      "AGENTS.md": "ab4603ba140e0571d7aa952255779674d8fcc79a0df5b0a15064761b2ceabd3a",
      "CONTRIBUTING.md": "7cc37fc9869fec3adc20a6fd302760559f9c5c1db2ae4ecbfb11fa3b3cedfdc5",
      "docs/RELEASING.md": "a4937aac0e28fdb4693630e016cca7a010413fe10c021370b5ae4eddc224ced6",
      "docs/SDK_BUNDLE.md": "161627add3fd5b146643fddc2c496a48023406383748e96b6fbdbbed75960ddb",
      "docs/development/contributions.md": "54ed3fb7f84c53ec1c88874a22fc917987b8e5e934c92d69e27f9e06a57b1289",
      "scenario/blender_manifest.toml": "7ac4a84b0856f6a7c5ada8182e1c343f097347a25cf5785d81d72b28ec10f444"
    },
    "scope": "overview",
    "base_revision": "cdc8775a4a074a4997eca84cec2699e0dbb16e8c"
  }
}
---

# docs/MAINTAINERS.md: overview

Evidence for [the canonical document](../../MAINTAINERS.md).

Source families separate independent maintenance work. The review date, coverage,
source fingerprints and document-wide limitations were preserved during the split.
Grouping sources does not renew the review or attribute every inherited claim to
this subset. Review and narrow this topic's limits when its evidence changes.
