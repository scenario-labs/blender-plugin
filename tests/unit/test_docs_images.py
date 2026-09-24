# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Keep documentation screenshots usable, referenced and small."""

import re
from pathlib import Path
from urllib.parse import unquote, urlsplit

import pytest

from tools.check_knowledge import parse_record

ROOT = Path(__file__).resolve().parents[2]
IMAGES = ROOT / "docs/images"
DOCUMENTS = [
    ROOT / "README.md",
    *sorted((ROOT / "docs").rglob("*.md")),
    ROOT / "docs/handbook-template.html",
]
UNREFERENCED_OK = {"social-preview.png"}  # GitHub's repository settings host the card.
TRUECOLOUR_OK = {"scenario-logo.png"}  # Preserve the exact upstream trademark asset.
MIN_ALT_WORDS = 8
MD_IMAGE = re.compile(r"!\[([^\]]*)\]\(([^)\s]+)")
NAME_REF = re.compile(r"(\w[\w.-]*\.png)")


def document_prose(document):
    text = document.read_text()
    if document.suffix == ".md" and text.startswith("---\n"):
        return parse_record(text)[1]
    return text


def colour_type(path):
    with path.open("rb") as stream:
        header = stream.read(26)
    assert len(header) == 26 and header[:8] == b"\x89PNG\r\n\x1a\n", f"{path.name} is not a PNG"
    assert header[12:16] == b"IHDR", f"{path.name} has no initial image header"
    return header[25]


def test_every_screenshot_is_referenced():
    references = {
        name for document in DOCUMENTS for name in NAME_REF.findall(document_prose(document))
    }
    orphans = sorted(
        path.name for path in IMAGES.glob("*.png") if path.name not in references | UNREFERENCED_OK
    )
    assert not orphans, f"Unreferenced files in docs/images: {orphans}"


def test_every_referenced_image_exists():
    for document in DOCUMENTS:
        for _alt, target in MD_IMAGE.findall(document_prose(document)):
            url = urlsplit(target)
            if not url.scheme and not url.netloc:
                assert (document.parent / unquote(url.path)).is_file(), (
                    f"{document.name}: missing image {target}"
                )


def test_screenshots_are_palette_quantised():
    bad = sorted(
        path.name
        for path in IMAGES.glob("*.png")
        if colour_type(path) != 3 and path.name not in TRUECOLOUR_OK
    )
    assert not bad, f"Run make images; still truecolour: {bad}"


def test_markdown_images_have_descriptive_alt_text():
    short = []
    for document in DOCUMENTS:
        if document.suffix != ".md":
            continue
        for alt, target in MD_IMAGE.findall(document_prose(document)):
            if (
                len(alt.split()) < MIN_ALT_WORDS
                or alt.strip().casefold() == Path(urlsplit(target).path).stem.casefold()
            ):
                short.append(f"{document.relative_to(ROOT)}: {target}")
    assert not short, "Describe each image in at least eight words:\n" + "\n".join(short)


def test_evidence_fingerprints_do_not_keep_orphan_images_alive(tmp_path, monkeypatch):
    images = tmp_path / "images"
    images.mkdir()
    (images / "orphan.png").write_bytes(b"unused image")
    record = tmp_path / "evidence.md"
    record.write_text(
        '---\n{"sources": {"images/orphan.png": "old fingerprint"}}\n---\n# Evidence\n'
    )
    monkeypatch.setitem(globals(), "DOCUMENTS", [record])
    monkeypatch.setitem(globals(), "IMAGES", images)
    with pytest.raises(AssertionError, match="Unreferenced.*orphan.png"):
        test_every_screenshot_is_referenced()
