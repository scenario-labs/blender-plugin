# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Quote, approve and recover model checks through shared SDK jobs."""

import argparse
import hashlib
import json
import os
import re
import tempfile
import time
import uuid
from collections import Counter
from dataclasses import asdict
from decimal import Decimal
from pathlib import Path

from scenario.core.api.catalog import ModelRecord
from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.result_metadata import ORIGINAL_MEDIA_TYPES
from scenario.core.jobs.results import ResultError
from scenario.core.jobs.store import JobOrigin, JobState, StoreError
from scenario.core.jobs.transfers import ResultDownloader, StoragePolicy
from scenario.core.scene import panorama_contract
from scenario.core.scene.panorama import MAX_FILE_BYTES, PanoramaError, inspect_panorama
from scenario.core.schema.params import parse_schema, validate
from tools.dev_config import live_settings

RESULT_KINDS = ("image", "material", "video", "model", "audio", "panorama", "hdri")
# Lowercase labels without paths: suite case names and saved run names.
RUN_NAME = re.compile(r"[a-z][a-z0-9_-]{0,39}")
# {"$panorama": "RUN"} names a completed run whose saved 360 result fills a
# contract input that takes a saved panorama, as the Environment lane requires.
PANORAMA_REFERENCE = "$panorama"
# Quotes of Environment lane contract models keep their verified references.
CONTRACT_QUOTE = 4
FINISHED = frozenset({JobState.READY, JobState.APPLY_FAILED, JobState.APPLIED})
STORAGE_HOSTS = frozenset({"cdn.cloud.scenario.com", "cdn.scenario.com"})
# Patina's selectable maps use these input names. Smoothness is the inverse
# representation supported by the shared material application contract.
MATERIAL_MAP_ROLES = {
    "basecolor": {"albedo"},
    "normal": {"normal"},
    "roughness": {"roughness", "smoothness"},
    "metalness": {"metallic"},
    "height": {"height"},
}


class SmokeError(RuntimeError):
    """Static, public-safe failure with an explicit process outcome."""

    def __init__(self, message, code=2):
        super().__init__(message)
        self.code = code


def decimal_cost(value):
    if not isinstance(value, str) or not re.fullmatch(r"[0-9]{1,64}(?:\.[0-9]{1,64})?", value):
        raise argparse.ArgumentTypeError("Use a finite nonnegative decimal CU value")
    return Decimal(value)


def digest(data):
    return hashlib.sha256(data).hexdigest()


def read_bytes(path):
    if path.is_symlink() or not path.is_file() or path.stat().st_size > 1024 * 1024:
        raise SmokeError("Use a regular JSON file of at most 1 MiB")
    return path.read_bytes()


