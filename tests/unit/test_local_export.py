# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Owned offline Film export: bounds, verification, no-overwrite publish and ownership."""

import hashlib
import json
import ntpath
import os
import sys
import threading
import unicodedata
from contextlib import nullcontext
from dataclasses import replace
from fractions import Fraction
from pathlib import Path, PureWindowsPath

import httpx
import pytest

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs import local_export as export
from scenario.core.jobs import local_render, mp4_inspection
from scenario.core.jobs.coordinator import JobCoordinator, LocalExportResult
from scenario.core.jobs.store import JobOrigin, JobScope, JobStore
from scenario.core.jobs.workers import ExportTask, JobWorkers, LocalExportWorker, WorkerError
from tests.unit.test_mp4_inspection import audio_track, movie, video_track

SCOPE = JobScope("https://service.example.invalid/v1", "account", "project")
ORIGIN = JobOrigin("file", "scene", "revision", None)
SOURCE = JobOrigin("file", "review", "revision", None)


@pytest.fixture
def media(tmp_path):
    path = tmp_path / "media" / "shot.mp4"
    path.parent.mkdir()
    path.write_bytes(b"synthetic movie bytes")
    return path


def make_spec(tmp_path, media, name="film-export-fixture"):
    directory = tmp_path / name
    directory.mkdir()
    (directory / "snapshot.blend").write_bytes(b"synthetic snapshot")
    worker = tmp_path / "film_export_worker.py"
    worker.write_text("# fixture", encoding="utf-8")
    return export.ExportSpec(
        directory,
        Path(sys.executable).resolve(),
        worker,
        "Fixture review",
        local_render.digest(directory / "snapshot.blend"),
        1,
        48,
        24,
        64,
        64,
        True,
        (export.media_stamp(media),),
    )


@pytest.fixture
def spec(tmp_path, media):
    return make_spec(tmp_path, media)


def encoded(spec, **changes):
    options = dict(width=spec.width, height=spec.height, frames=spec.frames, fps=spec.fps)
    options.update(changes)
    tracks = [video_track(**options)]
    if spec.audio:
        tracks.append(audio_track(seconds=spec.duration))
    return movie(*tracks)


def probe(spec, **changes):
    picture = {
        "codec_type": "video",
        "codec_name": "h264",
        "pix_fmt": "yuv420p",
        "width": spec.width,
        "height": spec.height,
        "avg_frame_rate": f"{spec.fps}/1",
        "nb_read_frames": str(spec.frames),
    }
    sound = {
        "codec_type": "audio",
        "codec_name": "aac",
        "sample_rate": "48000",
        "channels": 2,
        "time_base": "1/48000",
        "duration_ts": int(spec.duration * 48000) + 240,
    }
    picture.update(changes.pop("video", {}))
    sound.update(changes.pop("audio", {}))
    streams = [picture] + ([sound] if spec.audio else []) + changes.pop("extra", [])
    return json.dumps({"streams": streams}).encode()


def measured(spec, **changes):
    value = {
        "width": spec.width,
        "height": spec.height,
        "fps": float(spec.fps),
        "frames": spec.frames,
        "sound": {"frames": spec.frames, "rate": 48000, "channels": "STEREO"}
        if spec.audio
        else {"frames": 1, "rate": 0, "channels": "INVALID"},
        "decoded": [True, True],
    }
    value.update(changes)
    return json.dumps(value).encode()


class Child:
    """Fake owned processes: render writes MP4 bytes, verification writes JSON."""

    def __init__(self, monkeypatch, spec, *, ffprobe=True, video=None, report=None, extra=False):
        self.calls, self.spec = [], spec
        self.video = encoded(spec) if video is None else video
        self.report = probe(spec) if report is None else report
        self.extra = extra
        self.render_hook = None
        monkeypatch.setattr(
            export.shutil, "which", lambda name: "/fixture/ffprobe" if ffprobe else None
        )
        if not ffprobe and report is None:
            self.report = measured(spec)
        monkeypatch.setattr(export, "_run", self)

    def __call__(self, command, *, log, env, timeout, cancel, stdout=None, on_poll=None):
        self.calls.append((command, env, timeout))
        log.write_text("fixture")
        if str(self.spec.directory / "snapshot.blend") in command:
            output = self.spec.directory / "output"
            log.write_bytes(b"noise\nSCENARIO_PROGRESS 999999/1\nSCENARIO_PROGRESS 12/48\n")
            on_poll()
            (output / "film.mp4").write_bytes(self.video)
            if self.extra:
                (output / "film0001-0048.mp4").write_bytes(b"split")
            if self.render_hook:
                self.render_hook()
        elif command[0].endswith("ffprobe"):
            stdout.write_bytes(self.report)
        else:
            (self.spec.directory / "measured.json").write_bytes(self.report)


