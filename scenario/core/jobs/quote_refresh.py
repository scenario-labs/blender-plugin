# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""When a form whose price the scene revoked is priced again. No bpy.

A price is bound to the scene revision its inputs were read from (see
`origins.OriginRevisions`): a selection, transform, frame change, Undo or Redo
revokes it for good, and the coordinator then refuses to prepare it. Its owner
prices the unchanged form again instead of leaving a price that Generate
refuses, but only once the scene has kept one revision for SETTLE seconds, so a
drag or playback never asks for a dry run on every update. The new price is
approved like any other; nothing here sends, submits or spends.
"""

SETTLE = 0.7  # seconds one scene revision must last; the form's own debounce
# Status lines while a form is priced again; each fits one sidebar line (36 characters).
SCENE_CHANGED = "Scene changed; updating the price"
NOT_QUEUED = "Nothing sent; updating the price"
EXPIRED = "Price expired; updating the price"


class Settle:
    """Wait until one scene revision has lasted `delay` seconds."""

    def __init__(self, revision, now, delay=SETTLE):
        self.revision = revision
        self.since = now
        self.delay = delay

    def settled(self, revision, now):
        """Whether `revision` has been current for the delay; another one restarts the wait."""
        if revision != self.revision:
            self.revision, self.since = revision, now
            return False
        return now - self.since >= self.delay
