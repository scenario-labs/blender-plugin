# Adopted source provenance

## Studio form preparation

These Scenario form helpers and regression tests were moved from
[Scenario Blender Studio](https://github.com/edemaistre/scenario-blender-studio),
selected revision `e2b0277064f0c502d46524fba1d006d0ac83f846` (0.1.5).
Both files were introduced in source commit
[`6f269c8243611b7b531ddf003f2cf83da4b2df17`](https://github.com/edemaistre/scenario-blender-studio/commit/6f269c8243611b7b531ddf003f2cf83da4b2df17).

| Upstream path | Canonical path |
| --- | --- |
| `src/scenario_studio/schema.py` | [scenario/core/schema/forms.py](../scenario/core/schema/forms.py) |
| `tests/test_schema.py` | [tests/unit/test_forms.py](../tests/unit/test_forms.py) |

The intake preserves behavior. Changes are SPDX headers, test import
paths, Ruff formatting and an explicit `strict=False` on the existing `zip`
call to preserve its truncating semantics. No client, registration code or
Blender UI is imported. The existing conditional/one-of parameter implementation
remains in place until its contracts are reconciled with these form helpers.

These are first-party Scenario sources, covered by the repository license in
[scenario/LICENSE](../scenario/LICENSE). Original authorship is preserved in Git.
No fonts, icons, model records or media are included in this intake.

The dedicated intake/normalization PR precedes functional integration. Record
its final squash SHA in `.git-blame-ignore-revs` after merge; branch commit IDs
are not substitutes. Full-tree lint remains tracked under #28 while other
prototype source awaits replacement.
