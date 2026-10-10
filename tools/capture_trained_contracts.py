#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Capture sanitized trained-model REST contracts with reads and dryRun=true quotes only.

Usage: uv run --locked --env-file .env.local python tools/capture_trained_contracts.py

Uses the explicit test credential pair and optional project from the process
environment, through the shared SDK adapter. It never submits a generation and
never sends ipDetection, which is charged even with dryRun. Private records are
read but never written: only their REST types and route outcomes are recorded.
"""

import argparse
import copy
import datetime as dt
import json
import os
import pathlib
import re
import shutil
import sys
import tempfile
from importlib.metadata import version

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scenario.core.api.sdk_adapter import (  # noqa: E402
    AdapterError,
    AdapterUnavailable,
    Credentials,
    SDKAdapter,
    model_identifiers,
)
from tools.dev_config import live_settings  # noqa: E402
from tools.record_fixtures import scrub  # noqa: E402

FIXTURES = ROOT / "tests" / "fixtures"
OUTPUT = pathlib.PurePosixPath("models/trained")

# Public base models whose REST detail declares uiConfig.lorasComponent. The
# curated Z-Image and Qwen Image Edit 2511 lane models are included although no
# public LoRA of their types exists, so their declared slots stay pinned too.
BASE_IDS = (
    "model_bfl-flux-1-dev",
    "model_bfl-flux-2-dev",
    "model_flux-kontext-editing",
    "model_qwen-image-edit-2511",
    "model_z-image",
)
# Public Scenario LoRAs and compositions, by role. Each must be in the public list.
PUBLIC_TRAINED = {
    "flux1_lora_a": "model_YQrES2iPys22nYwh3YhVfMh8",
    "flux1_lora_b": "model_2taP2G9BJL1Rw8t81NwiXGZA",
    "flux1_composition": "model_7oiHtKChpcLpy4jq3Jq2BG8n",
    "flux1_composition_unlisted_concept": "model_MYqiLuoTmgR2F1hzXPX3BBgY",
    "flux2_dev_lora": "model_CMUu7BjxV8TpdhG3FKoxZRxC",
    "kontext_lora": "model_hFh8M6nQbqGFSKJdP536GXhE",
}
PROMPT = "a small wooden cabin in a snowy forest"
MISSING_MODEL = "model_FIXTUREMISSING0000000000"
REFERENCE = "@reference_image"
REFERENCE_PLACEHOLDER = "asset_FIXTUREREFERENCE00000000"
ROUTES = ("stack", "model_id", "composition", "direct")
# Accepted base-model routes are quoted again through SDKAdapter.estimate_model.
QUOTED_ROUTES = ("stack", "model_id", "composition")
TRAINED_FIELDS = (
    "id",
    "type",
    "privacy",
    "status",
    "custom",
    "capabilities",
    "compliantModelIds",
    "concepts",
    "parentModelId",
)
CONCEPT_FIELDS = ("modelId", "scale", "modelEpoch")
# Random Scenario identifiers. Readable slugs such as model_bfl-flux-1-dev,
# schema words such as model_array and FIXTURE placeholders are not matched.
_RANDOM_ID = re.compile(r"\b(?:model|asset)_(?!FIXTURE)[A-Za-z0-9]{16,}\b")
_FLUX1 = "model_bfl-flux-1-dev"
_KONTEXT = "model_flux-kontext-editing"

# (case, route, target, body). Values starting with "@" name PUBLIC_TRAINED roles
# or the selected scope's reference image. "check" cases probe server validation;
# "base" cases quote the base model alone for comparison.
CASES = (
    ("base_only", "base", _FLUX1, {"prompt": PROMPT}),
    (
        "stack_one",
        "stack",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a"], "lorasScale": [0.8]},
    ),
    (
        "stack_two",
        "stack",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a", "@flux1_lora_b"], "lorasScale": [0.8, 0.5]},
    ),
    (
        "stack_flux2",
        "stack",
        "model_bfl-flux-2-dev",
        {"prompt": PROMPT, "loras": ["@flux2_dev_lora"], "lorasScale": [1.0]},
    ),
    (
        "kontext_reference_only",
        "base",
        _KONTEXT,
        {"prompt": PROMPT, "referenceImages": [REFERENCE]},
    ),
    (
        "stack_kontext",
        "stack",
        _KONTEXT,
        {
            "prompt": PROMPT,
            "referenceImages": [REFERENCE],
            "loras": ["@kontext_lora"],
            "lorasScale": [1.0],
        },
    ),
    ("model_id_lora", "model_id", _FLUX1, {"prompt": PROMPT, "modelId": "@flux1_lora_a"}),
    ("composition", "composition", _FLUX1, {"prompt": PROMPT, "modelId": "@flux1_composition"}),
    (
        "composition_unlisted_concept",
        "composition",
        _FLUX1,
        {"prompt": PROMPT, "modelId": "@flux1_composition_unlisted_concept"},
    ),
    (
        "composition_with_loras",
        "composition",
        _FLUX1,
        {
            "prompt": PROMPT,
            "modelId": "@flux1_composition",
            "loras": ["@flux1_lora_a"],
            "lorasScale": [0.5],
        },
    ),
    ("direct_lora", "direct", "@flux1_lora_a", {"prompt": PROMPT, "aspectRatio": "1:1"}),
    (
        "direct_composition",
        "direct",
        "@flux1_composition",
        {"prompt": PROMPT, "aspectRatio": "1:1"},
    ),
    ("direct_flux2_lora", "direct", "@flux2_dev_lora", {"prompt": PROMPT, "aspectRatio": "1:1"}),
    ("check_without_scale", "check", _FLUX1, {"prompt": PROMPT, "loras": ["@flux1_lora_a"]}),
    (
        "check_scale_count_mismatch",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a", "@flux1_lora_b"], "lorasScale": [0.8]},
    ),
    (
        "check_scale_below_min",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a"], "lorasScale": [-0.5]},
    ),
    (
        "check_scale_above_max",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a"], "lorasScale": [3.0]},
    ),
    (
        "check_over_item_limit",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_lora_a"] * 7, "lorasScale": [0.5] * 7},
    ),
    (
        "check_incompatible_type",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux2_dev_lora"], "lorasScale": [0.8]},
    ),
    (
        "check_composition_in_loras",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": ["@flux1_composition"], "lorasScale": [0.8]},
    ),
    (
        "check_unknown_model",
        "check",
        _FLUX1,
        {"prompt": PROMPT, "loras": [MISSING_MODEL], "lorasScale": [0.8]},
    ),
)


class _Reply:
    """A raw-response stand-in, so the adapter guard can return a service reply."""

    def __init__(self, status, body):
        self._data = json.dumps({"status": status, "body": body}).encode()

    def read(self):
        return self._data


def dry_run(client, model_id, body):
    """Send POST /generate/custom/{model_id}?dryRun=true once; return (status, reply).

    The call goes through the adapter's request guard (selected project, online
    and closed checks, sanitized connection errors) and its configured zero-retry
    SDK client. It issues no Estimate, so nothing captured here can be submitted.
    Client errors (4xx) are recorded as evidence; any other failure stops the run.
    """
    from scenario_sdk import APIStatusError

    run = client._sdk.generate.with_raw_response.run_model

    def call(identifier, **options):
        if options.get("dry_run") != "true" or "ip_detection" in options:
            raise ValueError("Contract capture sends dry runs only")
        try:
            response = run(identifier, **options)
        except APIStatusError as error:
            if not 400 <= error.status_code < 500:
                raise
            return _Reply(error.status_code, error.body)
        try:
            reply = json.loads(response.read())
        except (ValueError, UnicodeError):
            raise AdapterError("Scenario returned invalid JSON") from None
        return _Reply(response.status_code, reply)

    (identifier,) = model_identifiers([model_id])
    result = json.loads(client._request(call, identifier, body=body, dry_run="true"))
    return result["status"], result["body"]


class Scrubber:
    """Replace private and random non-public identifiers with stable placeholders.

    Model IDs from the captured public list, the captured bases and the fixed
    synthetic IDs stay readable. Known private identifiers (records of the
    selected scope, its assets and the project) are replaced wherever they
    occur, and so is any other random model or asset identifier.
    """

    def __init__(self, public_ids, private_values=()):
        self.public = set(public_ids) | set(BASE_IDS) | {MISSING_MODEL, REFERENCE_PLACEHOLDER}
        self.private = {value for value in private_values if isinstance(value, str) and value}
        self._placeholders = {}

    def placeholder(self, value):
        if value not in self._placeholders:
            kind = value.split("_", 1)[0] if value.startswith(("model_", "asset_")) else "private"
            count = sum(1 for key in self._placeholders.values() if key.startswith(f"{kind}_"))
            self._placeholders[value] = f"{kind}_FIXTURE{count + 1:016d}"
        return self._placeholders[value]

    def text(self, value):
        if value in self.public:
            return value
        # Replace longer values first so a value containing another is not split;
        # the secondary key keeps placeholder numbering stable between runs.
        for private in sorted(self.private, key=lambda item: (-len(item), item)):
            if private in value:
                value = value.replace(private, self.placeholder(private))
        return _RANDOM_ID.sub(
            lambda match: (
                match.group(0)
                if match.group(0) in self.public
                else self.placeholder(match.group(0))
            ),
            value,
        )

    def data(self, value):
        if isinstance(value, dict):
            return {key: self.data(item) for key, item in value.items()}
        if isinstance(value, list):
            return [self.data(item) for item in value]
        return self.text(value) if isinstance(value, str) else value

    def leaked(self, text):
        return any(value in text for value in self.private)


def _carries(record):
    inputs = record.get("inputs")
    return {
        "inputs": isinstance(inputs, list) and bool(inputs),
        "uiConfig": isinstance(record.get("uiConfig"), dict),
    }


def _rows_carry(rows):
    return {
        "inputs": any(_carries(row)["inputs"] for row in rows),
        "uiConfig": any(_carries(row)["uiConfig"] for row in rows),
    }


def project_trained(record, scrubber):
    """Keep the routing fields of a public trained record, without training data.

    Training parameters can hold signed storage URLs and internal paths, and
    parent or concept models may not be public, so those IDs are scrubbed.
    """
    projection = {key: copy.deepcopy(record[key]) for key in TRAINED_FIELDS if key in record}
    if isinstance(projection.get("concepts"), list):
        projection["concepts"] = [
            {key: concept[key] for key in CONCEPT_FIELDS if key in concept}
            if isinstance(concept, dict)
            else concept
            for concept in projection["concepts"]
        ]
    projection["observedFields"] = sorted(record)
    return scrubber.data(projection)


def lora_component(record):
    """The base's lorasComponent and its inputs by name; AdapterError if absent."""
    component = (record.get("uiConfig") or {}).get("lorasComponent")
    if not isinstance(component, dict):
        raise AdapterError("A captured base model no longer declares lorasComponent")
    inputs = record.get("inputs") or []
    return component, {field.get("name"): field for field in inputs if isinstance(field, dict)}


