# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Advisory panorama metrics on synthetic arrays and the offline report flow."""

import json
import math
import os
import subprocess
import sys
from pathlib import Path

import pytest

from tests.unit.test_smoke_panorama import FLUX, HDR, HDRI, LDR, PLAIN, PROMPT, SETTINGS, Runs
from tests.unit.test_smoke_panorama import Service as SmokeService
from tools import panorama_report as report
from tools import smoke_image as model

ROOT = Path(__file__).resolve().parents[2]


def rows(*values):
    """Flat luminance values from rows given bottom first, as Blender stores them."""
    return [value for row in values for value in row]


def test_luminance_uses_rec709_weights_and_gray_channels():
    pixels = [1.0, 0.0, 0.0, 1.0, 0.0, 1.0, 0.0, 0.5, 0.0, 0.0, 1.0, 0.0]
    assert list(report.luminance(pixels, 4)) == pytest.approx([0.2126, 0.7152, 0.0722])
    assert list(report.luminance([0.25, 1.0, 0.5, 1.0], 2)) == [0.25, 0.5]
    assert list(report.luminance([2.0, 4.0, 8.0], 3)) == pytest.approx([3.8636])
    for pixels, channels in (([0.0] * 5, 4), ([0.0] * 5, 5)):
        with pytest.raises(report.ReportError, match="layout"):
            report.luminance(pixels, channels)


def test_seam_ratios_separate_a_wrapping_row_from_a_ramp():
    wrap = report.seam(rows([0, 1, 2, 3, 4, 3, 2, 1]) * 2, 8, 2)
    assert wrap == {
        "edge": 1.0,
        "neighbor": 1.0,
        "quarter_turn": 1.5,
        "edge_to_neighbor": 1.0,
        "edge_to_quarter_turn": pytest.approx(2 / 3),
    }
    ramp = report.seam(rows(range(8), range(8)), 8, 2)
    # Columns two apart differ by 2, except the two pairs that wrap (6).
    assert ramp == {
        "edge": 7.0,
        "neighbor": 1.0,
        "quarter_turn": 3.0,
        "edge_to_neighbor": 7.0,
        "edge_to_quarter_turn": pytest.approx(7 / 3),
    }
    flat = report.seam([0.5] * 8, 4, 2)
    assert flat["edge_to_neighbor"] is None and flat["edge_to_quarter_turn"] is None


def test_pole_ratios_compare_band_rows_with_the_whole_image():
    values = rows([0, 0, 0, 0], [0, 1, 0, 1], [0, 1, 0, 1], [2, 2, 2, 2])
    assert report.poles(values, 4, 4) == {"band_rows": 1, "top": 0.0, "bottom": 0.0}
    noisy = rows([0, 1, 0, 1], [0, 1, 0, 1], [0, 1, 0, 1], [2, 2, 2, 2])
    result = report.poles(noisy, 4, 4)
    # Bottom row variance 0.25 over the image variance 9.75 / 16.
    assert result["top"] == 0.0 and result["bottom"] == pytest.approx(0.25 / (9.75 / 16))
    assert report.poles([1.0] * 8, 4, 2) == {"band_rows": 1, "top": None, "bottom": None}
    assert report.poles([0.0] * (1536 * 768), 1536, 768)["band_rows"] == 8


@pytest.mark.parametrize("width,height,count", [(3, 2, 6), (4, 1, 4), (4, 2, 7), (4.0, 2, 8)])
def test_metrics_refuse_shapes_that_cannot_be_panoramas(width, height, count):
    with pytest.raises(report.ReportError, match="2:1 image"):
        report.seam([0.0] * count, width, height)


