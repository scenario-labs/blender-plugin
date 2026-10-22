# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""A price revoked by a scene change is requested again once the scene settles."""

from scenario.core.jobs.origins import OriginRevisions
from scenario.core.jobs.quote_refresh import NOT_QUEUED, SCENE_CHANGED, SETTLE, Settle


def test_a_revoked_price_stays_revoked_until_a_new_one_is_captured():
    # The finding: any scene update revokes the revision a price was captured
    # with, for good. Only a new capture, so a new price, is current again.
    origins = OriginRevisions()
    priced = origins.capture("scene")
    origins.invalidate("scene")  # a selection, transform or frame change
    assert not origins.current(priced)
    assert origins.capture("scene") != priced
    assert not origins.current(priced)


def test_the_scene_settles_once_one_revision_lasts_the_delay():
    origins = OriginRevisions()
    assert Settle(None, now=0.0).delay == SETTLE  # the form's own debounce
    settle = Settle(origins.capture("scene"), now=10.0, delay=1.0)
    assert not settle.settled(origins.capture("scene"), 10.5)
    assert settle.settled(origins.capture("scene"), 11.0)
    assert settle.settled(origins.capture("scene"), 12.0)


def test_each_scene_change_restarts_the_wait():
    # A drag or playback revokes the revision on every update: no dry run until it stops.
    origins = OriginRevisions()
    settle = Settle(origins.capture("scene"), now=0.0, delay=1.0)
    now = 0.0
    for _ in range(20):
        now += 0.5
        origins.invalidate("scene")
        assert not settle.settled(origins.capture("scene"), now)
    assert not settle.settled(origins.capture("scene"), now + 0.5)
    assert settle.settled(origins.capture("scene"), now + 1.0)


def test_an_unknown_revision_waits_like_any_other():
    # Without a job session there is no revision to read: the delay alone applies.
    settle = Settle(None, now=5.0, delay=0.0)
    assert settle.settled(None, 5.0)
    assert not settle.settled("captured", 5.0)
    assert settle.settled("captured", 5.0)


def test_status_lines_fit_one_sidebar_line():
    for note in (SCENE_CHANGED, NOT_QUEUED):
        assert len(note) <= 36  # panels.SIDEBAR_CHARS
