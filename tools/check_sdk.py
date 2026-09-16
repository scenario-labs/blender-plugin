# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Explicit live SDK catalog/estimate check; no generation submission entry point."""

import argparse
import json
from pathlib import Path

from scenario.core.api.sdk_adapter import AdapterError, Credentials, SDKAdapter
from tools.dev_config import live_settings


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--model", help="Retrieve this custom model and estimate the supplied inputs"
    )
    parser.add_argument("--parameters", type=Path, help="JSON input object; required with --model")
    args = parser.parse_args(argv)
    if bool(args.model) != bool(args.parameters):
        parser.error("--model and --parameters must be supplied together")
    settings = live_settings()
    try:
        parameters = json.loads(args.parameters.read_text()) if args.parameters else None
        credentials = Credentials(settings.credentials.key, settings.credentials.secret)
        with SDKAdapter(credentials, project_id=settings.project_id, online=lambda: True) as client:
            print(f"Catalog read passed: {len(client.models())} models")
            if args.model:
                quote = client.estimate_model(client.model(args.model), parameters)
                print(f"SDK dry-run estimate passed: {quote.cost} CU")
    except (AdapterError, ValueError, OSError) as error:
        # Keep service error text sanitized; never dump records, inputs or URLs.
        message = (
            str(error) if isinstance(error, AdapterError) else "Check the model and JSON parameters"
        )
        raise SystemExit(message) from None
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
