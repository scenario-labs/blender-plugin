# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Build the repository's social card with the locked development-only Pillow.

Run with: uv run --locked --no-env-file python tools/make_social_preview.py
The source is illustrative 3D artwork, not a capture of a paid plugin result.
Supply --artwork PATH for a replacement wide illustration.
Review the result for trademarks, private data and text legibility before upload.
"""

import argparse
import io
import os
import sys
import tempfile
import tomllib
from pathlib import Path

from PIL import Image, ImageDraw, ImageFont

ROOT = Path(__file__).resolve().parents[1]
ARTWORK = ROOT / "tools/assets/social-preview-artwork.png"
OUTPUT = ROOT / "docs/images/social-preview.png"
LOGO = ROOT / "docs/images/scenario-logo.png"
SIZE = (1280, 640)


def font(path, size):
    return ImageFont.truetype(path, size) if path else ImageFont.load_default(size=size)


def wrap(draw, text, face, width):
    lines, current = [], ""
    for word in text.split():
        if draw.textlength(word, font=face) > width:
            raise ValueError("A tagline word is too wide; revise the text or selected font")
        candidate = f"{current} {word}".strip()
        if draw.textlength(candidate, font=face) <= width:
            current = candidate
        else:
            lines.append(current)
            current = word
    if current:
        lines.append(current)
    if not lines or len(lines) > 4:
        raise ValueError("The manifest tagline must fit within four lines")
    return lines


def compose(artwork, font_path):
    manifest = tomllib.loads((ROOT / "scenario/blender_manifest.toml").read_text())
    tagline = manifest["tagline"]
    if not isinstance(tagline, str):
        raise ValueError("The manifest tagline must be text")
    with Image.open(artwork) as source:
        if source.width < SIZE[0] or source.height < SIZE[1]:
            raise ValueError("Artwork must be at least 1280 by 640 pixels")
        if source.width != source.height * 2:
            raise ValueError("Artwork must use a 2:1 composition with a dark left text area")
        background = source.convert("RGB").resize(SIZE, Image.Resampling.LANCZOS)
    # Keep the upstream logo's opaque black background seamless, while letting
    # the artwork fill the card instead of presenting it as an interface panel.
    mask = Image.new("L", SIZE)
    mask.putdata(
        [max(0, min(255, (x - 400) * 255 // 300)) for _ in range(SIZE[1]) for x in range(SIZE[0])]
    )
    card = Image.composite(background, Image.new("RGB", SIZE, "black"), mask)
    draw = ImageDraw.Draw(card)
    with Image.open(LOGO) as original:
        logo = original.convert("RGB")
    logo = logo.resize((round(logo.width * 84 / logo.height), 84), Image.Resampling.LANCZOS)
    card.paste(logo, (64, 64))
    heading, body, footer = (font(font_path, size) for size in (64, 30, 24))
    title = "Scenario for Blender"
    address = "github.com/scenario-labs/blender-plugin"
    if draw.textlength(title, font=heading) > 624 or draw.textlength(address, font=footer) > 624:
        raise ValueError("The selected font does not fit the title or repository address")
    draw.text((64, 200), title, font=heading, fill=(245, 245, 245))
    for index, line in enumerate(wrap(draw, tagline, body, 560)):
        draw.text((64, 300 + 40 * index), line, font=body, fill=(160, 160, 165))
    draw.text((64, 552), address, font=footer, fill=(160, 160, 165))
    # Palette output remains compatible with the documentation image checks.
    card = card.quantize(colors=256, method=Image.Quantize.MEDIANCUT, dither=Image.Dither.NONE)
    buffer = io.BytesIO()
    card.save(buffer, format="PNG", optimize=True)
    content = buffer.getvalue()
    if len(content) >= 1_000_000:
        raise ValueError("The social card exceeds GitHub's one-megabyte limit")
    return content


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--artwork", type=Path, default=ARTWORK)
    parser.add_argument("--font", type=Path, help="Optional TrueType/OpenType font")
    parser.add_argument("--output", type=Path, default=OUTPUT)
    args = parser.parse_args(argv)
    try:
        content = compose(args.artwork, args.font)
        args.output.parent.mkdir(parents=True, exist_ok=True)
        temporary = None
        try:
            with tempfile.NamedTemporaryFile(
                dir=args.output.parent, prefix=f".{args.output.name}.", suffix=".tmp", delete=False
            ) as handle:
                temporary = Path(handle.name)
                handle.write(content)
            os.replace(temporary, args.output)
        finally:
            if temporary is not None:
                temporary.unlink(missing_ok=True)
    except (OSError, ValueError, KeyError, Image.DecompressionBombError) as error:
        print(f"Social preview: {error}", file=sys.stderr)
        return 1
    destination = args.output.resolve()
    label = destination.relative_to(ROOT) if destination.is_relative_to(ROOT) else destination
    print(f"wrote {label} ({len(content)} bytes)")
    return 0


if __name__ == "__main__":
    sys.exit(main())
