# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Worker-owned persistent Film review copies, separate from scene application."""

import json
import shutil
import tempfile
from dataclasses import dataclass, field, replace
from fractions import Fraction
from pathlib import Path

from ..scene.film_finish import AudioDuration, compose_recipe
from ..scene.film_plan import TaskAssets, validate_film_plan
from . import media_probe
from .film_finishing import CompositionSource, composition_sources
from .film_tasks import _task_context
from .local_render import RenderCancelled
from .store import JobOrigin, JobScope, ResultAsset, StoredResult, _json
from .transfers import DownloadedResult, _root
from .upload_sources import _open, _stamp

MAX_TOTAL_BYTES = 2 * 1024**3


@dataclass(frozen=True)
class ReviewSource:
    scope: JobScope
    result: StoredResult
    path: Path = field(repr=False)
    media: media_probe.MediaInfo


@dataclass(frozen=True, eq=False)
class PreparedFilmReview:
    scope: JobScope
    origin: JobOrigin
    production_id: str
    recipe_json: str = field(repr=False)
    mode: str
    score_task_id: str
    observations: tuple[CompositionSource, ...]
    files: tuple[tuple[str, ReviewSource], ...] = field(repr=False)
    stamps: tuple = field(repr=False)
    directory: Path = field(repr=False)
    jobs: tuple = field(repr=False)
    master_task: str | None = None

    @property
    def recipe(self):
        return json.loads(self.recipe_json)


def check_copies(prepared):
    """Check private file identities without hashing large movies on the GUI thread.

    The application owns the private directory and its ancestors. Hashing and
    probing precede these stamps on the worker; the native caller checks them
    before and after decoding. This is not protection from a hostile same-user
    process replacing ancestors while native decoders open paths.
    """
    if prepared.directory.is_symlink() or not prepared.directory.is_dir():
        raise ValueError("The prepared Film media directory changed")
    for (_, source), expected in zip(prepared.files, prepared.stamps, strict=True):
        if source.path.parent != prepared.directory:
            raise ValueError("The prepared Film media location changed")
        stream, current = _open(source.path)
        with stream:
            if _stamp(current) != expected:
                raise ValueError("Prepared Film media changed; prepare it again")


def discard(prepared):
    discard_directory(prepared.directory)


def discard_directory(directory):
    """Remove an owned unused directory; an already removed root is complete."""
    try:
        shutil.rmtree(directory)
    except FileNotFoundError:
        if directory.exists() or directory.is_symlink():
            raise


def _master(coordinator, recipe, production_id, mode, score_task_id, sources, files):
    """Match the optional master to the compiled current source/timing recipe."""
    media = {task: source.media for task, source in files}
    draft = compose_recipe(
        recipe,
        {source.task_id: TaskAssets(source.scope, (source.asset_id,)) for source in sources},
        scope=coordinator.scope,
        mode=mode,
        score_task_id=score_task_id,
        audio_durations={
            source.task_id: AudioDuration(
                source.scope, source.asset_id, media[source.task_id].duration
            )
            for source in sources
            if source.kind == "audio"
        },
    )
    task = validate_film_plan(draft)[mode + "_master_task"]
    binding, tasks, *_ = _task_context(
        coordinator._store, draft, production_id=production_id, task_id=task, kind="model"
    )
    record = coordinator._store.film_job(production_id, task)
    if (
        record is None
        or record.intent.scope != coordinator.scope
        or record.intent.operation != "model"
        or record.intent.target_id != tasks[task]["model"]
        or record.intent.film_task != binding
        or len(record.results) != 1
        or not record.results[0].asset.media_type.startswith("video/")
    ):
        raise ValueError("Save the master for this exact Film recipe and its current sources first")
    return CompositionSource(
        task,
        coordinator.scope,
        record.intent.request_id,
        record.revision,
        record.results[0].asset.asset_id,
        "video",
        binding.task_sha256,
    )


def validate_sources(coordinator, prepared):
    """Recheck scoped task bindings and revisions before transferring ownership."""
    sources = composition_sources(
        coordinator._store,
        prepared.recipe,
        production_id=prepared.production_id,
        mode=prepared.mode,
        score_task_id=prepared.score_task_id,
        inspect_upload=coordinator._uploads.inspect if coordinator._uploads else None,
    )
    if prepared.master_task is not None:
        sources += (
            _master(
                coordinator,
                prepared.recipe,
                prepared.production_id,
                prepared.mode,
                prepared.score_task_id,
                sources,
                prepared.files,
            ),
        )
    if sources != prepared.observations:
        raise ValueError("Saved Film sources changed; prepare a fresh review")


