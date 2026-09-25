# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Audit the request-building schema invariants for selected or curated models.

Live reads use the shared SDK and explicit test credentials. --offline reads a
reviewed cache or fixture directory without credentials or network access.
"""

import argparse
import datetime as dt
import hashlib
import json
import os
import pathlib
import re
import stat
import sys
import tempfile
from contextlib import ExitStack

ROOT = pathlib.Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from scenario.core.api import catalog as C
from scenario.core.api.sdk_adapter import API_URL, AdapterError, Credentials, SDKAdapter
from scenario.core.schema.params import parse_schema
from tools.dev_config import live_settings

MODEL_ID = re.compile(r"model_[A-Za-z0-9][A-Za-z0-9_.-]{0,240}\Z")
ORDER = {"HIGH": 0, "MED": 1, "LOW": 2}

CONDITIONAL_WORDS = (
    "if no",
    "if not",
    "unless",
    "when no",
    "when not",
    "optional",
    "either",
    "or a ",
    "or an ",
    "instead of",
    "alternative",
    "if none",
)


def surfaced_model_ids():
    """Every model id the plugin can put in front of a user: curated lane lists + edit3d tasks + materials."""
    ids, where = {}, {}

    def add(mid, ctx):
        where.setdefault(mid, []).append(ctx)

    for lane, models in C.DEFAULT_MODELS.items():
        for m in models:
            add(m, f"lane:{lane}")
    for task_id, _label, _desc, models in C.EDIT3D_TASKS:
        for m in models:
            add(m, f"edit3d:{task_id}")
    for m in C.PATINA_MODELS:
        add(m, "material")
    for m in where:
        ids[m] = where[m]
    return ids


def schema_cache_dir(settings, base_url, root):
    scope = [settings.credentials.key, settings.credentials.secret, settings.project_id, base_url]
    digest = hashlib.sha256(json.dumps(scope).encode()).hexdigest()
    return root / digest


def directory_info(path, *, private, missing=False):
    """Check a live-cache directory without following its final component."""
    try:
        info = path.lstat()
    except FileNotFoundError:
        if missing:
            return None
        raise
    if not stat.S_ISDIR(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400:
        raise ValueError("Expected a real cache directory")
    if os.name == "posix":
        owner = os.geteuid()
        if private:
            if info.st_uid != owner or stat.S_IMODE(info.st_mode) & 0o077:
                raise ValueError("Expected a private user-owned cache directory")
        elif info.st_uid not in {0, owner} or (
            info.st_mode & 0o022 and not info.st_mode & stat.S_ISVTX
        ):
            raise ValueError("Untrusted live-cache parent")
    return info


def live_cache_root(root):
    # Resolve parent aliases once (including macOS /var -> /private/var), then
    # use that canonical path. The supplied cache leaf itself must not be a link.
    absolute = root.absolute()
    if not absolute.name or absolute.name == "..":
        raise ValueError("Expected a named cache directory")
    try:
        parent = absolute.parent.resolve(strict=True)
    except RuntimeError:
        # Python 3.11 reports symlink loops as RuntimeError, not OSError.
        raise ValueError("Invalid live-cache parent") from None
    for ancestor in (parent, *parent.parents):
        directory_info(ancestor, private=False)
    root = parent / absolute.name
    directory_info(root, private=True, missing=True)
    return root


def check_live_cache(root, cache_dir, *, create=False):
    # Create only after a successful SDK response; failed reads/configuration
    # must not leave empty persistent directories. Never repair caller modes.
    for path in (root, cache_dir):
        if create:
            try:
                path.mkdir(mode=0o700)
            except FileExistsError:
                # Existing cache directories are expected; validate their type,
                # owner and permissions below before treating them as usable.
                pass
        directory_info(path, private=True, missing=not create)


def model_record(data, model_id):
    if isinstance(data, dict) and "model" in data:
        data = data["model"]
    if not isinstance(data, dict) or data.get("id") != model_id:
        raise ValueError("Model identity does not match")
    return data


def fetch(client, model_id, cache_dir, *, live_root):
    """Read one cached model, or use the selected SDK once; never echo response errors."""
    cache = cache_dir / f"{model_id}.json"
    try:
        if live_root is not None:
            check_live_cache(live_root, cache_dir)
        try:
            info = cache.lstat()
        except FileNotFoundError:
            info = None
        if info is not None and (
            stat.S_ISLNK(info.st_mode) or getattr(info, "st_file_attributes", 0) & 0x400
        ):
            return None, "cached model must not be a symlink"
        if info is not None:
            if not stat.S_ISREG(info.st_mode):
                return None, "cached model must be a regular file"
            return model_record(json.loads(cache.read_text(encoding="utf-8")), model_id), None
    except (OSError, ValueError):
        return None, "invalid or unreadable cached model"
    if client is None:
        return None, "model is absent from the offline cache"
    try:
        model = model_record(client.model(model_id), model_id)
    except (AdapterError, ValueError):
        return None, "SDK model read failed or returned a different identity"
    # Replace only complete cache entries. Scope directories and temporary files
    # are private; an interrupted write must not become a future cache hit.
    staged = None
    try:
        check_live_cache(live_root, cache_dir, create=True)
        with tempfile.NamedTemporaryFile(
            mode="w", encoding="utf-8", dir=cache_dir, delete=False
        ) as f:
            staged = pathlib.Path(f.name)
            json.dump(model, f)
        os.replace(staged, cache)
    except (OSError, ValueError):
        return None, "could not store the model cache"
    finally:
        if staged is not None:
            try:
                staged.unlink(missing_ok=True)
            except OSError:
                # A private temporary file may remain after filesystem failure;
                # cleanup must not replace the safe primary result with a traceback.
                pass
    return model, None


def audit_one(model_id, contexts, record, schema):
    """Return a list of (severity, code, message) findings for one model."""
    out = []
    specs = schema.specs
    files = [s for s in specs if s.is_file]
    req_files = [s for s in files if s.required_always]
    prompts = [s for s in specs if s.is_prompt]
    edit3d = any(c.startswith("edit3d") for c in contexts)
    only_edit3d = edit3d and not any(
        c.startswith("lane:") for c in contexts if not c.startswith("lane:edit3d")
    )
    mesh = C.mesh_param(record)
    resolved = {
        name for group in schema.one_of for name in group
    }  # names the parser already put in an either/or group

    # 1. Over-required inputs: a required file whose description says it is conditional (either/or with another input).
    for s in files:
        desc = (s.description or "").lower()
        if (
            s.required_always
            and s.name not in resolved
            and any(w in desc for w in CONDITIONAL_WORDS)
        ):
            out.append(
                (
                    "HIGH",
                    "conditional-required-file",
                    f"file '{s.name}' ({s.label}) is required_always but its description reads conditional",
                )
            )

    # 2. Either/or: >1 required file inputs of different kinds, or a required file plus a prompt that says 'if no ...'.
    req_files = [s for s in req_files if s.name not in resolved]
    if len(req_files) >= 2:
        kinds = ", ".join(f"{s.name}[{s.kind}]" for s in req_files)
        out.append(
            (
                "MED",
                "multiple-required-files",
                f"{len(req_files)} required file inputs at once ({kinds}); the user must supply all of them",
            )
        )
    for p in prompts:
        pdesc = (p.description or "").lower()
        if (
            p.name not in resolved
            and any(w in pdesc for w in ("if no", "if not", "unless", "when no", "instead of"))
            and req_files
        ):
            # only meaningful if the required file's OWN description is conditional (caught by check #1); otherwise
            # the prompt pairs with an optional sibling image (Meshy texturePrompt<->textureImage), which is fine.
            if any(
                (f.description or "").lower().find("if no") >= 0
                or (f.description or "").lower().find("when no") >= 0
                for f in req_files
            ):
                out.append(
                    (
                        "HIGH",
                        "prompt-is-alternative",
                        f"prompt '{p.name}' is an alternative to a required file, still blocked",
                    )
                )

    # 3. edit3d/3d models must have a detectable mesh input (kind 3d file).
    if (
        (edit3d or "3d" in [c.split(":")[-1] for c in contexts])
        and mesh is None
        and any(s.kind == "3d" for s in files) is False
    ):
        needs_mesh = edit3d
        if needs_mesh:
            out.append(
                (
                    "HIGH",
                    "no-mesh-param",
                    "edit3d model but no file input with kind '3d'; the selected mesh cannot be attached",
                )
            )

    # 4. A prompt exists but the model's only home is a lane that does not draw the prompt row.
    #    All generation lanes draw the prompt except material (Patina) and edit3d only draws it when prompt_name is set.
    if prompts and only_edit3d and not schema.prompt_name:
        out.append(
            (
                "MED",
                "prompt-not-drawn",
                "has a prompt param but schema.prompt_name is unset, so the edit3d lane will not draw it",
            )
        )

    # 5. required flag lost: raw says required true/dict but parse produced required_always False (parser bug).
    raw_by_name = {r.get("name"): r for r in record.parameters}
    for s in specs:
        raw = raw_by_name.get(s.name) or {}
        rr = raw.get("required")
        raw_required = rr is True or (isinstance(rr, dict) and rr.get("always"))
        if raw_required and not s.required_always and s.name not in resolved:
            out.append(
                (
                    "HIGH",
                    "required-flag-lost",
                    f"'{s.name}' is required in the API but parse_schema dropped required_always",
                )
            )

    # 6. no prompt and no file and no settings at all -> empty payload (model unusable as wired).
    if not specs:
        out.append(("HIGH", "empty-schema", "no parameters in the schema at all"))
    return out


def report_text(ids, findings, failed, schemas, threshold, offline):
    total = sum(len(items) for items in findings.values())
    lines = [
        "# Payload audit",
        "",
        f"UTC date: {dt.datetime.now(dt.UTC).date().isoformat()}; "
        f"mode: {'offline cache' if offline else 'live scoped cache'}; "
        f"threshold: {threshold or 'report only'}; "
        f"{len(schemas)} schemas checked; {len(failed)} fetch/schema failures; {total} findings.",
        "",
    ]
    if failed:
        lines += ["## Fetch failures", ""]
        lines += [f"- `{mid}`: {reason}" for mid, reason in sorted(failed.items())]
        lines.append("")
    lines += ["## Findings", ""]
    for mid in sorted(findings, key=lambda m: (min(ORDER[s] for s, _, _ in findings[m]), m)):
        lines.append(f"### `{mid}` [{', '.join(ids[mid])}]")
        for severity, code, message in sorted(findings[mid], key=lambda item: ORDER[item[0]]):
            # Schema text can contain URLs. Reports preserve the diagnosis but
            # never include signed query strings or arbitrary response bodies.
            message = re.sub(r"https?://[^\s<>]+", "[URL omitted]", message, flags=re.IGNORECASE)
            lines.append(f"- **{severity}** `{code}`: {message}")
        lines.append("")
    if not findings:
        lines.append("No findings.")
    return "\n".join(lines) + "\n"


def make_client(settings, base_url):
    from httpx import InvalidURL

    try:
        return SDKAdapter(
            Credentials(settings.credentials.key, settings.credentials.secret),
            project_id=settings.project_id,
            base_url=base_url,
            online=lambda: True,
        )
    except InvalidURL:
        # SDK transport construction may reject a malformed port/host before
        # the adapter can translate request errors. Keep configuration private.
        raise ValueError("Invalid SDK API base URL") from None


def run(argv=None, *, client_factory=None):
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--fail-on", choices=tuple(ORDER), help="Fail on this severity or higher")
    parser.add_argument("--report", type=pathlib.Path, help="Write Markdown here instead of stdout")
    parser.add_argument(
        "--cache", type=pathlib.Path, help="Live cache root, or explicit offline input"
    )
    parser.add_argument("--models", nargs="+", help="Selected model IDs; default: all curated IDs")
    parser.add_argument(
        "--offline", action="store_true", help="Use --cache only; no credentials or SDK"
    )
    args = parser.parse_args(argv)
    if args.offline and args.cache is None:
        parser.error("--offline requires an explicit --cache directory")
    curated = surfaced_model_ids()
    ids = {mid: curated.get(mid, ["explicit"]) for mid in sorted(set(args.models or curated))}
    if any(not MODEL_ID.fullmatch(mid) for mid in ids):
        parser.error(
            "model IDs must start with model_ and contain only ASCII letters, digits, _, . or -"
        )
    configured_root = args.cache or os.environ.get("SCHEMA_CACHE") or None
    settings, base_url = None, (os.environ.get("SCENARIO_API_BASE") or API_URL).rstrip("/")
    if not args.offline:
        try:
            settings = live_settings()
        except SystemExit:
            print(
                "no test credentials: set SCENARIO_TEST_API_KEY and SCENARIO_TEST_API_SECRET",
                file=sys.stderr,
            )
            return 2
    findings, failed, schemas = {}, {}, {}
    factory = make_client if client_factory is None else client_factory
    cleanup_failed = False

    def cleanup_cache(cache):
        nonlocal cleanup_failed
        try:
            cache.cleanup()
        except OSError:
            cleanup_failed = True
            print("Could not remove the temporary model cache", file=sys.stderr)

    with ExitStack() as stack:
        root = None
        if args.offline:
            cache_dir = args.cache
        else:
            try:
                if configured_root is None:
                    temporary_cache = tempfile.TemporaryDirectory(prefix="scenario-schema-cache-")
                    stack.callback(cleanup_cache, temporary_cache)
                    configured_root = temporary_cache.name
                root = live_cache_root(pathlib.Path(configured_root))
                cache_dir = schema_cache_dir(settings, base_url, root)
                check_live_cache(root, cache_dir)
            except (OSError, ValueError):
                print("Unsafe or inaccessible live model cache", file=sys.stderr)
                return 2
        client = None
        for mid, contexts in ids.items():
            cache = cache_dir / f"{mid}.json"
            try:
                if root is not None:
                    check_live_cache(root, cache_dir)
                try:
                    cache.lstat()
                    present = True
                except FileNotFoundError:
                    present = False
                needs_client = not args.offline and client is None and not present
            except (OSError, ValueError):
                failed[mid] = "could not inspect the model cache"
                continue
            if needs_client:
                try:
                    client = stack.enter_context(factory(settings, base_url))
                except (ValueError, AdapterError):
                    print("Invalid SDK audit configuration", file=sys.stderr)
                    return 2
            model, error = fetch(client, mid, cache_dir, live_root=root)
            if model is None:
                failed[mid] = error
                continue
            try:
                record = C.ModelRecord.from_api(model)
                schema = parse_schema(record)
                entries = audit_one(mid, contexts, record, schema)
            except (ValueError, TypeError, AttributeError, KeyError):
                failed[mid] = "model schema could not be parsed"
                continue
            schemas[mid] = (record, schema)
            if entries:
                findings[mid] = entries
    report = report_text(ids, findings, failed, schemas, args.fail_on, args.offline)
    try:
        if args.report:
            args.report.write_text(report, encoding="utf-8")
        else:
            print(report, end="")
    except OSError:
        print("Could not write the audit report", file=sys.stderr)
        return 2
    if cleanup_failed:
        return 2
    return int(
        bool(args.fail_on)
        and (
            bool(failed)
            or any(
                ORDER[severity] <= ORDER[args.fail_on]
                for entries in findings.values()
                for severity, _, _ in entries
            )
        )
    )


def main():
    return run()


if __name__ == "__main__":
    raise SystemExit(main())
