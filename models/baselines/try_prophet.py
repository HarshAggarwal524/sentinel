import pandas as pd
from prophet_baseline import detect_anomalies_prophet

df = pd.read_csv("../experiments/NAB/data/artificialWithAnomaly/art_daily_jumpsup.csv")
df["timestamp"] = pd.to_datetime(df["timestamp"])

anomalies = detect_anomalies_prophet(df, interval_width=0.99)
print(f"Total points: {len(df)}")
print(f"Flagged as anomalous: {anomalies.sum()}")
print(df[anomalies][["timestamp", "value"]].head(10))