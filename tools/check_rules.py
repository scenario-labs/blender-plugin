# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Run the offline house rules over the repository or explicit files.

Default Git scans include tracked and nonignored proposed files. Each rule is a
line-oriented or AST convention check, not a general YAML, licence or
dependency validator; `reuse lint` and the wheel-bundle tests cover those.
"""

import argparse
import ast
import json
import os
import re
import subprocess
import sys
import tomllib
from collections.abc import Callable
from dataclasses import dataclass
from pathlib import Path, PurePosixPath

ROOT = Path(__file__).resolve().parents[1]
_USES = re.compile(r"^\s*(?:-\s*)?(?:uses|'uses'|\"uses\")\s*:\s*(.*)$")
_SCALAR = re.compile(r"(?:'([^'\r\n]*)'|\"([^\"\\\r\n]*)\"|([^\s'\"#]+))(?:\s+(#.*))?\s*$")
_REMOTE = re.compile(r"[\w.-]+/[\w.-]+(?:/[\w./-]+)?@[0-9a-f]{40}", re.ASCII)
_RELEASE = re.compile(r"#\s*v?\d+\.\d+\.\d+(?:[-+][\w.-]+)?(?:\s|$)", re.ASCII)
_BLOCK = re.compile(
    r"^\s*(?:-\s*)?(?P<key>[\w.-]+|'[^']+'|\"[^\"]+\")\s*:\s*"
    r"[|>](?:[1-9][+-]?|[+-][1-9]?)?\s*(?:#.*)?$"
)
_FLOW = re.compile(r"^\s*(?:-\s*)?(?:(?:[\w.-]+|'[^']+'|\"[^\"]+\")\s*:\s*)?[\[{]")
_FLOW_USES = re.compile(r"(?:^|[{,])\s*(?:uses|'uses'|\"uses\")\s*:")


@dataclass(frozen=True, order=True)
class Violation:
    path: str
    line: int
    rule: str
    message: str

    def __str__(self):
        return f"{self.path}:{self.line}: {self.rule}: {self.message}"


def tracked_files(root):
    """Include tracked and nonignored proposed files, with an archive-checkout fallback."""
    try:
        result = subprocess.run(
            ["git", "ls-files", "-z", "--cached", "--others", "--exclude-standard"],
            cwd=root,
            check=True,
            capture_output=True,
        )
    except (FileNotFoundError, subprocess.CalledProcessError):
        skipped = {".git", ".venv", "__pycache__", ".blender-profile", "dist", "workdir"}
        files = []
        for folder, directories, names in os.walk(root, followlinks=False):
            directories[:] = sorted(name for name in directories if name not in skipped)
            files.extend(Path(folder) / name for name in sorted(names))
        return files
    return [root / os.fsdecode(name) for name in result.stdout.split(b"\0") if name]


def action_file(path, root):
    try:
        relative = path.absolute().relative_to(root.absolute())
    except ValueError:
        return False
    return (
        relative.parent == Path(".github/workflows") and relative.suffix in {".yml", ".yaml"}
    ) or (
        relative.parts[:2] == (".github", "actions")
        and relative.name in {"action.yml", "action.yaml"}
    )


def actions_pinned(files, root):
    """Require one-line uses declarations with immutable remote pins and release comments."""
    violations = []
    for path in files:
        if not action_file(path, root):
            continue
        shown = display(path, root)
        if path.is_symlink():
            violations.append(Violation(shown, 1, "actions-pinned", "Use a regular action file"))
            continue
        try:
            lines = path.read_text(encoding="utf-8").splitlines()
        except (OSError, UnicodeError):
            violations.append(Violation(shown, 1, "actions-pinned", "Cannot read action file"))
            continue
        block_indent = None
        for number, line in enumerate(lines, 1):
            stripped = line.lstrip()
            if not stripped or stripped.startswith("#"):
                continue
            indent = len(line) - len(stripped)
            if block_indent is not None:
                if indent > block_indent:
                    continue  # Shell/script block contents are not action declarations.
                block_indent = None
            match = _USES.match(line)
            if match:
                scalar = _SCALAR.fullmatch(match[1])
                if scalar is None:
                    message = (
                        "Use a single-line plain or quoted uses value and trailing release comment"
                    )
                else:
                    reference = next(value for value in scalar.groups()[:3] if value is not None)
                    comment = scalar[4] or ""
                    if reference.startswith(("./", "docker://")):
                        continue
                    if _REMOTE.fullmatch(reference) and _RELEASE.match(comment):
                        continue
                    message = "Pin the remote action/workflow to a full 40-hex SHA with a # vX.Y.Z comment"
                violations.append(Violation(shown, number, "actions-pinned", message))
            elif _FLOW.match(line) and _FLOW_USES.search(line):
                violations.append(
                    Violation(
                        shown,
                        number,
                        "actions-pinned",
                        "Write uses on its own line; flow-style action declarations are unsupported",
                    )
                )
            elif block_match := _BLOCK.match(line):
                block_indent = block_match.start("key")
    return violations


# Built from parts so that neither REUSE nor this checker mistakes the
# constants for this file's own licence header.
_COPYRIGHT_TAG = "SPDX-" + "FileCopyrightText:"
_LICENCE_TAG = "SPDX-" + "License-Identifier: GPL-3.0-or-later"
_LICENCE_LINE = re.compile(re.escape(_LICENCE_TAG) + r"\s*(?:-->|\*/)?\s*$")
EM_DASH = chr(0x2014)
SPDX_SUFFIXES = {
    ".py",
    ".sh",
    ".js",
    ".mjs",
    ".ts",
    ".yml",
    ".yaml",
    ".toml",
    ".ini",
    ".cfg",
    ".sql",
    ".html",
}
SPDX_NAMES = {"Makefile"}
# Blender parses the manifest; REUSE.toml covers it until a header is validated natively.
SPDX_EXEMPT = {"scenario/blender_manifest.toml"}
# Licence texts are reproduced verbatim; media and archives are not text.
EXCLUDED_NAMES = {"LICENSE", "scenario/LICENSE"}
EXCLUDED_PREFIXES = ("LICENSES/",)
BINARY_SUFFIXES = {
    ".png",
    ".jpg",
    ".jpeg",
    ".gif",
    ".webp",
    ".ico",
    ".mp3",
    ".mp4",
    ".ogg",
    ".wav",
    ".webm",
    ".blend",
    ".glb",
    ".whl",
    ".zip",
}
# Modules that only Blender's own Python provides; numpy is bundled with Blender
# but absent from the development lock.
BLENDER_MODULES = {
    "bpy",
    "bmesh",
    "gpu",
    "gpu_extras",
    "blf",
    "mathutils",
    "bpy_extras",
    "idprop",
    "aud",
    "imbuf",
    "bl_math",
    "bl_ui",
    "bl_operators",
    "addon_utils",
    "rna_prop_ui",
    "freestyle",
    "numpy",
}
# Local MCP modules that run inside Blender and may import it.
MCP_BLENDER_MODULES = {"sandbox.py", "tools_blender.py", "tools_scenario.py"}
WHEEL_LOCK = "scenario/sdk-wheel-lock.json"
# Only the shared adapter and its extension layer talk to the SDK and its client.
SDK_MODULES = {"scenario_sdk", "httpx"}
SDK_ADAPTER = {"scenario/core/api/sdk_adapter.py", "scenario/core/api/sdk_extensions.py"}
DENYLIST = "tools/public_content_denylist.txt"
MANIFEST = "scenario/blender_manifest.toml"
# release-please owns these version copies; maintenance records and dependency
# pins legitimately name versions too.
VERSION_FILES = {
    MANIFEST,
    "scenario/__init__.py",
    ".release-please-manifest.json",
    "CHANGELOG.md",
    "pyproject.toml",
    "uv.lock",
    WHEEL_LOCK,
}
VERSION_PREFIXES = ("docs/maintenance/",)


def relative(path, root):
    """Return the POSIX path below root, or None for a file outside it."""
    try:
        return path.absolute().relative_to(root.absolute()).as_posix()
    except ValueError:
        return None


def display(path, root):
    name = relative(path, root)
    return str(path) if name is None else name


def text_lines(path):
    """Return the file's lines, or None for binary, unreadable or missing files."""
    if path.suffix.lower() in BINARY_SUFFIXES or path.is_symlink() or not path.is_file():
        return None
    try:
        data = path.read_bytes()
    except OSError:
        return None
    if b"\0" in data[:8192]:
        return None
    return data.decode("utf-8", errors="replace").splitlines()