def prepare(
    coordinator, recipe, *, production_id, mode, score_task_id, include_master, root, origin, cancel
):
    """Copy and measure on the existing worker, with cleanup on every failed admission."""
    if type(include_master) is not bool:
        raise ValueError("Choose explicitly whether to include the saved master")
    encoded = _json(recipe)
    plan = validate_film_plan(recipe)

    def current():
        with coordinator._request_guard(origin):
            if cancel.is_set():
                raise RenderCancelled("Film review preparation cancelled")

    current()
    with coordinator._request_guard(origin):
        observed = composition_sources(
            coordinator._store,
            recipe,
            production_id=production_id,
            mode=mode,
            score_task_id=score_task_id,
            inspect_upload=coordinator._uploads.inspect if coordinator._uploads else None,
        )
    media_probe.probe_tool()
    directory = Path(tempfile.mkdtemp(prefix="review-", dir=_root(root)))
    files, jobs, stamps = [], [], []
    total = 0
    kinds = {task["id"]: task["kind"] for task in plan["tasks"]}

    def stage(observation):
        nonlocal total
        current()
        if kinds.get(observation.task_id) == "upload":
            owner = coordinator._uploads
            saved = owner.inspect(observation.request_id)
            if saved is None or saved.revision != observation.revision:
                raise ValueError("Saved Film upload changed")
            stream, _ = owner._sources._source(saved.intent)
            stream.close()
            path = (
                owner._sources._directory(saved.intent.scope, observation.request_id) / "source.bin"
            )
            receipt = DownloadedResult(
                "source.bin", saved.intent.file_size, saved.intent.file_sha256
            )
            item = StoredResult(
                ResultAsset(observation.asset_id, "source.bin", saved.intent.content_type), receipt
            )
        else:
            verified = coordinator.verify_results(
                observation.request_id, expected_revision=observation.revision
            )
            pairs = [
                (item, path)
                for item, path in zip(verified.record.results, verified.paths, strict=True)
                if item.asset.asset_id == observation.asset_id
            ]
            if len(pairs) != 1:
                raise ValueError("Choose one matching saved Film output")
            item, path = pairs[0]
            jobs.append(verified)
        receipt = item.receipt
        if receipt is None or not 0 < receipt.size <= media_probe.MAX_BYTES:
            raise ValueError("Use bounded saved Film media")
        total += receipt.size
        if total > MAX_TOTAL_BYTES:
            raise ValueError("Keep one Film review within 2 GiB")
        if item.asset.media_type not in media_probe.FORMATS:
            raise ValueError("Use a supported Film movie or audio format")
        target = directory / (str(len(files)) + media_probe.FORMATS[item.asset.media_type][1])
        media_probe._snapshot(path, receipt, target, cancel)
        stream, before = _open(target)
        stream.close()
        copy_receipt = DownloadedResult(target.name, receipt.size, receipt.sha256)
        copied = StoredResult(replace(item.asset, name=target.name), copy_receipt)
        info = media_probe.measure(
            target, copy_receipt, item.asset.media_type, root=root, cancel=cancel
        )
        if info.kind != observation.kind or (
            info.kind == "video" and info.frame_rate != plan["fps"]
        ):
            raise ValueError("Match saved media kind and video frame rate to the Film cut")
        files.append((observation.task_id, ReviewSource(coordinator.scope, copied, target, info)))
        stream, info = _open(target)
        with stream:
            if _stamp(info) != _stamp(before):
                raise ValueError("Prepared Film media changed during inspection")
            stamps.append(_stamp(info))
        current()

    try:
        for source in observed:
            stage(source)
        master_task = None
        if include_master:
            with coordinator._request_guard(origin):
                master = _master(
                    coordinator, recipe, production_id, mode, score_task_id, observed, files
                )
            observed += (master,)
            master_task = master.task_id
            stage(master)
        media = dict(files)
        if master_task is not None and media[master_task].media.duration < Fraction(
            plan["total_frames"], plan["fps"]
        ):
            raise ValueError("Saved master does not cover the Film cut")
        for shot in plan["shots"]:
            field = "video_task" if mode == "final" else "previs_task"
            task = shot.get(field, shot["id"] + ("-video" if mode == "final" else "-previs"))
            trim = round(shot["source_trim"] * plan["fps"]) if mode == "final" else 0
            if media[task].media.duration < Fraction(trim + shot["frames"], plan["fps"]):
                raise ValueError("Saved Film picture does not cover the editorial cut")
        result = PreparedFilmReview(
            coordinator.scope,
            origin,
            production_id,
            encoded,
            mode,
            score_task_id,
            observed,
            tuple(files),
            tuple(stamps),
            directory,
            tuple(jobs),
            master_task,
        )
        current()
        with coordinator._request_guard(origin):
            validate_sources(coordinator, result)
        check_copies(result)
        return result
    except BaseException as error:
        coordinator._discard_failed_film_review(directory, error)
        raise
