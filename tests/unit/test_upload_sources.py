# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Upload snapshots compare like timestamps without weakening change detection."""

from types import SimpleNamespace

import pytest

from scenario.core.jobs import upload_sources
from scenario.core.jobs.store import JobOrigin, JobScope
from scenario.core.jobs.transfers import TransferError

DATA = b"abcde"


def source_operation(tmp_path, phase):
    root = tmp_path / "staged"
    root.mkdir()
    source = tmp_path / "reference.png"
    source.write_bytes(DATA)
    sources = upload_sources.UploadSources(root, max_bytes=30, part_bytes=3)
    scope = JobScope("https://service.example.invalid/v1", "account", "project")
    origin = JobOrigin("file", "scene", "revision", "object")

    def stage():
        return sources.stage(
            source,
            request_id="request",
            scope=scope,
            origin=origin,
            kind="image",
            content_type="image/png",
        )

    if phase == "stage":
        return source, stage, root
    intent = stage()
    path = sources._directory(scope, intent.request_id) / "source.bin"
    operation = (
        (lambda: sources.verify(intent)) if phase == "verify" else (lambda: sources.part(intent, 1))
    )
    return path, operation, root


def mock_stat_apis(
    monkeypatch, path, *, change=None, windows=True, descriptor_birthtime=True, path_birthtime=True
):
    original = path.stat()
    attributes = ("st_dev", "st_ino", "st_size", "st_mtime_ns", "st_ctime_ns", "st_mode")

    def snapshot(**overrides):
        values = {name: getattr(original, name) for name in attributes}
        values.update(st_ctime_ns=200, st_birthtime_ns=100)
        return SimpleNamespace(**(values | overrides))

    before, after, current = snapshot(), snapshot(), snapshot(st_ctime_ns=100)
    if not descriptor_birthtime:
        del before.st_birthtime_ns
        del after.st_birthtime_ns
    if not path_birthtime:
        del current.st_birthtime_ns
    if change == "descriptor-ctime":
        after.st_ctime_ns += 1
    elif change is not None:
        setattr(current, change, getattr(current, change) + 1)
    local_os = SimpleNamespace(**vars(upload_sources.os))
    local_os.name = "nt" if windows else "posix"
    snapshots = iter((before, after))
    local_os.fstat = lambda descriptor: next(snapshots)
    monkeypatch.setattr(upload_sources, "os", local_os)
    original_stat = type(path).stat
    monkeypatch.setattr(
        type(path),
        "stat",
        lambda self, **kwargs: current if self == path else original_stat(self, **kwargs),
    )


@pytest.mark.parametrize("phase", ["stage", "verify", "part"])
@pytest.mark.parametrize(
    "change",
    [None, "descriptor-ctime", "st_dev", "st_ino", "st_size", "st_mtime_ns", "st_birthtime_ns"],
)
def test_windows_upload_identity_preserves_change_detection(tmp_path, monkeypatch, phase, change):
    path, operation, root = source_operation(tmp_path, phase)
    mock_stat_apis(monkeypatch, path, change=change)
    if change is None:
        result = operation()
        if phase == "stage":
            assert result.file_size == len(DATA)
            assert result.part_bytes(1) == 3
        elif phase == "verify":
            assert result is None
        else:
            assert result == DATA[:3]
    else:
        with pytest.raises(TransferError):
            operation()
        if phase == "stage":
            assert list(root.iterdir()) == []
    assert path.read_bytes() == DATA


@pytest.mark.parametrize("phase", ["stage", "verify", "part"])
@pytest.mark.parametrize(
    "windows,descriptor_birthtime,path_birthtime",
    [(False, True, True), (True, False, False), (True, True, False), (True, False, True)],
)
def test_other_stat_apis_still_compare_ctime(
    tmp_path, monkeypatch, phase, windows, descriptor_birthtime, path_birthtime
):
    path, operation, root = source_operation(tmp_path, phase)
    mock_stat_apis(
        monkeypatch,
        path,
        windows=windows,
        descriptor_birthtime=descriptor_birthtime,
        path_birthtime=path_birthtime,
    )
    with pytest.raises(TransferError):
        operation()
    if phase == "stage":
        assert list(root.iterdir()) == []
    assert path.read_bytes() == DATA