def test_render_verifies_with_ffprobe_and_scrubs_environment(monkeypatch, spec):
    monkeypatch.setenv("SCENARIO_API_KEY", "synthetic-key")
    monkeypatch.setenv("BLENDER_USER_RESOURCES", "/normal-profile")
    child = Child(monkeypatch, spec)
    events = []
    staged = export.render(spec, progress=lambda *event: events.append(event))
    assert (staged.frames, staged.fps, staged.width, staged.height) == (48, 24, 64, 64)
    assert staged.audio and staged.verification == "ffprobe"
    assert staged.sha256 == local_render.digest(staged.path, maximum=export.MAX_OUTPUT_BYTES)
    assert (
        staged.media == (export.MediaReceipt("shot.mp4", 21, staged.media[0].sha256),)
        and len(staged.media[0].sha256) == 64
    )
    command, env, timeout = child.calls[0]
    for flag in ("--quiet", "--offline-mode", "--factory-startup", "--disable-autoexec"):
        assert flag in command
    assert timeout == spec.render_timeout == 300 + 2 * 48
    assert "SCENARIO_API_KEY" not in env
    assert str(spec.directory) in env["BLENDER_USER_RESOURCES"]
    assert not Path(env["BLENDER_USER_RESOURCES"]).exists()
    assert "-count_frames" in child.calls[1][0] and "-enable_drefs" in child.calls[1][0]
    assert ("render", 12, 48) in events and ("render", 999999, 48) not in events
    assert {event[0] for event in events} == {"media", "render", "verify"}
    assert json.loads((spec.directory / "started.json").read_text())["mode"] == "render"


def test_reused_snapshot_is_refused_before_hashing_without_private_paths(monkeypatch, spec):
    Child(monkeypatch, spec)
    export.render(spec)
    hashed = []
    monkeypatch.setattr(export, "_hash_media", lambda *args: hashed.append(args))
    for marker in ("started.json", "output"):
        with pytest.raises(export.LocalExportError, match="already used") as caught:
            export.render(spec)
        assert str(spec.directory) not in str(caught.value) and not hashed
        if marker == "started.json":
            (spec.directory / marker).unlink()


@pytest.mark.parametrize("ffprobe", [True, False])
def test_missing_verification_reports_fail_without_private_paths(monkeypatch, spec, ffprobe):
    child = Child(monkeypatch, spec, ffprobe=ffprobe)

    def run(command, *, stdout=None, **kwargs):
        # The verification child exits successfully without writing its report.
        if str(spec.directory / "snapshot.blend") in command:
            return child(command, stdout=stdout, **kwargs)
        kwargs["log"].write_text("fixture")

    monkeypatch.setattr(export, "_run", run)
    with pytest.raises(export.LocalExportError, match="missing or too large") as caught:
        export.render(spec)
    assert str(spec.directory) not in str(caught.value)


def test_staging_os_errors_never_expose_private_paths(monkeypatch, spec):
    Child(monkeypatch, spec)

    def unavailable(*args, **kwargs):
        raise PermissionError(13, "Permission denied", str(spec.directory / "worker-x"))

    monkeypatch.setattr(export.tempfile, "TemporaryDirectory", unavailable)
    with pytest.raises(export.LocalExportError, match="private staging files") as caught:
        export.render(spec)
    assert str(spec.directory) not in str(caught.value)
    assert caught.value.__cause__ is None and caught.value.__suppress_context__


def test_render_falls_back_to_blender_decode_without_ffprobe(monkeypatch, spec):
    child = Child(monkeypatch, spec, ffprobe=False)
    staged = export.render(spec)
    assert staged.verification == "blender"
    command = child.calls[1][0]
    assert "--factory-startup" in command and str(spec.directory / "snapshot.blend") not in command
    request = json.loads((spec.directory / "verify.json").read_text())
    assert request["mode"] == "verify" and request["frames"] == 48 and request["audio"] is True


def test_silent_exports_require_no_audio_stream(monkeypatch, spec):
    spec = replace(spec, audio=False)
    Child(monkeypatch, spec)
    assert export.render(spec).audio is False


@pytest.mark.parametrize(
    "video",
    [
        {"frames": 47},
        {"fps": 25, "frames": 48},
        {"width": 66},
        {"profile": 110},
        {"kind": b"mp4v"},
        {"timing": [(47, 512), (1, 1024)]},
    ],
    ids=["frames", "rate", "size", "ten-bit-profile", "codec", "variable-rate"],
)
def test_container_mismatch_never_publishes(monkeypatch, spec, video):
    Child(monkeypatch, spec, video=encoded(spec, **video))
    with pytest.raises(export.LocalExportError, match="H.264 frames"):
        export.render(spec)
    assert (spec.directory / "output/film.mp4").exists()


@pytest.mark.parametrize(
    "tracks",
    [
        lambda spec: movie(video_track()),
        lambda spec: movie(video_track(), audio_track(seconds=Fraction(3))),
        lambda spec: movie(video_track(), audio_track(seconds=Fraction(2), channels=1)),
        lambda spec: movie(video_track(), audio_track(seconds=Fraction(2), object_type=0x6B)),
    ],
    ids=["missing-audio", "audio-duration", "mono", "not-aac"],
)
def test_audio_mismatch_never_publishes(monkeypatch, spec, tracks):
    Child(monkeypatch, spec, video=tracks(spec))
    with pytest.raises(export.LocalExportError, match="stream inventory|AAC soundtrack"):
        export.render(spec)


@pytest.mark.parametrize(
    "changes",
    [
        {"video": {"nb_read_frames": "47"}},
        {"video": {"width": 66}},
        {"video": {"avg_frame_rate": "25/1"}},
        {"video": {"pix_fmt": "yuv444p"}},
        {"video": {"codec_name": "hevc"}},
        {"audio": {"codec_name": "mp3"}},
        {"audio": {"duration_ts": 48000 * 3}},
        {"audio": {"channels": 1}},
        {"extra": [{"codec_type": "data"}]},
    ],
)
def test_decoded_probe_mismatch_never_publishes(monkeypatch, spec, changes):
    Child(monkeypatch, spec, report=probe(spec, **changes))
    with pytest.raises(export.LocalExportError, match="Decoded video"):
        export.render(spec)