def _resolve(value, reference):
    if isinstance(value, dict):
        return {key: _resolve(item, reference) for key, item in value.items()}
    if isinstance(value, list):
        return [_resolve(item, reference) for item in value]
    if value == REFERENCE:
        return reference
    if isinstance(value, str) and value.startswith("@"):
        return PUBLIC_TRAINED[value[1:]]
    return value


def _evidence(status, reply):
    """Keep the service's reply: the exact quote fields or the rejection reason."""
    if 200 <= status < 300:
        return reply
    if isinstance(reply, dict) and isinstance(reply.get("reason"), str):
        return {"reason": reply["reason"]}
    return {"fields": sorted(reply) if isinstance(reply, dict) else []}


def adapter_quote(client, base, parameters):
    """Quote the same selection through the production path, `estimate_model`.

    It applies the shared form preparation (schema defaults and validation)
    and the adapter's exact dry run. The Estimate is never submitted, and
    closing the client discards it.
    """
    try:
        estimate = client.estimate_model(base, parameters)
    except (AdapterError, ValueError) as error:
        return {"rejected": str(error)}
    return {
        "addedDefaults": sorted(set(estimate.payload) - set(parameters)),
        "reply": json.loads(estimate.response_json),
    }


def _private_evidence(status, reply):
    """Status and reply field names only: a reason could name a private record."""
    return {"status": status, "fields": sorted(reply) if isinstance(reply, dict) else []}


