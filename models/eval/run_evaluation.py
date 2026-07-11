import json
import sys
import pandas as pd

sys.path.append("../baselines")
from seasonal_esd import detect_anomalies_seasonal_esd
from prophet_baseline import detect_anomalies_prophet
from scoring import evaluate_predictions

DATA_FILE = "artificialWithAnomaly/art_daily_jumpsup.csv"
NAB_DATA_PATH = "../experiments/NAB/data"
NAB_LABELS_PATH = "../experiments/NAB/labels/combined_windows.json"

df = pd.read_csv(f"{NAB_DATA_PATH}/{DATA_FILE}")
df["timestamp"] = pd.to_datetime(df["timestamp"])

with open(NAB_LABELS_PATH) as f:
    all_labels = json.load(f)
true_windows = all_labels[DATA_FILE]

# Evaluate Seasonal-Hybrid ESD
esd_predictions = detect_anomalies_seasonal_esd(df, period=288, threshold=3.0)
esd_results = evaluate_predictions(df, pd.Series(esd_predictions), true_windows)
print("Seasonal-Hybrid ESD:", esd_results)

# Evaluate Prophet
prophet_predictions = detect_anomalies_prophet(df, interval_width=0.99)
prophet_results = evaluate_predictions(df, pd.Series(prophet_predictions), true_windows)
print("Prophet:", prophet_results)