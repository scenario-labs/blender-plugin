# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The local record of answered invitations: tolerant reads and atomic, merging updates."""

import json

import pytest

from scenario.core.telemetry import prompts


def saved(directory):
    return json.loads((directory / prompts.PROMPTS_FILE).read_text(encoding="utf-8"))


def test_nothing_is_answered_without_a_record(tmp_path):
    assert prompts.read(tmp_path) == {}
    assert prompts.read(tmp_path / "missing") == {}


@pytest.mark.parametrize(
    "content",
    [b"", b"{", b"[]", b'"answered"', b"\xff\xfe", b'{"usage_card": "yes"}', b'{"usage_card": 1}'],
)
def test_a_malformed_record_reads_as_nothing_answered(tmp_path, content):
    (tmp_path / prompts.PROMPTS_FILE).write_bytes(content)
    assert prompts.read(tmp_path) == {}


def test_unknown_entries_are_ignored(tmp_path):
    (tmp_path / prompts.PROMPTS_FILE).write_text(
        json.dumps({"usage_card": prompts.ANSWERED, "later": True}), encoding="utf-8"
    )
    assert prompts.read(tmp_path) == {"usage_card": prompts.ANSWERED}


def test_an_answer_is_saved_and_read_back(tmp_path):
    directory = tmp_path / "state"
    assert prompts.update(directory, usage_card=prompts.ANSWERED) == {
        "usage_card": prompts.ANSWERED
    }
    assert prompts.read(directory) == {"usage_card": prompts.ANSWERED}
    assert saved(directory) == {"usage_card": prompts.ANSWERED}
    assert [path.name for path in directory.iterdir()] == [prompts.PROMPTS_FILE]


def test_an_update_keeps_what_another_blender_saved(tmp_path):
    (tmp_path / prompts.PROMPTS_FILE).write_text(json.dumps({"generations": 3}), encoding="utf-8")
    prompts.update(tmp_path, usage_card=prompts.ANSWERED)
    assert saved(tmp_path) == {"generations": 3, "usage_card": prompts.ANSWERED}


@pytest.mark.parametrize("entries", [{"usage_card": "declined"}, {"unknown": prompts.ANSWERED}])
def test_an_invalid_entry_is_refused_before_anything_is_written(tmp_path, entries):
    with pytest.raises(ValueError):
        prompts.update(tmp_path, **entries)
    assert not (tmp_path / prompts.PROMPTS_FILE).exists()


def test_a_write_failure_raises(tmp_path):
    blocked = tmp_path / "blocked"
    blocked.write_text("a file where the directory should be", encoding="utf-8")
    with pytest.raises(OSError):
        prompts.update(blocked, usage_card=prompts.ANSWERED)


@pytest.mark.parametrize(
    "entries",
    [
        {"generations": True},
        {"generations": -1},
        {"generations": prompts.RATING_AFTER + 1},
        {"generations": 2.0},
        {"quiet_until": float("inf")},
        {"quiet_until": -1},
        {"quiet_until": "soon"},
        {"rating_prompt": "later"},
    ],
)
def test_malformed_counts_and_dates_are_ignored(tmp_path, entries):
    (tmp_path / prompts.PROMPTS_FILE).write_text(json.dumps(entries), encoding="utf-8")
    assert prompts.read(tmp_path) == {}
    with pytest.raises(ValueError):
        prompts.update(tmp_path, **entries)


def test_generations_are_counted_up_to_the_rating_threshold(tmp_path):
    for count in range(1, prompts.RATING_AFTER + 3):
        saved = prompts.count_generation(tmp_path)
        assert saved["generations"] == min(count, prompts.RATING_AFTER)
    assert prompts.read(tmp_path)["generations"] == prompts.RATING_AFTER


def test_the_rating_prompt_is_due_once_after_enough_generations(tmp_path):
    assert not prompts.rating_due({})
    assert not prompts.rating_due({"generations": prompts.RATING_AFTER - 1})
    assert prompts.rating_due({"generations": prompts.RATING_AFTER})
    answered = {"generations": prompts.RATING_AFTER, "rating_prompt": prompts.ANSWERED}
    assert not prompts.rating_due(answered)


def test_prompts_stay_quiet_until_the_recorded_time():
    assert not prompts.quiet({}, 1000.0)
    saved = {"quiet_until": 1000.0 + prompts.QUIET_PERIOD}
    assert prompts.quiet(saved, 1000.0)
    assert prompts.quiet(saved, 1000.0 + prompts.QUIET_PERIOD - 1)
    assert not prompts.quiet(saved, 1000.0 + prompts.QUIET_PERIOD)
    assert prompts.QUIET_PERIOD == 7 * 24 * 3600