def _private_route(bases, kind_type):
    """The first captured base whose lorasComponent accepts this type, and how."""
    for base_id in BASE_IDS:
        component, fields = lora_component(bases[base_id])
        model_id_input = fields.get(component.get("modelIdInput"), {})
        model_input = fields.get(component.get("modelInput"), {})
        if kind_type in (model_id_input.get("modelTypes") or ()):
            return base_id, "model_id", component["modelIdInput"], None
        if kind_type in (model_input.get("modelTypes") or ()):
            return base_id, "stack", component["modelInput"], component["scaleInput"]
    return None


def _required(record):
    return {
        field.get("name")
        for field in record.get("inputs") or []
        if isinstance(field, dict)
        and isinstance(field.get("required"), dict)
        and field["required"].get("always") is True
    }


def private_observations(client, rows, bases, reference):
    """Read and quote one private trained record per REST type; record no identity."""
    if not rows:
        return {"present": False}
    first = {}
    for row in rows:
        kind_type = row.get("type")
        if isinstance(kind_type, str) and kind_type not in first:
            first[kind_type] = row
    types = {}
    for kind_type, row in sorted(first.items()):
        detail = client.model(row["id"])
        entry = {"detailCarries": _carries(detail), "custom": detail.get("custom") is True}
        status, reply = dry_run(client, row["id"], {"prompt": PROMPT, "aspectRatio": "1:1"})
        entry["direct"] = _private_evidence(status, reply)
        route = _private_route(bases, kind_type)
        if route is None:
            entry["viaBase"] = {"skipped": "No captured base declares this type"}
            types[kind_type] = entry
            continue
        base_id, route_kind, model_input, scale_input = route
        body = {"prompt": PROMPT}
        missing = _required(bases[base_id]) - {"prompt"}
        if "referenceImages" in missing and reference:
            body["referenceImages"] = [reference]
            missing.discard("referenceImages")
        if missing:
            entry["viaBase"] = {"base": base_id, "skipped": "The base needs other inputs"}
        else:
            if route_kind == "model_id":
                body[model_input] = row["id"]
            else:
                body[model_input] = [row["id"]]
                body[scale_input] = [0.8]
            status, reply = dry_run(client, base_id, body)
            entry["viaBase"] = {
                "base": base_id,
                "route": route_kind,
                **_private_evidence(status, reply),
            }
        types[kind_type] = entry
    return {"present": True, "listRowsCarry": _rows_carry(rows), "types": types}


