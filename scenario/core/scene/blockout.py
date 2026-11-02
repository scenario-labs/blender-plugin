# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Prompt to Blockout: turn a scene description into a structured greybox plan and back. No bpy, so it is testable.

An element is a primitive (box, cylinder, plane, wedge, cone, sphere) with a position, size, yaw and a semantic
category that decides its greybox colour and which sub-collection it lands in. The Scenario LLM writes the plan as
grouped JSON rows, a group label then one short array per element: under half the text of keyed objects, so plans
and above all refinements arrive sooner. parse_plan reads rows and keyed objects (older answers), tolerates the usual
noise and clamps every value so a bad answer can never place a runaway shape."""

import json
import re

MAX_ELEMENTS = 400
MIN_SIZE, MAX_SIZE = 0.02, 500.0
MAX_COORD = 2000.0

PRIMITIVES = ("box", "cylinder", "plane", "wedge", "cone", "sphere")

# semantic categories: label + a readable greybox colour (linear-ish RGB, alpha 1). A wall reads grey, vegetation
# green, a light yellow, so the blockout is legible without modelling anything.
CATEGORIES = {
    "floor": ("Floor", (0.62, 0.62, 0.64)),
    "wall": ("Wall", (0.78, 0.78, 0.80)),
    "structure": ("Structure", (0.55, 0.62, 0.72)),
    "prop": ("Prop", (0.85, 0.62, 0.35)),
    "furniture": ("Furniture", (0.70, 0.52, 0.38)),
    "vegetation": ("Vegetation", (0.42, 0.62, 0.40)),
    "vehicle": ("Vehicle", (0.75, 0.40, 0.40)),
    "water": ("Water", (0.40, 0.60, 0.78)),
    "light": ("Light", (0.90, 0.82, 0.45)),
    "other": ("Other", (0.66, 0.66, 0.66)),
}
DEFAULT_CATEGORY = "other"

# Density sets the element budget, the knob that most changes how much a blockout reads as a place.
DENSITIES = (
    ("simple", "Simple", "A small readable layout: 30 to 60 primitives", (30, 60)),
    ("medium", "Medium", "A dressed scene with some detail: 60 to 120 primitives", (60, 120)),
    ("advanced", "Advanced", "A rich scene with layered detail: 120 to 200 primitives", (120, 200)),
    ("expert", "Expert", "A dense, large scene: 200 to 350 primitives", (200, 350)),
)
DEFAULT_DENSITY = "advanced"

# Tiers pick the Scenario LLM model by family, newest first, so a model Scenario adds later is used
# without a plugin release. The fixed lists apply when the live model list is unknown or offers no
# family member. Fast runs Gemini Flash with low thinking: the lowest level 3.7 Flash supports.
TIERS = (
    ("best", "Best", "The newest Claude Opus: the richest plans, 3 to 4 minutes per plan"),
    ("fast", "Fast", "The newest Gemini Flash: a rougher plan in under a minute, at a lower price"),
)
DEFAULT_TIER = "best"
_FAMILIES = {
    "best": re.compile(r"claude-opus-(\d+)(?:-(\d+))?"),
    "fast": re.compile(r"gemini-(\d+)(?:\.(\d+))?-flash"),
}
_FALLBACKS = {
    "best": ("claude-opus-5-5", "claude-fable-5-1", "claude-sonnet-5-5", "gemini-3.7-flash"),
    "fast": ("gemini-3.7-flash", "claude-sonnet-5-5", "claude-haiku-4-5"),
}
FAST_THINKING = "low"


def model_parameters(tier, allowed=None, thinking_levels=None):
    """The Scenario LLM `model` (and Gemini `thinkingLevel`) for a tier, from the live allowed list.

    The newest model of the tier's family wins; otherwise the first fixed fallback the list offers.
    With no list (the schema is not loaded yet), the first fallback is used. Raises ValueError when
    the list offers nothing usable for the tier.
    """
    tier = tier if tier in _FAMILIES else DEFAULT_TIER
    allowed = tuple(allowed or ())
    model = None
    if allowed:
        family = []
        for value in allowed:
            match = _FAMILIES[tier].fullmatch(str(value))
            if match:
                family.append(((int(match.group(1)), int(match.group(2) or 0)), value))
        if family:
            model = max(family)[1]
        else:
            model = next((value for value in _FALLBACKS[tier] if value in allowed), None)
        if model is None:
            raise ValueError("The Scenario LLM offers no model for this tier")
    else:
        model = _FALLBACKS[tier][0]
    parameters = {"model": model}
    if (
        tier == "fast"
        and model.startswith("gemini-")
        and (not thinking_levels or FAST_THINKING in thinking_levels)
    ):
        parameters["thinkingLevel"] = FAST_THINKING
    return parameters


def model_label(model):
    """'claude-opus-5-5' -> 'Claude Opus 5.5', 'gemini-3.7-flash' -> 'Gemini 3.7 Flash'."""
    match = re.fullmatch(r"([a-z]+)-([a-z]+)-(\d+)(?:-(\d+))?", model or "")
    if match and match.group(1) == "claude":
        version = match.group(3) + ("." + match.group(4) if match.group(4) else "")
        return f"Claude {match.group(2).title()} {version}"
    words = (model or "").split("-")
    return " ".join(word.upper() if word == "gpt" else word.title() for word in words)


_ROLE = (
    "You are a senior level designer building a 3D blockout (greybox) in Blender for a game or "
    "film scene. The blockout is built only from simple primitives, but it must read clearly as "
    "the requested place: recognisable silhouette, correct real-world proportions, a clear "
    "hierarchy of masses, and enough secondary detail that someone seeing a grey render names the "
    "place at once.\n\n"
)
_FORMAT = (
    "OUTPUT: ONLY a JSON array, no prose, no code fence. Write each group as its label (a string) "
    "followed by one row per element of that group:\n"
    '["<group label>", ["<short unique name>", "<category>", "<primitive>", x, y, z, sx, sy, sz, '
    'yaw], ["<name>", ...], "<next group label>", [...], ...]\n'
    "category: floor|wall|structure|prop|furniture|vegetation|vehicle|water|light|other. "
    "primitive: box|cylinder|plane|wedge|cone|sphere. yaw: degrees about Z. Numbers have at most "
    "two decimals.\n"
    "Units are metres. Z is up. Ground is z = 0. x, y, z is the CENTRE of the shape, so an "
    "element resting on the ground has z = sz / 2, and an element resting on top of another "
    "has z = (support top) + sz / 2. sx, sy, sz is the full extent along x, y, z before the yaw "
    "rotation. A plane is a thin box. A wedge rises from -x (low edge) to +x (high edge): use two "
    "wedges back to back (one rotated 180) for a gable roof. A cone's tip points up. A cylinder's "
    "axis is Z.\n\n"
)
_RULES = (
    "COMPOSITION RULES\n"
    "1. Start from the big masses (ground, terrain, main buildings), then secondary masses "
    "(towers, wings, roofs, stairs, bridges), then tertiary detail that sells the identity "
    "(crenellations, buttresses, chimneys, window bands, doors, fences, props, vegetation).\n"
    "2. Use {low} to {high} elements. Spend at least a third of them on tertiary detail. Repeat "
    "detail rhythmically (a crenellation every 1.5 m along a wall top, a window every 3 to 4 m on "
    "a facade, a buttress every 5 to 6 m).\n"
    "3. Nothing floats and nothing is buried by accident: every element rests on the ground or on "
    "another element, or is attached to the side of one. Attached parts touch their support face "
    "exactly.\n"
    "4. No unintended overlaps. Intentional joins (a tower merging into a wall, a roof sitting on "
    "a body) are fine.\n"
    "5. Real proportions. Doors 1 m wide by 2.2 m (houses) or 3 to 4 m by 4 to 5 m (gates). Storey "
    "height 3 to 4 m. A person is 1.8 m. Keep every mass at believable metric scale for the place "
    "described.\n"
    "6. Group elements into 4 to 10 named groups that a level designer would use as collections "
    "(for example Keep, Curtain Walls, Towers, Gatehouse, Courtyard, Terrain).\n"
    "7. Categories drive colour: walls and towers of a building are structure or wall, roofs are "
    "structure, ground and paths are floor, water is water, trees and hedges are vegetation, carts "
    "and boats are vehicle, lanterns and torches are light, everything small and loose is prop.\n"
    "8. Design for a camera: leave a clear approach path and one open vantage point from which the "
    "main silhouette reads.\n\n"
    "Before answering, check every element's z against rule 3 and fix it.\n\n"
)
_IMAGE = (
    "A reference image is attached. Block out the place it shows: match its layout, silhouette, "
    "proportions and main masses, and infer plausible depth for what the picture hides. Orient it "
    "so the picture's camera looks toward +y: what is left in the picture has lower x, what is "
    "farther away has higher y.\n\n"
)


def instruction(prompt, density=DEFAULT_DENSITY, previous=None, *, image=False):
    """The LLM instruction. When `previous` (a plan) is given, it is a refinement of that plan."""
    low, high = next((r for k, _l, _d, r in DENSITIES if k == density), DENSITIES[2][3])
    head = _ROLE + _FORMAT + _RULES.replace("{low}", str(low)).replace("{high}", str(high))
    if image:
        head += _IMAGE
    if previous:
        return (
            head
            + "Here is the current plan in the same format; return an UPDATED full plan applying "
            + "this change: "
            + str(prompt)
            + "\nCurrent plan:\n"
            + encode_rows(previous)
        )
    text = str(prompt).strip() or "the place in the reference image"
    return head + "Scene to block out: " + text


def encode_rows(elements):
    """A plan as the grouped rows the LLM reads and writes: each group's label, then its rows."""
    rows, group = [], None
    for el in parse_plan(json.dumps(list(elements))):
        if el["group"] != group:
            group = el["group"]
            rows.append(group)
        row = [el["name"], el["category"], el["primitive"], *el["position"], *el["size"]]
        rows.append([*row, el["rotation"]])
    return json.dumps(rows, separators=(",", ":"))


