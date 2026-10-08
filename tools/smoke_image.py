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

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.store import JobOrigin, JobState
from scenario.core.jobs.transfers import ResultDownloader, StoragePolicy
from tools.dev_config import live_settings

RESULT_KINDS = ("image", "material", "video", "model", "audio")
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
    descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
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


def verify_result_kind(record, result_kind, *, material_payload=None):
    """Check saved metadata after receipt verification; this does not decode media."""
    assets = [item.asset for item in record.results]
    if not assets or any(item.receipt is None or item.receipt.size <= 0 for item in record.results):
        raise SmokeError("Downloaded results contain no usable bytes", 1)
    media_types = [item.media_type for item in assets]
    if result_kind == "image":
        matches = all(mime.startswith("image/") for mime in media_types)
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
            verify_result_kind(verified.record, result_kind, material_payload=material_payload)
            print(f"Verified {len(verified.paths)} result file(s); no Blender application")
            return 0
        elif record.state in {JobState.FAILED, JobState.CANCELED}:
            raise SmokeError("Saved remote job ended without successful results", 1)
        else:
            raise SmokeError("Saved request needs review; generation will not be replayed", 4)


def execute(args, settings, *, transport=None, downloader=None):
    """Use a private run directory; injected transports are for offline tests only."""
    material_payload = None
    root = args.run_dir.absolute()
    if root != root.resolve() or (root.exists() and not root.is_dir()):
        raise SmokeError("Use a private run directory without symlink components")
    if args.command == "quote":
        result_kind = args.result_kind
        parameters = json.loads(read_bytes(args.parameters))
        if not isinstance(parameters, dict):
            raise SmokeError("Parameters must be one JSON object")
        json_bytes(parameters)
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
        if plan.get("schema_version") not in (1, 2, 3):
            raise SmokeError("Unsupported quote record")
        result_kind = "image" if plan["schema_version"] == 1 else plan.get("result_kind")
        if result_kind not in RESULT_KINDS:
            raise SmokeError("Unsupported saved result kind")
        if args.expected_result_kind and result_kind != args.expected_result_kind:
            raise SmokeError("Use the entry point matching this run's approved result kind")
        if args.command == "submit" and digest(raw) != args.approved_quote:
            raise SmokeError("Quote record changed; approve its current exact contents")
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
    policy = StoragePolicy(frozenset({"cdn.cloud.scenario.com", "cdn.scenario.com"}))
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
