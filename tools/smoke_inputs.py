# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit reference uploads for a reviewed smoke plan; recovery never sends bytes."""

import argparse
import json
import os
import time
import uuid
from dataclasses import asdict
from pathlib import Path, PurePosixPath

from scenario.core.api.sdk_adapter import Credentials, SDKAdapter
from scenario.core.jobs.coordinator import JobCoordinator
from scenario.core.jobs.credential_storage import open_credential_store
from scenario.core.jobs.store import JobOrigin
from scenario.core.jobs.upload_sources import UploadSources
from scenario.core.jobs.upload_store import UploadState, UploadStore
from scenario.core.jobs.upload_transfers import PartUploader, S3UploadPolicy
from tools import smoke_image as model
from tools.dev_config import live_settings

MAX_BYTES = 32 * 1024 * 1024


def resolve(value, assets, used):
    if isinstance(value, dict):
        if "$input" in value:
            name = value["$input"]
            if set(value) != {"$input"} or not isinstance(name, str) or name not in assets:
                raise model.SmokeError("Use an exact named input reference")
            used.add(name)
            return assets[name]
        return {key: resolve(item, assets, used) for key, item in value.items()}
    if isinstance(value, list):
        return [resolve(item, assets, used) for item in value]
    return value


def validate(plan, settings):
    from tools import smoke_suite as suite

    if (
        not isinstance(plan, dict)
        or set(plan) != {"schema_version", "project_id", "inputs", "cases"}
        or plan["schema_version"] != 2
        or plan["project_id"] != settings.project_id
    ):
        raise model.SmokeError("Input plan requires version 2 and the selected test project")
    entries = suite.cases(plan["inputs"])
    for entry in entries:
        if (
            set(entry) != {"name", "file", "sha256", "kind", "content_type"}
            or not isinstance(entry["sha256"], str)
            or not suite.SHA256.fullmatch(entry["sha256"])
            or not isinstance(entry["kind"], str)
            or entry["kind"] not in {"image", "video", "audio", "3d", "asset", "text"}
            or not isinstance(entry["content_type"], str)
        ):
            raise model.SmokeError("Each input requires its file, exact hash, kind and MIME type")
        name = entry["file"]
        if (
            not isinstance(name, str)
            or "\\" in name
            or "\x00" in name
            or PurePosixPath(name).is_absolute()
            or any(part in {"", ".", ".."} for part in name.split("/"))
        ):
            raise model.SmokeError("Input files must be relative paths beneath the input root")
    suite.validate_plan(
        {"schema_version": 1, "project_id": plan["project_id"], "cases": plan["cases"]}, settings
    )
    used = set()
    resolved = {
        "schema_version": 1,
        "project_id": plan["project_id"],
        "cases": resolve(
            plan["cases"], {item["name"]: "input-placeholder" for item in entries}, used
        ),
    }
    suite.validate_plan(resolved, settings)
    if used != {entry["name"] for entry in entries}:
        raise model.SmokeError("Every declared input must be referenced by a case")
    return entries


def source_paths(entries, root):
    root = root.absolute()
    if root != root.resolve() or not root.is_dir():
        raise model.SmokeError("Use an explicit input directory without symbolic links")
    paths = {}
    for entry in entries:
        path = root.joinpath(*entry["file"].split("/"))
        if (
            path != path.resolve()
            or not path.is_relative_to(root)
            or not path.is_file()
            or not 1 <= path.stat().st_size <= MAX_BYTES
        ):
            raise model.SmokeError("Inputs must be regular files of at most 32 MiB without links")
        paths[entry["name"]] = path
    return paths


def follow(coordinator, record, *, mutate, timeout, clock=time.monotonic, sleep=time.sleep):
    deadline = clock() + timeout
    while record.state != UploadState.IMPORTED:
        if clock() >= deadline:
            raise model.SmokeError("Input deadline reached; preserve and inspect this run", 4)
        if mutate and record.state == UploadState.PREPARED:
            method = coordinator.initialize_upload
        elif mutate and record.state == UploadState.UPLOADING and record.active_part is None:
            method = (
                coordinator.transfer_upload_part
                if len(record.receipts) < len(record.intent.part_sha256)
                else coordinator.finalize_upload
            )
        elif record.upload_id and record.state in {
            UploadState.UPLOADING,
            UploadState.PART_UNCERTAIN,
            UploadState.FINALIZING,
            UploadState.FINALIZATION_UNCERTAIN,
            UploadState.PROCESSING,
        }:
            method = coordinator.refresh_upload
        else:
            raise model.SmokeError(
                "Saved upload needs review; no initialization or bytes replayed", 4
            )
        previous = record
        record = method(record.intent.request_id, expected_revision=record.revision)
        if not mutate and record.state == UploadState.UPLOADING:
            raise model.SmokeError(
                "Incomplete upload needs explicit review; recovery cannot send bytes", 4
            )
        if record == previous:
            sleep(min(2, max(0, deadline - clock())))
    return record.asset_id


