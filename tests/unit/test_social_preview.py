# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The committed sharing card meets the repository image requirements."""

import struct
from contextlib import contextmanager
from pathlib import Path

import pytest
from PIL import Image

from tools import make_social_preview as preview

CARD = Path(__file__).resolve().parents[2] / "docs/images/social-preview.png"


def test_social_preview_dimensions_and_size():
    content = CARD.read_bytes()
    assert content[:8] == b"\x89PNG\r\n\x1a\n"
    assert content[12:16] == b"IHDR"
    assert struct.unpack(">II", content[16:24]) == (1280, 640)
    assert content[25] == 3
    assert len(content) < 1_000_000


def test_success_replaces_output_and_removes_temporary_file(tmp_path, monkeypatch):
    output = tmp_path / "preview.png"
    output.write_bytes(b"previous card")
    monkeypatch.setattr(preview, "compose", lambda *_: b"replacement card")
    assert preview.main(["--output", str(output)]) == 0
    assert output.read_bytes() == b"replacement card"
    assert list(tmp_path.iterdir()) == [output]


@pytest.mark.parametrize("failure", ["write", "replace"])
def test_output_io_failure_preserves_previous_card(tmp_path, monkeypatch, capsys, failure):
    output = tmp_path / "preview.png"
    output.write_bytes(b"previous card")
    monkeypatch.setattr(preview, "compose", lambda *_: b"replacement card")
    original = preview.tempfile.NamedTemporaryFile

    @contextmanager
    def interrupted_write(*args, **kwargs):
        with original(*args, **kwargs) as handle:
            write = handle.write

            def fail(content):
                write(content[: len(content) // 2])
                handle.flush()
                raise OSError("synthetic write failure")

            handle.write = fail
            yield handle

    def interrupted_replace(*_):
        raise OSError("synthetic replacement failure")

    if failure == "write":
        monkeypatch.setattr(preview.tempfile, "NamedTemporaryFile", interrupted_write)
    else:
        monkeypatch.setattr(preview.os, "replace", interrupted_replace)
    assert preview.main(["--output", str(output)]) == 1
    assert capsys.readouterr().err.startswith("Social preview: synthetic")
    assert output.read_bytes() == b"previous card"
    assert list(tmp_path.iterdir()) == [output]


def test_oversized_artwork_fails_cleanly_without_replacing_card(tmp_path, monkeypatch, capsys):
    artwork = tmp_path / "artwork.png"
    Image.new("RGB", (1280, 640)).save(artwork)
    output = tmp_path / "preview.png"
    output.write_bytes(b"previous card")
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 1)
    assert preview.main(["--artwork", str(artwork), "--output", str(output)]) == 1
    error = capsys.readouterr().err
    assert error.startswith("Social preview:")
    assert "decompression bomb" in error
    assert output.read_bytes() == b"previous card"
