"""Pricing helpers for the controlled diagnostic demo repository."""


def calculate_total(prices: list[float]) -> float:
    """Return a currency-rounded total and reject negative prices."""
    if any(price < 0 for price in prices):
        raise ValueError("prices cannot be negative")

    return round(sum(prices), 2)


def format_total(total: float) -> str:
    """Format a total as a dollar amount."""
    return f"${total:.2f}"
