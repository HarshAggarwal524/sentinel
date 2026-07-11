import pandas as pd


def evaluate_predictions(df: pd.DataFrame, predicted_anomaly: pd.Series, labeled_windows: list) -> dict:
    """
    df: DataFrame with a 'timestamp' column (same order as predicted_anomaly).
    predicted_anomaly: boolean Series, True = flagged as anomalous.
    labeled_windows: list of [start_str, end_str] timestamp pairs (NAB's true answer key).

    Returns a dict with precision, recall, f1, tp, fp, fn.
    """
    timestamps = pd.to_datetime(df["timestamp"])
    flagged_timestamps = timestamps[predicted_anomaly]

    # Convert label windows into actual datetime ranges
    windows = [
        (pd.to_datetime(start), pd.to_datetime(end))
        for start, end in labeled_windows
    ]

    def is_inside_any_window(ts):
        return any(start <= ts <= end for start, end in windows)

    # False Positives: flagged points that fall outside every true window
    fp = sum(1 for ts in flagged_timestamps if not is_inside_any_window(ts))

    # True Positives (per NAB convention): a window counts as "caught"
    # if at least one flagged point falls inside it
    tp = 0
    fn = 0
    for start, end in windows:
        caught = any(start <= ts <= end for ts in flagged_timestamps)
        if caught:
            tp += 1
        else:
            fn += 1

    precision = tp / (tp + fp) if (tp + fp) > 0 else 0.0
    recall = tp / (tp + fn) if (tp + fn) > 0 else 0.0
    f1 = (2 * precision * recall / (precision + recall)) if (precision + recall) > 0 else 0.0

    return {
        "true_positives": tp,
        "false_positives": fp,
        "false_negatives": fn,
        "precision": round(precision, 3),
        "recall": round(recall, 3),
        "f1": round(f1, 3),
    }