import json
import os
import sys
import pandas as pd
import wandb

sys.path.append("../baselines")
from seasonal_esd import detect_anomalies_seasonal_esd
from prophet_baseline import detect_anomalies_prophet
from scoring import evaluate_predictions

DATASET_PATH = "../../sock_shop_dataset"
LABELS_PATH = f"{DATASET_PATH}/labels.json"

with open(LABELS_PATH) as f:
    all_labels = json.load(f)

all_files = list(all_labels.keys())
print(f"Found {len(all_files)} labeled Sock Shop files to evaluate.")

run = wandb.init(
    project="sentinel-anomaly-detection",
    name="week4-sock-shop-live-eval",
    tags=["sock-shop-live"],
    config={
        "esd_period": 10,
        "esd_threshold": 2.5,
        "prophet_interval_width": 0.95,
        "dataset": "sock-shop-live",
        "total_files": len(all_files),
    }
)

esd_results_all = []
prophet_results_all = []

import logging
logging.getLogger("cmdstanpy").setLevel(logging.WARNING)

for relative_path in all_files:
    full_path = f"{DATASET_PATH}/{relative_path}"
    true_windows = all_labels.get(relative_path, [])

    try:
        df = pd.read_csv(full_path)
        df["timestamp"] = pd.to_datetime(df["timestamp"])
    except Exception as e:
        print(f"Skipping {relative_path}: {e}")
        continue

    # Use a smaller period for Sock Shop data (15-second intervals,
    # so period=10 = ~2.5 minutes, appropriate for short windows)
    try:
        esd_pred = detect_anomalies_seasonal_esd(df, period=10, threshold=2.5)
        esd_score = evaluate_predictions(df, pd.Series(esd_pred), true_windows)
        esd_score["file"] = relative_path
        esd_results_all.append(esd_score)
    except Exception as e:
        print(f"ESD failed on {relative_path}: {e}")

    try:
        prophet_pred = detect_anomalies_prophet(df, interval_width=0.95)
        prophet_score = evaluate_predictions(df, pd.Series(prophet_pred), true_windows)
        prophet_score["file"] = relative_path
        prophet_results_all.append(prophet_score)
    except Exception as e:
        print(f"Prophet failed on {relative_path}: {e}")

    print(f"Done: {relative_path.split('/')[-1]}")

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

print("\n=== SOCK SHOP LIVE RESULTS ===")
print(f"ESD    (avg across {len(esd_results_all)} files): {esd_summary}")
print(f"Prophet (avg across {len(prophet_results_all)} files): {prophet_summary}")

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

esd_table = wandb.Table(dataframe=pd.DataFrame(esd_results_all))
prophet_table = wandb.Table(dataframe=pd.DataFrame(prophet_results_all))
wandb.log({
    "esd_sock_shop_results": esd_table,
    "prophet_sock_shop_results": prophet_table,
})

wandb.finish()
print("\nResults logged to W&B under tag: sock-shop-live")