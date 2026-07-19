"""Tests intentionally executed by the real Agent-Ops CLI."""

import pytest
from demo_app import calculate_total, format_total


@pytest.mark.parametrize(
    ("prices", "expected"),
    [
        ([], 0.0),
        ([1.25, 2.5], 3.75),
        ([0.1, 0.2], 0.3),
    ],
)
def test_calculate_total(prices: list[float], expected: float) -> None:
    assert calculate_total(prices) == expected


def test_calculate_total_rejects_negative_prices() -> None:
    with pytest.raises(ValueError, match="prices cannot be negative"):
        calculate_total([4.0, -0.01])


def test_format_total_emits_unicode_evidence() -> None:
    total = format_total(calculate_total([1.25, 2.5]))

    print(f"✅ total: {total} → ready")

    assert total == "$3.75"