def _from_rows(items, *, strict=False):
    """Keyed elements from grouped rows; keyed objects (older answers) pass through unchanged.

    A string sets the group of the rows after it. A row is [name, category, primitive, x, y, z,
    sx, sy, sz, yaw]; a row of another length could have lost any value, so it is never guessed:
    it is skipped, or refused when `strict`.
    """
    elements, group = [], None
    for item in items:
        if isinstance(item, str):
            group = item
        elif isinstance(item, dict):
            elements.append(item)
        elif isinstance(item, list) and len(item) == 10:
            name, category, primitive, x, y, z, sx, sy, sz, yaw = item
            element = {
                "name": name,
                "category": category,
                "primitive": primitive,
                "position": [x, y, z],
                "size": [sx, sy, sz],
                "rotation": yaw,
            }
            if group is not None:
                element["group"] = group
            elements.append(element)
        elif strict:
            raise ValueError("A Blockout row is incomplete")
    return elements


def _num(value, default, lo, hi):
    try:
        n = float(value)
    except (TypeError, ValueError):
        return default
    if n != n or n in (float("inf"), float("-inf")):
        return default
    return max(lo, min(hi, n))


def _vec3(value, defaults, lo, hi):
    seq = value if isinstance(value, (list, tuple)) else []
    return [_num(seq[i] if i < len(seq) else defaults[i], defaults[i], lo, hi) for i in range(3)]


