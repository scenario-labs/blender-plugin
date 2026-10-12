# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned Film case-study bundles: staging, child checks, private scans, archive and publish."""

import hashlib
import json
import sys
import threading
import zipfile
from dataclasses import replace
from pathlib import Path

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import local_case_study as study
from scenario.core.jobs import local_export as export
from scenario.core.jobs import local_render
from scenario.core.jobs.coordinator import JobCoordinator, LocalExportResult
from scenario.core.jobs.store import JobOrigin, JobScope, JobStore
from scenario.core.jobs.workers import ExportTask, LocalExportWorker
from scenario.core.scene import film_case_study as documents

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project")
ORIGIN = JobOrigin("file", "scene", "revision", None)
SOURCE = JobOrigin("file", "review", "revision", None)
MARKER = "private-asset-identifier-0001"


def texts(manifest=None, ledger=None):
    return (
        (documents.RECIPE_FILE, documents.encode({"title": "Cut"})),
        (documents.LEDGER_FILE, documents.encode(ledger or {"tasks": []})),
        (documents.MANIFEST_FILE, documents.encode(manifest or {"title": "Cut"})),
        (documents.GUIDE_FILE, "# Open Cut\n"),
    )


@pytest.fixture
def media(tmp_path):
    folder = tmp_path / "media"
    folder.mkdir()
    movie, image = folder / "0.mp4", folder / "texture.PNG"
    movie.write_bytes(b"synthetic movie bytes")
    image.write_bytes(b"synthetic texture bytes")
    return movie, image


def make_spec(tmp_path, media, **changes):
    directory = tmp_path / (study.STAGING_PREFIX + "fixture")
    root = directory / study.BUNDLE
    root.mkdir(parents=True)
    (root / study.SNAPSHOT).write_bytes(b"synthetic snapshot")
    worker = tmp_path / "film_case_study_worker.py"
    worker.write_text("# fixture", encoding="utf-8")
    items = tuple(
        study.BundleMedia(export.media_stamp(path), study.media_name(index, kind, path), kind)
        for index, (path, kind) in enumerate(zip(media, ("movie", "image"), strict=True), 1)
    )
    values = dict(
        directory=directory,
        binary=Path(sys.executable).resolve(),
        worker=worker,
        snapshot_sha256=local_render.digest(root / study.SNAPSHOT),
        top="Cut Case Study",
        blend="Cut Case Study.blend",
        scenes=("Cut / Final Review", "Film Timeline / Cut", "Film / s01 / Shot"),
        media=items,
        documents=texts(),
        markers=(MARKER,),
    )
    values.update(changes)
    return study.CaseStudySpec(**values)


@pytest.fixture
def spec(tmp_path, media):
    return make_spec(tmp_path, media)


class Child:
    """Fake owned processes: the bundle child writes a library, verification a report."""

    def __init__(self, monkeypatch, spec, *, blend=b"BLENDER library", verified=None, written=None):
        self.spec, self.calls, self.blend = spec, [], blend
        self.verified, self.written = verified, written
        self.copies = None
        monkeypatch.setattr(study, "_child", self)

    def default(self):
        return {
            "scenes": list(self.spec.scenes),
            "libraries": 0,
            "paths": ["//Media/" + item.name for item in self.spec.media],
            "packed_paths": ["//Packed/003 image.png"],
            "properties": [],
            "missing": [],
        }

    def __call__(self, command, *, log, env, timeout, cancel):
        self.calls.append((command, env, timeout))
        log.write_text("fixture")
        parameters = json.loads(Path(command[-1]).read_text(encoding="utf-8"))
        if parameters["mode"] == "bundle":
            media = self.spec.root / documents.MEDIA_FOLDER
            self.copies = {path.name: path.read_bytes() for path in media.iterdir()}
            Path(parameters["output"]).write_bytes(self.blend)
            Path(parameters["report"]).write_text(
                json.dumps(
                    {
                        "written": self.written or list(self.spec.scenes),
                        "counts": {"recreated_sound_strips": 2, "repacked_images": 1},
                    }
                )
            )
        else:
            report = self.default()
            report.update(self.verified or {})
            Path(parameters["report"]).write_text(json.dumps(report))