def json_bytes(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def sync_directory(root):
    # POSIX directory fsync retains newly created names across power loss. On
    # Windows the SQLite durable claim remains the paid-dispatch authority.
    if os.name == "posix":
        descriptor = os.open(root, os.O_RDONLY)
        try:
            os.fsync(descriptor)
        finally:
            os.close(descriptor)


def create_file(path, data):
    # Windows os.open defaults to text mode and would write LF as CRLF, so a
    # printed approval digest of these bytes would never match the saved record.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())
    sync_directory(path.parent)


def report(root, store, result_kind):
    value = {"schema_version": 2, "result_kind": result_kind, "jobs": []}
    for record in store.records():
        value["jobs"].append(
            {
                "state": record.state.value,
                "quote_cost": record.intent.quote_cost,
                "payload_sha256": record.intent.payload_sha256,
                "results": [
                    {"size": item.receipt.size, "sha256": item.receipt.sha256}
                    for item in record.results
                    if item.receipt is not None
                ],
            }
        )
    descriptor, temporary = tempfile.mkstemp(prefix=".report-", dir=root)
    try:
        with os.fdopen(descriptor, "wb") as output:
            output.write(json_bytes(value))
            output.flush()
            os.fsync(output.fileno())
        os.replace(temporary, root / "report.json")
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def material_requirements(payload_json):
    """Derive output checks from the exact normalized, quoted model payload."""
    try:
        payload = json.loads(payload_json)
        maps = payload["maps"]
        count = payload.get("numOutputs", 1)
        if (
            not isinstance(maps, list)
            or any(not isinstance(name, str) or name not in MATERIAL_MAP_ROLES for name in maps)
            or len(maps) != len(set(maps))
            or type(count) is not int
            or not 1 <= count <= 4
        ):
            raise ValueError
    except (TypeError, ValueError, KeyError):
        raise SmokeError(
            "Material checks require supported maps and output count in the quote", 4
        ) from None
    return maps, count


def _placeholders(value):
    """Count saved panorama placeholders anywhere in one JSON value."""
    if isinstance(value, dict):
        return (PANORAMA_REFERENCE in value) + sum(_placeholders(item) for item in value.values())
    if isinstance(value, list):
        return sum(_placeholders(item) for item in value)
    return 0


def _placeholder(value):
    return (
        isinstance(value, dict)
        and set(value) == {PANORAMA_REFERENCE}
        and isinstance(value[PANORAMA_REFERENCE], str)
        and RUN_NAME.fullmatch(value[PANORAMA_REFERENCE]) is not None
    )


def panorama_case(model_id, result_kind, parameters):
    """Check one case against the Environment lane contracts, before any network.

    A contract model must use the result kind of its output, so its saved
    projection and, for an HDR contract, its OpenEXR original are checked.
    A contract input that takes a saved 360 panorama accepts only saved
    panorama placeholders, and they fit nowhere else. Other models keep the
    plain result-kind checks. Returns the contract or None.
    """
    contract = panorama_contract.contract_for(model_id)
    if contract is not None:
        expected = "hdri" if contract.output == "hdr" else "panorama"
        if result_kind != expected:
            raise SmokeError(f"Use the {expected} result kind for this panorama model")
    inputs = (
        ()
        if contract is None
        else [rule.param for rule in contract.references if rule.kind == panorama_contract.PANORAMA]
    )
    allowed = 0
    for name in inputs:
        if name not in parameters:
            continue
        value = parameters[name]
        items = value if isinstance(value, list) else [value]
        if not all(map(_placeholder, items)):
            # The contract refuses any other asset; refuse before uploads or quotes.
            raise SmokeError(
                "Fill a saved 360 panorama input only with saved panorama placeholders"
            )
        allowed += len(items)
    if _placeholders(parameters) != allowed:
        raise SmokeError(
            "Use a saved panorama placeholder only in a panorama model input "
            "that takes a saved 360 panorama"
        )
    return contract


def saved_results(run_dir, settings):
    """Verify one completed run's saved receipts offline.

    The run's credential-scoped store must open with the selected API-key pair
    and project and match its saved quote scope; it must hold one finished job
    whose files still match their download receipts. The adapter refuses
    online access, so no Scenario request can be made.
    """
    root = Path(run_dir).absolute()
    if root != root.resolve() or not root.is_dir():
        raise SmokeError("Use a completed private run directory without symbolic links")
    for name in ("quote.json", "jobs.sqlite3", "scope.key"):
        if (root / name).is_symlink() or not (root / name).is_file():
            raise SmokeError("Saved run storage is incomplete; preserve it for review", 4)
    plan = json.loads(read_bytes(root / "quote.json"))
    credentials = Credentials(settings.credentials.key, settings.credentials.secret)
    try:
        store = open_credential_store(root, credentials, project_id=settings.project_id)
        records = store.records()
    except StoreError:
        raise SmokeError(
            "Saved run storage could not be opened; preserve it for review", 4
        ) from None
    if not isinstance(plan, dict) or asdict(store.scope) != plan.get("scope"):
        raise SmokeError("Saved runs must use the selected credentials and project")
    if len(records) != 1 or records[0].state not in FINISHED:
        raise SmokeError("The saved run has no completed, downloaded job", 4)
    adapter = SDKAdapter(
        credentials,
        account_id=store.scope.account_id,
        project_id=store.scope.project_id,
        online=lambda: False,
    )
    try:
        coordinator = JobCoordinator(
            adapter,
            store,
            result_downloader=ResultDownloader(
                StoragePolicy(STORAGE_HOSTS), online_access=lambda: False
            ),
            result_root=root / "results",
        )
        return coordinator.verify_results(
            records[0].intent.request_id, expected_revision=records[0].revision
        )
    except (ResultError, StoreError):
        raise SmokeError("Saved result files could not be verified; preserve the run", 1) from None
    finally:
        adapter.close()


def verified_bytes(item, path):
    """Read one verified result again and bind the bytes to its receipt."""
    try:
        if path.stat().st_size > MAX_FILE_BYTES:
            raise OSError
        data = path.read_bytes()
    except OSError:
        raise SmokeError("A saved result file is unreadable or too large", 1) from None
    if len(data) != item.receipt.size or digest(data) != item.receipt.sha256:
        raise SmokeError("A saved result file changed after verification", 1)
    return data


def saved_panorama(runs_root, name, settings):
    """The first downloaded LDR 360 result of one completed run, as a contract reference.

    This is the native "Use saved panorama" rule: Scenario's saved metadata
    declares the projection and the asset's own PNG or JPEG file passes the
    2:1 preflight, which also records its measured size for the upscale cap.
    """
    verified = saved_results(Path(runs_root) / name, settings)
    for item, path in zip(verified.record.results, verified.paths, strict=True):
        if panorama_contract.is_ldr_panorama(item):
            try:
                info = inspect_panorama(verified_bytes(item, path))
            except PanoramaError:
                raise SmokeError("A saved 360 result is not a supported 2:1 panorama", 1) from None
            return panorama_contract.PanoramaRef(
                item.asset.asset_id,
                producer=verified.record.intent.target_id,
                width=info.width,
                height=info.height,
            )
    raise SmokeError("The saved run has no downloaded LDR 360 panorama result", 1)


def resolve_panoramas(parameters, runs_root, settings):
    """Replace saved panorama placeholders with verified asset IDs, offline.

    Returns (parameters, references by asset ID). Without placeholders nothing
    is read; with them, `runs_root` must name a directory of completed runs.
    """
    if not _placeholders(parameters):
        return parameters, {}
    if runs_root is None:
        raise SmokeError("Name completed runs with --saved-runs for saved panorama inputs")
    root = Path(runs_root).absolute()
    if root != root.resolve() or not root.is_dir():
        raise SmokeError("Use a saved runs directory without symbolic links")
    found = {}

    def resolve(value):
        if isinstance(value, dict) and PANORAMA_REFERENCE in value:
            if not _placeholder(value):
                raise SmokeError("Use an exact saved panorama placeholder")
            name = value[PANORAMA_REFERENCE]
            if name not in found:
                found[name] = saved_panorama(root, name, settings)
            return found[name].asset_id
        if isinstance(value, dict):
            return {key: resolve(item) for key, item in value.items()}
        if isinstance(value, list):
            return [resolve(item) for item in value]
        return value

    resolved = resolve(parameters)
    return resolved, {ref.asset_id: ref for ref in found.values()}


def contract_body(adapter, contract, parameters, refs, *, code=2):
    """Apply the Environment lane contract to parameters against the current schema.

    The native form and local MCP run the same `panorama_contract.prepare`:
    schema drift fails closed, forced and default values are applied and only
    verified saved panoramas fill panorama inputs. The model read is free.
    """
    schema = parse_schema(ModelRecord.from_api(adapter.model(contract.model_id)))
    body, errors = panorama_contract.prepare(contract, schema.specs, parameters, panorama_refs=refs)
    errors += [
        error for error in validate(schema.specs, body, schema.one_of) if error not in errors
    ]
    if errors:
        raise SmokeError("Panorama contract refused the request: " + "; ".join(errors), code)
    return body


def _saved_refs(plan):
    """Rebuild the verified references bound into a contract quote."""
    refs = plan.get("panorama_refs")
    if not isinstance(refs, list):
        raise SmokeError("Invalid saved panorama references", 4)
    result = {}
    for ref in refs:
        if (
            not isinstance(ref, dict)
            or set(ref) != {"asset_id", "producer", "width", "height"}
            or not isinstance(ref["asset_id"], str)
            or not isinstance(ref["producer"], str)
            or any(
                ref[name] is not None and (type(ref[name]) is not int or ref[name] < 1)
                for name in ("width", "height")
            )
        ):
            raise SmokeError("Invalid saved panorama references", 4)
        result[ref["asset_id"]] = panorama_contract.PanoramaRef(**ref)
    return result


def panoramas(record, paths):
    """Return projected results whose verified bytes pass the World panorama preflight.

    Only the server-declared projection selects a file; the bounded container
    check then requires a 2:1 PNG, JPEG or OpenEXR. It does not decode pixels, measure
    dynamic range or judge seams, which stay with Blender and human review.
    """
    if len(paths) != len(record.results):
        raise SmokeError("Verified files do not match the saved results", 1)
    checked = []
    for item, path in zip(record.results, paths, strict=True):
        if item.asset.projection != "equirectangular":
            continue
        try:
            if path.stat().st_size > MAX_FILE_BYTES:
                raise PanoramaError("Panorama file exceeds the byte limit")
            checked.append((item.asset, inspect_panorama(path.read_bytes())))
        except (OSError, PanoramaError):
            raise SmokeError("A projected result is not a supported 2:1 panorama file", 1) from None
    return checked


def verify_result_kind(record, result_kind, *, material_payload=None, paths=()):
    """Check saved metadata after receipt verification.

    Panorama kinds also run the bounded container preflight on the verified files;
    no kind decodes media or applies it to a scene.
    """
    assets = [item.asset for item in record.results]
    if not assets or any(item.receipt is None or item.receipt.size <= 0 for item in record.results):
        raise SmokeError("Downloaded results contain no usable bytes", 1)
    media_types = [item.media_type for item in assets]
    if result_kind == "image":
        matches = all(mime.startswith("image/") for mime in media_types)
    elif result_kind in {"panorama", "hdri"}:
        checked = panoramas(record, paths)
        if result_kind == "hdri":
            # A declared OpenEXR original, never a tonemapped preview or a filename.
            checked = [
                (asset, info)
                for asset, info in checked
                if asset.source == "original"
                and asset.media_type in ORIGINAL_MEDIA_TYPES
                and info.hdr_capable
            ]
        matches = all(mime.startswith("image/") for mime in media_types) and bool(checked)
    elif result_kind == "material":
        if material_payload is None:
            raise SmokeError("Material quote lacks map expectations; inspect saved results", 4)
        if digest(material_payload.encode()) != record.intent.payload_sha256:
            raise SmokeError("Material expectations differ from the saved request", 4)
        maps, count = material_requirements(material_payload)
        roles = Counter(item.texture_role for item in assets)
        matches = (
            all(mime.startswith("image/") for mime in media_types)
            and max(roles["base"], roles["albedo"]) >= count
            and all(sum(roles[role] for role in MATERIAL_MAP_ROLES[name]) >= count for name in maps)
        )
    elif result_kind == "model":
        matches = "model/gltf-binary" in media_types
    else:
        matches = any(mime.startswith(result_kind + "/") for mime in media_types)
    if not matches:
        raise SmokeError("Downloaded results do not match the approved result kind", 1)


def follow(
    coordinator,
    store,
    *,
    timeout,
    result_kind="image",
    material_payload=None,
    clock=time.monotonic,
    sleep=time.sleep,
):
    """Follow one saved request; never estimate, prepare, submit or apply."""
    records = store.records()
    if len(records) != 1:
        raise SmokeError("Expected one saved request; inspect this run without submitting", 4)
    record = records[0]
    deadline = clock() + timeout
    while True:
        print(f"Saved job state: {record.state.value}")
        if record.state in {JobState.REMOTE, JobState.CANCEL_REQUESTED}:
            if clock() >= deadline:
                raise SmokeError("Polling deadline reached; resume this run without submitting", 4)
            record = coordinator.refresh_remote(
                record.intent.request_id, expected_revision=record.revision
            ).record
            if record.state in {JobState.REMOTE, JobState.CANCEL_REQUESTED}:
                sleep(min(2, max(0, deadline - clock())))
        elif record.state == JobState.DOWNLOADING:
            record = coordinator.recover_downloads(
                record.intent.request_id, expected_revision=record.revision
            )
        elif record.state in {JobState.SUCCEEDED, JobState.DOWNLOAD_FAILED}:
            record = coordinator.download_results(
                record.intent.request_id, expected_revision=record.revision
            )
        elif record.state == JobState.READY:
            verified = coordinator.verify_results(
                record.intent.request_id, expected_revision=record.revision
            )
            if not verified.paths:
                raise SmokeError("Downloaded results contain no usable files", 1)
            verify_result_kind(
                verified.record,
                result_kind,
                material_payload=material_payload,
                paths=verified.paths,
            )
            print(f"Verified {len(verified.paths)} result file(s); no Blender application")
            return 0
        elif record.state in {JobState.FAILED, JobState.CANCELED}:
            raise SmokeError("Saved remote job ended without successful results", 1)
        else:
            raise SmokeError("Saved request needs review; generation will not be replayed", 4)


def execute(args, settings, *, transport=None, downloader=None):
    """Use a private run directory; injected transports are for offline tests only."""
    material_payload = None
    contract = None
    refs = {}
    root = args.run_dir.absolute()
    if root != root.resolve() or (root.exists() and not root.is_dir()):
        raise SmokeError("Use a private run directory without symlink components")
    if args.command == "quote":
        result_kind = args.result_kind
        parameters = json.loads(read_bytes(args.parameters))
        if not isinstance(parameters, dict):
            raise SmokeError("Parameters must be one JSON object")
        json_bytes(parameters)
        contract = panorama_case(args.model, result_kind, parameters)
        # Saved panorama inputs are verified offline before the run exists.
        parameters, refs = resolve_panoramas(
            parameters, getattr(args, "saved_runs", None), settings
        )
        # Never overwrite another quote, job, uncertain attempt or scope key.
        root.mkdir(mode=0o700)
        sync_directory(root.parent)
    else:
        if not root.is_dir():
            raise SmokeError("Keep the original run directory for submission and recovery")
        if not (root / "jobs.sqlite3").is_file() or not (root / "scope.key").is_file():
            raise SmokeError("Run storage is incomplete; preserve it for review", 4)
        raw = read_bytes(root / "quote.json")
        plan = json.loads(raw)
        if plan.get("schema_version") not in (1, 2, 3, CONTRACT_QUOTE):
            raise SmokeError("Unsupported quote record")
        result_kind = "image" if plan["schema_version"] == 1 else plan.get("result_kind")
        if result_kind not in RESULT_KINDS:
            raise SmokeError("Unsupported saved result kind")
        if args.expected_result_kind and result_kind != args.expected_result_kind:
            raise SmokeError("Use the entry point matching this run's approved result kind")
        if args.command == "submit" and digest(raw) != args.approved_quote:
            raise SmokeError("Quote record changed; approve its current exact contents")
        saved_model = plan.get("model")
        if not isinstance(saved_model, str):
            raise SmokeError("Unsupported quote record")
        if plan["schema_version"] == CONTRACT_QUOTE:
            if panorama_contract.contract_for(saved_model) is None:
                raise SmokeError("Invalid saved panorama contract quote", 4)
            contract = panorama_case(saved_model, result_kind, {})
            refs = _saved_refs(plan)
        elif args.command == "submit" and panorama_contract.contract_for(saved_model):
            # An older quote of a contract model never ran the contract check.
            raise SmokeError(
                "This panorama quote has no contract check; create a new quote in a new run", 4
            )
        if plan["schema_version"] == 3:
            material_payload = plan.get("material_payload_json")
            if (
                result_kind != "material"
                or not isinstance(material_payload, str)
                or digest(material_payload.encode()) != plan["payload_sha256"]
            ):
                raise SmokeError("Invalid saved material expectations", 4)
            material_requirements(material_payload)
        if args.command == "submit":
            if result_kind == "material" and material_payload is None:
                raise SmokeError("Material quote lacks map expectations; create a new quote", 4)
            cost = decimal_cost(plan["cost"])
            if cost != args.approved_cost:
                raise SmokeError("The approved cost differs from the saved quote", 3)
            if cost > args.max_cu:
                raise SmokeError(
                    "The quote exceeds the approved spending cap; nothing submitted", 3
                )

    credentials = Credentials(settings.credentials.key, settings.credentials.secret)
    store = open_credential_store(root, credentials, project_id=settings.project_id)
    if args.command != "quote" and asdict(store.scope) != plan["scope"]:
        raise SmokeError("Credentials or project changed; use the run's original scope")
    result_root = root / "results"
    result_root.mkdir(mode=0o700, exist_ok=True)
    policy = StoragePolicy(STORAGE_HOSTS)
    adapter = SDKAdapter(
        credentials,
        account_id=store.scope.account_id,
        project_id=store.scope.project_id,
        online=lambda: True,
        transport=transport,
    )
    try:
        coordinator = JobCoordinator(
            adapter,
            store,
            result_downloader=downloader or ResultDownloader(policy, online_access=lambda: True),
            result_root=result_root,
        )
        if args.command == "quote":
            if contract is not None:
                parameters = contract_body(adapter, contract, parameters, refs)
            origin = JobOrigin(uuid.uuid4().hex, "model-smoke", "1", "download-only")
            quote = coordinator.quote_model(args.model, parameters, origin=origin)
            plan = {
                "schema_version": 2,
                "result_kind": result_kind,
                "scope": asdict(store.scope),
                "origin": asdict(origin),
                "model": args.model,
                "parameters": parameters,
                "payload_sha256": digest(quote.estimate.payload_json),
                "cost": format(quote.estimate.cost, "f"),
            }
            if contract is not None:
                plan["schema_version"] = CONTRACT_QUOTE
                plan["panorama_refs"] = [asdict(refs[key]) for key in sorted(refs)]
            if result_kind == "material":
                material_payload = quote.estimate.payload_json.decode()
                material_requirements(material_payload)
                plan["schema_version"] = 3
                plan["material_payload_json"] = material_payload
            raw = json_bytes(plan)
            create_file(root / "quote.json", raw)
            print(f"Exact quote: {quote.estimate.cost} CU")
            print(f"Quote approval SHA-256: {digest(raw)}")
            print("No generation submitted. Review the private quote file and selected test scope.")
            return 0
        if args.command == "submit":
            if store.records():
                raise SmokeError("A saved job already exists; use resume, never submit again", 4)
            # Exclusive creation arbitrates concurrent processes before any new
            # estimate or paid claim. Keep the marker on every failure/crash.
            try:
                create_file(root / "submission-attempt", b"Do not delete or repeat submission.\n")
            except FileExistsError:
                raise SmokeError(
                    "Submission was already attempted; use resume or inspect", 4
                ) from None
            origin = JobOrigin(**plan["origin"])
            if contract is not None:
                # The contract must still accept the approved body unchanged.
                body = contract_body(adapter, contract, plan["parameters"], refs, code=3)
                if body != plan["parameters"]:
                    raise SmokeError(
                        "Panorama contract changed; nothing submitted, review again", 3
                    )
            quote = coordinator.quote_model(plan["model"], plan["parameters"], origin=origin)
            if (
                quote.estimate.cost != args.approved_cost
                or quote.estimate.cost > args.max_cu
                or digest(quote.estimate.payload_json) != plan["payload_sha256"]
            ):
                raise SmokeError(
                    "Fresh quote or payload changed; nothing submitted, review again", 3
                )
            prepared = coordinator.prepare_quote(quote)
            coordinator.submit(
                prepared,
                origin=origin,
                operation=prepared.intent.operation,
                target_id=prepared.intent.target_id,
                payload=prepared.estimate.payload,
            )
        return follow(
            coordinator,
            store,
            timeout=args.timeout,
            result_kind=result_kind,
            material_payload=material_payload,
        )
    finally:
        adapter.close()
        report(root, store, result_kind)


def parser(*, default_result_kind="image"):
    result = argparse.ArgumentParser(description=__doc__)
    result.set_defaults(expected_result_kind=default_result_kind)
    commands = result.add_subparsers(dest="command", required=True)
    for command in ("quote", "submit", "resume"):
        item = commands.add_parser(command)
        item.add_argument("--run-dir", type=Path, required=True)
        if command == "quote":
            if default_result_kind is None:
                item.add_argument("--result-kind", choices=RESULT_KINDS, required=True)
            else:
                item.set_defaults(result_kind=default_result_kind)
            item.add_argument("--model", required=True)
            item.add_argument("--parameters", type=Path, required=True)
            item.add_argument(
                "--saved-runs",
                type=Path,
                help="Directory of completed runs named by saved panorama placeholders",
            )
        else:
            item.add_argument(
                "--timeout", type=int, default=300, choices=range(1, 3601), metavar="SECONDS"
            )
        if command == "submit":
            item.add_argument("--approved-quote", required=True, help="SHA-256 printed by quote")
            item.add_argument("--approved-cost", type=decimal_cost, required=True)
            item.add_argument("--max-cu", type=decimal_cost, required=True)
    return result


def main(argv=None, *, default_result_kind="image"):
    args = parser(default_result_kind=default_result_kind).parse_args(argv)
    if args.command == "submit" and os.environ.get("SCENARIO_SMOKE") != "1":
        print("Set SCENARIO_SMOKE=1 on the command line only after spending authorization")
        return 2
    try:
        settings = live_settings()
        return execute(args, settings)
    except SmokeError as error:
        print(str(error))
        return error.code
    except SystemExit:
        print("Configure the explicit test API-key pair before running this command")
        return 2
    except Exception:
        # Raw exceptions may carry private paths, parameters, IDs or signed URLs.
        print("Model check stopped; preserve the private run directory and inspect saved state")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
