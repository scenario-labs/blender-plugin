# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Film export name suggestions and the agent Output Folder policy, without Blender."""

from pathlib import Path

import pytest

from scenario.core.jobs import film_export_policy as policy
from scenario.core.jobs import local_export as export


@pytest.mark.parametrize(
    "title, mode, expected",
    [
        ("Prepared cut", "final", "Prepared cut - Final Review.mp4"),
        ("Act 1: the  return?", "previs", "Act 1- the return- - Previs Review.mp4"),
        ("..Lights\tout..", "final", "Lights-out - Final Review.mp4"),
        ("", "final", "Film - Final Review.mp4"),
        ("CON", "final", "CON - Final Review.mp4"),
        ("a/b\\c", "final", "a-b-c - Final Review.mp4"),
    ],
)
def test_default_names_are_portable_suggestions(title, mode, expected):
    name = policy.default_name(title, mode)
    assert name == expected
    assert export.portable_name(name)


def test_default_names_fit_the_name_limit():
    name = policy.default_name("é" * 300, "final")
    assert name.endswith(" - Final Review.mp4")
    assert len(name.encode("utf-8")) <= 255 and export.portable_name(name)


def test_agent_destinations_stay_inside_the_output_folder(tmp_path):
    output = tmp_path / "Scenario"
    film = output / "Film"
    # Only the exact missing Film folder may be created, with its missing parents.
    with pytest.raises(export.LocalExportError, match="already exist inside"):
        policy.require_within(output / "Other" / "Review.mp4", output, create=film)
    assert not output.exists()
    accepted = policy.require_within(film / "Review.mp4", output, create=film)
    assert accepted == film / "Review.mp4" and film.is_dir()
    assert not (film / "Review.mp4").exists()
    (output / "Nested").mkdir()
    assert policy.require_within(output / "Nested" / "Take.mp4", output).name == "Take.mp4"
    assert policy.require_within(output / "Top.mp4", output).name == "Top.mp4"
    outside = tmp_path / "Elsewhere"
    outside.mkdir()
    (output / "escape").symlink_to(outside, target_is_directory=True)
    (tmp_path / "Scenario-sibling").mkdir()
    rejected = [
        outside / "Review.mp4",
        output / "escape" / "Review.mp4",
        output / ".." / "Elsewhere" / "Review.mp4",
        tmp_path / "Scenario-sibling" / "Review.mp4",
        "Film/Review.mp4",
        "",
        None,
        str(film) + "/line\nbreak.mp4",
    ]
    for value in rejected:
        with pytest.raises(export.LocalExportError):
            policy.require_within(value, output, create=film)
    with pytest.raises(export.LocalExportError, match="absolute"):
        policy.require_within(film / "Review.mp4", Path("relative"))
    # A linked Output Folder is the user's choice; its resolved contents are inside.
    linked = tmp_path / "Linked"
    linked.symlink_to(output, target_is_directory=True)
    assert policy.require_within(linked / "Film" / "Review.mp4", linked).name == "Review.mp4"
    assert list(film.iterdir()) == []


def test_agent_destination_folder_spelling_is_not_folded(tmp_path):
    output = tmp_path / "Scenario"
    output.mkdir()
    alias = tmp_path / "SCENARIO"
    # A case-insensitive volume names the same folder, which is refused too: the
    # agent policy never guesses that two spellings name one directory.
    if not alias.exists():
        alias.mkdir()
    with pytest.raises(export.LocalExportError, match="only inside"):
        policy.require_within(alias / "Review.mp4", output)


def test_an_uncreatable_film_folder_is_reported_without_a_path(monkeypatch, tmp_path):
    output = tmp_path / "Scenario"

    def refuse(*args, **kwargs):
        raise PermissionError(str(output))

    monkeypatch.setattr(Path, "mkdir", refuse)
    with pytest.raises(export.LocalExportError, match="Cannot create the Film folder") as caught:
        policy.require_within(output / "Film" / "Review.mp4", output, create=output / "Film")
    assert str(tmp_path) not in str(caught.value)
