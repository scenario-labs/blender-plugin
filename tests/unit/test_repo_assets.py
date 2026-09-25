# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Exercise asset policy and the real CLI without installed optimizer dependencies."""

import binascii
import json
import os
import shutil
import struct
import subprocess
import sys
import zlib
from pathlib import Path

import pytest

from tools import docs_images
from tools.__main__ import main

ROOT = Path(__file__).resolve().parents[2]
ALT = "The image shows eight example controls beside an empty preview"


def png_bytes(*, width=8, height=4, colour_type=3, padding=0, animated=False):
    """Complete fixture PNGs, including CRCs and compressed scanlines."""

    def chunk(kind, data):
        return (
            struct.pack(">I", len(data))
            + kind
            + data
            + struct.pack(">I", binascii.crc32(kind + data) & 0xFFFFFFFF)
        )

    channels = 1 if colour_type == 3 else 3
    raw = b"".join(b"\0" + bytes(width * channels) for _ in range(height))
    data = b"\x89PNG\r\n\x1a\n" + chunk(
        b"IHDR", struct.pack(">IIBBBBB", width, height, 8, colour_type, 0, 0, 0)
    )
    if animated:
        data += chunk(b"acTL", struct.pack(">II", 1, 0))
    if colour_type == 3:
        data += chunk(b"PLTE", b"\0\0\0\xff\xff\xff")
    if padding:
        data += chunk(b"tEXt", b"Description\0" + b"x" * padding)
    if animated:
        data += chunk(b"fcTL", struct.pack(">IIIIIHHBB", 0, width, height, 0, 0, 1, 10, 0, 0))
    return data + chunk(b"IDAT", zlib.compress(raw)) + chunk(b"IEND", b"")


@pytest.fixture
def repository(tmp_path):
    root = tmp_path / "fixture repository"
    (root / "docs/images").mkdir(parents=True)
    (root / "docs/handbook-template.html").write_text("<html></html>", encoding="utf-8")
    (root / "README.md").write_text("# Example\n", encoding="utf-8")
    (root / "docs/USER_GUIDE.md").write_text(
        f"# Guide\n\n![{ALT}](images/capture.png)\n", encoding="utf-8"
    )
    (root / "docs/images/capture.png").write_bytes(png_bytes())
    return root


def snapshot(root):
    return {p.relative_to(root).as_posix(): p.read_bytes() for p in root.rglob("*") if p.is_file()}


def link_or_skip(link, target, *, directory=False):
    try:
        link.symlink_to(target, target_is_directory=directory)
    except OSError:
        pytest.skip("Host does not allow fixture symlinks")


@pytest.fixture
def optimizer(tmp_path, monkeypatch):
    """A real child process emulates pngquant output and exit statuses."""
    binary = tmp_path / "fake tools"
    binary.mkdir()
    script = binary / "fake_pngquant.py"
    script.write_text(
        "import json, os, shutil, sys, time\n"
        "from pathlib import Path\n"
        "args = sys.argv[1:]\n"
        "with open(os.environ['ASSET_TEST_CALLS'], 'a', encoding='utf-8') as log:\n"
        "    log.write(json.dumps(args) + '\\n')\n"
        "if os.environ.get('ASSET_TEST_SOURCE_COPY'):\n"
        "    shutil.copyfile(args[-1], os.environ['ASSET_TEST_SOURCE_COPY'])\n"
        "if os.environ.get('ASSET_TEST_MUTATE_PATH'):\n"
        "    Path(os.environ['ASSET_TEST_MUTATE_PATH']).write_bytes(b'concurrent edit')\n"
        "time.sleep(float(os.environ.get('ASSET_TEST_DELAY', '0')))\n"
        "status = int(os.environ.get('ASSET_TEST_STATUS', '0'))\n"
        "if status:\n"
        "    raise SystemExit(status)\n"
        "output = args[args.index('--output') + 1]\n"
        "shutil.copyfile(os.environ['ASSET_TEST_CANDIDATE'], output)\n",
        encoding="utf-8",
    )
    if os.name == "nt":
        executable = binary / "pngquant.cmd"
        executable.write_text(f'@echo off\n"{sys.executable}" "{script}" %*\n', encoding="utf-8")
    else:
        executable = binary / "pngquant"
        executable.write_text(
            f"#!{sys.executable}\n" + script.read_text(encoding="utf-8"), encoding="utf-8"
        )
        executable.chmod(0o755)
    candidate = tmp_path / "candidate.png"
    candidate.write_bytes(png_bytes())
    calls = tmp_path / "optimizer-calls.jsonl"
    monkeypatch.setenv("PATH", str(binary) + os.pathsep + os.environ.get("PATH", ""))
    monkeypatch.setenv("ASSET_TEST_CANDIDATE", str(candidate))
    monkeypatch.setenv("ASSET_TEST_CALLS", str(calls))
    return candidate, calls