def decide(cases):
    """Route kinds from dry-run statuses; dry-run acceptance is not a paid run."""
    decisions = {}
    for route in ROUTES:
        selected = [case for case in cases if case["route"] == route]
        statuses = [case["status"] for case in selected if case.get("status") is not None]
        accepted = [200 <= status < 300 for status in statuses]
        if not statuses:
            result = "not captured"
        elif all(accepted):
            result = "accepted"
        elif any(accepted):
            result = "mixed"
        else:
            result = "rejected"
        decisions[route] = {"result": result, "cases": [case["case"] for case in selected]}
    return decisions


def concept_reads(client, trained, public):
    """Read each composition concept by ID; record readability and type, never the ID."""
    result = {}
    for role, record in sorted(trained.items()):
        if not str(record.get("type")).endswith("-composition"):
            continue
        rows = []
        for concept in record.get("concepts") or ():
            model_id = concept.get("modelId") if isinstance(concept, dict) else None
            entry = {"listedPublic": model_id in public}
            try:
                detail = client.model(model_id)
            except AdapterUnavailable as error:
                entry.update(readable=False, status=error.status)
            else:
                entry.update(readable=True, type=detail.get("type"), privacy=detail.get("privacy"))
            rows.append(entry)
        result[role] = rows
    return result


