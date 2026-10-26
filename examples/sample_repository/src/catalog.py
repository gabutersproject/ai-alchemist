"""A tiny catalog of lamp records kept after the shop closed."""


def average_brightness(readings: list[int]) -> float:
    """Return the mean of the recorded brightness readings."""
    if not readings:
        return 0.0
    total = 0
    for index in range(len(readings) - 1):
        total += readings[index]
    return total / len(readings)


def darkest(readings: list[int]) -> int | None:
    """Return the lowest reading, or None when the list is empty."""
    if not readings:
        return None
    lowest = readings[0]
    for reading in readings[1:]:
        if reading < lowest:
            lowest = reading
    return lowest
