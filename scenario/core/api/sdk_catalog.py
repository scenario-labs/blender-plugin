# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Credential-bound catalog reads through the shared SDK adapter, without bpy."""

import copy
import threading
from concurrent.futures import Future
from contextlib import contextmanager

from .catalog import ModelRecord
from .errors import ScenarioError
from .sdk_adapter import AdapterError, SDKAdapter


class SDKCatalog:
    """One application catalog context, independent of the view that requested it.

    Reads share this connection's HTTP pool until retirement. Retirement disables
    subsequent requests and closes the pool only after the final reader exits.
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
        self._adapter = None
        self._lists = {}
        self._list_reads = {}
        self._records = {}
        self._model_reads = {}
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
            self._close_idle_adapter()
            if wait:
                self._condition.wait_for(lambda: not self._readers)

    def _close_idle_adapter(self):
        """Called under the condition; no network request can own this pool now."""
        if not self._active and not self._readers and self._adapter is not None:
            adapter, self._adapter = self._adapter, None
            adapter.close()

    def _check_active(self):
        if not self._active:
            raise ScenarioError(0, "The selected catalog connection changed")

    @contextmanager
    def _read(self):
        try:
            with self._condition:
                self._check_active()
                if self._adapter is None:
                    self._adapter = self._adapter_factory(
                        self._credentials, online=self._permission.is_set
                    )
                adapter = self._adapter
                self._readers += 1
            try:
                yield adapter
            finally:
                with self._condition:
                    self._readers -= 1
                    try:
                        self._close_idle_adapter()
                    finally:
                        self._condition.notify_all()
        except AdapterError as error:
            raise ScenarioError(0, str(error)) from None
        except ValueError:
            raise ScenarioError(0, "The catalog request is invalid") from None

    def fetch_list(self, privacy="public"):
        """Refresh once for overlapping readers of this connection/privacy scope."""
        with self._condition:
            self._check_active()
            if privacy not in ("public", "private"):
                raise ScenarioError(0, "The catalog request is invalid")
            pending = self._list_reads.get(privacy)
            owner = pending is None
            if owner:
                pending = self._list_reads[privacy] = Future()
        if not owner:
            rows = pending.result()
            with self._condition:
                self._check_active()
            return [ModelRecord.from_api(copy.deepcopy(row)) for row in rows]
        try:
            rows = self._fetch_list(privacy)
            records = [ModelRecord.from_api(row) for row in rows]
            pending.set_result(copy.deepcopy(rows))
            return records
        except BaseException as error:
            pending.set_exception(error)
            raise
        finally:
            with self._condition:
                del self._list_reads[privacy]

    def _fetch_list(self, privacy):
        with self._read() as adapter:
            rows = adapter.models(privacy=privacy)
            with self._condition:
                self._check_active()
                self._lists[privacy] = copy.deepcopy(rows)
        return rows

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
        with self._condition:
            self._check_active()
            if not refresh and model_id in self._records:
                return ModelRecord.from_api(copy.deepcopy(self._records[model_id]))
            pending = self._model_reads.get(model_id)
            owner = pending is None
            if owner:
                pending = self._model_reads[model_id] = Future()
        if not owner:
            row = pending.result()
            with self._condition:
                self._check_active()
            return ModelRecord.from_api(copy.deepcopy(row))
        try:
            row = self._fetch_model(model_id)
            record = ModelRecord.from_api(row)
            pending.set_result(copy.deepcopy(row))
            return record
        except BaseException as error:
            pending.set_exception(error)
            raise
        finally:
            with self._condition:
                del self._model_reads[model_id]

    def _fetch_model(self, model_id):
        with self._read() as adapter:
            row = adapter.model(model_id)
            if row.get("id") != model_id:
                raise ScenarioError(0, "Scenario returned a different model identity")
            with self._condition:
                self._check_active()
                self._records[model_id] = copy.deepcopy(row)
        return row