def _type_counts(rows):
    counts = {}
    for row in rows:
        key = row.get("type") if isinstance(row.get("type"), str) else "<not a string>"
        counts[key] = counts.get(key, 0) + 1
    return dict(sorted(counts.items()))


def capture(client, *, project_override):
    """Run every read and dry run, then return {relative path: JSON} to publish."""
    private_rows = client.models(privacy="private")
    public_rows = client.models(privacy="public")
    public = {row["id"]: row for row in public_rows}
    for model_id in (*BASE_IDS, *PUBLIC_TRAINED.values()):
        if public.get(model_id, {}).get("privacy") != "public":
            raise AdapterError("A captured model is no longer in the public catalog")
    scope_page = client.asset_page(page_size=20)
    images = [
        asset["id"]
        for asset in scope_page["assets"]
        if str(asset.get("mimeType", "")).startswith("image/")
    ]
    reference = images[0] if images else None
    # Names are never written, and replacing them as text could alter schemas,
    # so only identifiers are registered as private values.
    private_values = [project_override] if isinstance(project_override, str) else []
    private_values += [asset["id"] for asset in scope_page["assets"]]
    # A private copy of a public model names a public parent, which stays
    # readable; registering it would make the leak check refuse the capture.
    for row in private_rows:
        private_values += [
            value for value in (row["id"], row.get("parentModelId")) if value not in public
        ]
    scrubber = Scrubber(public, private_values)

    bases = {model_id: client.model(model_id) for model_id in BASE_IDS}
    trained = {role: client.model(model_id) for role, model_id in PUBLIC_TRAINED.items()}
    for expected, record in [*bases.items(), *((PUBLIC_TRAINED[r], m) for r, m in trained.items())]:
        if record.get("id") != expected:
            raise AdapterError("Scenario returned a different model identity")
    for record in bases.values():
        lora_component(record)
    bulk_ids = [*BASE_IDS, *PUBLIC_TRAINED.values()]
    bulk = client.models_bulk(bulk_ids)
    concepts = concept_reads(client, trained, public)

    cases = []
    for name, route, target, body in CASES:
        entry = {
            "case": name,
            "route": route,
            "target": _resolve(target, None),
            "body": _resolve(body, REFERENCE_PLACEHOLDER),
        }
        if reference is None and REFERENCE in json.dumps(body):
            entry.update(status=None, skipped="No image asset in the selected scope")
        else:
            status, reply = dry_run(client, entry["target"], _resolve(body, reference))
            entry.update(status=status, reply=_evidence(status, reply))
            if route in QUOTED_ROUTES and 200 <= status < 300:
                base = bases[entry["target"]]
                entry["adapterQuote"] = adapter_quote(client, base, _resolve(body, reference))
        cases.append(entry)

    files = {}
    for model_id, record in bases.items():
        files[str(OUTPUT / "bases" / f"{model_id}.json")] = scrub(scrubber.data({"model": record}))
    for record in sorted(trained.values(), key=lambda record: record["id"]):
        files[str(OUTPUT / "public" / f"{record['id']}.json")] = scrub(
            {"model": project_trained(record, scrubber)}
        )
    contracts = {
        "recordedAt": dt.datetime.now(dt.UTC).date().isoformat(),
        "recorder": "tools/capture_trained_contracts.py",
        "sdkVersion": version("scenario-sdk"),
        "scope": {
            "credentials": "explicit API-key pair",
            "projectOverride": isinstance(project_override, str),
        },
        "scrub": (
            "Account fields use placeholders and signed URLs are replaced. Private records are "
            "never written; private and random non-public identifiers use placeholders."
        ),
        "catalog": {
            "privateTrained": private_observations(client, private_rows, bases, reference),
            "public": {
                "types": _type_counts(public_rows),
                "listRowsCarry": _rows_carry(public_rows),
            },
            "bulk": {
                "requested": len(bulk_ids),
                "returned": len(bulk),
                "rowsCarry": _rows_carry(list(bulk.values())),
            },
            "trainedDetailsCarry": {
                role: _carries(record) for role, record in sorted(trained.items())
            },
            "compositionConcepts": concepts,
        },
        "publicTrained": dict(sorted(PUBLIC_TRAINED.items())),
        "routes": decide(cases),
        "dryRuns": cases,
    }
    files[str(OUTPUT / "contracts.json")] = scrub(scrubber.data(contracts))
    if scrubber.leaked(json.dumps(files)):
        raise ValueError("A private value survived scrubbing; nothing was written")
    return files