def make_truecolour(root, name="capture.png"):
    image = root / "docs/images" / name
    image.write_bytes(png_bytes(colour_type=2, padding=1024))
    return image


def test_policy_accepts_palette_and_named_exceptions_without_optimizer(repository, monkeypatch):
    for name in ("scenario-logo.png", "social-preview.png"):
        (repository / "docs/images" / name).write_bytes(
            png_bytes(colour_type=2 if name == "scenario-logo.png" else 3)
        )
    (repository / "README.md").write_text("scenario-logo.png\n", encoding="utf-8")
    monkeypatch.setenv("PATH", "")
    assert docs_images.check(repository) == []
    assert main(["assets", "check"], root=repository) == 0


@pytest.mark.parametrize("document", ["README.md", "docs/USER_GUIDE.md"])
@pytest.mark.parametrize("prefix", ["/", "%2F"])
def test_root_relative_image_reports_document_path_policy(repository, document, prefix, capsys):
    target = f"{prefix}docs/images/capture.png"
    (repository / document).write_text(f"![{ALT}]({target})\n", encoding="utf-8")
    assert main(["assets", "check"], root=repository) == 1
    output = capsys.readouterr().out
    assert f"{document}: root-relative image {target}" in output
    assert "use a path relative to the document" in output
    assert "missing image" not in output


@pytest.mark.parametrize("colour_type,expected", [(3, 0), (2, 1)])
def test_generated_social_card_is_preserved_but_still_checked(
    repository, monkeypatch, colour_type, expected
):
    card = repository / "docs/images/social-preview.png"
    card.write_bytes(png_bytes(colour_type=colour_type, padding=1024))
    before = snapshot(repository)
    monkeypatch.setenv("PATH", "")
    status, messages = docs_images.optimize(repository, names=[card.name])
    assert status == expected
    assert any("regenerate with tools/make_social_preview.py" in message for message in messages)
    assert snapshot(repository) == before
    diagnostics = docs_images.check(repository)
    if expected:
        assert diagnostics == [
            "Non-palette screenshot: social-preview.png; "
            "regenerate with tools/make_social_preview.py"
        ]
    else:
        assert diagnostics == []


@pytest.mark.parametrize(
    "problem", ["orphan", "missing", "truecolour", "short-alt", "filename-alt"]
)
def test_shared_policy_rejects_each_documentation_problem(repository, problem):
    image = repository / "docs/images/capture.png"
    guide = repository / "docs/USER_GUIDE.md"
    if problem == "orphan":
        (image.parent / "orphan.png").write_bytes(png_bytes())
    elif problem == "missing":
        image.unlink()
    elif problem == "truecolour":
        make_truecolour(repository)
    else:
        alt = "Image lane" if problem == "short-alt" else "capture"
        guide.write_text(f"![{alt}](images/capture.png)\n", encoding="utf-8")
    findings = docs_images.check(repository)
    name = "orphan.png" if problem == "orphan" else "capture.png"
    assert any(name in finding for finding in findings)
    assert main(["assets", "check"], root=repository) == 1


