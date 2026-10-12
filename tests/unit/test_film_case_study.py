# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Film case-study documents: approved takes, sanitizer, recipe and ledger.

The approved-take cases adapt the selected Studio revision's case-study export tests.
"""

import copy
import json

import pytest

from scenario.core.jobs.store import (
    CloudJobIntent,
    FilmTaskBinding,
    FilmUploadReference,
    JobIntent,
    JobOrigin,
    JobScope,
    JobState,
    ResultAsset,
    StoredJob,
    StoredResult,
)
from scenario.core.scene import film_case_study as study
from scenario.core.scene.film_plan import validate_film_plan
from scenario.core.scene.film_scene_plan import local_plan

SCOPE = JobScope(
    "https://service.example.invalid/v1",
    "local-key-0123456789",
    "proj_fixture9876",
    "team_fixture5432",
)
ORIGIN = JobOrigin("file", "scene", "revision")
PRODUCTION = "0123456789abcdef0123456789abcdef"


def recipe(**changes):
    raw = {
        "title": "Signal At Dawn",
        "project_id": SCOPE.project_id,
        "fps": 24,
        "heroes": {
            "courier": {
                "name": "Courier",
                "description": "Ivory armor",
                "mesh": "courier-mesh",
                "reference": "courier-ref",
            }
        },
        "shots": [
            {
                "id": "s01",
                "title": "Opening",
                "duration": 2,
                "scene": local_plan("studio", "", 2),
                "style_task": "s01-style-v2",
                "previs_task": "s01-previs-v3",
                "video_task": "s01-video-v2",
            }
        ],
        "tasks": [
            {
                "id": "s01-video-v2",
                "title": "Shot one video",
                "kind": "model",
                "model": "model_video",
                "parameters": {
                    "referenceVideos": ["$s01-previs-v3"],
                    "referenceImages": ["$courier-ref", "$s01-style-v2"],
                    "prompt": "Dawn, see https://signed.invalid/media?token=private",
                },
            },
            {
                "id": "s01-style-v2",
                "title": "Style",
                "kind": "model",
                "model": "model_image",
                "parameters": {"image": "$courier-ref", "apiKey": "private-key"},
            },
            {
                "id": "rejected-style",
                "title": "Rejected",
                "kind": "model",
                "model": "m",
                "parameters": {},
            },
            {"id": "courier-ref", "title": "Reference", "kind": "upload"},
        ],
    }
    raw.update(changes)
    return raw


def job(request, *, cost="12.5", state=JobState.APPLIED, cloud=False, types=("video/mp4",)):
    if cloud:
        intent = CloudJobIntent(request, SCOPE, ORIGIN, "model_video")
    else:
        intent = JobIntent(request, SCOPE, ORIGIN, "model", "model_video", "a" * 64, "b" * 64, cost)
    results = tuple(
        StoredResult(ResultAsset(f"asset_{request}result{index}", f"{index}.bin", kind))
        for index, kind in enumerate(types)
    )
    return StoredJob(intent, state, 7, f"job_{request}remote", results)


def upload(task):
    binding = FilmTaskBinding(PRODUCTION, task, "c" * 64, "d" * 64)
    return FilmUploadReference(
        SCOPE, binding, f"upload-request-{task}", 2, f"asset_{task}upload", "e" * 64, "image"
    )


def test_approved_tasks_follow_current_takes_and_parameter_dependencies():
    plan = validate_film_plan(recipe())
    known = {
        "courier-ref",
        "courier-mesh",
        "s01-style-v2",
        "s01-previs-v3",
        "s01-video-v2",
        "score",
        "final-master",
        "rejected-style",
    }
    assert study.approved_task_ids(plan, known) == [
        "courier-mesh",
        "courier-ref",
        "final-master",
        "s01-previs-v3",
        "s01-style-v2",
        "s01-video-v2",
        "score",
    ]
    # Without a filter every current candidate is returned, never a rejected take.
    candidates = study.approved_task_ids(plan, None)
    assert "rejected-style" not in candidates and "previs-master" in candidates


def test_approved_tasks_follow_named_audio_dialogue_and_masters_without_legacy_score():
    raw = recipe(
        audio_tracks=[
            {"id": "bed", "task": "music-v2", "kind": "music", "start": 0, "end": 2},
        ],
        final_master_task="final-master-v2",
    )
    raw["shots"][0]["dialogue"] = {
        "task": "mina-voice",
        "speaker": "Mina",
        "text": "Hold the light.",
        "offset": 0.5,
    }
    raw["tasks"].append(
        {
            "id": "mina-voice",
            "title": "Voice",
            "kind": "model",
            "model": "m",
            "parameters": {"audio": "$voice-ref:1"},
        }
    )
    plan = validate_film_plan(raw)
    selected = study.approved_task_ids(plan, None)
    assert {"music-v2", "mina-voice", "voice-ref", "final-master-v2"} <= set(selected)
    assert "score" not in selected and "final-master" not in selected


def test_a_legacy_review_selects_the_score_task_its_audio_mix_played():
    plan = validate_film_plan(recipe())
    played = [{"id": "score", "task": "theme-v3", "start": 0, "end": 1, "volume": 0.4}] * 2
    score = study.review_score_task(plan, json.dumps(played))
    assert score == "theme-v3"
    selected = study.approved_task_ids(plan, None, score_task_id=score)
    assert "theme-v3" in selected and "score" not in selected
    # A previs review plays no score, and named tracks carry their own tasks.
    assert study.review_score_task(plan, "[]") == "score"
    assert study.review_score_task(validate_film_plan(recipe(audio_tracks=[])), None) == "score"
    other = {"id": "score", "task": "theme-v4", "start": 1, "end": 2, "volume": 0.4}
    for unreadable in (
        None,
        "not json",
        "{}",
        "[1]",
        '[{"id": "score"}]',
        json.dumps([played[0], other]),
        json.dumps([{**other, "task": "../theme"}]),
    ):
        with pytest.raises(ValueError, match="Build the Film review again"):
            study.review_score_task(plan, unreadable)


def test_sanitize_drops_credentials_identities_urls_and_private_identifiers():
    value = {
        "api_secret": "x",
        "Authorization": "Bearer y",
        "refresh-token": "z",
        "projectId": "proj_private",
        "nested": [
            {
                "request_id": "r",
                "keep": "see https://signed.invalid/a?sig=1 and data:image/png;base64,AAA",
            },
            {"prompt": "Use asset_ABCDEFGH12345678 and local-key-0123456789 here"},
            "known-private-value",
        ],
        "max_tokens": 4,
        "id": "asset_kept12345678",
        "reference": "$asset-task",
    }
    result = study.sanitize(value, private={"known-private-value", "local-key-0123456789"})
    assert set(result) == {"nested", "max_tokens", "id", "reference"}
    keep, prompt, exact = result["nested"]
    assert keep == {"keep": "see [URL omitted] and [URL omitted]"}
    assert prompt == {"prompt": "Use [private ID omitted] and [private ID omitted] here"}
    assert exact == study.ID_OMITTED
    # Recipe identifiers and references are kept so the recipe still resolves.
    assert (result["id"], result["reference"]) == ("asset_kept12345678", "$asset-task")
    with pytest.raises(ValueError, match="nesting"):
        nested = current = {}
        for _ in range(5000):
            current["a"] = current = {}
        study.sanitize(nested)


def test_sanitized_recipe_keeps_approved_tasks_and_reloads_without_project_or_secrets():
    raw = recipe()
    original = copy.deepcopy(raw)
    result = study.sanitized_recipe(raw, ["s01-video-v2", "s01-style-v2", "courier-ref"])
    assert raw == original
    assert "project_id" not in result
    assert [task["id"] for task in result["tasks"]] == [
        "s01-video-v2",
        "s01-style-v2",
        "courier-ref",
    ]
    video, style, _ = result["tasks"]
    assert video["parameters"]["prompt"] == "Dawn, see [URL omitted]"
    assert video["parameters"]["referenceImages"] == ["$courier-ref", "$s01-style-v2"]
    assert "apiKey" not in style["parameters"]
    reloaded = validate_film_plan(result)
    assert reloaded["title"] == "Signal At Dawn" and reloaded["project_id"] is None
    assert reloaded["shots"][0]["video_task"] == "s01-video-v2"
    serialized = json.dumps(result)
    assert "private" not in serialized and "signed.invalid" not in serialized


def test_sanitized_recipe_that_would_not_reload_is_refused():
    with pytest.raises(ValueError, match="would not load again"):
        study.sanitized_recipe(recipe(), ["s01-video-v2"], private={"courier-mesh"})


def test_ledger_keeps_costs_and_types_without_service_identifiers():
    plan = validate_film_plan(recipe())
    records = {
        "s01-video-v2": job("video", cost="0.10000000000000001"),
        "s01-style-v2": job("style", cost="2", types=("image/png", "image/png")),
        "s01-previs-v3": job("previs", cloud=True, state=JobState.READY),
    }
    uploads = {"courier-ref": upload("courier-ref")}
    task_ids = ["courier-mesh", "courier-ref", "s01-previs-v3", "s01-style-v2", "s01-video-v2"]
    document = study.ledger(plan, task_ids, records=records, uploads=uploads, private={PRODUCTION})
    rows = {row["task"]: row for row in document["tasks"]}
    assert rows["s01-video-v2"] == {
        "task": "s01-video-v2",
        "title": "Shot one video",
        "kind": "model",
        "model": "model_video",
        "source": "generated",
        "state": "applied",
        "quoted_cost": "0.10000000000000001",
        "result_types": ["video/mp4"],
    }
    assert rows["s01-style-v2"]["result_types"] == ["image/png"]
    assert (rows["s01-previs-v3"]["source"], rows["s01-previs-v3"]["quoted_cost"]) == (
        "selected cloud result",
        None,
    )
    assert rows["courier-ref"]["source"] == "uploaded"
    assert rows["courier-ref"]["result_types"] == ["image"]
    assert rows["courier-mesh"]["source"] == "not saved"
    assert document["quoted_cost_total"] == "2.10000000000000001"
    assert (document["priced_tasks"], document["cost_unit"]) == (2, "CU")
    serialized = json.dumps(document)
    for private in (
        "job_videoremote",
        "asset_videoresult0",
        "upload-request-courier-ref",
        "asset_courier-refupload",
        SCOPE.account_id,
        SCOPE.project_id,
        SCOPE.team_id,
        PRODUCTION,
    ):
        assert private not in serialized, private


def test_documents_build_manifest_guide_and_attribution():
    raw = recipe()
    plan = validate_film_plan(raw)
    scenes = {
        "review": "Signal At Dawn / Final Review",
        "review_kind": "final",
        "timeline": "Film Timeline / Signal At Dawn",
        "shots": ["Film / s01 / Opening"],
        "all": [
            "Film / s01 / Opening",
            "Film Timeline / Signal At Dawn",
            "Signal At Dawn / Final Review",
        ],
    }
    texts = study.documents(
        raw,
        plan,
        task_ids=["s01-video-v2"],
        records={"s01-video-v2": job("video")},
        private={PRODUCTION},
        blend="Signal At Dawn Case Study.blend",
        scenes=scenes,
        frame=1,
        generator="Scenario for Blender 0.9.9",
    )
    assert list(texts) == [
        study.RECIPE_FILE,
        study.LEDGER_FILE,
        study.MANIFEST_FILE,
        study.GUIDE_FILE,
    ]
    manifest = json.loads(texts[study.MANIFEST_FILE])
    assert manifest["format"] == "scenario-film-case-study"
    assert (
        manifest["attribution"] == study.ATTRIBUTION and "Emmanuel de Maistre" in study.ATTRIBUTION
    )
    assert manifest["scenes"] == scenes
    assert manifest["opening"]["scene"] == scenes["review"]
    assert manifest["approved_tasks"] == ["s01-video-v2"]
    assert manifest["continuity_audit"]["visual_verification"] is False
    guide = texts[study.GUIDE_FILE]
    assert "Extract this archive first" in guide
    assert "Signal At Dawn Case Study.blend" in guide and scenes["timeline"] in guide
    assert study.ATTRIBUTION in guide
    for text in texts.values():
        assert PRODUCTION not in text and "signed.invalid" not in text
    # Deterministic JSON text, so identical inputs give identical receipts.
    assert study.encode({"b": 1, "a": "é"}) == '{\n  "a": "é",\n  "b": 1\n}\n'