def _recover_objects(text):
    """Every complete top-level {...} object inside an array text, for when the answer was cut off mid-element."""
    objects, depth, start, in_string, escape = [], 0, None, False, False
    for i, ch in enumerate(text):
        if in_string:
            if escape:
                escape = False
            elif ch == "\\":
                escape = True
            elif ch == '"':
                in_string = False
            continue
        if ch == '"':
            in_string = True
        elif ch == "{":
            if depth == 0:
                start = i
            depth += 1
        elif ch == "}":
            depth -= 1
            if depth == 0 and start is not None:
                try:
                    objects.append(json.loads(text[start : i + 1]))
                except ValueError:
                    pass
                start = None
    return objects


def _extract_json_array(text, *, recover=True):
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    if fence:
        text = fence.group(1).strip()
    if not recover:
        root = re.search(r"[\[{]", text)
        if root is None or root.group() != "[":
            return None  # A nested array inside a JSON object is not a plan.
    start, end = text.find("["), text.rfind("]")
    if start != -1 and end != -1 and end > start:
        try:
            return json.loads(text[start : end + 1])
        except ValueError:
            pass
    # the array was truncated (a capped output): recover the complete objects written before the cut
    if recover and start != -1:
        recovered = _recover_objects(text[start:])
        if recovered:
            return recovered
    return None


