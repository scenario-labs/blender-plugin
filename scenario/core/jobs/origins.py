# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thread-safe origin revisions; Blender observes edits only on its main thread."""

import threading
import uuid

from .store import JobOrigin, _identity


class OriginRevisions:
    """Session identities deliberately invalidate automatic application after restart.

    Persistent records remain recoverable, but a new process/file load cannot
    prove an old scene target is unchanged merely from its name or filepath.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._file_id = uuid.uuid4().hex
        self._revisions = {}

    def capture(self, scene_id, target_id=None):
        _identity(scene_id)
        if target_id is not None:
            _identity(target_id)
        with self._lock:
            revision = self._revisions.setdefault(scene_id, uuid.uuid4().hex)
            return JobOrigin(self._file_id, scene_id, revision, target_id)

    def current(self, origin):
        with self._lock:
            return (
                isinstance(origin, JobOrigin)
                and origin.file_id == self._file_id
                and self._revisions.get(origin.scene_id) == origin.revision
            )

    def invalidate(self, scene_id):
        with self._lock:
            self._revisions.pop(scene_id, None)

    def reset(self):
        with self._lock:
            self._file_id = uuid.uuid4().hex
            self._revisions.clear()
