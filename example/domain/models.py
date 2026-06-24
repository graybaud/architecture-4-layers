"""Pure business logic -- no framework imports."""

def convert(amount: float, rate: float) -> float:
    """Convert an amount from one currency to another.

    Args:
        amount: The amount to convert. Must be non-negative.
        rate: The exchange rate (multiplier).

    Returns:
        The converted amount, rounded to 2 decimal places.

    Raises:
        ValueError: If amount is negative.
    """
    if amount < 0:
        raise ValueError(f"Amount must be non-negative, got {amount}")
    return round(amount * rate, 2)
