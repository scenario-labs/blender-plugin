# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""SDK catalog workers and read-only local prototype records.

Generation and recovery belong to the scoped JobSession coordinator.
Workers never touch bpy; the main thread drains their completion queues.
"""

import copy
import logging
import queue
import threading
import time
from dataclasses import dataclass

from ..api.errors import ScenarioError

log = logging.getLogger("scenario.jobs")


@dataclass
class EstimateResult:
    key: str
    cu_cost: float = None
    error: str = None
    catalog: object = None
    quote: object = None


class JobManager:
    def __init__(self, registry, paths):
        self.registry = registry
        self.paths = paths
        self.events = queue.Queue()
        self.catalog_events = queue.Queue()
        self._threads = []
        self._stop = threading.Event()

    # -- public API (main thread) -----------------------------------------
    def preview_cost(self, catalog, key, model_id, body):
        """Non-spending pricing uses its captured SDK context."""
        self._spawn(self._run_cost_preview, catalog, key, model_id, copy.deepcopy(body))

    def fetch_catalog(self, catalog, privacy="public", model_ids=()):
        self._spawn(self._run_catalog, catalog, privacy, tuple(model_ids))

    def fetch_history(self, catalog, key, token=None, *, append=False):
        self._spawn(self._run_history, catalog, key, token, append)

    def check_connection(self, catalog, key):
        return self._spawn(self._run_connection_check, catalog, key)

    def fetch_models(self, catalog, model_ids, *, mark_dirty=True):
        """Fetch detailed records for a few models without re-fetching the list."""
        self._spawn(self._run_models, catalog, tuple(model_ids), mark_dirty)

    def drain(self):
        out = []
        while True:
            try:
                out.append(self.events.get_nowait())
            except queue.Empty:
                return out

    def drain_catalog(self):
        """Catalog reads are also drained by the main-thread headless MCP calls."""
        out = []
        while True:
            try:
                out.append(self.catalog_events.get_nowait())
            except queue.Empty:
                return out

    def has_active(self):
        return any(t.is_alive() for t in self._threads)

    def join(self, timeout=None):
        deadline = None if timeout is None else time.time() + timeout
        for t in list(self._threads):
            remaining = None if deadline is None else max(0.0, deadline - time.time())
            t.join(remaining)
        self._threads = [t for t in self._threads if t.is_alive()]

    def shutdown(self):
        self._stop.set()

    # -- workers ------------------------------------------------------------
    def _spawn(self, target, *args):
        thread = threading.Thread(
            target=self._guard,
            args=(target,) + args,
            daemon=True,
            name=f"scenario-{target.__name__}",
        )
        self._threads.append(thread)
        thread.start()
        return thread

    def _guard(self, target, *args):
        try:
            target(*args)
        except Exception as err:  # never let a worker die silently
            log.exception("worker %s failed", target.__name__)
            self.events.put(("error", str(err)))

    def _run_cost_preview(self, catalog, key, model_id, body):
        result = EstimateResult(key=key, catalog=catalog)
        try:
            result.quote = catalog.estimate(model_id, body)
            result.cu_cost = result.quote.cost
        except ScenarioError as err:
            result.error = err.reason
        except Exception:
            result.error = "Could not estimate this model"
        self.events.put(("estimate", result))

    def _run_history(self, catalog, key, token, append):
        payload = {"catalog": catalog, "key": key, "cursor": token, "append": append}
        try:
            page = catalog.history_page(token)
            payload.update(jobs=page["jobs"], token=page.get("nextPaginationToken"))
        except ScenarioError as err:
            payload["error"] = err.reason
        except Exception:
            payload["error"] = "Could not read Scenario history"
        self.catalog_events.put(("history", payload))

    def _run_connection_check(self, catalog, key):
        payload = {"catalog": catalog, "key": key, "error": None}
        try:
            catalog.check_connection()
        except ScenarioError as err:
            payload["error"] = err.reason
        except Exception:
            payload["error"] = "Could not check the Scenario connection"
        self.catalog_events.put(("connection", payload))

    def _run_catalog(self, catalog, privacy, model_ids):
        try:
            records = catalog.fetch_list(privacy=privacy)
        except (ScenarioError, OSError) as err:
            self.catalog_events.put(
                ("catalog_failed", {"catalog": catalog, "error": str(getattr(err, "reason", err))})
            )
            return
        # Publish choices before warming schemas: one slow default must not hold
        # the catalog or an independently requested selected model hostage.
        self.catalog_events.put(
            (
                "catalog",
                {
                    "catalog": catalog,
                    "privacy": privacy,
                    "records": records,
                    "detailed": [],
                    "warmup": True,
                },
            )
        )
        detailed = []
        for model_id in model_ids:
            if self._stop.is_set():
                return
            try:
                record = catalog.get(model_id)
            except (ScenarioError, OSError) as err:
                log.warning("model %s: %s", model_id, err)
            else:
                detailed.append(record)
                self.catalog_events.put(
                    (
                        "models",
                        {
                            "catalog": catalog,
                            "detailed": [record],
                            "failed": {},
                            "mark_dirty": False,
                        },
                    )
                )
        # Rebuild derived lane choices with all available details as before;
        # neither the list nor earlier schemas wait for this final warmup event.
        self.catalog_events.put(
            (
                "catalog",
                {"catalog": catalog, "privacy": privacy, "records": records, "detailed": detailed},
            )
        )

    def _run_models(self, catalog, model_ids, mark_dirty=True):
        detailed, failed = [], {}
        for model_id in model_ids:
            try:
                detailed.append(catalog.get(model_id, refresh=True))
            except (ScenarioError, OSError) as err:
                failed[model_id] = str(getattr(err, "reason", err))
        self.catalog_events.put(
            (
                "models",
                {
                    "catalog": catalog,
                    "detailed": detailed,
                    "failed": failed,
                    "mark_dirty": mark_dirty,
                },
            )
        )
