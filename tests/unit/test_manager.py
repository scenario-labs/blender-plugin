# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prototype records remain readable without a service job engine."""

import json

from scenario.core.jobs.manager import JobManager
from scenario.core.jobs.records import JobRecord, JobRegistry


def test_record_roundtrip():
    rec = JobRecord.new(lane="image", kind="image", model_id="model_x", body={"prompt": "p"})
    rec.job_id = "job_1"
    again = JobRecord.from_dict(json.loads(json.dumps(rec.to_dict())))
    assert (
        again.local_id == rec.local_id and again.job_id == "job_1" and again.status == "submitting"
    )
    assert not again.is_terminal


def test_catalog_worker_lifetime_preserves_unscoped_records(tmp_path):
    registry = JobRegistry(tmp_path / "jobs.json")
    for remote_id in (None, "remote-job"):
        rec = JobRecord.new("image", "image", "fixture", {})
        rec.job_id = remote_id
        registry.add(rec)
    registry.save()
    original = registry.path.read_bytes()
    manager = JobManager(registry, None)
    manager.shutdown()
    manager.join(1)
    assert not manager.has_active()
    assert manager.drain() == manager.drain_catalog() == []
    assert registry.path.read_bytes() == original
    assert [rec.status for rec in registry.all()] == ["submitting", "submitting"]
