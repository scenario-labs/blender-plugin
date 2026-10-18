# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Measure the local MCP tools/list payload from source without importing Blender.

The entries are rebuilt with the same AST parser as `make mcp-docs`. A schema
value computed at import time, such as an enum built from a constant, is
resolved from the literal it names in source, so it counts at its real size.
The JSON report feeds the pull request size comment; `--base-root` adds the
baseline measured from a checkout of the pull request's base.
"""

import argparse
import ast
import importlib.util
import json
import re
from pathlib import Path
from unittest.mock import patch

ROOT = Path(__file__).resolve().parents[1]
# Claude Code shows the model at most this many characters of a tool description.
DESCRIPTION_CUT = 2048
MEASUREMENT = (
    "tools/list entries rebuilt from source and serialized as the server sends them "
    "(json.dumps, UTF-8), without the JSON-RPC envelope. estimated_tokens is bytes / 4, "
    "rounded, not a tokenizer result. model_visible_bytes counts name, description and "
    "inputSchema only, what Claude Code shows the model. headroom is 2048 minus each "
    "description's UTF-16 length; Claude Code cuts descriptions at 2048."
)


def _generator(root):
    """The MCP docs parser of the checkout being measured."""
    spec = importlib.util.spec_from_file_location(
        f"gen_mcp_docs_{abs(hash(str(root)))}", root / "tools/gen_mcp_docs.py"
    )
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def _module_constants(path):
    """Module-level names in `path` bound to literals, including those imported by name."""
    tree = ast.parse(path.read_text(encoding="utf-8"))
    names = {}
    for node in tree.body:
        if isinstance(node, ast.ImportFrom) and node.level and node.module:
            source = (
                path.parents[node.level - 1].joinpath(*node.module.split(".")).with_suffix(".py")
            )
            wanted = {alias.name: alias.asname or alias.name for alias in node.names}
            if source.is_file() and wanted:
                found = _module_constants(source)
                names.update({wanted[n]: found[n] for n in wanted if n in found})
        elif isinstance(node, ast.Assign) and len(node.targets) == 1:
            target = node.targets[0]
            try:
                value = ast.literal_eval(node.value)
            except (ValueError, TypeError, SyntaxError):
                keys = getattr(node.value, "keys", None)
                if not isinstance(node.value, ast.Dict) or not all(
                    isinstance(k, ast.Constant) for k in keys
                ):
                    continue
                # A dispatch table of literal keys: list(NAME) in a schema reads its keys.
                value = tuple(k.value for k in keys)
            if isinstance(target, ast.Name):
                names[target.id] = value
            elif isinstance(target, ast.Tuple) and all(
                isinstance(e, ast.Name) for e in target.elts
            ):
                names.update(zip((e.id for e in target.elts), value, strict=True))
    return names


def _computed_value(node, names):
    """A schema value as the server computes it: constants by name, list(NAME), dicts."""
    if isinstance(node, ast.Constant):
        return node.value
    if isinstance(node, ast.Name) and node.id in names:
        return names[node.id]
    if (
        isinstance(node, ast.Call)
        and isinstance(node.func, ast.Name)
        and node.func.id == "list"
        and len(node.args) == 1
        and not node.keywords
    ):
        return list(_computed_value(node.args[0], names))
    if isinstance(node, ast.Dict) and None not in node.keys:
        return {
            _computed_value(k, names): _computed_value(v, names)
            for k, v in zip(node.keys, node.values, strict=True)
        }
    raise ValueError(
        f"Cannot size the computed schema value {ast.unparse(node)}; extend "
        "_computed_value in tools/mcp_tool_sizes.py"
    )


def payload(root=ROOT):
    """The tools/list entries of the checkout at `root`, in the server's registration order."""
    generator = _generator(root)
    entries = []
    for _, relative in generator.GROUPS:
        path = root / relative
        names = _module_constants(path)

        def value(node, names=names):
            try:
                return ast.literal_eval(node)
            except (ValueError, TypeError):
                return _computed_value(node, names)

        with patch.object(generator, "_value", value):
            tools = generator.parse_specs(path)
        for tool in tools:
            entry = {
                "name": tool["name"],
                "description": tool["description"],
                "inputSchema": {
                    "type": "object",
                    "properties": tool["properties"],
                    "required": tool["required"],
                },
            }
            if tool["annotations"]:
                entry["annotations"] = tool["annotations"]
            entries.append(entry)
    return entries


def _bytes(value):
    return len(json.dumps(value).encode("utf-8"))


def measure(entries):
    """Sizes of one tools/list payload and each description's headroom, tightest first."""
    size = _bytes(entries)
    visible = [
        {key: entry[key] for key in ("name", "description", "inputSchema")} for entry in entries
    ]
    headroom = []
    for entry in entries:
        chars = len(entry["description"].encode("utf-16-le")) // 2
        headroom.append(
            {"name": entry["name"], "chars": chars, "headroom": DESCRIPTION_CUT - chars}
        )
    headroom.sort(key=lambda row: (row["headroom"], row["name"]))
    return {
        "tools": len(entries),
        "bytes": size,
        "estimated_tokens": round(size / 4),
        "model_visible_bytes": _bytes(visible),
        "headroom": headroom,
    }


def report(base_root=None, base_ref=None):
    return {
        "version": 1,
        "base_ref": base_ref,
        "current": measure(payload()),
        "baseline": measure(payload(base_root)) if base_root else None,
        "measurement": MEASUREMENT,
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    parser.add_argument("--base-root", type=Path, help="checkout of the base to compare with")
    parser.add_argument("--base-ref", help="full commit SHA of that checkout")
    args = parser.parse_args(argv)
    if (args.base_root is None) != (args.base_ref is None):
        parser.error("--base-root and --base-ref go together")
    if args.base_ref is not None and not re.fullmatch(r"[0-9a-f]{40}", args.base_ref):
        parser.error("--base-ref must be a full commit SHA")
    print(json.dumps(report(args.base_root, args.base_ref), indent=2))


if __name__ == "__main__":
    main()