def test_build_copies_media_checks_children_and_archives_verified_files(monkeypatch, spec, media):
    monkeypatch.setenv("SCENARIO_API_KEY", "synthetic-key")
    child = Child(monkeypatch, spec)
    events = []
    staged = study.build(spec, progress=lambda *event: events.append(event))
    assert isinstance(staged, study.StagedBundle) and isinstance(staged, export.StagedFile)
    assert staged.sha256 == local_render.digest(staged.path, maximum=study.MAX_ARCHIVE_BYTES)
    assert staged.blend_sha256 == hashlib.sha256(b"BLENDER library").hexdigest()
    assert child.copies == {
        "001 movie.mp4": media[0].read_bytes(),
        "002 image.png": media[1].read_bytes(),
    }
    (bundle, _, timeout), (verify, env, _) = child.calls
    for flag in ("--quiet", "--offline-mode", "--factory-startup", "--disable-autoexec"):
        assert flag in bundle and flag in verify
    assert str(spec.root / study.SNAPSHOT) in bundle
    assert str(spec.root / spec.blend) in verify
    assert timeout == spec.child_timeout == 600 + 2 * 2 + 5 * 3
    assert "SCENARIO_API_KEY" not in env
    started = json.loads((spec.directory / "started.json").read_text())
    assert started["media"] == [
        {"path": str(item.stamp.path), "name": item.name, "kind": item.kind} for item in spec.media
    ]
    assert {event[0] for event in events} == {"media", "bundle", "verify", "archive", "check"}
    with zipfile.ZipFile(staged.path) as archive:
        names = archive.namelist()
        assert names == [
            "Cut Case Study/Cut Case Study.blend",
            "Cut Case Study/Film Recipe.json",
            "Cut Case Study/Production Ledger.json",
            "Cut Case Study/Case Study Manifest.json",
            "Cut Case Study/Open The Case Study.md",
            "Cut Case Study/Media/001 movie.mp4",
            "Cut Case Study/Media/002 image.png",
        ]
        info = {item.filename: item.compress_type for item in archive.infolist()}
        assert info["Cut Case Study/Media/001 movie.mp4"] == zipfile.ZIP_STORED
        assert info["Cut Case Study/Cut Case Study.blend"] == zipfile.ZIP_DEFLATED
        manifest = json.loads(archive.read("Cut Case Study/Case Study Manifest.json"))
        assert archive.read("Cut Case Study/Media/001 movie.mp4") == media[0].read_bytes()
    assert manifest["blend_file"] == {
        "file": "Cut Case Study.blend",
        "size": len(b"BLENDER library"),
        "sha256": staged.blend_sha256,
    }
    assert [item["file"] for item in manifest["media"]] == [
        "Media/001 movie.mp4",
        "Media/002 image.png",
    ]
    assert manifest["media"][0]["sha256"] == hashlib.sha256(media[0].read_bytes()).hexdigest()
    assert manifest["media_storage"]["recreated_sound_strips"] == 2
    assert [receipt.name for receipt in staged.media] == ["001 movie.mp4", "002 image.png"]
    # The verified archive holds the copies, so staging drops its originals.
    assert not (spec.root / documents.MEDIA_FOLDER).exists()


def test_reused_or_tampered_snapshots_never_start(monkeypatch, tmp_path, spec, media):
    child = Child(monkeypatch, spec)
    study.build(spec)
    with pytest.raises(export.LocalExportError, match="already used"):
        study.build(spec)
    second = tmp_path / "second"
    second.mkdir()
    other = make_spec(second, media)
    (other.root / study.SNAPSHOT).write_bytes(b"changed snapshot")
    with pytest.raises(export.LocalExportError, match="snapshot changed"):
        study.build(other)
    (other.root / study.SNAPSHOT).write_bytes(b"synthetic snapshot")
    other.worker.unlink()
    with pytest.raises(export.LocalExportError, match="worker is unavailable"):
        study.build(other)
    assert len(child.calls) == 2


