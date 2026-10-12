# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Portable Film case-study documents: approved takes, sanitized recipe and ledger.

Adapted from Emmanuel de Maistre's Scenario Studio film_export.py (its case-study
export). The approved-take selection, the credential and URL sanitizer, the bundle
layout and the opening guide follow that source. This first-party adaptation keeps
service identifiers (request, job, asset, upload, project and team IDs), signed
URLs and local paths out of the ledger and every document. It reads no storage,
file or service: the caller supplies scoped saved observations and file receipts.
"""

import copy
import json
import re
from decimal import Decimal

from ..jobs.store import CloudJobIntent, FilmUploadReference, StoredJob
from .film_plan import continuity_audit, identifier, validate_film_plan

SCHEMA_VERSION = 1
FORMAT = "scenario-film-case-study"
RECIPE_FILE = "Film Recipe.json"
LEDGER_FILE = "Production Ledger.json"
MANIFEST_FILE = "Case Study Manifest.json"
GUIDE_FILE = "Open The Case Study.md"
MEDIA_FOLDER = "Media"
URL_OMITTED = "[URL omitted]"
ID_OMITTED = "[private ID omitted]"
ATTRIBUTION = "Bundle layout adapted from Emmanuel de Maistre's Scenario Studio case-study export."
# Keys whose values are credentials or service identities are dropped wherever they appear.
_SECRET_SUFFIXES = (
    "apikey",
    "apisecret",
    "accesskey",
    "privatekey",
    "secret",
    "password",
    "passwd",
    "credential",
    "credentials",
    "authorization",
    "token",
    "cookie",
    "signature",
)
_PRIVATE_KEYS = frozenset(
    {
        "projectid",
        "teamid",
        "accountid",
        "ownerid",
        "userid",
        "organizationid",
        "orgid",
        "workspaceid",
        "requestid",
        "jobid",
        "remotejobid",
        "inferenceid",
        "assetid",
        "assetids",
        "uploadid",
        "uploadids",
        "uploadrequestid",
        "applicationid",
    }
)
# Recipe identifiers are kept verbatim so the sanitized recipe still reloads.
_IDENTIFIER_KEYS = frozenset({"id", "hero", "reference", "mesh", "materialfrom"})
_URL = re.compile(r"(?i)\b(?:[a-z][a-z0-9+.-]{0,31}://|data:[^\s,]{0,256},)\S*")
_SERVICE_ID = re.compile(
    r"\b(?:asset|job|upload|inference|request|proj|project|team|org|user|workspace)"
    r"_[A-Za-z0-9]{8,}\b"
)


def _compact(key):
    return re.sub(r"[^a-z0-9]", "", str(key).lower())


def _private_key(compact):
    return compact in _PRIVATE_KEYS or compact.endswith(_SECRET_SUFFIXES)


def _markers(private):
    """Exact private values, and the longer ones also as substrings."""
    exact = frozenset(value for value in private if isinstance(value, str) and value)
    return exact, tuple(sorted((value for value in exact if len(value) >= 8), key=len))[::-1]


def _clean(text, exact, embedded, *, identifier):
    if text in exact:
        return ID_OMITTED
    text = _URL.sub(URL_OMITTED, text)
    if not identifier and not text.startswith("$"):
        text = _SERVICE_ID.sub(ID_OMITTED, text)
    for marker in embedded:
        text = text.replace(marker, ID_OMITTED)
    return text


def _sanitize(value, exact, embedded, compact=""):
    if isinstance(value, dict):
        result = {}
        for key, item in value.items():
            name = _compact(key)
            if _private_key(name):
                continue
            result[key] = _sanitize(item, exact, embedded, name)
        return result
    if isinstance(value, (list, tuple)):
        return [_sanitize(item, exact, embedded, compact) for item in value]
    if isinstance(value, str):
        identifier = compact in _IDENTIFIER_KEYS or compact.endswith(("task", "tasks"))
        return _clean(value, exact, embedded, identifier=identifier)
    return copy.deepcopy(value)


def sanitize(value, *, private=()):
    """Drop credential and identity fields, omit URLs and known private identifiers.

    ``private`` names exact identifiers from the caller's scoped saved jobs and
    uploads. Scenario-shaped service identifiers inside free text are omitted too;
    recipe identifiers (task, shot and hero names) are kept so references resolve.
    """
    exact, embedded = _markers(private)
    try:
        return _sanitize(value, exact, embedded)
    except RecursionError:
        raise ValueError("Film case-study data nesting is too deep") from None


def _references(value):
    found = set()
    if isinstance(value, dict):
        for item in value.values():
            found.update(_references(item))
    elif isinstance(value, list):
        for item in value:
            found.update(_references(item))
    elif isinstance(value, str) and value.startswith("$"):
        found.add(value[1:].split(":", 1)[0])
    return found


def review_score_task(plan, audio_mix):
    """Return the score task a built review played, for ``approved_task_ids``.

    A plan without ``audio_tracks`` loops one score from the task chosen when the
    review was built; the review records it in its audio mix (``scenario_audio_mix``).
    Named tracks carry their own tasks and a previs review plays no score, so both
    keep the default. An unreadable mix refuses rather than guessing the task.
    """
    if "audio_tracks" in plan:
        return "score"
    try:
        mix = json.loads(audio_mix)
        if not isinstance(mix, list):
            raise ValueError("unreadable")
        tasks = {entry["task"] for entry in mix if entry["id"] == "score"}
        (task,) = tasks or {"score"}
        return identifier(task, "Score task")
    except (TypeError, ValueError, KeyError, RecursionError):
        raise ValueError("Build the Film review again; its audio mix is unreadable") from None


def approved_task_ids(plan, known, *, score_task_id="score"):
    """Select the current named takes and their explicit parameter dependencies.

    ``plan`` is a validated Film plan. Only identifiers in ``known`` (recipe tasks
    or saved observations) are returned, sorted; ``None`` returns every candidate.
    """
    selected = {plan["final_master_task"], plan["previs_master_task"]}
    if "audio_tracks" not in plan:
        selected.add(score_task_id)
    selected.update(track["task"] for track in plan.get("audio_tracks", []))
    for hero in plan.get("heroes", {}).values():
        selected.update(hero.get(key) for key in ("reference", "mesh", "material_from"))
    for shot in plan["shots"]:
        selected.update((shot["style_task"], shot["previs_task"], shot["video_task"]))
        if shot.get("dialogue"):
            selected.add(shot["dialogue"]["task"])
    selected.discard(None)
    tasks = {task["id"]: task for task in plan["tasks"]}
    pending = list(selected)
    while pending:
        task = tasks.get(pending.pop())
        if task is None:
            continue
        for dependency in _references(task.get("parameters", {})) - selected:
            selected.add(dependency)
            pending.append(dependency)
    return sorted(selected if known is None else selected & set(known))


def sanitized_recipe(raw, task_ids, *, private=()):
    """Return the recipe with only approved tasks, no project, credentials or URLs.

    The result must still validate as a Film recipe, so it can be loaded again.
    """
    recipe = copy.deepcopy(raw)
    if not isinstance(recipe, dict):
        raise ValueError("Load a valid Film recipe first")
    recipe.pop("project_id", None)
    selected = set(task_ids)
    recipe["tasks"] = [
        task
        for task in recipe.get("tasks", [])
        if isinstance(task, dict) and task.get("id") in selected
    ]
    result = sanitize(recipe, private=private)
    try:
        validate_film_plan(result)
    except ValueError:
        raise ValueError(
            "The sanitized Film recipe would not load again; rename recipe values that"
            " look like private service identifiers"
        ) from None
    return result


def _exact_cost(value):
    if value is None:
        return None
    cost = Decimal(value)
    if not cost.is_finite() or cost < 0:
        raise ValueError("Saved quote costs must be exact finite decimals")
    return cost


def ledger(plan, task_ids, *, records=None, uploads=None, private=()):
    """Summarize approved tasks without service identifiers, URLs or local paths.

    ``records`` maps task IDs to this scope's saved jobs and ``uploads`` to saved
    upload associations. A row keeps the recipe title, kind and model, how the take
    was obtained, its saved state, the exact quoted cost and result media types.
    """
    records, uploads = dict(records or {}), dict(uploads or {})
    tasks = {task["id"]: task for task in plan["tasks"]}
    rows, total, priced = [], Decimal(0), 0
    for task_id in task_ids:
        task = tasks.get(task_id, {})
        record, upload = records.get(task_id), uploads.get(task_id)
        row = {
            "task": task_id,
            "title": task.get("title"),
            "kind": task.get("kind"),
            "model": task.get("model") if task.get("kind") == "model" else None,
            "source": "not saved",
            "state": None,
            "quoted_cost": None,
            "result_types": [],
        }
        if isinstance(record, StoredJob):
            cloud = isinstance(record.intent, CloudJobIntent)
            row["source"] = "selected cloud result" if cloud else "generated"
            row["state"] = record.state.value
            cost = _exact_cost(record.intent.quote_cost)
            row["quoted_cost"] = None if cost is None else format(cost, "f")
            row["result_types"] = sorted({item.asset.media_type for item in record.results})
            if cost is not None:
                total += cost
                priced += 1
        elif isinstance(upload, FilmUploadReference):
            row.update(source="uploaded", state="associated", result_types=[upload.kind])
        rows.append(row)
    document = {
        "schema_version": SCHEMA_VERSION,
        "title": plan["title"],
        "cost_unit": "CU",
        "quoted_cost_total": format(total, "f") if priced else None,
        "priced_tasks": priced,
        "tasks": rows,
        "omitted": [
            "credentials",
            "signed and other URLs",
            "request, job, asset, upload, project and team identifiers",
            "local file paths",
            "generation parameters (see the recipe)",
        ],
    }
    return sanitize(document, private=private)


def _guide(title, blend, scenes, frame):
    review, timeline = scenes["review"], scenes.get("timeline")
    lines = [
        f"# Open {title}",
        "",
        (
            f"Extract this archive first, then keep `{blend}` beside its `{MEDIA_FOLDER}` folder"
            " when moving the bundle. Movie, sound, image and font files use relative paths;"
            " packed textures stay inside the Blender file."
        ),
        "",
        (
            f"This curated Blender data library contains {len(scenes['all'])} scenes and does not"
            " store a workspace. Blender may warn `Library file, loading empty scene` or show a"
            " default viewport."
        ),
        "",
        f"1. Open `{blend}` and use the scene selector to choose `{review}`.",
        "2. Change the large area's editor type to **Video Sequencer**.",
        (
            f"3. In the Video Sequencer header's own scene selector, choose `{review}`."
            " If it shows **New**, use its scene dropdown to select the existing review."
            " The Video Sequencer has its own scene selection."
        ),
        (
            "4. Set the view to **Sequencer & Preview**. Hover over the strip timeline and press"
            " **Home** to frame all strips."
        ),
        f"5. Go to frame **{frame}** and play the review.",
        "",
    ]
    if timeline:
        lines += [
            (
                f"For editable native shot timing, select `{timeline}`. Select any shot listed in"
                f" `{MANIFEST_FILE}` to inspect its geometry and camera."
            ),
            "",
        ]
    lines += [
        (
            f"`{RECIPE_FILE}` is the approved recipe without its project, credentials or URLs."
            f" `{LEDGER_FILE}` lists each approved take, how it was made and its quoted cost,"
            " without service identifiers. Blender keeps unused bytes of earlier settings inside"
            " some fields of a .blend file; review the bundle before publishing it widely."
        ),
        "",
        ATTRIBUTION,
        "",
    ]
    return "\n".join(lines)


def documents(
    raw,
    plan,
    *,
    task_ids,
    records=None,
    uploads=None,
    private=(),
    blend,
    scenes,
    frame,
    generator,
):
    """Build the sanitized recipe, ledger, manifest base and opening guide.

    ``scenes`` holds ``review``, ``review_kind``, ``timeline``, ``shots`` and ``all``
    scene names. The worker completes the manifest with file receipts.
    """
    recipe = sanitized_recipe(raw, task_ids, private=private)
    rows = ledger(plan, task_ids, records=records, uploads=uploads, private=private)
    manifest = sanitize(
        {
            "schema_version": SCHEMA_VERSION,
            "format": FORMAT,
            "generator": generator,
            "attribution": ATTRIBUTION,
            "title": plan["title"],
            "fps": plan["fps"],
            "duration": plan["duration"],
            "scenes": scenes,
            "approved_tasks": list(task_ids),
            "continuity_audit": continuity_audit(plan),
            "documents": {
                "recipe": RECIPE_FILE,
                "ledger": LEDGER_FILE,
                "guide": GUIDE_FILE,
            },
            "opening": {
                "file_kind": "blender_data_library",
                "scene": scenes["review"],
                "sequencer_scene": scenes["review"],
                "editor": "Video Sequencer",
                "view": "Sequencer & Preview",
                "frame_all_shortcut": "Home over the strip timeline",
                "frame": frame,
                "guide": GUIDE_FILE,
            },
        },
        private=private,
    )
    guide = sanitize(_guide(plan["title"], blend, scenes, frame), private=private)
    return {
        RECIPE_FILE: encode(recipe),
        LEDGER_FILE: encode(rows),
        MANIFEST_FILE: encode(manifest),
        GUIDE_FILE: guide,
    }


def encode(value):
    """Readable, deterministic JSON text for one bundle document."""
    return json.dumps(value, indent=2, ensure_ascii=False, sort_keys=True, allow_nan=False) + "\n"
