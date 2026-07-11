import pandas as pd
from scoring import evaluate_predictions


def test_perfect_detection():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=5, freq="h")})
    predicted = pd.Series([False, False, True, False, False])
    windows = [["2024-01-01 02:00:00", "2024-01-01 02:00:00"]]
    result = evaluate_predictions(df, predicted, windows)
    assert result["true_positives"] == 1
    assert result["false_positives"] == 0
    assert result["false_negatives"] == 0
    assert result["precision"] == 1.0
    assert result["recall"] == 1.0


def test_complete_miss():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=5, freq="h")})
    predicted = pd.Series([False, False, False, False, False])
    windows = [["2024-01-01 02:00:00", "2024-01-01 02:00:00"]]
    result = evaluate_predictions(df, predicted, windows)
    assert result["true_positives"] == 0
    assert result["false_negatives"] == 1
    assert result["recall"] == 0.0


def test_false_alarm():
    df = pd.DataFrame({"timestamp": pd.date_range("2024-01-01", periods=5, freq="h")})
    predicted = pd.Series([True, False, False, False, False])
    windows = []  # no real anomalies at all
    result = evaluate_predictions(df, predicted, windows)
    assert result["false_positives"] == 1
    assert result["precision"] == 0.0