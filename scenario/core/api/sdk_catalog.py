# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-bound catalog reads through the shared SDK adapter, without bpy."""

import copy
import threading
from contextlib import contextmanager

from .catalog import ModelRecord
from .errors import ScenarioError
from .sdk_adapter import AdapterError, SDKAdapter


class SDKCatalog:
    """One application catalog context, independent of the view that requested it.

    Reads own their HTTP pools until completion. Retirement disables subsequent
    requests and discards cached results without closing a pool under a worker.
    Cache entries live only in this connection: an authoritative account identity
    is required before persistent shared account/project caching can be enabled.
    """

    def __init__(self, credentials, *, online, adapter_factory=None):
        credentials.authorization()
        self._credentials = credentials
        self._adapter_factory = adapter_factory or SDKAdapter
        self._permission = threading.Event()
        self._condition = threading.Condition()
        self._active = True
        self._readers = 0
        self._lists = {}
        self._records = {}
        self.update_online(online)

    def update_online(self, enabled):
        """Mirror Blender permission on its main thread; workers read only Event."""
        with self._condition:
            if enabled and self._active:
                self._permission.set()
            else:
                self._permission.clear()

    @property
    def closed(self):
        with self._condition:
            return not self._active and not self._readers

    def close(self, *, wait=False):
        with self._condition:
            self._active = False
            self._permission.clear()
            self._lists.clear()
            self._records.clear()
            if wait:
                self._condition.wait_for(lambda: not self._readers)

    def _check_active(self):
        if not self._active:
            raise ScenarioError(0, "The selected catalog connection changed")

    @contextmanager
    def _read(self):
        with self._condition:
            self._check_active()
            self._readers += 1
        try:
            with self._adapter_factory(
                self._credentials, online=self._permission.is_set
            ) as adapter:
                yield adapter
        except AdapterError as error:
            raise ScenarioError(0, str(error)) from None
        except ValueError:
            raise ScenarioError(0, "The catalog request is invalid") from None
        finally:
            with self._condition:
                self._readers -= 1
                self._condition.notify_all()

    def fetch_list(self, privacy="public"):
        with self._read() as adapter:
            rows = adapter.models(privacy=privacy)
            with self._condition:
                self._check_active()
                self._lists[privacy] = copy.deepcopy(rows)
        return [ModelRecord.from_api(row) for row in rows]

    def load_list_cached(self, privacy="public"):
        with self._condition:
            self._check_active()
            rows = copy.deepcopy(self._lists.get(privacy))
        return None if rows is None else [ModelRecord.from_api(row) for row in rows]

    def load_cached(self, model_id):
        with self._condition:
            self._check_active()
            row = copy.deepcopy(self._records.get(model_id))
        return None if row is None else ModelRecord.from_api(row)

    def get(self, model_id, refresh=False):
        if not refresh:
            cached = self.load_cached(model_id)
            if cached is not None:
                return cached
        with self._read() as adapter:
            row = adapter.model(model_id)
            if row.get("id") != model_id:
                raise ScenarioError(0, "Scenario returned a different model identity")
            with self._condition:
                self._check_active()
                self._records[model_id] = copy.deepcopy(row)
        return ModelRecord.from_api(row)