def test_dynamic_range_uses_nearest_rank_percentiles_and_counts_non_finite_values():
    values = [float(value) for value in range(1000, 0, -1)] + [math.nan, math.inf, -math.inf]
    result = report.dynamic_range(values)
    assert result["percentiles"] == {"0.1": 1.0, "1": 10.0, "50": 500.0, "99": 990.0, "99.9": 999.0}
    assert (result["min"], result["max"], result["non_finite"]) == (1.0, 1000.0, 3)
    assert result["stops_p1_to_p99_9"] == pytest.approx(math.log2(99.9))
    dark = report.dynamic_range([0.0] * 10 + [4.0] * 990)
    assert dark["percentiles"]["1"] == 0.0 and dark["stops_p1_to_p99_9"] is None
    uniform = report.dynamic_range([2.0] * 8)
    assert uniform["stops_p1_to_p99_9"] == 0.0
    with pytest.raises(report.ReportError, match="finite"):
        report.dynamic_range([math.nan])


def test_metrics_measure_dynamic_range_only_for_scene_linear_data():
    pixels = [value for index in range(8) for value in (index, index, index, 1.0)]
    ldr = report.metrics(pixels, 4, 2, 4, scene_linear=False)
    assert ldr["dynamic_range"] is None and set(ldr) == {"seam", "poles", "dynamic_range"}
    hdr = report.metrics(pixels, 4, 2, 4, scene_linear=True)
    assert hdr["dynamic_range"]["max"] == pytest.approx(7.0)


def test_module_loads_without_extension_or_service_imports():
    # Blender runs the file directly, where source-checkout imports are refused.
    code = (
        "import sys; sys.path.insert(0, sys.argv[1]); import tools.panorama_report; "
        "print(sorted(name for name in sys.modules if name.split('.')[0] in "
        "{'scenario', 'scenario_sdk', 'httpx'} or name == 'tools.smoke_image'))"
    )
    result = subprocess.run(
        [sys.executable, "-I", "-c", code, str(ROOT)], capture_output=True, text=True, check=True
    )
    assert result.stdout.strip() == "[]"


def test_blender_arguments_run_this_file_with_an_exit_code():
    arguments = report.blender_arguments(Path("manifest.json"), Path("out.json"))
    assert arguments[:4] == ["--background", "--factory-startup", "--python-exit-code", "1"]
    assert arguments[4:7] == ["--python", str(Path(report.__file__).resolve()), "--"]
    assert arguments[7:] == ["measure", "--manifest", "manifest.json", "--output", "out.json"]


# The host flow on real saved runs.


class FakeBlender:
    """Stands in for isolated Blender: checks the private copies and returns metrics."""

    def __init__(self, change=None):
        self.change = change
        self.seen = []
        self.directory = None

    def __call__(self, arguments, *, blender, timeout):
        manifest = Path(arguments[arguments.index("--manifest") + 1])
        output = Path(arguments[arguments.index("--output") + 1])
        self.directory = manifest.parent
        assert (blender, timeout) == ("/opt/blender", 30)
        files = json.loads(manifest.read_bytes())["files"]
        self.seen = [(entry, (manifest.parent / entry["file"]).read_bytes()) for entry in files]
        if self.change == "fail":
            raise subprocess.CalledProcessError(1, "blender")
        measured = []
        for entry in files:
            pixels = [0.5, 0.5, 0.5, 1.0] * 8
            measured.append(
                {
                    "file": entry["file"],
                    **report.metrics(pixels, 4, 2, 4, scene_linear=entry["openexr"]),
                    "decoded": {"format": entry["format"], "float": entry["openexr"]},
                }
            )
        if self.change == "names":
            measured.reverse()
        output.write_bytes(report._json({"blender": "5.1.2", "files": measured}))


@pytest.fixture
def saved(tmp_path):
    service = SmokeService()
    runs = Runs(tmp_path, service)
    runs.complete("text")
    reference = {"image": {"$panorama": "text"}}
    assert runs.quote("hdri", HDRI, "hdri", reference, saved=runs.root) == 0
    assert runs.submit("hdri") == 0
    return runs, service


