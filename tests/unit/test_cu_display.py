# SPDX-FileCopyrightText: 2026 Scenario Inc.
# SPDX-License-Identifier: GPL-3.0-or-later

from decimal import Decimal

import pytest

from scenario.core.ui.costs import format_cu


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        (0, "0"),
        (12, "12"),
        (12.5, "12.5"),
        ("0.1234567890123456789", "0.123"),
        ("1.2345", "1.235"),
        ("0.0004", "0"),
        ("0.0005", "0.001"),
        ("1234.5678", "1,234.568"),
        ("9999.9999", "10,000"),
        (10_000, "10K"),
        (12_345, "12.3K"),
        (12_350, "12.4K"),
        (999_499, "999K"),
        (999_500, "1M"),
        (1_234_567, "1.23M"),
        (999_500_000, "1B"),
        (1_234_567_890, "1.23B"),
        (1_234_567_890_123, "1.23T"),
        (1_000_000_000_000_000, "1000T"),
    ],
)
def test_web_generation_indicator_format(value, expected):
    assert format_cu(value) == expected
    assert format_cu(Decimal(str(value))) == expected