def text_files(files, root):
    """Yield (display name, relative name, lines) for every checked text file."""
    for path in files:
        name = relative(path, root)
        if name in EXCLUDED_NAMES or (name or "").startswith(EXCLUDED_PREFIXES):
            continue
        lines = text_lines(path)
        if lines is not None:
            yield display(path, root), name, lines


def vendored_directories(root):
    """Shared skills are vendored unchanged; REUSE.toml records their licence."""
    try:
        lock = json.loads((root / "skills-lock.json").read_text(encoding="utf-8"))
        return tuple(
            PurePosixPath(skill["skillPath"]).parent.as_posix() + "/"
            for skill in lock["skills"].values()
        )
    except (OSError, ValueError, KeyError, TypeError, AttributeError):
        return ()


def spdx(files, root):
    """Require the first-party copyright and GPL lines within each source file's first 10 lines."""
    vendored = vendored_directories(root)
    violations = []
    for path in files:
        if path.suffix not in SPDX_SUFFIXES and path.name not in SPDX_NAMES:
            continue
        name = relative(path, root)
        if name is not None and (name in SPDX_EXEMPT or name.startswith(vendored)):
            continue
        lines = text_lines(path)
        if lines is None:
            continue
        head = lines[:10]
        if any(_COPYRIGHT_TAG in line for line in head) and any(
            _LICENCE_LINE.search(line) for line in head
        ):
            continue
        violations.append(
            Violation(
                display(path, root),
                1,
                "spdx",
                "missing SPDX header (CONTRIBUTING.md, Licensing of contributions)",
            )
        )
    return violations


