# Adopted source provenance

## Studio form preparation

The following source and regression tests come from
[Scenario Blender Studio](https://github.com/edemaistre/scenario-blender-studio),
selected revision `e2b0277064f0c502d46524fba1d006d0ac83f846` (0.1.5).
Both files were introduced by **Emmanuel de Maistre** in upstream commit
[`6f269c8243611b7b531ddf003f2cf83da4b2df17`](https://github.com/edemaistre/scenario-blender-studio/commit/6f269c8243611b7b531ddf003f2cf83da4b2df17).

| Upstream path | Canonical path |
| --- | --- |
| `src/scenario_studio/schema.py` | [scenario/core/schema/forms.py](../scenario/core/schema/forms.py) |
| `tests/test_schema.py` | [tests/unit/test_forms.py](../tests/unit/test_forms.py) |

The intake preserves behavior. Changes are SPDX/provenance headers, test import
paths, Ruff formatting and an explicit `strict=False` on the existing `zip`
call to preserve its truncating semantics. No client, registration code or
Blender UI is imported. The existing conditional/one-of parameter implementation
remains in place until its contracts are reconciled with these form helpers.

Studio's manifest licenses its source as GPL-3.0-or-later and attributes it to
2026 Scenario. Its original GPL text is preserved verbatim as
[scenario/licenses/Studio-GPL-3.0.txt](../scenario/licenses/Studio-GPL-3.0.txt).
That copy uses older FSF URLs; the canonical root and package `LICENSE` files
remain identical. No Studio fonts, icons, model records or media are included in
this intake, so their separate notices arrive with their eventual resources.

The dedicated intake/normalization PR precedes functional integration. Record
its final squash SHA in `.git-blame-ignore-revs` after merge; branch commit IDs
are not substitutes. Full-tree lint remains tracked under #28 while other
prototype source awaits replacement.