def test_probe_rejects_missing_audio_and_malformed_reports(spec):
    with pytest.raises(export.LocalExportError):
        export.check_probe(replace(spec, audio=False), probe(spec))
    for raw in (b"{}", b"[]", b"not json", json.dumps({"streams": [{}] * 9}).encode()):
        with pytest.raises(export.LocalExportError):
            export.check_probe(spec, raw)


@pytest.mark.parametrize(
    "changes",
    [
        {"frames": 47},
        {"fps": 25.0},
        {"width": 66},
        {"decoded": [True, False]},
        {"sound": None},
        {"sound": {"frames": 30, "rate": 48000, "channels": "STEREO"}},
        {"sound": {"frames": 48, "rate": 44100, "channels": "STEREO"}},
        {"frames": True},
    ],
)
def test_blender_decode_mismatch_never_publishes(monkeypatch, spec, changes):
    Child(monkeypatch, spec, ffprobe=False, report=measured(spec, **changes))
    with pytest.raises(export.LocalExportError, match="Blender could not decode"):
        export.render(spec)


def test_blender_check_requires_silence_for_silent_exports(spec):
    silent = replace(spec, audio=False)
    export.check_blender(silent, measured(silent))
    export.check_blender(silent, measured(silent, sound=None))
    with pytest.raises(export.LocalExportError):
        export.check_blender(silent, measured(spec))


@pytest.mark.parametrize("extra", [False, True])
def test_output_inventory_must_be_exactly_one_mp4(monkeypatch, spec, extra):
    child = Child(monkeypatch, spec, extra=extra)
    if not extra:
        child.video = b"not an mp4 container at all"
    with pytest.raises(export.LocalExportError, match="exactly one MP4|complete MP4"):
        export.render(spec)
    assert len(child.calls) == 1


def test_oversized_output_stops_the_child(monkeypatch, spec):
    child = Child(monkeypatch, spec)
    monkeypatch.setattr(export, "MAX_OUTPUT_BYTES", 16)

    def write_large():
        (spec.directory / "output/film.mp4").write_bytes(bytes(64))

    original = child.__call__

    def run(command, **kwargs):
        poll = kwargs["on_poll"]

        def check():
            write_large()
            poll()

        return original(command, **{**kwargs, "on_poll": check})

    monkeypatch.setattr(export, "_run", run)
    with pytest.raises(export.LocalExportError, match="size policy"):
        export.render(spec)


def test_media_changed_during_render_is_rejected(monkeypatch, spec, media):
    child = Child(monkeypatch, spec)
    child.render_hook = lambda: media.write_bytes(b"replaced movie bytes!")
    with pytest.raises(export.LocalExportError, match="changed during rendering"):
        export.render(spec)
    assert (spec.directory / "output/film.mp4").exists()


def test_media_changed_after_snapshot_never_starts(monkeypatch, spec, media):
    child = Child(monkeypatch, spec)
    media.write_bytes(b"changed after the snapshot")
    with pytest.raises(export.LocalExportError, match="changed after the scene snapshot"):
        export.render(spec)
    assert not child.calls and not (spec.directory / "started.json").exists()


def test_child_failures_use_export_wording_and_keep_logs(monkeypatch, spec):
    Child(monkeypatch, spec)

    def timed_out(command, *, log, **kwargs):
        log.write_text("fixture diagnostics")
        raise local_render.LocalRenderError("Local capture timed out; inspect retained frames")

    monkeypatch.setattr(export, "_run", timed_out)
    with pytest.raises(export.LocalExportError, match="Film export process failed or timed out"):
        export.render(spec)
    assert (spec.directory / "render.log").read_text() == "fixture diagnostics"


def test_tampered_snapshot_and_missing_worker_never_start(monkeypatch, spec):
    child = Child(monkeypatch, spec)
    (spec.directory / "snapshot.blend").write_bytes(b"modified")
    with pytest.raises(export.LocalExportError, match="snapshot changed"):
        export.render(spec)
    assert not child.calls and not (spec.directory / "started.json").exists()


@pytest.mark.parametrize("stage", ["before", "hashing", "child", "after"])
def test_cancellation_stops_at_each_stage(monkeypatch, spec, stage):
    child = Child(monkeypatch, spec)
    cancel = threading.Event()
    if stage == "before":
        cancel.set()
    elif stage == "hashing":

        def progress(phase, done, total):
            if phase == "media":
                cancel.set()

        with pytest.raises(local_render.RenderCancelled):
            export.render(spec, cancel=cancel, progress=progress)
        assert not (spec.directory / "started.json").exists()
        return
    elif stage == "child":

        def cancelled(command, **kwargs):
            raise local_render.RenderCancelled("Local capture cancelled")

        monkeypatch.setattr(export, "_run", cancelled)
    else:
        child.render_hook = cancel.set
    with pytest.raises(local_render.RenderCancelled):
        export.render(spec, cancel=cancel)
    if stage == "after":
        assert (spec.directory / "output/film.mp4").exists()
    assert not list(spec.directory.glob("worker-*"))


def test_progress_parsing_reads_only_a_bounded_tail(tmp_path):
    log = tmp_path / "render.log"
    log.write_bytes(b"SCENARIO_PROGRESS 7/48\n" + b"x" * 8192)
    assert export._progress_from_log(log, 48) is None
    log.write_bytes(b"x" * 8192 + b"SCENARIO_PROGRESS 7/48\nSCENARIO_PROGRESS 49/48\n")
    assert export._progress_from_log(log, 48) is None
    log.write_bytes(b"SCENARIO_PROGRESS 7/48\nSCENARIO_PROGRESS 8/48\n")
    assert export._progress_from_log(log, 48) == 8
    assert export._progress_from_log(tmp_path / "absent.log", 48) is None


