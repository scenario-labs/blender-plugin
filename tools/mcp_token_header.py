# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Headers helper for the repository's Claude Code and Codex MCP entries; see docs/MCP.md.

uv loads .env.local. The header goes to stdout for the client only; --check never prints the token.
"""

import argparse
import json

from tools.dev_config import local_mcp_token


def main(argv=None, environ=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--check", action="store_true", help="Validate the token without printing it"
    )
    args = parser.parse_args(argv)
    token = local_mcp_token(environ)
    if args.check:
        print("local MCP token found; Blender's server decides whether it is current")
    else:
        print(json.dumps({"Authorization": f"Bearer {token}"}))


if __name__ == "__main__":
    main()
