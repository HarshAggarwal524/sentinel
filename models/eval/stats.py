import statistics


def compute_avg_and_stddev(values: list[float]) -> tuple[float | None, float | None]:
    """Given a list of numeric values, return (average, standard deviation).
    Returns (None, None) if the list is empty.
    Returns (value, 0.0) if there's only one value (no spread possible)."""
    if not values:
        return None, None
    avg = statistics.mean(values)
    if len(values) == 1:
        return avg, 0.0
    stddev = statistics.stdev(values)
    return avg, stddev