def measure(runs, names, blender=None, settings=SETTINGS):
    blender = blender or FakeBlender()
    value = report.report(
        [runs.root / name for name in names],
        settings,
        blender="/opt/blender",
        timeout=30,
        runner=blender,
    )
    return value, blender


def test_report_measures_verified_projected_results_without_private_fields(saved):
    runs, service = saved
    before = len(service.calls)
    value, blender = measure(runs, ["text", "hdri"])
    assert len(service.calls) == before
    # Blender received exact copies of the receipt-verified files, never store paths.
    assert [data for _, data in blender.seen] == [LDR, HDR]
    assert [entry["file"] for entry, _ in blender.seen] == ["panorama-1.png", "panorama-2.exr"]
    assert not blender.directory.exists()
    assert value["schema_version"] == 1 and value["blender"] == "5.1.2"
    assert value["skipped_results"] == 0 and "human review" in value["note"]
    text, hdri = value["results"]
    assert {key: text[key] for key in ("run", "result", "model", "media_type", "source")} == {
        "run": 1,
        "result": 1,
        "model": FLUX,
        "media_type": "image/png",
        "source": "asset",
    }
    assert (text["size"], text["sha256"]) == (len(LDR), model.digest(LDR))
    assert text["container"] == {
        "format": "PNG",
        "width": 1536,
        "height": 768,
        "openexr": False,
        "chromaticities": None,
    }
    assert text["dynamic_range"] is None and text["seam"]["edge"] == 0.0
    assert (hdri["model"], hdri["media_type"], hdri["source"]) == (HDRI, "image/x-exr", "original")
    assert hdri["container"]["openexr"] and hdri["dynamic_range"]["stops_p1_to_p99_9"] == 0.0
    assert hdri["sha256"] == model.digest(HDR)
    serialized = report._json(value).decode()
    for private in ("asset-", "job-", "secret", "fixture", str(runs.root), "/v1/", "text"):
        assert private not in serialized


def test_report_skips_unprojected_results_and_hides_other_model_ids(saved):
    runs, service = saved
    service.models[PLAIN] = {"id": PLAIN, "type": "custom", "inputs": [PROMPT]}
    service.outputs[PLAIN] = [("image/png", None, LDR, None)]
    assert runs.quote("plain", PLAIN, "image", {"prompt": "a lake"}) == 0
    assert runs.submit("plain") == 0
    with pytest.raises(report.ReportError, match="no saved 360") as error:
        measure(runs, ["plain"])
    assert error.value.code == 4
    service.outputs[PLAIN] = [
        ("image/png", None, LDR, None),
        ("image/png", "skybox-base-360", LDR, None),
    ]
    assert runs.quote("mixed", PLAIN, "image", {"prompt": "a lake"}) == 0
    assert runs.submit("mixed") == 0
    value, _ = measure(runs, ["mixed"])
    assert value["skipped_results"] == 1
    [result] = value["results"]
    assert (result["result"], result["model"]) == (2, None)


def test_report_writes_private_copies_and_manifest_in_binary_mode(saved, monkeypatch):
    runs, _ = saved
    # A sentinel bit stands in for Windows's O_BINARY; it is cleared before the real call.
    sentinel = 1 << 40
    monkeypatch.setattr(os, "O_BINARY", sentinel, raising=False)
    real_open, opened = os.open, []

    def recording(path, flags, mode=0o777, *args, **kwargs):
        if Path(path).parent.name.startswith("panorama-report-"):
            opened.append((Path(path).name, flags))
        return real_open(path, flags & ~sentinel, mode, *args, **kwargs)

    monkeypatch.setattr(os, "open", recording)
    value, _ = measure(runs, ["text", "hdri"])
    assert len(value["results"]) == 2
    assert [name for name, _ in opened] == ["panorama-1.png", "panorama-2.exr", "manifest.json"]
    assert all(flags & sentinel for _, flags in opened)


