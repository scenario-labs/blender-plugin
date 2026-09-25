# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Documentation image policy and bounded, per-file PNG optimization."""

import os
import re
import shutil
import stat
import struct
import subprocess
import tempfile
import zlib
from dataclasses import dataclass
from pathlib import Path
from urllib.parse import unquote, urlsplit

from tools.check_knowledge import parse_record

ROOT = Path(__file__).resolve().parents[1]
UNREFERENCED_OK = {"social-preview.png"}  # GitHub's repository settings host the card.
TRUECOLOUR_OK = {"scenario-logo.png"}  # Preserve the exact upstream trademark asset.
OPTIMIZE_EXCLUSIONS = {
    "scenario-logo.png": "preserve upstream bytes",
    "social-preview.png": "regenerate with tools/make_social_preview.py",
}
MIN_ALT_WORDS = 8
MAX_PNG_BYTES = 64 * 1024 * 1024
MAX_PIXELS = 64 * 1024 * 1024
OPTIMIZER_TIMEOUT = 30
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)")
NAME_REF = re.compile(r"(\w[\w.-]*\.png)", re.IGNORECASE)
PNG_SIGNATURE = b"\x89PNG\r\n\x1a\n"


@dataclass(frozen=True)
class PNGInfo:
    width: int
    height: int
    colour_type: int
    size: int


def document_prose(document):
    text = document.read_text(encoding="utf-8")
    if document.suffix == ".md" and text.startswith("---\n"):
        return parse_record(text)[1]
    return text


def _read_regular(path):
    before = path.lstat()
    if not stat.S_ISREG(before.st_mode):
        raise ValueError(f"Expected a regular non-symlink PNG: {path.name}")
    with path.open("rb") as stream:
        opened = os.fstat(stream.fileno())
        if (before.st_dev, before.st_ino) != (opened.st_dev, opened.st_ino):
            raise ValueError(f"PNG changed while opening: {path.name}")
        data = stream.read(MAX_PNG_BYTES + 1)
    if len(data) > MAX_PNG_BYTES:
        raise ValueError(f"PNG exceeds {MAX_PNG_BYTES} bytes: {path.name}")
    return data