@pytest.mark.parametrize(
    "change",
    [
        {"fps": 24.0},
        {"fps": True},
        {"fps": 121},
        {"frame_end": 900 * 24 + 1},
        {"frame_start": 0},
        {"width": 65},
        {"height": 4098},
        {"width": 62},
        {"audio": 1},
        {"timeout": 0},
        {"timeout": export.MAX_TIMEOUT + 1},
        {"verify_timeout": float("nan")},
        {"snapshot_sha256": "A" * 64},
        {"scene_name": ""},
        {"binary": Path("relative")},
        {"media": [object()]},
    ],
)
def test_invalid_spec_rejected_before_work(spec, change):
    with pytest.raises(ValueError):
        replace(spec, **change)


def test_spec_media_and_duration_bounds(spec, media):
    stamp = spec.media[0]
    with pytest.raises(ValueError):
        replace(spec, media=(stamp, stamp))
    large = replace(stamp, path=media.with_name("large.mp4"), size=export.MAX_MEDIA_BYTES)
    with pytest.raises(ValueError):
        replace(spec, media=(stamp, large))
    many = tuple(replace(stamp, path=media.with_name(f"{i}.mp4")) for i in range(2001))
    with pytest.raises(ValueError):
        replace(spec, media=many)
    longest = replace(spec, fps=120, frame_end=export.MAX_FRAMES, media=())
    assert longest.render_timeout == export.MAX_TIMEOUT
    assert longest.duration == export.MAX_SECONDS
    assert replace(spec, timeout=12.5, verify_timeout=3).check_timeout == 3
    with pytest.raises(ValueError):
        export.ExportMedia(Path("relative.mp4"), 1, 1, 1, 1)


def test_media_stamps_require_regular_files(tmp_path, media):
    assert export.media_stamp(media).size == media.stat().st_size
    for path in (tmp_path, tmp_path / "missing.mp4"):
        with pytest.raises(export.LocalExportError, match="regular files"):
            export.media_stamp(path)
    empty = tmp_path / "empty.mp4"
    empty.write_bytes(b"")
    with pytest.raises(export.LocalExportError):
        export.media_stamp(empty)


@pytest.mark.parametrize("invalid_child_path", ["profile", "film.mp4"])
def test_windows_child_paths_are_checked_before_admission(monkeypatch, spec, invalid_child_path):
    child = Child(monkeypatch, spec)
    original = export.blender_path

    def reject(path):
        if path.name == invalid_child_path:
            return original(PureWindowsPath("C:/") / ("x" * 256) / path.name)
        return original(path)

    monkeypatch.setattr(export, "blender_path", reject)
    monkeypatch.setattr(local_render, "blender_path", reject)
    with pytest.raises(local_render.LocalRenderError, match="shorter absolute paths"):
        export.render(spec)
    assert not child.calls and not (spec.directory / "started.json").exists()
    assert not list(spec.directory.glob("worker-*"))


# Destination validation, reservation and publishing.


def test_destination_validation(tmp_path):
    folder = tmp_path / "Film"
    folder.mkdir()
    accepted = export.validate_destination(folder / "Review.MP4")
    assert accepted == folder.resolve() / "Review.MP4"
    longest = "x" * 251 + ".mp4"
    assert export.validate_destination(folder / longest).name == longest
    (folder / "taken.mp4").write_bytes(b"keep")
    (folder / "dangling.mp4").symlink_to(folder / "nowhere.mp4")
    private = tmp_path / "private"
    (private / "nested").mkdir(parents=True)
    (tmp_path / "alias").symlink_to(private / "nested")
    rejected = [
        "relative/film.mp4",
        str(folder / "film.mov"),
        str(folder / ".hidden.mp4"),
        str(folder / ".mp4"),
        str(folder / "taken.mp4"),
        str(folder / "dangling.mp4"),
        str(folder / "line\nbreak.mp4"),
        str(folder / "CON.mp4"),
        str(folder / ("x" * 252 + ".mp4")),
        str(tmp_path / "missing" / "film.mp4"),
        str(folder / "taken.mp4" / "film.mp4"),
        str(private / "film.mp4"),
        str(tmp_path / "alias" / "film.mp4"),
        b"/bytes/film.mp4",
        "",
    ]
    for value in rejected:
        with pytest.raises(export.LocalExportError):
            export.validate_destination(value, private_roots=(private,))
    assert (folder / "taken.mp4").read_bytes() == b"keep"
    with pytest.raises(export.LocalExportError, match="private storage"):
        export.validate_destination(folder / "Review.mp4", private_roots=(None,))


PORTABLE = ["Review.mp4", "Review final (v2).mp4", "CONSOLE.mp4", "COM10.mp4", "nul-take.mp4"]
NOT_PORTABLE = [
    "a:b.mp4",
    "q?.mp4",
    "x|y.mp4",
    "a<b.mp4",
    "a>b.mp4",
    "a*b.mp4",
    'say"hi".mp4',
    "back\\slash.mp4",
    "CON .mp4",
    "con.mp4",
    "Aux.final.mp4",
    "nul  .take.mp4",
    "CONIN$.mp4",
    "LPT9.mp4",
    "COM\u00b9.mp4",
    "x" * 252 + ".mp4",
    "tab\t.mp4",
]