def test_media_changed_after_the_snapshot_is_refused(monkeypatch, spec, media):
    child = Child(monkeypatch, spec)
    media[1].write_bytes(b"replaced texture with another length")
    with pytest.raises(export.LocalExportError, match="changed") as caught:
        study.build(spec)
    assert str(media[1].parent) not in str(caught.value)
    assert not child.calls


@pytest.mark.parametrize(
    "verified",
    [
        {"scenes": ["Cut / Final Review"]},
        {"libraries": 1},
        {"properties": ["Object:scenario_asset"]},
        {"missing": ["//Media/001 movie.mp4"]},
        {"paths": ["//Media/001 movie.mp4", "/private/source/texture.png"]},
        {"paths": ["//Media/001 movie.mp4"]},
        {"packed_paths": ["/private/packed.png"]},
        {"paths": "not a list"},
    ],
)
def test_verification_must_see_only_bundle_media_and_no_private_properties(
    monkeypatch, spec, verified
):
    Child(monkeypatch, spec, verified=verified)
    with pytest.raises(export.LocalExportError, match="outside the bundle"):
        study.build(spec)
    assert not (spec.directory / "output").exists()


def test_the_bundle_child_must_write_exactly_the_approved_scenes(monkeypatch, spec):
    Child(monkeypatch, spec, written=["Cut / Final Review", "Elsewhere"])
    with pytest.raises(export.LocalExportError, match="approved scenes"):
        study.build(spec)


def test_private_markers_in_the_library_refuse_saving_even_across_chunks(monkeypatch, spec):
    padding = b"x" * (1024 * 1024 - 5)
    Child(monkeypatch, spec, blend=padding + MARKER.encode() + b"tail")
    with pytest.raises(export.LocalExportError, match="private Scenario identifier"):
        study.build(spec)
    assert not (spec.directory / "output").exists()


def test_private_markers_in_documents_refuse_saving(monkeypatch, tmp_path, media):
    spec = make_spec(tmp_path, media, documents=texts(ledger={"note": MARKER.upper()}))
    Child(monkeypatch, spec)
    with pytest.raises(export.LocalExportError, match="private Scenario identifier"):
        study.build(spec)


@pytest.mark.parametrize("stage", ["media", "bundle", "archive", "check"])
def test_cancellation_stops_each_stage_and_keeps_staging(monkeypatch, spec, stage):
    Child(monkeypatch, spec)
    cancel = threading.Event()

    def progress(name, done, total):
        if name == stage:
            cancel.set()

    with pytest.raises(local_render.RenderCancelled):
        study.build(spec, cancel=cancel, progress=progress)
    # Staging stays for an explicit discard; nothing was published.
    assert (spec.directory / "started.json").exists()


def test_staging_os_errors_never_expose_private_paths(monkeypatch, spec):
    Child(monkeypatch, spec)

    def unavailable(*args, **kwargs):
        raise PermissionError(13, "Permission denied", str(spec.directory / "worker-x"))

    monkeypatch.setattr(study.tempfile, "TemporaryDirectory", unavailable)
    with pytest.raises(export.LocalExportError, match="private staging files") as caught:
        study.build(spec)
    assert str(spec.directory) not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_archive_check_detects_changed_or_extra_entries(tmp_path):
    source = tmp_path / "a.txt"
    source.write_bytes(b"alpha")
    members = [("Top/a.txt", source, 5, hashlib.sha256(b"alpha").hexdigest(), zipfile.ZIP_STORED)]
    archive = tmp_path / "bundle.zip"
    study._archive(archive, members, threading.Event(), lambda *_: None)
    study.check_archive(archive, members, threading.Event(), lambda *_: None)
    changed = [(*members[0][:3], "0" * 64, members[0][4])]
    with pytest.raises(export.LocalExportError, match="does not match"):
        study.check_archive(archive, changed, threading.Event(), lambda *_: None)
    with zipfile.ZipFile(archive, "a") as bundle:
        bundle.writestr("Top/extra.txt", b"extra")
    with pytest.raises(export.LocalExportError, match="unexpected entries"):
        study.check_archive(archive, members, threading.Event(), lambda *_: None)
    archive.write_bytes(b"not a zip")
    with pytest.raises(export.LocalExportError, match="complete ZIP"):
        study.check_archive(archive, members, threading.Event(), lambda *_: None)
    source.write_bytes(b"omega")
    with pytest.raises(export.LocalExportError, match="changed while archiving"):
        study._archive(tmp_path / "again.zip", members, threading.Event(), lambda *_: None)


