# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit per-scope lane defaults for trained and private models (#97).

One owner serves the selected credential scope and optional project override of
one job store. It saves or clears a default only when a caller passes the exact
choice and the revision it last observed; reading never writes, never falls back
to another lane, project or credential scope and never derives a default from a
model list or discovery result. A saved default is not spending authority: the
caller still rechecks routes against fresh schemas and obtains a new exact quote.
No bpy, network or SDK access happens here.
"""

import math
import threading
import uuid

from .store import (
    MAX_TRAINED_PICKS,
    JobStore,
    StoreConflict,
    TrainedDefaultState,
    TrainedModelDefault,
    TrainedModelPick,
)

_DEFAULT_FIELDS = frozenset({"route", "base_model_id", "picks"})
_PICK_FIELDS = frozenset({"model_id", "scale"})


class DefaultsRetired(StoreConflict):
    """The selected credentials or project changed after this owner was opened."""


class ModelDefaults:
    """Lane defaults of one selected scope, retired when that selection changes.

    `context_id` is an in-memory token, never persisted: callers that showed a
    lane's state pass it back with their write so a choice made under earlier
    credentials or project cannot land in the current scope. After `retire()`
    returns, no read or write runs through this owner.
    """

    def __init__(self, store):
        if not isinstance(store, JobStore):
            raise ValueError("Lane defaults require the selected credential-bound job store")
        self._store = store
        self._lock = threading.Lock()
        self._active = True
        self.context_id = uuid.uuid4().hex

    @property
    def scope(self):
        return self._store.scope

    @property
    def active(self):
        return self._active

    def retire(self):
        """Wait for any running call, then refuse every later read and write."""
        with self._lock:
            self._active = False

    def _call(self, operation, *args, **kwargs):
        with self._lock:
            if not self._active:
                raise DefaultsRetired(
                    "The selected credentials or project changed; review the default again"
                )
            return operation(*args, **kwargs)

    def lane(self, lane):
        """Return one lane's saved state; revision 0 and no default mean never saved."""
        return self._call(self._store.trained_default, lane)

    def saved(self):
        """Return the lanes that currently hold a default, ordered by lane."""
        return self._call(self._store.trained_defaults)

    def save(self, default, *, expected_revision):
        """Save an explicit choice over the observed revision; 0 creates the first one."""
        if not isinstance(default, TrainedModelDefault):
            raise ValueError("Choose an explicit trained-model default to save")
        return self._call(
            self._store.set_trained_default, default, expected_revision=expected_revision
        )

    def clear(self, lane, *, expected_revision):
        """Clear a lane's default; the revision still advances so stale writers conflict."""
        return self._call(
            self._store.clear_trained_default, lane, expected_revision=expected_revision
        )


def _scale(value):
    if value is None:
        return None
    if isinstance(value, bool) or not isinstance(value, int | float):
        raise ValueError("Use a number or null for each strength")
    try:
        scale = float(value)
    except OverflowError:
        raise ValueError("Use a finite strength") from None
    if not math.isfinite(scale):
        raise ValueError("Use a finite strength")
    return scale


def parse_default(lane, value):
    """Build one explicit default from JSON-shaped input shared by UI and MCP callers.

    `value` holds exactly `route`, `base_model_id` and `picks`; each pick holds a
    `model_id` and an optional numeric `scale` (null or absent means no strength).
    Unknown fields, booleans, strings as numbers and non-finite strengths are
    refused rather than coerced, and route rules are checked by the stored type.
    """
    if not isinstance(value, dict) or set(value) != _DEFAULT_FIELDS:
        raise ValueError("Give the default as route, base_model_id and picks")
    picks = value["picks"]
    if not isinstance(picks, list | tuple) or len(picks) > MAX_TRAINED_PICKS:
        raise ValueError(f"Give at most {MAX_TRAINED_PICKS} trained models as a list")
    chosen = []
    for pick in picks:
        if not isinstance(pick, dict) or not {"model_id"} <= set(pick) <= _PICK_FIELDS:
            raise ValueError("Give each trained model as model_id and an optional scale")
        chosen.append(TrainedModelPick(pick["model_id"], _scale(pick.get("scale"))))
    return TrainedModelDefault(lane, value["route"], value["base_model_id"], tuple(chosen))


def describe(state):
    """Return a lane state as plain JSON values, without scope, schema, quote or URL."""
    if not isinstance(state, TrainedDefaultState):
        raise ValueError("A saved lane state is required")
    default = state.default
    return {
        "lane": state.lane,
        "revision": state.revision,
        "default": None
        if default is None
        else {
            "route": default.route,
            "base_model_id": default.base_model_id,
            "picks": [{"model_id": pick.model_id, "scale": pick.scale} for pick in default.picks],
        },
    }