@pytest.mark.parametrize("name", PORTABLE + NOT_PORTABLE)
def test_destination_names_follow_windows_rules(tmp_path, name):
    portable = name in PORTABLE
    assert export.portable_name(name) is portable
    # A Windows-spelled destination keeps the basename unless it holds a separator.
    assert PureWindowsPath("C:\\Film\\" + name).name == name or "\\" in name
    if hasattr(ntpath, "isreserved") and "\\" not in name and len(name.encode()) <= 255:
        # Python 3.13+ applies the same rules to a full Windows path.
        assert ntpath.isreserved("C:\\Film\\" + name) is not portable
    if portable:
        assert export.validate_destination(tmp_path / name) == tmp_path.resolve() / name
    elif "\t" not in name and not (os.name == "nt" and "\\" in name):
        # On Windows a backslash separates folders instead of naming one file.
        with pytest.raises(export.LocalExportError, match="portable"):
            export.validate_destination(str(tmp_path) + "/" + name)
    assert list(tmp_path.iterdir()) == []


@pytest.mark.parametrize(
    "path, root, inside",
    [
        (r"\\?\C:\Users\a\AppData\Blender\state", r"C:\users\a\appdata\blender", True),
        (r"C:\Users\a\AppData\Blender", r"\\?\C:\Users\a\AppData\Blender", True),
        (r"\\?\UNC\server\share\Blender\x", r"\\SERVER\share\blender", True),
        (r"C:\Users\a\Videos", r"\\?\C:\Users\a\AppData\Blender", False),
        (r"D:\Blender", r"C:\Blender", False),
    ],
)
def test_private_roots_compare_windows_spellings(path, root, inside):
    assert export._inside(PureWindowsPath(path), PureWindowsPath(root)) is inside


@pytest.mark.parametrize(
    "spelling",
    [
        str.swapcase,
        # macOS volumes ignore composition: NFD names the same NFC folder.
        lambda text: unicodedata.normalize("NFD", text),
        lambda text: unicodedata.normalize("NFD", text).upper(),
    ],
)
def test_private_roots_ignore_case_and_composition_everywhere(tmp_path, spelling):
    relative = Path("Library", "Vid\u00e9os")
    private = tmp_path / relative
    private.mkdir(parents=True)
    alias = tmp_path / spelling(str(relative))
    assert str(alias) != str(private) and export._inside(alias, private)
    assert export._inside(alias / "nested", private)
    assert not export._inside(tmp_path / "Library" / "Videos", private)
    # A volume that ignores case or composition makes the alias the same folder;
    # on another volume it is a separate folder that is refused anyway.
    (alias / "nested").mkdir(parents=True, exist_ok=True)
    for folder in (alias, alias / "nested"):
        with pytest.raises(export.LocalExportError, match="outside Blender"):
            export.validate_destination(folder / "Review.mp4", private_roots=(private,))


@pytest.mark.parametrize("root", ["", "relative/private", "."])
def test_relative_private_roots_never_resolve_against_the_working_folder(
    monkeypatch, tmp_path, root
):
    # Blender returns a path for a missing user folder; an empty one is a bug.
    folder = tmp_path / "Film"
    folder.mkdir()
    monkeypatch.chdir(tmp_path)
    with pytest.raises(export.LocalExportError, match="private storage"):
        export.validate_destination(folder / "Review.mp4", private_roots=(root,))
    assert list(folder.iterdir()) == []


def staged_fixture(tmp_path, data=b"verified video bytes"):
    directory = tmp_path / "film-export-staged"
    (directory / "output").mkdir(parents=True)
    path = directory / "output" / "film.mp4"
    path.write_bytes(data)
    return export.StagedExport(
        directory,
        path,
        hashlib.sha256(data).hexdigest(),
        len(data),
        48,
        24,
        64,
        64,
        True,
        "ffprobe",
        (export.MediaReceipt("shot.mp4", 3, "0" * 64),),
    )


def leftovers(folder):
    return sorted(path.name for path in folder.iterdir() if path.name.startswith("."))


def test_reservation_never_overwrites_and_release_is_identity_checked(tmp_path):
    destination = tmp_path / "film.mp4"
    reservation = export.reserve(destination)
    assert destination.stat().st_size == 0
    with pytest.raises(export.LocalExportError, match="already exists"):
        export.reserve(destination)
    destination.unlink()
    destination.write_bytes(b"someone else")
    export.release(reservation)
    assert destination.read_bytes() == b"someone else"
    destination.unlink()
    export.release(reservation)
    with pytest.raises(export.LocalExportError, match="Cannot create"):
        export.reserve(tmp_path / "missing" / "film.mp4")
    with pytest.raises(export.LocalExportError, match="absolute"):
        export.reserve("film.mp4")
    assert not Path("film.mp4").exists()


def pinned(reservation):
    pin = reservation.pin
    return pin is not None and pin._fd is not None


@pytest.mark.skipif(not export._PIN_PLACEHOLDERS, reason="POSIX reservations hold it open")
def test_reservation_pins_its_inode_until_released_or_replaced(tmp_path):
    destination = tmp_path / "film.mp4"
    reservation = export.reserve(destination)
    assert pinned(reservation)
    destination.unlink()
    # Linux reuses a freed inode number at once; the open pin keeps ours allocated.
    destination.write_bytes(b"")
    assert destination.stat().st_ino != reservation.inode
    export.release(reservation)
    assert destination.exists() and not pinned(reservation)
    export.release(reservation)
    staged = staged_fixture(tmp_path)
    second = tmp_path / "second.mp4"
    reservation = export.reserve(second)
    export.publish(staged, second, reservation)
    assert second.read_bytes() == b"verified video bytes" and not pinned(reservation)