def test_evidence_fingerprints_do_not_keep_orphans_alive(repository):
    (repository / "docs/images/orphan.png").write_bytes(png_bytes())
    (repository / "docs/evidence.md").write_text(
        '---\n{"sources": {"docs/images/orphan.png": "old fingerprint"}}\n---\n# Evidence\n',
        encoding="utf-8",
    )
    assert any("orphan.png" in finding for finding in docs_images.check(repository))


def test_evidence_body_can_reference_an_image(repository):
    (repository / "docs/images/example.png").write_bytes(png_bytes())
    (repository / "docs/evidence.md").write_text(
        f'---\n{{"type": "Evidence"}}\n---\n![{ALT}](images/example.png)\n', encoding="utf-8"
    )
    assert docs_images.check(repository) == []


def test_uppercase_png_reference_uses_the_same_filename_policy(repository, monkeypatch):
    (repository / "docs/images/capture.png").rename(repository / "docs/images/CAPTURE.PNG")
    (repository / "docs/USER_GUIDE.md").write_text(
        f"![{ALT}](images/CAPTURE.PNG)\n", encoding="utf-8"
    )
    monkeypatch.setenv("PATH", "")
    assert main(["assets", "check"], root=repository) == 0
    assert main(["assets", "optimize", "CAPTURE.PNG"], root=repository) == 0


def test_alternate_case_logo_alias_is_rejected_before_read_or_optimizer(
    repository, optimizer, monkeypatch
):
    logo = make_truecolour(repository, "scenario-logo.png")
    (repository / "README.md").write_text("scenario-logo.png\n", encoding="utf-8")
    before = snapshot(repository)
    read_regular = docs_images._read_regular
    alias_reads = []

    def case_insensitive_read(path):
        # Model macOS/Windows alias lookup even on a case-sensitive test host.
        if path.name == "SCENARIO-LOGO.PNG":
            alias_reads.append(path)
            return read_regular(logo)
        return read_regular(path)

    monkeypatch.setattr(docs_images, "_read_regular", case_insensitive_read)
    status, _ = docs_images.optimize(repository, names=["SCENARIO-LOGO.PNG"])
    assert status == 2
    assert alias_reads == []
    assert not optimizer[1].exists()
    assert snapshot(repository) == before


@pytest.mark.parametrize(
    "name",
    [
        "../capture.png",
        "docs/images/capture.png",
        "/capture.png",
        "C:\\capture.png",
        "capture.jpg",
        ".",
        "",
    ],
)
def test_selection_rejects_paths_and_unsupported_names_before_writes(repository, optimizer, name):
    make_truecolour(repository)
    before = snapshot(repository)
    status, _ = docs_images.optimize(repository, names=["capture.png", name])
    assert status == 2
    assert snapshot(repository) == before
    assert not optimizer[1].exists()


@pytest.mark.parametrize("kind", ["directory", "symlink", "missing"])
def test_selection_preflights_all_entries_before_running_tools(repository, optimizer, kind):
    make_truecolour(repository)
    bad = repository / "docs/images/z-invalid.png"
    if kind == "directory":
        bad.mkdir()
    elif kind == "symlink":
        link_or_skip(bad, repository / "docs/images/capture.png")
    before = snapshot(repository)
    status, _ = docs_images.optimize(repository, names=["capture.png", "z-invalid.png"])
    assert status == 2
    assert snapshot(repository) == before
    assert not optimizer[1].exists()


def test_default_selection_rejects_a_symlinked_image_directory(repository, tmp_path, optimizer):
    images = repository / "docs/images"
    target = tmp_path / "outside-images"
    images.rename(target)
    link_or_skip(images, target, directory=True)
    before = snapshot(target)
    status, _ = docs_images.optimize(repository)
    assert status == 2
    assert snapshot(target) == before
    assert not optimizer[1].exists()