def parse_plan(text):
    """A sanitised list of blockout elements (at most MAX_ELEMENTS). Empty list when unparseable."""
    data = _extract_json_array(text)
    if not isinstance(data, list):
        return []
    elements = []
    for index, raw in enumerate(_from_rows(data)[:MAX_ELEMENTS]):
        if not isinstance(raw, dict):
            continue
        name = str(raw.get("name") or f"Block {index + 1}").strip()[:60] or f"Block {index + 1}"
        category = str(raw.get("category") or DEFAULT_CATEGORY).strip().lower()
        if category not in CATEGORIES:
            category = DEFAULT_CATEGORY
        primitive = str(raw.get("primitive") or "box").strip().lower()
        if primitive not in PRIMITIVES:
            primitive = "box"
        size = _vec3(raw.get("size"), [1.0, 1.0, 1.0], MIN_SIZE, MAX_SIZE)
        position = _vec3(raw.get("position"), [0.0, 0.0, size[2] / 2.0], -MAX_COORD, MAX_COORD)
        rotation = _num(raw.get("rotation"), 0.0, -360.0, 360.0)
        group = str(raw.get("group") or "Blockout").strip()[:60] or "Blockout"
        elements.append(
            {
                "name": name,
                "category": category,
                "primitive": primitive,
                "position": position,
                "size": size,
                "rotation": rotation,
                "group": group,
            }
        )
    return elements


def _unwrap(raw):
    """The plan inside the Scenario LLM's own answer wrapper, which some models echo.

    Only `{"results": [...]}` is unwrapped: its first result's `text`, or the list itself when it
    holds the elements. Any other object stays an object, so it is still refused as a plan.
    """
    if not isinstance(raw, dict) or set(raw) != {"results"} or not isinstance(raw["results"], list):
        return raw
    results = raw["results"]
    if (
        len(results) == 1
        and isinstance(results[0], dict)
        and isinstance(results[0].get("text"), str)
    ):
        text = results[0]["text"]
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            return _extract_json_array(text, recover=False)
    return results


def _complete_json(text):
    text = (text or "").strip()
    fence = re.search(r"```(?:json)?\s*(.+?)```", text, re.DOTALL)
    for candidate in (text, fence.group(1).strip()) if fence else (text,):
        try:
            return _unwrap(json.loads(candidate))
        except json.JSONDecodeError:
            continue
    return _extract_json_array(text, recover=False)


def parse_complete_plan(text):
    """Accept a complete array with optional prose/fences/answer wrapper, never a recovered prefix."""
    raw = _complete_json(text)
    if not isinstance(raw, list) or any(not isinstance(item, (dict, list, str)) for item in raw):
        raise ValueError("Expected a complete bounded Blockout array")
    raw = _from_rows(raw, strict=True)
    if not 1 <= len(raw) <= MAX_ELEMENTS:
        raise ValueError("Expected a complete bounded Blockout array")
    elements = parse_plan(json.dumps(raw, allow_nan=False))
    if len(elements) != len(raw):
        raise ValueError("The Blockout plan is incomplete")
    return elements


def plan_summary(elements):
    """Counts by category and by group, for the tab to show what was designed before or after building."""
    by_category, by_group = {}, {}
    for el in elements:
        by_category[el["category"]] = by_category.get(el["category"], 0) + 1
        by_group[el["group"]] = by_group.get(el["group"], 0) + 1
    return {"total": len(elements), "by_category": by_category, "by_group": by_group}