@pytest.mark.parametrize(
    "changes",
    [
        {"top": "CON"},
        {"blend": "Cut.mp4"},
        {"blend": ".hidden.blend"},
        {"scenes": ()},
        {"scenes": ("Same", "Same")},
        {"documents": texts()[:3]},
        {"documents": (texts()[1], texts()[0], *texts()[2:])},
        {"documents": ((documents.RECIPE_FILE, "[1]"), *texts()[1:])},
        {"markers": ("short",)},
        {"markers": ("line\nbreak-identifier",)},
        {"snapshot_sha256": "0" * 63},
        {"timeout": 0},
        {"timeout": True},
        {"binary": Path("relative")},
    ],
)
def test_invalid_specifications_are_rejected_before_work(spec, changes):
    with pytest.raises(ValueError):
        replace(spec, **changes)


def test_media_names_must_be_unique_and_within_the_budget(spec, media, monkeypatch):
    duplicate = replace(spec.media[1], name=spec.media[0].name.upper())
    with pytest.raises(ValueError, match="2,000 distinct"):
        replace(spec, media=(spec.media[0], duplicate))
    monkeypatch.setattr(study, "MAX_MEDIA_BYTES", 10)
    with pytest.raises(ValueError, match="2,000 distinct"):
        replace(spec, media=spec.media)
    with pytest.raises(ValueError, match="portable"):
        study.BundleMedia(spec.media[0].stamp, "CON.mp4", "movie")
    with pytest.raises(ValueError, match="kind"):
        study.BundleMedia(spec.media[0].stamp, "001 clip.mp4", "clip")


def test_bundle_and_media_names_stay_portable():
    assert study.bundle_names("Signal: At Dawn?") == (
        "Signal- At Dawn- Case Study",
        "Signal- At Dawn- Case Study.blend",
        "Signal- At Dawn- - Case Study.zip",
    )
    assert study.bundle_names("  . ") == (
        "Film Case Study",
        "Film Case Study.blend",
        "Film - Case Study.zip",
    )
    long = study.bundle_names("é" * 300)
    assert all(len(name.encode()) <= 255 and export.portable_name(name) for name in long)
    assert study.media_name(1, "movie", Path("/a/0.MP4")) == "001 movie.mp4"
    assert study.media_name(12, "image", "frame.weird-suffix") == "012 image"
    assert study.media_name(2000, "font", "font.ttf") == "2000 font.ttf"
    with pytest.raises(ValueError):
        study.media_name(0, "movie", "a.mp4")


def test_space_check_counts_media_copies_and_the_archive(monkeypatch, tmp_path, spec):
    destination = tmp_path / "Cut.zip"
    study.check_space(spec, destination)
    staging, target = study.estimated_bytes(spec)
    assert staging > target > spec.media_bytes
    monkeypatch.setattr(
        study.shutil, "disk_usage", lambda path: type("Usage", (), {"free": staging})()
    )
    with pytest.raises(export.LocalExportError, match="free disk space"):
        study.check_space(spec, destination)
    with pytest.raises(export.LocalExportError, match="must already exist"):
        study.check_space(spec, tmp_path / "missing" / "Cut.zip")


