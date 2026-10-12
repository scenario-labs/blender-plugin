# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Advisory seam, pole and dynamic-range evidence for saved 360 panorama results.

Development tool; the extension does not ship it. `report` verifies the saved
receipts of completed smoke runs offline, copies each result whose saved
metadata declares an equirectangular projection into a private temporary
directory and runs isolated background Blender, which decodes the copies and
measures them. The values describe decoded pixels: they never accept or reject
a panorama. Seams, poles and lighting stay with human review under #98.

The module imports only the standard library at load time, so Blender runs it
directly; the host side imports the shared smoke engine when it needs it.
"""

import argparse
import array
import hashlib
import json
import math
import operator
import os
import sys
import tempfile
from decimal import Decimal
from pathlib import Path

SCHEMA_VERSION = 1
# Rows measured at each pole: one percent of the height, at least one row.
POLE_FRACTION = 0.01
PERCENTILES = ("0.1", "1", "50", "99", "99.9")
# Rec.709 luminance weights on the values Blender decodes: OpenEXR floats after
# its color space conversion (ACES2065-1 becomes scene-linear Rec.709); PNG and
# JPEG keep their stored encoding, so their values are luma, not luminance.
LUMA = (0.2126, 0.7152, 0.0722)
SUFFIXES = {"PNG": ".png", "JPEG": ".jpg", "OPEN_EXR": ".exr"}
MAX_FILES = 16
MAX_JSON_BYTES = 1024 * 1024
NOTE = (
    "Advisory measurements of decoded pixels. Seams, poles and lighting need human "
    "review in Blender; these values never accept or reject a panorama."
)


class ReportError(RuntimeError):
    """Static, public-safe failure with an explicit process outcome."""

    def __init__(self, message, code=1):
        super().__init__(message)
        self.code = code


def _shape(values, width, height):
    if (
        type(width) is not int
        or type(height) is not int
        or width < 4
        or height < 2
        or len(values) != width * height
    ):
        raise ReportError("Measure a 2:1 image of at least 4 x 2 pixels")


def _ratio(numerator, denominator):
    return numerator / denominator if denominator else None


def luminance(pixels, channels):
    """One value per pixel: Rec.709 weights on RGB, or the first channel of gray data."""
    if channels not in (1, 2, 3, 4) or len(pixels) % channels:
        raise ReportError("Unsupported pixel layout")
    if channels < 3:
        return array.array("d", pixels[0::channels])
    red, green, blue = (pixels[index::channels] for index in range(3))
    r, g, b = LUMA
    return array.array("d", map(lambda x, y, z: r * x + g * y + b * z, red, green, blue))


def seam(values, width, height):
    """Compare the wrap edge, the first and last columns, with other column pairs.

    Rows are consecutive runs of `width` values. `edge` is the mean absolute
    difference across the wrap, `neighbor` the mean over adjacent columns inside
    the image and `quarter_turn` the mean between columns a quarter of the width
    apart, wrapping around. Across a seamless wrap the edge differs like adjacent
    columns do: `edge_to_neighbor` stays around 1 or below and
    `edge_to_quarter_turn` well below 1. A ratio is None when its reference is 0.
    """
    _shape(values, width, height)
    shift = width // 4
    edge = neighbor = quarter = 0.0
    for start in range(0, width * height, width):
        row = values[start : start + width]
        edge += abs(row[0] - row[-1])
        neighbor += math.fsum(map(abs, map(operator.sub, row[1:], row[:-1])))
        quarter += math.fsum(map(abs, map(operator.sub, row, row[shift:] + row[:shift])))
    edge /= height
    neighbor /= height * (width - 1)
    quarter /= height * width
    return {
        "edge": edge,
        "neighbor": neighbor,
        "quarter_turn": quarter,
        "edge_to_neighbor": _ratio(edge, neighbor),
        "edge_to_quarter_turn": _ratio(edge, quarter),
    }


def _variance(values):
    mean = math.fsum(values) / len(values)
    return math.fsum((value - mean) ** 2 for value in values) / len(values)


def poles(values, width, height, fraction=POLE_FRACTION):
    """Row variance in the top and bottom bands relative to the whole image's variance.

    Each row at an equirectangular pole is one direction, so a uniform band
    scores near 0 and a band as varied as the whole image near 1. Rows follow
    Blender's order: the first `width` values are the bottom row. A ratio is
    None when the whole image is uniform.
    """
    _shape(values, width, height)
    rows = max(1, round(height * fraction))

    def band(first):
        return (
            math.fsum(
                _variance(values[row * width : (row + 1) * width])
                for row in range(first, first + rows)
            )
            / rows
        )

    image = _variance(values)
    return {
        "band_rows": rows,
        "top": _ratio(band(height - rows), image),
        "bottom": _ratio(band(0), image),
    }


def percentile(ordered, percent):
    """Nearest-rank percentile of a nonempty ascending sequence; `percent` is a decimal string."""
    rank = max(1, math.ceil(Decimal(percent) * len(ordered) / 100))
    return ordered[min(rank, len(ordered)) - 1]


def dynamic_range(values):
    """Scene-linear luminance percentiles and the stop span from p1 to p99.9.

    Non-finite values are counted and left out. The span is None when p1 is not
    positive, for example when at least one percent of the pixels are black.
    """
    finite = sorted(value for value in values if math.isfinite(value))
    if not finite:
        raise ReportError("The image has no finite pixel values")
    points = {name: percentile(finite, name) for name in PERCENTILES}
    low, high = points["1"], points["99.9"]
    return {
        "percentiles": points,
        "min": finite[0],
        "max": finite[-1],
        "non_finite": len(values) - len(finite),
        "stops_p1_to_p99_9": math.log2(high / low) if low > 0 else None,
    }


def metrics(pixels, width, height, channels, *, scene_linear):
    """Seam and pole ratios for every image; dynamic range for scene-linear OpenEXR data."""
    values = luminance(pixels, channels)
    _shape(values, width, height)
    return {
        "seam": seam(values, width, height),
        "poles": poles(values, width, height),
        "dynamic_range": dynamic_range(values) if scene_linear else None,
    }


def _json(value):
    return json.dumps(value, sort_keys=True, indent=2, allow_nan=False).encode() + b"\n"


def _create(path, data):
    # Binary mode: on Windows the default text mode would translate line feeds.
    flags = os.O_CREAT | os.O_EXCL | os.O_WRONLY | getattr(os, "O_BINARY", 0)
    descriptor = os.open(path, flags, 0o600)
    with os.fdopen(descriptor, "wb") as output:
        output.write(data)
        output.flush()
        os.fsync(output.fileno())


def _read_json(path):
    path = Path(path)
    if path.is_symlink() or not path.is_file() or path.stat().st_size > MAX_JSON_BYTES:
        raise ReportError("Use a regular JSON file of at most 1 MiB")
    return json.loads(path.read_bytes())


# Inside isolated background Blender.


def measure_file(path, expected):
    """Decode one private copy with Blender and measure it; Blender's main thread only.

    `expected` holds the container facts from the host preflight: format,
    width, height and whether it is OpenEXR. A decode that disagrees fails.
    """
    import bpy

    image = bpy.data.images.load(str(path), check_existing=False)
    try:
        width, height = (int(value) for value in image.size)
        if (width, height) != (expected["width"], expected["height"]) or (
            image.file_format != expected["format"]
        ):
            raise ReportError("Blender decoded a different image than its container declares")
        if expected["openexr"] and not image.is_float:
            raise ReportError("An OpenEXR result did not decode as floating-point data")
        count = len(image.pixels)
        channels = count // (width * height)
        if channels * width * height != count:
            raise ReportError("Blender returned an unexpected pixel layout")
        pixels = array.array("f", bytes(4 * count))
        image.pixels.foreach_get(pixels)
        result = metrics(pixels, width, height, channels, scene_linear=expected["openexr"])
        result["decoded"] = {
            "format": image.file_format,
            "width": width,
            "height": height,
            "channels": channels,
            "float": bool(image.is_float),
            "colorspace": image.colorspace_settings.name,
        }
        return result
    finally:
        bpy.data.images.remove(image)


def measure(manifest_path, output_path):
    """Measure every file a host manifest lists and write the results once."""
    import bpy

    manifest_path = Path(manifest_path)
    manifest = _read_json(manifest_path)
    files = manifest.get("files") if isinstance(manifest, dict) else None
    if not isinstance(files, list) or not 1 <= len(files) <= MAX_FILES:
        raise ReportError("Invalid measurement manifest")
    results = []
    for entry in files:
        name = entry.get("file") if isinstance(entry, dict) else None
        if not isinstance(name, str) or Path(name).name != name or name.startswith("."):
            raise ReportError("Invalid measurement manifest")
        results.append({"file": name, **measure_file(manifest_path.parent / name, entry)})
    _create(
        Path(output_path),
        _json({"blender": bpy.app.version_string, "files": results}),
    )


# On the host.


def collect(run_dirs, settings):
    """Verified 360 results of completed runs, with public-safe descriptions.

    Returns ([(entry, bytes, container info)], skipped result count). Only
    results whose saved Scenario metadata declares an equirectangular
    projection are measured; their bytes are bound to the download receipts.
    More than MAX_FILES of them are refused before any is read for measurement.
    """
    from scenario.core.scene import panorama_contract
    from scenario.core.scene.panorama import PanoramaError, inspect_panorama
    from tools import smoke_image as model

    if len({Path(directory).resolve() for directory in run_dirs}) != len(run_dirs):
        raise ReportError("Name each run directory once", 2)
    projected, skipped = [], 0
    for run, directory in enumerate(run_dirs, 1):
        verified = model.saved_results(directory, settings)
        producer = verified.record.intent.target_id
        for position, (item, path) in enumerate(
            zip(verified.record.results, verified.paths, strict=True), 1
        ):
            if item.asset.projection != "equirectangular":
                skipped += 1
                continue
            projected.append((run, position, producer, item, path))
            if len(projected) > MAX_FILES:
                raise ReportError(f"Measure at most {MAX_FILES} panorama files per report", 2)
    if not projected:
        raise ReportError("The runs hold no saved 360 panorama results to measure", 4)
    found = []
    for run, position, producer, item, path in projected:
        data = model.verified_bytes(item, path)
        try:
            info = inspect_panorama(data)
        except PanoramaError:
            raise ReportError("A projected result is not a supported 2:1 panorama") from None
        entry = {
            "run": run,
            "result": position,
            # Contract models are public; other model IDs are not reported.
            "model": producer if panorama_contract.contract_for(producer) else None,
            "media_type": item.asset.media_type,
            "source": item.asset.source,
            "size": item.receipt.size,
            "sha256": item.receipt.sha256,
            "container": {
                "format": info.file_format,
                "width": info.width,
                "height": info.height,
                "openexr": info.hdr_capable,
                "chromaticities": info.chromaticities,
            },
        }
        found.append((entry, data, info))
    return found, skipped


def blender_arguments(manifest, output):
    """Background Blender arguments; tools.blender_env adds offline mode and a fresh profile."""
    return [
        "--background",
        "--factory-startup",
        "--python-exit-code",
        "1",
        "--python",
        str(Path(__file__).resolve()),
        "--",
        "measure",
        "--manifest",
        str(manifest),
        "--output",
        str(output),
    ]


def _isolated(arguments, *, blender, timeout):
    from tools import blender_env

    blender_env.run(arguments, blender=blender, timeout=timeout)


def _checked(measured, names):
    """The Blender output must describe exactly the files that were sent."""
    files = measured.get("files") if isinstance(measured, dict) else None
    if (
        not isinstance(files, list)
        or [item.get("file") if isinstance(item, dict) else None for item in files] != names
        or not isinstance(measured.get("blender"), str)
        or any(set(item) != {"file", "decoded", "seam", "poles", "dynamic_range"} for item in files)
    ):
        raise ReportError("Blender returned unexpected measurements")
    return files


def _copy_matches(path, entry):
    """Whether a private copy holds exactly the bytes its download receipt describes."""
    try:
        data = path.read_bytes()
    except OSError:
        return False
    return len(data) == entry["size"] and hashlib.sha256(data).hexdigest() == entry["sha256"]


def report(run_dirs, settings, *, blender=None, timeout=600, runner=_isolated):
    """Measure the saved 360 results of completed runs; returns the report object."""
    found, skipped = collect(run_dirs, settings)
    with tempfile.TemporaryDirectory(prefix="panorama-report-") as directory:
        root = Path(directory)
        files, names = [], []
        for index, (_, data, info) in enumerate(found, 1):
            name = f"panorama-{index}{SUFFIXES[info.file_format]}"
            _create(root / name, data)
            names.append(name)
            files.append(
                {
                    "file": name,
                    "format": info.file_format,
                    "width": info.width,
                    "height": info.height,
                    "openexr": info.hdr_capable,
                }
            )
        manifest, output = root / "manifest.json", root / "measurements.json"
        _create(manifest, _json({"files": files}))
        # Blender must measure the verified bytes, so read every copy back first.
        if not all(
            _copy_matches(root / name, entry)
            for name, (entry, _, _) in zip(names, found, strict=True)
        ):
            raise ReportError(
                "A private panorama copy does not match its download receipt; nothing was measured"
            )
        try:
            runner(blender_arguments(manifest, output), blender=blender, timeout=timeout)
            measured = _read_json(output)
        except Exception:
            raise ReportError(
                "Blender could not measure the panoramas; nothing was reported"
            ) from None
        results = _checked(measured, names)
    return {
        "schema_version": SCHEMA_VERSION,
        "note": NOTE,
        "blender": measured["blender"],
        "skipped_results": skipped,
        "results": [
            {**entry, **{key: value for key, value in result.items() if key != "file"}}
            for (entry, _, _), result in zip(found, results, strict=True)
        ],
    }


def main(argv=None):
    parser = argparse.ArgumentParser(description=__doc__)
    commands = parser.add_subparsers(dest="command", required=True)
    host = commands.add_parser("report", help="Measure saved 360 results of completed runs")
    host.add_argument("--run-dir", type=Path, action="append", required=True)
    host.add_argument("--output", type=Path, required=True)
    host.add_argument("--blender", help="Blender executable; defaults to BLENDER or discovery")
    host.add_argument("--timeout", type=int, default=600, choices=range(1, 3601), metavar="SECONDS")
    inside = commands.add_parser("measure", help="Run by report inside background Blender")
    inside.add_argument("--manifest", type=Path, required=True)
    inside.add_argument("--output", type=Path, required=True)
    args = parser.parse_args(argv)
    if args.command == "measure":
        measure(args.manifest, args.output)
        return 0
    from tools.smoke_image import SmokeError

    try:
        output = args.output.absolute()
        if output.exists() or output != output.resolve():
            raise ReportError("Use a new report file without symbolic links", 2)
        from tools.dev_config import live_settings

        settings = live_settings()
        value = report(args.run_dir, settings, blender=args.blender, timeout=args.timeout)
        _create(output, _json(value))
    except (ReportError, SmokeError) as error:
        print(str(error))
        return error.code
    except SystemExit:
        print("Configure the explicit test API-key pair of these runs before reporting")
        return 2
    except Exception:
        # Raw exceptions may carry private paths or identifiers.
        print("Report stopped; the saved runs were not changed")
        return 1
    print(f"Measured {len(value['results'])} saved 360 result file(s)")
    print(f"Skipped {value['skipped_results']} result file(s) without a declared projection")
    print("Advisory only: review seams, poles and lighting in Blender before any acceptance")
    return 0


if __name__ == "__main__":
    if "bpy" in sys.modules:
        # Inside Blender: an exception sets the exit code through --python-exit-code.
        main(sys.argv[sys.argv.index("--") + 1 :])
    else:
        raise SystemExit(main())
