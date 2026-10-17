# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The saved local MCP token: created once, private, reused, replaced on request."""

import os
import stat

import pytest

from scenario.mcp import local_token

POSIX = os.name == "posix"


def saved(directory):
    return (directory / local_token.TOKEN_FILE).read_text(encoding="ascii").strip()


def test_first_start_saves_a_private_token_that_later_starts_reuse(tmp_path):
    token = local_token.load_or_create(tmp_path)
    assert local_token.valid(token)
    assert saved(tmp_path) == token
    if POSIX:
        assert stat.S_IMODE((tmp_path / local_token.TOKEN_FILE).stat().st_mode) == 0o600
    assert local_token.load_or_create(tmp_path) == token
    assert [p.name for p in tmp_path.iterdir()] == [local_token.TOKEN_FILE]


def test_replace_saves_a_different_token(tmp_path):
    first = local_token.load_or_create(tmp_path)
    second = local_token.replace(tmp_path)
    assert second != first and saved(tmp_path) == second
    assert local_token.load_or_create(tmp_path) == second


@pytest.mark.parametrize(
    "content",
    [b"", b"   \n", b"short", b"has space inside the token value", b"\xff" * 30, b"a" * 300],
)
def test_an_empty_or_invalid_file_is_replaced_by_a_new_token(tmp_path, content):
    (tmp_path / local_token.TOKEN_FILE).write_bytes(content)
    token = local_token.load_or_create(tmp_path)
    assert local_token.valid(token) and saved(tmp_path) == token


@pytest.mark.skipif(not POSIX, reason="POSIX permissions")
def test_a_readable_older_file_is_kept_and_made_private(tmp_path):
    path = tmp_path / local_token.TOKEN_FILE
    path.write_text("A" * 32 + "\n", encoding="ascii")
    path.chmod(0o644)
    assert local_token.load_or_create(tmp_path) == "A" * 32
    assert stat.S_IMODE(path.stat().st_mode) == 0o600


@pytest.mark.skipif(not POSIX, reason="symbolic links and FIFOs")
def test_links_and_special_files_are_refused_not_followed(tmp_path):
    target = tmp_path / "elsewhere"
    target.write_text("B" * 32, encoding="ascii")
    (tmp_path / local_token.TOKEN_FILE).symlink_to(target)
    for call in (local_token.load_or_create, local_token.replace):
        with pytest.raises(OSError, match="not a link"):
            call(tmp_path)
    assert target.read_text(encoding="ascii") == "B" * 32
    fifo_dir = tmp_path / "fifo"
    fifo_dir.mkdir()
    os.mkfifo(fifo_dir / local_token.TOKEN_FILE)
    with pytest.raises(OSError, match="regular file"):
        local_token.load_or_create(fifo_dir)


def test_a_missing_folder_is_created(tmp_path):
    folder = tmp_path / "state" / "nested"
    token = local_token.load_or_create(folder)
    assert saved(folder) == token