def em_dash(files, root):
    """Reject U+2014 in maintained text."""
    return [
        Violation(shown, number, "em-dash", "em dash: use a comma, a colon or two sentences")
        for shown, _, lines in text_files(files, root)
        for number, line in enumerate(lines, 1)
        if EM_DASH in line
    ]


def python_imports(path):
    """Yield (line, top-level module) for absolute imports, nested ones included."""
    tree = ast.parse(path.read_bytes(), filename=str(path))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.lineno, alias.name.partition(".")[0]
        elif isinstance(node, ast.ImportFrom) and node.level == 0 and node.module:
            yield node.lineno, node.module.partition(".")[0]
        elif (
            isinstance(node, ast.Call)
            and (
                (isinstance(node.func, ast.Name) and node.func.id == "__import__")
                or (isinstance(node.func, ast.Attribute) and node.func.attr == "import_module")
            )
            and node.args
            and isinstance(node.args[0], ast.Constant)
            and isinstance(node.args[0].value, str)
        ):
            yield node.lineno, node.args[0].value.partition(".")[0]


def import_rule(files, root, rule, selected, message):
    """Report each import in the selected package modules for which message() returns text."""
    violations = []
    for path in files:
        name = relative(path, root)
        if name is None or not name.endswith(".py") or not selected(name) or not path.is_file():
            continue
        try:
            imports = list(python_imports(path))
        except (OSError, SyntaxError, ValueError):
            violations.append(Violation(name, 1, rule, "cannot parse this Python module"))
            continue
        violations.extend(
            Violation(name, line, rule, text)
            for line, module in imports
            if (text := message(module))
        )
    return violations


def boundary_module(name):
    if name.startswith("scenario/core/"):
        return True
    folder, _, module = name.rpartition("/")
    return folder == "scenario/mcp" and module not in MCP_BLENDER_MODULES


def bpy_boundary(files, root):
    """Keep Blender-only modules out of scenario/core and the non-Blender MCP modules."""
    return import_rule(
        files,
        root,
        "bpy-boundary",
        boundary_module,
        lambda module: (
            f"{module} is Blender-only: keep it in scenario/blender (AGENTS.md)"
            if module in BLENDER_MODULES
            else None
        ),
    )


def approved_modules(root):
    """Standard library, Blender, the package and the pinned SDK wheel closure."""
    approved = set(sys.stdlib_module_names) | BLENDER_MODULES | {"scenario", "__future__"}
    try:
        lock = json.loads((root / WHEEL_LOCK).read_text(encoding="utf-8"))
        # Each locked distribution's import name is its normalized project name.
        approved |= {wheel["package"].replace("-", "_") for wheel in lock["wheels"]}
    except (OSError, ValueError, KeyError, TypeError):
        # Without a readable lock no SDK dependency is approved, so every SDK
        # import fails this rule; test_wheel_bundle.py rejects a malformed lock.
        pass
    return approved


