# Licence options and decision

Prepared for [#26](https://github.com/scenario-labs/blender-plugin/issues/26).
**Decision: GPL-3.0-or-later.** On 2026-10-13 the maintainer decided to keep the
licence that 0.10.0 shipped under, and #26 is closed. The comparison below
informed that decision and remains as background. It changes no licence and
records no IP assignment or permission to relicense. Contributions remain
inbound=outbound under GPL-3.0-or-later.

## Constraints and current evidence

[Blender's licensing guidance](https://www.blender.org/about/license/) requires
published Python add-ons to use a GPL-compatible licence. Its separate
[Extensions Platform policy](https://docs.blender.org/manual/en/latest/advanced/extensions/licenses.html)
requires GPL-3.0-or-later add-ons and CC0 assets. Releases use GitHub assets and
the project's own extension repository; listing eligibility is a separate
question, not a reason to erase existing asset licences.

The [root GPL text](../../LICENSE) and [packaged copy](../../scenario/LICENSE)
are identical; the [manifest](../../scenario/blender_manifest.toml) declares
GPL-3.0-or-later. Every tracked Python and shell file carries that SPDX
identifier. [Contributions](../../CONTRIBUTING.md#licensing-of-contributions)
and the [PR template](../../.github/pull_request_template.md) already specify
inbound=outbound GPL-3.0-or-later, with no copyright assignment, CLA or DCO.

This is not a single-licence ownership inventory. The
[SDK bundle](../SDK_BUNDLE.md#notices-and-upgrades) preserves MIT, BSD, Apache,
MPL and other dependency notices. The
[roadmap consolidation amendment](https://github.com/scenario-labs/roadmap/issues/672)
also requires adopted Studio source and font/icon/asset attribution to survive.
Commit authors, SPDX lines and company affiliation do not establish an IP
assignment or authority over every contribution. The original issue's assumption
that Scenario can unilaterally relicense every line must be verified, not reused.

## Four alternatives

The options below concern code for which the necessary rights are confirmed.
Original third-party terms remain in every option. GPL permits commercial use;
its copyleft obligations concern distribution and derivative works, not a blanket
ban on selling software. See the [GNU licence comparison](https://www.gnu.org/licenses/license-list.html)
and [compatibility guidance](https://www.gnu.org/licenses/gpl-faq.html#AllCompatibility).

| Option | Benefits and constraints | Migration cost and legal check |
| --- | --- | --- |
| **Keep GPL-3.0-or-later** | Matches current headers, inbound terms and the platform's add-on licence requirement. Distribution remains subject to GPL obligations; it does not offer permissive reuse of Scenario's GPL code by itself. | No code-licence migration. Continue bundled-notice checks and attribution review; the bundled icons' first-party origin is recorded in `scenario/icons/README.md`. Confirm that this remains the intended policy; no new ownership assertion is needed to retain existing grants. |
| **GPL-2.0-or-later** | Adds an older GPL version without a demonstrated product requirement. Apache-2.0 is compatible with GPLv3, not GPLv2; choosing GPLv3 under an or-later grant can matter for the actual dependency combination. Platform listing still needs a GPLv3-or-later-compliant submission. | Broad header, licence-text and documentation review with little demonstrated benefit. Counsel must assess rights to offer GPLv2 and the exact dependency combination. Existing GPLv3-only contributions cannot simply be relabelled GPLv2. |
| **MIT or BSD-3-Clause for Scenario-owned extension code** | Permissive reuse could align with sibling projects. These licences are GPL-compatible according to the GNU list, but that does not remove Blender-related distribution obligations or change third-party terms. A permissive-only add-on declaration does not meet the platform's stated GPL-3.0-or-later requirement. | Broad migration across eligible source, package declarations, notices and contribution policy. Confirm ownership/consents and legal treatment of the distributed combination first; changing a root file cannot relicense adopted GPL code. |
| **MIT core, GPL-3.0-or-later Blender layer** | Could support reuse outside Blender while keeping the extension layer GPL. The current core avoids `bpy`, but an import boundary alone proves neither independent packaging nor licence separability. | Highest ongoing complexity: audit the core and its dependencies, define the package boundary, map files to licences, preserve notices, test separate packaging and document inbound terms by component. Counsel must confirm ownership/consents and the proposed separation. |

## Change inventory and decision gate

For any approved change, review root and packaged `LICENSE`, any component
`LICENSES/` texts, manifest licence metadata, affected SPDX headers, README
badge/notice, the user guide, TRADEMARKS code-licence wording, CONTRIBUTING inbound
terms, the PR template, canonical agent guidance and licence/bundle checks.
A split needs an explicit per-component licence map; a manifest list or GitHub
badge is not that map. Verify GitHub's resulting detection rather than promising
a particular label. The header inventory far exceeds the original issue's 135
files; no bulk replacement of adopted notices is safe.
Already published releases retain their original terms and bytes.

The comparison recommended retaining the current policy unless maintainers
identified a concrete permissive-reuse requirement and, if they did, evaluating
an independently packaged core before proposing a whole-extension migration.
The decision followed it, so no licence text, header, manifest declaration or
contribution term changes.

A later proposal to change the licence would record the chosen option, decision
date, approvers and verified rights/consents, and amend roadmap D14/D15 while
retaining the consolidation amendment's attribution requirements. It would then
implement only the approved changes, verify exact ZIP licence texts, update
contribution terms and need a separately authorized release. This page grants
no release or relicensing authorization.
