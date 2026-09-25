# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Repository development tools, independent of the installed Blender extension."""

import argparse

from tools import docs_images


def main(argv=None, *, root=None):
    parser = argparse.ArgumentParser(description=__doc__)
    groups = parser.add_subparsers(dest="group", required=True)
    assets = groups.add_parser("assets", help="Check and optimize documentation PNG assets")
    commands = assets.add_subparsers(dest="command", required=True)
    commands.add_parser("check", help="Check image references, alt text and PNG policy")
    optimize = commands.add_parser(
        "optimize",
        help="Safely palette-quantize new screenshots",
        description="Select all PNGs in this checkout's docs/images by default, or named PNGs there.",
    )
    optimize.add_argument(
        "--dry-run",
        action="store_true",
        help="List eligible inputs without running pngquant or writing",
    )
    optimize.add_argument(
        "names", nargs="*", metavar="PNG_BASENAME", help="Basenames in docs/images, never paths"
    )
    args = parser.parse_args(argv)
    root = docs_images.ROOT if root is None else root
    try:
        if args.command == "check":
            messages = docs_images.check(root)
            status = 1 if messages else 0
        else:
            status, messages = docs_images.optimize(root, args.names, dry_run=args.dry_run)
    except (OSError, ValueError) as error:
        print(f"Asset error: {error}")
        return 2
    for message in messages:
        print(message)
    if not messages:
        print("Documentation assets are ready; no changes needed.")
    return status


if __name__ == "__main__":
    raise SystemExit(main())