def approved_dependencies(files, root):
    """Reject runtime imports outside the approved set; wheel pins are checked elsewhere.

    tests/unit/test_wheel_bundle.py keeps the manifest wheels, the wheel lock, its
    licence notices and the uv.lock SDK closure identical, so a manifest wheels
    entry is not an error here.
    """
    approved = approved_modules(root)
    return import_rule(
        files,
        root,
        "approved-dependencies",
        lambda name: name.startswith("scenario/"),
        lambda module: (
            None
            if module in approved
            else f"{module} is not the standard library, Blender or the pinned SDK bundle "
            "(docs/SDK_BUNDLE.md)"
        ),
    )


def sdk_adapter(files, root):
    """Scenario service calls go through the shared adapter, not direct SDK or httpx use."""
    return import_rule(
        files,
        root,
        "sdk-adapter",
        lambda name: name.startswith("scenario/") and name not in SDK_ADAPTER,
        lambda module: (
            f"import {module} only in the shared adapter (AGENTS.md, Scenario SDK first)"
            if module in SDK_MODULES
            else None
        ),
    )


def public_content(files, root):
    """Report denylisted content by pattern line number, never by the matched text."""
    try:
        lines = (root / DENYLIST).read_text(encoding="utf-8").splitlines()
    except OSError:
        return []
    patterns = []
    violations = []
    for number, line in enumerate(lines, 1):
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        try:
            patterns.append((number, re.compile(line)))
        except re.error:
            violations.append(Violation(DENYLIST, number, "public-content", "invalid pattern"))
    for shown, name, text in text_files(files, root):
        if name == DENYLIST:
            continue
        for number, line in enumerate(text, 1):
            for pattern_line, pattern in patterns:
                if pattern.search(line):
                    violations.append(
                        Violation(
                            shown,
                            number,
                            "public-content",
                            f"matches public-content denylist pattern {pattern_line}",
                        )
                    )
    return violations


def version_literal(files, root):
    """The current version appears only where release-please maintains it."""
    try:
        version = tomllib.loads((root / MANIFEST).read_text(encoding="utf-8"))["version"]
    except (OSError, ValueError, KeyError):
        return []
    pattern = re.compile(r"(?<![\d.])" + re.escape(version) + r"(?!\.?\d)")
    return [
        Violation(
            shown, number, "version-literal", "version literal outside the release-please files"
        )
        for shown, name, lines in text_files(files, root)
        if name not in VERSION_FILES and not (name or "").startswith(VERSION_PREFIXES)
        for number, line in enumerate(lines, 1)
        if pattern.search(line)
    ]


def no_snapshot_dirs(files, root):
    """History lives in Git, not in versions/ or archive/ copies."""
    violations = []
    for path in files:
        name = relative(path, root)
        if name is None:
            continue
        parts = PurePosixPath(name).parts
        if parts[0] == "versions" or "archive" in parts[:-1]:
            violations.append(
                Violation(
                    name,
                    1,
                    "no-snapshot-dirs",
                    "history lives in git: use git show <tag>:<path> or the release zip",
                )
            )
    return violations


RULES: dict[str, Callable[[list[Path], Path], list[Violation]]] = {
    "actions-pinned": actions_pinned,
    "approved-dependencies": approved_dependencies,
    "bpy-boundary": bpy_boundary,
    "em-dash": em_dash,
    "no-snapshot-dirs": no_snapshot_dirs,
    "public-content": public_content,
    "sdk-adapter": sdk_adapter,
    "spdx": spdx,
    "version-literal": version_literal,
}


def run(rules, files, root):
    return sorted(violation for name in rules for violation in RULES[name](files, root))


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("files", nargs="*", type=Path)
    parser.add_argument("--rule", action="append", choices=sorted(RULES))
    parser.add_argument("--list", action="store_true", help="List implemented rules")
    args = parser.parse_args(argv)
    if args.list:
        print("\n".join(sorted(RULES)))
        return 0
    files = [path.absolute() for path in args.files] if args.files else tracked_files(ROOT)
    violations = run(args.rule or RULES, files, ROOT)
    for violation in violations:
        print(violation)
    return 1 if violations else 0


if __name__ == "__main__":
    raise SystemExit(main())