def execute(args, settings, *, transport=None, uploader=None):
    root = args.run_dir.absolute()
    if root != root.resolve() or (root.exists() and not root.is_dir()):
        raise model.SmokeError("Use a private input run directory without symbolic links")
    if args.command == "upload":
        raw = model.read_bytes(args.plan)
        if model.digest(raw) != args.approved_plan:
            raise model.SmokeError("Input plan differs from the authorized bytes", 3)
        plan = json.loads(raw)
        entries = validate(plan, settings)
        paths = source_paths(entries, args.input_root)
        root.mkdir(mode=0o700)
        model.sync_directory(root.parent)
    else:
        for name in ("jobs.sqlite3", "scope.key", "uploads.sqlite3", "inputs.json"):
            if not (root / name).is_file() or (root / name).is_symlink():
                raise model.SmokeError("Keep the complete original input run for recovery", 4)
        saved = json.loads(model.read_bytes(root / "inputs.json"))
        if not isinstance(saved, dict) or set(saved) != {"plan", "scope", "requests"}:
            raise model.SmokeError("Invalid saved input manifest")
        plan = saved["plan"]
        entries = validate(plan, settings)

    credentials = Credentials(settings.credentials.key, settings.credentials.secret)
    store = open_credential_store(root, credentials, project_id=settings.project_id)
    if args.command != "upload" and asdict(store.scope) != saved["scope"]:
        raise model.SmokeError("Use the original input credentials and project")
    sources_root = root / "sources"
    sources_root.mkdir(mode=0o700, exist_ok=True)
    uploads = UploadStore(root / "uploads.sqlite3", store.scope)
    adapter = SDKAdapter(
        credentials,
        account_id=store.scope.account_id,
        project_id=store.scope.project_id,
        online=lambda: True,
        transport=transport,
    )
    coordinator = JobCoordinator(
        adapter,
        store,
        upload_store=uploads,
        upload_sources=UploadSources(sources_root, max_bytes=MAX_BYTES),
        part_uploader=uploader or PartUploader(S3UploadPolicy(), online_access=lambda: True),
    )
    try:
        if args.command == "upload":
            requests = {}
            # Stage and hash EVERY source before the first remote mutation.
            for entry in entries:
                record = coordinator.prepare_upload(
                    paths[entry["name"]],
                    origin=JobOrigin(uuid.uuid4().hex, "smoke-input", "1", entry["name"]),
                    kind=entry["kind"],
                    content_type=entry["content_type"],
                    expected_sha256=entry["sha256"],
                )
                requests[entry["name"]] = record.intent.request_id
            saved = {"plan": plan, "scope": asdict(store.scope), "requests": requests}
            manifest = model.json_bytes(saved)
            if len(manifest) > 1024 * 1024:
                raise model.SmokeError("Input manifest exceeds the recovery size limit")
            model.create_file(root / "inputs.json", manifest)
        if set(saved["requests"]) != {entry["name"] for entry in entries}:
            raise model.SmokeError("Saved input bindings are incomplete")
        records = []
        for entry in entries:
            record = coordinator.inspect_upload(saved["requests"][entry["name"]])
            if (
                record is None
                or record.intent.file_sha256 != entry["sha256"]
                or record.intent.kind != entry["kind"]
                or record.intent.content_type != entry["content_type"]
                or record.intent.origin.target_id != entry["name"]
            ):
                raise model.SmokeError("Saved upload differs from the reviewed input")
            records.append(record)
        assets = {}
        for index, (entry, record) in enumerate(zip(entries, records, strict=True), 1):
            print(f"Input {index}: {record.state.value}")
            assets[entry["name"]] = follow(
                coordinator, record, mutate=args.command == "upload", timeout=args.timeout
            )
        prepared = {
            "schema_version": 1,
            "project_id": settings.project_id,
            "cases": resolve(plan["cases"], assets, set()),
        }
        raw = model.json_bytes(prepared)
        destination = root / "prepared-plan.json"
        if destination.exists():
            if model.read_bytes(destination) != raw:
                raise model.SmokeError("Prepared plan changed; preserve this run for review")
        else:
            model.create_file(destination, raw)
        print(f"Verified {len(assets)} imported input(s); no generation submitted")
        return destination
    finally:
        coordinator.close()


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    for name in ("upload", "resume"):
        item = commands.add_parser(name)
        item.add_argument("--run-dir", type=Path, required=True)
        item.add_argument(
            "--timeout", type=int, default=300, choices=range(1, 3601), metavar="SECONDS"
        )
        if name == "upload":
            item.add_argument("--plan", type=Path, required=True)
            item.add_argument("--input-root", type=Path, required=True)
            item.add_argument("--approved-plan", required=True)
    args = parser.parse_args(argv)
    if args.command == "upload" and os.environ.get("SCENARIO_SMOKE") != "1":
        print("Set SCENARIO_SMOKE=1 only after authorization to upload the exact plan inputs")
        return 2
    try:
        execute(args, live_settings())
        return 0
    except model.SmokeError as error:
        print(str(error))
        return error.code
    except SystemExit:
        print("Configure the explicit test API-key pair before running this command")
        return 2
    except Exception:
        print("Input preparation stopped; preserve private state and inspect before further writes")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