def test_windows_reservations_keep_no_open_handle(monkeypatch, tmp_path):
    monkeypatch.setattr(export, "_PIN_PLACEHOLDERS", False)
    reservation = export.reserve(tmp_path / "film.mp4")
    assert reservation.pin is None
    export.release(reservation)
    assert not (tmp_path / "film.mp4").exists()


def test_longest_portable_name_publishes_and_republishes(tmp_path):
    staged = staged_fixture(tmp_path)
    folder = tmp_path / "Film"
    folder.mkdir()
    for prefix in ("x", "y"):
        destination = export.validate_destination(folder / (prefix * 251 + ".mp4"))
        assert len(destination.name.encode()) == 255
        export.publish(staged, destination)
        assert destination.read_bytes() == b"verified video bytes"
    assert not leftovers(folder)


def test_publish_copies_verified_bytes_and_replaces_only_the_placeholder(tmp_path):
    staged = staged_fixture(tmp_path)
    destination = tmp_path / "Review.mp4"
    events = []
    published = export.publish(staged, destination, progress=lambda *e: events.append(e))
    assert destination.read_bytes() == b"verified video bytes"
    assert (published.sha256, published.size) == (staged.sha256, staged.size)
    assert published.media == staged.media and published.verification == "ffprobe"
    assert staged.path.exists() and not leftovers(tmp_path)
    assert events[-1] == ("publish", staged.size, staged.size)
    with pytest.raises(export.LocalExportError, match="already exists"):
        export.publish(staged, destination)
    assert destination.read_bytes() == b"verified video bytes"


@pytest.mark.parametrize("replacement", [b"user file", b""])
def test_publish_rejects_a_replaced_placeholder_without_overwriting(tmp_path, replacement):
    staged = staged_fixture(tmp_path)
    destination = tmp_path / "Review.mp4"
    reservation = export.reserve(destination)
    destination.unlink()
    # An empty replacement differs from our placeholder only by file identity.
    destination.write_bytes(replacement)
    with pytest.raises(export.ExportPublishError, match="destination changed") as caught:
        export.publish(staged, destination, reservation)
    assert caught.value.staged is staged
    assert destination.read_bytes() == replacement
    assert staged.path.exists() and not leftovers(tmp_path)


def test_replace_failure_keeps_staged_output_and_removes_placeholder(monkeypatch, tmp_path):
    staged = staged_fixture(tmp_path)
    destination = tmp_path / "Review.mp4"

    def fail(*args):
        raise PermissionError("locked")

    monkeypatch.setattr(export.os, "replace", fail)
    with pytest.raises(export.ExportPublishError, match="move the verified video") as caught:
        export.publish(staged, destination)
    assert caught.value.staged is staged
    assert not destination.exists() and not leftovers(tmp_path) and staged.path.exists()


def test_changed_staging_and_cancelled_publish_leave_no_destination(tmp_path):
    staged = staged_fixture(tmp_path)
    staged.path.write_bytes(b"tampered video bytes")
    with pytest.raises(export.ExportPublishError, match="changed before publishing"):
        export.publish(staged, tmp_path / "Review.mp4")
    assert not (tmp_path / "Review.mp4").exists() and not leftovers(tmp_path)
    staged = staged_fixture(tmp_path / "second")
    cancel = threading.Event()
    cancel.set()
    with pytest.raises(export.ExportPublishCancelled) as caught:
        export.publish(staged, tmp_path / "Review.mp4", cancel=cancel)
    assert isinstance(caught.value, local_render.RenderCancelled)
    assert caught.value.staged is staged
    assert not (tmp_path / "Review.mp4").exists() and not leftovers(tmp_path)


def test_cancel_after_the_copy_never_replaces_the_placeholder(tmp_path):
    staged = staged_fixture(tmp_path)
    destination = tmp_path / "Review.mp4"
    cancel = threading.Event()

    def progress(phase, done, total):
        # Retirement arrives after the last chunk, while the copy is synced.
        if done == total:
            cancel.set()

    with pytest.raises(export.ExportPublishCancelled) as caught:
        export.publish(staged, destination, cancel=cancel, progress=progress)
    assert caught.value.staged is staged and staged.path.exists()
    assert not destination.exists() and not leftovers(tmp_path)


def test_publish_checks_free_space_for_the_exact_copy(monkeypatch, tmp_path):
    staged = staged_fixture(tmp_path)
    destination = tmp_path / "Review.mp4"
    usage = export.shutil.disk_usage(tmp_path)
    free = [staged.size + export.SPACE_MARGIN - 1]
    monkeypatch.setattr(export.shutil, "disk_usage", lambda path: usage._replace(free=free[0]))
    with pytest.raises(export.ExportPublishError, match="free disk space") as caught:
        export.publish(staged, destination)
    assert caught.value.staged is staged and staged.path.exists()
    assert not destination.exists() and not leftovers(tmp_path)
    free[0] += 1
    export.publish(staged, destination)
    assert destination.read_bytes() == b"verified video bytes"


def test_low_free_space_stops_the_child(monkeypatch, spec):
    Child(monkeypatch, spec)
    usage = export.shutil.disk_usage(spec.directory)
    monkeypatch.setattr(
        export.shutil, "disk_usage", lambda path: usage._replace(free=export.SPACE_MARGIN - 1)
    )
    with pytest.raises(export.LocalExportError, match="free disk space"):
        export.render(spec)
    assert not (spec.directory / "output" / "film.mp4").exists()


