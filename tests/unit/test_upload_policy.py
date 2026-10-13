# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Which local files a connected agent may upload: extension folders and session choices."""

import builtins
import io
import os
from pathlib import Path

import pytest

from scenario.mcp import upload_policy
from scenario.mcp.upload_policy import ChosenFiles, UploadRefused, allowed_upload


@pytest.fixture
def layout(tmp_path):
    root = tmp_path / "extension"
    (root / "state" / "shared-results").mkdir(parents=True)
    outside = tmp_path / "home"
    outside.mkdir()
    produced = root / "state" / "shared-results" / "result.png"
    produced.write_bytes(b"result")
    private = outside / "private.png"
    private.write_bytes(b"private")
    return root.resolve(), outside.resolve(), produced.resolve(), private.resolve()


def symlink(link, target):
    try:
        link.symlink_to(target)
    except (OSError, NotImplementedError):
        pytest.skip("This platform or account cannot create symbolic links")


def test_file_the_extension_produced_is_allowed(layout):
    root, _outside, produced, _private = layout
    assert allowed_upload(str(produced), roots=[root], chosen=ChosenFiles()) == produced


def test_file_chosen_this_session_is_allowed(layout):
    root, _outside, _produced, private = layout
    chosen = ChosenFiles()
    assert chosen.record(str(private)) == private
    assert allowed_upload(str(private), roots=[root], chosen=chosen) == private


def test_other_readable_file_is_refused(layout):
    root, outside, _produced, private = layout
    chosen = ChosenFiles()
    chosen.record(str(private))
    other = outside / "other.png"
    other.write_bytes(b"other")
    with pytest.raises(UploadRefused, match="Nothing was read or sent"):
        allowed_upload(str(other), roots=[root], chosen=chosen)


def test_link_inside_an_allowed_folder_is_judged_by_its_target(layout):
    root, _outside, produced, private = layout
    escape = root / "state" / "escape.png"
    symlink(escape, private)
    with pytest.raises(UploadRefused):
        allowed_upload(str(escape), roots=[root], chosen=ChosenFiles())
    inside = root / "state" / "inside.png"
    symlink(inside, produced)
    assert allowed_upload(str(inside), roots=[root], chosen=ChosenFiles()) == produced


def test_linked_folder_escaping_an_allowed_root_is_refused(layout):
    root, outside, _produced, _private = layout
    symlink(root / "state" / "linked", outside)
    with pytest.raises(UploadRefused):
        allowed_upload(
            str(root / "state" / "linked" / "private.png"), roots=[root], chosen=ChosenFiles()
        )


def test_dot_dot_out_of_an_allowed_root_is_refused(layout):
    root, _outside, _produced, private = layout
    path = root / "state" / ".." / ".." / private.parent.name / private.name
    with pytest.raises(UploadRefused):
        allowed_upload(str(path), roots=[root], chosen=ChosenFiles())


def test_chosen_link_allows_its_target_but_not_a_later_retarget(layout):
    root, outside, _produced, private = layout
    link = outside / "link.png"
    symlink(link, private)
    chosen = ChosenFiles()
    assert chosen.record(str(link)) == private
    assert allowed_upload(str(link), roots=[root], chosen=chosen) == private
    secret = outside / "secret.png"
    secret.write_bytes(b"secret")
    link.unlink()
    symlink(link, secret)
    with pytest.raises(UploadRefused):
        allowed_upload(str(link), roots=[root], chosen=chosen)


@pytest.mark.parametrize("name", ["missing.png", "folder"])
def test_missing_file_or_folder_is_refused_with_the_same_message(layout, name):
    root, outside, _produced, _private = layout
    (outside / "folder").mkdir()
    chosen = ChosenFiles()
    assert chosen.record(str(outside / name)) is None
    assert len(chosen) == 0
    with pytest.raises(UploadRefused) as missing:
        allowed_upload(str(outside / name), roots=[root], chosen=chosen)
    with pytest.raises(UploadRefused) as outside_file:
        allowed_upload(str(layout[3]), roots=[root], chosen=chosen)
    # One answer for both, so refusals reveal nothing about which files exist.
    assert str(missing.value) == str(outside_file.value) == upload_policy.REFUSED


@pytest.mark.parametrize("raw", ["", None, 42, "bad\0path.png"])
def test_invalid_paths_are_refused(layout, raw):
    root = layout[0]
    with pytest.raises(UploadRefused):
        allowed_upload(raw, roots=[root], chosen=ChosenFiles())


def test_home_shorthand_is_expanded_before_comparison(layout, monkeypatch):
    root, outside, _produced, private = layout
    monkeypatch.setenv("HOME", str(outside))
    monkeypatch.setenv("USERPROFILE", str(outside))
    chosen = ChosenFiles()
    chosen.record(str(private))
    assert allowed_upload("~/private.png", roots=[root], chosen=chosen) == private


def test_missing_or_unusable_roots_allow_nothing(layout):
    _root, outside, produced, _private = layout
    for roots in ([], [outside / "missing"], [produced], [None]):
        with pytest.raises(UploadRefused):
            allowed_upload(str(produced), roots=roots, chosen=ChosenFiles())


def test_refusal_reads_nothing(layout, monkeypatch):
    root, outside, _produced, private = layout
    other = outside / "other.png"
    other.write_bytes(b"other")

    def no_read(*args, **kwargs):
        raise AssertionError("the policy must not open a file it refuses")

    monkeypatch.setattr(builtins, "open", no_read)
    monkeypatch.setattr(io, "open", no_read)
    monkeypatch.setattr(os, "open", no_read)
    monkeypatch.setattr(Path, "open", no_read)
    for path in (other, outside / "missing.png"):
        with pytest.raises(UploadRefused):
            allowed_upload(str(path), roots=[root], chosen=ChosenFiles())


def test_chosen_files_forget_the_oldest_past_their_limit(layout):
    _root, outside, _produced, _private = layout
    chosen = ChosenFiles(limit=2)
    paths = []
    for index in range(3):
        path = outside / f"chosen-{index}.png"
        path.write_bytes(b"x")
        paths.append(chosen.record(str(path)))
    assert len(chosen) == 2
    assert paths[0] not in chosen
    assert paths[1] in chosen and paths[2] in chosen
    chosen.record(str(paths[1]))  # Choosing again refreshes it.
    newest = outside / "chosen-3.png"
    newest.write_bytes(b"x")
    chosen.record(str(newest))
    assert paths[1] in chosen and paths[2] not in chosen