def _png_info(data, name):
    if not data.startswith(PNG_SIGNATURE):
        raise ValueError(f"Not a PNG: {name}")
    offset = len(PNG_SIGNATURE)
    header = None
    palette = False
    image_data = False
    ended_data = False
    while offset < len(data):
        if len(data) - offset < 12:
            raise ValueError(f"Truncated PNG chunk: {name}")
        length = int.from_bytes(data[offset : offset + 4], "big")
        kind = data[offset + 4 : offset + 8]
        end = offset + 12 + length
        if end > len(data):
            raise ValueError(f"Truncated PNG chunk: {name}")
        payload = data[offset + 8 : end - 4]
        crc = int.from_bytes(data[end - 4 : end], "big")
        if zlib.crc32(kind + payload) != crc:
            raise ValueError(f"Invalid PNG checksum: {name}")
        if kind in (b"acTL", b"fcTL", b"fdAT"):
            raise ValueError(f"Animated PNG is unsupported; use a static screenshot: {name}")
        if header is None:
            if kind != b"IHDR" or length != 13:
                raise ValueError(f"Missing initial PNG image header: {name}")
            width, height, depth, colour, compression, filtering, interlace = struct.unpack(
                ">IIBBBBB", payload
            )
            depths = {0: {1, 2, 4, 8, 16}, 2: {8, 16}, 3: {1, 2, 4, 8}, 4: {8, 16}, 6: {8, 16}}
            if (
                not width
                or not height
                or width * height > MAX_PIXELS
                or depth not in depths.get(colour, ())
                or compression != 0
                or filtering != 0
                or interlace not in (0, 1)
            ):
                raise ValueError(f"Invalid or oversized PNG header: {name}")
            header = PNGInfo(width, height, colour, len(data))
        elif kind == b"IHDR":
            raise ValueError(f"Duplicate PNG header: {name}")
        elif kind == b"PLTE":
            if (
                palette
                or image_data
                or not length
                or length % 3
                or length > 768
                or header.colour_type in (0, 4)
                or (header.colour_type == 3 and length // 3 > 2**depth)
            ):
                raise ValueError(f"Invalid PNG palette: {name}")
            palette = True
        elif kind == b"IDAT":
            if ended_data or (header.colour_type == 3 and not palette):
                raise ValueError(f"Invalid PNG image-data order: {name}")
            image_data = True
        elif kind == b"IEND":
            if length or not image_data or end != len(data):
                raise ValueError(f"Invalid PNG end: {name}")
            return header
        elif not kind.isalpha() or kind[0] & 32 == 0:
            raise ValueError(f"Unsupported critical PNG chunk: {name}")
        if image_data and kind != b"IDAT":
            ended_data = True
        offset = end
    raise ValueError(f"Missing PNG end: {name}")


def png_info(path):
    path = Path(path)
    return _png_info(_read_regular(path), path.name)


def _images(root):
    root = Path(root).resolve()
    for directory in (root / "docs", root / "docs/images"):
        if directory.is_symlink() or not directory.is_dir():
            raise ValueError("docs/images must be a regular repository directory")
    return root / "docs/images"


def _selection(root, names):
    directory = _images(root)
    entries = {path.name for path in directory.iterdir()}
    if not names:
        names = [name for name in entries if Path(name).suffix.lower() == ".png"]
    selected = []
    for name in sorted(set(names)):
        if (
            not name
            or name != name.strip()
            or "/" in name
            or "\\" in name
            or ":" in name
            or any(ord(character) < 32 for character in name)
            or Path(name).suffix.lower() != ".png"
        ):
            raise ValueError(f"Expected a PNG basename, not a path: {name!r}")
        if name not in entries:
            raise ValueError(f"No PNG with that exact basename in docs/images: {name!r}")
        path = directory / name
        data = _read_regular(path)
        selected.append((path, data, _png_info(data, name)))
    return selected


def check(root=ROOT):
    """Return sorted policy diagnostics; malformed inputs raise instead of passing."""
    root = Path(root).resolve()
    selected = _selection(root, ())
    documents = [root / "README.md", *sorted((root / "docs").rglob("*.md"))]
    documents.append(root / "docs/handbook-template.html")
    prose = [(path, document_prose(path)) for path in documents]
    references = {name for _path, text in prose for name in NAME_REF.findall(text)}
    messages = []
    for path, _data, info in selected:
        if path.name not in references | UNREFERENCED_OK:
            messages.append(f"Unreferenced image: {path.name}")
        if info.colour_type != 3 and path.name not in TRUECOLOUR_OK:
            remedy = OPTIMIZE_EXCLUSIONS.get(path.name, "run make images")
            messages.append(f"Non-palette screenshot: {path.name}; {remedy}")
    for document, text in prose:
        for alt, target in MD_IMAGE.findall(text):
            url = urlsplit(target)
            if not url.scheme and not url.netloc:
                path = unquote(url.path)
                if path.startswith("/"):
                    messages.append(
                        f"{document.relative_to(root)}: root-relative image {target}; "
                        "use a path relative to the document"
                    )
                elif not (document.parent / path).is_file():
                    messages.append(f"{document.relative_to(root)}: missing image {target}")
            if document.suffix == ".md" and (
                len(alt.split()) < MIN_ALT_WORDS
                or alt.strip().casefold() == Path(url.path).stem.casefold()
            ):
                messages.append(f"{document.relative_to(root)}: describe {target} in eight words")
    return sorted(set(messages))


def optimize(root=ROOT, names=(), *, dry_run=False, timeout=OPTIMIZER_TIMEOUT):
    """Optimize selected non-palette screenshots; never requantize existing palettes."""
    messages = []
    changed = 0
    skipped = 0
    try:
        selected = _selection(root, names)
        candidates = []
        for path, data, info in selected:
            if path.name in OPTIMIZE_EXCLUSIONS:
                messages.append(f"Skipped {path.name}: {OPTIMIZE_EXCLUSIONS[path.name]}")
                skipped += 1
            elif info.colour_type == 3:
                messages.append(f"Unchanged {path.name}: already palette PNG")
                skipped += 1
            else:
                candidates.append((path, data, info))
        tool = shutil.which("pngquant") if candidates and not dry_run else None
        if candidates and not dry_run and not tool:
            raise ValueError("pngquant not found; install pngquant before optimizing screenshots")
        for path, original, before in candidates:
            if dry_run:
                messages.append(f"Would optimize {path.name}")
                continue
            with tempfile.TemporaryDirectory(prefix=".optimize-", dir=path.parent) as temporary:
                source = Path(temporary) / "source.png"
                source.write_bytes(original)
                output = Path(temporary) / "optimized.png"
                result = subprocess.run(
                    [
                        tool,
                        "--quality=70-90",
                        "--nofs",
                        "--strip",
                        "--skip-if-larger",
                        "--output",
                        str(output),
                        "--",
                        str(source),
                    ],
                    capture_output=True,
                    timeout=timeout,
                    check=False,
                )
                if result.returncode in (98, 99):
                    reason = (
                        "would not shrink" if result.returncode == 98 else "minimum quality unmet"
                    )
                    messages.append(f"Unchanged {path.name}: {reason} ({result.returncode})")
                    skipped += 1
                    continue
                if result.returncode:
                    raise ValueError(f"pngquant failed for {path.name}: exit {result.returncode}")
                after = png_info(output)
                if (
                    (after.width, after.height) != (before.width, before.height)
                    or after.colour_type != 3
                    or after.size >= before.size
                ):
                    raise ValueError(
                        f"Unsafe optimizer output for {path.name}: dimensions/palette/size"
                    )
                if _read_regular(path) != original:
                    raise ValueError(f"Source changed during optimization: {path.name}")
                os.chmod(output, stat.S_IMODE(path.stat().st_mode))
                os.replace(output, path)
                messages.append(f"Optimized {path.name}: {before.size} -> {after.size} bytes")
                changed += 1
        problems = check(root)
        pending = len(candidates) if dry_run else 0
        messages.extend(problems)
        messages.append(
            f"Summary: {changed} changed, {skipped} skipped, {pending} pending; "
            f"{len(problems)} validation issue(s)."
        )
        return (1 if problems or pending else 0), messages
    except (OSError, ValueError, subprocess.SubprocessError) as error:
        return 2, messages + [f"Asset error: {error}"]