def test_final_staged_hash_observes_cancellation(monkeypatch, spec):
    Child(monkeypatch, spec)
    cancel = threading.Event()
    digest = export.digest

    def hashing(path, **options):
        if Path(path).name == export.VIDEO_NAME:
            # Retirement arrives while the staged video is hashed.
            cancel.set()
        return digest(path, **options)

    monkeypatch.setattr(export, "digest", hashing)
    with pytest.raises(local_render.RenderCancelled, match="staged output is retained"):
        export.render(spec, cancel=cancel)
    assert (spec.directory / "output" / "film.mp4").exists()


def test_unwritable_destination_folder_keeps_staged_output(tmp_path):
    if os.name == "nt" or os.geteuid() == 0:
        pytest.skip("POSIX permission regression")
    staged = staged_fixture(tmp_path)
    folder = tmp_path / "locked"
    folder.mkdir()
    folder.chmod(0o500)
    try:
        with pytest.raises(export.LocalExportError, match="Cannot create"):
            export.publish(staged, folder / "Review.mp4")
    finally:
        folder.chmod(0o700)
    assert staged.path.exists() and list(folder.iterdir()) == []


def test_space_check_and_staging_discard(monkeypatch, tmp_path, spec):
    assert export.estimated_bytes(spec) > 64 * 1024**2
    export.check_space(spec, tmp_path / "Review.mp4")
    usage = export.shutil.disk_usage(tmp_path)
    monkeypatch.setattr(
        export.shutil, "disk_usage", lambda path: usage._replace(free=export.estimated_bytes(spec))
    )
    with pytest.raises(export.LocalExportError, match="free disk space"):
        export.check_space(spec, tmp_path / "Review.mp4")
    with pytest.raises(export.LocalExportError, match="folder must already exist"):
        export.check_space(spec, tmp_path / "missing" / "Review.mp4")
    with pytest.raises(export.LocalExportError, match="staging"):
        export.discard_staging(tmp_path)
    export.discard_staging(spec.directory)
    assert not spec.directory.exists()


# Coordinator and owned export thread.


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


def blocking_render(tmp_path, entered, release):
    def render(spec, *, cancel, progress):
        progress("render", 1, spec.frames)
        entered.set()
        assert release.wait(5)
        return staged_fixture(tmp_path / "staging")

    return render


