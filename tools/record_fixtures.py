#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record REST fixtures used by unit tests. Uses explicit test credentials from the process environment.

Usage: uv run --locked --env-file .env.local python tools/record_fixtures.py
Offline: uv run --locked --no-env-file python tools/record_fixtures.py --scrub-existing
"""

import argparse
import json
import pathlib
import sys
from urllib.parse import parse_qsl

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scenario.core.api.client import ScenarioClient
from scenario.core.api.errors import ScenarioError
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
    "model_patina-material",
    "model_patina",
    "model_patina-material-extract",
    "model_openai-gpt-image-2",
    "model_google-gemini-3-1-flash",
    "model_bytedance-seedance-2-0",
    "model_meshy-7-img23d",
    "model_meshy-7-txt23d",
    "model_tripo-v3-1-image-to-3d",
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
    settings = live_settings()
    client = ScenarioClient(
        settings.credentials.key, settings.credentials.secret, project_id=settings.project_id
    )
    out = ROOT / "tests" / "fixtures" / "models"
    out.mkdir(parents=True, exist_ok=True)
    for model_id in MODEL_IDS:
        try:
            data = client.get(f"/models/{model_id}")
        except ScenarioError as err:
            print("MISSING", model_id, err.status)
            continue
        write_fixture(out / f"{model_id}.json", data)
        print("saved", model_id)
    page1 = client.get("/models", query={"privacy": "public", "pageSize": 5})
    write_fixture(FIXTURES / "models_list_page1.json", page1)
    token = page1.get("nextPaginationToken")
    page2 = client.get(
        "/models", query={"privacy": "public", "pageSize": 5, "paginationToken": token}
    )
    first1 = page1["models"][0]["id"]
    first2 = page2["models"][0]["id"] if page2.get("models") else None
    print("pagination param 'paginationToken' works:", first1 != first2)
    if first1 == first2:
        page2b = client.get(
            "/models", query={"privacy": "public", "pageSize": 5, "pageToken": token}
        )
        print("fallback 'pageToken' works:", page2b["models"][0]["id"] != first1)


if __name__ == "__main__":
    main()
