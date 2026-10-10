# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Catalog workers for trained models: the private list and lazy base descriptions (#97)."""

from scenario.core.api import catalog
from scenario.core.api.errors import ScenarioError
from scenario.core.jobs.manager import JobManager


def record(model_id, **fields):
    return catalog.ModelRecord.from_api({"id": model_id, "name": model_id, **fields})


class Catalog:
    """A connection whose list and description reads are scripted per call."""

    def __init__(self, private=(), public=(), details=None, list_error=None):
        self.private, self.public = list(private), list(public)
        self.details = dict(details or {})
        self.list_error = list_error
        self.calls = []

    def fetch_list(self, privacy="public"):
        self.calls.append(("list", privacy))
        if self.list_error is not None:
            raise self.list_error
        return list(self.private if privacy == "private" else self.public)

    def trained_models(self, refresh=False):
        self.calls.append(("trained", refresh))
        return catalog.trained_models(self.private, self.public)

    def get(self, model_id, refresh=False):
        self.calls.append(("get", model_id))
        value = self.details[model_id]
        if isinstance(value, Exception):
            raise value
        return value


def run(target, *args):
    manager = JobManager(None, None)
    target(manager, *args)
    return manager.drain_catalog()


def test_the_private_list_is_read_again_and_paired_with_public_loras():
    private = [record("model_private-lora", type="flux.1-lora", privacy="private")]
    public = [record("model_public-lora", type="flux.1-lora"), record("model_base")]
    connection = Catalog(private, public)
    ((name, payload),) = run(JobManager._run_trained, connection)
    assert name == "trained_catalog"
    assert payload["catalog"] is connection
    assert [(kind, item.id) for kind, item in payload["pairs"]] == [
        ("lora", "model_private-lora"),
        ("lora", "model_public-lora"),
    ]
    assert payload["private"] == ["model_private-lora"]
    assert connection.calls == [("list", "private"), ("trained", False)]


def test_a_private_list_failure_is_reported_without_blocking_anything_else():
    connection = Catalog(list_error=ScenarioError(0, "Online access is disabled"))
    assert run(JobManager._run_trained, connection) == [
        ("trained_catalog_failed", {"catalog": connection, "error": "Online access is disabled"})
    ]
    local = Catalog(list_error=OSError("disk"))
    assert run(JobManager._run_trained, local) == [
        ("trained_catalog_failed", {"catalog": local, "error": "disk"})
    ]


def test_base_descriptions_arrive_in_batches_with_progress():
    ids = [f"model_{index}" for index in range(23)]
    details = {model_id: record(model_id) for model_id in ids}
    connection = Catalog(details=details)
    events = run(JobManager._run_base_schemas, connection, "image", ids)
    assert [name for name, _payload in events] == ["trained_bases"] * 3
    assert [
        (len(p["detailed"]), p["checked"], p["total"], p["done"], p["error"]) for _n, p in events
    ] == [(10, 10, 23, False, ""), (10, 20, 23, False, ""), (3, 23, 23, True, "")]
    assert {p["lane"] for _n, p in events} == {"image"}
    assert [call[1] for call in connection.calls] == ids


def test_one_unreadable_base_is_skipped_but_repeated_failures_stop_the_scan():
    details = {
        "model_a": record("model_a"),
        "model_missing": ScenarioError(404, "Not available"),
        "model_b": record("model_b"),
        "model_c": ScenarioError(0, "Too many requests (HTTP 429). Try again shortly."),
        "model_d": RuntimeError("unexpected"),
        "model_e": ScenarioError(0, "Too many requests (HTTP 429). Try again shortly."),
        "model_f": record("model_f"),
    }
    connection = Catalog(details=details)
    events = run(JobManager._run_base_schemas, connection, "render_image", list(details))
    ((_name, payload),) = events
    assert [item.id for item in payload["detailed"]] == ["model_a", "model_b"]
    assert (payload["checked"], payload["failed"], payload["done"]) == (6, 4, True)
    assert payload["error"] == "Too many requests (HTTP 429). Try again shortly."
    assert ("get", "model_f") not in connection.calls  # nothing is read after giving up


def test_an_empty_scan_still_finishes_and_a_stopped_manager_reads_nothing():
    ((name, payload),) = run(JobManager._run_base_schemas, Catalog(), "image", [])
    assert name == "trained_bases"
    assert (payload["detailed"], payload["checked"], payload["total"], payload["done"]) == (
        [],
        0,
        0,
        True,
    )
    manager = JobManager(None, None)
    manager.shutdown()
    connection = Catalog(details={"model_a": record("model_a")})
    manager._run_base_schemas(connection, "image", ["model_a"])
    assert manager.drain_catalog() == [] and connection.calls == []
