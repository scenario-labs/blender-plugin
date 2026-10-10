# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later
"""The compact composer's model chip label with a trained choice (#97): pure text fitting."""

from scenario.core.ui import composer_layout as cl

DOT = "·"
ELLIPSIS = "…"


def _width(text):
    return len(text)  # one unit per character keeps the expected labels readable


def test_a_base_without_trained_models_is_left_to_the_usual_clipping():
    assert cl.fit_model_label("FLUX.1 Dev", "", 0, 5, _width) == "FLUX.1 Dev"


def test_the_first_lora_is_named_and_the_others_counted_when_it_fits():
    label = cl.fit_model_label("FLUX.1 Dev", "Studio LoRA", 2, 100, _width)
    assert label == f"FLUX.1 Dev {DOT} Studio LoRA (+2)"
    single = cl.fit_model_label("FLUX.1 Dev", "Studio LoRA", 0, 100, _width)
    assert single == f"FLUX.1 Dev {DOT} Studio LoRA"


def test_the_lora_name_is_shortened_before_the_count_is_lost():
    label = cl.fit_model_label("FLUX.1 Dev", "Watercolor Landscapes", 1, 26, _width)
    assert label == f"FLUX.1 Dev {DOT} Waterco{ELLIPSIS} (+1)"
    assert _width(label) <= 26


def test_the_base_is_shortened_when_even_a_short_lora_name_cannot_fit():
    label = cl.fit_model_label("FLUX.1 Dev", "Watercolor", 3, 12, _width)
    assert label == f"FL{ELLIPSIS} {DOT} {ELLIPSIS} (+3)"
    assert _width(label) <= 12


def test_nothing_fitting_falls_back_to_the_full_label_for_clipping():
    assert cl.fit_model_label("FLUX", "LoRA", 9, 2, _width) == f"FLUX {DOT} LoRA (+9)"