def test_report_refuses_a_copy_that_differs_from_its_receipt_before_blender(saved, monkeypatch):
    runs, _ = saved
    original, directories = report._create, []

    def text_mode(path, data):
        # What a text-mode write on Windows does to a PNG: LF becomes CRLF.
        directories.append(path.parent)
        original(path, data.replace(b"\n", b"\r\n") if path.suffix == ".png" else data)

    monkeypatch.setattr(report, "_create", text_mode)
    blender = FakeBlender()
    with pytest.raises(report.ReportError, match="does not match its download receipt") as error:
        measure(runs, ["text", "hdri"], blender)
    assert error.value.code == 1
    assert blender.directory is None and not blender.seen
    assert directories and not directories[0].exists()


@pytest.mark.parametrize("change", ["fail", "names"])
def test_report_fails_closed_when_blender_does_not_measure_every_file(saved, change):
    runs, _ = saved
    blender = FakeBlender(change)
    with pytest.raises(report.ReportError, match="Blender") as error:
        measure(runs, ["text", "hdri"], blender)
    assert error.value.code == 1 and not blender.directory.exists()


def test_report_requires_distinct_completed_runs_of_the_selected_scope(saved, tmp_path):
    runs, _ = saved
    with pytest.raises(report.ReportError, match="once"):
        measure(runs, ["text", "text"])
    # Another spelling of the same run is the same run, refused before any is read.
    with pytest.raises(report.ReportError, match="once"):
        measure(runs, ["text", "hdri/../text"])
    with pytest.raises(model.SmokeError, match="selected credentials and project"):
        measure(runs, ["text"], settings=type(SETTINGS)(SETTINGS.credentials, "another"))
    assert runs.quote("pending", FLUX, "panorama", {"prompt": "a lake"}) == 0
    with pytest.raises(model.SmokeError, match="no completed"):
        measure(runs, ["pending"])
    [result] = (runs.root / "text" / "results").rglob("*.png")
    result.write_bytes(LDR + b"changed")
    with pytest.raises(model.SmokeError, match="could not be verified"):
        measure(runs, ["text"])


def test_report_refuses_more_files_than_its_cap_before_reading_any(saved, monkeypatch):
    runs, _ = saved
    read = []
    monkeypatch.setattr(report, "MAX_FILES", 1)
    monkeypatch.setattr(model, "verified_bytes", lambda item, path: read.append(path))
    with pytest.raises(report.ReportError, match="at most 1 panorama file") as error:
        measure(runs, ["text", "hdri"])
    assert error.value.code == 2 and read == []


def test_main_writes_a_new_private_report_and_prints_counts_only(saved, monkeypatch, capsys):
    runs, _ = saved
    output = runs.root.parent / "report.json"
    monkeypatch.setattr("tools.dev_config.live_settings", lambda: SETTINGS)
    arguments = ["report", "--run-dir", str(runs.root / "hdri"), "--output", str(output)]
    arguments += ["--blender", "/opt/blender", "--timeout", "30"]
    original = report.report

    def bounded(run_dirs, settings, *, blender, timeout):
        return original(run_dirs, settings, blender=blender, timeout=timeout, runner=FakeBlender())

    monkeypatch.setattr(report, "report", bounded)
    assert report.main(arguments) == 0
    assert output.stat().st_mode & 0o777 == 0o600
    assert json.loads(output.read_bytes())["results"][0]["source"] == "original"
    printed = capsys.readouterr().out
    assert "Measured 1 saved 360 result file(s)" in printed and "Advisory only" in printed
    assert "asset-" not in printed and str(runs.root) not in printed
    # Never overwrite a report; missing credentials stop before reading runs.
    assert report.main(arguments) == 2
    output.unlink()

    def missing():
        raise SystemExit(2)

    monkeypatch.setattr("tools.dev_config.live_settings", missing)
    assert report.main(arguments) == 2 and not output.exists()
    assert "API-key pair" in capsys.readouterr().out
