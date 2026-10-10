# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""Render Image and Render Video: a capture of the scene, optional style images, a look, a precise prompt.

Render Image: viewport or camera still + style images + look -> a finished still (image edit models).
Render Video: playblast of the timeline + images (first frame, styles) + look -> a finished clip (video models with a video input).
Uploaded scene/first-frame snapshots are required before the final quote.
Prompt Spark has a separate exact-price approval before the final render quote."""

from ..core.api.catalog import tagged_video_model
from ..core.scene import capture_plan, render_prompt


def image_specs(schema):
    return [s for s in schema.specs if s.is_file and (s.kind or "image") == "image"]


def video_spec(schema):
    return next((s for s in schema.specs if s.is_file and s.kind == "video"), None)


def scene_spec(lane, schema):
    """The input that receives the capture: the video input for Render Video, the image list (else the single image) for Render Image."""
    if lane == "render_video":
        return video_spec(schema)
    specs = image_specs(schema)
    arrays = [s for s in specs if s.ptype == "file_array"]
    return (arrays or specs or [None])[0]


def style_spec(schema, exclude=None):
    """Where style images go: the image list input, or the single image input that is not already taken."""
    for spec in image_specs(schema):
        if spec.ptype == "file_array" and spec is not exclude:
            return spec
    for spec in image_specs(schema):
        if spec is not exclude:
            return spec
    return None


def first_frame_spec(schema):
    """A single image input named like a first frame (Seedance `image`, H3 `firstFrameImage`), else None."""
    for spec in image_specs(schema):
        if (
            spec.ptype == "file"
            and any(k in spec.name.lower() for k in ("image", "firstframe", "first_frame", "start"))
            and "last" not in spec.name.lower()
        ):
            return spec
    return None


def first_frame_target(schema):
    """Where Render Video sends its first frame: the first-frame input, else reference image 1.

    Some models say their first-frame input cannot be sent with reference videos
    (Seedance 2.x, Minimax H3, Wan 3.0; `Schema.exclusive`). Their first frame
    becomes the first image of the reference-image list, so the scene clip is kept.
    None when no image input can go with the clip; the first frame is then refused.
    """
    clip = video_spec(schema)
    first = first_frame_spec(schema)
    if first is None:
        options = [style_spec(schema)]
    else:
        options = [first, *(s for s in image_specs(schema) if s.ptype == "file_array")]
    return next(
        (
            spec
            for spec in options
            if spec is not None and (clip is None or not schema.excludes(spec.name, clip.name))
        ),
        None,
    )


_FIRST_FRAME_REASONS = {
    "exclusive": (
        "This model can't use an exact first frame with the scene clip",
        "No exact first frame with the scene clip",
    ),
    "no_first_frame_input": (
        "This model has no first-frame input",
        "No first-frame input on this model",
    ),
}


def first_frame_route(schema):
    """How Render Video sends the first frame, for MCP and the form; None when it cannot.

    `sent_as` is `first_frame` for the model's own first-frame input, else
    `reference_image` with a `reason` and a `note` naming the input it joins.
    """
    spec = first_frame_target(schema)
    if spec is None:
        return None
    label = spec.label or spec.name
    if spec is first_frame_spec(schema):
        return {
            "input": spec.name,
            "label": label,
            "sent_as": "first_frame",
            "reason": None,
            "note": None,
        }
    reason = "no_first_frame_input" if first_frame_spec(schema) is None else "exclusive"
    return {
        "input": spec.name,
        "label": label,
        "sent_as": "reference_image",
        "reason": reason,
        "note": f"{_FIRST_FRAME_REASONS[reason][0]}, so the image is sent as image 1 of {label}.",
    }


def first_frame_route_lines(reason, label):
    """Two short lines saying the image is sent as reference image 1, or () for an exact first frame."""
    if reason not in _FIRST_FRAME_REASONS:
        return ()
    return (_FIRST_FRAME_REASONS[reason][1], f"Sent as image 1 of {label}")


def style_input(lane, schema):
    """The native style slot; Render Video reserves its first-frame input."""
    return (
        style_spec(schema, exclude=first_frame_spec(schema))
        if lane == "render_video"
        else scene_spec(lane, schema)
    )


def hidden_inputs(schema):
    """File inputs Render Image does not use: anything that is not an image (Gemini 3.1 also takes a video)."""
    return {s.name for s in schema.specs if s.is_file and (s.kind or "image") != "image"}


def hidden_param_names(schema):
    """Parameters that only make sense with a hidden input, by name prefix (`video` -> `videoFps`) or by dependency."""
    hidden = hidden_inputs(schema)
    out = set()
    for spec in schema.specs:
        if spec.is_file or spec.is_prompt:
            continue
        lower = spec.name.lower()
        if any(lower.startswith(h.lower()) for h in hidden) or any(
            dep in hidden for dep in spec.required_if_defined
        ):
            out.add(spec.name)
    return out


def capture_source(lane_state, lane):
    base = "CAMERA" if lane_state.capture_source == "CAMERA" else "VIEWPORT"
    return base + ("_CLIP" if lane == "render_video" else "")


def decorate(scene, lane, lane_state, schema, request, for_estimate):
    """Turn a generic request into a render request: the capture first, the images in the order the prompt names them, the prompt itself."""
    spec = scene_spec(lane, schema)
    if spec is None:
        request.errors.append(
            "This model takes no "
            + ("video" if lane == "render_video" else "image")
            + " input; pick another one"
        )
        return request
    from ..core.api.errors import ScenarioError
    from . import render_references

    try:
        render_references.require_uploaded(lane, lane_state, schema, render_references.SCENE)
        first_frame = lane == "render_video" and render_references.first_frame_enabled(lane_state)
        if first_frame:
            render_references.require_uploaded(
                lane, lane_state, schema, render_references.FIRST_FRAME
            )
    except ScenarioError as error:
        request.errors.append(error.reason)
        return request
    look = lane_state.prompt.strip()
    image_count = sum(
        len(value) if isinstance(value, list) else 1
        for name, value in request.body.items()
        if (item := schema.by_name(name)) is not None
        and item.is_file
        and (item.kind or "image") == "image"
    )
    style_count = max(0, image_count - 1)
    if lane == "render_video":
        tagged = tagged_video_model(request.model_id)
        request.spark = (
            None
            if (look or not lane_state.spark_enabled)
            else {
                "kind": "video",
                "image_count": image_count,
                "first_frame": first_frame,
                "tagged": tagged,
            }
        )
        prompt = render_prompt.video_prompt(
            look or render_prompt.DEFAULT_LOOK, image_count, first_frame, tagged
        )
    else:
        request.spark = (
            None
            if (look or not lane_state.spark_enabled)
            else {"kind": "image", "style_count": style_count}
        )
        prompt = render_prompt.image_prompt(look or render_prompt.DEFAULT_LOOK, style_count)
    if schema.prompt_name:
        request.body[schema.prompt_name] = prompt
    if lane == "render_image":
        # parameters that belong to inputs the lane hides (Gemini's video -> videoFps) are not sent either
        for name in hidden_param_names(schema):
            request.body.pop(name, None)
    if request.spark is not None:
        request.errors.append(
            "Approve Prompt Spark preparation, enter a look or turn off Spark before pricing"
        )
    request.meta.update(
        {
            "render_lane": lane,
            "look": look,
            "prompt_name": schema.prompt_name or "prompt",
            "spark": bool(request.spark),
        }
    )
    return request


def on_result(rec):
    """Ignore retired unbound look events; shared prompt delivery owns its field."""


# -- drawing --------------------------------------------------------------


def _clip_info(scene):
    fps = scene.render.fps / (scene.render.fps_base or 1.0)
    return capture_plan.frame_span(
        scene.frame_start,
        scene.frame_end,
        fps,
        use_preview=scene.use_preview_range,
        preview_start=scene.frame_preview_start,
        preview_end=scene.frame_preview_end,
    )


def _draw_rendering_style(layout, context, lane, lane_state, schema):
    """A collapsible "Rendering Style" section holding the look prompt, the Prompt Spark options, the video first
    frame (Render Video only) and the style images, so everything that shapes the look sits in one place."""
    from . import panels, render_references

    box = layout.box()
    box.label(
        text="Rendering Style", icon="BRUSH_DATA"
    )  # a section like Clip to render / Camera path, always open
    panels.draw_prompt_row(box, lane_state, lane, text="Look")
    if not lane_state.prompt.strip():
        row = box.row(align=True)
        row.prop(
            lane_state, "spark_enabled", text="Prepare look with Prompt Spark"
        )  # tooltip carries the detail
    if lane == "render_video":
        _draw_first_frame(box, lane_state, schema)
    # references drawn flat inside this box (no nested boxes): the capture/frames, plus any audio reference
    styles = style_input(lane, schema)
    keep = {styles.name} if styles is not None else set()
    keep |= {
        s.name for s in schema.specs if s.is_file and s.kind == "audio"
    }  # audio reference is useful, keep it
    fixed = None
    title = (
        {
            styles.name: (
                "Style images (the capture is image 1)"
                if lane == "render_image"
                else "Reference frames"
            )
        }
        if styles is not None
        else None
    )
    panels.draw_references(
        box,
        lane_state,
        schema,
        title_for=title,
        fixed_first=fixed,
        hide={
            s.name
            for s in schema.specs
            if s.is_file and (s.name not in keep or (lane == "render_image" and s.ptype == "file"))
        },
        boxed=False,
        skip_refs={
            ref.as_pointer()
            for ref in lane_state.references
            if ref.get(render_references.ROLE)
            in {render_references.SCENE, render_references.FIRST_FRAME}
        },
    )


def _draw_first_frame(box, lane_state, schema):
    from . import first_frame_handoff, panels, render_references

    existing = render_references.slot(lane_state, render_references.FIRST_FRAME)
    row = box.row(align=True)
    row.prop(lane_state, "use_first_frame", text="First frame")
    row = box.row(align=True)
    row.prop(lane_state, "first_frame_path", text="")
    icon_id = panels.thumbnail(lane_state.first_frame_path)
    if icon_id:
        row.template_icon(icon_value=icon_id, scale=2.0)
    if lane_state.first_frame_path:
        row.operator("scenario.clear_first_frame", text="", icon="X")
    if (lane_state.use_first_frame and lane_state.first_frame_path) or existing:
        render_references.draw_slot(
            box, "render_video", lane_state, schema, render_references.FIRST_FRAME
        )
        route = first_frame_route(schema)
        lines = first_frame_route_lines(route["reason"], route["label"]) if route else ()
        if lines:
            # Say where the image goes before it is uploaded and while it is used.
            box.label(text=lines[0], icon="INFO")
            box.label(text=lines[1])
    # Read-only: the slot's provenance only, never the saved job or its file.
    if any(first_frame_handoff.provenance(ref) is not None for _, ref in existing):
        box.label(text="From a saved result", icon="FILE_REFRESH")


def draw_render_image_lane(layout, context):
    from . import generation, panels, params_ui, render_references

    scene = context.scene
    lane_state = scene.scenario.lane_state("render_image")
    box = layout.box()
    box.label(text="Scene to render", icon="RESTRICT_VIEW_OFF")
    row = box.row(align=True)
    row.prop(lane_state, "capture_source", expand=True)
    box.prop(lane_state, "force_solid")
    panels.draw_model_row(layout, lane_state, "render_image")
    schema = generation.schema_for(lane_state.model_id)
    if schema is None:
        panels.draw_schema_status(layout, lane_state, "render_image")
        return
    if scene_spec("render_image", schema) is None:
        layout.label(text="This model takes no image input; pick another one", icon="ERROR")
    else:
        render_references.draw_slot(
            box, "render_image", lane_state, schema, render_references.SCENE
        )
        box.label(text="Uploaded snapshot stays unchanged", icon="INFO")
        _draw_rendering_style(layout, context, "render_image", lane_state, schema)
    params_ui.draw_params(layout, lane_state, schema, exclude=hidden_param_names(schema))
    panels.draw_generate_row(layout, lane_state, "render_image")


def draw_render_video_lane(layout, context):
    from . import generation, panels, params_ui, render_references

    scene = context.scene
    lane_state = scene.scenario.lane_state("render_video")
    box = layout.box()
    box.label(text="Clip to render", icon="RENDER_ANIMATION")
    row = box.row(align=True)
    row.prop(lane_state, "capture_source", expand=True)
    start, end, seconds = _clip_info(scene)
    fps = scene.render.fps / (scene.render.fps_base or 1.0)
    box.label(text=f"Frames {start} to {end}: {seconds:.1f} s at {fps:g} fps, 1280x720")
    row = box.row(align=True)
    row.prop(lane_state, "force_solid")
    row.prop(lane_state, "match_timeline")
    # with Match timeline on, the model's duration drives the capture length; the camera-path section states it below.
    try:
        from . import shot_planner

        shot_planner.draw_shot_planner(layout, context)
    except ImportError:
        pass
    panels.draw_model_row(layout, lane_state, "render_video")
    schema = generation.schema_for(lane_state.model_id)
    if schema is None:
        panels.draw_schema_status(layout, lane_state, "render_video")
        return
    if scene_spec("render_video", schema) is None:
        layout.label(text="This model takes no video input; pick another one", icon="ERROR")
    else:
        render_references.draw_slot(
            box, "render_video", lane_state, schema, render_references.SCENE
        )
        box.label(text="Captures this range without padding", icon="INFO")
        _draw_rendering_style(layout, context, "render_video", lane_state, schema)
    # the model's own single-image inputs (Last Frame, First Frame) are handled by the Rendering Style section, not the generic parameter list
    params_ui.draw_params(layout, lane_state, schema)
    panels.draw_generate_row(layout, lane_state, "render_video")