def test_missing_optimizer_has_actionable_error_and_preserves_original(
    repository, monkeypatch, capsys
):
    make_truecolour(repository)
    before = snapshot(repository)
    monkeypatch.setenv("PATH", "")
    assert main(["assets", "optimize"], root=repository) == 2
    assert "pngquant" in capsys.readouterr().out.lower()
    assert snapshot(repository) == before


def test_success_keeps_shape_and_skips_palette_on_second_pass(repository, optimizer, monkeypatch):
    original = make_truecolour(repository)
    before = original.read_bytes()
    (repository / "docs/images/scenario-logo.png").write_bytes(before)
    (repository / "README.md").write_text("scenario-logo.png\n", encoding="utf-8")
    source_copy = optimizer[0].parent / "source-received.png"
    monkeypatch.setenv("ASSET_TEST_SOURCE_COPY", str(source_copy))
    status, _ = docs_images.optimize(repository)
    assert status == 0
    assert original.read_bytes() == optimizer[0].read_bytes()
    assert original.stat().st_size < len(before)
    assert (repository / "docs/images/scenario-logo.png").read_bytes() == before
    calls_before = optimizer[1].read_bytes()
    args = json.loads(calls_before.splitlines()[0])
    assert "--quality=70-90" in args and "--nofs" in args and "--strip" in args
    assert "--skip-if-larger" in args
    assert Path(args[-1]) != original
    assert source_copy.read_bytes() == before
    assert not Path(args[-1]).exists()
    after = snapshot(repository)
    assert docs_images.optimize(repository)[0] == 0
    assert optimizer[1].read_bytes() == calls_before
    assert snapshot(repository) == after


def test_dry_run_plans_without_optimizer_or_repository_changes(repository, optimizer, monkeypatch):
    make_truecolour(repository)
    before = snapshot(repository)
    monkeypatch.setenv("PATH", "")
    assert main(["assets", "optimize", "--dry-run"], root=repository) == 1
    assert not optimizer[1].exists()
    assert snapshot(repository) == before


@pytest.mark.parametrize("status", [98, 99, 7])
def test_optimizer_status_preserves_input_and_cleans_candidates(
    repository, optimizer, monkeypatch, status
):
    make_truecolour(repository)
    before = snapshot(repository)
    monkeypatch.setenv("ASSET_TEST_STATUS", str(status))
    result, messages = docs_images.optimize(repository)
    assert result == (1 if status in (98, 99) else 2)
    assert any(str(status) in message for message in messages)
    assert snapshot(repository) == before
    assert not list((repository / "docs/images").glob(".optimize-*"))


@pytest.mark.parametrize("kind", ["malformed", "changed-dimensions", "truecolour", "larger"])
def test_rejected_optimizer_output_never_replaces_original(repository, optimizer, kind):
    make_truecolour(repository)
    candidate, _ = optimizer
    if kind == "malformed":
        candidate.write_bytes(b"not a PNG")
    elif kind == "changed-dimensions":
        candidate.write_bytes(png_bytes(width=9))
    elif kind == "truecolour":
        candidate.write_bytes(png_bytes(colour_type=2))
    else:
        candidate.write_bytes(png_bytes(padding=2048))
    before = snapshot(repository)
    assert docs_images.optimize(repository)[0] == 2
    assert snapshot(repository) == before
    assert not list((repository / "docs/images").glob(".optimize-*"))


def test_timeout_preserves_input_and_cleans_candidate(repository, optimizer, monkeypatch):
    make_truecolour(repository)
    monkeypatch.setenv("ASSET_TEST_DELAY", "2")
    before = snapshot(repository)
    status, _ = docs_images.optimize(repository, timeout=0.05)
    assert status == 2
    assert snapshot(repository) == before
    assert not list((repository / "docs/images").glob(".optimize-*"))


