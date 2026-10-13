# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Thread-safe origin revisions; Blender observes edits only on its main thread."""

import threading
import uuid
from contextlib import contextmanager

from .store import JobOrigin, _identity

# Marks a destination-only origin's revision. Ordinary revisions are bare hex.
_DESTINATION = "destination-"


def destination_only(origin):
    """Whether this origin binds only where a result goes, not the scene's content."""
    return isinstance(origin, JobOrigin) and origin.revision.startswith(_DESTINATION)


class OriginRevisions:
    """Session identities deliberately invalidate automatic application after restart.

    Persistent records remain recoverable, but a new process/file load cannot
    prove an old scene target is unchanged merely from its name or filepath.

    An ordinary origin binds inputs taken from the scene to its current
    revision; any scene update revokes it. A destination-only origin binds a
    payload that does not come from the scene, such as a file the user chose, to
    the scene it is for. Scene updates keep it; removing that scene, undo, redo,
    file loading or deactivation (``reset``) revoke it.
    """

    def __init__(self):
        self._lock = threading.Lock()
        self._file_id = uuid.uuid4().hex
        self._revisions = {}
        self._destinations = {}

    def capture(self, scene_id, target_id=None):
        _identity(scene_id)
        if target_id is not None:
            _identity(target_id)
        with self._lock:
            revision = self._revisions.setdefault(scene_id, uuid.uuid4().hex)
            return JobOrigin(self._file_id, scene_id, revision, target_id)

    def capture_destination(self, scene_id):
        """Bind to a scene, not its content; never use it to price or apply scene inputs."""
        _identity(scene_id)
        with self._lock:
            token = self._destinations.setdefault(scene_id, uuid.uuid4().hex)
            return JobOrigin(self._file_id, scene_id, _DESTINATION + token)

    @contextmanager
    def guard(self, origin):
        """Serialize invalidation against the entire durable submission claim."""
        with self._lock:
            yield isinstance(origin, JobOrigin) and self._current(origin)

    def _current(self, origin):
        if destination_only(origin):
            # The token, not the file identity, carries a destination's lifetime:
            # a render-thread reset changes the file identity but keeps destinations.
            token = self._destinations.get(origin.scene_id)
            return (
                token is not None
                and origin.target_id is None
                and origin.revision == _DESTINATION + token
            )
        revision = self._revisions.get(origin.scene_id)
        return origin.file_id == self._file_id and revision == origin.revision

    def current(self, origin):
        with self.guard(origin) as current:
            return current

    def invalidate(self, scene_id):
        """The scene's content may have changed; its destinations remain."""
        with self._lock:
            self._revisions.pop(scene_id, None)

    def remove(self, scene_id):
        """The scene is gone: revoke its revision and its destination."""
        with self._lock:
            self._revisions.pop(scene_id, None)
            self._destinations.pop(scene_id, None)

    def reset(self, *, keep_destinations=False):
        """Revoke every revision; destinations too unless the scenes are known to remain.

        A render thread cannot tell which scene changed, so it revokes every
        revision, but it never removes or replaces a scene, so it keeps destinations.
        """
        with self._lock:
            self._file_id = uuid.uuid4().hex
            self._revisions.clear()
            if not keep_destinations:
                self._destinations.clear()