class RestoreFailed(OSError):
    """The previous fixtures could not be moved back; they stay at `kept`."""

    def __init__(self, kept):
        super().__init__("The previous trained-model fixtures could not be restored")
        self.kept = kept


def publish(files, fixtures=None):
    """Replace the whole trained fixture directory only after every file is staged.

    A failed replacement moves the previous directory back. If that also fails,
    the staging directory is kept, since it then holds the only previous copy.
    """
    fixtures = FIXTURES if fixtures is None else fixtures
    target = fixtures / OUTPUT
    if target.is_symlink() or not target.resolve().is_relative_to(fixtures.resolve()):
        raise ValueError("Fixture output must stay inside its directory")
    target.parent.mkdir(parents=True, exist_ok=True)
    staged = pathlib.Path(tempfile.mkdtemp(prefix=".recording-", dir=fixtures))
    keep = False
    try:
        for relative, data in files.items():
            path = staged / "new" / pathlib.PurePosixPath(relative).relative_to(OUTPUT)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(json.dumps(data, indent=1) + "\n", encoding="utf-8")
        if target.exists():
            os.replace(target, staged / "previous")
        try:
            os.replace(staged / "new", target)
        except OSError:
            if (staged / "previous").exists():
                try:
                    os.replace(staged / "previous", target)
                except OSError as error:
                    keep = True
                    raise RestoreFailed(staged / "previous") from error
            raise
    finally:
        if not keep:
            shutil.rmtree(staged)


def main(argv=None):
    parser = argparse.ArgumentParser(
        description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.parse_args(argv)
    settings = live_settings()
    credentials = Credentials(settings.credentials.key, settings.credentials.secret)
    try:
        # This standalone, explicitly invoked tool has no Blender permission state.
        with SDKAdapter(credentials, project_id=settings.project_id, online=lambda: True) as client:
            files = capture(client, project_override=settings.project_id)
        publish(files)
    except (AdapterError, ValueError):
        # Keep response, record and configuration text out of the terminal.
        print("Trained-model contract capture failed; no fixture was changed.", file=sys.stderr)
        return 1
    except RestoreFailed as error:
        print(
            "Could not restore the previous trained-model fixtures; "
            f"they are kept in {error.kept}.",
            file=sys.stderr,
        )
        return 1
    except OSError:
        print("Could not write trained-model fixtures; inspect the diff.", file=sys.stderr)
        return 1
    for route, decision in files[str(OUTPUT / "contracts.json")]["routes"].items():
        print(f"{route}: {decision['result']}")
    for relative in sorted(files):
        print("saved", relative)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