def test_export_runs_on_owned_thread_and_publishes(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    threads = []

    def render(value, *, cancel, progress):
        threads.append(threading.current_thread())
        progress("render", 48, 48)
        return staged_fixture(tmp_path / "staging")

    monkeypatch.setattr(export, "render", render)
    destination = tmp_path / "Review.mp4"
    task = exports.export_film(spec, destination, origin=ORIGIN, source_origin=SOURCE)
    assert isinstance(task, ExportTask)
    result = task.result(5)
    assert isinstance(result, LocalExportResult)
    assert (result.scope, result.origin, result.source_origin) == (SCOPE, ORIGIN, SOURCE)
    assert result.export.destination == destination and destination.exists()
    assert threads[0].name == "ScenarioFilmExport"
    assert threads[0] is not threading.main_thread()
    assert task.progress()[0] == "publish"
    copy = exports.publish_film_export(
        result.staged, tmp_path / "Copy.mp4", origin=ORIGIN, source_origin=SOURCE
    ).result(5)
    assert copy.export.sha256 == result.export.sha256 and copy.staged is result.staged


def test_export_does_not_occupy_shared_job_workers(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    shared = JobWorkers(coordinator, workers=1, pending_limit=1)
    entered, release = threading.Event(), threading.Event()
    monkeypatch.setattr(export, "render", blocking_render(tmp_path, entered, release))
    task = exports.export_film(spec, tmp_path / "Review.mp4", origin=ORIGIN, source_origin=SOURCE)
    try:
        assert entered.wait(5)
        with pytest.raises(WorkerError, match="current Film export"):
            exports.export_film(spec, tmp_path / "Other.mp4", origin=ORIGIN, source_origin=SOURCE)
        # The shared pool still accepts and runs a local capture meanwhile.
        captured = threading.Event()

        def capture(value, *, cancel):
            captured.set()
            raise local_render.LocalRenderError("fixture capture")

        monkeypatch.setattr(local_render, "render", capture)
        from tests.unit.test_job_workers import local_spec

        pending = shared.render_local(local_spec(tmp_path), origin=ORIGIN, source_origin=ORIGIN)
        with pytest.raises(local_render.LocalRenderError):
            pending.result(5)
        assert captured.is_set() and not shared._local_cancels
    finally:
        release.set()
        task.result(5)
        shared.shutdown()


@pytest.mark.parametrize("retire", [False, True])
def test_cancel_and_retirement_release_the_placeholder(monkeypatch, tmp_path, owner, spec, retire):
    coordinator, exports = owner()
    entered = threading.Event()
    seen = {}

    def render(value, *, cancel, progress):
        seen["placeholder"] = (tmp_path / "Review.mp4").exists()
        entered.set()
        assert cancel.wait(5)
        raise local_render.RenderCancelled("Film export cancelled")

    monkeypatch.setattr(export, "render", render)
    task = exports.export_film(spec, tmp_path / "Review.mp4", origin=ORIGIN, source_origin=SOURCE)
    assert entered.wait(5)
    if retire:
        exports.shutdown()
        assert exports.stopped
        with pytest.raises(WorkerError, match="inactive"):
            exports.export_film(spec, tmp_path / "Other.mp4", origin=ORIGIN, source_origin=SOURCE)
    else:
        exports.cancel(task)
    with pytest.raises(local_render.RenderCancelled):
        task.result(5)
    assert seen["placeholder"] and not (tmp_path / "Review.mp4").exists()


@pytest.mark.parametrize("late", [False, True])
def test_origin_change_before_reservation_and_inactive_owner_before_publish(
    monkeypatch, tmp_path, owner, spec, late
):
    coordinator, exports = owner()
    current = [not late]
    coordinator._origin_guard = lambda origin: nullcontext(current[0])
    rendered = []

    def render(value, *, cancel, progress):
        rendered.append(value)
        coordinator.deactivate()
        return staged_fixture(tmp_path / "staging")

    monkeypatch.setattr(export, "render", render)
    destination = tmp_path / "Review.mp4"
    task = exports.export_film(spec, destination, origin=ORIGIN, source_origin=SOURCE)
    if late:
        with pytest.raises(local_render.RenderCancelled, match="scene changed"):
            task.result(5)
        assert not rendered
    else:
        with pytest.raises(export.ExportPublishCancelled, match="inactive") as caught:
            task.result(5)
        assert caught.value.staged.path.exists()
    assert not destination.exists()


def test_republish_requires_this_owners_staged_export(monkeypatch, tmp_path, owner):
    coordinator, exports = owner()
    foreign = staged_fixture(tmp_path)
    task = exports.publish_film_export(
        foreign, tmp_path / "Copy.mp4", origin=ORIGIN, source_origin=SOURCE
    )
    with pytest.raises(ValueError, match="verified staged Film export"):
        task.result(5)
    with pytest.raises(TypeError):
        exports.publish_film_export(
            object(), tmp_path / "x.mp4", origin=ORIGIN, source_origin=SOURCE
        )
    with pytest.raises(TypeError):
        exports.export_film(object(), tmp_path / "x.mp4", origin=ORIGIN, source_origin=SOURCE)


def test_relative_destination_is_refused_before_a_thread_starts(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    monkeypatch.chdir(tmp_path)
    for command, value in ((exports.export_film, spec), (exports.publish_film_export, None)):
        value = value if value is not None else staged_fixture(tmp_path)
        with pytest.raises(export.LocalExportError, match="absolute"):
            command(value, "Review.mp4", origin=ORIGIN, source_origin=SOURCE)
    assert exports._threads == [] and not (tmp_path / "Review.mp4").exists()


@pytest.mark.parametrize("name", ["a:b.mp4", "CON .mp4", ".hidden.mp4", "missing/Review.mp4"])
def test_coordinator_rechecks_destination_shape_before_reserving(
    monkeypatch, tmp_path, owner, spec, name
):
    coordinator, exports = owner()
    monkeypatch.setattr(export, "render", lambda *a, **k: pytest.fail("Rendered"))
    monkeypatch.setattr(export, "check_space", lambda *a: pytest.fail("Checked space"))
    folder = tmp_path / "Film"
    folder.mkdir()
    task = exports.export_film(spec, str(folder) + "/" + name, origin=ORIGIN, source_origin=SOURCE)
    with pytest.raises(export.LocalExportError, match="portable|visible|folder must"):
        task.result(5)
    assert list(folder.iterdir()) == []


def test_reused_snapshot_never_reserves_a_destination(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    (spec.directory / "started.json").write_text("{}")
    monkeypatch.setattr(export, "render", lambda *a, **k: pytest.fail("Rendered"))
    task = exports.export_film(spec, tmp_path / "Review.mp4", origin=ORIGIN, source_origin=SOURCE)
    with pytest.raises(export.LocalExportError, match="already used"):
        task.result(5)
    assert not (tmp_path / "Review.mp4").exists()


def test_space_failure_releases_the_reserved_placeholder(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    order = []

    def full(value, destination):
        order.append(("space", Path(destination).exists()))
        raise export.LocalExportError("Not enough free disk space for this video export")

    monkeypatch.setattr(export, "check_space", full)
    monkeypatch.setattr(export, "render", lambda *a, **k: pytest.fail("Rendered"))
    task = exports.export_film(spec, tmp_path / "Review.mp4", origin=ORIGIN, source_origin=SOURCE)
    with pytest.raises(export.LocalExportError, match="free disk space"):
        task.result(5)
    assert order == [("space", True)] and not (tmp_path / "Review.mp4").exists()


def test_existing_destination_fails_before_rendering(monkeypatch, tmp_path, owner, spec):
    coordinator, exports = owner()
    monkeypatch.setattr(export, "render", lambda *a, **k: pytest.fail("Rendered"))
    destination = tmp_path / "Review.mp4"
    destination.write_bytes(b"keep")
    task = exports.export_film(spec, destination, origin=ORIGIN, source_origin=SOURCE)
    with pytest.raises(export.LocalExportError, match="already exists"):
        task.result(5)
    assert destination.read_bytes() == b"keep"


def test_container_check_uses_the_real_inspection_types(spec):
    summary = mp4_inspection.Mp4Summary(
        (mp4_inspection.Mp4Video("h264", 100, 64, 64, 48, Fraction(24), Fraction(2)),),
        (mp4_inspection.Mp4Audio("aac", 48000, 2, Fraction(2)),),
        0,
    )
    export.check_container(spec, summary)
    with pytest.raises(export.LocalExportError, match="stream inventory"):
        export.check_container(spec, replace(summary, other_tracks=1))
