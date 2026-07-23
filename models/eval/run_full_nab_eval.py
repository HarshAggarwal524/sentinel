import json
import os
import sys
import pandas as pd
import wandb

sys.path.append("../baselines")
from seasonal_esd import detect_anomalies_seasonal_esd
from prophet_baseline import detect_anomalies_prophet
from scoring import evaluate_predictions

NAB_DATA_PATH = "../experiments/NAB/data"
NAB_LABELS_PATH = "../experiments/NAB/labels/combined_windows.json"

with open(NAB_LABELS_PATH) as f:
    all_labels = json.load(f)

# Collect every .csv file path NAB has
all_files = []
for category in os.listdir(NAB_DATA_PATH):
    category_path = os.path.join(NAB_DATA_PATH, category)
    if not os.path.isdir(category_path):
        continue
    for fname in os.listdir(category_path):
        if fname.endswith(".csv"):
            relative_path = f"{category}/{fname}"
            all_files.append(relative_path)

all_files.sort()
print(f"Found {len(all_files)} NAB files to evaluate.")

# Initialise a W&B run for this evaluation
run = wandb.init(
    project="sentinel-anomaly-detection",
    name="week3-baseline-eval",
    config={
        "esd_period": 288,
        "esd_threshold": 3.0,
        "prophet_interval_width": 0.99,
        "dataset": "full-NAB",
    }
)

esd_results_all = []
prophet_results_all = []

for relative_path in all_files:
    full_path = os.path.join(NAB_DATA_PATH, relative_path)
    true_windows = all_labels.get(relative_path, [])

    try:
        df = pd.read_csv(full_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        print(f"Skipping {relative_path}: {e}")
        continue

    # Seasonal-Hybrid ESD
    try:
        esd_pred = detect_anomalies_seasonal_esd(df, period=288, threshold=3.0)
        esd_score = evaluate_predictions(df, pd.Series(esd_pred), true_windows)
        esd_score["file"] = relative_path
        esd_results_all.append(esd_score)
    except Exception as e:
        print(f"ESD failed on {relative_path}: {e}")

    # Prophet (suppress its verbose logs)
    try:
        import logging
        logging.getLogger("cmdstanpy").setLevel(logging.WARNING)
        prophet_pred = detect_anomalies_prophet(df, interval_width=0.99)
        prophet_score = evaluate_predictions(df, pd.Series(prophet_pred), true_windows)
        prophet_score["file"] = relative_path
        prophet_results_all.append(prophet_score)
    except Exception as e:
        print(f"Prophet failed on {relative_path}: {e}")

    print(f"Done: {relative_path}")

# Summarise results
def average_scores(results):
    if not results:
        return {}
    df = pd.DataFrame(results)
    return {
        "avg_precision": round(df["precision"].mean(), 3),
        "avg_recall": round(df["recall"].mean(), 3),
        "avg_f1": round(df["f1"].mean(), 3),
        "avg_fp": round(df["false_positives"].mean(), 3),
    }

esd_summary = average_scores(esd_results_all)
prophet_summary = average_scores(prophet_results_all)

print("\n=== RESULTS SUMMARY ===")
print(f"Seasonal-Hybrid ESD (avg across {len(esd_results_all)} files): {esd_summary}")
print(f"Prophet            (avg across {len(prophet_results_all)} files): {prophet_summary}")

# Log to W&B
wandb.log({
    "esd/avg_precision": esd_summary.get("avg_precision"),
    "esd/avg_recall": esd_summary.get("avg_recall"),
    "esd/avg_f1": esd_summary.get("avg_f1"),
    "esd/avg_fp_per_file": esd_summary.get("avg_fp"),
    "prophet/avg_precision": prophet_summary.get("avg_precision"),
    "prophet/avg_recall": prophet_summary.get("avg_recall"),
    "prophet/avg_f1": prophet_summary.get("avg_f1"),
    "prophet/avg_fp_per_file": prophet_summary.get("avg_fp"),
})

# Also log a full per-file results table
esd_table = wandb.Table(dataframe=pd.DataFrame(esd_results_all))
prophet_table = wandb.Table(dataframe=pd.DataFrame(prophet_results_all))
wandb.log({"esd_per_file_results": esd_table, "prophet_per_file_results": prophet_table})

wandb.finish()
print("\nResults logged to Weights & Biases.")