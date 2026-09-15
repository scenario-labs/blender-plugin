#!/usr/bin/env python3
# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Record REST fixtures used by unit tests. Uses explicit test credentials from the process environment.

Usage: uv run --locked --env-file .env.local python tools/record_fixtures.py
"""

import json
import pathlib
import sys

ROOT = pathlib.Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from scenario.core.api.client import ScenarioClient
from scenario.core.api.errors import ScenarioError
from tools.dev_config import live_settings

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


def main():
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
            print("MISSING", model_id, err.status, err.reason)
            continue
        (out / f"{model_id}.json").write_text(json.dumps(data, indent=1))
        print("saved", model_id)
    page1 = client.get("/models", query={"privacy": "public", "pageSize": 5})
    (ROOT / "tests" / "fixtures" / "models_list_page1.json").write_text(json.dumps(page1, indent=1))
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
