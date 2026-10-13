<!-- SPDX-FileCopyrightText: 2026 Scenario Inc. -->
<!-- SPDX-License-Identifier: GPL-3.0-or-later -->
# Scenario icons

This folder contains the eight modality and prompt-tool marks: `image`, `video`,
`audio`, `3d`, `text`, `dice`, `sparkles` and `translate`. Each has a 64 px
`<name>.png` and a 32 px `<name>_32.png`.
[The Blender loader](../blender/icons.py) loads the 64 px files into a preview
collection and falls back to built-in icons when previews are unavailable.

## Generator and origin

The source generator is
[`tools/make_icons.py`](https://github.com/scenario-labs/blender-plugin/blob/main/tools/make_icons.py).
It draws light-grey shapes on a transparent background, using 1.5 px strokes
on a 16-unit grid and downsampling the larger working canvas. Its description
says that the glyphs match the Scenario web app's icon style.

The designs are first-party. On 2026-10-13 the web app's source was checked
([#24](https://github.com/scenario-labs/blender-plugin/issues/24)):
- **The web app's own icons.** Its image, video, audio, 3D, text, dice,
  sparkles and translate icons are Scenario Inc.'s own SVG artwork, filled shapes
  exported from its design files, with no third-party attribution.
- **Third-party sets.** The web app's third-party icon packages are used for
  other glyphs, never for these eight.
- **This folder.** The generator draws its own stroke versions in that style; it
  copies no path data from the web app or from any icon set.

Record any upstream set, licence and required notice here if a future icon is
adopted from one.

## Font option

The default generator draws the translate icon's Latin A with strokes.
`--font-a` instead selects a font available on the generating machine, so the
result can depend on the machine's font installation. Its candidates include
DejaVu, Blender's bundled Inter, Arial, Liberation Sans and Helvetica.

Do not use that option for a distributed icon without first identifying the
actual font and version and reviewing its terms and any required notices.
For example, Blender's bundled Inter uses the SIL Open Font License 1.1;
its DejaVu Sans Mono notice covers Bitstream Vera and Arev, with DejaVu changes
in the public domain. Those examples do not establish rights for a different
system font or prove which generator invocation produced an existing PNG.

## Licence and distribution

The repository's current first-party policy is GPL-3.0-or-later, copyright
Scenario Inc.; the unchanged [GPL text](../LICENSE) ships in the extension.
This policy does not replace any third-party terms or resolve the open design
origin question above. This notice adds no claim of permission to relicense
upstream artwork.

[Blender's Extensions Platform policy](https://docs.blender.org/manual/en/latest/advanced/extensions/licenses.html)
requires CC0 assets for its listings. This extension is distributed outside that
platform; no CC0 grant or platform-listing acceptance is claimed here.