def test_destinations_and_publish_cover_zip_archives(monkeypatch, tmp_path, spec):
    folder = tmp_path / "out"
    folder.mkdir()
    with pytest.raises(export.LocalExportError, match="ending in .zip"):
        export.validate_destination(folder / "Cut.mp4", suffix=".zip")
    with pytest.raises(ValueError, match="supported export"):
        export.validate_destination(folder / "Cut.tar", suffix=".tar")
    assert export.validate_destination(folder / "Cut.ZIP", suffix=".zip") == folder / "Cut.ZIP"
    Child(monkeypatch, spec)
    staged = study.build(spec)
    published = export.publish(staged, folder / "Cut.zip")
    assert isinstance(published, study.PublishedBundle)
    assert (published.sha256, published.size) == (staged.sha256, staged.size)
    assert published.scenes == spec.scenes
    with pytest.raises(export.LocalExportError, match="already exists"):
        export.publish(staged, folder / "Cut.zip")
    monkeypatch.setattr(export, "_free", lambda path: 0)
    with pytest.raises(export.ExportPublishError, match="this case-study export") as caught:
        export.publish(staged, folder / "Other.zip")
    assert caught.value.staged is staged and not (folder / "Other.zip").exists()


@pytest.fixture
def owner(tmp_path):
    adapters, workers = [], []

    def create():
        adapter = SDKAdapter(
            Credentials("key", "secret"),
            online=lambda: True,
            base_url=SCOPE.service,
            account_id=SCOPE.account_id,
            project_id=SCOPE.project_id,
            transport=httpx.MockTransport(lambda request: pytest.fail("Export used the network")),
        )
        adapters.append(adapter)
        coordinator = JobCoordinator(adapter, JobStore(tmp_path / "jobs.sqlite3", SCOPE))
        exports = LocalExportWorker(coordinator)
        workers.append(exports)
        return coordinator, exports

    yield create
    for exports in workers:
        exports.shutdown()
    for adapter in adapters:
        adapter.close()


def test_case_study_runs_on_the_owned_export_thread_and_republishes(
    monkeypatch, tmp_path, owner, spec
):
    coordinator, exports = owner()
    threads = []
    built = Child(monkeypatch, spec)
    original = study.build

    def build(value, *, cancel, progress):
        threads.append(threading.current_thread())
        return original(value, cancel=cancel, progress=progress)

    monkeypatch.setattr(study, "build", build)
    destination = tmp_path / "Cut.zip"
    with pytest.raises(export.LocalExportError, match="ending in .zip"):
        exports.export_case_study(
            spec, tmp_path / "Cut.mp4", origin=ORIGIN, source_origin=SOURCE
        ).result(5)
    task = exports.export_case_study(spec, destination, origin=ORIGIN, source_origin=SOURCE)
    assert isinstance(task, ExportTask)
    result = task.result(10)
    assert isinstance(result, LocalExportResult)
    assert isinstance(result.export, study.PublishedBundle)
    assert result.export.destination == destination and zipfile.is_zipfile(destination)
    assert threads[0].name == "ScenarioFilmExport"
    assert len(built.calls) == 2
    with pytest.raises(export.LocalExportError, match="ending in .zip"):
        exports.publish_film_export(
            result.staged, tmp_path / "Copy.mp4", origin=ORIGIN, source_origin=SOURCE
        ).result(5)
    copy = exports.publish_film_export(
        result.staged, tmp_path / "Copy.zip", origin=ORIGIN, source_origin=SOURCE
    ).result(5)
    assert copy.export.sha256 == result.export.sha256 and copy.staged is result.staged
    with pytest.raises(TypeError):
        exports.export_case_study(object(), destination, origin=ORIGIN, source_origin=SOURCE)


def test_a_build_that_finishes_after_retirement_registers_and_publishes_nothing(
    monkeypatch, tmp_path, owner, spec
):
    coordinator, exports = owner()
    Child(monkeypatch, spec)
    original = study.build

    def build(value, *, cancel, progress):
        staged = original(value, cancel=cancel, progress=progress)
        # The owner retires while the archive is being verified.
        coordinator.deactivate()
        return staged

    monkeypatch.setattr(study, "build", build)
    destination = tmp_path / "Cut.zip"
    task = exports.export_case_study(spec, destination, origin=ORIGIN, source_origin=SOURCE)
    with pytest.raises(export.ExportPublishCancelled, match="inactive") as caught:
        task.result(10)
    # The verified archive stays in private staging for discard, but nothing can
    # re-publish it and the placeholder is released.
    assert caught.value.staged.path.exists()
    assert not coordinator._staged_exports
    assert not destination.exists()