def test_concurrent_source_edit_is_not_overwritten(repository, optimizer, monkeypatch):
    source = make_truecolour(repository)
    monkeypatch.setenv("ASSET_TEST_MUTATE_PATH", str(source))
    status, messages = docs_images.optimize(repository)
    assert status == 2
    assert any("Source changed" in message for message in messages)
    assert source.read_bytes() == b"concurrent edit"
    assert not list(source.parent.glob(".optimize-*"))


def test_failed_atomic_replace_preserves_original_and_cleans_candidates(
    repository, optimizer, monkeypatch
):
    make_truecolour(repository)
    before = snapshot(repository)

    def fail_replace(*args):
        raise OSError("fixture replacement failure")

    monkeypatch.setattr(docs_images.os, "replace", fail_replace)
    assert docs_images.optimize(repository)[0] == 2
    assert snapshot(repository) == before
    assert not list((repository / "docs/images").glob(".optimize-*"))


@pytest.mark.parametrize("damage", ["checksum", "truncated", "zero-dimension"])
def test_malformed_selected_source_fails_preflight_before_tools(repository, optimizer, damage):
    make_truecolour(repository)
    bad = png_bytes()
    if damage == "checksum":
        bad = bad[:-1] + bytes([bad[-1] ^ 1])
    elif damage == "truncated":
        bad = bad[:-8]
    else:
        bad = png_bytes(width=0)
    (repository / "docs/images/z-invalid.png").write_bytes(bad)
    before = snapshot(repository)
    assert docs_images.optimize(repository)[0] == 2
    assert snapshot(repository) == before
    assert not optimizer[1].exists()


def test_animated_png_is_rejected_without_flattening_or_launching_optimizer(repository, optimizer):
    (repository / "docs/images/capture.png").write_bytes(
        png_bytes(colour_type=2, padding=1024, animated=True)
    )
    before = snapshot(repository)
    status, messages = docs_images.optimize(repository)
    assert status == 2
    assert any("Animated PNG" in message for message in messages)
    assert snapshot(repository) == before
    assert not optimizer[1].exists()


def test_no_work_needs_no_optimizer(repository, monkeypatch):
    monkeypatch.setenv("PATH", "")
    assert docs_images.optimize(repository)[0] == 0
    (repository / "docs/images/capture.png").unlink()
    (repository / "docs/USER_GUIDE.md").write_text("# Guide\n", encoding="utf-8")
    assert docs_images.optimize(repository)[0] == 0


def test_actual_module_cli_uses_module_repository_not_cwd(repository, optimizer, tmp_path):
    tools = repository / "tools"
    tools.mkdir()
    for name in ("__main__.py", "docs_images.py", "check_knowledge.py"):
        shutil.copyfile(ROOT / "tools" / name, tools / name)
    make_truecolour(repository)
    cwd = tmp_path / "unrelated-directory"
    cwd.mkdir()
    (cwd / "capture.png").write_bytes(b"must not touch this unrelated file")
    env = os.environ.copy()
    env["PYTHONPATH"] = str(repository)
    result = subprocess.run(
        [sys.executable, "-m", "tools", "assets", "optimize", "capture.png"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr
    assert (repository / "docs/images/capture.png").read_bytes() == optimizer[0].read_bytes()
    assert (cwd / "capture.png").read_bytes() == b"must not touch this unrelated file"
    env["PATH"] = ""
    result = subprocess.run(
        [sys.executable, "-m", "tools", "assets", "check"],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=10,
    )
    assert result.returncode == 0, result.stdout + result.stderr


@pytest.mark.parametrize(
    "args", [[], ["other"], ["assets"], ["assets", "other"], ["assets", "check", "--dry-run"]]
)
def test_cli_rejects_unsupported_commands(args, repository):
    with pytest.raises(SystemExit) as error:
        main(args, root=repository)
    assert error.value.code == 2
