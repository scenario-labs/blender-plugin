#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record REST fixtures used by unit tests. Uses explicit test credentials from the process environment.

Usage: uv run --locked --env-file .env.local python tools/record_fixtures.py
Offline: uv run --locked --no-env-file python tools/record_fixtures.py --scrub-existing
"""

import argparse
import datetime as dt
import json
import os
import pathlib
import sys
import tempfile
from importlib.metadata import version
from urllib.parse import parse_qsl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from tools.dev_config import live_settings

FIXTURES = ROOT / "tests" / "fixtures"
PLACEHOLDERS = {
    "userId": "apiu_FIXTURE0000000000000000",
    "authorId": "apiu_FIXTURE0000000000000000",
    "createdBy": "apiu_FIXTURE0000000000000000",
    "ownerId": "proj_FIXTURE00000000000000000",
    "projectId": "proj_FIXTURE00000000000000000",
    "teamId": "team_FIXTURE0000000000000000",
}
SIGNED_QUERY_KEYS = frozenset(
    {"key-pair-id", "policy", "signature", "x-amz-signature", "x-amz-credential"}
)
SIGNED_URL_PLACEHOLDER = "https://cdn.example/FIXTURE"

MODEL_IDS = [
    "model_bytedance-seedance-2-0",
    "model_cartwheel-text-to-motion",
    "model_google-gemini-3-1-flash",
    "model_meshy-7-img23d",
    "model_meshy-7-retexture",
    "model_meshy-7-txt23d",
    "model_meshy-rigging",
    "model_minimax-h3",
    "model_openai-gpt-image-2",
    "model_patina",
    "model_patina-material",
    "model_patina-material-extract",
    "model_rodin-hyper3d-bang",
    "model_runway-aleph-2",
    "model_scenario-llm",
    "model_tripo-retopology",
    "model_tripo-v3-1-image-to-3d",
    "model_uthana-text-to-motion-3.0",
]


def is_signed_url(value):
    """Recognize signed HTTP URL query keys, including encoded names and casing."""
    if not isinstance(value, str) or not value.lower().startswith(("http://", "https://")):
        return False
    # Inspect query names even if a captured URL has a malformed host. Fragments
    # are not sent to the server, and signature words inside values are not keys.
    query = value.split("#", 1)[0].partition("?")[2]
    return any(
        key.lower() in SIGNED_QUERY_KEYS for key, _ in parse_qsl(query, keep_blank_values=True)
    )


def scrub(data):
    """Copy JSON, replacing known account fields and signed URLs only.

    Non-string fields retain their shape so malformed records and schemas stay
    diagnosable. Asset, job and model identities and schema semantics are kept.
    """
    if isinstance(data, dict):
        return {
            key: PLACEHOLDERS[key]
            if key in PLACEHOLDERS and isinstance(value, str)
            else scrub(value)
            for key, value in data.items()
        }
    if isinstance(data, list):
        return [scrub(value) for value in data]
    return SIGNED_URL_PLACEHOLDER if is_signed_url(data) else data


def write_fixture(path, data):
    path.write_text(json.dumps(scrub(data), indent=1), encoding="utf-8")


def scrub_existing(fixtures=None):
    """Scrub JSON offline, preserving existing indentation and final LF."""
    fixtures = FIXTURES if fixtures is None else fixtures
    updates = []
    for path in sorted(fixtures.rglob("*.json")):
        # An abruptly killed recording can leave private staging behind. It is
        # not part of the published inventory and must remain untouched.
        if any(part.startswith(".") for part in path.relative_to(fixtures).parts[:-1]):
            continue
        if path.is_symlink():
            raise ValueError(f"fixture must not be a symlink: {path.relative_to(fixtures)}")
        try:
            original = path.read_text(encoding="utf-8")
            data = json.loads(original)
        except (UnicodeError, json.JSONDecodeError):
            # Do not echo fixture contents that may include an unsanitized URL.
            raise ValueError(f"invalid fixture JSON: {path.relative_to(fixtures)}") from None
        clean = scrub(data)
        if clean == data:
            continue
        indent = next(
            (
                line[: len(line) - len(line.lstrip())]
                for line in original.splitlines()
                if line[:1].isspace()
            ),
            "",
        )
        dumped = (
            json.dumps(clean, indent=indent)
            if "\n" in original.rstrip("\n")
            else json.dumps(clean, separators=(",", ":"))
        )
        updates.append((path, dumped + ("\n" if original.endswith("\n") else "")))
    # Parse the whole inventory before changing files, so a malformed record
    # leaves the existing fixture set intact for inspection.
    for path, text in updates:
        path.write_text(text, encoding="utf-8")
        print("scrubbed", path.relative_to(fixtures))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--scrub-existing", action="store_true", help="scrub local JSON, without API access"
    )
    args = parser.parse_args(argv)
    if args.scrub_existing:
        scrub_existing()
        return
    try:
        record()
    except (AdapterError, ValueError):
        # Keep unexpected response and configuration text out of the terminal.
        print("Fixture recording failed; no successful refresh is recorded.", file=sys.stderr)
        return 1
    except OSError:
        print("Could not write fixtures; no successful refresh is recorded.", file=sys.stderr)
        return 1
    return 0


def record():
    """Fetch the complete requested set before replacing any committed fixture."""
    paths = [f"models/{model_id}.json" for model_id in MODEL_IDS]
    paths += ["models_list_page1.json", "PROVENANCE.json"]
    for relative in paths:
        path = FIXTURES / relative
        if path.is_symlink() or not path.resolve().is_relative_to(FIXTURES.resolve()):
            raise ValueError("Fixture output must stay inside its directory")
    settings = live_settings()
    credentials = Credentials(settings.credentials.key, settings.credentials.secret)
    records, endpoints = {}, {}
    # This standalone, explicitly invoked read tool has no Blender permission
    # state. It never estimates, generates, downloads media or discovers identity.
    with SDKAdapter(credentials, project_id=settings.project_id, online=lambda: True) as client:
        for model_id in MODEL_IDS:
            relative = f"models/{model_id}.json"
            model = client.model(model_id)
            if model.get("id") != model_id:
                raise AdapterError("Scenario returned a different model identity")
            records[relative] = {"model": model}
            endpoints[relative] = f"GET /models/{model_id}"
        records["models_list_page1.json"] = client.model_page(privacy="public", page_size=5)
        endpoints["models_list_page1.json"] = "GET /models?privacy=public&pageSize=5"
    records["PROVENANCE.json"] = {
        "recordedAt": dt.datetime.now(dt.UTC).date().isoformat(),
        "recorder": "tools/record_fixtures.py",
        "sdkVersion": version("scenario-sdk"),
        "scrub": "Known account fields use synthetic placeholders; signed URLs are replaced.",
        "files": endpoints,
    }
    FIXTURES.mkdir(parents=True, exist_ok=True)
    # Stage every sanitized output first. Publish provenance last and remove
    # an older run's claim before any replacements; an interrupted write cannot
    # make a partially refreshed set look like a completed recording run.
    with tempfile.TemporaryDirectory(prefix=".recording-", dir=FIXTURES) as temp:
        staged = pathlib.Path(temp)
        for relative, data in records.items():
            target = staged / relative
            target.parent.mkdir(parents=True, exist_ok=True)
            write_fixture(target, data)
        (FIXTURES / "PROVENANCE.json").unlink(missing_ok=True)
        for relative in records:
            destination = FIXTURES / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(staged / relative, destination)
    for relative in records:
        print("saved", relative)


if __name__ == "__main__":
    raise SystemExit(main())
